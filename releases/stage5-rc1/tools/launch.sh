#!/usr/bin/env bash
# Explicit RC entry only; does not switch the user's default launcher.
set -euo pipefail
rc=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/releases/stage5-rc1
isolation=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
[[ "$(readlink -f -- "${BASH_SOURCE[0]}")" == "$rc/tools/launch.sh" ]] || exit 2
mode="${1:-gui}"; threads="${2:-4}"
[[ "$mode" == gui || "$mode" == cli ]] && [[ "$threads" == 2 || "$threads" == 4 ]] || exit 2
cd "$rc"
set -a
source tools/stage5_board_paths.sh
set +a
# Reuse the audited discovery/owner guard. Its current isolation path is an explicit dependency.
audio=$(python3 -I -B -c 'import sys;sys.path.insert(0,sys.argv[1]+"/tools");from stage5_05_voice_run import discover_audio,devices;a=discover_audio();assert devices(a)["clear"],"device busy or DRM baseline changed";print(a["alsa_device"])' "$isolation")
report="$isolation/reports/stage5_05_board/rc1_manual_$(date -u +%Y%m%d_%H%M%S)_$$"
mkdir -m 700 "$report"
for leaf in cache config data tmp shader_cache; do mkdir -m 700 "$report/$leaf"; done
export XDG_CACHE_HOME="$report/cache" XDG_CONFIG_HOME="$report/config" XDG_DATA_HOME="$report/data" TMPDIR="$report/tmp" QT_SHADER_CACHE_DIR="$report/shader_cache"
unset STAGE5_REPLAY_FILE STAGE5_REPLAY_AUDIO_FILE STAGE5_REPLAY_FRAME_DIR STAGE5_CAPTURE_AUDIO_FIXTURES
export STAGE5_STOP_MODE="${STAGE5_STOP_MODE:-drain}"
printf 'RC=stage5-rc1 HyperX=%s Logs=%s\n' "$audio" "$report"
printf '%s\n' "$$" > "$report/launcher.pid"
if [[ "$mode" == gui ]]; then
 export DISPLAY="${DISPLAY:-:0}" XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}" XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}" QT_QPA_PLATFORM=xcb
 exec "$rc/build/rk3576_multimodal_gui" --capture "$audio" --playback "$audio" --report-root "$report" --threads "$threads" --seconds 180
else
 export STAGE5_PROFILE="$report/profile.jsonl"
 exec "$rc/build/asr_llm_tts_smoke" "$audio" "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" "$STAGE5_KOKORO" "$audio" 180 "$threads" 17 "$STAGE5_VLM" "$STAGE5_VISION" /dev/video11
fi
