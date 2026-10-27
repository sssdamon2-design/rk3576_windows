from pathlib import Path,PurePosixPath
import os,hashlib,tarfile,json,subprocess,sys,base64
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');a=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_rc1_board/source_bundle.tgz');dest=r/'releases/stage5-rc1'
assert hashlib.sha256(a.read_bytes()).hexdigest()=='dc884c9502c53fbc4f15f691165ae2e09af57cfbbdad8d84c7b297fb9a4d2137'
assert not dest.exists() and not dest.is_symlink() and not (r/'releases').is_symlink()
with tarfile.open(a,'r:gz') as t:
 members=t.getmembers();assert len(members)==110 and len({m.name for m in members})==110 and sum(m.size for m in members)<4*1024**2
 for m in members:
  p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\' not in m.name and ':' not in m.name
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
files={p.name:base64.b64encode(p.read_bytes()).decode() for p in report.iterdir() if p.is_file()}
print('RC_BUILD_EVIDENCE',json.dumps({'files':files,'original_321_unchanged':original,'four_accepted_binaries_unchanged':True,'returncode':result.returncode}))
raise SystemExit(result.returncode)
