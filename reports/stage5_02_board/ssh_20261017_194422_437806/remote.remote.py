from pathlib import Path
import subprocess,json
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
for mode in ['drain','cancel_pending']:
 command=['python3',str(root/'tools/stage5_02_board_run.py'),'--name','candidate_stop_'+mode,'--replay','--stop-mode',mode,'--signal','SIGTERM','--trigger','tts','--delay','0.1','--tts-queue-ms','60000','--request-lifetime-ms','120000','--seconds','30','--timeout','180','--grace','70']
 print('COMMAND',json.dumps(command),flush=True)
 result=subprocess.run(command,timeout=270)
 print('HARNESS_EXIT',mode,result.returncode,flush=True)
 if result.returncode:raise SystemExit(result.returncode)
command=['python3',str(root/'tools/stage5_02_board_run.py'),'--name','candidate_idle_sigint','--signal','SIGINT','--trigger','ready','--delay','2','--seconds','30','--timeout','100','--grace','45']
print('COMMAND',json.dumps(command),flush=True)
raise SystemExit(subprocess.run(command,timeout=160).returncode)
