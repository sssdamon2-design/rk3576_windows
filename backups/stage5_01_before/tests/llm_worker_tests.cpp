#include "ai/llm_worker.h"

#include <chrono>
#include <condition_variable>
#include <future>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

using namespace std::chrono_literals;

namespace
{

void check(bool condition, const char* message)
{
    if (!condition)
        throw std::runtime_error(message);
}

class GatedLLM final : public ILLMBackend
{
public:
    std::promise<void> entered;
    std::promise<void> release;
    std::shared_future<void> gate =
        release.get_future().share();

    int calls = 0;

    bool initialize(
        const BackendConfig&,
        std::string& error) override
    {
        error.clear();
        return true;
    }

    InferenceResult infer(
        const std::string& question) override
    {
        return inferStreaming(question, {});
    }

    InferenceResult inferStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk) override
    {
        ++calls;

        if (calls == 1)
        {
            entered.set_value();
            gate.wait();
        }

        if (on_chunk)
        {
            on_chunk("part:");
            on_chunk(question);
        }

        InferenceResult result;
        result.success = true;
        result.text = "part:" + question;
        return result;
    }

    void shutdown() noexcept override {}
};

void testQueueFullAndFifo()
{
    auto backend = std::make_unique<GatedLLM>();
    auto* gate = backend.get();
    auto first_entered = gate->entered.get_future();

    LLMEngine engine(std::move(backend));
    std::string error;
    check(engine.initialize({}, error), "mock LLM init");

    LLMWorker worker(engine, 2);

    check(
        worker.submit(0, "not started")
            == LLMSubmitStatus::NotRunning,
        "submit before start");

    check(worker.start(error), "worker start");

    std::mutex done_mutex;
    std::condition_variable done_cv;
    std::vector<std::uint64_t> completed;
    std::vector<std::string> chunks;
    bool all_success = true;

    const auto on_chunk =
        [&](std::uint64_t id, const std::string& text)
    {
        std::lock_guard<std::mutex> lock(done_mutex);
        chunks.push_back(std::to_string(id) + ":" + text);
    };

    const auto on_done =
        [&](std::uint64_t id,
            const InferenceResult& result,
            double wait_ms)
    {
        {
            std::lock_guard<std::mutex> lock(done_mutex);
            completed.push_back(id);

            if (!result.success || wait_ms < 0.0)
                all_success = false;
        }

        done_cv.notify_all();
    };

    check(
        worker.submit(1, "A", on_chunk, on_done)
            == LLMSubmitStatus::Accepted,
        "submit first");

    const bool entered =
        first_entered.wait_for(2s)
        == std::future_status::ready;

    const bool accept2 =
        worker.submit(2, "B", on_chunk, on_done)
        == LLMSubmitStatus::Accepted;

    const bool accept3 =
        worker.submit(3, "C", on_chunk, on_done)
        == LLMSubmitStatus::Accepted;

    const bool full =
        worker.submit(4, "D", on_chunk, on_done)
        == LLMSubmitStatus::QueueFull;

    const bool pending2 = worker.pendingCount() == 2;
    const bool rejected1 = worker.rejectedCount() == 1;

    // 即使检查失败，也先释放阻塞的 mock，避免 join 卡死。
    gate->release.set_value();

    bool finished = false;

    {
        std::unique_lock<std::mutex> lock(done_mutex);

        finished = done_cv.wait_for(
            lock,
            3s,
            [&] { return completed.size() == 3; });
    }

    worker.requestStop();
    worker.join();

    check(entered, "worker did not start first inference");

    check(
        accept2 && accept3 && full && pending2 && rejected1,
        "bounded queue behaviour");

    check(finished && all_success, "worker completion");

    check(
        completed == std::vector<std::uint64_t>({1, 2, 3}),
        "FIFO order");

    check(chunks.size() == 6, "stream chunks not propagated");

    check(
        worker.submit(5, "E")
            == LLMSubmitStatus::NotRunning,
        "submit after stop");
}

void testStopCancelsPending()
{
    auto backend = std::make_unique<GatedLLM>();
    auto* gate = backend.get();
    auto first_entered = gate->entered.get_future();

    LLMEngine engine(std::move(backend));
    std::string error;
    check(engine.initialize({}, error), "mock LLM init");

    LLMWorker worker(engine, 2);
    check(worker.start(error), "worker start");

    std::mutex mutex;
    std::vector<std::uint64_t> ids;
    std::vector<bool> success;
    std::vector<std::string> errors;

    const auto on_done =
        [&](std::uint64_t id,
            const InferenceResult& result,
            double)
    {
        std::lock_guard<std::mutex> lock(mutex);
        ids.push_back(id);
        success.push_back(result.success);
        errors.push_back(result.error_message);
    };

    check(
        worker.submit(11, "active", {}, on_done)
            == LLMSubmitStatus::Accepted,
        "active submit");

    const bool entered =
        first_entered.wait_for(2s)
        == std::future_status::ready;

    const bool second_accepted =
        worker.submit(12, "queued", {}, on_done)
        == LLMSubmitStatus::Accepted;

    worker.requestStop();

    const bool rejected =
        worker.submit(13, "after stop")
        == LLMSubmitStatus::NotRunning;

    gate->release.set_value();
    worker.join();

    check(
        entered && second_accepted && rejected,
        "stop setup");

    check(
        ids == std::vector<std::uint64_t>({11, 12}),
        "stop completion order");

    check(
        success.size() == 2 && success[0] && !success[1],
        "active vs queued cancellation");

    check(
        errors[1].find("cancelled") != std::string::npos,
        "cancel diagnostic");
}

}  // namespace

int main()
{
    try
    {
        testQueueFullAndFifo();
        testStopCancelsPending();

        std::cout
            << "LLMWorker tests passed: "
            << "FIFO, bounded queue, streaming, stop.\n";

        return 0;
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "LLMWorker tests FAILED: "
            << e.what() << '\n';

        return 1;
    }
}
