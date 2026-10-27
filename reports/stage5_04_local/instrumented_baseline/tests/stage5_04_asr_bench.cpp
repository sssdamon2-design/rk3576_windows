#include "audio/asr_service.h"
#include "common/request_trace.h"
#include <sherpa-onnx/c-api/c-api.h>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <memory>
#include <stdexcept>
#include <vector>
int main(int argc,char** argv) try {
    if(argc!=5)throw std::runtime_error("usage: asr_bench model_dir mono_16k_wave report_dir measured_repeats");
    const std::filesystem::path out(argv[3]);const int repeats=std::stoi(argv[4]);
    if(!std::filesystem::is_directory(out)||repeats<1||repeats>64)throw std::runtime_error("invalid report/repeats");
    std::unique_ptr<const SherpaOnnxWave,decltype(&SherpaOnnxFreeWave)> wave(SherpaOnnxReadWave(argv[2]),SherpaOnnxFreeWave);
    if(!wave||wave->sample_rate!=16000||wave->num_samples<=0)throw std::runtime_error("expected valid mono 16 kHz wave");
    std::vector<float> samples(wave->samples,wave->samples+wave->num_samples);wave.reset();
    ASRService service;std::string error;
    if(!service.initialize(std::string(argv[1])+"/model.int8.onnx",std::string(argv[1])+"/tokens.txt",error))throw std::runtime_error(error);
    std::ofstream csv(out/"asr_samples.csv");csv<<"iteration,phase,api_ms,wall_ms,audio_seconds,rtf,text\n"<<std::setprecision(12);
    std::string expected;
    for(int i=0;i<repeats+2;++i){
        auto trace=makeRequestTrace(i+1);RequestTraceScope scope(trace);std::string text;double latency=0;
        const auto start=RequestTrace::Clock::now();traceMark("asr_begin",start);
        if(!service.recognize(samples,text,latency,error))throw std::runtime_error(error);
        const auto end=RequestTrace::Clock::now();traceMark("asr_end",end);
        if(i==0)expected=text;else if(text!=expected)throw std::runtime_error("fixed input ASR answer changed");
        const double seconds=double(samples.size())/16000;
        csv<<i<<','<<(i==0?"first_use":i==1?"warmup":"measured")<<','<<latency<<','<<std::chrono::duration<double,std::milli>(end-start).count()<<','<<seconds<<','<<latency/(seconds*1000)<<','<<std::quoted(text)<<'\n'<<std::flush;
        std::cout<<"[ASRBench] sample="<<i<<" ms="<<latency<<" text="<<text<<'\n'<<std::flush;
    }
    service.shutdown();return 0;
}catch(const std::exception& e){std::cerr<<"[ASRBench ERROR] "<<e.what()<<'\n';return 1;}
