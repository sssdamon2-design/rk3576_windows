
#include "audio/asr_pipeline.h"
#include "app/pipeline_admission.h"
#include "app/pipeline_metrics.h"
#include "app/profiling_inputs.h"
#include <fstream>
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"
#include "audio/tts_worker.h"

#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"
#include "ai/vlm_engine.h"
#include "video/camera_service.h"
#include "video/latest_frame_buffer.h"

#include <chrono>
#include <algorithm>
#include <fstream>
#include <sstream>
#include <cstdlib>
#include <atomic>
#include <cerrno>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <thread>

#include <pthread.h>
#include <signal.h>

#include <unistd.h>

namespace {
// Construct before SDKs/workers: all descendant threads inherit the blocked set.
// sigtimedwait runs in an ordinary thread; there is no asynchronous signal handler.
class StopSignals {
public:
    StopSignals()
    {
        sigemptyset(&signals_);
        sigaddset(&signals_, SIGINT);
        sigaddset(&signals_, SIGTERM);
        if (pthread_sigmask(SIG_BLOCK, &signals_, &previous_) != 0)
            throw std::runtime_error("Cannot block stop signals");
        try
        {
            thread_ = std::thread([this] {
                const timespec interval{0, 100000000};
                while (!finished_.load())
                {
                    const int received = sigtimedwait(&signals_, nullptr, &interval);
                    if (received == SIGINT || received == SIGTERM)
                    {
                        int empty = 0;
                        signal_.compare_exchange_strong(empty, received);
                    }
                    else if (received < 0 && errno != EAGAIN && errno != EINTR)
                    {
                        wait_failed_.store(true);
                        break;
                    }
                }
            });
        }
        catch (...)
        {
            pthread_sigmask(SIG_SETMASK, &previous_, nullptr);
            throw;
        }
    }
    ~StopSignals()
    {
        finished_.store(true);
        if (thread_.joinable()) thread_.join();
        pthread_sigmask(SIG_SETMASK, &previous_, nullptr);
    }
    StopSignals(const StopSignals&) = delete;
    StopSignals& operator=(const StopSignals&) = delete;
    int received() const noexcept { return signal_.load(); }
    bool failed() const noexcept { return wait_failed_.load(); }
private:
    sigset_t signals_{};
    sigset_t previous_{};
    std::atomic<int> signal_{0};
    std::atomic<bool> finished_{false};
    std::atomic<bool> wait_failed_{false};
    std::thread thread_;
};
} // namespace

// ==========================================================
// Stage 3.5
//
// ALSA Capture
//     ↓
// Silero VAD
//     ↓
// SenseVoice ASR
//     ↓
// IntentRouter
//     ↓
// LLMWorker -> RKLLM / Qwen2.5
//     ↓
// TTSWorker -> Kokoro
//     ↓
// AlsaPlaybackService
//     ↓
// USB Headset
//
// TEXT and VISION share one asynchronous bounded inference FIFO.
// ==========================================================

