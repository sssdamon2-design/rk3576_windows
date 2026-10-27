"""Package exact final sources and canonical five-stage evidence; no model/build trees."""
from pathlib import Path
import argparse,hashlib,json,tarfile,sys
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);a=p.parse_args();local=ROOT/'reports/stage5_05_local'
 v=json.loads((local/'validation_summary.json').read_text(encoding='utf-8'));assert v['all_checks_passed'] and v['document_gate_required']
 selected=set()
 def add_tree(folder,exclude=()):
  for p in folder.rglob('*'):
   rel=p.relative_to(folder)
   if p.is_file() and not p.is_symlink() and not any(x in rel.parts for x in exclude):selected.add(p.resolve())
 for name in ['include','src','tests','config','tools','docs','backups']:
  add_tree(ROOT/name,('__pycache__',))
 for p in ROOT.glob('README_STAGE5*'):selected.add(p.resolve())
 for name in ['CMakeLists.txt','STAGE5_CODEX_TASK.md']:selected.add((ROOT/name).resolve())
 for stage in range(1,6):
  folder=ROOT/f'reports/stage5_0{stage}_local'
  for p in folder.rglob('*'):
   if not p.is_file() or p.is_symlink():continue
   rel=p.relative_to(folder)
   if any(x.startswith(('snapshot_','render_','delivery_','instrumentation_')) for x in rel.parts):continue
   if any(x in {'payloads','__pycache__','baseline_5_3_source'} for x in rel.parts):continue
   if p.suffix in {'.tgz','.docx','.pdf'}:continue
   if p.name in {'final_delivery_receipt.json','final_archive_manifest.json','final_archive.json'}:continue
   selected.add(p.resolve())
 # Preserve renderer failure/native-export logs, but not internal QA PDFs/PNGs.
 for folder in local.glob('render_*'):
  for p in folder.iterdir():
   if p.is_file() and p.suffix in {'.json','.log'}:selected.add(p.resolve())
 # Stage1 keeps actual terminal captures directly; do not reupload its declined tgz.
 add_tree(ROOT/'reports/stage5_01_board',('stage5_01_acceptance_local.tgz',))
 canonical={2:ROOT/'reports/stage5_02_board/collected_20261017_195843',3:ROOT/'reports/stage5_03_board/collected_20261017_205548',4:ROOT/'reports/stage5_04_board/collected_20261017_231748',5:a.collection.resolve()}
 for stage,folder in canonical.items():
  assert folder.is_dir(),folder
  add_tree(folder/'files',('final_acceptance',))
  if (folder/'manifest.json').exists():selected.add((folder/'manifest.json').resolve())
 # Preserve current Stage5.5 host transport commands and failures without old duplicates.
 for folder in (ROOT/'reports/stage5_05_board').glob('ssh_*'):add_tree(folder)
 for p in selected:
  assert p.is_relative_to(ROOT) and not p.is_symlink() and p.stat().st_size<128*1024**2,p
  assert 'models' not in p.relative_to(ROOT).parts,p
 manifest=[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(selected)]
 total=sum(x['bytes'] for x in manifest);assert total<768*1024**2,total
 (local/'final_archive_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');selected.add((local/'final_archive_manifest.json').resolve())
 out=local/'RK3576_STAGE5_FINAL_REVIEW.tgz';assert not out.exists(),'never overwrite a final delivery archive'
 with tarfile.open(out,'w:gz',compresslevel=6) as package:
  for p in sorted(selected):package.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
 result={'archive':out.relative_to(ROOT).as_posix(),'bytes':out.stat().st_size,'uncompressed_bytes':total,'files':len(selected),'sha256':sha(out),'canonical_collections':{str(k):str(x.relative_to(ROOT)) for k,x in canonical.items()},'models_included':False,'stable_replaced':False,'user_review_pending':True}
 (local/'final_archive.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('FINAL_ARCHIVE',json.dumps(result))
if __name__=='__main__':main()
