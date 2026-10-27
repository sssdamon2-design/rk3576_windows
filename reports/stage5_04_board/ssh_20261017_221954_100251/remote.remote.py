from pathlib import Path
import subprocess
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
p=r/'reports/stage5_04_board/baseline_build_v2'
for x in ('build.stdout.log','build.stderr.log','result.json'):
 f=p/x
 if f.exists():print(x,f.read_text()[-3000:])
print(subprocess.check_output(['ps','-eo','pid,ppid,pcpu,etime,args'],text=True)[-12000:])
