#include "ai/llm_worker.h"
#include <algorithm>
#include <atomic>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <utility>

LLMWorker::LLMWorker(LLMEngine& engine,std::size_t capacity):LLMWorker(capacity){engine_=&engine;}
LLMWorker::LLMWorker(std::size_t capacity):capacity_(capacity) {
    if (!capacity_) throw std::invalid_argument("LLMWorker capacity must be greater than zero");
}
LLMWorker::~LLMWorker(){requestStop();join();}
bool LLMWorker::start(std::string& error) {
    std::lock_guard<std::mutex> lock(mutex_);error.clear();
    if (started_ || stop_requested_) {error="LLMWorker can only be started once; use restart after stop/join";return false;}
    try {thread_=std::thread(&LLMWorker::run,this);started_=true;++stats_.generation;}
    catch(const std::exception& e){error=std::string("LLMWorker thread creation failed: ")+e.what();return false;}
    return true;
}
bool LLMWorker::restart(std::string& error) {
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!started_ || !stop_requested_ || thread_.joinable() || !pending_.empty()) {error="restart requires stopped and joined worker";return false;}
     started_=false;stop_requested_=false;rejected_=0;
     const auto generation=stats_.generation;stats_={};stats_.generation=generation;}
    return start(error);
}
LLMSubmitStatus LLMWorker::submit(std::uint64_t id,std::string question,LLMWorkerChunk chunk,LLMWorkerDone done,TaskOptions options) {
    if (!engine_) throw std::logic_error("submit(text) requires an LLMEngine");
    return submitTask(id,[this,question=std::move(question)](const LLMStreamCallback& callback){
        return engine_->inferStreaming(question,callback);
    },std::move(chunk),std::move(done),std::move(options));
}
LLMSubmitStatus LLMWorker::submitTask(std::uint64_t id,Inference inference,LLMWorkerChunk chunk,LLMWorkerDone done,TaskOptions options) {
    if (!inference) throw std::invalid_argument("Empty inference task");
    const auto trace=options.trace;std::chrono::steady_clock::time_point enqueued{};std::size_t depth=0;
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!started_ || stop_requested_) {++stats_.rejected_stopped;if(trace)trace->mark("inference_rejected_stopped");return LLMSubmitStatus::NotRunning;}
     if (pending_.size()>=capacity_) {++rejected_;++stats_.rejected_full;if(trace)trace->mark("inference_rejected_full");return LLMSubmitStatus::QueueFull;}
     Task task;task.id=id;task.inference=std::move(inference);task.on_chunk=std::move(chunk);task.on_done=std::move(done);
     task.enqueued_at=std::chrono::steady_clock::now();enqueued=task.enqueued_at;task.options=std::move(options);
     pending_.push_back(std::move(task));++stats_.accepted;depth=pending_.size();stats_.peak_depth=std::max(stats_.peak_depth,depth);}
    if(trace)trace->mark("inference_enqueued",enqueued,static_cast<double>(depth));
    cv_.notify_one();return LLMSubmitStatus::Accepted;
}
void LLMWorker::requestStop(StopMode mode) noexcept {
    {std::lock_guard<std::mutex> lock(mutex_);
     if (!stop_requested_ || mode==StopMode::CancelPending) stop_mode_=mode;
     stop_requested_=true;}
    cv_.notify_all();
}
void LLMWorker::join(){if(thread_.joinable())thread_.join();}
std::size_t LLMWorker::pendingCount() const {std::lock_guard<std::mutex> lock(mutex_);return pending_.size();}
std::size_t LLMWorker::rejectedCount() const {std::lock_guard<std::mutex> lock(mutex_);return rejected_;}
WorkerStats LLMWorker::stats() const {std::lock_guard<std::mutex> lock(mutex_);auto copy=stats_;copy.pending=pending_.size();return copy;}
bool LLMWorker::waitIdleFor(std::chrono::milliseconds timeout) {
    std::unique_lock<std::mutex> lock(mutex_);
    return cv_.wait_for(lock,timeout,[&]{return pending_.empty() && stats_.active==0;});
}
void LLMWorker::run() {
    using Clock=std::chrono::steady_clock;
    for (;;) {
        Task task;bool cancel=false;
        {std::unique_lock<std::mutex> lock(mutex_);
         cv_.wait(lock,[&]{return stop_requested_ || !pending_.empty();});
         if (pending_.empty() && stop_requested_) return;
         task=std::move(pending_.front());pending_.pop_front();stats_.active=1;
         cancel=stop_requested_ && stop_mode_==StopMode::CancelPending;}
        const auto begin=Clock::now();
        RequestTraceScope trace_scope(task.options.trace);
        traceMark("inference_dequeued",begin);
        const double waited=std::chrono::duration<double,std::milli>(begin-task.enqueued_at).count();
        InferenceResult result;
        result.disposition=task.options.disposition(task.enqueued_at,begin,cancel);
        const auto disposition=result.disposition;
        if (disposition!=TaskDisposition::Completed) {
            traceMark(disposition==TaskDisposition::Cancelled?"inference_cancelled":"inference_expired");
            result.error_message=std::string("Inference task ")+dispositionName(disposition);
            std::cerr<<"[Inference "<<dispositionName(disposition)<<" #"<<task.id<<"] queue_ms="<<waited<<'\n';
        } else {
            {std::lock_guard<std::mutex> lock(mutex_);++stats_.started;}
            traceMark("inference_begin");
            std::atomic<bool> chunk_failed{false};
            try {
                result=task.inference([&](const std::string& chunk){
                    if (task.on_chunk) try {task.on_chunk(task.id,chunk);} catch(...) {chunk_failed.store(true);}
                });
            } catch(const std::exception& e) {result.success=false;result.text.clear();result.error_message=std::string("LLMWorker inference exception: ")+e.what();}
              catch(...) {result.success=false;result.text.clear();result.error_message="LLMWorker inference: unknown exception";}
            if (chunk_failed.load()) {result.success=false;result.text.clear();result.error_message="LLMWorker chunk callback threw an exception";}
            traceMark(result.success?"inference_end":"inference_failed");
        }
        const double service=std::chrono::duration<double,std::milli>(Clock::now()-begin).count();
        bool callback_failed=false;
        if (task.on_done) try {task.on_done(task.id,result,disposition==TaskDisposition::Cancelled?-1.0:waited);}
        catch(...) {callback_failed=true;std::cerr<<"[Inference callback error #"<<task.id<<"]\n";}
        const bool failed=disposition==TaskDisposition::Completed && !result.success;
        task=Task{};
        {std::lock_guard<std::mutex> lock(mutex_);
         ++stats_.completed;stats_.active=0;stats_.failed+=failed;
         stats_.cancelled+=disposition==TaskDisposition::Cancelled;stats_.expired+=disposition==TaskDisposition::Expired;
         stats_.callback_errors+=callback_failed;stats_.queue_wait_sum_ms+=waited;
         stats_.queue_wait_max_ms=std::max(stats_.queue_wait_max_ms,waited);stats_.service_sum_ms+=service;}
        cv_.notify_all();
    }
}
