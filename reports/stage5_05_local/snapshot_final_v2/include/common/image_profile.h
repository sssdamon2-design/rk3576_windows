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
#include <string_view>

// Frame IDs and request IDs belong to different namespaces. SDK callbacks carry
// an explicit RequestTrace; ordinary synchronous stages inherit this scoped ID.
inline thread_local std::uint64_t image_profile_request_id=0;

// Optional diagnostic JSONL. Each duration ends before file I/O; no frame data held.
class ImageProfile {
public:
    using Clock=std::chrono::steady_clock;
    static double ms(Clock::time_point start,Clock::time_point end=Clock::now()) {
        return std::chrono::duration<double,std::milli>(end-start).count();
    }
    static ImageProfile& instance(){static ImageProfile profile;return profile;}
    bool enabled() const noexcept {return enabled_;}
    void sample(const char* stage,double duration,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) noexcept {
        if(!enabled_ || (!background_ && image_profile_request_id==0))return;
        try {
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"stage\":\""<<stage<<"\",\"ms\":"<<duration<<",\"id\":"<<id<<",\"request_id\":"<<image_profile_request_id<<",\"bytes\":"<<bytes<<",\"allocations\":"<<allocations<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] write failed\n";}
        } catch(...) {std::cerr<<"[ImageProfile ERROR] exception\n";}
    }
    void request(std::uint64_t id,const char* event,Clock::time_point at,double value=-1) noexcept {
        if(!enabled_)return;
        try {
            const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(at.time_since_epoch()).count();
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"kind\":\"request\",\"stage\":\"request_event\",\"ms\":0,\"id\":0,\"bytes\":0,\"allocations\":0,\"request_id\":"<<id<<",\"event\":\""<<event<<"\",\"at_ns\":"<<ns<<",\"value\":"<<value<<"}\n";
            output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] request write failed\n";}
        }catch(...){std::cerr<<"[ImageProfile ERROR] request exception\n";}
    }
    // Complete user-visible text shares the existing JSONL mutex and clock.
    // Console streaming from several threads is not a reliable GUI protocol.
    void text(std::uint64_t id,const char* event,std::string_view value) noexcept {
        if(!enabled_)return;
        try {
            const auto ns=std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now().time_since_epoch()).count();
            std::lock_guard<std::mutex> lock(mutex_);
            output_<<"{\"kind\":\"request\",\"stage\":\"request_event\",\"ms\":0,\"id\":0,\"request_id\":"<<id
                   <<",\"event\":\""<<event<<"\",\"at_ns\":"<<ns<<",\"value\":-1,\"text\":\"";
            constexpr char hex[]="0123456789abcdef";
            for(unsigned char c:value) {
                if(c=='"')output_<<"\\\"";
                else if(c=='\\')output_<<"\\\\";
                else if(c=='\n')output_<<"\\n";
                else if(c=='\r')output_<<"\\r";
                else if(c=='\t')output_<<"\\t";
                else if(c<0x20)output_<<"\\u00"<<hex[c>>4]<<hex[c&15];
                else output_.put(static_cast<char>(c));
            }
            output_<<"\"}\n";output_.flush();
            if(!output_ && !failed_){failed_=true;std::cerr<<"[ImageProfile ERROR] text write failed\n";}
        }catch(...){std::cerr<<"[ImageProfile ERROR] text exception\n";}
    }
private:
    ImageProfile(){
        const char* path=std::getenv("STAGE5_PROFILE");
        background_=path==nullptr; // Legacy image profiling retains all Camera samples.
        if(!path)path=std::getenv("STAGE5_IMAGE_PROFILE");
        if(path) {
            enabled_=true;output_.open(path,std::ios::out|std::ios::trunc);
            if(!output_){enabled_=false;failed_=true;std::cerr<<"[ImageProfile ERROR] cannot open log\n";}
        }
    }
    bool enabled_=false,failed_=false,background_=true;
    std::mutex mutex_;
    std::ofstream output_;
};
inline void imageSample(const char* stage,double ms,std::uint64_t id=0,std::size_t bytes=0,std::size_t allocations=0) {
    ImageProfile::instance().sample(stage,ms,id,bytes,allocations);
}
