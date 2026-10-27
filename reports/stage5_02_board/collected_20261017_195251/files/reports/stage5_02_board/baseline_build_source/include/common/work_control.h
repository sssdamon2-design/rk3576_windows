#pragma once
#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <memory>

enum class StopMode { Drain, CancelPending };
enum class TaskDisposition { Completed, Cancelled, Expired };
inline const char* dispositionName(TaskDisposition value) noexcept {
    return value==TaskDisposition::Cancelled?"cancelled":value==TaskDisposition::Expired?"expired":"completed";
}
struct TaskOptions {
    using Clock=std::chrono::steady_clock;
    Clock::time_point deadline=Clock::time_point::max();
    std::chrono::milliseconds max_queue_wait=std::chrono::milliseconds::max();
    std::shared_ptr<std::atomic<bool>> cancelled;
    TaskDisposition disposition(Clock::time_point enqueued, Clock::time_point now, bool stopping) const noexcept {
        if (stopping || (cancelled && cancelled->load())) return TaskDisposition::Cancelled;
        if (now>=deadline || (max_queue_wait!=std::chrono::milliseconds::max() && now-enqueued>=max_queue_wait))
            return TaskDisposition::Expired;
        return TaskDisposition::Completed;
    }
};
struct WorkerStats {
    std::uint64_t generation=0;
    std::size_t accepted=0,rejected_full=0,rejected_stopped=0,started=0,completed=0;
    std::size_t failed=0,cancelled=0,expired=0,callback_errors=0,peak_depth=0,pending=0,active=0;
    double queue_wait_sum_ms=0,queue_wait_max_ms=0,service_sum_ms=0;
};
