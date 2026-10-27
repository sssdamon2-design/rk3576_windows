
#pragma once

#include "audio/alsa_playback_service.h"
#include "audio/tts_service.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

// 任务提交状态。
// 与现有 LLMSubmitStatus 保持一致。
enum class TTSSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

// 一次 TTS 合成和播放的执行结果。
struct TTSWorkerResult
{
    bool success = false;

    std::string error_message;

    // TTS 模型合成耗时。
    double synthesis_ms = 0.0;

    // ALSA 播放调用耗时，包含 drain。
    double playback_ms = 0.0;

    // 生成的音频时长。
    double audio_seconds = 0.0;

    std::int32_t sample_rate = 0;

    // 本次播放检测到的 XRUN 数量。
    std::uint64_t xrun_count = 0;
};

// 完成回调参数：
// request_id、结果、等待队列耗时（ms）。
// 取消的任务使用 queue_wait_ms=-1。
using TTSWorkerDone = std::function<void(
    std::uint64_t,
    const TTSWorkerResult&,
    double
)>;

// 单消费者 + 有界 FIFO。
// 不拥有 TTSService / AlsaPlaybackService。
//
// 必须先初始化两个 Service，再启动 Worker。
// 回调在 Worker 线程执行；回调中不得销毁
// 或 join 当前 Worker。
// start/join/destruction must be serialized by the owner thread.
// Callback captures must outlive the joined Worker, as must both Services.
class TTSWorker final
{
public:
    explicit TTSWorker(
        TTSService& tts,
        AlsaPlaybackService& playback,
        std::size_t capacity = 2
    );

    ~TTSWorker();

    TTSWorker(const TTSWorker&) = delete;
    TTSWorker& operator=(const TTSWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 非阻塞提交任务。
    TTSSubmitStatus submit(
        std::uint64_t id,
        std::string text,
        TTSWorkerDone on_done = {}
    );

    // 不再接收新任务。
    // 等待队列中的任务报告取消；
    // 正在执行的任务允许自然完成。
    void requestStop() noexcept;

    // 必须从非 Worker 线程调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;

private:
    struct Task
    {
        std::uint64_t id = 0;

        std::string text;

        TTSWorkerDone on_done;

        std::chrono::steady_clock::time_point
            enqueued_at{};
    };

    void run();

    // 外部对象引用，不负责销毁。
    TTSService& tts_;
    AlsaPlaybackService& playback_;

    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;

    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;

    std::size_t rejected_ = 0;
};
