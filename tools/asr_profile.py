
#!/usr/bin/env python3
"""RK3576 ASR / VAD / Camera profiling tool."""

import argparse
import codecs
import json
import os
import pty
import re
import select
import signal
import statistics
import subprocess
import time

from datetime import datetime
from pathlib import Path


def percentile(values, p):
    """Calculate percentile with linear interpolation."""
    if not values:
        return None

    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100

    low = int(position)
    high = min(low + 1, len(ordered) - 1)

    value = ordered[low] + (
        ordered[high] - ordered[low]
    ) * (position - low)

    return round(value, 3)


def read_process(pid):
    """
    Read Linux process statistics.

    CPU: user + system clock ticks.
    VmRSS: current physical memory.
    VmHWM: peak resident memory.
    """
    try:
        stat = Path(
            f"/proc/{pid}/stat"
        ).read_text()

        # comm is enclosed in parentheses.
        fields = stat[
            stat.rfind(")") + 2:
        ].split()

        cpu_ticks = (
            int(fields[11]) +
            int(fields[12])
        )

        rss = 0
        hwm = 0

        status = Path(
            f"/proc/{pid}/status"
        ).read_text().splitlines()

        for line in status:
            if line.startswith("VmRSS:"):
                rss = int(line.split()[1])

            elif line.startswith("VmHWM:"):
                hwm = int(line.split()[1])

        return cpu_ticks, rss, hwm

    except (OSError, ValueError, IndexError):
        return None


