#!/usr/bin/env python3
"""Read only the isolated Stage 5.5 reports, preserving raw logs locally."""
from datetime import datetime
import hashlib,json,tarfile,argparse
from pathlib import Path,PurePosixPath
import stage5_phase2_deploy as transport

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--complete-only',action='store_true');args=parser.parse_args()
 report=transport.ROOT/'reports/stage5_05_board'/('collected_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
 report.mkdir()
 payload=('ONLY_COMPLETE='+repr(args.complete_only)+'\n').encode()+b'''from pathlib import Path
import sys,tarfile
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
selected=root/'reports/stage5_05_board'
assert selected.is_dir() and not root.is_symlink()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as package:
 for p in sorted(selected.rglob('*')):
  if p.is_file() and not p.is_symlink():
   parts=p.relative_to(selected).parts
   if ONLY_COMPLETE and len(parts)>1 and parts[0] not in {'baseline_5_3_source','raw_baseline_build'} and not (selected/parts[0]/'result.json').exists():continue
   assert p.resolve().is_relative_to(selected) and p.stat().st_size<128*1024**2
   package.add(p,arcname=str(p.relative_to(root)),recursive=False)
'''
 code=transport.run_step(report,'collection',transport.remote_command(),payload,120,binary=True)
 if code:return code
 destination=report/'files';destination.mkdir();manifest=[];total=0
 with tarfile.open(report/'collection.tgz','r:gz') as package:
  for item in package:
   relative=PurePosixPath(item.name)
   assert item.isfile() and not relative.is_absolute() and '..' not in relative.parts
   assert relative.parts[:2]==('reports','stage5_05_board') and item.size<128*1024**2
   total+=item.size;assert total<512*1024**2
   target=destination/Path(*relative.parts);assert target.resolve().is_relative_to(destination.resolve())
   target.parent.mkdir(parents=True,exist_ok=True);content=package.extractfile(item).read()
   with target.open('xb') as output:output.write(content)
   manifest.append(dict(file=item.name,bytes=len(content),sha256=hashlib.sha256(content).hexdigest()))
 (report/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print('COLLECTED',report,'files',len(manifest),'bytes',total)
 return 0
if __name__=='__main__':raise SystemExit(main())
