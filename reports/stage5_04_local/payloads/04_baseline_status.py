from pathlib import Path
import json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_baseline_2t')
for n in ['terminal.log','tts_samples.csv','stderr.log']:
 p=r/n
 if p.exists():
  with p.open('rb') as f:f.seek(max(0,p.stat().st_size-1800));print(n,f.read().decode(errors='replace'))
p=r/'result.json'
if p.exists():print('RESULT',p.read_text())
