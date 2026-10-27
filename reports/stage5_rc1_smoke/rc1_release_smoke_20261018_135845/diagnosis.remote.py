from pathlib import Path
import sys,subprocess,json,base64
R=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(R/'tools'))
from stage5_05_voice_run import discover_audio
report=R/'reports/stage5_rc1_board/rc1_release_smoke_20261018_135845';a=discover_audio()
commands=[['ps','-eo','pid,uid,comm,args'],['amixer','-c',str(a['card_number']),'scontents'],['who']]
results=[]
for cmd in commands:
 r=subprocess.run(cmd,capture_output=True,timeout=15);out=r.stdout.decode(errors='replace')
 if cmd[0]=='ps':out='\n'.join(s for s in out.splitlines() if any(x in s.lower() for x in ['xorg','vnc','xwayland','xsession','gnome-session','xfce','rk3576_multimodal_gui']))
 results.append({'command':cmd,'returncode':r.returncode,'stdout':out,'stderr':r.stderr.decode(errors='replace')})
results.append({'X11_sockets':[str(x) for x in Path('/tmp/.X11-unix').glob('*')]})
with (report/'diagnosis_readonly.json').open('x') as f:json.dump(results,f,indent=2)
print('DIAGNOSIS',json.dumps(results),flush=True)
run=R/'reports/stage5_05_board/rc1_release_smoke_20261018_135845'
images=list(run.glob('run_*/listening.png'))
print('SCREENSHOTS',json.dumps([str(x) for x in images]),flush=True)
for p in images:print('IMAGE',base64.b64encode(p.read_bytes()).decode(),flush=True)
