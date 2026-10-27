
#pragma once

#include <string>
#include <vector>

// sherpa-onnx C API 的模型句柄前向声明。
// 具体定义由官方 c-api.h 提供。
struct SherpaOnnxOfflineRecognizer;

// ASRService：封装离线语音识别模型。
// 一个对象持有一个常驻的 Recognizer。
class ASRService
{
public:
    ASRService() = default;

    // 析构函数：自动释放模型资源。
    ~ASRService();

    // 禁止复制，防止两个对象重复释放模型句柄。
    ASRService(const ASRService&) = delete;
    ASRService& operator=(const ASRService&) = delete;

    // 加载模型和词表。
    bool initialize(
        const std::string& model_path,
        const std::string& tokens_path,
        std::string& error
    );

    // 输入：
    // samples：16 kHz、Mono、归一化 Float32 PCM。
    //
    // 输出：
    // text：识别出的中文文本。
    // latency_ms：本次识别接口耗时，单位毫秒。
    // error：失败原因。
    bool recognize(
        const std::vector<float>& samples,
        std::string& text,
        double& latency_ms,
        std::string& error
    );

    // 释放模型资源。
    // 可以重复调用。
    void shutdown() noexcept;

private:
    // sherpa-onnx 离线模型实例句柄。
    const SherpaOnnxOfflineRecognizer* recognizer_ = nullptr;
};
