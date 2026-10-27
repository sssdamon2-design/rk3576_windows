#include "ai/rk_backends.h"
#include "ai/llm_engine.h"
#include "ai/vlm_engine.h"
#include "video/camera_service.h"
#include <algorithm>
#include <chrono>
#include <condition_variable>
#include <iostream>
#include <memory>
#include <mutex>
#include <thread>

// Real SDK diagnostic, never a mock benchmark or an NPU utilization measurement.
int main(int argc, char** argv) try
{
    if (argc != 5) return 2;
    using Clock=std::chrono::steady_clock;
    const auto origin=Clock::now();
    auto ms=[&](Clock::time_point t) { return std::chrono::duration<double,std::milli>(t-origin).count(); };
    LLMEngine llm(std::make_unique<RKLLMBackend>());
    VLMEngine vlm(std::make_unique<RK3576VLMBackend>());
    std::string error;
    if (!llm.initialize(BackendConfig{argv[1],{}},error)) { std::cerr<<error<<'\n';return 1; }
    LatestFrameBuffer frames;
    constexpr std::uint32_t nv12=std::uint32_t('N')|(std::uint32_t('V')<<8)|(std::uint32_t('1')<<16)|(std::uint32_t('2')<<24);
    CameraService camera(argv[4],3840,2160,nv12,frames);
    if (!camera.start()) { std::cerr<<camera.stats().last_error<<'\n';return 1; }
    if (!vlm.initialize(BackendConfig{argv[2],argv[3]},error)) { std::cerr<<error<<'\n';return 1; }
    const auto deadline=Clock::now()+std::chrono::seconds(3);
    while (!frames.getLatest() && Clock::now()<deadline) std::this_thread::sleep_for(std::chrono::milliseconds(10));
    if (!frames.getLatest()) return 1;
    unsigned int successful=0;
    for (bool parallel : {false,true})
    {
        for (int round=0;round<3;++round)
        {
            InferenceResult text,vision;
            double tb=0,te=0,vb=0,ve=0;
            auto run_text=[&] {
                tb=ms(Clock::now());
                text=llm.infer("What is one plus one? Answer in one short sentence.");
                te=ms(Clock::now());
            };
            std::cout<<"PROBE_BEGIN parallel="<<parallel<<" round="<<round<<'\n'<<std::flush;
            if (parallel)
            {
                std::mutex mutex;
                std::condition_variable cv;
                bool go=false;
                struct Joined { std::thread thread; ~Joined(){if(thread.joinable())thread.join();} } joined;
                joined.thread=std::thread([&] {
                    {std::unique_lock<std::mutex> lock(mutex);cv.wait(lock,[&]{return go;});}
                    run_text();
                });
                {std::lock_guard<std::mutex> lock(mutex);go=true;}
                cv.notify_one();
                vb=ms(Clock::now());
                vision=vlm.infer(frames.getLatest(),"What do you see? Answer briefly.");
                ve=ms(Clock::now());
                joined.thread.join();
            }
            else
            {
                run_text();
                vb=ms(Clock::now());
                vision=vlm.infer(frames.getLatest(),"What do you see? Answer briefly.");
                ve=ms(Clock::now());
            }
            const double overlap=std::max(0.0,std::min(te,ve)-std::max(tb,vb));
            std::cout<<"PROBE_RESULT parallel="<<parallel<<" round="<<round
                     <<" text_ok="<<text.success<<" vision_ok="<<vision.success
                     <<" text_ms="<<te-tb<<" vision_ms="<<ve-vb
                     <<" sdk_call_overlap_ms="<<overlap
                     <<" pair_ms="<<std::max(te,ve)-std::min(tb,vb)<<'\n'<<std::flush;
            if (!text.success) std::cerr<<"TEXT_ERROR "<<text.error_message<<'\n';
            if (!vision.success) std::cerr<<"VISION_ERROR "<<vision.error_message<<'\n';
            successful+=text.success && vision.success;
        }
    }
    camera.stop();vlm.shutdown();llm.shutdown();
    std::cout<<"PROBE_SUMMARY pairs="<<successful<<"/6\n";
    return successful==6?0:1;
}
catch(const std::exception& e){std::cerr<<"PROBE_FATAL "<<e.what()<<'\n';return 1;}
