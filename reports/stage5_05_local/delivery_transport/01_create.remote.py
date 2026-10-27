from pathlib import Path
import os,shutil,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');p=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_acceptance')
assert os.getuid()==1000 and not r.is_symlink() and p.resolve().is_relative_to(r)
assert not p.exists(),'refuse existing final delivery directory'
assert shutil.disk_usage(r).free>147337657+500*1024**2
p.mkdir(mode=0o700)
print('CREATED_FINAL_REVIEW_ONLY',p)
