from pathlib import Path
import os,shutil
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');target=r/'releases/stage5-rc1';a=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_rc1_board/source_bundle.tgz')
assert os.getuid()==1000 and r.resolve()==r
assert not target.exists() and not target.is_symlink() and not a.exists()
assert shutil.disk_usage(r).free>700*1024**2
assert not (r/'releases').is_symlink()
print('RC_EXCLUSIVE_TARGET_CONFIRMED')
