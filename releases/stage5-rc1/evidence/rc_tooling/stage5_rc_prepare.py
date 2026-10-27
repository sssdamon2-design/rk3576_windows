"""Freeze accepted Stage5 source and collect RC materials without changing history."""
from pathlib import Path
import hashlib,json,shutil,subprocess,tarfile
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'releases/stage5-rc1'
REPORT=ROOT/'reports/stage5_rc1_local'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 REPORT.mkdir(exist_ok=True);assert not OUT.exists(),'never replace an RC snapshot';OUT.mkdir(parents=True)
 git={}
 for name,args in {'root':['rev-parse','--show-toplevel'],'branch':['symbolic-ref','--short','HEAD'],'HEAD':['rev-parse','HEAD'],'status':['status','--short','--untracked-files=all'],'tag':['tag','--list','stage5-rc1']}.items():
  r=subprocess.run(['git',*args],cwd=ROOT,capture_output=True,timeout=15)
  git[name]={'argv':['git',*args],'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}
 assert git['root']['exit_code']!=0,'Git repo appeared; review actual branch before freezing'
 save(REPORT/'git_state.json',git)
 rows=json.loads((ROOT/'reports/stage5_05_local/final_v2_deployment_manifest.json').read_text())
 manifest=[]
 for row in rows:
  p=ROOT/row['file'];assert p.is_file() and not p.is_symlink() and sha(p)==row['sha256'],row['file']
  target=OUT/'source'/row['file'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
  manifest.append({'file':row['file'],'bytes':p.stat().st_size,'sha256':sha(p)})
 assert len(manifest)==104
 encoded=json.dumps(manifest,sort_keys=True,separators=(',',':')).encode()
 version={'version':'stage5-rc1','created_at_UTC':datetime.now(timezone.utc).isoformat(),'git_commit':None,'git_tag_created':False,'git_reason':'workspace is not a Git repository','source_snapshot_id':'sha256:'+hashlib.sha256(encoded).hexdigest(),'source_manifest_format':'UTF-8 json.dumps(rows,sort_keys=True,separators=(comma,colon)); rows ordered as SOURCE_MANIFEST.json','accepted_board_source':'stage5_05_source_final_v2','source_files':104,'core_modified':False,'models_and_SDK_included':False,'entry_switched':False}
 save(OUT/'VERSION.json',version);save(OUT/'SOURCE_MANIFEST.json',manifest)
 shutil.copytree(ROOT/'config',OUT/'config')
 (OUT/'tools').mkdir();shutil.copyfile(ROOT/'tools/stage5_board_paths.sh',OUT/'tools/stage5_board_paths.sh')
 shutil.copytree(ROOT/'docs',OUT/'docs',ignore=shutil.ignore_patterns('*.docx','*.pdf'))
 shutil.copyfile(ROOT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx',OUT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx')
 # Preserve diagram/screenshot paths referenced by the unchanged historical chapters.
 for d in ['reports/stage5_05_local/plots','reports/stage5_05_local/figures']:
  shutil.copytree(ROOT/d,OUT/d)
 (OUT/'evidence').mkdir();old=ROOT/'reports/stage5_05_local';info=json.loads((old/'final_archive.json').read_text(encoding='utf-8'));archive=ROOT/info['archive'];assert sha(archive)==info['sha256']
 with tarfile.open(archive,'r:gz') as t:
  members=t.getmembers();assert len(members)==info['files'] and len({m.name for m in members})==len(members)
  from pathlib import PurePosixPath
  assert all(m.isfile() and not PurePosixPath(m.name).is_absolute() and '..' not in PurePosixPath(m.name).parts for m in members)
  entries=json.loads(t.extractfile('reports/stage5_05_local/final_archive_manifest.json').read())
  for row in entries:
   f=t.extractfile(row['file']);h=hashlib.sha256();size=0
   for b in iter(lambda:f.read(1024*1024),b''):h.update(b);size+=len(b)
   assert size==row['bytes'] and h.hexdigest()==row['sha256'],row['file']
 shutil.copyfile(archive,OUT/'evidence'/archive.name)
 for name in ['final_archive.json','final_archive_manifest.json','final_delivery_receipt.json','manual_source_manifest.json','document_QA.json','INDEX.md','validation_summary.json','patch_roundtrip.json']:
  shutil.copyfile(old/name,OUT/'evidence'/name)
 for stage in range(1,6):
  source=ROOT/f'reports/stage5_0{stage}_local';dest=OUT/'evidence'/f'stage5_0{stage}';dest.mkdir()
  for name in ['changes.patch','validation_summary.json','change_manifest.json']:
   if (source/name).exists():shutil.copyfile(source/name,dest/name)
 save(REPORT/'freeze_result.json',{'version':version,'all_104_match_accepted':True,'historical_archive_all_hashes_checked':True,'historical_archive_files':info['files'],'historical_archive_sha256':info['sha256'],'git_state':git,'new_snapshot':str(OUT.relative_to(ROOT))})
 print(json.dumps(version,ensure_ascii=False))
if __name__=='__main__':main()
