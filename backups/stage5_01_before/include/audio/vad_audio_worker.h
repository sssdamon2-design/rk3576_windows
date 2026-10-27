
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

    // 仅在 join() 之后读取以下状态。
    bool ok() const { return ok_; }
    const std::string& error() const { return error_; }
    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();

    std::string device_;
    std::string vad_model_;

    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t record_seconds_;

    std::atomic<bool> stop_requested_{false};
    std::thread thread_;

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};
