#pragma once
#include <cstdint>
#include <string>
#include "common/work_control.h"

// 不可用的指标使用 -1，不伪造 TTFT 或 tokens/s。
struct InferenceResult
{
    bool success = false;
    std::string text;
    std::string error_message;
    double latency_ms = 0.0;
    uint64_t frame_id = 0;
    uint64_t frame_timestamp_ns = 0;
    double frame_age_ms = -1.0;

    // 从 rkllm_run 提交前至首个非空文本回调的耗时；无法获得时为 -1。
    double first_text_ms = -1.0;
    TaskDisposition disposition = TaskDisposition::Completed;
};
