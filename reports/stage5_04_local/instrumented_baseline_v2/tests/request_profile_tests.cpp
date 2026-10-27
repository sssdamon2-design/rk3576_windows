#include "common/request_trace.h"
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <thread>
int main(int argc,char** argv) try {
    if(argc!=2)throw std::runtime_error("profile log path required");
#ifdef _WIN32
    _putenv_s("STAGE5_PROFILE",argv[1]);
#else
    setenv("STAGE5_PROFILE",argv[1],1);
#endif
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
