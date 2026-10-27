#include "ai/llm_worker.h"
#include "app/pipeline_admission.h"
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/tts_worker.h"
#include <atomic>
#include <future>
#include <iostream>
#include <stdexcept>
#include <vector>
using namespace std::chrono_literals;
namespace {
void check(bool value,const char* message){if(!value)throw std::runtime_error(message);}
struct Gate {
    std::promise<void> entered,release;
    std::shared_future<void> ready=entered.get_future().share(),go=release.get_future().share();
    bool opened=false;
    void open(){if(!opened){opened=true;release.set_value();}}
};
struct OpenOnExit {Gate& gate;~OpenOnExit(){gate.open();}};
InferenceResult answer(){InferenceResult r;r.success=true;r.text="fake answer";return r;}
std::atomic<int> recognizes{0};
std::function<void()> synth_hook;
void testASRContinues() {
    recognizes=0;Gate gate;std::mutex output,done_mutex;std::vector<std::uint64_t> done;
    ASRService asr;AudioBufferQueue queue(4);InferenceWorker worker(4);std::string error;
    check(worker.start(error),"ASR test worker start");OpenOnExit unblock{gate};
    std::atomic<int> submitted{0};std::atomic<int> executed{0};
    ASRWorker consumer(queue,asr,output,[&](const std::string& text){
        const auto id=static_cast<std::uint64_t>(std::stoi(text));
        const auto caller=std::this_thread::get_id();
        auto status=worker.submitTask(id,[&,id,caller](const LLMStreamCallback&){
            check(std::this_thread::get_id()!=caller,"inference ran on ASR thread");
            if(id==1){gate.entered.set_value();gate.go.wait();}
            ++executed;return answer();
        },{},[&](std::uint64_t id,const InferenceResult& r,double){
            check(r.success,"alternating task failed");std::lock_guard<std::mutex> lock(done_mutex);done.push_back(id);
        });
        check(status==LLMSubmitStatus::Accepted,"alternating submit");++submitted;
    });
    for(int id=1;id<=3;++id){AudioSegment s;s.sequence=id;s.samples.assign(160,static_cast<float>(id));queue.push(std::move(s));}
    queue.close();consumer.start();
    check(gate.ready.wait_for(2s)==std::future_status::ready,"first fake VLM not executing");
    const auto deadline=std::chrono::steady_clock::now()+2s;
    while(submitted.load()!=3 && std::chrono::steady_clock::now()<deadline)std::this_thread::yield();
    const bool continued=submitted==3 && recognizes==3 && executed==0;
    consumer.join();gate.open();worker.requestStop(StopMode::Drain);worker.join();
    check(continued,"ASR did not advance while first VLM blocked");
    check(consumer.ok() && done==std::vector<std::uint64_t>({1,2,3}),"TEXT/VISION FIFO/ASR completion");
}
void testBoundCancelExpireRestart() {
    Gate gate;std::vector<TaskDisposition> results;std::mutex mutex;InferenceWorker worker(1);std::string error;
    check(worker.start(error),"start bounded");OpenOnExit unblock{gate};
    auto done=[&](std::uint64_t,const InferenceResult& r,double){std::lock_guard<std::mutex> lock(mutex);results.push_back(r.disposition);};
    worker.submitTask(1,[&](const LLMStreamCallback&){gate.entered.set_value();gate.go.wait();return answer();},{},done);
    check(gate.ready.wait_for(2s)==std::future_status::ready,"active gate");
    TaskOptions options;options.cancelled=std::make_shared<std::atomic<bool>>(false);
    check(worker.submitTask(2,[](const LLMStreamCallback&){throw std::runtime_error("cancelled body executed");return answer();},{},done,options)==LLMSubmitStatus::Accepted,"pending submit");
    check(worker.submitTask(3,[](const LLMStreamCallback&){return answer();})==LLMSubmitStatus::QueueFull,"full not rejected");
    options.cancelled->store(true);gate.open();check(worker.waitIdleFor(2s),"cancel idle");
    TaskOptions expired;expired.deadline=TaskOptions::Clock::now()-1ms;
    worker.submitTask(4,[](const LLMStreamCallback&){throw std::runtime_error("expired body executed");return answer();},{},done,expired);
    check(worker.waitIdleFor(2s),"expiry idle");worker.requestStop(StopMode::Drain);worker.join();
    auto stats=worker.stats();check(stats.started==1 && stats.cancelled==1 && stats.expired==1 && stats.rejected_full==1 && stats.completed==3,"terminal stats");
    check(results==std::vector<TaskDisposition>({TaskDisposition::Completed,TaskDisposition::Cancelled,TaskDisposition::Expired}),"terminal callbacks");
    check(!worker.start(error),"implicit restart contract changed");check(worker.restart(error),"explicit restart failed");
    worker.submitTask(5,[](const LLMStreamCallback&){return answer();},{},[](std::uint64_t,const InferenceResult&,double){throw 1;});
    check(worker.waitIdleFor(2s),"throwing done stranded owner");worker.requestStop();worker.join();
    check(worker.stats().generation==2 && worker.stats().callback_errors==1,"restart/error publication");
}
void testStopModes() {
    for(auto mode:{StopMode::Drain,StopMode::CancelPending}) {
        Gate gate;InferenceWorker worker(1);std::string error;std::atomic<int> executed{0};
        check(worker.start(error),"stop worker start");OpenOnExit unblock{gate};
        worker.submitTask(1,[&](const LLMStreamCallback&){gate.entered.set_value();gate.go.wait();++executed;return answer();});
        check(gate.ready.wait_for(2s)==std::future_status::ready,"stop active gate");
        worker.submitTask(2,[&](const LLMStreamCallback&){++executed;return answer();});
        worker.requestStop(mode);check(worker.submitTask(3,[](const LLMStreamCallback&){return answer();})==LLMSubmitStatus::NotRunning,"accept after close");
        gate.open();worker.join();check(executed==(mode==StopMode::Drain?2:1),"drain/cancel semantics");
        check(worker.stats().completed==2,"lost terminal count");
    }
}
void testAdmission() {
    PipelineAdmission admission(2);
    auto first=admission.tryAcquire(1,1s),second=admission.tryAcquire(2,1s);
    check(first && second && !admission.tryAcquire(3,1s),"pipeline capacity");
    check(admission.cancel(2) && second->cancelled(),"cancel by id");first.reset();
    auto next=admission.tryAcquire(3,1s);check(bool(next),"credit not recovered");
    admission.close(true);check(next->cancelled() && !admission.tryAcquire(4,1s),"close/cancel flags");
    second.reset();next.reset();check(admission.stats().inflight==0 && admission.stats().peak==2,"ticket lifetime");
    // Race final ticket release against cancellation; cancellation map holds flags, not tickets.
    for(int i=0;i<200;++i){PipelineAdmission a(1);auto ticket=a.tryAcquire(1,1s);std::thread close([&]{a.close(true);});ticket.reset();close.join();check(a.stats().inflight==0,"release/cancel deadlock");}
}
void testTTS() {
    TTSService tts;AlsaPlaybackService playback;std::string error;
    check(tts.initialize("fake",error) && playback.open("fake",16000,error),"fake services init");
    Gate gate;synth_hook=[&]{gate.entered.set_value();gate.go.wait();};
    TTSWorker worker(tts,playback,1);check(worker.start(error),"tts start");OpenOnExit unblock{gate};
    worker.submit(1,"first");check(gate.ready.wait_for(2s)==std::future_status::ready,"tts synth active");
    TaskOptions expired;expired.deadline=TaskOptions::Clock::now()-1ms;
    check(worker.submit(2,"stale",{},expired)==TTSSubmitStatus::Accepted,"tts pending");
    check(worker.submit(3,"full")==TTSSubmitStatus::QueueFull,"tts bound");
    gate.open();check(worker.waitIdleFor(2s),"tts drain");worker.requestStop(StopMode::Drain);worker.join();
    check(worker.stats().started==1 && worker.stats().expired==1 && worker.stats().completed==2,"tts expiry accounting");
    synth_hook={};check(worker.restart(error),"tts restart");
    worker.submit(4,"again",[](std::uint64_t,const TTSWorkerResult&,double){throw 1;});
    check(worker.waitIdleFor(2s),"tts callback failure idle");worker.requestStop();worker.join();
    check(worker.stats().generation==2 && worker.stats().callback_errors==1,"tts callback errors");
}
void testTraceOwnership() {
    auto trace=std::make_shared<RequestTrace>(777);std::weak_ptr<RequestTrace> weak=trace;
    {
        RequestTraceScope outer(trace);check(currentRequestTrace()==trace && image_profile_request_id==777,"trace scope enter");
        {RequestTraceScope empty({});check(!currentRequestTrace() && image_profile_request_id==0,"trace nested clear");}
        check(currentRequestTrace()==trace && image_profile_request_id==777,"trace scope restore");
    }
    check(!currentRequestTrace() && image_profile_request_id==0,"trace scope leaked TLS");
    TaskOptions options;options.trace=trace;std::string error;InferenceWorker inference(1);
    check(inference.start(error),"trace inference start");std::atomic<bool> infer_ok{false},done_ok{false};
    inference.submitTask(777,[&](const LLMStreamCallback&){infer_ok=currentRequestTrace()==trace && image_profile_request_id==777;return answer();},{},[&](std::uint64_t,const InferenceResult&,double){done_ok=currentRequestTrace()==trace;},options);
    check(inference.waitIdleFor(2s),"trace inference wait");inference.requestStop();inference.join();
    check(infer_ok && done_ok,"trace did not propagate through inference/callback");
    TTSService tts;AlsaPlaybackService playback;check(tts.initialize("fake",error) && playback.open("fake",16000,error),"trace fake init");
    std::atomic<bool> tts_ok{false};synth_hook=[&]{tts_ok=currentRequestTrace()==trace && image_profile_request_id==777;};
    TTSWorker worker(tts,playback,1);check(worker.start(error),"trace TTS start");
    worker.submit(777,"trace",{},options);check(worker.waitIdleFor(2s),"trace TTS wait");worker.requestStop();worker.join();synth_hook={};check(tts_ok,"trace did not propagate to TTS");
    ASRService asr;AudioBufferQueue queue(1);std::mutex output;std::atomic<bool> context_ok{false};
    ASRWorker consumer(queue,asr,output,{},[&](const std::string&,const AudioSegment& segment){context_ok=segment.sequence==777 && segment.trace==trace && currentRequestTrace()==trace;});
    AudioSegment segment;segment.sequence=777;segment.trace=trace;segment.samples={1};queue.push(std::move(segment));queue.close();consumer.start();consumer.join();check(consumer.ok() && context_ok,"trace ASR context callback");
    options.trace.reset();trace.reset();check(weak.expired(),"completed requests retained profiling ownership");
}
} // namespace

