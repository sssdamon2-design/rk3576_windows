#include "common/request_trace.h"
#include "app/profiling_inputs.h"
#include <limits>
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <thread>
namespace {
void fixtureChecks(const std::filesystem::path& log){
    const auto folder=log.parent_path()/("profiling_fixtures_"+std::to_string(RequestTrace::Clock::now().time_since_epoch().count()));
    if(!std::filesystem::create_directory(folder))throw std::runtime_error("fixture directory collision");
    auto rejects=[](auto action){bool failed=false;try{action();}catch(const std::exception&){failed=true;}if(!failed)throw std::runtime_error("invalid fixture accepted");};
    const std::vector<float> pcm{0.0f,0.5f,-0.5f};dumpProfilingAudio(folder,1,pcm);
    if(loadProfilingAudio(folder/"segment_1.f32")!=pcm)throw std::runtime_error("PCM fixture changed");
    rejects([&]{dumpProfilingAudio(folder,1,pcm);});
    {const float invalid=std::numeric_limits<float>::quiet_NaN();std::ofstream out(folder/"invalid.f32",std::ios::binary);out.write(reinterpret_cast<const char*>(&invalid),sizeof(invalid));}
    rejects([&]{loadProfilingAudio(folder/"invalid.f32");});
    {std::ofstream out(folder/"frame_0.nv12",std::ios::binary);const char nv12[6]={0,1,2,3,4,5};out.write(nv12,6);}
    auto metadata=[&](int stride){std::ofstream out(folder/"frame_0.json");out<<"{\"width\":2,\"height\":2,\"stride\":"<<stride<<",\"bytes\":6,\"frame_id\":7}";};
    metadata(2);auto frame=loadProfilingFrame(folder);
    if(frame->data.size()!=6||frame->width!=2||frame->data[5]!=5||frame->received_at!=std::chrono::steady_clock::time_point{})throw std::runtime_error("fixed frame ownership/timestamp");
    metadata(1);rejects([&]{loadProfilingFrame(folder);});
    for(const auto& file:std::filesystem::directory_iterator(folder))std::filesystem::remove(file.path());std::filesystem::remove(folder);
}
}
int main(int argc,char** argv) try {
    if(argc!=2)throw std::runtime_error("profile log path required");
#ifdef _WIN32
    _putenv_s("STAGE5_PROFILE",argv[1]);
#else
    setenv("STAGE5_PROFILE",argv[1],1);
#endif
    fixtureChecks(argv[1]);
    auto trace=makeRequestTrace(42);if(!trace)throw std::runtime_error("profile did not enable");
    const auto before=RequestTrace::Clock::now();trace->mark("begin",before);
    {RequestTraceScope scope(trace);traceMark("scoped");imageSample("test_stage",1.25,999,8,1);
     std::thread callback([trace]{trace->mark("sdk_callback");});callback.join();}
    if(currentRequestTrace() || image_profile_request_id)throw std::runtime_error("TLS leaked");
    trace->mark("end");std::ifstream input(argv[1]);std::stringstream data;data<<input.rdbuf();const auto text=data.str();
    for(const char* expected:{"\"request_id\":42","\"event\":\"begin\"","\"event\":\"scoped\"","\"event\":\"sdk_callback\"","\"event\":\"end\"","\"stage\":\"test_stage\"","\"id\":999","\"at_ns\":"})
        if(text.find(expected)==std::string::npos)throw std::runtime_error(expected);
    std::size_t count=0;for(char c:text)count+=c=='\n';if(count!=5)throw std::runtime_error("unexpected event count");
    std::cout<<"PASS request profiling: scoped request ID, distinct frame ID, explicit SDK callback, steady timestamps, flushed JSONL\n";return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}
