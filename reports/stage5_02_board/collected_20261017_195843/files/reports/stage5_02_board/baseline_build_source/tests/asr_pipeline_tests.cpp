#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"

#include <atomic>
#include <chrono>
#include <future>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

// Test-only service definitions. Never linked into multimodal_audio.
// This verifies production queue/worker control flow, not ASR inference.
namespace
{
enum class Fault { None, Standard, Unknown };
std::atomic<Fault> fault{Fault::None};
std::atomic<int> calls{0};

void check(bool okay, const char* message)
{
    if (!okay) throw std::runtime_error(message);
}

AudioSegment segment(std::uint64_t id)
{
    AudioSegment result;
    result.sequence = id;
    result.samples.assign(160, 0.0f);
    return result;
}

void testQueue()
{
    AudioBufferQueue queue(2);
    check(queue.push(segment(1)) && queue.push(segment(2)) &&
          queue.push(segment(3)), "queue push");
    check(queue.droppedCount() == 1, "drop-oldest count");
    queue.close();
    queue.close();
    check(!queue.push(segment(4)), "closed queue accepted input");
    AudioSegment output;
    check(queue.pop(output) && output.sequence == 2, "drop-oldest order");
    check(queue.pop(output) && output.sequence == 3, "queue drain order");
    check(!queue.pop(output), "closed queue did not reach EOF");

    AudioBufferQueue idle(1);
    auto waiter = std::async(std::launch::async, [&] {
        AudioSegment value;
        return idle.pop(value);
    });
    idle.close();
    check(waiter.wait_for(std::chrono::seconds(2)) == std::future_status::ready,
          "close did not wake consumer");
    check(!waiter.get(), "empty close returned a segment");
}

void testIdleDestructionAndUnwind()
{
    ASRService asr;
    std::mutex print_mutex;
    AudioBufferQueue queue(1);
    {
        ASRWorker worker(queue, asr, print_mutex);
        worker.start();
        // No producer ever starts or closes input. Destructor must wake pop().
    }
    check(!queue.push(segment(1)), "destructor did not close input");

    AudioBufferQueue unwind_queue(1);
    bool caught = false;
    try
    {
        ASRWorker worker(unwind_queue, asr, print_mutex);
        worker.start();
        throw std::runtime_error("test owner startup failure");
    }
    catch (const std::runtime_error&) { caught = true; }
    check(caught && !unwind_queue.push(segment(1)), "exception unwind cleanup");
}

void testDrainAndStartContract()
{
    ASRService asr;
    std::mutex print_mutex;
    AudioBufferQueue queue(3);
    std::vector<std::string> texts; // Outlives worker and its callback.
    calls = 0;
    fault = Fault::None;
    ASRWorker worker(queue, asr, print_mutex,
                     [&](const std::string& text) { texts.push_back(text); });
    check(queue.push(segment(1)), "float input");
    AudioSegment pcm;
    pcm.sequence = 2;
    pcm.pcm.assign(160, 0);
    check(queue.push(std::move(pcm)), "PCM input");
    worker.start();
    bool rejected = false;
    try { worker.start(); }
    catch (const std::logic_error&) { rejected = true; }
    check(rejected, "second start was not rejected");
    worker.requestStop(); // Close and drain; no silent cancellation.
    worker.join();
    worker.join();
    check(worker.ok() && worker.processedCount() == 2 && calls == 2 &&
          texts.size() == 2, "stop did not drain both input formats");
    rejected = false;
    try { worker.start(); }
    catch (const std::logic_error&) { rejected = true; }
    check(rejected, "restart after join was not rejected");
}

void testFailures()
{
    ASRService asr;
    std::mutex print_mutex;
    for (const auto value : {Fault::Standard, Fault::Unknown})
    {
        fault = value;
        AudioBufferQueue queue(1);
        ASRWorker worker(queue, asr, print_mutex);
        check(queue.push(segment(1)), "fault input");
        worker.start();
        worker.join(); // Failure itself must close input.
        check(!worker.ok() && !worker.error().empty() &&
              !queue.push(segment(2)), "inference exception escaped worker");
    }
    fault = Fault::None;
    for (const bool unknown : {false, true})
    {
        AudioBufferQueue queue(1);
        ASRWorker worker(queue, asr, print_mutex, [unknown](const std::string&) {
            if (unknown) throw 7;
            throw std::runtime_error("test callback failure");
        });
        check(queue.push(segment(1)), "callback input");
        worker.start();
        worker.join();
        check(!worker.ok() && worker.error().find("callback") != std::string::npos,
              "callback error lost");
    }
    AudioBufferQueue queue(1);
    ASRWorker worker(queue, asr, print_mutex);
    check(queue.push(AudioSegment{}), "empty input enqueue");
    worker.start();
    worker.join();
    check(!worker.ok() && !worker.error().empty(), "empty input accepted");
}
} // namespace

ASRService::~ASRService() = default;
bool ASRService::recognize(const std::vector<float>& samples, std::string& text,
                           double& latency_ms, std::string& error)
{
    ++calls;
    if (fault == Fault::Standard) throw std::runtime_error("test service failure");
    if (fault == Fault::Unknown) throw 42;
    check(samples.size() == 160, "worker changed sample count");
    text = "test-only transcript";
    latency_ms = 0.0; // Test data only; never reported as model performance.
    error.clear();
    return true;
}

int main()
{
    try
    {
        testQueue();
        testIdleDestructionAndUnwind();
        testDrainAndStartContract();
        testFailures();
        std::cout << "ASR pipeline tests passed: queue, idle destruction, unwind, "
                     "drain, one-shot start, service/callback faults. No SDK or hardware used.\n";
        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr << e.what() << '\n';
        return 1;
    }
}
