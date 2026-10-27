set -eu
if [ -e '/home/cat/projects/RK3576/rk3576_multimodal_stage5_review' ] || [ -L '/home/cat/projects/RK3576/rk3576_multimodal_stage5_review' ]; then printf 'DESTINATION_EXISTS_STOP\n'; exit 20; fi; printf 'DESTINATION_ABSENT\n'; printf 'SSH_READONLY_CONNECTED\n'; uname -m; uname -r; id; date -Is
python3 -I -B - <<'STAGE5_READONLY_PY'
#!/usr/bin/env python3
"""Read-only inventory sent through SSH stdin; never install or build anything."""
import glob
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

BASE = Path("/home/cat/projects/RK3576")
ORIGINAL = BASE / "rk3576_multimodal"
REVIEW = BASE / "rk3576_multimodal_stage5_review"
STABLE_BUILD = ORIGINAL / "build/stage5_full"
STABLE_EXE = STABLE_BUILD / "asr_llm_tts_smoke"
DISK_RESERVE_BYTES = 2 * 1024 ** 3  # Planning allowance, not measured build size.


def run(command, env=None):
    try:
        result = subprocess.run(command, capture_output=True, text=True, errors="replace",
                                timeout=20, env=env)
        return {"command": command, "exit_code": result.returncode,
                "stdout": result.stdout, "stderr": result.stderr}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {"command": command, "exit_code": None, "error": str(error)}


def fingerprint():
    selected = {ORIGINAL / "CMakeLists.txt", ORIGINAL / "README_STAGE5.txt"}
    for directory in ("src", "include", "tests", "config", "build/stage5_full"):
        start = ORIGINAL / directory
        if not start.is_dir():
            continue
        for current, dirs, files in os.walk(start, followlinks=False):
            for name in dirs + files:
                path = Path(current) / name
                if path.is_symlink():
                    selected.add(path)
            selected.update(Path(current) / name for name in files)
    result = {}
    for path in sorted(selected):
        relative = str(path.relative_to(ORIGINAL))
        try:
            if path.is_symlink():
                result[relative] = {"symlink": os.readlink(path)}
                continue
            before = path.stat()
            digest = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.stat()
            result[relative] = {"sha256": digest.hexdigest(), "bytes": after.st_size,
                                "mtime_ns": after.st_mtime_ns,
                                "changed_while_reading": (before.st_size, before.st_mtime_ns) !=
                                (after.st_size, after.st_mtime_ns)}
        except OSError as error:
            result[relative] = {"error": str(error)}
    return result


def devices_and_owners():
    nodes = sorted(set(glob.glob("/dev/video*") + glob.glob("/dev/snd/pcm*") +
                       glob.glob("/dev/rknpu*") + glob.glob("/dev/dri/renderD*")))
    node_info = []
    by_device = {}
    for name in nodes:
        path = Path(name)
        try:
            value = path.stat()
            if not stat.S_ISCHR(value.st_mode):
                continue
            driver = None
            if name.startswith("/dev/dri/"):
                driver_path = Path("/sys/class/drm") / path.name / "device/driver"
                if driver_path.exists():
                    driver = str(driver_path.resolve())
            kind = ("alsa_pcm" if name.startswith("/dev/snd/pcm") else
                    "camera_target" if name == "/dev/video11" else
                    "camera_other" if name.startswith("/dev/video") else
                    "npu" if "rknpu" in (name + (driver or "")).lower() else "render_unclassified")
            row = {"path": name, "kind": kind, "driver": driver,
                   "major": os.major(value.st_rdev), "minor": os.minor(value.st_rdev)}
            node_info.append(row)
            by_device.setdefault(value.st_rdev, []).append(row)
        except OSError:
            pass
    owners = []
    denied = []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            descriptors = list((process / "fd").iterdir())
        except PermissionError:
            denied.append(int(process.name))
            continue
        except FileNotFoundError:
            continue
        for descriptor in descriptors:
            try:
                value = descriptor.stat()
                if stat.S_ISCHR(value.st_mode) and value.st_rdev in by_device:
                    owners.append({"pid": int(process.name), "fd": descriptor.name,
                                   "comm": (process / "comm").read_text().strip(),
                                   "devices": by_device[value.st_rdev]})
            except PermissionError:
                denied.append(int(process.name))
            except FileNotFoundError:
                pass
    # Ordinary users may not see other users' FDs. Only a noninteractive,
    # read-only fuser listing is attempted with sudo; no kill option is used.
    privileged = None
    if denied and nodes and Path("/usr/bin/fuser").is_file() and shutil.which("sudo"):
        privileged = run(["sudo", "-n", "--", "/usr/bin/fuser", "-v", "--"] + nodes)
    privileged_clear = bool(privileged and privileged.get("exit_code") == 1 and
                            not privileged.get("stdout", "").strip() and
                            not privileged.get("stderr", "").strip())
    normal_clear = not denied and not owners
    pcm = {}
    for filename in glob.glob("/proc/asound/card*/pcm*/sub*/status"):
        try:
            pcm[filename] = Path(filename).read_text()
        except OSError as error:
            pcm[filename] = "UNREADABLE: " + str(error)
    return {"nodes": node_info, "visible_owners": owners,
            "permission_denied_pids": sorted(set(denied)),
            "sudo_readonly_fuser": privileged, "alsa_status": pcm,
            "all_listed_nodes_clear_confirmed": normal_clear or privileged_clear,
            "npu_node_identified": any(row["kind"] == "npu" for row in node_info)}


