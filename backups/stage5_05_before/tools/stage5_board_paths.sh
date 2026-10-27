#!/usr/bin/env bash
# Source this file. Historical paths from 4.md, verified on board before use.
STAGE5_BASE=/home/cat/projects/RK3576
STAGE5_ORIGINAL="$STAGE5_BASE/rk3576_multimodal"
STAGE5_REVIEW="$STAGE5_BASE/rk3576_multimodal_stage5_review"
STAGE5_ASR="$STAGE5_BASE/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
STAGE5_VAD="$STAGE5_BASE/asr_runtime/vad/silero_vad.onnx"
STAGE5_QWEN="$STAGE5_BASE/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm"
STAGE5_KOKORO="$STAGE5_BASE/tts_runtime/models/kokoro-multi-lang-v1_1"
STAGE5_VLM="$STAGE5_ORIGINAL/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm"
STAGE5_VISION="$STAGE5_ORIGINAL/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn"
STAGE5_SHERPA="$STAGE5_BASE/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
STAGE5_RKLLM="$STAGE5_BASE/rkllm_sdk"
STAGE5_RKNN_INCLUDE="$STAGE5_BASE/rknn_test/include"
STAGE5_RKNN_LIBRARY=/usr/lib/librknnrt.so
# Prefer the stable build's explicit SDK cache paths, never eval its contents.
stage5_cache_value() {
    local key="$1" cache="$STAGE5_ORIGINAL/build/stage5_full/CMakeCache.txt"
    if [[ -r "$cache" ]]; then
        sed -n "s/^${key}:[^=]*=//p" "$cache" | head -n 1
    fi
}
stage5_value=$(stage5_cache_value SHERPA_ONNX_ROOT)
[[ -z "$stage5_value" ]] || STAGE5_SHERPA="$stage5_value"
stage5_value=$(stage5_cache_value RKLLM_SDK_ROOT)
[[ -z "$stage5_value" ]] || STAGE5_RKLLM="$stage5_value"
stage5_value=$(stage5_cache_value RKNN_INCLUDE_DIR)
[[ -z "$stage5_value" ]] || STAGE5_RKNN_INCLUDE="$stage5_value"
stage5_value=$(stage5_cache_value RKNN_RUNTIME_LIBRARY)
[[ -z "$stage5_value" ]] || STAGE5_RKNN_LIBRARY="$stage5_value"
unset stage5_value
STAGE5_RKLLM_LIB="$STAGE5_RKLLM/rkllm-runtime/Linux/librkllm_api/aarch64"
export LD_LIBRARY_PATH="$STAGE5_SHERPA/lib:$STAGE5_RKLLM_LIB:$(dirname -- "$STAGE5_RKNN_LIBRARY")${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

stage5_check_dependencies() {
    local path failed=0
    for path in "$STAGE5_ASR/model.int8.onnx" "$STAGE5_ASR/tokens.txt" \
        "$STAGE5_VAD" "$STAGE5_QWEN" "$STAGE5_KOKORO/model.onnx" \
        "$STAGE5_KOKORO/tokens.txt" "$STAGE5_KOKORO/voices.bin" \
        "$STAGE5_KOKORO/lexicon-us-en.txt" "$STAGE5_KOKORO/lexicon-zh.txt" \
        "$STAGE5_VLM" "$STAGE5_VISION" \
        "$STAGE5_SHERPA/include/sherpa-onnx/c-api/c-api.h" \
        "$STAGE5_SHERPA/lib/libsherpa-onnx-c-api.so" \
        "$STAGE5_RKLLM/rkllm-runtime/Linux/librkllm_api/include/rkllm.h" \
        "$STAGE5_RKLLM_LIB/librkllmrt.so" \
        "$STAGE5_RKNN_INCLUDE/rknn_api.h" "$STAGE5_RKNN_LIBRARY"; do
        if [[ -r "$path" && -f "$path" ]]; then
            stat -Lc 'READABLE %s bytes %n' -- "$path"
        else
            printf 'MISSING_OR_UNREADABLE %s\n' "$path"
            failed=1
        fi
    done
    [[ -d "$STAGE5_KOKORO/espeak-ng-data" ]] || failed=1
    return "$failed"
}

stage5_stable_fingerprint() {
    # Reads only: source files and the preserved known-good executable.
    (
        cd -- "$STAGE5_ORIGINAL"
        { printf '%s\0' CMakeLists.txt build/stage5_full/asr_llm_tts_smoke;
          find src include tests -type f \( -name '*.cpp' -o -name '*.h' -o -name '*.hpp' -o -name '*.cmake' \) -print0;
        } | sort -z | xargs -0 sha256sum --
    )
}
