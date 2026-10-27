
#include "audio/asr_service.h"
#include "audio/audio_capture.h"
#include "audio/audio_preprocessor.h"

#include <cstddef>
#include <cstdint>
#include <iostream>
#include <string>
#include <vector>

int main(int argc, char** argv)
{
    // 参数：
    // argv[1]：ALSA 设备，例如 plughw:3,0。
    // argv[2]：SenseVoiceSmall 模型目录。
    if (argc != 3)
    {
        std::cerr
            << "Usage: asr_live_smoke "
            << "<ALSA device> <model directory>\n";
        return 2;
    }

    const std::string device = argv[1];
    const std::string model_dir = argv[2];

    std::string error;

    // 1. 创建 ASRService。
    ASRService asr;

    std::cout << "Loading SenseVoiceSmall...\n"
              << std::flush;

    // 2. 初始化模型。
    // 整个程序只初始化一次。
    if (!asr.initialize(
            model_dir + "/model.int8.onnx",
            model_dir + "/tokens.txt",
            error))
    {
        std::cerr
            << "ASR init failed: "
            << error << '\n';
        return 1;
    }

    std::cout << "ASR initialized\n";

    // 3. 创建 ALSA 音频采集对象。
    AudioCapture capture(device);

    if (!capture.open(error))
    {
        std::cerr
            << "AudioCapture failed: "
            << error << '\n';
        return 1;
    }

    // 音频配置：
    // 16 kHz、单声道、S16_LE。
    constexpr std::size_t sample_rate = 16000;
    constexpr std::size_t duration_seconds = 5;
    constexpr std::size_t chunk_frames = 320;

    // 一轮录音总共 80000 个样本。
    constexpr std::size_t total_frames =
        sample_rate * duration_seconds;

    // 每次读取 320 Frames，共读取 250 次。
    constexpr std::size_t total_chunks =
        total_frames / chunk_frames;

    // 4. 连续执行两轮语音识别。
    // 两轮复用同一个模型。
    for (int round = 1; round <= 2; ++round)
    {
        std::cout
            << "\nRound " << round
            << ": speak for 5 seconds now...\n"
            << std::flush;

        // 5. 保存一轮录音的 S16 PCM。
        std::vector<int16_t> pcm;
        pcm.reserve(total_frames);

        // 每次 AudioCapture 读取的 Chunk。
        std::vector<int16_t> chunk;

        // 6. 录制 5 秒音频。
        for (std::size_t i = 0; i < total_chunks; ++i)
        {
            if (!capture.readFrames(
                    chunk,
                    chunk_frames,
                    error))
            {
                std::cerr
                    << "Capture failed: "
                    << error << '\n';
                return 1;
            }

            // 将每个 Chunk 追加到整句缓冲区。
            pcm.insert(
                pcm.end(),
                chunk.begin(),
                chunk.end()
            );
        }

        // 7. S16 PCM 转 Float32。
        std::vector<float> samples;

        if (!AudioPreprocessor::convertS16ToFloat32(
                pcm,
                16000,
                1,
                samples,
                error))
        {
            std::cerr
                << "Preprocess failed: "
                << error << '\n';
            return 1;
        }

        // 8. 直接调用 C++ ASRService。
        std::string text;
        double latency_ms = 0.0;

        if (!asr.recognize(
                samples,
                text,
                latency_ms,
                error))
        {
            std::cerr
                << "Recognition failed: "
                << error << '\n';
            return 1;
        }

        // 9. 输出识别结果。
        std::cout
            << "Recognized: " << text << '\n';

        std::cout
            << "Latency: "
            << latency_ms << " ms\n";

        // 10. 计算实时率。
        const double rtf =
            latency_ms / 1000.0 / duration_seconds;

        std::cout
            << "RTF: " << rtf << '\n';
    }

    // 退出时通过析构函数自动释放资源。
    std::cout
        << "\nASR smoke test completed\n";

    return 0;
}
