from pathlib import Path
import sys,json,os,hashlib,subprocess
R=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');rc=R/'releases/stage5-rc1'
pre=R/'reports/stage5_rc1_board'/'rc1_release_smoke_20261018_135845_retry1'
settings=json.loads((pre/'preflight.json').read_text());assert settings['passed']
if settings['owner_baseline']:os.environ['STAGE5_NPU_OWNER_BASELINE']=settings['owner_baseline']
# Execute only the existing, audited harness with explicit RC paths in memory.
source=(R/'tools/stage5_05_gui_run.py').read_text()
replacements=[("re.fullmatch(r'stage5_05_\\w+',a.build)","a.build=='stage5-rc1'",1),("ROOT/'build'/a.build","ROOT/'releases/stage5-rc1/build'",2),("'2' if a.mode in {'paired_restart','microphone'} else '0'","'0'",1),("'--auto-start',","",1),("source \"$1/tools/stage5_board_paths.sh\"","source \"$1/releases/stage5-rc1/tools/stage5_board_paths.sh\"",1)]
for old,new,count in replacements:
 assert source.count(old)==count,(old,source.count(old));source=source.replace(old,new)
# Retain frozen default queue/deadline parameters; no altered model prompt or TTS strategy.
source='\n'.join(line for line in source.splitlines() if not (line.strip().startswith("env['STAGE5_TTS_QUEUE_MS']=") or line.strip().startswith("env['STAGE5_REQUEST_LIFETIME_MS']=")))+'\n'
# Manual start lets the user confirm the VNC window before the finite microphone interval.
old_loop='   now=time.monotonic()'
assert source.count(old_loop)==1
source=source.replace(old_loop,old_loop+'\n   if child.poll() is None and sent is None and any("[GUI finished]" in line for line in lines):\n    checked(child.pid,command[0],token,signal.SIGTERM);sent=now\n')
with (pre/'harness_executed.py').open('x') as f:f.write(source)
with (pre/'test_scope.json').open('x') as f:json.dump({'RC':'stage5-rc1','seconds':180,'timeout_seconds':360,'mode':'manual GUI start, then natural microphone; no replay','auto_stop_after_answers':False,'production_core_changed':False,'harness_adaptation':'existing 5.5 harness, paths/CLI test controls in memory only; frozen defaults preserved','frozen_version':json.loads((rc/'VERSION.json').read_text())},f,indent=2)
sys.argv=['stage5_05_gui_run.py','--name','rc1_release_smoke_20261018_135845_retry1','--build','stage5-rc1','--mode','microphone','--seconds','180','--timeout','360','--threads','4']
namespace={'__name__':'rc_smoke_harness','__file__':str(R/'tools/stage5_05_gui_run.py')};exec(compile(source,'<RC smoke harness>','exec'),namespace)
code=namespace['main']()
verify=subprocess.run(['python3','-I','-B',str(rc/'tools/verify.py')],capture_output=True,timeout=90)
with (pre/'RC_verify_after.json').open('x') as f:json.dump({'returncode':verify.returncode,'stdout':verify.stdout.decode(),'stderr':verify.stderr.decode()},f,indent=2)
assert verify.returncode==0
result=json.loads((R/'reports/stage5_05_board'/'rc1_release_smoke_20261018_135845_retry1'/'result.json').read_text())
print('RC_SMOKE_FINISHED',json.dumps({'harness_exit_code':code,'result':result}),flush=True)
raise SystemExit(code)
