
#include "ai/rk_backends.h"

namespace
{

#ifndef RK3576_WITH_RKLLM

const char* llm_error =
    "RK3576 Runtime/SDK not available: "
    "RKLLM headers, library and verified adapter are absent";

#endif

#ifndef RK3576_WITH_VLM
const char* vlm_error =
    "RK3576 Runtime/SDK not available: "
    "VLM runtime, vision encoder and verified adapter are absent";
#endif

InferenceResult unavailable(const char* message)
{
    InferenceResult result;
    result.error_message = message;
    return result;
}

}  // namespace

// 未启用真实 RKLLM 时，使用占位 Backend。
#ifndef RK3576_WITH_RKLLM

struct RKLLMBackend::Impl
{
};

RKLLMBackend::RKLLMBackend() = default;

RKLLMBackend::~RKLLMBackend()
{
    shutdown();
}

bool RKLLMBackend::initialize(
    const BackendConfig&,
    std::string& error)
{
    error = llm_error;
    return false;
}

InferenceResult RKLLMBackend::infer(
    const std::string&)
{
    return unavailable(llm_error);
}

// 操作 2.7 新增：补齐流式接口的占位实现。
// Runtime 不可用时不能伪造 Token 或调用流式输出回调。
InferenceResult RKLLMBackend::inferStreaming(
    const std::string& question,
    const LLMStreamCallback& on_chunk)
{
    (void)on_chunk;
    return infer(question);
}

void RKLLMBackend::shutdown() noexcept
{
    impl_.reset();
}

#endif

// 真实后端编译时不链接以下占位方法。
#ifndef RK3576_WITH_VLM
struct RK3576VLMBackend::Impl {};
RK3576VLMBackend::RK3576VLMBackend() = default;
RK3576VLMBackend::~RK3576VLMBackend() { shutdown(); }

// VLM 尚未启用时继续明确报错。
bool RK3576VLMBackend::initialize(
    const BackendConfig&,
    std::string& error)
{
    error = vlm_error;
    return false;
}

InferenceResult RK3576VLMBackend::infer(
    LatestFrameBuffer::FramePtr,
    const std::string&)
{
    return unavailable(vlm_error);
}

void RK3576VLMBackend::shutdown() noexcept
{
}

#endif  // !RK3576_WITH_VLM
