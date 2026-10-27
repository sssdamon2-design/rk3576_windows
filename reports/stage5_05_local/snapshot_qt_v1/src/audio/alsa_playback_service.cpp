
#include "audio/alsa_playback_service.h"
#include <alsa/asoundlib.h>

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <new>
#include <string>
#include <vector>
#include "common/request_trace.h"

AlsaPlaybackService::~AlsaPlaybackService()
{
    close();
}

bool AlsaPlaybackService::open(
    const std::string& device,
    std::int32_t sample_rate,
    std::string& error)
{
    close();
    error.clear();

    if (device.empty() || sample_rate <= 0)
    {
        error = "Invalid ALSA device or sample rate";
        return false;
    }

    // 1. 打开阻塞式 ALSA Playback PCM。
    int rc = snd_pcm_open(
        &pcm_,
        device.c_str(),
        SND_PCM_STREAM_PLAYBACK,
        0
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_open: ") +
                snd_strerror(rc);
        pcm_ = nullptr;
        return false;
    }

    // 2. 统一配置硬件和软件参数。
    // soft_resample=1 允许 ALSA 插件进行采样率转换。
    // latency=500000 us，即 500 ms 的目标缓冲延迟。
    rc = snd_pcm_set_params(
        pcm_,
        SND_PCM_FORMAT_S16_LE,
        SND_PCM_ACCESS_RW_INTERLEAVED,
        1,
        static_cast<unsigned int>(sample_rate),
        1,
        500000
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_set_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 3. 查询真正协商出来的 buffer 和 period。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 ||
        buffer_frames < 2 ||
        period_frames == 0)
    {
        error = "Cannot obtain valid ALSA buffer parameters";
        close();
        return false;
    }

    // 4. 设置软件参数。
    snd_pcm_sw_params_t* sw = nullptr;
    snd_pcm_sw_params_alloca(&sw);

    rc = snd_pcm_sw_params_current(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("sw_params_current: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 至少积累一部分音频再启动播放。
    // 阈值不超过缓冲区大小减 1。
    const snd_pcm_uframes_t start_threshold =
        std::min(
            buffer_frames - 1,
            period_frames * 2
        );

    rc = snd_pcm_sw_params_set_start_threshold(
        pcm_,
        sw,
        start_threshold
    );

    if (rc < 0)
    {
        error = std::string("set_start_threshold: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params_set_avail_min(
        pcm_,
        sw,
        period_frames
    );

    if (rc < 0)
    {
        error = std::string("set_avail_min: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("snd_pcm_sw_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    sample_rate_ = sample_rate;
    xrun_count_ = 0;

    std::cout
        << "[ALSA config]"
        << " buffer_frames=" << buffer_frames
        << " period_frames=" << period_frames
        << " start_threshold=" << start_threshold
        << " buffer_ms="
        << (1000.0 * buffer_frames / sample_rate)
        << '\n';

    return true;
}

bool AlsaPlaybackService::play(
    const float* samples,
    std::size_t sample_count,
    std::string& error)
{
    error.clear();

    if (pcm_ == nullptr)
    {
        error = "ALSA device is not initialized";
        return false;
    }

    if (samples == nullptr || sample_count == 0)
    {
        error = "Invalid audio samples";
        return false;
    }

    // 1. 先在内存中完成全部格式转换，
    // 避免播放期间进行耗时的逐样本转换。
    std::vector<std::int16_t> pcm_data;
    traceMark("playback_convert_begin");

    try
    {
        pcm_data.resize(sample_count);
    }
    catch (const std::bad_alloc&)
    {
        error = "Cannot allocate playback PCM buffer";
        return false;
    }

    for (std::size_t i = 0; i < sample_count; ++i)
    {
        float value = samples[i];

        if (!std::isfinite(value))
        {
            value = 0.0f;
        }

        value = std::max(
            -1.0f,
            std::min(1.0f, value)
        );

        const float scale =
            value < 0.0f ? 32768.0f : 32767.0f;

        pcm_data[i] = static_cast<std::int16_t>(
            std::lround(value * scale)
        );
    }

    // 2. 准备播放设备。
    traceMark("playback_convert_end");
    int rc = snd_pcm_prepare(pcm_);

    if (rc < 0)
    {
        error = std::string("snd_pcm_prepare: ") +
                snd_strerror(rc);
        return false;
    }

    // 查询 period，以便按照设备缓冲节奏提交数据。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 || period_frames == 0)
    {
        error = "Cannot query playback period size";
        return false;
    }

    std::size_t offset = 0;
    int consecutive_recoveries = 0;
    int wait_timeouts = 0;
    bool first_submission=true;

    // 3. 持续将音频送入 ALSA。
    while (offset < pcm_data.size())
    {
        const std::size_t remaining =
            pcm_data.size() - offset;

        const snd_pcm_uframes_t frames =
            static_cast<snd_pcm_uframes_t>(
                std::min(
                    remaining,
                    static_cast<std::size_t>(
                        period_frames
                    )
                )
            );

        const auto submit_begin=std::chrono::steady_clock::now();
        const snd_pcm_sframes_t written =
            snd_pcm_writei(
                pcm_,
                pcm_data.data() + offset,
                frames
            );

        if (written > 0)
        {
            if(first_submission){
                traceMark("alsa_first_submit_begin",submit_begin,static_cast<double>(written));
                traceMark("alsa_first_submit_complete",std::chrono::steady_clock::now(),static_cast<double>(written));
                first_submission=false;
            }
            offset += static_cast<std::size_t>(written);

            consecutive_recoveries = 0;
            wait_timeouts = 0;
            continue;
        }

        if (written == -EAGAIN || written == 0)
        {
            const int wait_rc =
                snd_pcm_wait(pcm_, 1000);

            if (wait_rc < 0)
            {
                error = std::string("snd_pcm_wait: ") +
                        snd_strerror(wait_rc);
                return false;
            }

            if (wait_rc == 0)
            {
                if (++wait_timeouts > 5)
                {
                    error = "ALSA wait timeout";
                    return false;
                }
            }

            continue;
        }

        // EPIPE 表示播放缓冲区欠载。
        if (written == -EPIPE)
        {
            ++xrun_count_;

            std::cerr
                << "[ALSA XRUN] write offset="
                << offset
                << " total=" << pcm_data.size()
                << '\n';
        }

        const int recover_rc = snd_pcm_recover(
            pcm_,
            static_cast<int>(written),
            1
        );

        if (recover_rc < 0)
        {
            error = std::string("snd_pcm_recover: ") +
                    snd_strerror(recover_rc);
            return false;
        }

        if (++consecutive_recoveries > 5)
        {
            error = "Too many ALSA recoveries";
            return false;
        }
    }

    // 4. 记录全部数据写入后的 PCM 状态。
    snd_pcm_state_t state = snd_pcm_state(pcm_);

    std::cout
        << "[ALSA write]"
        << " submitted_frames=" << offset
        << " state=" << snd_pcm_state_name(state)
        << '\n';

    // 对短音频：如果还未达到自动启动阈值，
    // 显式启动播放，再进行 drain。
    if (state == SND_PCM_STATE_PREPARED)
    {
        rc = snd_pcm_start(pcm_);

        if (rc < 0)
        {
            error = std::string("snd_pcm_start: ") +
                    snd_strerror(rc);
            return false;
        }
    }

    // 5. 等待 ALSA 将缓冲区中的音频播放完。
    traceMark("alsa_drain_begin");
    rc = snd_pcm_drain(pcm_);

    if (rc < 0)
    {
        if (rc == -EPIPE)
        {
            ++xrun_count_;
        }

        state = snd_pcm_state(pcm_);

        error = std::string("snd_pcm_drain: ") +
                snd_strerror(rc) +
                " state=" +
                snd_pcm_state_name(state);

        return false;
    }

    // XRUN 即使恢复成功，也说明本次播放可能存在断续。
    if (xrun_count_ != 0)
    {
        error = "Playback completed with detected XRUN";
        return false;
    }

    traceMark("alsa_drain_complete");
    return true;
}

void AlsaPlaybackService::close() noexcept
{
    if (pcm_ != nullptr)
    {
        snd_pcm_close(pcm_);
        pcm_ = nullptr;
    }

    sample_rate_ = 0;
    xrun_count_ = 0;
}
