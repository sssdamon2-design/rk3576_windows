
#pragma once

#include <alsa/asoundlib.h>

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

// 单声道 16 kHz / S16_LE ALSA 采集器。
// 该类非线程安全：open/readFrames/stats/close 应在同一采集线程使用。
class AudioCapture {
public:
    struct Stats {
        std::uint64_t xrun_count = 0;
        std::uint64_t suspend_count = 0;
        std::uint64_t recovered_errors = 0;
        std::uint64_t recovery_failures = 0;
    };

    explicit AudioCapture(const std::string& device);
    ~AudioCapture();

    AudioCapture(const AudioCapture&) = delete;
    AudioCapture& operator=(const AudioCapture&) = delete;

    bool open(std::string& error);

    bool readFrames(
        std::vector<std::int16_t>& samples,
        std::size_t frame_count,
        std::string& error
    );

    void close() noexcept;

    // 仅在采集线程内读取。
    Stats stats() const noexcept {
        return stats_;
    }

private:
    std::string device_;
    snd_pcm_t* pcm_ = nullptr;
    Stats stats_{};
};
