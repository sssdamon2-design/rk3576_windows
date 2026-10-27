#include <algorithm>

#include "audio/tts_worker.h"

#include <exception>
#include <stdexcept>
#include <utility>

TTSWorker::TTSWorker(
    TTSService& tts,
    AlsaPlaybackService& playback,
    std::size_t capacity)
    : tts_(tts),
      playback_(playback),
      capacity_(capacity)
{
    if (capacity_ == 0)
    {
        throw std::invalid_argument(
            "TTSWorker capacity must be > 0"
        );
    }
}

TTSWorker::~TTSWorker()
{
    requestStop();
    join();
}

bool TTSWorker::start(std::string& error)
{
    std::lock_guard<std::mutex> lock(mutex_);
    error.clear();

    if (started_ || stop_requested_)
    {
        error =
            "TTSWorker can only be started once";
        return false;
    }

    // 两个 Service 必须事先初始化。
    if (!tts_.ready() || !playback_.ready())
    {
        error =
            "Initialize TTSService and ALSA Playback "
            "before starting TTSWorker";
        return false;
    }

    try
    {
        // 启动 TTSWorker::run() 工作线程。
        thread_ = std::thread(
            &TTSWorker::run,
            this
        );

        started_ = true;
    }
    catch (const std::exception& e)
    {
        error =
            std::string(
                "TTSWorker thread creation failed: "
            ) + e.what();

        return false;
    }

    return true;
}

TTSSubmitStatus TTSWorker::submit(
    std::uint64_t id,
    std::string text,
    TTSWorkerDone on_done)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
        {
            return TTSSubmitStatus::NotRunning;
        }

        if (pending_.size() >= capacity_)
        {
            ++rejected_;
            return TTSSubmitStatus::QueueFull;
        }

        Task task;
        task.id = id;
        task.text = std::move(text);
        task.on_done = std::move(on_done);

        task.enqueued_at =
            std::chrono::steady_clock::now();

        pending_.push_back(std::move(task));
        measured_peak_=std::max(measured_peak_,pending_.size());
    }

    // 通知一个等待中的消费者线程。
    cv_.notify_one();

    return TTSSubmitStatus::Accepted;
}

void TTSWorker::requestStop() noexcept
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        stop_requested_ = true;
    }

    // 唤醒线程，让它处理停止请求。
    cv_.notify_all();
}

void TTSWorker::join()
{
    if (thread_.joinable())
    {
        thread_.join();
    }
}

std::size_t TTSWorker::pendingCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return pending_.size();
}

std::size_t TTSWorker::rejectedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return rejected_;
}

void TTSWorker::run()
{
    for (;;)
    {
        Task task;
        bool cancelled = false;

        {
            std::unique_lock<std::mutex> lock(mutex_);

            // 没有任务时休眠，不进行忙轮询。
            cv_.wait(lock, [this] {
                return stop_requested_ ||
                       !pending_.empty();
            });

            // 队列清空且要求停止时，退出线程。
            if (pending_.empty() && stop_requested_)
            {
                return;
            }

            // FIFO：取出队首任务。
            task = std::move(pending_.front());
            pending_.pop_front();

            // 停止请求到来后，
            // 尚未开始的排队任务转为取消结果。
            cancelled = stop_requested_;
        }

        TTSWorkerResult result;

        double queue_wait_ms = -1.0;

        if (cancelled)
        {
            result.error_message =
                "TTS task cancelled: worker stopping";
        }
        else
        {
            // 等待队列的耗时。
            queue_wait_ms =
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() -
                    task.enqueued_at
                ).count();

            try
            {
                TTSAudio audio;
                std::string error;

                // 1. 在工作线程中执行 TTS。
                if (!tts_.synthesize(
                        task.text, audio, error))
                {
                    result.error_message =
                        "TTS synthesize: " + error;
                }
                else if (
                    audio.sample_rate <= 0 ||
                    audio.samples.empty())
                {
                    result.error_message =
                        "TTS returned invalid PCM";
                }
                else
                {
                    result.synthesis_ms =
                        audio.synthesis_ms;

                    result.sample_rate =
                        audio.sample_rate;

                    result.audio_seconds =
                        static_cast<double>(
                            audio.samples.size()
                        ) / audio.sample_rate;

                    // 记录本次播放前的 XRUN 总数。
                    const std::uint64_t xruns_before =
                        playback_.xrunCount();

                    const auto play_start =
                        std::chrono::steady_clock::now();

                    // 2. 在同一工作线程中播放 PCM。
                    const bool played = playback_.play(
                        audio.samples.data(),
                        audio.samples.size(),
                        error
                    );

                    const auto play_end =
                        std::chrono::steady_clock::now();

                    result.playback_ms =
                        std::chrono::duration<
                            double, std::milli
                        >(
                            play_end - play_start
                        ).count();

                    result.xrun_count =
                        playback_.xrunCount() -
                        xruns_before;

                    if (!played)
                    {
                        result.error_message =
                            "ALSA playback: " + error;
                    }
                    else if (result.xrun_count != 0)
                    {
                        result.error_message =
                            "ALSA detected XRUN";
                    }
                    else
                    {
                        result.success = true;
                    }
                }
            }
            catch (const std::exception& e)
            {
                result.error_message =
                    std::string(
                        "TTSWorker exception: "
                    ) + e.what();
            }
            catch (...)
            {
                result.error_message =
                    "TTSWorker: unknown exception";
            }
        }

        // 3. 处理完成或取消后，通知业务层。
        // 不持有 mutex_ 执行用户回调。
        if (task.on_done)
        {
            try
            {
                task.on_done(
                    task.id,
                    result,
                    queue_wait_ms
                );
            }
            catch (...)
            {
                // 回调异常不能杀死工作线程。
            }
        }
    }
}