def run_once(args, index, destination):

    command = [
        args.binary,
        args.device,
        args.model,
        args.vad,
    ]

    if args.camera:
        command.append(args.camera)

    env = os.environ.copy()

    runtime_lib = str(
        Path(args.runtime) / "lib"
    )

    old_library_path = env.get(
        "LD_LIBRARY_PATH", ""
    )

    env["LD_LIBRARY_PATH"] = (
        runtime_lib +
        (":" + old_library_path
         if old_library_path else "")
    )

    # Pseudo-terminal enables timely line output.
    master, slave = pty.openpty()

    begin = time.monotonic()

    try:
        child = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=slave,
            stderr=slave,
            start_new_session=True,
            env=env,
        )
    finally:
        os.close(slave)

    print(
        f"\n===== Run {index}/{args.runs}"
        f" | PID={child.pid} =====",
        flush=True
    )

    decoder = codecs.getincrementaldecoder(
        "utf-8"
    )("replace")

    buffer = ""
    lines = []

    records = []
    vad_events = {}
    asr_events = []
    summary = {}

    cpu_samples = []
    mem_samples = []

    sample_interval = 0.5

    ticks_per_second = os.sysconf(
        "SC_CLK_TCK"
    )

    previous = read_process(child.pid)
    previous_at = time.monotonic()
    last_sample = previous_at

    timed_out = False

    def collect_line(raw_line, timestamp):
        line = raw_line.rstrip("\r")

        if not line:
            return

        print(line, flush=True)
        lines.append(line)

        # Parse VAD segment event.
        match = re.search(
            r"\[VAD\] Speech #(\d+)"
            r" duration=([\d.]+) s",
            line
        )

        if match:
            number = int(match.group(1))
            vad_events[number] = timestamp

        # Parse ASR model latency and RTF.
        match = re.search(
            r"\[ASR\] Segment #(\d+):.*?"
            r"\| latency=([\d.]+) ms"
            r" \| RTF=([\d.]+)",
            line
        )

        if match:
            number = int(match.group(1))

            vad_to_asr = None

            if number in vad_events:
                vad_to_asr = round(
                    (
                        timestamp -
                        vad_events[number]
                    ) * 1000,
                    2
                )

            asr_events.append({
                "segment": number,
                "latency_ms": float(
                    match.group(2)
                ),
                "rtf": float(
                    match.group(3)
                ),
                "vad_log_to_asr_log_ms":
                    vad_to_asr,
            })

        # Parse application summary.
        match = re.match(
            r"^(Detected|Recognized|Routed|"
            r"TEXT|VISION|Dropped|"
            r"Vision frame seen|Wall time):"
            r"\s*(.+)",
            line
        )

        if match:
            summary[
                match.group(1)
            ] = match.group(2)

    try:
        while True:
            now = time.monotonic()

            # Stop a hung run safely.
            if now - begin > args.timeout:
                timed_out = True

                if child.poll() is None:
                    os.killpg(
                        child.pid,
                        signal.SIGTERM
                    )

                break

            readable, _, _ = select.select(
                [master], [], [], 0.2
            )

            if readable:
                try:
                    data = os.read(
                        master, 8192
                    )
                except OSError:
                    data = b""

                if not data:
                    break

                buffer += decoder.decode(data)

                while "\n" in buffer:
                    one, buffer = buffer.split(
                        "\n", 1
                    )

                    collect_line(
                        one,
                        time.monotonic()
                    )

            now = time.monotonic()

            # Sample /proc once every 0.5 s.
            if now - last_sample >= sample_interval:

                current = read_process(
                    child.pid
                )

                if current is not None:
                    _, rss, hwm = current

                    mem_samples.append(
                        (rss, hwm)
                    )

                    cpu_pct = None

                    if previous is not None:
                        elapsed = (
                            now - previous_at
                        )

                        if elapsed > 0:
                            cpu_pct = (
                                current[0] -
                                previous[0]
                            ) * 100 / (
                                ticks_per_second *
                                elapsed
                            )

                            cpu_samples.append(
                                cpu_pct
                            )

                    records.append({
                        "time_s": round(
                            now - begin, 3
                        ),
                        "cpu_pct_one_core_100":
                            round(cpu_pct, 2)
                            if cpu_pct is not None
                            else None,
                        "rss_mib": round(
                            rss / 1024, 2
                        ),
                        "hwm_mib": round(
                            hwm / 1024, 2
                        ),
                    })

                    previous = current
                    previous_at = now

                last_sample = now

    except KeyboardInterrupt:
        print(
            "\nInterrupted: stopping child process",
            flush=True
        )

        timed_out = True

        if child.poll() is None:
            os.killpg(
                child.pid,
                signal.SIGTERM
            )

    finally:
        tail = (
            decoder.decode(
                b"", final=True
            ) + buffer
        )

        if tail.strip():
            collect_line(
                tail,
                time.monotonic()
            )

        os.close(master)

        try:
            exitcode = child.wait(
                timeout=5
            )
        except subprocess.TimeoutExpired:
            os.killpg(
                child.pid,
                signal.SIGKILL
            )
            exitcode = child.wait()

    # Save full original console output.
    log_file = destination / (
        f"run_{index:02d}.log"
    )

    log_file.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )

    # Save CPU / memory samples.
    telemetry_file = destination / (
        f"run_{index:02d}_telemetry.json"
    )

    telemetry_file.write_text(
        json.dumps(
            records,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return {
        "run": index,
        "exitcode": exitcode,
        "timed_out": timed_out,
        "wall_time_s": round(
            time.monotonic() - begin, 2
        ),
        "summary": summary,
        "asr_events": asr_events,
        "avg_process_cpu_pct": (
            round(
                statistics.mean(
                    cpu_samples
                ), 2
            ) if cpu_samples else None
        ),
        "peak_process_cpu_pct": (
            round(
                max(cpu_samples), 2
            ) if cpu_samples else None
        ),
        "peak_rss_mib": (
            round(
                max(
                    m[1] for m in mem_samples
                ) / 1024,
                2
            ) if mem_samples else None
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "RK3576 ASR/VAD/Camera profiler"
        )
    )

    parser.add_argument(
        "--runtime", required=True
    )
    parser.add_argument(
        "--model", required=True
    )
    parser.add_argument(
        "--vad", required=True
    )
    parser.add_argument(
        "--device", default="plughw:3,0"
    )
    parser.add_argument(
        "--camera", default=None
    )
    parser.add_argument(
        "--binary",
        default="./build/asr/asr_route_smoke"
    )
    parser.add_argument(
        "--runs", type=int, default=1
    )
    parser.add_argument(
        "--timeout", type=float, default=90.0
    )
    parser.add_argument(
        "--output", default="reports"
    )
    parser.add_argument(
        "--mode",
        choices=("speech", "silence"),
        default="speech"
    )

    args = parser.parse_args()

    if args.runs < 1 or args.timeout <= 0:
        parser.error(
            "--runs and --timeout must be positive"
        )

    for path in (
        args.runtime,
        args.model,
        args.vad,
        args.binary
    ):
        if not Path(path).exists():
            parser.error(
                f"Not found: {path}"
            )

    destination = Path(
        args.output
    ) / (
        "op10_" +
        datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )
    )

    destination.mkdir(
        parents=True,
        exist_ok=False
    )

    print(
        "Report directory:",
        destination.resolve()
    )

    if args.mode == "silence":
        print(
            "SILENCE CONTROL: stay quiet "
            "during each 20-second run."
        )
        print(
            "The smoke executable may print FAIL "
            "when no speech is detected."
        )
    else:
        print(
            "SPEECH: say both TEXT and VISION "
            "questions during each run."
        )

    runs = []

    for number in range(
        1, args.runs + 1
    ):
        runs.append(
            run_once(
                args,
                number,
                destination
            )
        )

    latencies = [
        event["latency_ms"]
        for run in runs
        for event in run["asr_events"]
    ]

    rtfs = [
        event["rtf"]
        for run in runs
        for event in run["asr_events"]
    ]

    vad_to_asr = [
        event["vad_log_to_asr_log_ms"]
        for run in runs
        for event in run["asr_events"]
        if event[
            "vad_log_to_asr_log_ms"
        ] is not None
    ]

    rss_values = [
        run["peak_rss_mib"]
        for run in runs
        if run["peak_rss_mib"]
        is not None
    ]

    cpu_values = [
        run["avg_process_cpu_pct"]
        for run in runs
        if run["avg_process_cpu_pct"]
        is not None
    ]

    aggregate = {
        "asr_segments": len(latencies),

        "asr_latency_mean_ms": (
            round(
                statistics.mean(
                    latencies
                ), 2
            ) if latencies else None
        ),

        "asr_latency_p50_ms":
            percentile(latencies, 50),

        "asr_latency_p95_ms":
            percentile(latencies, 95),

        "rtf_mean": (
            round(
                statistics.mean(
                    rtfs
                ), 3
            ) if rtfs else None
        ),

        "vad_log_to_asr_log_p50_ms":
            percentile(vad_to_asr, 50),

        "vad_log_to_asr_log_p95_ms":
            percentile(vad_to_asr, 95),

        "max_process_rss_mib": (
            max(rss_values)
            if rss_values else None
        ),

        "mean_process_cpu_pct": (
            round(
                statistics.mean(
                    cpu_values
                ), 2
            ) if cpu_values else None
        ),
    }

    details = {
        "mode": args.mode,
        "runs": runs,
        "aggregate": aggregate,
    }

    report = (
        destination / "summary.json"
    )

    report.write_text(
        json.dumps(
            details,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(
        "\n=== OP10 PROFILING SUMMARY ==="
    )

    for key, value in aggregate.items():
        print(
            f"{key}: {value}"
        )

    print(
        f"Report: {report.resolve()}"
    )

    if len(latencies) < 20:
        print(
            "NOTE: Fewer than 20 ASR segments. "
            "P95 is descriptive only."
        )

    for run in runs:
        summary = run["summary"]

        print(
            f"Run {run['run']}: "
            f"exit={run['exitcode']}, "
            f"detected={summary.get('Detected', '?')}, "
            f"routed={summary.get('Routed', '?')}, "
            f"dropped={summary.get('Dropped', '?')}"
        )


if __name__ == "__main__":
    main()
