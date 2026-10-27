#!/usr/bin/env bash
# Phase 2 only: isolated source compilation. Never run CTest or AI programs.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $(uname -m) == aarch64 || $(uname -m) == arm64 ]] || { echo 'ARM64 required'; exit 2; }
cd -- "$ROOT"
sha256sum --check SOURCE_SHA256SUMS
[[ ! -L "$ROOT/build" && ! -L "$ROOT/reports" ]] || { echo 'Refusing symlinked output'; exit 2; }
[[ ! -e "$ROOT/build/stage5_01_board" ]] || { echo 'Build directory already exists; stop'; exit 2; }
free_bytes=$(df -B1 --output=avail "$ROOT" | tail -n 1 | tr -d ' ')
(( free_bytes >= 2147483648 )) || { echo 'Less than planned 2 GiB disk reserve; stop'; exit 2; }
stamp=$(date -u +%Y%m%dT%H%M%SZ)
logdir="$ROOT/reports/stage5_01_board/compile_only_$stamp"
mkdir -p -- "$ROOT/reports/stage5_01_board"
mkdir -- "$logdir"
exec > >(tee "$logdir/session.log") 2>&1
stage5_stable_fingerprint > "$logdir/stable_before.sha256"
finish() {
    code=$?
    trap - EXIT
    set +e
    stage5_stable_fingerprint > "$logdir/stable_after.sha256"
    fingerprint_code=$?
    cmp "$logdir/stable_before.sha256" "$logdir/stable_after.sha256"
    compare_code=$?
    if [[ "$fingerprint_code" != 0 || "$compare_code" != 0 ]]; then code=1; fi
    printf '%s\n' "$code" > "$logdir/exit_code.txt"
    printf 'CTest=NOT_EXECUTED\nAI_PROGRAMS=NOT_STARTED\n' > "$logdir/phase_scope.txt"
    exit "$code"
}
trap finish EXIT
date -Is
uname -a
df -h "$ROOT"
free -h
stage5_check_dependencies
timeout --signal=TERM --kill-after=15s 180s \
    cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" 2>&1 | tee "$logdir/configure.log"
timeout --signal=TERM --kill-after=15s 600s \
    cmake --build "$ROOT/build/stage5_01_board" --parallel 3 2>&1 | tee "$logdir/build.log"
timeout 15s ldd "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" | tee "$logdir/ldd.log"
if grep -q 'not found' "$logdir/ldd.log"; then exit 1; fi
df -h "$ROOT"
printf 'PHASE2_COMPILE_ONLY_COMPLETE; CTest and hardware tests await phase 3 authorization.\n'
