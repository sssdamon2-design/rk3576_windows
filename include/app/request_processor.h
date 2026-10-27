#pragma once
#include "ai/llm_engine.h"
#include "ai/vlm_engine.h"
#include "router/intent_router.h"

struct RequestResult
{
    RouteDecision route;
    InferenceResult inference;
};

class RequestProcessor
{
public:
    RequestProcessor(LatestFrameBuffer& frames, LLMEngine& llm, VLMEngine& vlm);
    RequestResult process(const std::string& question);
    RequestResult processStreaming(
        const std::string& question,
        const LLMStreamCallback& on_chunk);

private:
    LatestFrameBuffer& frames_;
    LLMEngine& llm_;
    VLMEngine& vlm_;
    IntentRouter router_;
};

