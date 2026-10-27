
#pragma once

#include "audio/asr_pipeline.h"

#include <atomic>
#include <cstddef>
#include <mutex>
#include <string>
#include <thread>

class VadAudioWorker {
public:
    VadAudioWorker(
        std::string device,
        std::string vad_model,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t record_seconds
    );

    ~VadAudioWorker();

    VadAudioWorker(const VadAudioWorker&) = delete;
    VadAudioWorker& operator=(const VadAudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();
    // Completion publication lets the owner observe stop signals without blocking in join.
    bool isFinished() const noexcept { return finished_.load(std::memory_order_acquire); }

    // 仅在 join() 之后读取以下状态。
    bool ok() const { return ok_; }
    const std::string& error() const { return error_; }
    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();
    void runImpl();

    std::string device_;
    std::string vad_model_;

    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t record_seconds_;

    std::atomic<bool> stop_requested_{false};
    std::atomic<bool> finished_{false};
    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};
