#include "ai/rk_backends.h"
#include "rkllm.h"

#include <chrono>
#include <memory>
#include <mutex>
#include <string>
#include <utility>

namespace
{

struct RunContext
{
    std::mutex mutex;
    std::string text;
    const LLMStreamCallback* on_chunk = nullptr;
    std::chrono::steady_clock::time_point start;
    double first_text_ms = -1.0;
    bool failed = false;
};

// SDK C 回调中不允许 C++ 异常逃逸。
int onRKLLMResult(RKLLMResult* result, void* userdata, LLMCallState state)
{
    auto* context = static_cast<RunContext*>(userdata);
    if (context == nullptr) return 0;

    if (state == RKLLM_RUN_ERROR)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
        return 0;
    }

    if (state != RKLLM_RUN_NORMAL || result == nullptr ||
        result->text == nullptr || result->text[0] == '\0')
        return 0;

    try
    {
        // 必须在当前回调期间复制 Runtime 提供的字符数据。
        const std::string chunk(result->text);
        {
            std::lock_guard<std::mutex> lock(context->mutex);
            if (context->first_text_ms < 0.0)
            {
                const auto now = std::chrono::steady_clock::now();
                context->first_text_ms =
                    std::chrono::duration<double, std::milli>(now - context->start).count();
            }
            context->text.append(chunk);
        }

        // 不持有 RunContext 的 mutex 调用上层，避免锁重入。
        // 第一版要求回调只做短小的、非阻塞的处理。
        if (context->on_chunk != nullptr && *context->on_chunk)
            (*context->on_chunk)(chunk);
    }
    catch (...)
    {
        std::lock_guard<std::mutex> lock(context->mutex);
        context->failed = true;
    }
    return 0;
}

}  // namespace

struct RKLLMBackend::Impl
{
    std::string model_path;
    LLMHandle handle = nullptr;
    RKLLMParam params{};
    RKLLMCallback callbacks{};

    ~Impl() noexcept
    {
        if (handle != nullptr)
        {
            (void)rkllm_destroy(handle);
            handle = nullptr;
        }
    }
};

RKLLMBackend::RKLLMBackend() = default;

RKLLMBackend::~RKLLMBackend()
{
    shutdown();
}

bool RKLLMBackend::initialize(const BackendConfig& config, std::string& error)
{
    shutdown();
    error.clear();

    if (config.model_path.empty())
    {
        error = "RKLLM model_path is empty";
        return false;
    }

    auto next = std::make_unique<Impl>();
    next->model_path = config.model_path;
    next->params = rkllm_createDefaultParam();
    next->params.model_path = next->model_path.c_str();

    // 保持与已经验证成功的官方 Demo 参数一致。
    next->params.top_k = 1;
    next->params.top_p = 0.95f;
    next->params.temperature = 0.8f;
    next->params.repeat_penalty = 1.1f;
    next->params.frequency_penalty = 0.0f;
    next->params.presence_penalty = 0.0f;
    next->params.max_new_tokens = 128;
    next->params.max_context_len = 1024;
    next->params.skip_special_token = true;
    next->params.is_async = false;
    next->params.extend_param.base_domain_id = 0;
    next->params.extend_param.embed_flash = 1;

    next->callbacks.result_callback = onRKLLMResult;

    const int ret = rkllm_init(&next->handle, &next->params, &next->callbacks);
    if (ret != 0 || next->handle == nullptr)
    {
        error = "rkllm_init failed, ret=" + std::to_string(ret);
        return false;
    }

    impl_ = std::move(next);
    return true;
}

InferenceResult RKLLMBackend::infer(const std::string& question)
{
    return inferStreaming(question, {});
}

InferenceResult RKLLMBackend::inferStreaming(
    const std::string& question,
    const LLMStreamCallback& on_chunk)
{
    InferenceResult output;
    if (!impl_ || impl_->handle == nullptr)
    {
        output.error_message = "RKLLM backend is not initialized";
        return output;
    }
    if (question.empty())
    {
        output.error_message = "RKLLM question is empty";
        return output;
    }

    RKLLMInput input{};
    input.input_type = RKLLM_INPUT_PROMPT;
    input.role = "user";
    input.prompt_input = question.c_str();

    RKLLMInferParam infer_params{};
    infer_params.mode = RKLLM_INFER_GENERATE;
    infer_params.keep_history = 0;

    RunContext context;
    context.on_chunk = &on_chunk;
    context.start = std::chrono::steady_clock::now();

    const int ret = rkllm_run(impl_->handle, &input, &infer_params, &context);

    std::lock_guard<std::mutex> lock(context.mutex);
    if (ret != 0)
    {
        output.error_message = "rkllm_run failed, ret=" + std::to_string(ret);
        return output;
    }
    if (context.failed)
    {
        output.error_message = "RKLLM callback reported an error";
        return output;
    }
    if (context.text.empty())
    {
        output.error_message = "RKLLM inference produced no text";
        return output;
    }

    output.success = true;
    output.text = std::move(context.text);
    output.first_text_ms = context.first_text_ms;
    return output;
}

void RKLLMBackend::shutdown() noexcept
{
    impl_.reset();
}
