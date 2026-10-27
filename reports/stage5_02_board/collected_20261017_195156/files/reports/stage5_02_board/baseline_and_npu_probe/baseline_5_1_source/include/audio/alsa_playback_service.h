
#pragma once

#include <alsa/asoundlib.h>

#include <cstddef>
#include <cstdint>
#include <string>

// 阻塞式 ALSA 音频播放服务。
// 输入 float PCM，内部转换成 S16_LE。
// 3.3 阶段仅在一个线程中使用，不支持并发调用。
class AlsaPlaybackService
{
public:
    AlsaPlaybackService() = default;
    ~AlsaPlaybackService();

    // ALSA PCM 句柄不可复制。
    AlsaPlaybackService(const AlsaPlaybackService&) = delete;
    AlsaPlaybackService& operator=(const AlsaPlaybackService&) = delete;

    // 初始化声卡和 PCM 播放参数。
    bool open(
        const std::string& device,
        std::int32_t sample_rate,
        std::string& error
    );

    // 播放单声道 float PCM。
    // 本函数阻塞，直到音频播放完成或出错。
    bool play(
        const float* samples,
        std::size_t sample_count,
        std::string& error
    );

    // 关闭设备并释放资源。
    void close() noexcept;

    bool ready() const noexcept
    {
        return pcm_ != nullptr;
    }

    std::uint64_t xrunCount() const noexcept
    {
        return xrun_count_;
    }

private:
    // ALSA PCM 设备句柄。
    snd_pcm_t* pcm_ = nullptr;

    // 当前配置的采样率。
    std::int32_t sample_rate_ = 0;

    // Playback 发生缓冲区欠载的次数。
    std::uint64_t xrun_count_ = 0;
};
