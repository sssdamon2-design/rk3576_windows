#!/usr/bin/env bash
# Read-only inspection. No mkdir, copying, compilation, device open, sudo or deletion.
set -euo pipefail
STAGE5_BASE=/home/cat/projects/RK3576
STAGE5_ORIGINAL="$STAGE5_BASE/rk3576_multimodal"
printf '=== identity ===\n'
date -Is
uname -a
id
printf '=== tools ===\n'
for tool in cmake ctest c++ python3 tar sha256sum arecord aplay; do
    command -v "$tool" || true
done
printf '=== resources ===\n'
free -h
df -h "$STAGE5_BASE"
ps -eo pid,ppid,comm,rss,args --sort=-rss | head -n 16 || true
printf '=== devices (listing only) ===\n'
if command -v arecord >/dev/null; then arecord -l; fi
if command -v aplay >/dev/null; then aplay -l; fi
ls -l /dev/video11 || true
printf '=== stable executable and source fingerprints ===\n'
cd -- "$STAGE5_ORIGINAL"
sha256sum CMakeLists.txt src/audio/asr_llm_tts_smoke.cpp \
    src/ai/rkllm_backend.cpp src/ai/rk3576_vlm_backend.cpp \
    build/stage5_full/asr_llm_tts_smoke
printf '=== stable SDK cache (if present) ===\n'
if [[ -r build/stage5_full/CMakeCache.txt ]]; then
    sed -n -e '/^SHERPA_ONNX_ROOT:/p' -e '/^RKLLM_SDK_ROOT:/p' \
        -e '/^RKNN_INCLUDE_DIR:/p' -e '/^RKNN_RUNTIME_LIBRARY:/p' \
        -e '/^CMAKE_CXX_COMPILER:/p' build/stage5_full/CMakeCache.txt
fi
printf '=== historical model locations (existence, not inference) ===\n'
stat -L -- "$STAGE5_BASE/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx" \
    "$STAGE5_BASE/asr_runtime/vad/silero_vad.onnx" \
    "$STAGE5_BASE/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm" \
    "$STAGE5_BASE/tts_runtime/models/kokoro-multi-lang-v1_1/model.onnx" \
    models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm \
    models/vlm/smolvlm_vision_scatterfix_rk3576.rknn
printf '=== review destination ===\n'
if [[ -e "$STAGE5_BASE/rk3576_multimodal_stage5_review" ]]; then
    printf 'EXISTS: do not overwrite; choose a new directory and revise scripts first.\n'
else
    printf 'ABSENT: available after explicit deployment approval.\n'
fi
