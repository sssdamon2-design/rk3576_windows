#include "video/image_preprocessor.h"
#include "video/owned_frame_pool.h"
#include "video/latest_frame_buffer.h"
#include "video/camera_service.h"
#include "camera_test_capture.h"
#include <atomic>
#include <chrono>
#include <future>
#include <iostream>
#include <random>
#include <stdexcept>
#include <thread>
namespace {
void check(bool value,const char* message){if(!value)throw std::runtime_error(message);}
void imageTests() {
    Rgb512Preprocessor cached;std::mt19937 random(3576);std::vector<uint8_t> reference,actual;std::string error;
    for(auto dims:{std::pair<int,int>{2,2},{4,6},{32,18},{512,512},{1920,1080},{3840,2160}}) {
        for(int padding:{0,16}) {
            ImageFrame frame;frame.width=dims.first;frame.height=dims.second;frame.pixel_format=0x3231564e;
            const size_t stride=frame.width+padding;frame.plane_strides={static_cast<uint32_t>(stride)};
            frame.data.resize(stride*(frame.height+frame.height/2));frame.plane_sizes={frame.data.size()};
            for(auto& value:frame.data)value=static_cast<uint8_t>(random());
            check(frameToRgb512Reference(frame,reference,error) && cached.convert(frame,actual,error),"valid conversion failed");
            check(reference==actual,"cached differs from reference RGB bytes");
            const auto storage=actual.data();check(cached.convert(frame,actual,error) && actual.data()==storage,"RGB capacity not reused");
        }
    }
    ImageFrame red;red.width=red.height=2;red.pixel_format=0x3231564e;red.plane_strides={4};red.plane_sizes={12};
    red.data={81,81,0xee,0xee,81,81,0xee,0xee,90,240,0xee,0xee};
    check(cached.convert(red,actual,error),"padded color conversion");check(actual[0]>actual[2] && actual[0]>actual[1],"RGB/BGR channel order");
    ImageFrame vertical=red;vertical.data[0]=vertical.data[1]=16;vertical.data[4]=vertical.data[5]=235;vertical.data[8]=vertical.data[9]=128;
    check(cached.convert(vertical,actual,error),"vertical conversion");check(actual.front()==0 && actual[511*512*3]==255,"vertical orientation/limited range");
    for(int failure=0;failure<6;++failure) {
        auto bad=red;
        if(failure==0)bad.width=3;
        if(failure==1)bad.pixel_format=0;
        if(failure==2)bad.plane_strides={1};
        if(failure==3)bad.data.resize(2);
        if(failure==4)bad.plane_sizes={1};
        if(failure==5)bad.plane_sizes={10000};
        check(!cached.convert(bad,actual,error) && !error.empty(),"bad plane layout accepted");
    }
}
void poolTests() {
    OwnedFramePool pool;auto a=pool.acquire(),b=pool.acquire(),c=pool.acquire();
    check(a && b && c && !pool.acquire(),"pool is not bounded at three");
    a->data={42};b->data={17};const auto address=a.get();std::weak_ptr<ImageFrame> old=a;
    a.reset();auto next=pool.acquire();check(next && next.get()==address,"returned owned storage not reused");
    check(old.expired() && !old.lock(),"old weak generation revived into writable lease");
    next->data={99};check(b->data[0]==17,"held frame overwritten");next.reset();b.reset();c.reset();
    check(pool.stats().in_use==0 && pool.stats().allocated==3,"pool return leak");
    std::shared_ptr<ImageFrame> survivor;
    {OwnedFramePool temporary;survivor=temporary.acquire();survivor->data={88};}
    check(survivor->data[0]==88,"pool owner destruction invalidated external lease");survivor.reset();
}
void concurrentLifetime() {
    OwnedFramePool pool;LatestFrameBuffer latest;auto frame=pool.acquire();frame->data.assign(64,0x42);latest.update(std::move(frame));
    const auto held=latest.getLatest();std::atomic<bool> stop{false},valid{true};std::promise<void> entered;auto ready=entered.get_future();
    std::thread reader([&]{entered.set_value();while(!stop.load()){if(held->data.size()!=64||held->data[0]!=0x42)valid=false;}});
    struct Join {std::atomic<bool>& stop;std::thread& thread;~Join(){stop=true;if(thread.joinable())thread.join();}} join{stop,reader};
    check(ready.wait_for(std::chrono::seconds(2))==std::future_status::ready,"reader not ready");
    for(int i=0;i<500;++i){auto fresh=pool.acquire();check(bool(fresh),"three slots insufficient for held/latest/writer");fresh->data.assign(64,static_cast<uint8_t>(i));latest.update(std::move(fresh));}
    stop=true;reader.join();check(valid,"concurrent reader observed reused live storage");latest.clear();
}
void cameraExhaustion() {
    test_capture_mode=TestCaptureMode::Frames;LatestFrameBuffer latest;CameraService camera("fake",2,2,0,latest);check(camera.start(),"camera pool start");
    std::vector<LatestFrameBuffer::FramePtr> held;uint64_t previous=0;auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(held.size()!=3 && std::chrono::steady_clock::now()<deadline){auto frame=latest.getLatest();if(frame&&frame->frame_id!=previous){previous=frame->frame_id;held.push_back(frame);}std::this_thread::sleep_for(std::chrono::milliseconds(1));}
    check(held.size()==3,"could not hold three pool leases");deadline=std::chrono::steady_clock::now()+std::chrono::seconds(2);
    while(!camera.stats().pool_discarded && std::chrono::steady_clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(1));
    check(camera.stats().pool_discarded>0,"exhaustion not drained/counted");camera.stop();for(auto& frame:held)check(!frame->data.empty(),"stop destroyed held frame");
    held.clear();check(camera.start(),"restart after pool exhaustion");camera.stop();
}
}
int main() try {imageTests();poolTests();concurrentLifetime();cameraExhaustion();std::cout<<"PASS image pipeline: exact RGB, padded stride, channels/orientation, invalid layouts, bounded leases, weak generations, concurrent readers, exhaustion/restart. Fake camera only.\n";return 0;}
catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
