"""Add only absent RC delivery files; verify existing files, never replace them."""
from pathlib import Path
import hashlib,json,base64
import stage5_phase2_deploy as t
ROOT=Path(__file__).resolve().parents[1]
def main():
 local=ROOT/'reports/stage5_rc1_local';logs=local/'final_deploy';logs.mkdir()
 info=json.loads((local/'archive_result.json').read_text());a=ROOT/info['archive']
 remote=t.REMOTE+'/reports/stage5_rc1_board/stage5-rc1.tgz'
 guard=f'''from pathlib import Path
import os,shutil
r=Path({t.REMOTE!r});rc=r/'releases/stage5-rc1';a=Path({remote!r})
assert os.getuid()==1000 and r.resolve()==r and rc.resolve()==rc and rc.is_dir()
assert not a.exists() and not a.is_symlink()
assert not (r/'reports/stage5_rc1_board/final_delivery_receipt.json').exists()
assert shutil.disk_usage(r).free>{info['bytes']+info['uncompressed_bytes']}+524288000
print('FINAL_ADDITIVE_DEPLOY_GUARD_PASSED')
'''
 assert t.run_step(logs,'01_guard',t.remote_command(),guard.encode(),30)==0
 assert t.run_step(logs,'02_upload',[t.SCP,'-S',t.SSH,*t.OPTIONS,str(a.relative_to(ROOT)),'cat@192.168.10.27:'+remote],timeout=180)==0
 payload=f'''from pathlib import Path,PurePosixPath
import os,hashlib,json,tarfile,subprocess,sys,shutil,base64
from datetime import datetime,timezone
r=Path({t.REMOTE!r});rc=r/'releases/stage5-rc1';archive=Path({remote!r});report=r/'reports/stage5_rc1_board'
assert os.getuid()==1000 and r.resolve()==r and rc.resolve()==rc
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
assert sha(archive)=={info['sha256']!r}
written=skipped=0;disk_before=shutil.disk_usage(r).free
with tarfile.open(archive,'r:gz') as bundle:
 members=bundle.getmembers();assert len(members)=={info['files']} and len({{m.name for m in members}})==len(members)
 assert sum(m.size for m in members)=={info['uncompressed_bytes']}
 manifest=json.loads(bundle.extractfile('stage5-rc1/PACKAGE_MANIFEST.json').read())
 expected={{'stage5-rc1/'+x['file']:x for x in manifest}}
 assert set(m.name for m in members)==set(expected)|{{'stage5-rc1/PACKAGE_MANIFEST.json','stage5-rc1/SHA256SUMS'}}
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and p.parts[0]=='stage5-rc1' and len(p.parts)>1 and '..' not in p.parts and '\\\\' not in m.name and ':' not in m.name
  n='/'.join(p.parts[1:]);assert p.parts[1] not in {{'build','models','sdk','.git'}}
  h=hashlib.sha256(bundle.extractfile(m).read()).hexdigest()
  if m.name in expected:assert h==expected[m.name]['sha256'] and m.size==expected[m.name]['bytes']
  dest=rc/n;assert dest.resolve().is_relative_to(rc) and not dest.is_symlink()
  if dest.exists():assert dest.is_file() and dest.stat().st_size==m.size and sha(dest)==h,n
 for m in members:
  dest=rc/PurePosixPath(m.name).relative_to('stage5-rc1')
  if dest.exists():skipped+=1;continue
  assert shutil.disk_usage(r).free>524288000
  dest.parent.mkdir(parents=True,exist_ok=True)
  assert dest.parent.resolve().is_relative_to(rc)
  with dest.open('xb') as f:
   with bundle.extractfile(m) as source:shutil.copyfileobj(source,f)
  written+=1
steps=[]
for name,args,expected_code in [
 ('verify',['python3','-I','-B',str(rc/'tools/verify.py')],0),
 ('checksums',['sha256sum','-c','SHA256SUMS'],0),
 ('launch_syntax',['bash','-n',str(rc/'tools/launch.sh')],0),
 ('launch_reject_invalid_mode',['bash',str(rc/'tools/launch.sh'),'invalid','4'],2)]:
 result=subprocess.run(args,cwd=rc,capture_output=True,timeout=120)
 for stream,data in [('stdout',result.stdout),('stderr',result.stderr)]:
  with (report/(name+'.'+stream+'.log')).open('xb') as f:f.write(data)
 steps.append({{'name':name,'argv':args,'returncode':result.returncode,'expected_returncode':expected_code}})
 assert result.returncode==expected_code,name
sys.path.insert(0,str(r/'tools'));from stage5_board_readonly_inventory import fingerprint
assert fingerprint()==json.loads((r/'reports/stage5_05_board/original_before.json').read_text())
accepted=json.loads((r/'reports/stage5_05_board/accepted_binaries_before.json').read_text())
assert all(sha(r/n)==h for n,h in accepted.items())
source=json.loads((rc/'SOURCE_MANIFEST.json').read_text())
assert all(sha(r/'stage5_05_source_final_v2'/x['file'])==x['sha256']==sha(rc/'source'/x['file']) for x in source)
build=json.loads((report/'build/result.json').read_text())
assert all(sha(rc/'build'/n)==v['sha256'] for n,v in build['binaries'].items())
result={{'version':'stage5-rc1','at_UTC':datetime.now(timezone.utc).isoformat(),'archive':str(archive),'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'files':len(members),'new_files_written':written,'existing_identical_files_skipped':skipped,'steps':steps,'disk_free_before_bytes':disk_before,'disk_free_after_bytes':shutil.disk_usage(r).free,'original_321_unchanged':True,'four_historical_binaries_unchanged':True,'accepted_final_v2_104_unchanged':True,'RC_binaries_unchanged_after_packaging':True,'RC_directory':str(rc),'hardware_test_this_round':False,'HyperX_missing_at_preflight':True,'entry_switched':False,'system_configuration_changed':False}}
assert result['disk_free_after_bytes']>524288000
with (report/'final_delivery_receipt.json').open('x') as f:json.dump(result,f,indent=2)
files={{p.name:base64.b64encode(p.read_bytes()).decode() for p in report.iterdir() if p.is_file() and (p.suffix=='.log' or p.name=='final_delivery_receipt.json')}}
print('FINAL_DELIVERY',json.dumps({{'receipt':result,'files':files}}))
'''
 assert t.run_step(logs,'03_finalize',t.remote_command(),payload.encode(),360)==0
 raw=(logs/'03_finalize.stdout.log').read_text(encoding='utf-8');result=json.loads(next(s for s in raw.splitlines() if s.startswith('FINAL_DELIVERY ')).split(' ',1)[1])
 out=local/'board_final';out.mkdir()
 for n,b in result['files'].items():assert Path(n).name==n;(out/n).write_bytes(base64.b64decode(b))
 (local/'final_delivery_receipt.json').write_text(json.dumps(result['receipt'],indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result['receipt'],indent=2))
if __name__=='__main__':main()
