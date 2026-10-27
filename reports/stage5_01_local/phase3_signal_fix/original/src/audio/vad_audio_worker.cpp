
#include "audio/vad_audio_worker.h"

#include "audio/audio_capture.h"
#include "audio/audio_preprocessor.h"

#include <sherpa-onnx/c-api/c-api.h>

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <deque>
#include <exception>
#include <iostream>
#include <stdexcept>
#include <memory>
#include <utility>
#include <vector>

VadAudioWorker::VadAudioWorker(
    std::string device,
    std::string vad_model,
    AudioBufferQueue& queue,
    std::mutex& print_mutex,
    std::size_t record_seconds)
    : device_(std::move(device)),
      vad_model_(std::move(vad_model)),
      queue_(queue),
      print_mutex_(print_mutex),
      record_seconds_(record_seconds)
{
}

VadAudioWorker::~VadAudioWorker()
{
    requestStop();
    join();
}

void VadAudioWorker::start()
{
    if (started_)
        throw std::logic_error("VadAudioWorker can only be started once");
    thread_ = std::thread(
        &VadAudioWorker::run, this
    );
    started_ = true;
}

void VadAudioWorker::requestStop() noexcept
{
    stop_requested_.store(true);
}

void VadAudioWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

void VadAudioWorker::run()
{
    try
    {
        runImpl();
    }
    catch (const std::exception& e)
    {
        ok_ = false;
        error_ = std::string("VadAudioWorker exception: ") + e.what();
        queue_.close();
    }
    catch (...)
    {
        ok_ = false;
        error_ = "VadAudioWorker: unknown exception";
        queue_.close();
    }
}

