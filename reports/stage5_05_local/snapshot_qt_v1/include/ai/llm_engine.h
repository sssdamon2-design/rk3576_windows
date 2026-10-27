#pragma once
#include <memory>
#include <mutex>
#include "ai/llm_backend.h"

class LLMEngine
{
public:
    explicit LLMEngine(std::unique_ptr<ILLMBackend> backend);
    ~LLMEngine();
    bool initialize(const BackendConfig& config, std::string& error);
    InferenceResult infer(const std::string& question);
    InferenceResult inferStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk);
    void shutdown() noexcept;

private:
    // 每个 runtime 实例串行访问；流式回调不能重入这个 LLMEngine。
    std::mutex mutex_;
    std::unique_ptr<ILLMBackend> backend_;
    bool initialized_ = false;
    std::string initialization_error_;
};
