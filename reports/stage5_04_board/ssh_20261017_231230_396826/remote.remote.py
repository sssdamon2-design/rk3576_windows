from pathlib import Path
import subprocess,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert json.loads((r/'reports/stage5_04_board/candidate_build_v3/result.json').read_text())['successful']
cmd=['python3','-u',str(r/'tools/stage5_04_voice_run.py'),'--name','candidate_voice_4t_final_retry1','--variant','candidate','--revision','v3','--tts-threads','4','--seconds','120','--signal','SIGINT','--trigger','both_done','--delay','0.2','--timeout','300','--grace','70']
raise SystemExit(subprocess.run(cmd,timeout=390).returncode)
