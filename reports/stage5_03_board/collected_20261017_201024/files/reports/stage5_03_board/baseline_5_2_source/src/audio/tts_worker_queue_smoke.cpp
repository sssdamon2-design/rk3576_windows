
#include "audio/tts_worker.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>

int main(int argc, char** argv)
{
    if (argc != 5)
    {
        std::cerr
            << "Usage: tts_worker_queue_smoke "
            << "<model_dir> <device> <threads> <sid>\n";
        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];

    int threads = 2;
    int sid = 17;

    try
    {
        std::size_t n1 = 0;
        std::size_t n2 = 0;

        const std::string arg_threads = argv[3];
        const std::string arg_sid = argv[4];

        threads = std::stoi(arg_threads, &n1);
        sid = std::stoi(arg_sid, &n2);

        if (n1 != arg_threads.size() ||
            n2 != arg_sid.size() ||
            threads < 1 || threads > 8 ||
            sid < 0)
        {
            throw std::invalid_argument("invalid argument");
        }
    }
    catch (const std::exception&)
    {
        std::cerr << "[Args] Invalid threads or sid\n";
        return 2;
    }

    TTSService tts;
    AlsaPlaybackService playback;
    std::string error;

    std::cout << "[Init] Loading Kokoro...\n"
              << std::flush;

    if (!tts.initialize(model_dir, error, threads, sid))
    {
        std::cerr << "[Init] FAIL: " << error << '\n';
        return 1;
    }

    if (!playback.open(device, tts.sampleRate(), error))
    {
        std::cerr << "[ALSA] FAIL: " << error << '\n';
        return 1;
    }

    std::mutex done_mutex;
    std::condition_variable done_cv;

    bool first_done = false;
    bool second_done = false;

    TTSWorkerResult first_result;
    TTSWorkerResult second_result;

    // 只允许一个等待任务。
    TTSWorker worker(tts, playback, 1);

    if (!worker.start(error))
    {
        std::cerr << "[Worker] FAIL: " << error << '\n';
        return 1;
    }

    // 第一个任务：应当正常执行并播放。
    const auto s1 = worker.submit(
        101,
        "你好，我是你的智能语音助手。",
        [&](std::uint64_t,
            const TTSWorkerResult& result,
            double)
        {
            {
                std::lock_guard<std::mutex> lock(done_mutex);
                first_result = result;
                first_done = true;
            }
            done_cv.notify_all();
        }
    );

    if (s1 != TTSSubmitStatus::Accepted)
    {
        std::cerr << "[Task 101] Not accepted\n";
        worker.requestStop();
        worker.join();
        return 1;
    }

    // 等待 Task 101 从 FIFO 取出。
    // 此时它正在执行或即将执行，等待队列为空。
    bool dequeued = false;

    for (int i = 0; i < 200; ++i)
    {
        if (worker.pendingCount() == 0)
        {
            dequeued = true;
            break;
        }

        std::this_thread::sleep_for(
            std::chrono::milliseconds(10)
        );
    }

    if (!dequeued)
    {
        std::cerr << "[Test] Task 101 not dequeued\n";
        worker.requestStop();
        worker.join();
        return 1;
    }

    // 第二个任务：应该进入唯一的等待位置。
    const auto s2 = worker.submit(
        102,
        "这个排队任务应该被取消。",
        [&](std::uint64_t,
            const TTSWorkerResult& result,
            double)
        {
            {
                std::lock_guard<std::mutex> lock(done_mutex);
                second_result = result;
                second_done = true;
            }
            done_cv.notify_all();
        }
    );

    // 第三个任务：队列已满，应该被拒绝。
    const auto s3 = worker.submit(
        103,
        "这条任务不应该进入队列。"
    );

    std::cout
        << "[Queue] task101=Accepted"
        << " task102="
        << (s2 == TTSSubmitStatus::Accepted
                ? "Accepted" : "Unexpected")
        << " task103="
        << (s3 == TTSSubmitStatus::QueueFull
                ? "QueueFull" : "Unexpected")
        << " pending=" << worker.pendingCount()
        << '\n'
        << std::flush;

    // 请求停止：Task 101 自然完成，
    // Task 102 应报告取消。
    worker.requestStop();

    // 停止后的新任务必须被拒绝。
    const auto s4 = worker.submit(
        104,
        "停止后不能接受这条任务。"
    );

    std::cout
        << "[Stop] task104="
        << (s4 == TTSSubmitStatus::NotRunning
                ? "NotRunning" : "Unexpected")
        << '\n'
        << std::flush;

    // 等待两个被接受任务的完成/取消回调。
    bool callbacks_received = false;

    {
        std::unique_lock<std::mutex> lock(done_mutex);

        callbacks_received = done_cv.wait_for(
            lock,
            std::chrono::seconds(120),
            [&] {
                return first_done && second_done;
            }
        );
    }

    worker.join();

    const bool first_ok =
        first_done && first_result.success;

    const bool cancelled_ok =
        second_done &&
        !second_result.success &&
        second_result.error_message.find("cancelled") !=
            std::string::npos;

    const bool queue_ok =
        s2 == TTSSubmitStatus::Accepted &&
        s3 == TTSSubmitStatus::QueueFull &&
        s4 == TTSSubmitStatus::NotRunning &&
        worker.rejectedCount() == 1;

    std::cout
        << std::boolalpha
        << "[Result] callbacks=" << callbacks_received
        << " first_success=" << first_ok
        << " second_cancelled=" << cancelled_ok
        << " rejected_count=" << worker.rejectedCount()
        << '\n';

    if (!callbacks_received ||
        !first_ok ||
        !cancelled_ok ||
        !queue_ok)
    {
        std::cerr << "FAIL\n";
        return 1;
    }

    std::cout << "PASS\n";
    return 0;
}
