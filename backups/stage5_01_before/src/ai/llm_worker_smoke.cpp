
#include "ai/llm_worker.h"
#include "ai/rk_backends.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>

// 独立的 RKLLM + LLMWorker 实机验收入口。
int main(int argc, char** argv)
{
    if (argc != 2)
    {
        std::cerr
            << "Usage: rkllm_worker_smoke "
            << "/absolute/path/to/model.rkllm\n";
        return 2;
    }

    BackendConfig config;
    config.model_path = argv[1];

    std::string error;

    LLMEngine llm(std::make_unique<RKLLMBackend>());

    if (!llm.initialize(config, error))
    {
        std::cerr
            << "LLM initialization failed: "
            << error << '\n';
        return 1;
    }

    // Worker 不拥有 LLMEngine。
    // 必须先等待 Worker 结束，再关闭 LLMEngine。
    LLMWorker worker(llm, 2);

    if (!worker.start(error))
    {
        std::cerr
            << "LLMWorker start failed: "
            << error << '\n';
        llm.shutdown();
        return 1;
    }

    std::mutex state_mutex;
    std::condition_variable done_cv;
    std::mutex print_mutex;

    bool done = false;
    bool printed_prefix = false;

    std::size_t chunk_count = 0;

    InferenceResult final_result;
    double queue_wait_ms = -1.0;

    const std::uint64_t request_id = 1;

    const std::string question =
        "请用两句话解释Linux中互斥锁的作用。";

    const auto before_submit =
        std::chrono::steady_clock::now();

    // 提交异步请求。
    const auto status = worker.submit(
        request_id,
        question,

        // 流式文本回调：由 Worker 推理过程触发。
        [&](std::uint64_t id, const std::string& chunk)
        {
            if (id != request_id || chunk.empty())
                return;

            {
                std::lock_guard<std::mutex> lock(print_mutex);

                if (!printed_prefix)
                {
                    std::cout << "\n[Worker stream] ";
                    printed_prefix = true;
                }

                std::cout << chunk << std::flush;
            }

            {
                std::lock_guard<std::mutex> lock(state_mutex);
                ++chunk_count;
            }
        },

        // 推理完成回调。
        [&](std::uint64_t id,
            const InferenceResult& result,
            double wait_ms)
        {
            if (id != request_id)
                return;

            {
                std::lock_guard<std::mutex> lock(state_mutex);

                final_result = result;
                queue_wait_ms = wait_ms;
                done = true;
            }

            done_cv.notify_one();
        }
    );

    // 测量 submit() 调用本身的耗时。
    const double submit_ms =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() - before_submit
        ).count();

    if (status != LLMSubmitStatus::Accepted)
    {
        std::cerr << "LLMWorker rejected the request\n";

        worker.requestStop();
        worker.join();
        llm.shutdown();

        return 1;
    }

    {
        std::lock_guard<std::mutex> lock(print_mutex);

        std::cout
            << std::fixed
            << std::setprecision(2)
            << "[Main] submit returned in "
            << submit_ms
            << " ms (NPU inference is running in worker thread)\n";
    }

    // 主线程每隔两秒继续执行自己的任务。
    std::size_t heartbeats = 0;

    for (;;)
    {
        std::unique_lock<std::mutex> lock(state_mutex);

        if (done_cv.wait_for(
                lock,
                std::chrono::seconds(2),
                [&] { return done; }))
        {
            break;
        }

        lock.unlock();

        ++heartbeats;

        std::lock_guard<std::mutex> print_lock(print_mutex);

        std::cout
            << "\n[Main] heartbeat #"
            << heartbeats
            << ": main thread is responsive\n"
            << std::flush;
    }

    // 正确的停止和资源释放顺序。
    worker.requestStop();
    worker.join();

    llm.shutdown();

    std::lock_guard<std::mutex> lock(print_mutex);

    std::cout
        << "\n[Main] completed: success="
        << std::boolalpha
        << final_result.success
        << ", stream_chunks="
        << chunk_count
        << ", queue_wait_ms="
        << queue_wait_ms
        << ", first_text_ms="
        << final_result.first_text_ms
        << ", request_latency_ms="
        << final_result.latency_ms
        << '\n';

    if (!final_result.success)
    {
        std::cerr
            << "[Main] inference error: "
            << final_result.error_message
            << '\n';
    }

    return final_result.success && chunk_count > 0 ? 0 : 1;
}
