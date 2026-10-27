
#include "audio/audio_preprocessor.h"

#include <cmath>
#include <iostream>
#include <string>
#include <vector>

bool expect(bool ok, const char* label)
{
    if (!ok)
        std::cerr << "FAIL: " << label << '\n';

    return ok;
}

int main()
{
    bool all_passed = true;
    std::string error;

    // 测试 1：正常的 16-bit PCM 数据。
    std::vector<int16_t> input{
        -32768, -16384, 0, 16384, 32767
    };

    std::vector<float> output;

    bool success =
        AudioPreprocessor::convertS16ToFloat32(
            input, 16000, 1, output, error
        );

    all_passed &= expect(
        success && error.empty(),
        "16k mono converts"
    );

    all_passed &= expect(
        output.size() == input.size(),
        "sample count preserved"
    );

    if (output.size() == input.size())
    {
        const float expected[]{
            -1.0f,
            -0.5f,
             0.0f,
             0.5f,
             32767.0f / 32768.0f
        };

        for (std::size_t i = 0; i < output.size(); ++i)
        {
            all_passed &= expect(
                std::fabs(output[i] - expected[i]) < 1e-6f,
                "normalized sample value"
            );
        }
    }

    // 测试 2：拒绝错误采样率。
    success =
        AudioPreprocessor::convertS16ToFloat32(
            input, 48000, 1, output, error
        );

    all_passed &= expect(
        !success && !error.empty() && output.empty(),
        "reject mismatched sample rate"
    );

    // 测试 3：拒绝双声道输入。
    success =
        AudioPreprocessor::convertS16ToFloat32(
            input, 16000, 2, output, error
        );

    all_passed &= expect(
        !success && !error.empty() && output.empty(),
        "reject stereo input"
    );

    // 测试 4：拒绝空音频。
    success =
        AudioPreprocessor::convertS16ToFloat32(
            {}, 16000, 1, output, error
        );

    all_passed &= expect(
        !success && !error.empty() && output.empty(),
        "reject empty samples"
    );

    if (all_passed)
        std::cout
            << "All AudioPreprocessor tests passed\n";

    return all_passed ? 0 : 1;
}
