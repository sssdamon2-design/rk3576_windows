
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"

#include <chrono>
#include <iostream>
#include <mutex>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 3)
    {
        std::cerr
            << "Usage: asr_pipeline_smoke "
            << "<ALSA device> <model directory>\n";
        return 2;
    }

    const std::string device = argv[1];
    const std::string dir = argv[2];

    std::string error;
    ASRService asr;

    // 1. 只加载一次 SenseVoiceSmall。
    std::cout << "Loading model once...\n"
              << std::flush;

    if (!asr.initialize(
            dir + "/model.int8.onnx",
            dir + "/tokens.txt",
            error))
    {
        std::cerr
            << "ASR init failed: "
            << error << '\n';
        return 1;
    }

    // 2. 共录制 4 段，每段 5 秒。
    constexpr std::size_t kSegments = 4;

    // 队列最多缓存两个完整音频段。
    AudioBufferQueue queue(2);

    // 两个线程打印日志时共用一把锁。
    std::mutex print_mutex;

    // 3. 创建消费者和生产者。
    ASRWorker consumer(
        queue,
        asr,
        print_mutex
    );

    AudioWorker producer(
        device,
        queue,
        print_mutex,
        kSegments
    );

    std::cout
        << "Record four 5-second segments.\n"
        << "Say one short phrase during each window.\n";

    // 4. 记录整个并行流水线的开始时间。
    const auto begin =
        std::chrono::steady_clock::now();

    // 5. 启动两个线程。
    consumer.start();
    producer.start();

    // 6. 等待采集线程结束。
    producer.join();

    // 采集线程结束时会关闭队列，
    // 消费者处理完剩余音频后自动退出。
    consumer.join();

    const auto end =
        std::chrono::steady_clock::now();

    const double elapsed =
        std::chrono::duration<double>(
            end - begin
        ).count();

    // 7. 输出最终统计。
    std::cout
        << "\n=== Pipeline summary ===\n"
        << "Produced: "
        << producer.producedCount() << '\n'
        << "Recognized: "
        << consumer.processedCount() << '\n'
        << "Dropped: "
        << queue.droppedCount() << '\n'
        << "Wall time: "
        << elapsed << " s\n";

    if (!producer.ok())
    {
        std::cerr
            << "Capture error: "
            << producer.error() << '\n';
    }

    if (!consumer.ok())
    {
        std::cerr
            << "ASR error: "
            << consumer.error() << '\n';
    }

    // 8. 检查四段音频是否完整处理。
    const bool complete =
        producer.ok() &&
        consumer.ok() &&
        producer.producedCount() == kSegments &&
        consumer.processedCount() == kSegments &&
        queue.droppedCount() == 0;

    std::cout
        << (complete ? "PASS\n" : "FAIL\n");

    return complete ? 0 : 1;
}
