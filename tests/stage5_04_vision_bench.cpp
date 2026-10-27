#include "ai/rk_backends.h"
#include "ai/vlm_engine.h"
#include "common/request_trace.h"
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <regex>
#include <sstream>
#include <stdexcept>
namespace fs=std::filesystem;
static std::shared_ptr<ImageFrame> loadFrame(const fs::path& folder,int index){
    const auto name="frame_"+std::to_string(index);std::ifstream meta(folder/(name+".json"));std::stringstream contents;contents<<meta.rdbuf();const auto text=contents.str();
    auto field=[&](const char* key){std::smatch m;if(!std::regex_search(text,m,std::regex(std::string("\"")+key+"\":([0-9]+)")))throw std::runtime_error(std::string("missing ")+key);return std::stoull(m[1]);};
    auto frame=std::make_shared<ImageFrame>();frame->width=field("width");frame->height=field("height");frame->pixel_format=0x3231564e;
    frame->plane_strides={static_cast<std::uint32_t>(field("stride"))};frame->plane_sizes={static_cast<std::size_t>(field("bytes"))};frame->frame_id=field("frame_id");frame->data.resize(field("bytes"));
    std::ifstream input(folder/(name+".nv12"),std::ios::binary);input.read(reinterpret_cast<char*>(frame->data.data()),frame->data.size());if(!input)throw std::runtime_error("fixture read failed");
    return frame;
}
static std::string csvText(const std::string& value){std::string out="\"";for(char c:value){if(c=='"')out+='"';out+=c;}return out+'"';}
int main(int argc,char** argv)try{
    if(argc!=6)throw std::runtime_error("usage: vision_bench language.rkllm vision.rknn fixture_dir report_dir measured_repeats");
    const fs::path report(argv[4]);const int repeats=std::stoi(argv[5]);if(!fs::is_directory(report)||repeats<1||repeats>64)throw std::runtime_error("invalid report/repeats");
    std::shared_ptr<ImageFrame> frames[3];for(int i=0;i<3;++i)frames[i]=loadFrame(argv[3],i);
    VLMEngine engine(std::make_unique<RK3576VLMBackend>());std::string error;
    if(!engine.initialize(BackendConfig{argv[1],argv[2]},error))throw std::runtime_error(error);
    std::ofstream csv(report/"vision_samples.csv");csv<<"iteration,phase,fixture,frame_id,latency_ms,decoder_first_text_ms,success,answer\n"<<std::setprecision(12);
    for(int i=0;i<repeats+2;++i){
        auto trace=makeRequestTrace(i+1);RequestTraceScope scope(trace);traceMark("inference_begin");
        const auto result=engine.infer(frames[i%3],"What do you see? Answer briefly.");
        traceMark(result.success?"inference_end":"inference_failed");
        csv<<i<<','<<(i==0?"first_use":i==1?"warmup":"measured")<<','<<i%3<<','<<result.frame_id<<','<<result.latency_ms<<','<<result.first_text_ms<<','<<result.success<<','<<csvText(result.text)<<'\n'<<std::flush;
        std::cout<<"[VisionBench] sample="<<i<<" fixture="<<i%3<<" success="<<result.success<<" ms="<<result.latency_ms<<" answer="<<result.text<<'\n'<<std::flush;
        if(!result.success)throw std::runtime_error(result.error_message);
    }
    engine.shutdown();return 0;
}catch(const std::exception& e){std::cerr<<"[VisionBench ERROR] "<<e.what()<<'\n';return 1;}