void VadAudioWorker::runImpl()
{
    // 生产者结束时关闭队列，唤醒消费者。
    struct QueueCloser {
        AudioBufferQueue& queue;

        ~QueueCloser() {
            queue.close();
        }
    } closer{queue_};

    // ==================================================
    // 1. 初始化 Silero VAD
    // ==================================================

    SherpaOnnxVadModelConfig config{};

    config.silero_vad.model =
        vad_model_.c_str();

    config.silero_vad.threshold = 0.50f;
    config.silero_vad.min_silence_duration = 0.60f;
    config.silero_vad.min_speech_duration = 0.25f;
    config.silero_vad.max_speech_duration = 8.0f;
    config.silero_vad.window_size = 512;

    config.sample_rate = 16000;
    config.num_threads = 1;
    config.provider = "cpu";

    using VadPtr = std::unique_ptr<
        const SherpaOnnxVoiceActivityDetector,
        decltype(
            &SherpaOnnxDestroyVoiceActivityDetector
        )
    >;

    VadPtr vad(
        SherpaOnnxCreateVoiceActivityDetector(
            &config,
            30.0f
        ),
        &SherpaOnnxDestroyVoiceActivityDetector
    );

    if (!vad)
    {
        error_ = "Failed to initialize Silero VAD";
        return;
    }

    // ==================================================
    // 2. ALSA 初始化和异常计数
    // ==================================================

    AudioCapture capture(device_);

    // 退出采集线程时，自动打印异常统计。
    // capture 对象在这个 RAII 结构析构期间仍有效。
    struct CaptureStatsPrinter {
        AudioCapture& capture;
        std::mutex& print_mutex;

        ~CaptureStatsPrinter()
        {
            const auto s = capture.stats();

            std::lock_guard<std::mutex> lock(
                print_mutex
            );

            std::cout
                << "[ALSA] XRUN="
                << s.xrun_count

                << " Suspends="
                << s.suspend_count

                << " Recoveries="
                << s.recovered_errors

                << " RecoveryFailures="
                << s.recovery_failures

                << '\n'
                << std::flush;
        }
    } stats_printer{capture, print_mutex_};

    if (!capture.open(error_))
        return;

    constexpr std::size_t kSampleRate = 16000;
    constexpr std::size_t kChunkFrames = 320;
    constexpr std::size_t kWindowFrames = 512;

    constexpr std::size_t kHistoryCapacity =
        kSampleRate * 15;

    constexpr std::int64_t kPreRollSamples = 3200;

    std::deque<float> history;

    std::int64_t captured_samples = 0;

    // 用采集块读取完成时的主机时钟，
    // 估算某个样本对应的时间。
    //
    // 这不是 ALSA 硬件时间戳。
    using Clock = std::chrono::steady_clock;

    Clock::time_point latest_read_completed_at{};

    std::int64_t latest_read_end_sample = 0;

    // VAD 接受 512 Samples 的窗口。
    std::array<float, kWindowFrames> window{};

    std::size_t filled = 0;

    std::vector<std::int16_t> chunk;
    std::vector<float> float_chunk;

    // ==================================================
    // 3. 从 VAD 中提取完整语音段
    // ==================================================

    auto drain_segments = [&]() -> bool
    {
        while (!SherpaOnnxVoiceActivityDetectorEmpty(
                   vad.get()))
        {
            using SpeechPtr = std::unique_ptr<
                const SherpaOnnxSpeechSegment,
                decltype(
                    &SherpaOnnxDestroySpeechSegment
                )
            >;

            SpeechPtr speech(
                SherpaOnnxVoiceActivityDetectorFront(
                    vad.get()
                ),
                &SherpaOnnxDestroySpeechSegment
            );

            if (!speech ||
                speech->n <= 0 ||
                speech->samples == nullptr)
            {
                error_ = "Invalid VAD speech segment";
                return false;
            }

            AudioSegment segment;
            segment.sequence = produced_ + 1;

            // VAD 语音段在整条音频流中的起始采样索引。
            const std::int64_t speech_start =
                std::max<std::int64_t>(
                    0,
                    speech->start
                );

            // 历史缓存的起始样本位置。
            const std::int64_t history_start =
                captured_samples -
                static_cast<std::int64_t>(
                    history.size()
                );

            // 最多增加 200 ms 前导音频。
            const std::int64_t prefix_start =
                std::max(
                    history_start,
                    std::max<std::int64_t>(
                        0,
                        speech_start - kPreRollSamples
                    )
                );

            const std::int64_t prefix_end =
                std::min(
                    speech_start,
                    captured_samples
                );

            for (std::int64_t pos = prefix_start;
                 pos < prefix_end;
                 ++pos)
            {
                segment.samples.push_back(
                    history[
                        static_cast<std::size_t>(
                            pos - history_start
                        )
                    ]
                );
            }

            // 拼接完整的 VAD 语音段。
            segment.samples.insert(
                segment.samples.end(),
                speech->samples,
                speech->samples + speech->n
            );

            const double duration =
                static_cast<double>(
                    segment.samples.size()
                ) / kSampleRate;

            // ==================================================
            // 4. 计算音频段末尾的估算时间戳
            // ==================================================

            // VAD 返回音频段的末尾采样点。
            // 不包含额外附加的 pre-roll。
            const std::int64_t audio_end_index =
                speech->start +
                static_cast<std::int64_t>(
                    speech->n
                );

            const auto captured_stats =
                capture.stats();

            // 出现可观察的 XRUN / 挂起时，
            // 采样索引与时间之间可能出现不连续，
            // 此时不输出可能误导的时间估算。
            if (
                latest_read_completed_at !=
                    Clock::time_point{} &&

                audio_end_index >= 0 &&

                audio_end_index <=
                    latest_read_end_sample &&

                captured_stats.xrun_count == 0 &&

                captured_stats.suspend_count == 0
            )
            {
                const double seconds_ago =
                    static_cast<double>(
                        latest_read_end_sample -
                        audio_end_index
                    ) /
                    static_cast<double>(
                        kSampleRate
                    );

                segment.audio_end_estimated_at =
                    latest_read_completed_at -
                    std::chrono::duration_cast<
                        Clock::duration
                    >(
                        std::chrono::duration<double>(
                            seconds_ago
                        )
                    );

                segment.timing_valid = true;
            }

            // 完整语音已复制，可以从 VAD 内部删除。
            SherpaOnnxVoiceActivityDetectorPop(
                vad.get()
            );

            const auto sequence = segment.sequence;

            // VAD 完成语音段处理的时刻。
            segment.vad_ready_at = Clock::now();

            // 准备送入队列的时刻。
            segment.enqueued_at = Clock::now();

            if (!queue_.push(std::move(segment)))
            {
                error_ = "Audio queue was closed";
                return false;
            }

            ++produced_;

            {
                std::lock_guard<std::mutex> lock(
                    print_mutex_
                );

                std::cout
                    << "[VAD] Speech #"
                    << sequence
                    << " duration="
                    << duration
                    << " s\n"
                    << std::flush;
            }
        }

        return true;
    };

    // ==================================================
    // 5. 连续读取 ALSA 数据
    // ==================================================

    const std::size_t total_chunks =
        record_seconds_ *
        kSampleRate /
        kChunkFrames;

    for (
        std::size_t i = 0;

        i < total_chunks &&
        !stop_requested_.load();

        ++i
    )
    {
        chunk.clear();

        if (!capture.readFrames(
                chunk,
                kChunkFrames,
                error_))
        {
            return;
        }

        if (chunk.size() != kChunkFrames)
        {
            error_ = "Unexpected short ALSA chunk";
            return;
        }

        // ALSA 当前块读取完成，记录主机时间。
        // 每块为 320 / 16000 = 20 ms。
        latest_read_completed_at =
            Clock::now();

        latest_read_end_sample =
            captured_samples +
            static_cast<std::int64_t>(
                chunk.size()
            );

        // S16_LE PCM 转 Float32。
        if (!AudioPreprocessor::convertS16ToFloat32(
                chunk,
                16000,
                1,
                float_chunk,
                error_))
        {
            return;
        }

        for (float sample : float_chunk)
        {
            // 保留历史音频用于前导补偿。
            history.push_back(sample);
            ++captured_samples;

            if (history.size() > kHistoryCapacity)
                history.pop_front();

            // 重组成 512 Samples 的 VAD 窗口。
            window[filled++] = sample;

            if (filled == kWindowFrames)
            {
                SherpaOnnxVoiceActivityDetectorAcceptWaveform(
                    vad.get(),
                    window.data(),
                    static_cast<std::int32_t>(
                        kWindowFrames
                    )
                );

                filled = 0;

                if (!drain_segments())
                    return;
            }
        }
    }

    // ==================================================
    // 6. 结束采集并 Flush VAD
    // ==================================================

    if (filled != 0)
    {
        // 不足 512 Samples 的窗口补零。
        std::fill(
            window.begin() + filled,
            window.end(),
            0.0f
        );

        SherpaOnnxVoiceActivityDetectorAcceptWaveform(
            vad.get(),
            window.data(),
            static_cast<std::int32_t>(
                kWindowFrames
            )
        );
    }

    SherpaOnnxVoiceActivityDetectorFlush(
        vad.get()
    );

    if (!drain_segments())
        return;

    ok_ = !stop_requested_.load();
}
