#pragma once
#include <chrono>
#include <cstddef>
#include <stdexcept>
#include <cstdint>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>

// Optional diagnostic JSONL. Each duration ends before file I/O; no frame data held.
class ImageProfile {
public:
    using Clock=std::chrono::steady_clock;
    static double ms(Clock::time_point start,Clock::time_point end=Clock::now()) {
        return std::chrono::duration<double,std::milli>(end-start).count();
    }
    static ImageProfile& instance(){static ImageProfile profile;return profile;}
    void sample(const char* stage,double duration,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) noexcept {
        if(!enabled_)return;
        try {
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"stage\":\""<<stage<<"\",\"ms\":"<<duration<<",\"id\":"<<id<<",\"bytes\":"<<bytes<<",\"allocations\":"<<allocations<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] write failed\n";}
        } catch(...) {std::cerr<<"[ImageProfile ERROR] exception\n";}
    }
private:
    ImageProfile(){
        if(const char* path=std::getenv("STAGE5_IMAGE_PROFILE")) {
            enabled_=true;output_.open(path,std::ios::out|std::ios::trunc);
            if(!output_){enabled_=false;failed_=true;std::cerr<<"[ImageProfile ERROR] cannot open log\n";}
        }
    }
    bool enabled_=false,failed_=false;
    std::mutex mutex_;
    std::ofstream output_;
};
inline void imageSample(const char* stage,double ms,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) {
    ImageProfile::instance().sample(stage,ms,id,bytes,allocations);
}
