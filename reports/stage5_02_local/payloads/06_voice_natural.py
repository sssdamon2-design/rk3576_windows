from pathlib import Path
import subprocess
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
raise SystemExit(subprocess.run(['python3',str(root/'tools/stage5_02_board_run.py'),'--name','candidate_voice_natural','--seconds','90','--timeout','180','--grace','60'],timeout=260).returncode)
