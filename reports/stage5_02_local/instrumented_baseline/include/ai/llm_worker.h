#pragma once

#include "ai/llm_engine.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

enum class LLMSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

using LLMWorkerChunk =
    std::function<void(std::uint64_t, const std::string&)>;

using LLMWorkerDone =
    std::function<void(std::uint64_t, const InferenceResult&, double)>;

// 单消费者、有界排队；不拥有 LLMEngine。
// Engine 必须比 Worker 活得更久。
// 回调中不得销毁 Worker，也不能 join Worker 自己的线程。
// start/join/destruction must be serialized by the owner thread.
// Callback captures (including mutexes/counters) must outlive the joined Worker.
class LLMWorker final
{
public:
    explicit LLMWorker(LLMEngine& engine, std::size_t capacity = 2);
    ~LLMWorker();

    LLMWorker(const LLMWorker&) = delete;
    LLMWorker& operator=(const LLMWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 正在执行的任务不占用等待队列容量。
    LLMSubmitStatus submit(std::uint64_t id,
                           std::string question,
                           LLMWorkerChunk on_chunk = {},
                           LLMWorkerDone on_done = {});

    // 停止接收新请求，排队任务取消。
    void requestStop() noexcept;

    // 需要先 requestStop，且不能从 Worker 线程内部调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;
    std::size_t peakCount() const {std::lock_guard<std::mutex> lock(mutex_);return measured_peak_;}

private:
    struct Task
    {
        std::uint64_t id = 0;
        std::string question;
        LLMWorkerChunk on_chunk;
        LLMWorkerDone on_done;
        std::chrono::steady_clock::time_point enqueued_at{};
    };

    void run();

    LLMEngine& engine_;
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;
    std::size_t rejected_ = 0;
    std::size_t measured_peak_ = 0;
};
