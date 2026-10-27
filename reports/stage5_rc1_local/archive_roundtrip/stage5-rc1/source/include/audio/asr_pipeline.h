
#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>
#include "common/request_trace.h"

class ASRService;

// 一个完整的待识别音频段。
struct AudioSegment {
    RequestTracePtr trace;
    std::uint64_t sequence = 0;

    // 操作 7 使用：S16_LE PCM。
    std::vector<std::int16_t> pcm;

    // 操作 8 使用：VAD 输出的 Float32。
    std::vector<float> samples;

    // 操作 10：阶段时间戳。
    // audio_end_estimated_at 为主机读取时钟推算的
    // VAD 音频段末尾时间，而非精确发声结束时间。
    bool timing_valid = false;

    std::chrono::steady_clock::time_point
        audio_end_estimated_at{};

    std::chrono::steady_clock::time_point
        vad_ready_at{};

    std::chrono::steady_clock::time_point
        enqueued_at{};
};

// 有界音频段队列。
struct AudioQueueStats {
    std::size_t pushed=0,popped=0,dropped=0,rejected_closed=0,pending=0,peak=0;
};
class AudioBufferQueue {
public:
    explicit AudioBufferQueue(std::size_t capacity);

    bool push(AudioSegment segment);
    bool pop(AudioSegment& segment);

    void close();

    std::size_t droppedCount() const;
    AudioQueueStats stats() const;

private:
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<AudioSegment> items_;

    bool closed_ = false;
    std::size_t dropped_ = 0;
    AudioQueueStats stats_;
};

// 操作 7 的音频生产者。
class AudioWorker {
public:
    AudioWorker(
        std::string device,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t segment_count
    );

    ~AudioWorker();

    AudioWorker(const AudioWorker&) = delete;
    AudioWorker& operator=(const AudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();

    // Read result state only after join().
    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();
    void runImpl();

    std::string device_;
    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t segment_count_;

    std::atomic<bool> stop_requested_{false};
    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};

// ASR 消费者。
// 支持操作 9 的可选识别文本回调。
class ASRWorker {
public:
    using TextCallback =
        std::function<void(const std::string&)>;
    using ContextCallback = std::function<void(const std::string&,const AudioSegment&)>;

    ASRWorker(
        AudioBufferQueue& queue,
        ASRService& asr,
        std::mutex& print_mutex,
        TextCallback on_text = {},
        ContextCallback on_context = {}
    );

    ~ASRWorker();

    ASRWorker(const ASRWorker&) = delete;
    ASRWorker& operator=(const ASRWorker&) = delete;

    // Start once; start/join/destruction must be serialized by the owner.
    void start();
    // Close input and drain queued segments. Does not cancel active inference.
    void requestStop();
    void join();

    // Read result state only after join().
    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t processedCount() const {
        return processed_;
    }

private:
    void run();
    void runImpl();

    AudioBufferQueue& queue_;
    ASRService& asr_;
    std::mutex& print_mutex_;

    TextCallback on_text_;
    ContextCallback on_context_;

    std::thread thread_;
    bool started_ = false; // Lifecycle operations belong to one owner thread.

    bool ok_ = false;
    std::string error_;
    std::size_t processed_ = 0;
};

