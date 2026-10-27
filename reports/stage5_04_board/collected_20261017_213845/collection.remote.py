ONLY_COMPLETE=True
from pathlib import Path
import sys,tarfile
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
selected=root/'reports/stage5_04_board'
assert selected.is_dir() and not root.is_symlink()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as package:
 for p in sorted(selected.rglob('*')):
  if p.is_file() and not p.is_symlink():
   parts=p.relative_to(selected).parts
   if ONLY_COMPLETE and len(parts)>1 and parts[0] not in {'baseline_5_3_source','raw_baseline_build'} and not (selected/parts[0]/'result.json').exists():continue
   assert p.resolve().is_relative_to(selected) and p.stat().st_size<128*1024**2
   package.add(p,arcname=str(p.relative_to(root)),recursive=False)
