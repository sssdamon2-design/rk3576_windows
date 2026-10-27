from pathlib import Path
import subprocess,json
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert root.is_dir() and not root.is_symlink()
for variant in ['baseline','candidate']:
 command=['python3',str(root/'tools/stage5_02_board_run.py'),'--name',variant+'_replay_overload','--variant',variant,'--replay','--seconds','30','--timeout','200','--grace','60']
 print('COMMAND',json.dumps(command),flush=True)
 result=subprocess.run(command,timeout=280)
 print('HARNESS_EXIT',variant,result.returncode,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
