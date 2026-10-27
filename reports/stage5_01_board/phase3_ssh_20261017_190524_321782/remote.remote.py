
import io, json, os, subprocess, sys, tarfile
from pathlib import Path
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert root.is_dir() and not root.is_symlink()
reports=root/'reports/stage5_01_board'
build=root/'build/stage5_01_board'
if build.is_dir():
    output=subprocess.run(['cmake','--build',str(build),'--target','help'],capture_output=True,timeout=20)
    (reports/'phase2_targets_help.log').write_bytes(output.stdout+output.stderr)
    files=sorted(p for p in build.iterdir() if p.is_file() and not p.is_symlink() and p.read_bytes()[:4] == b'\x7fELF')
    rows=[]
    for p in files:
        r=subprocess.run(['file',str(p)],capture_output=True,timeout=5)
        rows.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'file':r.stdout.decode(errors='replace'),'exit_code':r.returncode})
    (reports/'phase2_elf_files.json').write_text(json.dumps(rows,indent=2)+'\n')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as output:
    for p in sorted(reports.rglob('*')):
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
    for name in ('CMakeCache.txt','CMakeFiles/CMakeOutput.log','CMakeFiles/CMakeError.log','CTestTestfile.cmake'):
        p=build/name
        if p.is_file() and not p.is_symlink():
            output.add(p,arcname=str(p.relative_to(root)),recursive=False)
