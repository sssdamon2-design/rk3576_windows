#include <algorithm>
#include "ai/llm_worker.h"

#include <atomic>
#include <exception>
#include <stdexcept>
#include <utility>

LLMWorker::LLMWorker(LLMEngine& engine, std::size_t capacity)
    : engine_(engine), capacity_(capacity)
{
    if (capacity_ == 0)
        throw std::invalid_argument(
            "LLMWorker capacity must be greater than zero");
}

LLMWorker::~LLMWorker()
{
    requestStop();
    join();
}

bool LLMWorker::start(std::string& error)
{
    std::lock_guard<std::mutex> lock(mutex_);
    error.clear();

    if (started_ || stop_requested_)
    {
        error = "LLMWorker can only be started once";
        return false;
    }

    try
    {
        thread_ = std::thread(&LLMWorker::run, this);
        started_ = true;
    }
    catch (const std::exception& e)
    {
        error = std::string("LLMWorker thread creation failed: ")
              + e.what();
        return false;
    }

    return true;
}

LLMSubmitStatus LLMWorker::submit(
    std::uint64_t id,
    std::string question,
    LLMWorkerChunk on_chunk,
    LLMWorkerDone on_done)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
            return LLMSubmitStatus::NotRunning;

        if (pending_.size() >= capacity_)
        {
            ++rejected_;
            return LLMSubmitStatus::QueueFull;
        }

        Task task;
        task.id = id;
        task.question = std::move(question);
        task.on_chunk = std::move(on_chunk);
        task.on_done = std::move(on_done);
        task.enqueued_at = std::chrono::steady_clock::now();

        pending_.push_back(std::move(task));
        measured_peak_=std::max(measured_peak_,pending_.size());
    }

    cv_.notify_one();
    return LLMSubmitStatus::Accepted;
}

void LLMWorker::requestStop() noexcept
{
    {
        std::lock_guard<std::mutex> lock(mutex_);
        stop_requested_ = true;
    }

    cv_.notify_all();
}

void LLMWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

std::size_t LLMWorker::pendingCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return pending_.size();
}

std::size_t LLMWorker::rejectedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return rejected_;
}

void LLMWorker::run()
{
    for (;;)
    {
        Task task;
        bool cancelled = false;

        {
            std::unique_lock<std::mutex> lock(mutex_);

            cv_.wait(lock, [this] {
                return stop_requested_ || !pending_.empty();
            });

            if (pending_.empty() && stop_requested_)
                return;

            task = std::move(pending_.front());
            pending_.pop_front();
            cancelled = stop_requested_;
        }

        InferenceResult result;
        double queue_wait_ms = -1.0;

        if (cancelled)
        {
            result.error_message =
                "LLM request cancelled: worker stopping";
        }
        else
        {
            const auto now = std::chrono::steady_clock::now();

            queue_wait_ms =
                std::chrono::duration<double, std::milli>(
                    now - task.enqueued_at).count();

            std::atomic<bool> chunk_callback_failed{false};

            try
            {
                result = engine_.inferStreaming(
                    task.question,
                    [&](const std::string& chunk)
                    {
                        if (!task.on_chunk)
                            return;

                        try
                        {
                            task.on_chunk(task.id, chunk);
                        }
                        catch (...)
                        {
                            chunk_callback_failed.store(true);
                        }
                    });
            }
            catch (const std::exception& e)
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    std::string("LLMWorker inference exception: ")
                    + e.what();
            }
            catch (...)
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    "LLMWorker inference: unknown exception";
            }

            if (chunk_callback_failed.load())
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    "LLMWorker chunk callback threw an exception";
            }
        }

        if (task.on_done)
        {
            try
            {
                task.on_done(task.id, result, queue_wait_ms);
            }
            catch (...)
            {
                // 上层回调异常不能终止整个 Worker。
            }
        }
    }
}
