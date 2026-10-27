from pathlib import Path
import json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_baseline_2t')
with (r/'terminal.log').open() as f:print('SDK',''.join(f.readline() for _ in range(2)))
with (r/'resources.jsonl').open('rb') as f:
 f.seek(max(0,(r/'resources.jsonl').stat().st_size-25000));lines=f.read().splitlines();v=json.loads(lines[-1])
print('STATUS',v['status']);print('SYSFS',v['sysfs'])
for tid,task in v['tasks'].items():
 s=task['stat'].split();print('THREAD',tid,'ticks',int(s[13])+int(s[14]),'cpu',s[38],'allowed',task['allowed'])
print('ROWS',sum(1 for _ in (r/'tts_samples.csv').open())-1)
