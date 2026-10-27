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


import sys
assert os.getuid()==1000 and REVIEW.is_dir() and not REVIEW.is_symlink()
report=REVIEW/'reports/stage5_03_board';report.mkdir()
sys.path.insert(0,str(REVIEW/'tools'))
from stage5_02_board_run import discover_audio,devices
assert devices(discover_audio())['clear'],'resources occupied'
assert shutil.disk_usage(REVIEW).free>=500*1024**2
before=fingerprint()
accepted=REVIEW/'reports/stage5_02_board/final_state_v2/source_sha256.json'
expected=json.loads(accepted.read_text());assert all(hashlib.sha256((REVIEW/p).read_bytes()).hexdigest()==digest for p,digest in expected.items())
snapshot=report/'baseline_5_2_source';snapshot.mkdir()
for name in expected:
 p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REVIEW/name,p)
(report/'original_before.json').write_text(json.dumps(before,indent=2))
executables=['build/stage5_01_board/asr_llm_tts_smoke','build/stage5_02_board/asr_llm_tts_smoke']
(report/'accepted_binaries_before.json').write_text(json.dumps({name:hashlib.sha256((REVIEW/name).read_bytes()).hexdigest() for name in executables},indent=2))
commands=[['uname','-a'],['free','-b'],['df','-B1',str(REVIEW)],['v4l2-ctl','-d','/dev/video11','--get-fmt-video'],['v4l2-ctl','-d','/dev/video11','--get-parm'],['ldconfig','-p'],['ls','-l','/dev/rga','/dev/dma_heap'],['dpkg-query','-W','*rga*']]
results=[run(cmd) for cmd in commands]
for row in results:
 if row['command'][0]=='ldconfig' and 'stdout' in row:row['stdout']='\n'.join(x for x in row['stdout'].splitlines() if 'rga' in x.lower())
headers=[]
for start in [Path('/usr/include/rga'),Path('/usr/local/include/rga'),Path('/usr/include/librga'),Path('/usr/local/include/librga')]:
 if start.is_dir():
  for p in start.rglob('*.h'):
   if p.is_file() and p.stat().st_size<300000:headers.append({'path':str(p),'text':p.read_text(errors='replace')})
for p in [Path('/home/cat/projects/RK3576/rknn_test/include/rknn_api.h')]:
 headers.append({'path':str(p),'text':p.read_text(errors='replace')})
libs=[]
for pattern in ['/usr/lib/librga*','/usr/lib/aarch64-linux-gnu/librga*','/usr/local/lib/librga*']:
 libs.extend({'path':p,'resolved':str(Path(p).resolve()),'bytes':Path(p).stat().st_size} for p in glob.glob(pattern))
(report/'readonly_environment.json').write_text(json.dumps({'commands':results,'libraries':libs,'headers':headers,'disk_free_bytes':shutil.disk_usage(REVIEW).free,'original_321_unchanged':before==fingerprint()},indent=2))
print(json.dumps({'commands':results,'libraries':libs,'headers':[h['path'] for h in headers],'disk_free_bytes':shutil.disk_usage(REVIEW).free,'original_321_unchanged':before==fingerprint()},indent=2),flush=True)
