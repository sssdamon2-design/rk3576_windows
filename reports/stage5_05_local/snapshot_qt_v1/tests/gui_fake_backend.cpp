// Deterministic test process. Never loads SDKs or opens hardware.
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <csignal>
#include <pthread.h>
static volatile std::sig_atomic_t stopped=0;
static void stop(int) { stopped=1; }
int main() {
    sigset_t set;sigemptyset(&set);sigaddset(&set,SIGINT);sigaddset(&set,SIGTERM);
    std::signal(SIGINT,stop);std::signal(SIGTERM,stop);
    pthread_sigmask(SIG_UNBLOCK,&set,nullptr);
    std::cout<<"[Init] Loading SenseVoice...\n[Init] Loading Kokoro...\n[ALSA config] fake\n[Init] VLM and Camera ready\n[Listen] FAKE UNIT TEST\n"
             <<"[ASR] Segment #1: fake transcript | latency=0 ms\n[ASR->LLM #1] fake\n[LLM #1] fake answer\n"<<std::flush;
    while(!stopped)std::this_thread::sleep_for(std::chrono::milliseconds(5));
    std::cout<<"[Shutdown] complete signal=2\n"<<std::flush;return 0;
}
