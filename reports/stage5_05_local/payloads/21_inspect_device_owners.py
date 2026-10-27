from pathlib import Path
import json,subprocess
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
p=r/'final_burst_audio/devices_before.json';x=json.loads(p.read_text());print(json.dumps(x,indent=2));
for value in x['query']['stdout'].split():
 if value.isdigit():
  pid=Path('/proc')/value
  if pid.exists():print('OWNER',value,(pid/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),(pid/'exe').resolve())
