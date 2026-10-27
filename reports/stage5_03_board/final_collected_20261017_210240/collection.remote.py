from pathlib import Path
import sys,tarfile
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
selected=root/'reports/stage5_03_board'
assert selected.is_dir() and not root.is_symlink()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as package:
 for p in sorted(selected.rglob('*')):
  if p.is_file() and not p.is_symlink() and p.relative_to(selected).parts[0] in {'final_state','final_acceptance'}:
   assert p.resolve().is_relative_to(selected) and p.stat().st_size<20*1024**2
   package.add(p,arcname=str(p.relative_to(root)),recursive=False)
