#!/usr/bin/env python3
"""Capture one authorized isolated board run; never treats SIGINT death as clean shutdown."""

import argparse
import json
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time

REVIEW = Path("/home/cat/projects/RK3576/rk3576_multimodal_stage5_review")


def resource_sample(pid):
    result = {"elapsed_monotonic": time.monotonic(), "pid": pid}
    try:
        status = Path(f"/proc/{pid}/status").read_text()
        for line in status.splitlines():
            key = line.split(":", 1)[0]
            if key in {"VmRSS", "VmHWM", "VmSize", "Threads", "State"}:
                result[key] = line.split(":", 1)[1].strip()
        result["fd_count"] = len(list(Path(f"/proc/{pid}/fd").iterdir()))
        result["task_ids"] = sorted(p.name for p in Path(f"/proc/{pid}/task").iterdir())
    except (OSError, ValueError) as error:
        result["sample_error"] = str(error)
    return result


def parse_summary(text):
    import re
    parsed = {}
    for label in ("VAD segments", "ASR recognized", "Audio queue dropped",
                  "LLM accepted/completed/success/failed/rejected",
                  "TTS accepted/completed/success/failed/rejected/empty",
                  "VISION completed/success/failed"):
        found = re.search(r"^" + re.escape(label) + r": ([0-9/]+)\s*$", text, re.M)
        parsed[label] = [int(x) for x in found.group(1).split("/")] if found else None
    parsed["program_PASS"] = bool(re.search(r"^PASS\s*$", text, re.M))
    parsed["error_lines"] = [line for line in text.splitlines() if re.search(
        r"\[Fatal\]|\[Timeout\]|\[.*(?:error|Error|rejected)\]|segmentation fault|bad_alloc", line)]
    return parsed


def accepted(summary, exitcode, expect, interrupted, timed_out, forced):
    # The first submitted patch has no cooperative voice SIGINT implementation.
    # Signal cases are observations, never acceptance passes merely for exiting.
    if interrupted or timed_out or forced or exitcode != 0 or not summary["program_PASS"]:
        return False
    llm = summary["LLM accepted/completed/success/failed/rejected"]
    tts = summary["TTS accepted/completed/success/failed/rejected/empty"]
    vision = summary["VISION completed/success/failed"]
    vad = summary["VAD segments"]
    asr = summary["ASR recognized"]
    dropped = summary["Audio queue dropped"]
    if not all(x is not None for x in (llm, tts, vision, vad, asr, dropped)):
        return False
    if [len(x) for x in (llm, tts, vision, vad, asr, dropped)] != [5, 6, 3, 1, 1, 1]:
        return False
    if summary["error_lines"]:
        return False
    if dropped != [0] or not (vad[0] == asr[0] and asr[0] > 0):
        return False
    if not (llm[0] == llm[1] == llm[2] and llm[3:] == [0, 0]):
        return False
    if not (vision[0] == vision[1] and vision[2] == 0):
        return False
    if not (tts[0] == tts[1] == tts[2] == llm[2] + vision[1] and tts[3:] == [0, 0, 0]):
        return False
    return (expect == "text" and llm[2] > 0 or
            expect == "vision" and vision[1] > 0 or
            expect == "both" and llm[2] > 0 and vision[1] > 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="Explicitly run only after user authorization")
    parser.add_argument("--name", required=True)
    parser.add_argument("--expect", choices=("text", "vision", "both"), default="both")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--sigint-after-ready", type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not args.name.replace("_", "").replace("-", "").isalnum():
        parser.error("Provide a simple run name and -- executable arguments")
    if args.timeout <= 0 or (args.sigint_after_ready is not None and args.sigint_after_ready < 0):
        parser.error("Invalid time limit")
    if not args.execute:
        print(json.dumps({"status": "NOT_EXECUTED", "command": command,
                          "expect": args.expect, "name": args.name}, indent=2))
        return 0
    root = Path(__file__).resolve().parents[1]
    exe = Path(command[0]).resolve()
    if sys.platform != "linux" or root != REVIEW or exe != REVIEW / "build/stage5_01_board/asr_llm_tts_smoke":
        parser.error("Only the isolated Linux review executable may be run")
    report_parent = root / "reports/stage5_01_board"
    if report_parent.resolve() != report_parent:
        parser.error("Report directory must not redirect outside the review tree")
    report_parent.mkdir(parents=True, exist_ok=True)
    report = report_parent / args.name
    report.mkdir() # Refuse overwriting a previous run.
    (report / "command.json").write_text(json.dumps(command, indent=2) + "\n")
    child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    events = queue.Queue()
    def reader():
        try:
            for line in iter(child.stdout.readline, b""):
                events.put(line)
        finally:
            events.put(None)
    reading = threading.Thread(target=reader, daemon=True)
    reading.start()
    requested = threading.Event()
    previous = {}
    for value in (signal.SIGINT, signal.SIGTERM):
        previous[value] = signal.signal(value, lambda *_: requested.set())
    start = time.monotonic()
    ready_at = None
    interrupted = False
    timed_out = False
    forced = False
    stop_at = None
    eof = False
    next_sample = start
    try:
        with (report / "terminal.log").open("wb") as log, (report / "resources.jsonl").open("w") as resources:
            while child.poll() is None or not eof:
                try:
                    line = events.get(timeout=0.1)
                    if line is None:
                        eof = True
                    else:
                        log.write(line)
                        log.flush()
                        sys.stdout.buffer.write(line)
                        sys.stdout.buffer.flush()
                        if b"[Listen]" in line and ready_at is None:
                            ready_at = time.monotonic()
                except queue.Empty:
                    pass
                now = time.monotonic()
                if now >= next_sample and child.poll() is None:
                    sample = resource_sample(child.pid)
                    sample["elapsed_s"] = now - start
                    resources.write(json.dumps(sample) + "\n")
                    resources.flush()
                    next_sample = now + 1
                automated = (args.sigint_after_ready is not None and ready_at is not None and
                             now - ready_at >= args.sigint_after_ready)
                if child.poll() is None and stop_at is None and (requested.is_set() or automated or now-start > args.timeout):
                    timed_out = now - start > args.timeout and not requested.is_set() and not automated
                    interrupted = not timed_out
                    try:
                        os.killpg(child.pid, signal.SIGTERM if timed_out else signal.SIGINT)
                    except ProcessLookupError:
                        pass
                    stop_at = now
                if child.poll() is None and stop_at is not None and now-stop_at > 15:
                    forced = True
                    try:
                        os.killpg(child.pid, signal.SIGKILL) # Only this launched test process group.
                    except ProcessLookupError:
                        pass
            exitcode = child.wait()
    finally:
        for value, handler in previous.items():
            signal.signal(value, handler)
        if child.poll() is None:
            child.kill()
            child.wait()
    text = (report / "terminal.log").read_text(encoding="utf-8", errors="replace")
    summary = parse_summary(text)
    passed = accepted(summary, exitcode, args.expect, interrupted, timed_out, forced)
    outcome = {"child_exit_code": exitcode, "elapsed_s": time.monotonic()-start,
               "interrupted": interrupted, "timed_out": timed_out, "forced_kill": forced,
               "process_gone": not Path(f"/proc/{child.pid}").exists(),
               "automatic_functional_acceptance": passed, "summary": summary,
               "graceful_sigint_acceptance": "NOT_PASSED: current voice entry has no cooperative handler" if interrupted else "NOT_TESTED",
               "audible_output_confirmed_by_user": None,
               "leak_freedom_proven": False}
    (report / "result.json").write_text(json.dumps(outcome, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(outcome, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
