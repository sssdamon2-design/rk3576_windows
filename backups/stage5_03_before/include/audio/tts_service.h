
#pragma once

#include <cstdint>
#include <string>
#include <vector>

struct SherpaOnnxOfflineTts;

struct TTSAudio
{
    std::vector<float> samples;
    std::int32_t sample_rate = 0;
    double synthesis_ms = 0.0;
};

class TTSService
{
public:
    TTSService() = default;
    ~TTSService();

    TTSService(const TTSService&) = delete;
    TTSService& operator=(const TTSService&) = delete;
    TTSService(TTSService&&) = delete;
    TTSService& operator=(TTSService&&) = delete;

    // 新增 speaker_id，默认 0，保持旧调用兼容。
    bool initialize(
        const std::string& model_dir,
        std::string& error,
        std::int32_t num_threads = 2,
        std::int32_t speaker_id = 0
    );

    bool synthesize(
        const std::string& text,
        TTSAudio& output,
        std::string& error
    );

    void shutdown() noexcept;

    bool ready() const noexcept
    {
        return tts_ != nullptr;
    }

    std::int32_t sampleRate() const noexcept;
    std::int32_t numSpeakers() const noexcept;

    std::int32_t speakerId() const noexcept
    {
        return speaker_id_;
    }

private:
    // 当前实例所使用的 sherpa-onnx TTS 对象。
    const SherpaOnnxOfflineTts* tts_ = nullptr;

    // 本次初始化选中的音色编号。
    std::int32_t speaker_id_ = 0;
};
