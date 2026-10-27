// Deterministic test process. Never loads SDKs or opens hardware.
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <csignal>
#include <pthread.h>
#include <cstdlib>
#include <fstream>
static volatile std::sig_atomic_t stopped=0;
static void stop(int) { stopped=1; }
int main() {
    sigset_t set;sigemptyset(&set);sigaddset(&set,SIGINT);sigaddset(&set,SIGTERM);
    std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
    pthread_sigmask(SIG_UNBLOCK,&set,nullptr);
    if(const char* path=std::getenv("STAGE5_PROFILE")) {
        std::ofstream events(path);
        events<<"{\"kind\":\"request\",\"request_id\":1,\"at_ns\":1,\"event\":\"asr_text\",\"text\":\"fake transcript\"}\n"
              <<"{\"kind\":\"request\",\"request_id\":1,\"at_ns\":2,\"event\":\"router_end\",\"value\":0}\n"
              <<"{\"kind\":\"request\",\"request_id\":1,\"at_ns\":3,\"event\":\"answer_text\",\"text\":\"fake answer\"}\n";
    }
    std::cout<<"[Init] Loading SenseVoice...\n[Init] Loading Kokoro...\n[ALSA config] fake\n[Init] VLM and Camera ready\n[Listen] FAKE UNIT TEST\n"
             <<"[ASR] Segment #1: fake transcript | latency=0 ms\n[ASR->LLM #1] fake\n[LLM #1] fake answer\n"<<std::flush;
    while(!stopped)std::this_thread::sleep_for(std::chrono::milliseconds(5));
    std::cout<<"[Shutdown] complete signal=2\n"<<std::flush;return 0;
}
