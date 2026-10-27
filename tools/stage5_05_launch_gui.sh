#!/usr/bin/env bash
# Existing desktop only. No installation, permission changes, or stable overwrite.
set -euo pipefail
root=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
cd "$root"
set -a
source "$root/tools/stage5_board_paths.sh"
set +a
threads="${1:-4}"
[[ "$threads" == 2 || "$threads" == 4 ]] || { echo 'threads must be 2 or 4' >&2; exit 2; }
audio=$(python3 -I -B -c 'import sys; sys.path.insert(0,sys.argv[1]+"/tools"); from stage5_05_voice_run import discover_audio,devices; audio=discover_audio(); state=devices(audio); assert state["clear"], "Camera/ALSA/NPU busy or inspection failed: "+str(state["query"]); print(audio["alsa_device"])' "$root")
report="$root/reports/stage5_05_board/manual_gui_$(date -u +%Y%m%d_%H%M%S)_$$"
mkdir -m 700 "$report"
for leaf in cache config data tmp shader_cache; do mkdir -m 700 "$report/$leaf"; done
export DISPLAY="${DISPLAY:-:0}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
export XDG_CACHE_HOME="$report/cache" XDG_CONFIG_HOME="$report/config" XDG_DATA_HOME="$report/data" TMPDIR="$report/tmp" QT_SHADER_CACHE_DIR="$report/shader_cache"
export QT_QPA_PLATFORM=xcb
unset STAGE5_REPLAY_FILE STAGE5_REPLAY_AUDIO_FILE STAGE5_REPLAY_FRAME_DIR STAGE5_CAPTURE_AUDIO_FIXTURES
printf 'HyperX=%s\nLogs=%s\n' "$audio" "$report"
exec "$root/build/stage5_05_final_v2/rk3576_multimodal_gui" --capture "$audio" --playback "$audio" --report-root "$report" --threads "$threads" --seconds 3600
