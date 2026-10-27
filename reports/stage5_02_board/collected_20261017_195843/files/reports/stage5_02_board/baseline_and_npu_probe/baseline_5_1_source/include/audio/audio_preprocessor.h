
#pragma once

#include <cstdint>
#include <string>
#include <vector>

// 音频预处理：将 16-bit PCM 转换为归一化 Float32。
// 本阶段只接受 16 kHz、单声道输入。
class AudioPreprocessor
{
public:
    static constexpr uint32_t kExpectedSampleRate = 16000;
    static constexpr uint32_t kExpectedChannels = 1;

    static bool convertS16ToFloat32(
        const std::vector<int16_t>& pcm,
        uint32_t sample_rate,
        uint32_t channels,
        std::vector<float>& output,
        std::string& error
    );
};
