from pathlib import Path
import json,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
for p in sorted(r.glob('gui_*/result.json')):
 x=json.loads(p.read_text());print('GUI_DONE',p.parent.name,{k:x[k] for k in ['returncode','duration_seconds','all_sessions_orderly','forced_kill','devices_released']})
for p in r.glob('gui_*/run_*/resources.jsonl'):
 print('BACKEND_SAMPLES',str(p.relative_to(r)),sum(1 for _ in p.open()))
for p in [r/'final_matrix_launcher.log',r/'final_matrix/progress.json']:
 if p.exists():
  if p.suffix=='.log':print('MATRIX_LOG',p.read_text()[-1500:])
  else:print('MATRIX_PROGRESS',[x['case'] for x in json.loads(p.read_text())])
for p in r.glob('gui_*/pid.json'):
 x=json.loads(p.read_text());proc=Path('/proc')/str(x['pid'])
 if proc.exists():print('RUNNING',p.parent.name,x['pid'],(proc/'status').read_text().split('VmRSS:')[-1][:100])
print('TEMPS',{p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
