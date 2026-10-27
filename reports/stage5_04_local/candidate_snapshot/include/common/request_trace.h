#pragma once
#include "common/image_profile.h"
#include <memory>
#include <utility>

// One bounded-lifetime object travels through existing queue/task ownership.
// No central map retains completed requests. Raw timestamps use steady_clock.
class RequestTrace {
public:
    using Clock=std::chrono::steady_clock;
    explicit RequestTrace(std::uint64_t id):id_(id){}
    std::uint64_t id() const noexcept {return id_;}
    void mark(const char* event,Clock::time_point at=Clock::now(),double value=-1) const noexcept {
        ImageProfile::instance().request(id_,event,at,value);
    }
private:
    const std::uint64_t id_;
};
using RequestTracePtr=std::shared_ptr<RequestTrace>;
inline RequestTracePtr makeRequestTrace(std::uint64_t id) {
    return ImageProfile::instance().enabled()?std::make_shared<RequestTrace>(id):RequestTracePtr{};
}
inline RequestTracePtr& currentRequestTrace(){static thread_local RequestTracePtr trace;return trace;}
class RequestTraceScope {
public:
    explicit RequestTraceScope(RequestTracePtr trace):previous_(std::move(currentRequestTrace())),previous_id_(image_profile_request_id) {
        currentRequestTrace()=std::move(trace);image_profile_request_id=currentRequestTrace()?currentRequestTrace()->id():0;
    }
    ~RequestTraceScope(){currentRequestTrace()=std::move(previous_);image_profile_request_id=previous_id_;}
    RequestTraceScope(const RequestTraceScope&)=delete;
    RequestTraceScope& operator=(const RequestTraceScope&)=delete;
private:
    RequestTracePtr previous_;
    std::uint64_t previous_id_;
};
inline void traceMark(const char* event,RequestTrace::Clock::time_point at=RequestTrace::Clock::now(),double value=-1) noexcept {
    if(currentRequestTrace())currentRequestTrace()->mark(event,at,value);
}
