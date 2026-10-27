#!/usr/bin/env python3
"""Authorized phase 2 only: immutable bundle deployment and monitored ARM64 build.

No CTest, AI executable, device test, installation, or deletion is performed.
Run --prepare to inspect exact payloads, then --execute with approved networking.
"""
import argparse
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/home/cat/projects/RK3576/rk3576_multimodal_stage5_review'
ARCHIVE = 'stage5_01_review_preflight_v2.tgz'
EXPECTED = 'a653dd57e1ed5138170dd6d6ff7eb77a1518aa0e97c909402b662cab45c13c6e'
SSH = 'C:/Windows/System32/OpenSSH/ssh.exe'
SCP = 'C:/Windows/System32/OpenSSH/scp.exe'
OPTIONS = ['-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5',
           '-o', 'ConnectionAttempts=1', '-o', 'ServerAliveInterval=5',
           '-o', 'ServerAliveCountMax=2', '-o', 'StrictHostKeyChecking=yes',
           '-o', 'UpdateHostKeys=no', '-o', 'ClearAllForwardings=yes',
           '-o', 'ControlMaster=no', '-o', 'ControlPath=none',
           '-o', 'PermitLocalCommand=no', '-o', 'RemoteCommand=none']


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def fingerprint_code():
    source = (ROOT / 'tools/stage5_board_readonly_inventory.py').read_text(encoding='utf-8')
    return source.split('\ndef devices_and_owners(', 1)[0]


