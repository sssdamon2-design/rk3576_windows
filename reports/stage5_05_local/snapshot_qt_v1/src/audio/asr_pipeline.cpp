
#include "audio/asr_pipeline.h"

#include "audio/asr_service.h"
#include "audio/audio_preprocessor.h"

#include <chrono>
#include <algorithm>
#include <exception>
#include <iostream>
#include <stdexcept>
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
    const auto trace=segment.trace;
    const auto enqueued_at=segment.enqueued_at;
    std::uint64_t dropped_sequence=0;
    bool dropped=false;
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (closed_)
        {
            if(trace)trace->mark("asr_rejected_closed");
            ++stats_.rejected_closed;
            std::cerr << "[Audio queue rejected #" << segment.sequence << "] closed\n";
            return false;
        }

        // 队列满时丢弃最旧的完整音频段。
        if (items_.size() >= capacity_)
        {
            if(items_.front().trace)items_.front().trace->mark("asr_dropped_replaced");
            dropped_sequence=items_.front().sequence;
            dropped=true;
            items_.pop_front();
            ++dropped_;
        }

        items_.push_back(std::move(segment));
        ++stats_.pushed;
        stats_.peak=std::max(stats_.peak,items_.size());
    }
    if(dropped) std::cerr << "[Audio queue dropped #" << dropped_sequence << "] replaced_oldest\n";
    if(trace)trace->mark("asr_enqueued",enqueued_at);

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
    ++stats_.popped;

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

AudioQueueStats AudioBufferQueue::stats() const {
    std::lock_guard<std::mutex> lock(mutex_);
    auto copy=stats_;copy.dropped=dropped_;copy.pending=items_.size();return copy;
}

// ====================================================
// 3. ASRWorker
// ====================================================

ASRWorker::ASRWorker(
    AudioBufferQueue& queue,
    ASRService& asr,
    std::mutex& print_mutex,
    TextCallback on_text,
    ContextCallback on_context)
    : queue_(queue),
      asr_(asr),
      print_mutex_(print_mutex),
      on_text_(std::move(on_text)),
      on_context_(std::move(on_context))
{
}

ASRWorker::~ASRWorker()
{
    // Wake an idle consumer even if producer construction/start failed.
    if (thread_.joinable())
        requestStop();
    join();
}

void ASRWorker::start()
{
    if (started_)
        throw std::logic_error("ASRWorker can only be started once");
    thread_ = std::thread(
        &ASRWorker::run, this
    );
    started_ = true;
}

void ASRWorker::requestStop()
{
    queue_.close();
}

void ASRWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void ASRWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("ASRWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "ASRWorker: unknown exception";
        queue_.close();
    }
}

void ASRWorker::runImpl()
{
    AudioSegment segment;

    while (queue_.pop(segment))
    {
        using Clock = std::chrono::steady_clock;

        // 消费者真正从队列取出音频的时间。
        const auto popped_at = Clock::now();
        RequestTraceScope trace_scope(segment.trace);
        traceMark("asr_dequeued",popped_at);

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
        traceMark("asr_begin",infer_start);

        if (!asr_.recognize(
                samples,
                text,
                latency_ms,
                error))
        {
            traceMark("asr_failed");
            error_ = "ASR: " + error;
            queue_.close();
            return;
        }

        // 获取文字结果的时间。
        const auto result_ready = Clock::now();
        traceMark("asr_end",result_ready);

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

        // ASR 完成后调用业务回调；完整语音入口直接路由，未经过 RequestProcessor。
        // 必须在释放 print_mutex_ 后执行。
        if ((on_text_ || on_context_) && !text.empty())
        {
            try
            {
                if(on_context_)on_context_(text,segment);
                else on_text_(text);
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
        else if(text.empty())traceMark("asr_empty_text");
    }

    ok_ = true;
}
