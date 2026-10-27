// Manual Stage 5.3 diagnostic, reuses production CameraService/VLMEngine.
#include "video/camera_service.h"
#include "ai/vlm_engine.h"
#include "ai/rk_backends.h"
#include "common/timing.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <thread>
#include <filesystem>
#include <iomanip>
#include <stdexcept>
#include <regex>
#include <sstream>
namespace fs=std::filesystem;
using Clock=std::chrono::steady_clock;
int main(int argc,char** argv) try {
    if(argc!=6)throw std::runtime_error("usage: probe vlm.rkllm vision.rknn /dev/video11 report_dir samples");
    const fs::path report(argv[4]);if(!fs::is_directory(report))throw std::runtime_error("report directory must exist");
    const int samples=std::stoi(argv[5]);if(samples<1||samples>64)throw std::runtime_error("samples must be 1..64");
    LatestFrameBuffer latest;CameraService camera(argv[3],3840,2160,0x3231564e,latest);
    const bool fixed=std::string(argv[3])=="fixed";
    if(!fixed && !camera.start())throw std::runtime_error(camera.stats().last_error);
    VLMEngine engine(std::make_unique<RK3576VLMBackend>());BackendConfig config;
    config.model_path=argv[1];config.vision_model_path=argv[2];std::string error;
    if(!engine.initialize(config,error))throw std::runtime_error(error);
    std::ofstream metrics(report/"requests.csv");metrics<<"sample,frame_id,bytes,width,height,stride,frame_age_ms,get_latest_wall_ms,vlm_ms,success\n";
    for(int i=0;i<samples;++i) {
        auto read=Clock::now();auto frame=latest.getLatest();
        if(fixed) {
            const auto fixture=fs::path(std::getenv("STAGE5_FIXED_FRAMES"));
            const std::string name="frame_"+std::to_string(i%3);
            std::ifstream meta(fixture/(name+".json"));std::stringstream content;content<<meta.rdbuf();
            const auto field=[&](const char* key){std::smatch m;const std::string text=content.str();if(!std::regex_search(text,m,std::regex(std::string("\"")+key+"\":([0-9]+)")))throw std::runtime_error("missing fixture field");return std::stoull(m[1]);};
            auto loaded=std::make_shared<ImageFrame>();loaded->width=field("width");loaded->height=field("height");loaded->pixel_format=0x3231564e;
            loaded->plane_strides={static_cast<uint32_t>(field("stride"))};loaded->plane_sizes={static_cast<std::size_t>(field("bytes"))};loaded->frame_id=field("frame_id");loaded->data.resize(field("bytes"));
            std::ifstream raw(fixture/(name+".nv12"),std::ios::binary);raw.read(reinterpret_cast<char*>(loaded->data.data()),loaded->data.size());if(!raw)throw std::runtime_error("fixture read failed");
            loaded->received_at=Clock::now();frame=std::move(loaded);
        }
        const double got=elapsedMilliseconds(read);
        if(!frame)throw std::runtime_error("no frame");
        if(!fixed && i<3) {
            std::ofstream raw(report/("frame_"+std::to_string(i)+".nv12"),std::ios::binary);raw.write(reinterpret_cast<const char*>(frame->data.data()),frame->data.size());
            std::ofstream meta(report/("frame_"+std::to_string(i)+".json"));meta<<"{\"width\":"<<frame->width<<",\"height\":"<<frame->height<<",\"stride\":"<<frame->plane_strides.at(0)<<",\"bytes\":"<<frame->data.size()<<",\"frame_id\":"<<frame->frame_id<<"}\n";
        }
        auto result=engine.infer(frame,"What do you see? Answer briefly.");
        metrics<<i<<','<<frame->frame_id<<','<<frame->data.size()<<','<<frame->width<<','<<frame->height<<','<<frame->plane_strides.at(0)<<','<<result.frame_age_ms<<','<<got<<','<<result.latency_ms<<','<<result.success<<'\n'<<std::flush;
        std::cout<<"[MemoryProbe] sample="<<i<<" success="<<result.success<<" frame="<<frame->frame_id<<" vlm_ms="<<result.latency_ms<<" answer="<<result.text<<" error="<<result.error_message<<'\n'<<std::flush;
        if(!result.success)throw std::runtime_error(result.error_message);
    }
    const auto stats=camera.stats();camera.stop();engine.shutdown();
    std::ofstream out(report/"camera.json");out<<"{\"frames\":"<<stats.frame_count<<",\"fps\":"<<stats.approximate_fps<<",\"timeouts\":"<<stats.timeout_count<<",\"last_error\":"<<std::quoted(stats.last_error)<<"}\n";
    std::cout<<"[MemoryProbe] stopped fps="<<stats.approximate_fps<<" frames="<<stats.frame_count<<" timeouts="<<stats.timeout_count<<"\n";return 0;
} catch(const std::exception& e){std::cerr<<"[MemoryProbe ERROR] "<<e.what()<<'\n';return 1;}
