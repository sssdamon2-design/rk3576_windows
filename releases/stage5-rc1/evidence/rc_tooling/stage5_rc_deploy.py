"""Upload a new source-only RC, safely unpack, rebuild and collect actual logs."""
from pathlib import Path
import hashlib,json,base64
import stage5_phase2_deploy as t
ROOT=Path(__file__).resolve().parents[1]
def main():
 local=ROOT/'reports/stage5_rc1_local';logs=local/'source_deploy';logs.mkdir()
 archive=local/'stage5-rc1-source.tgz';digest=hashlib.sha256(archive.read_bytes()).hexdigest()
 remote=t.REMOTE+'/reports/stage5_rc1_board/source_bundle.tgz'
 guard=f'''from pathlib import Path
import os,shutil
r=Path({t.REMOTE!r});target=r/'releases/stage5-rc1';a=Path({remote!r})
assert os.getuid()==1000 and r.resolve()==r
assert not target.exists() and not target.is_symlink() and not a.exists()
assert shutil.disk_usage(r).free>700*1024**2
assert not (r/'releases').is_symlink()
print('RC_EXCLUSIVE_TARGET_CONFIRMED')
'''
 assert t.run_step(logs,'01_guard',t.remote_command(),guard.encode(),30)==0
 assert t.run_step(logs,'02_scp',[t.SCP,'-S',t.SSH,*t.OPTIONS,str(archive.relative_to(ROOT)),'cat@192.168.10.27:'+remote],timeout=90)==0
 payload=f'''from pathlib import Path,PurePosixPath
import os,hashlib,tarfile,json,subprocess,sys,base64
r=Path({t.REMOTE!r});a=Path({remote!r});dest=r/'releases/stage5-rc1'
assert hashlib.sha256(a.read_bytes()).hexdigest()=={digest!r}
assert not dest.exists() and not dest.is_symlink() and not (r/'releases').is_symlink()
with tarfile.open(a,'r:gz') as t:
 members=t.getmembers();assert len(members)==110 and len({{m.name for m in members}})==110 and sum(m.size for m in members)<4*1024**2
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\\\' not in m.name and ':' not in m.name
 (r/'releases').mkdir(exist_ok=True);dest.mkdir()
 for m in members:
  p=dest/m.name;assert p.resolve().is_relative_to(dest);p.parent.mkdir(parents=True,exist_ok=True)
  with p.open('xb') as f:f.write(t.extractfile(m).read())
manifest=json.loads((dest/'SOURCE_MANIFEST.json').read_text());assert len(manifest)==104
assert all(hashlib.sha256((dest/'source'/x['file']).read_bytes()).hexdigest()==x['sha256'] for x in manifest)
result=subprocess.run(['python3','-I','-B',str(dest/'tools/build.py')],timeout=900)
sys.path.insert(0,str(r/'tools'));from stage5_board_readonly_inventory import fingerprint
original=fingerprint()==json.loads((r/'reports/stage5_05_board/original_before.json').read_text());assert original
accepted=json.loads((r/'reports/stage5_05_board/accepted_binaries_before.json').read_text());assert all(hashlib.sha256((r/n).read_bytes()).hexdigest()==h for n,h in accepted.items())
report=r/'reports/stage5_rc1_board/build'
files={{p.name:base64.b64encode(p.read_bytes()).decode() for p in report.iterdir() if p.is_file()}}
print('RC_BUILD_EVIDENCE',json.dumps({{'files':files,'original_321_unchanged':original,'four_accepted_binaries_unchanged':True,'returncode':result.returncode}}))
raise SystemExit(result.returncode)
'''
 rc=t.run_step(logs,'03_unpack_build',t.remote_command(),payload.encode(),960)
 raw=(logs/'03_unpack_build.stdout.log').read_text(encoding='utf-8');line=next(s for s in raw.splitlines() if s.startswith('RC_BUILD_EVIDENCE '));result=json.loads(line.split(' ',1)[1]);out=local/'board_build';out.mkdir()
 for n,b in result.pop('files').items():assert Path(n).name==n;(out/n).write_bytes(base64.b64decode(b))
 (local/'board_build_protection.json').write_text(json.dumps(result,indent=2)+'\n');assert rc==result['returncode']==0
 print('RC_BUILD_COLLECTED',json.dumps(json.loads((out/'result.json').read_text())))
if __name__=='__main__':main()
