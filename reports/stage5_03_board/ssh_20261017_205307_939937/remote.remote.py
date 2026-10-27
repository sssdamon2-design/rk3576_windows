from pathlib import Path
import subprocess,os,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
cases=[['--name','sigint_idle_final','--signal','SIGINT','--trigger','ready','--delay','2','--seconds','30','--timeout','100','--grace','50'],['--name','sigterm_vision_cancel_final','--replay','--replay-source','pair','--stop-mode','cancel_pending','--signal','SIGTERM','--trigger','vision','--delay','0.2','--seconds','30','--timeout','130','--grace','70'],['--name','sigterm_tts_drain_final','--replay','--replay-source','pair','--tts-queue-ms','60000','--request-lifetime-ms','120000','--signal','SIGTERM','--trigger','tts','--delay','0.2','--seconds','30','--timeout','170','--grace','80']]
for args in cases:
 code=subprocess.run(['python3',str(r/'tools/stage5_03_voice_run.py'),*args],timeout=270).returncode
 if code:raise SystemExit(code)
 result=json.loads((r/'reports/stage5_03_board'/args[1]/'result.json').read_text())
 assert result['returncode']==0 and not result['forced_kill'] and not result['timeout'] and result['trigger_observed'] and result['devices_released'] and result['shutdown_complete_marker'],result
for name,fixed,n in [('candidate_live_final_12',False,12),('candidate_fixed_final_6',True,6)]:
 cmd=['python3',str(r/'tools/stage5_03_probe_run.py'),'--name',name,'--variant','candidate','--samples',str(n)]
 if fixed:cmd+=['--fixed']
 code=subprocess.run(cmd,env=dict(os.environ,STAGE5_CAPTURE_FIXTURES='0'),timeout=240).returncode
 if code:raise SystemExit(code)
