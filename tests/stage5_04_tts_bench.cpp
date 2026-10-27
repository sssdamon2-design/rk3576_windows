// Manual benchmark of the existing TTSService, including the frozen 5.3 library.
#include "audio/tts_service.h"
#include <sherpa-onnx/c-api/c-api.h>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <string>
#ifdef STAGE5_BENCH_TRACE
#include "common/request_trace.h"
#endif
using Clock=std::chrono::steady_clock;
static double ms(Clock::time_point a){return std::chrono::duration<double,std::milli>(Clock::now()-a).count();}
int main(int argc,char** argv) try {
    if(argc!=5)throw std::runtime_error("usage: tts_bench model_dir report_dir threads measured_repeats");
    const std::filesystem::path report(argv[2]);
    if(!std::filesystem::is_directory(report))throw std::runtime_error("report must already exist");
    const int threads=std::stoi(argv[3]),repeats=std::stoi(argv[4]);
    if(threads<1||threads>8||repeats<1||repeats>64)throw std::runtime_error("argument bounds");
    const std::string texts[]={u8"一加一等于二。","A computer monitor displaying a webpage with some text and images."};
    std::ofstream inputs(report/"inputs.txt");for(auto& text:texts)inputs<<text<<'\n';inputs.close();
    std::cout<<"[SDK] sherpa="<<SherpaOnnxGetVersionStr()<<" git="<<SherpaOnnxGetGitSha1()
             <<" ort="<<SherpaOnnxGetOnnxruntimeVersionStr()<<"\n"<<std::flush;
    TTSService tts;std::string error;const auto init=Clock::now();
    if(!tts.initialize(argv[1],error,threads,17))throw std::runtime_error(error);
    std::cout<<"[TTSInit] ms="<<ms(init)<<" threads="<<threads<<" sid=17 sample_rate="<<tts.sampleRate()<<"\n"<<std::flush;
    std::ofstream csv(report/"tts_samples.csv");
    csv<<"iteration,language,phase,threads,synthesis_ms,call_wall_ms,audio_seconds,rtf,samples,sample_rate,peak,rms,nonfinite,pcm_fnv64\n"<<std::setprecision(12);
    // Iteration 0 is first-use; iteration 1 warms both languages; the remaining N are measured.
    for(int i=0;i<repeats+2;++i)for(int language=0;language!=2;++language){
#ifdef STAGE5_BENCH_TRACE
        auto trace=makeRequestTrace(static_cast<std::uint64_t>(i*2+language+1));RequestTraceScope scope(trace);
        traceMark("tts_synthesis_begin");
#endif
        TTSAudio audio;auto start=Clock::now();
        if(!tts.synthesize(texts[language],audio,error))throw std::runtime_error(error);
#ifdef STAGE5_BENCH_TRACE
        traceMark("tts_api_return");
#endif
        const double wall=ms(start),seconds=double(audio.samples.size())/audio.sample_rate;
        if(audio.samples.empty()||audio.sample_rate!=24000)throw std::runtime_error("invalid PCM shape/rate");
        double peak=0,energy=0;std::size_t nonfinite=0;std::uint64_t hash=14695981039346656037ULL;
        for(float x:audio.samples){if(!std::isfinite(x)){++nonfinite;continue;}peak=std::max(peak,double(std::abs(x)));energy+=double(x)*x;
            unsigned char bytes[sizeof(float)];std::memcpy(bytes,&x,sizeof(x));for(auto c:bytes){hash^=c;hash*=1099511628211ULL;}}
        const char* phase=i==0?"first_use":i==1?"warmup":"measured";
        csv<<i<<','<<(language==0?"zh":"en")<<','<<phase<<','<<threads<<','<<audio.synthesis_ms<<','<<wall<<','<<seconds<<','<<audio.synthesis_ms/(seconds*1000)<<','<<audio.samples.size()<<','<<audio.sample_rate<<','<<peak<<','<<std::sqrt(energy/audio.samples.size())<<','<<nonfinite<<','<<hash<<'\n'<<std::flush;
        if(i==2){std::ofstream pcm(report/(language==0?"zh.f32":"en.f32"),std::ios::binary);pcm.write(reinterpret_cast<const char*>(audio.samples.data()),audio.samples.size()*sizeof(float));if(!pcm)throw std::runtime_error("PCM dump failed");}
        std::cout<<"[TTSBench] iteration="<<i<<" language="<<(language==0?"zh":"en")<<" phase="<<phase<<" synth_ms="<<audio.synthesis_ms<<" wall_ms="<<wall<<" audio_seconds="<<seconds<<" nonfinite="<<nonfinite<<"\n"<<std::flush;
        if(nonfinite)throw std::runtime_error("nonfinite waveform");
    }
    tts.shutdown();std::cout<<"[TTSBench] complete\n";return 0;
}catch(const std::exception& e){std::cerr<<"[TTSBench ERROR] "<<e.what()<<'\n';return 1;}
