#!/usr/bin/env python3
"""Run only the user-authorized read-only RK3576 guard/inspection over SSH."""
import argparse
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("guard", "full"), required=True)
    parser.add_argument("--occupancy-only", action="store_true")
    parser.add_argument("--target-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    client = Path("C:/Windows/System32/OpenSSH/ssh.exe")
    destination = "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review"
    guard = (f"if [ -e '{destination}' ] || [ -L '{destination}' ]; then "
             "printf 'DESTINATION_EXISTS_STOP\\n'; exit 20; fi; "
             "printf 'DESTINATION_ABSENT\\n'; printf 'SSH_READONLY_CONNECTED\\n'; "
             "uname -m; uname -r; id; date -Is")
    payload = None
    remote_command = guard
    if args.phase == "full":
        inspection = (root / "tools/stage5_board_readonly_inventory.py").read_bytes()
        if args.occupancy_only:
            inspection = inspection.split(b'if __name__ == "__main__":', 1)[0]
            call = "devices_and_owners(target_only=True)" if args.target_only else "devices_and_owners()"
            inspection += ('print("STAGE5_READONLY_JSON_BEGIN")\n'
                           'print(json.dumps({"resource_occupancy": ' + call + ', '
                           '"review_directory_absent_after": not os.path.lexists(REVIEW)}, indent=2))\n'
                           'print("STAGE5_READONLY_JSON_END")\n').encode("ascii")
        payload = ("set -eu\n" + guard + "\npython3 -I -B - <<'STAGE5_READONLY_PY'\n").encode("ascii")
        payload += inspection + b"\nSTAGE5_READONLY_PY\n"
        remote_command = "timeout 120s bash -s"
    command = [str(client), "-T", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
               "-o", "ConnectionAttempts=1", "-o", "ServerAliveInterval=5",
               "-o", "ServerAliveCountMax=2", "-o", "StrictHostKeyChecking=yes",
               "-o", "UpdateHostKeys=no", "-o", "ClearAllForwardings=yes",
               "-o", "ControlMaster=no", "-o", "ControlPath=none",
               "-o", "PermitLocalCommand=no", "-o", "RemoteCommand=none",
               "cat@192.168.10.27", remote_command]
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S_%f")
    report = root / "reports/stage5_01_board" / ("readonly_" + args.phase + "_" + stamp)
    report.mkdir(parents=True)
    (report / "command.json").write_text(json.dumps(command, indent=2) + "\n", encoding="utf-8")
    if payload is not None:
        (report / "inspection_script.sh").write_bytes(payload)
    timed_out = False
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        stdout, stderr = process.communicate(payload, timeout=30 if args.phase == "guard" else 150)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.kill() # Only the local SSH client; no remote process kill command.
        stdout, stderr = process.communicate()
    (report / "stdout.log").write_bytes(stdout)
    (report / "stderr.log").write_bytes(stderr)
    outcome = {
        "phase": args.phase, "ssh_process_exit_code": process.returncode,
        "occupancy_only": args.occupancy_only,
        "target_only": args.target_only,
        "local_client_timeout": timed_out,
        "remote_command_exit_known": not timed_out and process.returncode != 255,
        "destination_exists_stop": b"DESTINATION_EXISTS_STOP" in stdout,
        "destination_absent_observed": b"DESTINATION_ABSENT" in stdout,
        "ssh_connection_confirmed": b"SSH_READONLY_CONNECTED" in stdout,
        "scope": "Only authorized read-only inspection; no remote file writes/builds/program tests",
        "payload_sha256": hashlib.sha256(payload).hexdigest() if payload else None,
        "report_directory": str(report.relative_to(root)),
    }
    (report / "execution.json").write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    decoded = stdout.decode("utf-8", errors="replace")
    if args.phase == "full" and "STAGE5_READONLY_JSON_BEGIN" in decoded:
        value = json.loads(decoded.split("STAGE5_READONLY_JSON_BEGIN", 1)[1].split("STAGE5_READONLY_JSON_END", 1)[0])
        (report / "inventory.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        occupancy = value.get("resource_occupancy", {})
        query = occupancy.get("sudo_readonly_fuser") or {}
        print(json.dumps({"checks": value.get("checks"),
                          "all_listed_nodes_clear_confirmed": occupancy.get("all_listed_nodes_clear_confirmed"),
                          "fuser_exit_code": query.get("exit_code"),
                          "fuser_stdout": query.get("stdout"), "fuser_stderr": query.get("stderr"),
                          "npu_node_identified": occupancy.get("npu_node_identified"),
                          "camera_sysfs_names": occupancy.get("camera_sysfs_names"),
                          "camera_service_process": occupancy.get("camera_service_process"),
                          "review_directory_absent_after": value.get("review_directory_absent_after")}, indent=2))
    else:
        print(decoded, end="")
    if stderr:
        print("--- SSH stderr ---\n" + stderr.decode("utf-8", errors="replace"), end="")
    print("\n" + json.dumps(outcome, indent=2))
    return process.returncode if process.returncode is not None and not timed_out else 124


if __name__ == "__main__":
    raise SystemExit(main())
