
#include "audio/tts_worker.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 6)
    {
        std::cerr
            << "Usage: tts_worker_smoke "
            << "<model_dir> <device> <text> "
            << "<threads> <speaker_id>\n";

        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];
    const std::string text = argv[3];

    int threads = 2;
    int sid = 17;

    try
    {
        const std::string threads_arg = argv[4];
        const std::string sid_arg = argv[5];

        std::size_t n1 = 0;
        std::size_t n2 = 0;

        threads = std::stoi(threads_arg, &n1);
        sid = std::stoi(sid_arg, &n2);

        if (n1 != threads_arg.size() ||
            n2 != sid_arg.size() ||
            threads < 1 ||
            threads > 8 ||
            sid < 0)
        {
            throw std::invalid_argument(
                "Invalid threads or sid"
            );
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "Invalid threads or speaker_id\n";

        return 2;
    }

    std::string error;

    // 先创建并初始化两个 Service。
    TTSService tts;
    AlsaPlaybackService playback;

    std::cout
        << "[Init] Loading TTS model...\n"
        << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            sid))
    {
        std::cerr
            << "[Init] FAIL: "
            << error << '\n';

        return 1;
    }

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() -
            init_start
        ).count();

    std::cout
        << "[Init] OK init_ms="
        << init_ms << '\n';

    // ALSA 使用 TTS 模型的实际采样率。
    if (!playback.open(
            device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[ALSA] Open FAIL: "
            << error << '\n';

        return 1;
    }

    // Worker 最后构造，确保它最先析构。
    TTSWorker worker(tts, playback, 2);

    if (!worker.start(error))
    {
        std::cerr
            << "[Worker] Start FAIL: "
            << error << '\n';

        return 1;
    }

    // 主线程用于接收完成回调的同步变量。
    std::mutex done_mutex;
    std::condition_variable done_cv;

    bool finished = false;

    TTSWorkerResult final_result;
    double queue_wait_ms = -1.0;

    // 提交一个真实 TTS 播放任务。
    const auto status = worker.submit(
        1,
        text,
        [&](std::uint64_t id,
            const TTSWorkerResult& result,
            double queue_ms)
        {
            if (id != 1)
            {
                return;
            }

            {
                std::lock_guard<std::mutex>
                    lock(done_mutex);

                final_result = result;
                queue_wait_ms = queue_ms;
                finished = true;
            }

            done_cv.notify_one();
        }
    );

    if (status != TTSSubmitStatus::Accepted)
    {
        std::cerr
            << "[Main] submit rejected\n";

        worker.requestStop();
        worker.join();

        return 1;
    }

    // 这条日志应在 TTS 合成完成前出现。
    std::cout
        << "[Main] submit accepted; "
        << "main thread remains responsive\n"
        << std::flush;

    // 主线程阻塞等待“完成通知”，
    // 但不负责执行 TTS 推理或音频播放。
    bool completed = false;

    {
        std::unique_lock<std::mutex>
            lock(done_mutex);

        completed = done_cv.wait_for(
            lock,
            std::chrono::seconds(180),
            [&] {
                return finished;
            }
        );
    }

    // 退出前执行安全停止。
    worker.requestStop();
    worker.join();

    if (!completed)
    {
        std::cerr
            << "[Worker] FAIL: completion timeout\n";

        return 1;
    }

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Done] success="
        << std::boolalpha
        << final_result.success
        << " queue_ms=" << queue_wait_ms
        << " synth_ms=" << final_result.synthesis_ms
        << " audio_sec=" << final_result.audio_seconds
        << " playback_ms=" << final_result.playback_ms
        << " xrun_count=" << final_result.xrun_count
        << '\n';

    if (!final_result.success)
    {
        std::cerr
            << "[Done] error="
            << final_result.error_message
            << '\n';

        return 1;
    }

    std::cout << "PASS\n";

    return 0;
}
