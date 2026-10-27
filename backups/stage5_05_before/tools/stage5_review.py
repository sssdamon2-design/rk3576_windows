#!/usr/bin/env python3
"""Save a reviewable Stage 5.1 diff, hashes and full source appendix. No deployment."""

import difflib
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main():
    root = Path(__file__).resolve().parents[1]
    before = root / "backups/stage5_01_before"
    report = root / "reports/stage5_01_local"
    if not before.is_dir():
        raise SystemExit("Missing original snapshot; refusing to invent a baseline")
    report.mkdir(parents=True, exist_ok=True)
    paths = [Path("CMakeLists.txt"), Path("README_STAGE5.txt")]
    for folder in ("src", "include", "tests", "docs", "config", "tools"):
        paths.extend(p.relative_to(root) for p in (root / folder).rglob("*")
                     if p.is_file() and p.suffix in {".cpp", ".h", ".hpp", ".cmake",
                                                   ".md", ".txt", ".py", ".ps1", ".sh"})
    paths = sorted(set(paths))
    changed = [p for p in paths if sha256(before / p) != sha256(root / p)]
    source_paths = [p for p in changed if p.suffix in {".cpp", ".h", ".hpp", ".py", ".sh"}
                    or p.name == "CMakeLists.txt"]
    appendix = [
        "# 第五阶段5.1实际修改源码全文\n\n",
        "由 tools/stage5_review.py 从当前源码读取生成，不能作为编译或硬件通过证据。"
        "改动语句的语法、所有权和线程解释见 stage5_01_architecture_audit.md 操作5。\n\n",
        "第三阶段信号修复、当前ARM64/硬件验收与剩余风险见 "
        "[stage5_01_board_acceptance.md](stage5_01_board_acceptance.md)。"
        "本附录展示本地当前代码；实际部署版本必须与板端源文件哈希和日志核对。\n\n",
    ]
    for index, path in enumerate(source_paths, 1):
        content = (root / path).read_text(encoding="utf-8")
        appendix.append(f"## 操作 {index}：`{path.as_posix()}`\n\n")
        appendix.append(f"完整路径：`{root / path}`\n\n")
        appendix.append(f"SHA256：`{sha256(root / path)}`\n\n")
        language = "cmake" if path.name == "CMakeLists.txt" else (
            "python" if path.suffix == ".py" else "bash" if path.suffix == ".sh" else "cpp")
        appendix.append("### 最终完整源码\n\n```" + language + "\n" +
                        content.rstrip("\n") + "\n```\n\n")
    appendix_path = root / "docs/stage5_01_source_appendix.md"
    appendix_path.write_text("".join(appendix), encoding="utf-8", newline="\n")
    changed = sorted(set(changed + [appendix_path.relative_to(root)]))

    patch = []
    manifest = []
    for path in changed:
        old_path, new_path = before / path, root / path
        old = old_path.read_text(encoding="utf-8") if old_path.exists() else ""
        new = new_path.read_text(encoding="utf-8")
        patch.extend(difflib.unified_diff(
            old.splitlines(keepends=True), new.splitlines(keepends=True),
            fromfile="a/" + path.as_posix() if old_path.exists() else "/dev/null",
            tofile="b/" + path.as_posix()))
        manifest.append({"file": path.as_posix(), "before_sha256": sha256(old_path),
                         "after_sha256": sha256(new_path),
                         "status": "modified" if old_path.exists() else "added"})
    (report / "changes.patch").write_text("".join(patch), encoding="utf-8", newline="\n")
    (report / "change_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {}
    vlm_path = Path("src/ai/rk3576_vlm_backend.cpp")
    old = (before / vlm_path).read_text(encoding="utf-8")
    new = (root / vlm_path).read_text(encoding="utf-8")
    checks["cpu_preprocessor_unchanged"] = (
        old[old.index("bool frameToRgb512"):old.index("struct GenerationState")] ==
        new[new.index("bool frameToRgb512"):new.index("// Own only a successfully")])
    checks["vlm_initialization_unchanged"] = (
        old[old.index("bool RK3576VLMBackend::initialize"):old.index("InferenceResult RK3576")] ==
        new[new.index("bool RK3576VLMBackend::initialize"):new.index("InferenceResult RK3576")])
    checks["vlm_tokens_and_generation_unchanged"] = (
        old[old.index('    std::string prompt = "<image>"'): ] ==
        new[new.index('    std::string prompt = "<image>"'): ])
    for filename, cls in (("asr_pipeline.cpp", "ASRWorker"),
                          ("vad_audio_worker.cpp", "VadAudioWorker")):
        old = (before / "src/audio" / filename).read_text(encoding="utf-8")
        new = (root / "src/audio" / filename).read_text(encoding="utf-8")
        old_body = old[old.index(f"void {cls}::run()") + len(f"void {cls}::run()") :]
        new_body = new[new.index(f"void {cls}::runImpl()") + len(f"void {cls}::runImpl()") :]
        if cls == "VadAudioWorker" and "    ok_ = true;" in new_body:
            # Explicitly account for the reviewed signal-stop guard and completion status.
            # The VAD/PCM/pre-roll/timing/queue algorithm must otherwise remain identical.
            guard = "\n    if (stop_requested_.load())\n    {\n        ok_ = true;\n        return;\n    }\n"
            final = "    // A requested stop is successful if capture/VAD cleanup and final flush succeeded.\n    ok_ = true;"
            limited = new_body.count(guard) == 1 and new_body.count(final) == 1
            normalized = new_body.replace(guard, "", 1).replace(final, "    ok_ = !stop_requested_.load();", 1)
            checks["VadAudioWorker_signal_stop_changes_limited"] = limited and old_body == normalized
        else:
            checks[cls + "_algorithm_unchanged"] = old_body == new_body
    old = (before / "src/audio/asr_pipeline.cpp").read_text(encoding="utf-8")
    new = (root / "src/audio/audio_worker.cpp").read_text(encoding="utf-8")
    checks["AudioWorker_algorithm_unchanged"] = (
        old[old.index("void AudioWorker::run()") + len("void AudioWorker::run()"):
            old.index("// ====================================================\n// 3. ASRWorker")].strip() ==
        new[new.index("void AudioWorker::runImpl()") + len("void AudioWorker::runImpl()"):].strip())
    checks["qwen_backend_unchanged"] = (
        sha256(before / "src/ai/rkllm_backend.cpp") == sha256(root / "src/ai/rkllm_backend.cpp"))
    checks["camera_capture_unchanged"] = (
        sha256(before / "src/video/video_capture.cpp") == sha256(root / "src/video/video_capture.cpp"))
    for filename in ("asr_llm_smoke.cpp", "asr_llm_tts_smoke.cpp"):
        old = (before / "src/audio" / filename).read_text(encoding="utf-8")
        new = (root / "src/audio" / filename).read_text(encoding="utf-8")
        checks[filename + "_routing_prompts_callbacks_unchanged"] = (
            old[old.index("    const auto on_text ="):old.index("    ASRWorker consumer(")] ==
            new[new.index("    const auto on_text ="):new.index("    ASRWorker consumer(")])
    (report / "source_invariants.json").write_text(
        json.dumps({"checks": checks, "note": "Source equality checks only; no SDK/hardware validation."},
                   indent=2) + "\n", encoding="utf-8")
    print(f"Saved patch and hashes for {len(manifest)} files; full appendix: {len(source_paths)} files")
    if not all(checks.values()):
        raise SystemExit("Source equality check failed: " + str(checks))
    print("Source invariants passed (not inference/quality/performance evidence)")


if __name__ == "__main__":
    main()
