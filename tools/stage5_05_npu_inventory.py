"""Read-only exact DRM desktop-owner baseline; unknown model processes refuse."""
from pathlib import Path
import argparse,json,os,re,sys
ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_05_voice_run import query,owner_identity
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert a.output.resolve().parent==(ROOT/'reports/stage5_05_board').resolve() and not a.output.exists()
 nodes=[]
 for path in Path('/sys/class/drm').iterdir():
  if re.fullmatch(r'card\d+',path.name) and (path/'device/driver').exists() and 'rknpu' in str((path/'device/driver').resolve()).lower():nodes.append('/dev/dri/'+path.name)
 assert nodes
 result={'primary_nodes':{},'scope':'read-only snapshot of exact existing seat/display holders; not a measurement of NPU utilization; unknown model holders refuse'}
 roles={'systemd':(0,{'init','systemd'}),'systemd-logind':(0,{'systemd-logind'}),'Xorg':(os.getuid(),{'Xorg'})}
 for node in nodes:
  q=query(['sudo','-n','--','/usr/bin/fuser','-v',node]);assert q['exit_code'] in (0,1)
  identities=[owner_identity(int(x)) for x in q['stdout'].split() if x.isdigit()]
  for x in identities:
   assert x['comm'] in roles,'unknown holder, do not accept as desktop: '+str(x)
   uid,commands=roles[x['comm']];assert x['uid']==uid and Path(x['cmdline'].split()[0]).name in commands,x
  result['primary_nodes'][node]={'query':q,'identities':identities}
 with a.output.open('x') as f:json.dump(result,f,indent=2)
 print('DRM_BASELINE_SAVED',a.output,json.dumps(result))
if __name__=='__main__':main()
