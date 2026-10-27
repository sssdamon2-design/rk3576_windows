import sys,subprocess,json
sys.path.insert(0,'/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools')
from stage5_05_voice_run import owner_identity
q=subprocess.run(['sudo','-n','--','/usr/bin/fuser','-v','/dev/dri/card1'],capture_output=True,text=True,timeout=15)
print('QUERY',q.returncode,q.stdout,q.stderr)
print('IDENTITIES',json.dumps([owner_identity(int(p)) for p in q.stdout.split() if p.isdigit()]))
