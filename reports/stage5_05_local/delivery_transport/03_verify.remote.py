from pathlib import Path,PurePosixPath
import hashlib,json,tarfile,shutil,sys
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');out=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_acceptance');archive=out/'RK3576_STAGE5_FINAL_REVIEW.tgz'
assert archive.is_file() and not archive.is_symlink()
digest=hashlib.sha256(archive.read_bytes()).hexdigest();assert digest=='704eec9a30c23a5253854d21af53e834f47844cbd477355c7283c1ab3db50734'
manifest_name='reports/stage5_05_local/final_archive_manifest.json'
with tarfile.open(archive,'r:gz') as package:
 members=package.getmembers();names=[m.name for m in members];assert len(names)==len(set(names))==4835
 assert sum(m.size for m in members)<768*1024**2
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and 'models' not in p.parts and '.git' not in p.parts
 manifest=json.loads(package.extractfile(manifest_name).read());assert {x['file'] for x in manifest}==set(names)-{manifest_name}
 for row in manifest:
  data=package.extractfile(row['file']).read();assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],row['file']
sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
same=fingerprint()==json.loads((r/'reports/stage5_05_board/original_before.json').read_text());assert same
free=shutil.disk_usage(r).free;assert free>500*1024**2
result={'archive':str(archive),'sha256':digest,'bytes':archive.stat().st_size,'files':len(names),'all_member_SHA256_match':True,'safe_paths':True,'extracted':False,'stable_promoted':False,'original_321_unchanged':same,'disk_free_bytes':free,'user_review_pending':True}
with (out/'result.json').open('x') as f:json.dump(result,f,indent=2)
print('FINAL_DELIVERY_RECEIPT',json.dumps(result))
