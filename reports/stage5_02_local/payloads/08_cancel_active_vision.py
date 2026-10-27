from pathlib import Path
import subprocess
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
command=['python3',str(root/'tools/stage5_02_board_run.py'),'--name','candidate_cancel_active_vision','--replay','--stop-mode','cancel_pending','--signal','SIGTERM','--trigger','vision','--delay','0.2','--seconds','30','--timeout','100','--grace','40']
raise SystemExit(subprocess.run(command,timeout=160).returncode)
