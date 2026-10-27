
#include "audio/audio_capture.h"

#include <cerrno>
#include <limits>

AudioCapture::AudioCapture(const std::string& device)
    : device_(device)
{
}

AudioCapture::~AudioCapture()
{
    close();
}

bool AudioCapture::open(std::string& error)
{
    error.clear();

    if (pcm_ != nullptr)
        return true;

    const int open_result = snd_pcm_open(
        &pcm_,
        device_.c_str(),
        SND_PCM_STREAM_CAPTURE,
        0
    );

    if (open_result < 0)
    {
        error = std::string("snd_pcm_open: ") +
                snd_strerror(open_result);

        pcm_ = nullptr;
        return false;
    }

    // S16_LE、单声道、16000 Hz。
    const int config_result = snd_pcm_set_params(
        pcm_,
        SND_PCM_FORMAT_S16_LE,
        SND_PCM_ACCESS_RW_INTERLEAVED,
        1,
        16000,
        1,
        100000
    );

    if (config_result < 0)
    {
        error = std::string("snd_pcm_set_params: ") +
                snd_strerror(config_result);

        close();
        return false;
    }

    stats_ = {};
    return true;
}

bool AudioCapture::readFrames(
    std::vector<std::int16_t>& samples,
    std::size_t frame_count,
    std::string& error)
{
    error.clear();
    samples.clear();

    if (!pcm_)
    {
        error = "Audio device is not open";
        return false;
    }

    if (frame_count == 0 ||
        frame_count >
            std::numeric_limits<snd_pcm_uframes_t>::max())
    {
        error = "Invalid frame count";
        return false;
    }

    samples.resize(frame_count);

    std::size_t total = 0;
    int consecutive_errors = 0;
    int consecutive_zero_reads = 0;

    while (total < frame_count)
    {
        const snd_pcm_sframes_t result =
            snd_pcm_readi(
                pcm_,
                samples.data() + total,
                static_cast<snd_pcm_uframes_t>(
                    frame_count - total
                )
            );

        if (result > 0)
        {
            total += static_cast<std::size_t>(result);

            consecutive_errors = 0;
            consecutive_zero_reads = 0;
            continue;
        }

        // 被信号中断时直接重试。
        if (result == -EINTR)
            continue;

        if (result == 0)
        {
            if (++consecutive_zero_reads <= 3)
                continue;

            error = "ALSA returned zero frames repeatedly";

            samples.clear();
            return false;
        }

        // 对于 Capture，-EPIPE 通常意味着 Overrun。
        if (result == -EPIPE)
            ++stats_.xrun_count;

        // ALSA PCM 设备被挂起。
        if (result == -ESTRPIPE)
            ++stats_.suspend_count;

        if (++consecutive_errors > 3)
        {
            error =
                std::string("Too many consecutive ALSA errors: ") +
                snd_strerror(static_cast<int>(result));

            samples.clear();
            return false;
        }

        // 尝试恢复错误状态，维持采集。
        const int recovery = snd_pcm_recover(
            pcm_,
            static_cast<int>(result),
            1
        );

        if (recovery < 0)
        {
            ++stats_.recovery_failures;

            error = std::string("snd_pcm_recover: ") +
                    snd_strerror(recovery);

            samples.clear();
            return false;
        }

        ++stats_.recovered_errors;
        consecutive_zero_reads = 0;
    }

    return true;
}

void AudioCapture::close() noexcept
{
    if (pcm_)
    {
        snd_pcm_close(pcm_);
        pcm_ = nullptr;
    }
}

