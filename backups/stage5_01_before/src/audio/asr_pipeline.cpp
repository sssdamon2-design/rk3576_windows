
#include "audio/asr_pipeline.h"

#include "audio/asr_service.h"
#include "audio/audio_capture.h"
#include "audio/audio_preprocessor.h"

#include <chrono>
#include <exception>
#include <iostream>
#include <utility>

// ====================================================
// 1. AudioBufferQueue
// ====================================================

AudioBufferQueue::AudioBufferQueue(std::size_t capacity)
    : capacity_(capacity == 0 ? 1 : capacity)
{
}

bool AudioBufferQueue::push(AudioSegment segment)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (closed_)
            return false;

        // 队列满时丢弃最旧的完整音频段。
        if (items_.size() >= capacity_)
        {
            items_.pop_front();
            ++dropped_;
        }

        items_.push_back(std::move(segment));
    }

    cv_.notify_one();
    return true;
}

bool AudioBufferQueue::pop(AudioSegment& segment)
{
    std::unique_lock<std::mutex> lock(mutex_);

    cv_.wait(lock, [this] {
        return closed_ || !items_.empty();
    });

    if (items_.empty())
        return false;

    segment = std::move(items_.front());
    items_.pop_front();

    return true;
}

void AudioBufferQueue::close()
{
    {
        std::lock_guard<std::mutex> lock(mutex_);
        closed_ = true;
    }

    cv_.notify_all();
}

std::size_t AudioBufferQueue::droppedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return dropped_;
}

// ====================================================
// 2. AudioWorker
// ====================================================

AudioWorker::AudioWorker(
    std::string device,
    AudioBufferQueue& queue,
    std::mutex& print_mutex,
    std::size_t segment_count)
    : device_(std::move(device)),
      queue_(queue),
      print_mutex_(print_mutex),
      segment_count_(segment_count)
{
}

AudioWorker::~AudioWorker()
{
    requestStop();
    join();
}

void AudioWorker::start()
{
    thread_ = std::thread(
        &AudioWorker::run, this
    );
}

void AudioWorker::requestStop() noexcept
{
    stop_requested_.store(true);
}

void AudioWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void AudioWorker::run()
{
    struct QueueCloser {
        AudioBufferQueue& queue;

        ~QueueCloser() {
            queue.close();
        }
    } closer{queue_};

    AudioCapture capture(device_);

    if (!capture.open(error_))
        return;

    constexpr std::size_t kFramesPerRead = 320;
    constexpr std::size_t kReadsPerSegment = 250;

    constexpr std::size_t kFramesPerSegment =
        kFramesPerRead * kReadsPerSegment;

    std::vector<std::int16_t> chunk;

    for (std::size_t id = 1;
         id <= segment_count_ &&
         !stop_requested_.load();
         ++id)
    {
        {
            std::lock_guard<std::mutex> lock(
                print_mutex_
            );

            std::cout
                << "[Capture] Recording #"
                << id
                << " (5 seconds)...\n"
                << std::flush;
        }

        AudioSegment segment;
        segment.sequence = id;

        segment.pcm.reserve(kFramesPerSegment);

        for (std::size_t i = 0;
             i < kReadsPerSegment;
             ++i)
        {
            if (stop_requested_.load())
                break;

            chunk.clear();

            if (!capture.readFrames(
                    chunk,
                    kFramesPerRead,
                    error_))
            {
                return;
            }

            if (chunk.size() != kFramesPerRead)
            {
                error_ = "Unexpected short ALSA chunk";
                return;
            }

            segment.pcm.insert(
                segment.pcm.end(),
                chunk.begin(),
                chunk.end()
            );
        }

        if (stop_requested_.load())
            break;

        if (!queue_.push(std::move(segment)))
        {
            error_ = "Audio queue was closed";
            return;
        }

        ++produced_;
    }

    ok_ = true;
}

// ====================================================
// 3. ASRWorker
// ====================================================

