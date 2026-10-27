#!/usr/bin/env bash
# Usage: bash tools/stage5_board_voice.sh text|vision|both|sigint RUN_NAME
# Requires explicit prior user authorization. Run names must be new.
set -euo pipefail
ROOT=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
source "$ROOT/tools/stage5_board_paths.sh"
[[ "$ROOT" == "$STAGE5_REVIEW" ]] || { echo 'Refusing unexpected source root'; exit 2; }
[[ $# == 2 ]] || { echo 'Expected mode and unique run name'; exit 2; }
mode="$1"
name="$2"
case "$mode" in text|vision|both|sigint) ;; *) echo 'Invalid mode'; exit 2;; esac
[[ "$name" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Invalid run name'; exit 2; }
[[ ! -e "$ROOT/reports/stage5_01_board/$name" ]] || { echo 'Run exists'; exit 2; }
stage5_check_dependencies
cd -- "$ROOT"
fingerprints=$(stage5_stable_fingerprint)
postcheck() {
    code=$?
    trap - EXIT
    set +e
    after=$(stage5_stable_fingerprint)
    if [[ "$fingerprints" != "$after" ]]; then
        echo 'ERROR: stable source/binary fingerprint changed'
        code=1
    fi
    if [[ -d "$ROOT/reports/stage5_01_board/$name" ]]; then
        printf '%s\n' "$fingerprints" > "$ROOT/reports/stage5_01_board/$name/stable_before.sha256"
        printf '%s\n' "$after" > "$ROOT/reports/stage5_01_board/$name/stable_after.sha256"
        printf '%s\n' "$code" > "$ROOT/reports/stage5_01_board/$name/runner_exit_code.txt"
        dmesg --ctime > "$ROOT/reports/stage5_01_board/$name/dmesg_after.log" 2>&1
    fi
    exit "$code"
}
trap postcheck EXIT
expect="$mode"
extras=()
seconds=15
if [[ "$mode" == sigint ]]; then
    expect=both
    seconds=120
    extras=(--sigint-after-ready 2)
fi
args=(plughw:1,0 "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" \
      "$STAGE5_KOKORO" plughw:1,0 "$seconds" 2 17)
if [[ "$mode" != text ]]; then
    args+=("$STAGE5_VLM" "$STAGE5_VISION" /dev/video11)
fi
python3 "$ROOT/tools/stage5_board_capture.py" --execute --name "$name" \
    --expect "$expect" --timeout 300 "${extras[@]}" -- \
    "$ROOT/build/stage5_01_board/asr_llm_tts_smoke" "${args[@]}"
