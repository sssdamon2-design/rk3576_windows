from pathlib import Path
import json,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');p=r/'reports/stage5_04_board'
for name in ['raw_tts_final_4t','candidate_asr_30','candidate_vision_30','baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
 f=p/name
 if not f.exists():continue
 if (f/'result.json').exists():print(name,'COMPLETE',(f/'result.json').read_text())
 else:
  print(name,'IN_PROGRESS')
  for leaf in ['tts_samples.csv','asr_samples.csv','vision_samples.csv','terminal.log']:
   log=f/leaf
   if log.exists():print(leaf,log.read_text(errors='replace').splitlines()[-2:])
