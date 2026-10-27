
#!/usr/bin/env python3

"""RK3576 Operation 10: VAD / ASR timing report."""

import argparse
import json
import math
import re
from pathlib import Path
from statistics import mean


# 支持普通小数、负数及科学计数法。
# 例如：
# 0.162322
# 8.3e-05
# 1.2E+03
NUMBER = (
    r"[-+]?"
    r"(?:\d+(?:\.\d*)?|\.\d+)"
    r"(?:[eE][-+]?\d+)?"
)

FIELDS = (
    "endpoint_est_ms",
    "vad_to_queue_ms",
    "queue_wait_ms",
    "preprocess_ms",
    "asr_wall_ms",
    "total_est_ms",
)


def percentile(values, percent):
    if not values:
        return None

    ordered = sorted(values)

    position = (
        (len(ordered) - 1)
        * percent / 100.0
    )

    low = int(position)
    high = min(low + 1, len(ordered) - 1)

    value = (
        ordered[low]
        + (ordered[high] - ordered[low])
        * (position - low)
    )

    return value


def metric_stats(values, digits=3):
    if not values:
        return {
            "mean": None,
            "p50": None,
            "p95": None,
        }

    return {
        "mean": round(mean(values), digits),
        "p50": round(
            percentile(values, 50),
            digits
        ),
        "p95": round(
            percentile(values, 95),
            digits
        ),
    }


def parse_timing_line(line):
    result = {}

    for field in FIELDS:
        pattern = (
            r"(?<!\w)"
            + re.escape(field)
            + r"=(" + NUMBER + r")"
            + r"(?=\s|$)"
        )

        match = re.search(pattern, line)

        if not match:
            return None

        value = float(match.group(1))

        if not math.isfinite(value):
            return None

        result[field] = value

    return result


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate RK3576 ASR timing statistics"
        )
    )

    parser.add_argument(
        "report_directory",
        type=Path
    )

    args = parser.parse_args()

    if not args.report_directory.is_dir():
        parser.error(
            "Report directory does not exist"
        )

    logs = sorted(
        args.report_directory.glob("run_*.log")
    )

    if not logs:
        parser.error(
            "No run_XX.log files found"
        )

    samples = {
        field: [] for field in FIELDS
    }

    xrun = 0
    suspended = 0
    recoveries = 0
    failures = 0

    routing_passed = 0
    alsa_reported_runs = 0
    incomplete_timings = 0
    consistency_errors = []

    for path in logs:
        content = path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        if re.search(
            r"^PASS\s*$",
            content,
            re.MULTILINE
        ):
            routing_passed += 1

        has_alsa_stats = False

        for line in content.splitlines():

            # ==============================
            # 1. 分阶段耗时
            # ==============================

            if line.startswith(
                "[Timing] Segment #"
            ):
                timing = parse_timing_line(line)

                if timing is None:
                    incomplete_timings += 1
                    continue

                for field in FIELDS:
                    samples[field].append(
                        timing[field]
                    )

                # 验证各阶段总和与 total 一致。
                stage_sum = sum(
                    timing[key]
                    for key in FIELDS
                    if key != "total_est_ms"
                )

                difference = abs(
                    stage_sum
                    - timing["total_est_ms"]
                )

                consistency_errors.append(
                    difference
                )

            # ==============================
            # 2. ALSA 错误统计
            # ==============================

            if line.startswith(
                "[ALSA] XRUN="
            ):
                match = re.search(
                    r"XRUN=(\d+)\s+"
                    r"Suspends=(\d+)\s+"
                    r"Recoveries=(\d+)\s+"
                    r"RecoveryFailures=(\d+)",
                    line
                )

                if match:
                    has_alsa_stats = True

                    xrun += int(match.group(1))
                    suspended += int(match.group(2))
                    recoveries += int(match.group(3))
                    failures += int(match.group(4))

        if has_alsa_stats:
            alsa_reported_runs += 1

    # ==================================
    # 3. 汇总所有时间样本
    # ==================================

    metrics = {}

    for field in FIELDS:

        # 极短耗时保留 6 位小数，
        # 防止被四舍五入成 0.00 ms。
        digits = (
            6
            if field in (
                "vad_to_queue_ms",
                "preprocess_ms",
                "queue_wait_ms",
            )
            else 3
        )

        metrics[field] = metric_stats(
            samples[field],
            digits
        )

    result = {
        "runs": len(logs),

        "routing_passed_runs": routing_passed,

        "timing_samples": len(
            samples["total_est_ms"]
        ),

        "incomplete_timing_lines":
            incomplete_timings,

        "alsa_reported_runs":
            alsa_reported_runs,

        "observed_alsa_xrun": xrun,

        "observed_alsa_suspend":
            suspended,

        "alsa_recoveries":
            recoveries,

        "alsa_recovery_failures":
            failures,

        "max_stage_sum_error_ms": (
            round(
                max(consistency_errors),
                6
            )
            if consistency_errors
            else None
        ),

        "metrics_ms": metrics,

        "note": (
            "Audio segment end is estimated "
            "from the host ALSA read clock. "
            "Not a hardware timestamp and "
            "not full LLM/VLM/TTS latency."
        )
    }

    # ==================================
    # 4. 保存 JSON
    # ==================================

    output = (
        args.report_directory
        / "op10_final_timing.json"
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        ) + "\n",
        encoding="utf-8"
    )

    print(
        "\n=== OP10 FINAL TIMING REPORT ==="
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )

    print(f"\nSaved: {output}")

    if result["timing_samples"] < 20:
        print(
            "NOTE: Timing sample count is "
            "below 20; P95 is descriptive only."
        )

    if alsa_reported_runs != len(logs):
        print(
            "WARNING: Some runs have no "
            "ALSA statistics line."
        )

    if incomplete_timings:
        print(
            "WARNING: Some timing lines "
            "could not be parsed."
        )


if __name__ == "__main__":
    main()
