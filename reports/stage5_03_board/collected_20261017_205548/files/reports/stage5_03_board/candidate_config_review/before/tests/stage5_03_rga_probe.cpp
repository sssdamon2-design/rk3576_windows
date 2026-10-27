// Manual RGA comparison only: never selected by the production VLM backend.
#include "video/image_preprocessor.h"
#include "im2d.h"
#include "rknn_api.h"
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <linux/dma-heap.h>
#include <linux/dma-buf.h>
using Clock=std::chrono::steady_clock;
namespace fs=std::filesystem;
double ms(Clock::time_point t){return std::chrono::duration<double,std::milli>(Clock::now()-t).count();}
struct Imported {rga_buffer_handle_t handle=0;~Imported(){if(handle)releasebuffer_handle(handle);}};
struct DmaMemory {
    int fd=-1;void* data=MAP_FAILED;size_t bytes;
    explicit DmaMemory(size_t count):bytes(count) {
        int heap=open("/dev/dma_heap/system",O_RDWR|O_CLOEXEC);
        if(heap<0)throw std::runtime_error("open DMA heap failed");
        dma_heap_allocation_data request{};request.len=bytes;request.fd_flags=O_RDWR|O_CLOEXEC;
        const int result=ioctl(heap,DMA_HEAP_IOCTL_ALLOC,&request);close(heap);
        if(result<0)throw std::runtime_error("DMA heap allocation failed");
        fd=static_cast<int>(request.fd);data=mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_SHARED,fd,0);
        if(data==MAP_FAILED){close(fd);fd=-1;throw std::runtime_error("DMA mmap failed");}
    }
    void sync(uint64_t flags){dma_buf_sync request{};request.flags=flags;if(ioctl(fd,DMA_BUF_IOCTL_SYNC,&request))throw std::runtime_error("DMA cache sync failed");}
    ~DmaMemory(){if(data!=MAP_FAILED)munmap(data,bytes);if(fd>=0)close(fd);}
};
struct Vision {
    rknn_context context=0;
    ~Vision(){if(context)rknn_destroy(context);}
    std::vector<float> infer(const std::vector<uint8_t>& rgb) {
        rknn_input input{};input.type=RKNN_TENSOR_UINT8;input.fmt=RKNN_TENSOR_NHWC;input.size=rgb.size();input.buf=const_cast<uint8_t*>(rgb.data());
        if(rknn_inputs_set(context,1,&input) || rknn_run(context,nullptr))throw std::runtime_error("RKNN input/run failed");
        rknn_output output{};output.want_float=1;
        if(rknn_outputs_get(context,1,&output,nullptr))throw std::runtime_error("RKNN outputs failed");
        struct Guard {rknn_context context;rknn_output& output;~Guard(){rknn_outputs_release(context,1,&output);}} guard{context,output};
        if(!output.buf || output.size!=64*576*sizeof(float))throw std::runtime_error("Wrong vision embedding dimension");
        const auto* values=static_cast<float*>(output.buf);return std::vector<float>(values,values+64*576);
    }
};
void runRga(rga_buffer_t src,rga_buffer_t dst) {
    dst.color_space_mode=IM_YUV_TO_RGB_BT709_LIMIT;
    im_opt_t options{};options.interp=IM_INTERP(INTER_LINEAR,INTER_LINEAR);
    auto code=improcess(src,dst,{}, {0,0,src.width,src.height},{0,0,512,512},{},-1,nullptr,&options,IM_SYNC);
    if(code!=IM_STATUS_SUCCESS)throw std::runtime_error(std::string("RGA process: ")+imStrError_t(code));
}
void compare(const char* mode,int index,const std::vector<uint8_t>& cpu,const std::vector<uint8_t>& rgb,const std::vector<float>& expected,const std::vector<float>& actual) {
    uint64_t sum=0,changed=0;int maximum=0;
    for(size_t i=0;i<cpu.size();++i){const int difference=std::abs(int(cpu[i])-int(rgb[i]));sum+=difference;changed+=difference!=0;maximum=std::max(maximum,difference);}
    double dot=0,left=0,right=0,error=0;float largest=0;
    for(size_t i=0;i<expected.size();++i){if(!std::isfinite(actual[i]))throw std::runtime_error("nonfinite RGA embedding");dot+=double(expected[i])*actual[i];left+=double(expected[i])*expected[i];right+=double(actual[i])*actual[i];const float delta=std::abs(expected[i]-actual[i]);largest=std::max(largest,delta);error+=double(delta)*delta;}
    std::cout<<"RGA_QUALITY mode="<<mode<<" frame="<<index<<" rgb_changed="<<changed<<" rgb_mae="<<double(sum)/cpu.size()<<" rgb_max="<<maximum<<" embedding_cosine="<<dot/std::sqrt(left*right)<<" embedding_relative_l2="<<std::sqrt(error/left)<<" embedding_max="<<largest<<'\n';
}
int main(int argc,char** argv) try {
    if(argc!=4)throw std::runtime_error("usage: rga_probe fixed_frames_dir report_dir vision.rknn");
    fs::path fixtures(argv[1]),report(argv[2]);if(!fs::is_directory(report))throw std::runtime_error("report dir absent");
    std::cout<<"RGA_HEADER "<<RGA_API_FULL_VERSION<<"\nRGA_INFO "<<querystring(RGA_ALL)<<'\n';
    const auto header=imcheckHeader();std::cout<<"RGA_HEADER_CHECK status="<<header<<'\n';
    Vision vision;if(rknn_init(&vision.context,argv[3],0,0,nullptr))throw std::runtime_error("RKNN init failed");
    std::ofstream timing(report/"rga_samples.csv");timing<<"frame,mode,iteration,ms\n";
    for(int index=0;index<3;++index) {
        ImageFrame frame;frame.width=3840;frame.height=2160;frame.pixel_format=0x3231564e;frame.plane_strides={3840};frame.data.resize(12441600);frame.plane_sizes={frame.data.size()};
        std::ifstream raw(fixtures/("frame_"+std::to_string(index)+".nv12"),std::ios::binary);raw.read(reinterpret_cast<char*>(frame.data.data()),frame.data.size());if(!raw)throw std::runtime_error("fixture size/read failed");
        std::string error;std::vector<uint8_t> cpu,cached_rgb,rgb(512*512*3);Rgb512Preprocessor cached;
        if(!frameToRgb512Reference(frame,cpu,error)||!cached.convert(frame,cached_rgb,error)||cached_rgb!=cpu)throw std::runtime_error("cached RGB mismatch");
        for(int i=0;i<100;++i){auto t=Clock::now();frameToRgb512Reference(frame,cpu,error);timing<<index<<",cpu_reference_reused,"<<i<<','<<ms(t)<<'\n';t=Clock::now();cached.convert(frame,cached_rgb,error);timing<<index<<",cpu_cached,"<<i<<','<<ms(t)<<'\n';}
        auto imported_at=Clock::now();Imported src,dst;src.handle=importbuffer_virtualaddr(frame.data.data(),frame.data.size());dst.handle=importbuffer_virtualaddr(rgb.data(),rgb.size());
        std::cout<<"RGA_IMPORT mode=virtual frame="<<index<<" ms="<<ms(imported_at)<<'\n';if(!src.handle||!dst.handle)throw std::runtime_error("RGA virtual import failed");
        auto source=wrapbuffer_handle(src.handle,3840,2160,RK_FORMAT_YCbCr_420_SP,3840,2160);auto destination=wrapbuffer_handle(dst.handle,512,512,RK_FORMAT_RGB_888);
        runRga(source,destination);
        for(int i=0;i<100;++i){auto t=Clock::now();runRga(source,destination);timing<<index<<",rga_virtual_hot,"<<i<<','<<ms(t)<<'\n';}
        auto expected=vision.infer(cpu),actual=vision.infer(rgb);compare("virtual",index,cpu,rgb,expected,actual);
        std::ofstream(report/("rga_virtual_"+std::to_string(index)+".rgb"),std::ios::binary).write(reinterpret_cast<const char*>(rgb.data()),rgb.size());
        // DMA-BUF staging is an experiment, includes another CPU copy, not zero-copy.
        DmaMemory dma_source(frame.data.size()),dma_dest(rgb.size());dma_source.sync(DMA_BUF_SYNC_START|DMA_BUF_SYNC_WRITE);
        auto staging=Clock::now();std::memcpy(dma_source.data,frame.data.data(),frame.data.size());std::cout<<"DMA_STAGING_COPY frame="<<index<<" bytes="<<frame.data.size()<<" ms="<<ms(staging)<<'\n';
        dma_source.sync(DMA_BUF_SYNC_END|DMA_BUF_SYNC_WRITE);
        Imported dma_in,dma_out;dma_in.handle=importbuffer_fd(dma_source.fd,dma_source.bytes);dma_out.handle=importbuffer_fd(dma_dest.fd,dma_dest.bytes);
        if(!dma_in.handle||!dma_out.handle)throw std::runtime_error("RGA DMA import failed");
        source=wrapbuffer_handle(dma_in.handle,3840,2160,RK_FORMAT_YCbCr_420_SP,3840,2160);destination=wrapbuffer_handle(dma_out.handle,512,512,RK_FORMAT_RGB_888);
        runRga(source,destination);
        for(int i=0;i<100;++i){auto t=Clock::now();runRga(source,destination);timing<<index<<",rga_dmabuf_hot,"<<i<<','<<ms(t)<<'\n';}
        dma_dest.sync(DMA_BUF_SYNC_START|DMA_BUF_SYNC_READ);std::memcpy(rgb.data(),dma_dest.data,rgb.size());dma_dest.sync(DMA_BUF_SYNC_END|DMA_BUF_SYNC_READ);
        actual=vision.infer(rgb);compare("dmabuf",index,cpu,rgb,expected,actual);
    }
    std::cout<<"RGA_DIAGNOSTIC_COMPLETE production_path_unchanged=1\n";return 0;
} catch(const std::exception& e){std::cerr<<"RGA_DIAGNOSTIC_ERROR "<<e.what()<<'\n';return 1;}
