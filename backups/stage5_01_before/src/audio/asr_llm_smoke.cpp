
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <unistd.h>

// Operation 2.9: ALSA -> Silero VAD -> SenseVoice -> LLMWorker -> RKLLM.
// This smoke test intentionally handles only TEXT questions.
int main(int argc, char** argv)
{
    if (argc != 5 && argc != 6)
    {
        std::cerr << "Usage: asr_llm_smoke <ALSA device> <ASR model dir> "
                  << "<VAD model> <RKLLM model> [record seconds: 20]\n";
        return 2;
    }

    const std::string audio_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    std::size_t record_seconds = 20;

    if (argc == 6)
    {
        try
        {
            const std::string value = argv[5];
            std::size_t parsed = 0;
            const unsigned long seconds = std::stoul(value, &parsed);

            if (parsed != value.size() || seconds < 1 || seconds > 120)
                throw std::invalid_argument("out of range");

            record_seconds = static_cast<std::size_t>(seconds);
        }
        catch (const std::exception&)
        {
            std::cerr << "Record seconds must be an integer from 1 to 120\n";
            return 2;
        }
    }

    const std::string asr_model = asr_dir + "/model.int8.onnx";
    const std::string asr_tokens = asr_dir + "/tokens.txt";

    for (const auto& path : {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr << "Cannot read model file: " << path << '\n';
            return 1;
        }
    }

    std::string error;

    LLMEngine llm(std::make_unique<RKLLMBackend>());

    std::cout << "[Init] RKLLM loading...\n" << std::flush;

    if (!llm.initialize(BackendConfig{llm_model, {}}, error))
    {
        std::cerr << "[Init] RKLLM failed: " << error << '\n';
        return 1;
    }

    ASRService asr;

    std::cout << "[Init] SenseVoice loading...\n" << std::flush;

    if (!asr.initialize(asr_model, asr_tokens, error))
    {
        std::cerr << "[Init] ASR failed: " << error << '\n';
        return 1;
    }

    // LLMWorker 内部使用独立线程执行 RKLLM 推理。
    // 队列容量为 2，用于限制等待推理的任务数量。
    LLMWorker llm_worker(llm, 2);

    if (!llm_worker.start(error))
    {
        std::cerr << "[Init] LLMWorker failed: " << error << '\n';
        return 1;
    }

    // 音频队列用于连接 VAD 与 ASRWorker。
    AudioBufferQueue audio_queue(4);

    // 保护多线程终端输出，避免日志严重交错。
    std::mutex print_mutex;

    // 保护 LLM 请求完成情况。
    std::mutex state_mutex;
    std::condition_variable completed_cv;

    IntentRouter router;

    std::uint64_t next_id = 1;

    std::size_t accepted = 0;
    std::size_t completed = 0;
    std::size_t successful = 0;
    std::size_t failed = 0;
    std::size_t rejected = 0;
    std::size_t skipped_vision = 0;

    // ASRWorker 识别出文字后执行此回调。
    // 注意：本回调运行在 ASRWorker 的工作线程中。
    const auto on_text = [&](const std::string& recognized)
    {
        // 先通过 IntentRouter 判断请求类型。
        const RouteDecision route = router.route(recognized);

        // 当前操作 2.9 仅支持 TEXT。
        if (route.type != RequestType::Text)
        {
            ++skipped_vision;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[Route] VISION not supported in operation 2.9: "
                << recognized << '\n';

            return;
        }

        // 为每个请求分配唯一 ID。
        const std::uint64_t id = next_id++;

        // 用于控制流式输出前缀只打印一次。
        auto prefix_printed = std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[ASR->LLM] request #" << id
                << ": " << recognized
                << '\n'
                << std::flush;
        }

        // =====================================================
        // 操作 2.9 优化：构造简短回答 Prompt
        //
        // recognized：SenseVoice 输出的原始识别文字。
        // prompt：提交给 Qwen 的完整问题。
        //
        // 只约束 LLM 回答，不修改 ASR 原始识别内容。
        // =====================================================

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过50个汉字。";

        // =====================================================
        // 非阻塞提交 LLMWorker
        //
        // submit() 仅负责提交任务。
        // 真正耗时的 rkllm_run() 在 Worker 线程执行。
        // =====================================================

        const auto status = llm_worker.submit(
            id,
            prompt,

            // 流式输出回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const std::string& chunk)
            {
                if (chunk.empty())
                    return;

                std::lock_guard<std::mutex> lock(print_mutex);

                if (!*prefix_printed)
                {
                    std::cout
                        << "\n[LLM #" << request_id << "] ";

                    *prefix_printed = true;
                }

                std::cout << chunk << std::flush;
            },

            // LLM 推理完成回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const InferenceResult& result,
                double wait_ms)
            {
                {
                    std::lock_guard<std::mutex> lock(print_mutex);

                    if (*prefix_printed)
                        std::cout << '\n';

                    std::cout
                        << "[LLM done #" << request_id << "] success="
                        << (result.success ? "true" : "false")
                        << " queue_wait_ms=" << wait_ms
                        << " first_text_ms=" << result.first_text_ms
                        << " request_latency_ms=" << result.latency_ms
                        << '\n';

                    if (!result.success)
                    {
                        std::cout
                            << "[LLM error] "
                            << result.error_message
                            << '\n';
                    }
                }

                {
                    std::lock_guard<std::mutex> lock(state_mutex);

                    ++completed;

                    if (result.success)
                        ++successful;
                    else
                        ++failed;
                }

                // 通知主线程：某个 LLM 请求已完成。
                completed_cv.notify_one();
            }
        );

        // 判断任务是否成功加入队列。
        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            ++accepted;
        }
        else
        {
            ++rejected;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "[LLM rejected #" << id << "] "
                << (status == LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "worker not running")
                << '\n';
        }
    };

    // ASRWorker 从音频队列取出语音片段，执行 SenseVoice。
    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        on_text
    );

    // VadAudioWorker 负责 ALSA 录音和 Silero VAD 分段。
    VadAudioWorker producer(
        audio_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    std::cout
        << "[Listen] "
        << record_seconds
        << " seconds. Speak one short TEXT question, then pause.\n"
        << std::flush;

    try
    {
        // 启动 ASR 消费线程。
        consumer.start();

        // 启动 ALSA + VAD 生产线程。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Thread creation failed: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        return 1;
    }

    // 等待录音/VAD 线程结束。
    producer.join();

    // 等待 ASR 处理完剩余语音片段。
    consumer.join();

    // ASRWorker 退出后，不会再产生新的 LLM 请求。
    // 先等待所有已接受请求完成，再停止 LLMWorker。
    {
        std::unique_lock<std::mutex> lock(state_mutex);

        while (completed < accepted)
        {
            if (!completed_cv.wait_for(
                    lock,
                    std::chrono::seconds(2),
                    [&] { return completed == accepted; }))
            {
                const auto remaining = accepted - completed;

                lock.unlock();

                {
                    std::lock_guard<std::mutex> out(print_mutex);

                    std::cout
                        << "\n[Main] waiting for "
                        << remaining
                        << " LLM request(s)...\n"
                        << std::flush;
                }

                lock.lock();
            }
        }
    }

    // 正确的资源释放顺序：
    // 1. 停止 Worker。
    // 2. 等待 Worker 线程退出。
    // 3. 关闭 RKLLM Runtime。
    llm_worker.requestStop();
    llm_worker.join();
    llm.shutdown();

    // 输出整个语音问答链路的统计信息。
    {
        std::lock_guard<std::mutex> out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM summary ===\n"
            << "VAD segments: " << producer.producedCount() << '\n'
            << "ASR recognized: " << consumer.processedCount() << '\n'
            << "Audio queue dropped: " << audio_queue.droppedCount() << '\n'
            << "LLM accepted: " << accepted << '\n'
            << "LLM completed: " << completed << '\n'
            << "LLM successful: " << successful << '\n'
            << "LLM failed: " << failed << '\n'
            << "LLM rejected: " << rejected << '\n'
            << "Skipped VISION: " << skipped_vision << '\n';

        if (!producer.ok())
            std::cerr << "[VAD] " << producer.error() << '\n';

        if (!consumer.ok())
            std::cerr << "[ASR] " << consumer.error() << '\n';
    }

    // 最终验收条件。
    const bool passed =
        producer.ok() &&
        consumer.ok() &&
        accepted > 0 &&
        accepted == completed &&
        successful > 0 &&
        failed == 0 &&
        rejected == 0 &&
        audio_queue.droppedCount() == 0;

    std::cout << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
