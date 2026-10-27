from pathlib import Path
import subprocess
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
raise SystemExit(subprocess.run(['python3',str(r/'tools/stage5_03_voice_run.py'),'--name','voice_natural_retry1','--seconds','120','--timeout','240','--grace','70'],timeout=320).returncode)
