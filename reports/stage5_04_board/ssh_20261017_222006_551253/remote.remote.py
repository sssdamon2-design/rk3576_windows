from pathlib import Path
import subprocess,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert json.loads((r/'reports/stage5_04_board/baseline_build_v2/result.json').read_text())['successful']
cmd=['python3','-u',str(r/'tools/stage5_04_voice_run.py'),'--name','baseline_voice_2t','--variant','baseline','--revision','v2','--tts-threads','2','--capture-fixtures','--seconds','120','--timeout','300','--grace','70']
raise SystemExit(subprocess.run(cmd,timeout=390).returncode)
