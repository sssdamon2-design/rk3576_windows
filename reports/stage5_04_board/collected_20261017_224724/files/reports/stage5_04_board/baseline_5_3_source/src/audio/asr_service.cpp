
#include "audio/asr_service.h"

// sherpa-onnx 官方 C API。
#include <sherpa-onnx/c-api/c-api.h>

#include <chrono>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <memory>
#include <unistd.h>

// 对象销毁时自动释放模型。
ASRService::~ASRService()
{
    shutdown();
}

// 初始化 SenseVoiceSmall 模型。
bool ASRService::initialize(
    const std::string& model_path,
    const std::string& tokens_path,
    std::string& error)
{
    error.clear();

    // 重新初始化前，先释放旧模型。
    shutdown();

    // 检查模型是否可读。
    if (::access(model_path.c_str(), R_OK) != 0)
    {
        error = "Model file is not readable: " + model_path;
        return false;
    }

    // 检查词表是否可读。
    if (::access(tokens_path.c_str(), R_OK) != 0)
    {
        error = "Tokens file is not readable: " + tokens_path;
        return false;
    }

    // 1. 创建离线识别配置。
    // {} 表示零初始化。
    SherpaOnnxOfflineRecognizerConfig config{};

    // 2. 音频特征配置。
    config.feat_config.sample_rate = 16000;
    config.feat_config.feature_dim = 80;

    // 3. 指定 SenseVoiceSmall INT8 模型。
    config.model_config.sense_voice.model =
        model_path.c_str();

    // 固定中文识别。
    config.model_config.sense_voice.language = "zh";

    // 与之前命令行测试保持一致。
    config.model_config.sense_voice.use_itn = 0;

    // 4. 指定词表。
    config.model_config.tokens = tokens_path.c_str();

    // 5. 使用 ARM CPU 推理。
    config.model_config.provider = "cpu";

    // 初始使用两个 CPU 线程。
    config.model_config.num_threads = 2;

    config.model_config.modeling_unit = "cjkchar";

    // 6. 解码方式。
    config.decoding_method = "greedy_search";

    // 7. 创建 Recognizer。
    // 这里会初始化模型，耗时可能为数秒。
    recognizer_ = SherpaOnnxCreateOfflineRecognizer(&config);

    if (recognizer_ == nullptr)
    {
        error = "Failed to create sherpa-onnx recognizer";
        return false;
    }

    return true;
}

// 执行一次离线语音识别。
bool ASRService::recognize(
    const std::vector<float>& samples,
    std::string& text,
    double& latency_ms,
    std::string& error)
{
    error.clear();
    text.clear();
    latency_ms = 0.0;

    // 1. 检查模型是否初始化。
    if (recognizer_ == nullptr)
    {
        error = "ASR model is not initialized";
        return false;
    }

    // 2. 检查输入音频。
    if (samples.empty() ||
        samples.size() >
            static_cast<std::size_t>(
                std::numeric_limits<int32_t>::max()))
    {
        error = "Invalid audio sample count";
        return false;
    }

    // 开始计时。
    const auto start =
        std::chrono::steady_clock::now();

    // 3. 创建本次识别使用的 OfflineStream。
    //
    // 使用 unique_ptr + SDK 专用销毁函数。
    // 离开作用域时自动释放 Stream。
    using StreamPtr = std::unique_ptr<
        const SherpaOnnxOfflineStream,
        decltype(&SherpaOnnxDestroyOfflineStream)>;

    StreamPtr stream(
        SherpaOnnxCreateOfflineStream(recognizer_),
        &SherpaOnnxDestroyOfflineStream
    );

    if (!stream)
    {
        error = "Failed to create offline stream";
        return false;
    }

    // 4. 将 Float32 PCM 直接传入模型。
    // 输入采样率为 16000 Hz。
    //
    // 离线识别要求一次提交完整语音。
    SherpaOnnxAcceptWaveformOffline(
        stream.get(),
        16000,
        samples.data(),
        static_cast<int32_t>(samples.size())
    );

    // 5. 同步执行推理。
    SherpaOnnxDecodeOfflineStream(
        recognizer_,
        stream.get()
    );

    // 6. 获取识别结果。
    //
    // 结果由 SDK 分配，需要调用 SDK 的销毁接口。
    using ResultPtr = std::unique_ptr<
        const SherpaOnnxOfflineRecognizerResult,
        decltype(&SherpaOnnxDestroyOfflineRecognizerResult)>;

    ResultPtr result(
        SherpaOnnxGetOfflineStreamResult(stream.get()),
        &SherpaOnnxDestroyOfflineRecognizerResult
    );

    if (!result)
    {
        error = "Failed to obtain ASR result";
        return false;
    }

    // 7. 复制识别文本。
    // 不能长期保存 SDK 返回的原始指针。
    if (result->text != nullptr)
    {
        text = result->text;
    }

    // 8. 结束计时。
    const auto end =
        std::chrono::steady_clock::now();

    latency_ms =
        std::chrono::duration<double, std::milli>(
            end - start
        ).count();

    return true;
}

// 释放模型实例。
void ASRService::shutdown() noexcept
{
    if (recognizer_ != nullptr)
    {
        SherpaOnnxDestroyOfflineRecognizer(recognizer_);
        recognizer_ = nullptr;
    }
}
