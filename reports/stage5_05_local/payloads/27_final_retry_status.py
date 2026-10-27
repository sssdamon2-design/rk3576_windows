from pathlib import Path
import json
b=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
for name in ['final_matrix_retry1','real_invalid_paths','protection_final','camera_gap_recheck','final_camera_followup','protection_final_after_camera']:
 p=b/name/'result.json'
 if p.exists():
  x=json.loads(p.read_text());print('DONE',name,json.dumps({k:v for k,v in x.items() if k not in {'frozen_sources','cases','final_executable_SHA256'}},ensure_ascii=False))
for name in ['final_matrix_retry1_launcher.log','final_camera_followup_launcher.log']:
 p=b/name
 if p.exists():print('COORDINATOR_LOG',name,p.read_text()[-2400:])
for p in sorted(b.glob('final_*audio*/result.json')):
 x=json.loads(p.read_text());print('CASE',p.parent.name,x.get('returncode'),x.get('signal_to_exit_seconds'),x.get('termination_reason'))
for name in ['final_matrix_retry1/progress.json','final_camera_followup/progress.json']:
 p=b/name
 if p.exists():print('PROGRESS',name,p.read_text()[-800:])
print('TEMP',{p.parent.name:int(p.read_text())/1000 for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
