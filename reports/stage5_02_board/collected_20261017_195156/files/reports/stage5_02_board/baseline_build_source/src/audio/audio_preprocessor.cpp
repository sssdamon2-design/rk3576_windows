
#include "audio/audio_preprocessor.h"

#include <cstddef>

bool AudioPreprocessor::convertS16ToFloat32(
    const std::vector<int16_t>& pcm,
    uint32_t sample_rate,
    uint32_t channels,
    std::vector<float>& output,
    std::string& error)
{
    // 每次调用前清空上一轮结果。
    error.clear();
    output.clear();

    // 1. 检查采样率。
    if (sample_rate != kExpectedSampleRate)
    {
        error = "Expected 16000 Hz audio; "
                "resampling is not implemented";
        return false;
    }

    // 2. 检查声道数。
    if (channels != kExpectedChannels)
    {
        error = "Expected mono audio; "
                "channel mixing is not implemented";
        return false;
    }

    // 3. 禁止空音频输入。
    if (pcm.empty())
    {
        error = "PCM buffer is empty";
        return false;
    }

    // 4. 为输出分配与输入相同数量的样本。
    output.resize(pcm.size());

    // 5. S16 -> Float32 幅值归一化。
    for (std::size_t i = 0; i < pcm.size(); ++i)
    {
        output[i] =
            static_cast<float>(pcm[i]) / 32768.0f;
    }

    return true;
}
