from pathlib import Path
import subprocess
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
raise SystemExit(subprocess.run(['python3',str(root/'tools/stage5_02_board_run.py'),'--name','candidate_voice_burst','--seconds','60','--timeout','160','--grace','60'],timeout=240).returncode)
