from pathlib import Path
import os,shutil
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');rc=r/'releases/stage5-rc1';a=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_rc1_board/stage5-rc1.tgz')
assert os.getuid()==1000 and r.resolve()==r and rc.resolve()==rc and rc.is_dir()
assert not a.exists() and not a.is_symlink()
assert not (r/'reports/stage5_rc1_board/final_delivery_receipt.json').exists()
assert shutil.disk_usage(r).free>317880179+524288000
print('FINAL_ADDITIVE_DEPLOY_GUARD_PASSED')