def payloads():
    baseline = json.loads((ROOT / 'reports/stage5_01_board/stable_original_baseline.json').read_text(encoding='utf-8'))['fingerprints']
    common = fingerprint_code() + '\nEXPECTED_BASELINE = ' + repr(baseline) + '\n'
    guard = common + '''
if os.path.lexists(REVIEW):
    print('DESTINATION_EXISTS_STOP', flush=True)
    raise SystemExit(20)
assert os.getuid() == 1000 and os.geteuid() != 0, 'ordinary cat required'
assert os.uname().machine == 'aarch64', 'ARM64 required'
assert fingerprint() == EXPECTED_BASELINE, 'original differs from approved baseline'
assert shutil.disk_usage(BASE).free >= 2147483648, 'less than 2 GiB planning reserve'
os.umask(0o077)
REVIEW.mkdir()  # exclusive: no parents=True or exist_ok=True
print('CREATED_EXCLUSIVE_ISOLATED_DIRECTORY', REVIEW, flush=True)
print('ORIGINAL_BASELINE_IDENTICAL', len(EXPECTED_BASELINE), flush=True)
'''
    extract = f'''
import hashlib, json, os, subprocess, tarfile
from pathlib import Path, PurePosixPath
root = Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink() and str(root.resolve()) == str(root)
archive = root / {ARCHIVE!r}
assert archive.is_file() and not archive.is_symlink()
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == {EXPECTED!r}, 'archive hash mismatch'
subprocess.run(['sha256sum', '-c', {ARCHIVE!r} + '.sha256'], cwd=root, check=True, timeout=10)
with tarfile.open(archive, 'r:gz') as package:
    members = package.getmembers()
    names = [m.name for m in members]
    assert len(names) == len(set(names)), 'duplicate members'
    assert len(names) == 87, 'unexpected member count'
    assert sum(m.size for m in members) < 5*1024*1024, 'unexpected expansion size'
    for m in members:
        p = PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts
        assert p.parts[0] in {{'CMakeLists.txt','README_STAGE5.txt','src','include','tests','tools','docs','SOURCE_SHA256SUMS'}}
        assert not os.path.lexists(root / m.name), 'refusing existing extraction destination'
    manifest = package.extractfile('SOURCE_SHA256SUMS').read().decode('utf-8')
    hashes = dict((name, sha) for sha, name in (line.split('  ', 1) for line in manifest.splitlines()))
    assert set(hashes) == set(names) - {{'SOURCE_SHA256SUMS'}}
    for name, sha in hashes.items():
        assert hashlib.sha256(package.extractfile(name).read()).hexdigest() == sha
subprocess.run(['tar','--keep-old-files','-xzf',archive.name], cwd=root, check=True, timeout=30)
subprocess.run(['sha256sum','-c','SOURCE_SHA256SUMS'], cwd=root, check=True, timeout=15)
report = root / 'reports/stage5_01_board'
report.mkdir(parents=True)
result = {{'archive':archive.name,'sha256':digest,'regular_members':len(names),'safe_paths':True,'all_member_hashes_match':True,'extraction_exit_code':0}}
(report / 'phase2_archive_validation.json').write_text(json.dumps(result,indent=2)+'\\n')
print('ARCHIVE_VALIDATED_AND_EXTRACTED', json.dumps(result), flush=True)
'''
    compile_payload = common + f'''
import signal
root = Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink()
assert fingerprint() == EXPECTED_BASELINE, 'original changed before compilation'
logdir = root / 'reports/stage5_01_board' / ('supervisor_' + time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()))
logdir.mkdir()
(logdir / 'stable_before.json').write_text(json.dumps(fingerprint(),indent=2)+'\\n')
command = ['timeout','--signal=TERM','--kill-after=15s','840s','bash',str(root/'tools/stage5_board_compile_only.sh')]
(logdir/'command.json').write_text(json.dumps(command,indent=2)+'\\n')
process = subprocess.Popen(command, start_new_session=True)
started = time.monotonic()
reason = None
minimum = shutil.disk_usage(root).free
with (logdir/'disk_samples.jsonl').open('x') as samples:
    while process.poll() is None:
        available = shutil.disk_usage(root).free
        minimum = min(minimum, available)
        samples.write(json.dumps({{'unix_time':time.time(),'free_bytes':available}})+'\\n')
        samples.flush()
        if available < 500*1024*1024:
            reason = 'DISK_BELOW_500_MiB'
        elif time.monotonic()-started > 840:
            reason = 'SUPERVISOR_TIMEOUT_840_SECONDS'
        if reason:
            print('STOP_BUILD',reason,flush=True)
            # Only this build's new process group, never unrelated processes.
            try:
                os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid,signal.SIGKILL)
                process.wait(timeout=10)
            break
        time.sleep(1)
child_code = process.wait()
after = fingerprint()
unchanged = after == EXPECTED_BASELINE
(logdir/'stable_after.json').write_text(json.dumps(after,indent=2)+'\\n')
result = {{'build_process_exit_code':child_code,'stop_reason':reason,'original_321_entries_unchanged':unchanged,'minimum_disk_free_bytes':minimum,'final_disk_free_bytes':shutil.disk_usage(root).free,'duration_seconds':time.monotonic()-started,'ctest_executed':False,'ai_programs_started':False}}
code = 90 if reason == 'DISK_BELOW_500_MiB' else 124 if reason else child_code
if not unchanged:
    code = 91
result['supervisor_exit_code'] = code
(logdir/'result.json').write_text(json.dumps(result,indent=2)+'\\n')
print('PHASE2_SUPERVISOR_RESULT',json.dumps(result),flush=True)
raise SystemExit(code if 0 <= code <= 255 else 1)
'''
    collect = f'''
import io, json, os, subprocess, sys, tarfile
from pathlib import Path
root=Path({REMOTE!r})
assert root.is_dir() and not root.is_symlink()
reports=root/'reports/stage5_01_board'
build=root/'build/stage5_01_board'
if build.is_dir():
    output=subprocess.run(['cmake','--build',str(build),'--target','help'],capture_output=True,timeout=20)
    (reports/'phase2_targets_help.log').write_bytes(output.stdout+output.stderr)
    files=sorted(p for p in build.iterdir() if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b'\\x7fELF')
    rows=[]
    for p in files:
        r=subprocess.run(['file',str(p)],capture_output=True,timeout=5)
        rows.append({{'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'file':r.stdout.decode(errors='replace'),'exit_code':r.returncode}})
    (reports/'phase2_elf_files.json').write_text(json.dumps(rows,indent=2)+'\\n')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as output:
    for p in sorted(reports.rglob('*')):
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
    for name in ('CMakeCache.txt','CMakeFiles/CMakeOutput.log','CMakeFiles/CMakeError.log','CTestTestfile.cmake'):
        p=build/name
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
'''
    return {'01_create':guard,'03_validate_extract':extract,'04_compile':compile_payload,'05_collect':collect}


