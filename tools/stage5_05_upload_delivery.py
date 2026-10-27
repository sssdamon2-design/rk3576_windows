"""Upload only a new final review archive; verify without extracting or promoting."""
from pathlib import Path
import json,hashlib
import stage5_phase2_deploy as t
ROOT=Path(__file__).resolve().parents[1]
def main():
 local=ROOT/'reports/stage5_05_local';info=json.loads((local/'final_archive.json').read_text(encoding='utf-8'));archive=ROOT/info['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==info['sha256']
 log=local/'delivery_transport';log.mkdir();remote=t.REMOTE+'/reports/stage5_05_board/final_acceptance';name=archive.name
 guard=f'''from pathlib import Path
import os,shutil,json
r=Path({t.REMOTE!r});p=Path({remote!r})
assert os.getuid()==1000 and not r.is_symlink() and p.resolve().is_relative_to(r)
assert not p.exists(),'refuse existing final delivery directory'
assert shutil.disk_usage(r).free>{info['bytes']}+500*1024**2
p.mkdir(mode=0o700)
print('CREATED_FINAL_REVIEW_ONLY',p)
'''
 rc=t.run_step(log,'01_create',t.remote_command(),guard.encode(),30);assert rc==0,'guard failed; no upload'
 rc=t.run_step(log,'02_scp',[t.SCP,'-S',t.SSH,*t.OPTIONS,str(archive.relative_to(ROOT)),'cat@192.168.10.27:'+remote+'/'+name],timeout=180);assert rc==0,'upload failed; preserve partial artifact, do not overwrite'
 verify=f'''from pathlib import Path,PurePosixPath
import hashlib,json,tarfile,shutil,sys
r=Path({t.REMOTE!r});out=Path({remote!r});archive=out/{name!r}
assert archive.is_file() and not archive.is_symlink()
digest=hashlib.sha256(archive.read_bytes()).hexdigest();assert digest=={info['sha256']!r}
manifest_name='reports/stage5_05_local/final_archive_manifest.json'
with tarfile.open(archive,'r:gz') as package:
 members=package.getmembers();names=[m.name for m in members];assert len(names)==len(set(names))=={info['files']}
 assert sum(m.size for m in members)<768*1024**2
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and 'models' not in p.parts and '.git' not in p.parts
 manifest=json.loads(package.extractfile(manifest_name).read());assert {{x['file'] for x in manifest}}==set(names)-{{manifest_name}}
 for row in manifest:
  data=package.extractfile(row['file']).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['file']
sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
same=fingerprint()==json.loads((r/'reports/stage5_05_board/original_before.json').read_text());assert same
free=shutil.disk_usage(r).free;assert free>500*1024**2
result={{'archive':str(archive),'sha256':digest,'bytes':archive.stat().st_size,'files':len(names),'all_member_SHA256_match':True,'safe_paths':True,'extracted':False,'stable_promoted':False,'original_321_unchanged':same,'disk_free_bytes':free,'user_review_pending':True}}
with (out/'result.json').open('x') as f:json.dump(result,f,indent=2)
print('FINAL_DELIVERY_RECEIPT',json.dumps(result))
'''
 rc=t.run_step(log,'03_verify',t.remote_command(),verify.encode(),180);assert rc==0,'archive validation failed; preserve logs'
 text=(log/'03_verify.stdout.log').read_text(encoding='utf-8');receipt=json.loads(next(x.split('FINAL_DELIVERY_RECEIPT ',1)[1] for x in text.splitlines() if x.startswith('FINAL_DELIVERY_RECEIPT ')))
 (local/'final_delivery_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('FINAL_DELIVERY_VERIFIED',json.dumps(receipt))
if __name__=='__main__':main()
