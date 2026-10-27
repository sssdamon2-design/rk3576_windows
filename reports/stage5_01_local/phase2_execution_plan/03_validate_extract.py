
import hashlib, json, os, subprocess, tarfile
from pathlib import Path, PurePosixPath
root = Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert root.is_dir() and not root.is_symlink() and str(root.resolve()) == str(root)
archive = root / 'stage5_01_review_preflight_v2.tgz'
assert archive.is_file() and not archive.is_symlink()
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
assert digest == 'a653dd57e1ed5138170dd6d6ff7eb77a1518aa0e97c909402b662cab45c13c6e', 'archive hash mismatch'
subprocess.run(['sha256sum', '-c', 'stage5_01_review_preflight_v2.tgz' + '.sha256'], cwd=root, check=True, timeout=10)
with tarfile.open(archive, 'r:gz') as package:
    members = package.getmembers()
    names = [m.name for m in members]
    assert len(names) == len(set(names)), 'duplicate members'
    assert len(names) == 87, 'unexpected member count'
    assert sum(m.size for m in members) < 5*1024*1024, 'unexpected expansion size'
    for m in members:
        p = PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts
        assert p.parts[0] in {'CMakeLists.txt','README_STAGE5.txt','src','include','tests','tools','docs','SOURCE_SHA256SUMS'}
        assert not os.path.lexists(root / m.name), 'refusing existing extraction destination'
    manifest = package.extractfile('SOURCE_SHA256SUMS').read().decode('utf-8')
    hashes = dict((name, sha) for sha, name in (line.split('  ', 1) for line in manifest.splitlines()))
    assert set(hashes) == set(names) - {'SOURCE_SHA256SUMS'}
    for name, sha in hashes.items():
        assert hashlib.sha256(package.extractfile(name).read()).hexdigest() == sha
subprocess.run(['tar','--keep-old-files','-xzf',archive.name], cwd=root, check=True, timeout=30)
subprocess.run(['sha256sum','-c','SOURCE_SHA256SUMS'], cwd=root, check=True, timeout=15)
report = root / 'reports/stage5_01_board'
report.mkdir(parents=True)
result = {'archive':archive.name,'sha256':digest,'regular_members':len(names),'safe_paths':True,'all_member_hashes_match':True,'extraction_exit_code':0}
(report / 'phase2_archive_validation.json').write_text(json.dumps(result,indent=2)+'\n')
print('ARCHIVE_VALIDATED_AND_EXTRACTED', json.dumps(result), flush=True)