def remote_command():
    return [SSH, '-T', *OPTIONS, 'cat@192.168.10.27', 'python3 -I -B -']


def run_step(report, name, command, payload=None, timeout=60, binary=False):
    dump(report / (name+'.command.json'), command)
    if payload is not None:
        (report/(name+'.remote.py')).write_bytes(payload)
    out = report/(name+('.tgz' if binary else '.stdout.log'))
    err = report/(name+'.stderr.log')
    timed_out=False
    with out.open('xb') as stdout, err.open('xb') as stderr:
        process=subprocess.Popen(command, stdin=subprocess.PIPE if payload else subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        try:
            process.communicate(payload, timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            process.kill()  # local SSH only; remote build supervisor remains bounded
            process.communicate()
    result={'exit_code':process.returncode,'local_timeout':timed_out,'remote_exit_known':not timed_out and process.returncode!=255}
    dump(report/(name+'.execution.json'),result)
    print(name,json.dumps(result),flush=True)
    return process.returncode if not timed_out else 124


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    assert args.prepare != args.execute, 'choose exactly one action'
    package=ROOT/'reports/stage5_01_local/board_package'/ARCHIVE
    assert hashlib.sha256(package.read_bytes()).hexdigest()==EXPECTED
    scripts=payloads()
    for source in scripts.values():
        compile(source,'<remote>','exec')
    if args.prepare:
        destination=ROOT/'reports/stage5_01_local/phase2_execution_plan'
        destination.mkdir(exist_ok=True)
        for name,source in scripts.items():
            (destination/(name+'.py')).write_text(source,encoding='utf-8')
        print('Prepared four syntax-checked payloads; immutable 126256-byte archive verified. No remote action.')
        return 0
    report=ROOT/'reports/stage5_01_board'/('phase2_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    dump(report/'scope.json',{'authorization':'User approved phase 2 isolated deploy/compile only','remote_root':REMOTE,'archive':ARCHIVE,'sha256':EXPECTED,'ctest':False,'hardware_tests':False,'disk_stop_below_bytes':500*1024*1024})
    code=run_step(report,'01_create',remote_command(),scripts['01_create'].encode(),60)
    if code:
        return code
    code=run_step(report,'02_upload',[SCP,'-S',SSH,*OPTIONS,str(package),str(package)+'.sha256','cat@192.168.10.27:'+REMOTE+'/'],timeout=90)
    if code:
        return code
    code=run_step(report,'03_validate_extract',remote_command(),scripts['03_validate_extract'].encode(),90)
    if code:
        return code
    build_code=run_step(report,'04_compile',remote_command(),scripts['04_compile'].encode(),900)
    collect_code=run_step(report,'05_collect',remote_command(),scripts['05_collect'].encode(),90,binary=True)
    if collect_code==0:
        destination=report/'collected'
        destination.mkdir()
        with tarfile.open(report/'05_collect.tgz','r:gz') as archive:
            for member in archive.getmembers():
                p=PurePosixPath(member.name)
                assert member.isfile() and not p.is_absolute() and '..' not in p.parts
                target=destination/Path(*p.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as output:
                    output.write(archive.extractfile(member).read())
    dump(report/'result.json',{'compile_ssh_exit_code':build_code,'collection_ssh_exit_code':collect_code,'ctest_executed':False,'hardware_tests_executed':False})
    print('REPORT_DIRECTORY',str(report.relative_to(ROOT)),flush=True)
    return build_code or collect_code


if __name__=='__main__':
    raise SystemExit(main())
