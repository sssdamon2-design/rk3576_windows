#include "app/request_processor.h"
#include <utility>

RequestProcessor::RequestProcessor(
    LatestFrameBuffer& frames, LLMEngine& llm, VLMEngine& vlm)
    : frames_(frames), llm_(llm), vlm_(vlm) {}

RequestResult RequestProcessor::process(const std::string& question)
{
    return processStreaming(question, {});
}

RequestResult RequestProcessor::processStreaming(
    const std::string& question,
    const LLMStreamCallback& on_chunk)
{
    RequestResult result;
    result.route = router_.route(question);
    if (result.route.type == RequestType::Vision)
    {
        // 相机帧只短暂加锁获取，VLM 推理不持有 LatestFrameBuffer 锁。
        auto frame = frames_.getLatest();
        result.inference = vlm_.infer(std::move(frame), question);
    }
    else
    {
        result.inference = llm_.inferStreaming(question, on_chunk);
    }
    return result;
}
