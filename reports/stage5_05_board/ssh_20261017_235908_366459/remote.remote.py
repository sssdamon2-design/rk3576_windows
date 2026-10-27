from pathlib import Path
import json,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
for p in sorted(r.glob('mixed_*/result.json')):
 x=json.loads(p.read_text());print('DONE',p.parent.name,{k:x[k] for k in ['returncode','duration_seconds','termination_reason','forced_kill','devices_released']})
for p in sorted(r.glob('mixed_*/pid.json')):
 x=json.loads(p.read_text());proc=Path('/proc')/str(x['pid'])
 if proc.exists():
  print('RUNNING',p.parent.name,'PID',x['pid'],[(s.split(':',1)[0],s.split(':',1)[1].strip()) for s in (proc/'status').read_text().splitlines() if s.split(':')[0] in {'VmRSS','VmHWM','Threads'}])
  terminal=p.parent/'terminal.log'
  with terminal.open('rb') as f:f.seek(max(0,terminal.stat().st_size-1200));print(f.read().decode(errors='replace'))
print('TEMPERATURES_C',{p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
print('COOLING',{p.parent.name:p.read_text().strip() for p in Path('/sys/class/thermal').glob('cooling_device*/cur_state')})
print('MATRIX_COMPLETE',(r/'thermal_matrix/result.json').exists())
