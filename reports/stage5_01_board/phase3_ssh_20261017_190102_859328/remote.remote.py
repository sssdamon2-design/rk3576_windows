import subprocess
from pathlib import Path
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert root.is_dir() and not root.is_symlink()
cmd=['python3','-I',str(root/'tools/stage5_board_phase3_run.py'),'--name','voice_both_natural_01','--seconds','90','--timeout','240','--grace','45']
r=subprocess.run(cmd,timeout=300)
raise SystemExit(r.returncode)
