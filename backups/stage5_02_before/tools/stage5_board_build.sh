#!/usr/bin/env bash
# Board execution is separately authorized by the user; not run by packaging.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $(uname -m) == aarch64 || $(uname -m) == arm64 ]] || { echo 'ARM64 required'; exit 2; }
[[ -x "$STAGE5_ORIGINAL/build/stage5_full/asr_llm_tts_smoke" ]] || { echo 'Stable executable missing'; exit 2; }
cd -- "$ROOT"
sha256sum --check SOURCE_SHA256SUMS
stamp=$(date -u +%Y%m%dT%H%M%SZ)
logdir="$ROOT/reports/stage5_01_board/build_$stamp"
mkdir -p -- "$ROOT/reports/stage5_01_board"
mkdir -- "$logdir"
exec > >(tee "$logdir/session.log") 2>&1
printf '=== target environment ===\n'
date -Is
uname -a
cmake --version
c++ --version
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
    exit "$code"
}
trap finish EXIT
stage5_check_dependencies
cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" \
    -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" 2>&1 | tee "$logdir/configure.log"
cmake --build "$ROOT/build/stage5_01_board" --parallel 3 2>&1 | tee "$logdir/build.log"
ctest --test-dir "$ROOT/build/stage5_01_board" --output-on-failure -V 2>&1 | tee "$logdir/ctest.log"
ldd "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" | tee "$logdir/ldd.log"
if grep -q 'not found' "$logdir/ldd.log"; then exit 1; fi
printf 'BUILD_AND_PORTABLE_CTEST_COMPLETE: real voice tests still required.\n'
