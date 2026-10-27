#pragma once
#include <memory>
#include "ai/llm_backend.h"
#include "ai/vlm_backend.h"

class RKLLMBackend final : public ILLMBackend
{
public:
    RKLLMBackend();
    ~RKLLMBackend() override;

    bool initialize(const BackendConfig& config, std::string& error) override;
    InferenceResult infer(const std::string& question) override;
    InferenceResult inferStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk) override;
    void shutdown() noexcept override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

class RK3576VLMBackend final : public IVLMBackend
{
public:
    RK3576VLMBackend();
    ~RK3576VLMBackend() override;
    bool initialize(const BackendConfig& config, std::string& error) override;
    InferenceResult infer(LatestFrameBuffer::FramePtr frame,
                          const std::string& question) override;
    void shutdown() noexcept override;
private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};