def main():
    # First check, including dangling symlinks. Stop before any further query.
    if os.path.lexists(REVIEW):
        print("DESTINATION_EXISTS_STOP")
        return 20
    print("DESTINATION_ABSENT\nSSH_READONLY_CONNECTED", flush=True)
    result = {"started_unix_time": time.time(), "read_only": True,
              "review_directory_absent_before": True}
    before = fingerprint()
    result["identity"] = {name: run(command) for name, command in {
        "uname": ["uname", "-a"], "user": ["id"], "time": ["date", "-Is"],
        "memory": ["free", "-h"], "disk": ["df", "-h", str(BASE)],
        "processes": ["ps", "-eo", "pid,ppid,user,comm,rss,args", "--sort=-rss"],
        "capture_devices": ["arecord", "-l"], "playback_devices": ["aplay", "-l"],
        "cmake": ["cmake", "--version"], "compiler": ["c++", "--version"]}.items()}
    disk = shutil.disk_usage(BASE)
    fs = os.statvfs(BASE)
    result["disk_budget"] = {"free_bytes": disk.free, "free_inodes": fs.f_favail,
                             "required_reserve_bytes": DISK_RESERVE_BYTES,
                             "reserve_is_planning_allowance_not_measurement": True,
                             "enough": disk.free >= DISK_RESERVE_BYTES and fs.f_favail >= 2000}
    cache = {}
    cache_path = STABLE_BUILD / "CMakeCache.txt"
    if cache_path.is_file():
        for line in cache_path.read_text(errors="replace").splitlines():
            if "=" in line and ":" in line.split("=", 1)[0]:
                key, value = line.split("=", 1)
                cache[key.split(":", 1)[0]] = value
    sdk = {
        "SHERPA_ONNX_ROOT": cache.get("SHERPA_ONNX_ROOT") or str(BASE / "asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"),
        "RKLLM_SDK_ROOT": cache.get("RKLLM_SDK_ROOT") or str(BASE / "rkllm_sdk"),
        "RKNN_INCLUDE_DIR": cache.get("RKNN_INCLUDE_DIR") or str(BASE / "rknn_test/include"),
        "RKNN_RUNTIME_LIBRARY": cache.get("RKNN_RUNTIME_LIBRARY") or "/usr/lib/librknnrt.so"}
    result["sdk_paths"] = {key: {"path": value, "source": "stable_CMakeCache" if cache.get(key) else "historical_default"}
                           for key, value in sdk.items()}
    asr = BASE / "asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
    kokoro = BASE / "tts_runtime/models/kokoro-multi-lang-v1_1"
    rklib = Path(sdk["RKLLM_SDK_ROOT"]) / "rkllm-runtime/Linux/librkllm_api"
    paths = {
        "asr_model": asr / "model.int8.onnx", "asr_tokens": asr / "tokens.txt",
        "vad": BASE / "asr_runtime/vad/silero_vad.onnx",
        "qwen": BASE / "rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm",
        "vlm": ORIGINAL / "models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm",
        "vision": ORIGINAL / "models/vlm/smolvlm_vision_scatterfix_rk3576.rknn",
        "sherpa_header": Path(sdk["SHERPA_ONNX_ROOT"]) / "include/sherpa-onnx/c-api/c-api.h",
        "sherpa_library": Path(sdk["SHERPA_ONNX_ROOT"]) / "lib/libsherpa-onnx-c-api.so",
        "rkllm_header": rklib / "include/rkllm.h", "rkllm_library": rklib / "aarch64/librkllmrt.so",
        "rknn_header": Path(sdk["RKNN_INCLUDE_DIR"]) / "rknn_api.h",
        "rknn_library": Path(sdk["RKNN_RUNTIME_LIBRARY"]),
        "alsa_header": Path("/usr/include/alsa/asoundlib.h"),
        "stable_executable": STABLE_EXE}
    for name in ("model.onnx", "tokens.txt", "voices.bin", "lexicon-us-en.txt", "lexicon-zh.txt", "espeak-ng-data"):
        paths["kokoro_" + name] = kokoro / name
    result["dependencies"] = {}
    for name, path in paths.items():
        row = {"path": str(path), "exists": path.exists(), "readable": os.access(path, os.R_OK)}
        if path.exists():
            row.update({"resolved_path": str(path.resolve()), "bytes": path.stat().st_size,
                        "is_directory": path.is_dir()})
        result["dependencies"][name] = row
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = ":".join((str(Path(sdk["SHERPA_ONNX_ROOT"]) / "lib"),
                                                 str(rklib / "aarch64"),
                                                 str(Path(sdk["RKNN_RUNTIME_LIBRARY"]).parent)))
    result["stable_binary_file_type"] = run(["file", "-L", str(STABLE_EXE)])
    result["dynamic_link_inspection"] = run(["ldd", str(STABLE_EXE)], environment)
    result["resource_occupancy"] = devices_and_owners()
    after = fingerprint()
    result["original_fingerprints_before"] = before
    result["original_fingerprints_after"] = after
    result["original_scope"] = "CMakeLists/README/src/include/tests/config and all regular files/symlinks in build/stage5_full; model weights not hashed/copied"
    result["original_unchanged"] = before == after and not any(
        row.get("error") or row.get("changed_while_reading") for row in before.values())
    result["review_directory_absent_after"] = not os.path.lexists(REVIEW)
    result["checks"] = {
        "review_directory_absent": result["review_directory_absent_after"],
        "disk_budget_sufficient": result["disk_budget"]["enough"],
        "original_and_stable_build_present": ORIGINAL.is_dir() and STABLE_BUILD.is_dir() and STABLE_EXE.is_file(),
        "original_fingerprints_unchanged": result["original_unchanged"],
        "all_required_paths_readable": all(row["exists"] and row["readable"] for row in result["dependencies"].values()),
        "dynamic_libraries_resolved": result["dynamic_link_inspection"].get("exit_code") == 0 and
                                      "not found" not in result["dynamic_link_inspection"].get("stdout", ""),
        "device_owners_clear": result["resource_occupancy"]["all_listed_nodes_clear_confirmed"],
        "npu_device_identified": result["resource_occupancy"]["npu_node_identified"]}
    result["stage1_all_checks_passed"] = all(result["checks"].values())
    print("STAGE5_READONLY_JSON_BEGIN")
    print(json.dumps(result, indent=2, ensure_ascii=True))
    print("STAGE5_READONLY_JSON_END")
    if not result["review_directory_absent_after"]:
        print("DESTINATION_EXISTS_STOP")
        return 20
    return 0 if result["stage1_all_checks_passed"] else 22


if __name__ == "__main__":
    raise SystemExit(main())

STAGE5_READONLY_PY