ASRWorker::ASRWorker(
    AudioBufferQueue& queue,
    ASRService& asr,
    std::mutex& print_mutex,
    TextCallback on_text)
    : queue_(queue),
      asr_(asr),
      print_mutex_(print_mutex),
      on_text_(std::move(on_text))
{
}

ASRWorker::~ASRWorker()
{
    join();
}

void ASRWorker::start()
{
    thread_ = std::thread(
        &ASRWorker::run, this
    );
}

void ASRWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void ASRWorker::run()
{
    AudioSegment segment;

    while (queue_.pop(segment))
    {
        using Clock = std::chrono::steady_clock;

        // 消费者真正从队列取出音频的时间。
        const auto popped_at = Clock::now();

        std::vector<float> samples;
        std::string error;

        if (!segment.samples.empty())
        {
            // VAD 已输出 Float32，直接移动。
            samples = std::move(segment.samples);
        }
        else
        {
            // 兼容原始 S16_LE 录音流水线。
            if (!AudioPreprocessor::convertS16ToFloat32(
                    segment.pcm,
                    16000,
                    1,
                    samples,
                    error))
            {
                error_ = "Preprocessing: " + error;
                queue_.close();
                return;
            }
        }

        if (samples.empty())
        {
            error_ = "Empty ASR audio segment";
            queue_.close();
            return;
        }

        std::string text;
        double latency_ms = 0.0;

        // 推理开始时间。
        const auto infer_start = Clock::now();

        if (!asr_.recognize(
                samples,
                text,
                latency_ms,
                error))
        {
            error_ = "ASR: " + error;
            queue_.close();
            return;
        }

        // 获取文字结果的时间。
        const auto result_ready = Clock::now();

        ++processed_;

        const double audio_duration_ms =
            1000.0 *
            static_cast<double>(samples.size()) /
            16000.0;

        const double rtf =
            latency_ms / audio_duration_ms;

        // 统一使用 steady_clock 时间差。
        auto elapsed_ms = [](
            Clock::time_point first,
            Clock::time_point second)
        {
            return std::chrono::duration<
                double, std::milli
            >(second - first).count();
        };

        {
            std::lock_guard<std::mutex> lock(
                print_mutex_
            );

            // 原始 ASR 输出格式保持不变。
            std::cout
                << "[ASR] Segment #"
                << segment.sequence
                << ": "
                << (text.empty() ? "<empty>" : text)
                << " | latency="
                << latency_ms
                << " ms"
                << " | RTF="
                << rtf
                << '\n';

            // 仅对来自 VAD 的有效时间戳计算。
            if (segment.timing_valid)
            {
                std::cout
                    << "[Timing] Segment #"
                    << segment.sequence

                    << " endpoint_est_ms="
                    << elapsed_ms(
                        segment.audio_end_estimated_at,
                        segment.vad_ready_at
                    )

                    << " vad_to_queue_ms="
                    << elapsed_ms(
                        segment.vad_ready_at,
                        segment.enqueued_at
                    )

                    << " queue_wait_ms="
                    << elapsed_ms(
                        segment.enqueued_at,
                        popped_at
                    )

                    << " preprocess_ms="
                    << elapsed_ms(
                        popped_at,
                        infer_start
                    )

                    << " asr_wall_ms="
                    << elapsed_ms(
                        infer_start,
                        result_ready
                    )

                    << " total_est_ms="
                    << elapsed_ms(
                        segment.audio_end_estimated_at,
                        result_ready
                    )

                    << '\n';
            }
        }

        // ASR 完成后回调 RequestProcessor。
        // 必须在释放 print_mutex_ 后执行。
        if (on_text_ && !text.empty())
        {
            try
            {
                on_text_(text);
            }
            catch (const std::exception& e)
            {
                error_ =
                    std::string("ASR text callback: ") +
                    e.what();

                queue_.close();
                return;
            }
            catch (...)
            {
                error_ =
                    "ASR text callback: unknown exception";

                queue_.close();
                return;
            }
        }
    }

    ok_ = true;
}
