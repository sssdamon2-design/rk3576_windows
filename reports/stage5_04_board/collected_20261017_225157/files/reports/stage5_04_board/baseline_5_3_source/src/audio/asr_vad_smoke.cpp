
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"

#include <chrono>
#include <iostream>
#include <mutex>
#include <string>
#include <unistd.h>

int main(int argc, char** argv)
{
    if (argc != 4)
    {
        std::cerr
            << "Usage: asr_vad_smoke "
            << "<ALSA device> "
            << "<SenseVoice model directory> "
            << "<Silero VAD model>\n";
        return 2;
    }

    const std::string device = argv[1];
    const std::string model_dir = argv[2];
    const std::string vad_model = argv[3];

    if (::access(vad_model.c_str(), R_OK) != 0)
    {
        std::cerr
            << "VAD model is not readable: "
            << vad_model << '\n';
        return 1;
    }

    std::string error;

    // 1. SenseVoiceSmall 只初始化一次。
    ASRService asr;

    std::cout
        << "Loading SenseVoiceSmall...\n"
        << std::flush;

    if (!asr.initialize(
            model_dir + "/model.int8.onnx",
            model_dir + "/tokens.txt",
            error))
    {
        std::cerr
            << "ASR init failed: "
            << error << '\n';
        return 1;
    }

    std::cout << "ASR initialized\n";

    // 2. 复用操作 7 的有界线程安全队列。
    AudioBufferQueue queue(4);
    std::mutex print_mutex;

    // 3. ASR 消费者线程。
    ASRWorker consumer(
        queue,
        asr,
        print_mutex
    );

    // 4. VAD 生产者线程。
    // 连续监听 20 秒，由 VAD 决定语音段数量。
    constexpr std::size_t kRecordSeconds = 20;

    VadAudioWorker producer(
        device,
        vad_model,
        queue,
        print_mutex,
        kRecordSeconds
    );

    std::cout
        << "Listening for 20 seconds...\n"
        << "Speak 3 short sentences, "
        << "with pauses between them.\n"
        << std::flush;

    const auto start =
        std::chrono::steady_clock::now();

    // 5. 消费者与生产者并发执行。
    consumer.start();
    producer.start();

    producer.join();
    consumer.join();

    const auto end =
        std::chrono::steady_clock::now();

    const double elapsed =
        std::chrono::duration<double>(
            end - start
        ).count();

    const std::size_t detected =
        producer.producedCount();

    const std::size_t recognized =
        consumer.processedCount();

    const std::size_t dropped =
        queue.droppedCount();

    std::cout
        << "\n=== VAD + ASR summary ===\n"
        << "Detected: " << detected << '\n'
        << "Recognized: " << recognized << '\n'
        << "Dropped: " << dropped << '\n'
        << "Wall time: " << elapsed << " s\n";

    if (!producer.ok())
    {
        std::cerr
            << "VAD/AudioCapture error: "
            << producer.error() << '\n';
    }

    if (!consumer.ok())
    {
        std::cerr
            << "ASRWorker error: "
            << consumer.error() << '\n';
    }

    // 至少检测到一段人声，且所有提交的语音都完成识别。
    const bool passed =
        producer.ok() &&
        consumer.ok() &&
        detected >= 1 &&
        detected == recognized &&
        dropped == 0;

    std::cout
        << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
