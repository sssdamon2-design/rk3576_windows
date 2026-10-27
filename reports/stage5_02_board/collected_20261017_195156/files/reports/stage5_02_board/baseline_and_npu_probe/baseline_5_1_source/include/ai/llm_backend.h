#pragma once
#include <functional>
#include <string>
#include "ai/backend_config.h"
#include "common/inference_result.h"

// 每次 SDK 返回可显示文本片段时，通知上层。
using LLMStreamCallback = std::function<void(const std::string&)>;

class ILLMBackend
{
public:
    virtual ~ILLMBackend() = default;
    virtual bool initialize(const BackendConfig& config, std::string& error) = 0;
    virtual InferenceResult infer(const std::string& question) = 0;

    // 默认实现保证旧的测试 Backend 继续可用。
    // 注意：默认实现是“推理结束后一次性通知”，不是真正的流式推理。
    virtual InferenceResult inferStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk)
    {
        InferenceResult result = infer(question);
        if (result.success && on_chunk && !result.text.empty())
            on_chunk(result.text);
        return result;
    }

    // 必须可重复调用，并释放部分初始化留下的资源。
    virtual void shutdown() noexcept = 0;
};
