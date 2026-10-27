
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"

#include "ai/rk_backends.h"
#include "app/request_processor.h"
#include "video/camera_service.h"
#include "video/latest_frame_buffer.h"

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <unistd.h>

int main(int argc, char** argv)
{
    if (argc != 4 && argc != 5)
    {
        std::cerr
            << "Usage: asr_route_smoke "
            << "<ALSA device> <ASR model dir> "
            << "<VAD model> [camera device]\n";

        return 2;
    }

    const std::string audio_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];

    const bool use_camera = (argc == 5);

    const std::string camera_device =
        use_camera ? argv[4] : "/dev/video11";

    if (::access(vad_model.c_str(), R_OK) != 0)
    {
        std::cerr
            << "VAD model is not readable: "
            << vad_model << '\n';

        return 1;
    }

    // =================================================
    // 1. 创建多模态业务模块
    // =================================================

    LatestFrameBuffer frames;

    constexpr std::uint32_t nv12 =
        std::uint32_t('N') |
        (std::uint32_t('V') << 8) |
        (std::uint32_t('1') << 16) |
        (std::uint32_t('2') << 24);

    CameraService camera(
        camera_device,
        3840,
        2160,
        nv12,
        frames
    );

    // 当前 LLM/VLM 后端尚未接入真实 SDK。
    // 返回明确错误，不生成虚假的 AI 回答。
    LLMEngine llm(
        std::make_unique<RKLLMBackend>()
    );

    VLMEngine vlm(
        std::make_unique<RK3576VLMBackend>()
    );

    std::string error;

    if (!llm.initialize({}, error))
    {
        std::cout
            << "[LLM] Not ready: "
            << error << '\n';
    }

    if (!vlm.initialize({}, error))
    {
        std::cout
            << "[VLM] Not ready: "
            << error << '\n';
    }

    // 已有的多模态业务入口。
    RequestProcessor processor(
        frames,
        llm,
        vlm
    );

    // =================================================
    // 2. 加载 SenseVoiceSmall
    // =================================================

    ASRService asr;

    std::cout
        << "Loading SenseVoiceSmall...\n"
        << std::flush;

    if (!asr.initialize(
            asr_dir + "/model.int8.onnx",
            asr_dir + "/tokens.txt",
            error))
    {
        std::cerr
            << "ASR init failed: "
            << error << '\n';

        return 1;
    }

    std::cout << "ASR initialized\n";

    // =================================================
    // 3. 启动摄像头
    // =================================================

    if (use_camera)
    {
        if (!camera.start())
        {
            std::cerr
                << "Camera start failed: "
                << camera.stats().last_error
                << '\n';

            return 1;
        }

        std::cout
            << "Camera started: "
            << camera_device << '\n';
    }
    else
    {
        std::cout
            << "Camera disabled: routing-only test\n";
    }

    // =================================================
    // 4. 创建 ASR 多线程流水线
    // =================================================

    AudioBufferQueue queue(4);
    std::mutex print_mutex;

    std::size_t routed = 0;
    std::size_t text_routes = 0;
    std::size_t vision_routes = 0;

    bool vision_frame_seen = false;

    // 操作 9 核心：
    // ASR 文本直接传入 RequestProcessor。
    //
    // 回调运行在 ASRWorker 线程，
    // 因此不应长期执行耗时业务。
    auto on_recognized =
        [&](const std::string& question)
    {
        const RequestResult response =
            processor.process(question);

        ++routed;

        if (response.route.type ==
            RequestType::Text)
        {
            ++text_routes;
        }
        else
        {
            ++vision_routes;

            if (response.inference.frame_id != 0)
            {
                vision_frame_seen = true;
            }
        }

        // 只在打印时持有锁。
        std::lock_guard<std::mutex> lock(
            print_mutex
        );

        std::cout
            << "\n[Request] "
            << question << '\n'
            << "[Route] "
            << requestTypeName(response.route.type)
            << " ("
            << response.route.reason
            << ")\n";

        if (response.route.type ==
            RequestType::Vision)
        {
            std::cout
                << "[Frame] ID="
                << response.inference.frame_id
                << ", age="
                << response.inference.frame_age_ms
                << " ms\n";
        }

        if (response.inference.success)
        {
            std::cout
                << "[AI] "
                << response.inference.text
                << '\n';
        }
        else
        {
            std::cout
                << "[Backend unavailable/error] "
                << response.inference.error_message
                << '\n';
        }
    };

    // ASR 消费者负责推理与回调。
    ASRWorker consumer(
        queue,
        asr,
        print_mutex,
        on_recognized
    );

    // VAD 生产者负责采集和自动分段。
    constexpr std::size_t kRecordSeconds = 20;

    VadAudioWorker producer(
        audio_device,
        vad_model,
        queue,
        print_mutex,
        kRecordSeconds
    );

    std::cout
        << "Listening for 20 seconds...\n"
        << "Speak a TEXT question and "
        << "a VISION question.\n"
        << std::flush;

    // =================================================
    // 5. 启动双线程
    // =================================================

    const auto begin =
        std::chrono::steady_clock::now();

    consumer.start();
    producer.start();

    producer.join();
    consumer.join();

    const double wall_seconds =
        std::chrono::duration<double>(
            std::chrono::steady_clock::now() -
            begin
        ).count();

    // 工作线程退出后再停止 Camera。
    camera.stop();

    // =================================================
    // 6. 输出最终统计
    // =================================================

    std::cout
        << "\n=== ASR routing summary ===\n"
        << "Detected: "
        << producer.producedCount()
        << '\n'
        << "Recognized: "
        << consumer.processedCount()
        << '\n'
        << "Routed: "
        << routed
        << '\n'
        << "TEXT: "
        << text_routes
        << '\n'
        << "VISION: "
        << vision_routes
        << '\n'
        << "Dropped: "
        << queue.droppedCount()
        << '\n'
        << "Vision frame seen: "
        << (vision_frame_seen ? "yes" : "no")
        << '\n'
        << "Wall time: "
        << wall_seconds
        << " s\n";

    if (!producer.ok())
    {
        std::cerr
            << "VAD/AudioCapture error: "
            << producer.error()
            << '\n';
    }

    if (!consumer.ok())
    {
        std::cerr
            << "ASRWorker error: "
            << consumer.error()
            << '\n';
    }

    // 本次验收的是语音到业务路由，
    // 不要求未部署的 LLM/VLM 成功推理。
    const bool passed =
        producer.ok() &&
        consumer.ok() &&
        routed >= 2 &&
        routed <= consumer.processedCount() &&
        text_routes >= 1 &&
        vision_routes >= 1 &&
        queue.droppedCount() == 0 &&
        (!use_camera || vision_frame_seen);

    std::cout
        << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