// Test-only service implementations: no SDK, ALSA, model or device is called.
ASRService::~ASRService()=default;
bool ASRService::recognize(const std::vector<float>& samples,std::string& text,double& latency,std::string& error){++recognizes;text=std::to_string(static_cast<int>(samples.at(0)));latency=0;error.clear();return true;}
struct SherpaOnnxOfflineTts {};
struct _snd_pcm {};
TTSService::~TTSService(){shutdown();}
bool TTSService::initialize(const std::string&,std::string&,std::int32_t,std::int32_t){static SherpaOnnxOfflineTts fake;tts_=&fake;return true;}
bool TTSService::synthesize(const std::string&,TTSAudio& output,std::string&){if(synth_hook)synth_hook();output.sample_rate=16000;output.samples.assign(160,0);return true;}
void TTSService::shutdown() noexcept {tts_=nullptr;}
AlsaPlaybackService::~AlsaPlaybackService(){close();}
bool AlsaPlaybackService::open(const std::string&,std::int32_t,std::string&){static _snd_pcm fake;pcm_=&fake;return true;}
bool AlsaPlaybackService::play(const float*,std::size_t,std::string&){return true;}
void AlsaPlaybackService::close() noexcept {pcm_=nullptr;}
int main() try {
    testASRContinues();testBoundCancelExpireRestart();testStopModes();testAdmission();testTTS();testTraceOwnership();
    std::cout<<"PASS deterministic async pipeline: ASR progression, alternating FIFO, overload, cancel/expiry, restart, callback failures, ticket races, TTS. Fake services only.\n";return 0;
} catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
