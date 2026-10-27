from pathlib import Path
import json,subprocess,sys
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(r/'tools'))
from stage5_05_voice_run import owner_identity,devices,discover_audio
q=subprocess.run(['sudo','-n','--','/usr/bin/fuser','-v','/dev/dri/card1'],capture_output=True,text=True,timeout=15);assert q.returncode==0
identities=[owner_identity(int(x)) for x in q.stdout.split() if x.isdigit()]
assert [(x['pid'],x['uid'],x['comm']) for x in identities]==[(1,0,'systemd'),(932,0,'systemd-logind'),(1619,1000,'Xorg')],identities
assert [Path(x['cmdline'].split()[0]).name for x in identities]==['init','systemd-logind','Xorg']
b=r/'reports/stage5_05_board';baseline={'primary_nodes':{'/dev/dri/card1':{'command':q.args,'stdout':q.stdout,'stderr':q.stderr,'returncode':q.returncode,'identities':identities}},'scope':'exact existing seat/display holders; Xorg real uid1000 but fuser displays root effective owner; no inference program started; unknown owners reject'}
with (b/'npu_primary_baseline.json').open('x') as f:json.dump(baseline,f,indent=2)
state=devices(discover_audio());print('EXACT_BASELINE',json.dumps(baseline));print('PRECHECK',json.dumps(state));assert state['clear']
with (b/'final_burst_audio/result.json').open('x') as f:json.dump({'returncode':None,'runner_returncode':1,'program_started':False,'stage':'preflight','input_mode':'NOT_EXECUTED protection refused preexisting seat DRM owners'},f,indent=2)
with (b/'final_matrix/result.json').open('x') as f:json.dump({'complete':False,'stopped_at':'final_burst_audio preflight','failure_reason':'primary DRM baseline classification needed','completed_cases':json.loads((b/'final_matrix/progress.json').read_text())},f,indent=2)