int main(int argc, char** argv) try
{
    // ------------------------------------------------------
    // 1. 命令行参数检查
    // ------------------------------------------------------

    if (argc < 7 || (argc > 10 && argc != 13))
    {
        std::cerr
            << "Usage: asr_llm_tts_smoke "
            << "<capture_device> "
            << "<asr_model_dir> "
            << "<vad_model> "
            << "<rkllm_model> "
            << "<kokoro_dir> "
            << "<playback_device> "
            << "[record_seconds=12] "
            << "[tts_threads=4] "
            << "[sid=17] "
            << "[vlm_rkllm vision_rknn camera_device]\n";

        return 2;
    }

    const std::string capture_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    const std::string kokoro_dir = argv[5];
    const std::string playback_device = argv[6];

    unsigned int record_seconds = 12;

    int tts_threads = 4;
    int sid = 17;

    // 兼容旧命令。新增三项参数时启用完整视觉语音链路。
    // 语音模式须传三个原有可选参数，再传 VLM 模型与 Camera 设备。
    const bool enable_vision = (argc == 13);
    const std::string vlm_model = enable_vision ? argv[10] : "";
    const std::string vision_model = enable_vision ? argv[11] : "";
    const std::string camera_device = enable_vision ? argv[12] : "";

    // ------------------------------------------------------
    // 2. 解析可选参数
    // ------------------------------------------------------

    try
    {
        const auto parse = [](
            const char* arg,
            int lo,
            int hi
        ) -> int
        {
            const std::string value(arg);

            std::size_t used = 0;

            const int result =
                std::stoi(value, &used);

            if (used != value.size() ||
                result < lo ||
                result > hi)
            {
                throw std::invalid_argument(
                    "out of range"
                );
            }

            return result;
        };

        if (argc >= 8)
        {
            record_seconds =
                static_cast<unsigned int>(
                    parse(argv[7], 1, 120)
                );
        }

        if (argc >= 9)
        {
            tts_threads =
                parse(argv[8], 1, 8);
        }

        if (argc >= 10)
        {
            sid =
                parse(argv[9], 0, 10000);
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "[Args] Invalid record_seconds / "
            << "threads / sid\n";

        return 2;
    }

    // ------------------------------------------------------
    // 3. 检查 ASR / VAD / LLM 模型文件
    // ------------------------------------------------------

    const std::string asr_model =
        asr_dir + "/model.int8.onnx";

    const std::string asr_tokens =
        asr_dir + "/tokens.txt";

    for (const auto& path :
         {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr
                << "[Init] Cannot read model file: "
                << path
                << '\n';

            return 1;
        }
    }

    if (enable_vision)
    {
        for (const auto& path : {vlm_model, vision_model})
        {
            if (::access(path.c_str(), R_OK) != 0)
            {
                std::cerr << "[Init] Cannot read VLM file: " << path << '\n';
                return 1;
            }
        }
    }

    std::string error;

    StopSignals stop_signals;

    // ------------------------------------------------------
    // 4. 初始化 RKLLM
    // ------------------------------------------------------

    LLMEngine llm(
        std::make_unique<RKLLMBackend>()
    );

    std::cout
        << "[Init] Loading RKLLM...\n"
        << std::flush;

    if (!llm.initialize(
            BackendConfig{llm_model, {}},
            error))
    {
        std::cerr
            << "[Init] RKLLM failed: "
            << error
            << '\n';

        return 1;
    }

    // ------------------------------------------------------
    // 5. 初始化 SenseVoice
    // ------------------------------------------------------

    ASRService asr;

    std::cout
        << "[Init] Loading SenseVoice...\n"
        << std::flush;

    if (!asr.initialize(
            asr_model,
            asr_tokens,
            error))
    {
        std::cerr
            << "[Init] ASR failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 6. 初始化 Kokoro TTS
    // ------------------------------------------------------

    TTSService tts;

    std::cout
        << "[Init] Loading Kokoro...\n"
        << std::flush;

    if (!tts.initialize(
            kokoro_dir,
            error,
            tts_threads,
            sid))
    {
        std::cerr
            << "[Init] Kokoro failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 7. 初始化 ALSA Playback
    // ------------------------------------------------------

    AlsaPlaybackService playback;

    if (!playback.open(
            playback_device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[Init] ALSA playback failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // Callback state precedes workers: reverse destruction joins workers first.
    // ------------------------------------------------------
    // 10. 创建 ASR 音频队列和线程同步对象
    // ------------------------------------------------------

    AudioBufferQueue audio_queue(4);

    // 保护不同线程的日志输出。
    std::mutex print_mutex;

    // 保护 LLM/TTS 任务完成计数。
    std::mutex state_mutex;

    // 通知主线程有任务完成。
    std::condition_variable completed_cv;

    IntentRouter router;

    // 由单个 ASRWorker 回调生成请求 ID。
    std::uint64_t next_id = 1;

    const int max_inflight = pipelineEnv("STAGE5_MAX_INFLIGHT", 2, 1, 8);
    const int request_lifetime_ms = pipelineEnv("STAGE5_REQUEST_LIFETIME_MS", 45000, 1, 300000);
    const int inference_queue_ms = pipelineEnv("STAGE5_INFERENCE_QUEUE_MS", 10000, 1, 60000);
    const int tts_queue_ms = pipelineEnv("STAGE5_TTS_QUEUE_MS", 12000, 1, 60000);
    const char* stop_value = std::getenv("STAGE5_STOP_MODE");
    const std::string stop_mode = stop_value ? stop_value : "drain";
    if (stop_mode != "drain" && stop_mode != "cancel_pending") throw std::invalid_argument("Invalid STAGE5_STOP_MODE");
    PipelineAdmission admission(static_cast<std::size_t>(max_inflight));
    std::size_t dispatch_calls=0, pipeline_rejected=0, cancelled_before_submit=0;
    std::size_t vision_accepted=0, vision_rejected=0;
    std::size_t llm_cancelled=0, llm_expired=0, vision_cancelled=0, vision_expired=0;
    std::size_t tts_cancelled=0, tts_expired=0, downstream_cancelled=0;
    // Must outlive the asynchronous inference worker, including exception unwinding.
    LatestFrameBuffer frames;
    std::unique_ptr<CameraService> camera;
    std::unique_ptr<VLMEngine> vlm;
    LatestFrameBuffer::FramePtr profiling_frame;
    if(const char* folder=std::getenv("STAGE5_REPLAY_FRAME_DIR")){
        if(!enable_vision || (!std::getenv("STAGE5_REPLAY_FILE") && !std::getenv("STAGE5_REPLAY_AUDIO_FILE")))throw std::invalid_argument("Fixed frame is allowed only with explicit replay and VISION");
        profiling_frame=loadProfilingFrame(folder);
        std::cout<<"[InputMode] fixed NV12 for replay VLM; Camera still captures independently\n";
    }

    // ------------------------------------------------------
    // 11. LLM 和 TTS 统计
    // ------------------------------------------------------

    std::size_t llm_accepted = 0;
    std::size_t llm_completed = 0;
    std::size_t llm_successful = 0;
    std::size_t llm_failed = 0;
    std::size_t llm_rejected = 0;

    std::size_t skipped_vision = 0;
    std::size_t vision_completed = 0;
    std::size_t vision_successful = 0;
    std::size_t vision_failed = 0;

    std::size_t tts_accepted = 0;
    std::size_t tts_completed = 0;
    std::size_t tts_successful = 0;
    std::size_t tts_failed = 0;
    std::size_t tts_rejected = 0;
    std::size_t tts_empty = 0;

    // ------------------------------------------------------
    // 8. 创建并启动 TTSWorker
    // ------------------------------------------------------
    //
    // TTSWorker 不拥有 TTSService 和 PlaybackService。
    // 两个 Service 必须比 Worker 活得更久。
    //
    // capacity=2 表示最多允许两个等待任务。
    // ------------------------------------------------------

    TTSWorker tts_worker(
        tts,
        playback,
        2
    );

    if (!tts_worker.start(error))
    {
        std::cerr
            << "[Init] TTSWorker failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 9. 创建并启动 LLMWorker
    // ------------------------------------------------------

    LLMWorker llm_worker(
        llm,
        2
    );

    if (!llm_worker.start(error))
    {
        std::cerr
            << "[Init] LLMWorker failed: "
            << error
            << '\n';

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // Stage 4: 正式 Camera + VLM Backend。保持旧的 TEXT 链路不变。
    if (enable_vision)
    {
        constexpr std::uint32_t nv12 = std::uint32_t('N') |
            (std::uint32_t('V') << 8) |
            (std::uint32_t('1') << 16) |
            (std::uint32_t('2') << 24);

        camera = std::make_unique<CameraService>(
            camera_device, 3840, 2160, nv12, frames);
        if (!camera->start())
        {
            std::cerr << "[Init] Camera failed: "
                      << camera->stats().last_error << '\n';
            llm_worker.requestStop();
            llm_worker.join();
            tts_worker.requestStop();
            tts_worker.join();
            llm.shutdown();
            return 1;
        }

        vlm = std::make_unique<VLMEngine>(
            std::make_unique<RK3576VLMBackend>());
        std::cout << "[Init] Loading SmolVLM2 RKNN + RKLLM...\n"
                  << std::flush;
        if (!vlm->initialize(
            BackendConfig{vlm_model, vision_model}, error))
        {
            std::cerr << "[Init] VLM failed: " << error << '\n';
            camera->stop();
            llm_worker.requestStop();
            llm_worker.join();
            tts_worker.requestStop();
            tts_worker.join();
            llm.shutdown();
            return 1;
        }
        std::cout << "[Init] VLM and Camera ready\n";
    }

    // ------------------------------------------------------
    // 12. ASR 识别完成回调
    // ------------------------------------------------------
    //
    // 此回调在 ASRWorker 线程执行。
    //
    // recognized 是 SenseVoice 的识别结果。
    // ------------------------------------------------------

    const auto on_text =
        [&](const std::string& recognized, RequestTracePtr supplied_trace = {})
    {
        const auto request_id = supplied_trace ? supplied_trace->id() : next_id++;
        if(supplied_trace)next_id=std::max(next_id,request_id+1);
        const auto trace=supplied_trace ? std::move(supplied_trace) : makeRequestTrace(request_id);
        RequestTraceScope trace_scope(trace);
        traceMark("business_dispatch_begin");
        DispatchTimer dispatch_timer{print_mutex, ++dispatch_calls};
        // --------------------------------------------------
        // 12.1 意图判断
        // --------------------------------------------------

        const RouteDecision route =
            router.route(recognized);

        auto ticket = admission.tryAcquire(request_id, std::chrono::milliseconds(request_lifetime_ms));
        if (!ticket)
        {
            traceMark("pipeline_rejected_busy");
            ++pipeline_rejected;
            std::lock_guard<std::mutex> out(print_mutex);
            std::cout << "[Pipeline rejected #" << request_id << "] route=" << requestTypeName(route.type)
                      << " reason=busy_or_closed limit=" << max_inflight << '\n';
            return;
        }

        if (route.type == RequestType::Vision)
        {
            if (!enable_vision || !vlm)
            {
                traceMark("vision_disabled");
                ++skipped_vision;
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "\n[Route] VISION disabled: "
                          << recognized << '\n';
                return;
            }

            const auto question_at = std::chrono::steady_clock::now();
            // 先复用已在实机验证的英语单图问答；中文语音负责触发路由。
            // 避免 256M 模型不稳定的中文指令影响最终闭环验收。
            const std::string vlm_question =
                "What do you see? Answer briefly.";

            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "\n[ASR->VISION #" << request_id << "] "
                          << recognized << '\n';
            }

            const auto status = llm_worker.submitTask(request_id,
                [&, vlm_question](const LLMStreamCallback&) {
                    // Fetch a fresh owned frame when the task executes, never pin queued full frames.
                    return vlm->infer(profiling_frame?profiling_frame:frames.getLatest(), vlm_question);
                }, {},
                [&, question_at, ticket, trace](std::uint64_t request_id, const InferenceResult& result, double inference_wait_ms)
                {
                    {
                        std::lock_guard<std::mutex> lock(state_mutex);
                        ++vision_completed;
                        if (result.disposition==TaskDisposition::Cancelled) ++vision_cancelled;
                        else if (result.disposition==TaskDisposition::Expired) ++vision_expired;
                        else if (result.success && !result.text.empty()) ++vision_successful;
                        else ++vision_failed;
                    }

                    {
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[VLM done #" << request_id << "] success="
                                  << (result.success ? "true" : "false")
                                  << " queue_ms=" << inference_wait_ms
                                  << " disposition=" << dispositionName(result.disposition)
                                  << " frame_id=" << result.frame_id
                                  << " frame_age_ms=" << result.frame_age_ms
                                  << " latency_ms=" << result.latency_ms
                                  << '\n';
                        if (result.success)
                            std::cout << "[VLM Answer #" << request_id << "] "
                                      << result.text << '\n';
                        else
                            std::cout << (result.disposition==TaskDisposition::Completed ? "[VLM Error] " : "[VLM terminal] ") << result.error_message << '\n';
                    }

                    if (result.success && !result.text.empty() && ticket->cancelled())
                    {
                        { std::lock_guard<std::mutex> lock(state_mutex); ++downstream_cancelled; }
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[Pipeline downstream cancelled #" << request_id << "] stage=tts\n";
                    }
                    if (result.success && !result.text.empty() && !ticket->cancelled())
                    {
                        const auto status = tts_worker.submit(
                            request_id, result.text,
                            [&, question_at, ticket](
                                std::uint64_t done_id,
                                const TTSWorkerResult& outcome,
                                double queue_ms)
                            {
                                const double e2e_ms = std::chrono::duration<
                                    double, std::milli>(
                                    std::chrono::steady_clock::now() - question_at
                                ).count();
                                {
                                    std::lock_guard<std::mutex> out(print_mutex);
                                    std::cout << "[VISION TTS done #" << done_id
                                              << "] success="
                                              << (outcome.success ? "true" : "false")
                                              << " queue_ms=" << queue_ms
                                              << " synth_ms=" << outcome.synthesis_ms
                                              << " playback_ms=" << outcome.playback_ms
                                              << " asr_text_to_end_ms=" << e2e_ms
                                              << '\n';
                                    if (!outcome.success)
                                        std::cout << (outcome.disposition==TaskDisposition::Completed ? "[TTS error] " : "[TTS terminal] ")
                                                  << outcome.error_message << '\n';
                                }
                                {
                                    std::lock_guard<std::mutex> lock(state_mutex);
                                    ++tts_completed;
                                    if (outcome.success) ++tts_successful;
                                    else if (outcome.disposition==TaskDisposition::Cancelled) ++tts_cancelled;
                                    else if (outcome.disposition==TaskDisposition::Expired) ++tts_expired;
                                    else ++tts_failed;
                                }
                                completed_cv.notify_all();
                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms), trace));

                {
                    std::lock_guard<std::mutex> lock(state_mutex);
                    if (status == TTSSubmitStatus::Accepted)
                        ++tts_accepted;
                    else
                        ++tts_rejected;
                }
                if (status != TTSSubmitStatus::Accepted)
                {
                    std::lock_guard<std::mutex> out(print_mutex);
                    std::cout << "[VISION TTS rejected #" << request_id
                              << "] status=" << static_cast<int>(status)
                              << '\n';
                }
            }
            else if (result.success && result.text.empty())
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                ++tts_empty;
            }
            // Inference/done run on the shared worker; ASR only submits.
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms), trace));
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                if (status==LLMSubmitStatus::Accepted) ++vision_accepted;
                else if (status==LLMSubmitStatus::NotRunning && ticket->cancelled()) ++cancelled_before_submit;
                else ++vision_rejected;
            }
            if (status!=LLMSubmitStatus::Accepted)
            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << (ticket->cancelled() ? "[VISION submission cancelled #" : "[VISION rejected #") << request_id << "] status=" << static_cast<int>(status) << '\n';
            }
            return;
        }

        // --------------------------------------------------
        // 12.2 分配请求 ID
        // --------------------------------------------------

        const std::uint64_t id =
            request_id;

        // 记录 ASR 输出文本的时刻。
        const auto question_at =
            std::chrono::steady_clock::now();

        // 记录 LLM 是否已经输出前缀。
        auto prefix_printed =
            std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "\n[ASR->LLM #" << id << "] "
                << recognized
                << '\n';
        }

        // --------------------------------------------------
        // 12.3 构造 LLM Prompt
        // --------------------------------------------------
        //
        // 限制回答长度，降低当前 Kokoro 的合成等待。
        // 不改变 ASR 原始文本。
        // --------------------------------------------------

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过25个汉字。";

        // --------------------------------------------------
        // 12.4 非阻塞提交 LLMWorker
        // --------------------------------------------------

        const auto status =
            llm_worker.submit(
                id,
                prompt,

                // ------------------------------------------
                // LLM 流式文本回调
                // ------------------------------------------

                [&, prefix_printed](
                    std::uint64_t request_id,
                    const std::string& chunk)
                {
                    if (chunk.empty())
                    {
                        return;
                    }

                    std::lock_guard<std::mutex>
                        out(print_mutex);

                    if (!*prefix_printed)
                    {
                        std::cout
                            << "\n[LLM #"
                            << request_id
                            << "] ";

                        *prefix_printed = true;
                    }

                    std::cout
                        << chunk
                        << std::flush;
                },

                // ------------------------------------------
                // LLM 推理完成回调
                // ------------------------------------------
                //
                // 关键：这里把 LLM 答案交给 TTSWorker。
                // ------------------------------------------

                [&, prefix_printed, question_at, ticket, trace](
                    std::uint64_t request_id,
                    const InferenceResult& result,
                    double llm_queue_ms)
                {
                    {
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        if (*prefix_printed)
                        {
                            std::cout << '\n';
                        }

                        std::cout
                            << "[LLM done #"
                            << request_id
                            << "] success="
                            << (result.success
                                ? "true"
                                : "false")
                            << " queue_ms="
                            << llm_queue_ms
                            << " first_text_ms="
                            << result.first_text_ms
                            << " latency_ms="
                            << result.latency_ms
                            << '\n';

                        if (!result.success)
                        {
                            std::cout
                                << (result.disposition==TaskDisposition::Completed ? "[LLM error] " : "[LLM terminal] ")
                                << result.error_message
                                << '\n';
                        }
                    }

                    // --------------------------------------
                    // 12.5 判断 LLM 是否产生有效文本
                    // --------------------------------------

                    TTSSubmitStatus tts_status =
                        TTSSubmitStatus::NotRunning;

                    std::string tts_submit_error;

                    if (result.success && !result.text.empty() && ticket->cancelled())
                    {
                        { std::lock_guard<std::mutex> lock(state_mutex); ++downstream_cancelled; }
                        std::lock_guard<std::mutex> out(print_mutex);
                        std::cout << "[Pipeline downstream cancelled #" << request_id << "] stage=tts\n";
                    }
                    const bool has_answer =
                        result.success &&
                        !result.text.empty() && !ticket->cancelled();

                    if (has_answer)
                    {
                        try
                        {
                            // ------------------------------
                            // 12.6 向 TTSWorker 提交答案
                            // ------------------------------

                            tts_status =
                                tts_worker.submit(
                                    request_id,
                                    result.text,

                                    // ----------------------
                                    // TTS 完成回调
                                    // ----------------------

                                    [&, question_at, ticket](
                                        std::uint64_t tts_id,
                                        const TTSWorkerResult& tts_result,
                                        double tts_queue_ms)
                                    {
                                        // 从 ASR 输出文本到
                                        // 播放任务结束的耗时。
                                        const double e2e_ms =
                                            std::chrono::duration<
                                                double,
                                                std::milli
                                            >(
                                                std::chrono::
                                                    steady_clock::now()
                                                - question_at
                                            ).count();

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > out(print_mutex);

                                            std::cout
                                                << "[TTS done #"
                                                << tts_id
                                                << "] success="
                                                << (tts_result.success
                                                    ? "true"
                                                    : "false")
                                                << " queue_ms="
                                                << tts_queue_ms
                                                << " synth_ms="
                                                << tts_result.synthesis_ms
                                                << " audio_sec="
                                                << tts_result.audio_seconds
                                                << " playback_ms="
                                                << tts_result.playback_ms
                                                << " xruns="
                                                << tts_result.xrun_count
                                                << " asr_text_to_end_ms="
                                                << e2e_ms
                                                << '\n';

                                            if (!tts_result.success)
                                            {
                                                std::cout
                                                    << (tts_result.disposition==TaskDisposition::Completed ? "[TTS error] " : "[TTS terminal] ")
                                                    << tts_result.error_message
                                                    << '\n';
                                            }
                                        }

                                        // ------------------
                                        // 更新 TTS 任务统计
                                        // ------------------

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > lock(state_mutex);

                                            ++tts_completed;

                                            if (tts_result.success)
                                            {
                                                ++tts_successful;
                                            }
                                            else if (tts_result.disposition==TaskDisposition::Cancelled) ++tts_cancelled;
                                            else if (tts_result.disposition==TaskDisposition::Expired) ++tts_expired;
                                            else ++tts_failed;
                                        }

                                        // 唤醒等待中的主线程。
                                        completed_cv.notify_all();
                                    }, ticket->options(std::chrono::milliseconds(tts_queue_ms), trace)
                                );
                        }
                        catch (const std::exception& e)
                        {
                            tts_submit_error = e.what();
                        }
                        catch (...)
                        {
                            tts_submit_error =
                                "unknown exception";
                        }

                        // ----------------------------------
                        // 12.7 处理 TTS 提交失败
                        // ----------------------------------

                        if (tts_status !=
                            TTSSubmitStatus::Accepted)
                        {
                            std::lock_guard<std::mutex>
                                out(print_mutex);

                            std::cout
                                << "[TTS rejected #"
                                << request_id
                                << "] ";

                            if (!tts_submit_error.empty())
                            {
                                std::cout
                                    << tts_submit_error;
                            }
                            else if (
                                tts_status ==
                                TTSSubmitStatus::QueueFull)
                            {
                                std::cout
                                    << "queue full";
                            }
                            else
                            {
                                std::cout
                                    << "not running";
                            }

                            std::cout << '\n';
                        }
                    }
                    else if (result.success)
                    {
                        // LLM 成功但回答为空，
                        // 不能向 TTS 提交空文本。
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        std::cout
                            << "[TTS skipped #"
                            << request_id
                            << "] LLM returned empty answer\n";
                    }

                    // --------------------------------------
                    // 12.8 更新任务计数
                    // --------------------------------------
                    //
                    // 重要：
                    // 先提交 TTS，再标记 LLM completed。
                    //
                    // 这样主线程等完所有 LLM 后，
                    // 就能确认不再产生新的 TTS 请求。
                    // --------------------------------------

                    {
                        std::lock_guard<std::mutex>
                            lock(state_mutex);

                        ++llm_completed;

                        if (result.success)
                        {
                            ++llm_successful;
                        }
                        else if (result.disposition==TaskDisposition::Cancelled) ++llm_cancelled;
                        else if (result.disposition==TaskDisposition::Expired) ++llm_expired;
                        else ++llm_failed;

                        if (result.success &&
                            result.text.empty())
                        {
                            ++tts_empty;
                        }

                        if (has_answer)
                        {
                            if (tts_status ==
                                TTSSubmitStatus::Accepted)
                            {
                                ++tts_accepted;
                            }
                            else
                            {
                                ++tts_rejected;
                            }
                        }
                    }

                    completed_cv.notify_all();
                }, ticket->options(std::chrono::milliseconds(inference_queue_ms), trace)
            );

        // --------------------------------------------------
        // 12.9 处理 LLM 任务提交结果
        // --------------------------------------------------

        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex>
                lock(state_mutex);

            ++llm_accepted;
        }
        else
        {
            // 只有 ASRWorker 修改该计数。
            {
                std::lock_guard<std::mutex> lock(state_mutex);
                if (status==LLMSubmitStatus::NotRunning && ticket->cancelled()) ++cancelled_before_submit;
                else ++llm_rejected;
            }

            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << (ticket->cancelled() ? "[LLM submission cancelled #" : "[LLM rejected #")
                << id
                << "] "
                << (status ==
                    LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "not running")
                << '\n';
        }
    };

    // ------------------------------------------------------
    // 13. 创建 ASRWorker 和 VadAudioWorker
    // ------------------------------------------------------

    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        {},
        [&](const std::string& text,const AudioSegment& segment){on_text(text,segment.trace);}
    );

    VadAudioWorker producer(
        capture_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");
    const char* audio_replay_path=std::getenv("STAGE5_REPLAY_AUDIO_FILE");
    if(replay_path && audio_replay_path)throw std::invalid_argument("Text and audio replay are mutually exclusive");
    const bool replay_mode=replay_path!=nullptr || audio_replay_path!=nullptr;
    if (!replay_mode)
    {
        std::cout
            << "[Listen] "
            << record_seconds
            << " seconds. "
            << (enable_vision ? "Ask ONE short voice question (text or camera).\n"
                               : "Ask ONE short text question and pause.\n")
            << std::flush;
    }
    else std::cout << (audio_replay_path?"[Replay ready] fixed presegmented audio; real ASR, no microphone/VAD\n":"[Replay ready] controlled text; microphone/VAD/ASR not run\n") << std::flush;

    // ------------------------------------------------------
    // 14. 启动录音/VAD 和 ASR 工作线程
    // ------------------------------------------------------

    if (replay_mode)
    {
        std::ifstream input(audio_replay_path?audio_replay_path:replay_path);
        if (!input) throw std::runtime_error("Cannot open replay input");
        std::cout << (audio_replay_path?"[InputMode] replay_audio REAL_ASR_NO_MICROPHONE_OR_VAD\n":"[InputMode] replay_only NO_MICROPHONE_ASR_OR_VAD_INFERENCE\n") << std::flush;
        if(audio_replay_path)consumer.start();
        const auto replay_start=std::chrono::steady_clock::now();
        std::uint64_t audio_replay_sequence=1; // Producer-only; next_id belongs to the ASR callback thread.
        std::string line;
        while (std::getline(input,line))
        {
            if (line.empty()) continue;
            const auto tab=line.find('\t');
            if (tab==std::string::npos) throw std::runtime_error("Invalid replay line");
            std::size_t used=0;
            const long delay=std::stol(line.substr(0,tab),&used);
            if (used!=tab || delay<0 || delay>120000) throw std::runtime_error("Invalid replay offset");
            const auto scheduled=replay_start+std::chrono::milliseconds(delay);
            while(stop_signals.received()==0 && std::chrono::steady_clock::now()<scheduled)
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
            if (stop_signals.received()!=0) break;
            std::cout << "[Replay] scheduled_ms=" << delay << (audio_replay_path?" source=fixed_audio\n":" source=controlled_text\n") << std::flush;
            if(audio_replay_path){
                AudioSegment segment;segment.sequence=audio_replay_sequence++;
                segment.trace=makeRequestTrace(segment.sequence);
                segment.samples=loadProfilingAudio(line.substr(tab+1));
                segment.enqueued_at=std::chrono::steady_clock::now();
                if(segment.trace)segment.trace->mark("offline_audio_ready",segment.enqueued_at);
                if(!audio_queue.push(std::move(segment)))throw std::runtime_error("Audio replay queue closed");
            }else on_text(line.substr(tab+1));
        }
        audio_queue.close();
        if(audio_replay_path)consumer.join();
    }
    else
    {
    try
    {
        // ASR 消费者先启动。
        consumer.start();

        // VAD 录音生产者后启动。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Cannot start capture/ASR thread: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 15. 等待录音/VAD 和 ASR 完成
    // ------------------------------------------------------

    bool stop_reported = false;
    while (!producer.isFinished())
    {
        if (stop_signals.received() != 0 || stop_signals.failed())
        {
            producer.requestStop();
            if (stop_mode == "cancel_pending")
            {
                admission.close(true);
                llm_worker.requestStop(StopMode::CancelPending);
            }
            if (!stop_reported)
            {
                std::lock_guard<std::mutex> out(print_mutex);
                std::cout << "[Shutdown] signal=" << stop_signals.received()
                          << " stopping capture; draining accepted work\n" << std::flush;
                stop_reported = true;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    producer.join();

    consumer.join();
    }
    asr.shutdown();
    admission.close(false);
    std::cout << (replay_mode ? "[Shutdown] replay input closed; recognizer destroyed\n" : "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\n") << std::flush;

    // 此时 ASRWorker 已经退出，
    // 不会继续向 LLMWorker 提交新请求。

    // ------------------------------------------------------
    // 16. 通用 Worker 完成等待函数
    // ------------------------------------------------------
    //
    // 在等待期间，主线程每 2 秒输出一次进度。
    //
    // accepted / completed 都必须由 state_mutex 保护。
    // ------------------------------------------------------

    const auto wait_for_jobs = [&](const char* stage, auto& worker, int deadline_seconds) -> bool
    {
        const auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(deadline_seconds);
        while (!worker.waitIdleFor(std::chrono::milliseconds(100)))
        {
            if ((stop_signals.received()!=0 || stop_signals.failed()) && stop_mode=="cancel_pending")
            {
                admission.close(true);
                llm_worker.requestStop(StopMode::CancelPending);
            }
            if (std::chrono::steady_clock::now()>=deadline)
            {
                std::cerr << "[Timeout] " << stage << " did not become idle\n";
                return false;
            }
        }
        return true;
    };

    // ------------------------------------------------------
    // 17. 等待全部 LLM 任务完成
    // ------------------------------------------------------

    const bool llm_drained =
        wait_for_jobs(
            "LLM",
            llm_worker,
            180
        );

    if (!llm_drained)
    {
        std::cerr
            << "[Timeout] LLM tasks "
            << "did not finish in 180s\n";
    }

    // ------------------------------------------------------
    // 18. 停止 LLMWorker
    // ------------------------------------------------------
    //
    // 必须等 LLMWorker 完全停止，
    // 才能确认不会再向 TTSWorker 提交任务。
    // ------------------------------------------------------

    llm_worker.requestStop();
    llm_worker.join();

    // LLM 不再被工作线程访问后，
    // 才允许释放 RKLLM Runtime。
    llm.shutdown();

    std::cout << "[Shutdown] LLM joined; Qwen runtime destroyed\n" << std::flush;

    // ------------------------------------------------------
    // 19. 等待全部 TTS 任务完成
    // ------------------------------------------------------
    //
    // 必须先等待 accepted == completed，
    // 然后再 requestStop。
    //
    // 否则会把队列中等待的 TTS 任务取消。
    // ------------------------------------------------------

    const bool tts_drained =
        wait_for_jobs(
            "TTS",
            tts_worker,
            600
        );

    if (!tts_drained)
    {
        std::cerr
            << "[Timeout] TTS tasks "
            << "did not finish in 600s\n";
    }

    // ------------------------------------------------------
    // 20. 停止 TTSWorker
    // ------------------------------------------------------

    tts_worker.requestStop();
    tts_worker.join();

    std::cout << "[Shutdown] TTS joined; playback_xruns=" << playback.xrunCount()
              << '\n' << std::flush;

    // 只有 Worker 退出以后，
    // 才能安全关闭 ALSA 和 TTSService。
    playback.close();
    tts.shutdown();
    if (camera) camera->stop();
    if (vlm) vlm->shutdown();
    std::cout << "[Shutdown] playback/TTS closed; Camera stopped; VLM destroyed\n"
              << "[Shutdown] complete signal=" << stop_signals.received() << '\n'
              << std::flush;

    // ------------------------------------------------------
    // 21. 输出整个语音交互链路的统计
    // ------------------------------------------------------

    {
        std::lock_guard<std::mutex>
            out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM -> TTS summary ===\n"

            << "VAD segments: "
            << producer.producedCount()
            << '\n'

            << "ASR recognized: "
            << consumer.processedCount()
            << '\n'

            << "Audio queue dropped: "
            << audio_queue.droppedCount()
            << '\n'

            << "LLM accepted/completed/"
            << "success/failed/rejected: "
            << llm_accepted
            << '/'
            << llm_completed
            << '/'
            << llm_successful
            << '/'
            << llm_failed
            << '/'
            << llm_rejected
            << '\n'

            << "TTS accepted/completed/"
            << "success/failed/rejected/empty: "
            << tts_accepted
            << '/'
            << tts_completed
            << '/'
            << tts_successful
            << '/'
            << tts_failed
            << '/'
            << tts_rejected
            << '/'
            << tts_empty
            << '\n'

            << "Skipped VISION: "
            << skipped_vision
            << '\n'
            << "VISION completed/success/failed: "
            << vision_completed << '/'
            << vision_successful << '/'
            << vision_failed << '\n';

        if (!replay_mode && !producer.ok())
        {
            std::cerr
                << "[VAD] "
                << producer.error()
                << '\n';
        }

        if (!replay_mode && !consumer.ok())
        {
            std::cerr
                << "[ASR] "
                << consumer.error()
                << '\n';
        }
    }

    const auto audio_stats=audio_queue.stats();
    std::cout << "[AudioQueueStats] pushed=" << audio_stats.pushed << " popped=" << audio_stats.popped
              << " dropped=" << audio_stats.dropped << " rejected_closed=" << audio_stats.rejected_closed
              << " peak=" << audio_stats.peak << " pending=" << audio_stats.pending << '\n';
    const auto inference_stats=llm_worker.stats();
    const auto tts_stats=tts_worker.stats();
    const auto admission_stats=admission.stats();
    printWorkerStats("inference", inference_stats);
    printWorkerStats("tts", tts_stats);
    std::cout << "[PipelineStats] dispatched=" << dispatch_calls << " accepted=" << admission_stats.accepted
              << " rejected=" << pipeline_rejected << " inflight=" << admission_stats.inflight
              << " peak=" << admission_stats.peak << " limit=" << max_inflight
              << " vision_accepted=" << vision_accepted << " vision_rejected=" << vision_rejected
              << " llm_cancelled=" << llm_cancelled << " llm_expired=" << llm_expired
              << " vision_cancelled=" << vision_cancelled << " vision_expired=" << vision_expired
              << " cancelled_before_submit=" << cancelled_before_submit
              << " downstream_cancelled=" << downstream_cancelled
              << " tts_cancelled=" << tts_cancelled << " tts_expired=" << tts_expired << '\n';

    // ------------------------------------------------------
    // 22. 最终验收条件
    // ------------------------------------------------------

    const bool passed =
        (replay_mode || (producer.ok() && consumer.ok())) && audio_queue.droppedCount()==0 &&
        llm_drained && tts_drained && !stop_signals.failed() &&
        (stop_signals.received()!=0 || llm_successful+vision_successful>0) &&
        inference_stats.accepted==inference_stats.completed && tts_stats.accepted==tts_stats.completed &&
        inference_stats.failed==0 && tts_stats.failed==0 &&
        inference_stats.callback_errors==0 && tts_stats.callback_errors==0 &&
        admission_stats.inflight==0 && llm_rejected==0 && vision_rejected==0 && tts_rejected==0;

    std::cout
        << (passed ? (stop_signals.received() != 0 ? "STOPPED\n" : "PASS\n") : "FAIL\n");

    return passed ? 0 : 1;
}
catch (const std::exception& e)
{
    std::cerr << "[Fatal] Voice pipeline exception: " << e.what() << '\n';
    return 1;
}
catch (...)
{
    std::cerr << "[Fatal] Voice pipeline: unknown exception\n";
    return 1;
}
