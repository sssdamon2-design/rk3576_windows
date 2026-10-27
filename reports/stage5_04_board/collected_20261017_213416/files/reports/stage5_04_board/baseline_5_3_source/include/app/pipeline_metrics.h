#pragma once
#include "common/work_control.h"
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>

inline int pipelineEnv(const char* name,int fallback,int low,int high) {
    const char* value=std::getenv(name);if(!value)return fallback;
    std::size_t used=0;const std::string text(value);const int result=std::stoi(text,&used);
    if(used!=text.size() || result<low || result>high)throw std::invalid_argument(std::string("Invalid ")+name);
    return result;
}
struct DispatchTimer {
    std::mutex& mutex;
    std::uint64_t id;
    std::chrono::steady_clock::time_point start=std::chrono::steady_clock::now();
    ~DispatchTimer(){
        const auto ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
        std::lock_guard<std::mutex> lock(mutex);std::cout<<"[Dispatch] id="<<id<<" callback_ms="<<ms<<'\n'<<std::flush;
    }
};
inline void printWorkerStats(const char* stage,const WorkerStats& s) {
    std::cout<<"[QueueStats] stage="<<stage<<" generation="<<s.generation
             <<" accepted="<<s.accepted<<" completed="<<s.completed<<" started="<<s.started
             <<" failed="<<s.failed<<" cancelled="<<s.cancelled<<" expired="<<s.expired
             <<" rejected_full="<<s.rejected_full<<" rejected_stopped="<<s.rejected_stopped
             <<" peak="<<s.peak_depth<<" pending="<<s.pending<<" active="<<s.active
             <<" callback_errors="<<s.callback_errors<<" queue_sum_ms="<<s.queue_wait_sum_ms
             <<" queue_max_ms="<<s.queue_wait_max_ms<<" service_sum_ms="<<s.service_sum_ms<<'\n';
}
