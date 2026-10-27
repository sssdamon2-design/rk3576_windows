"""Verify frozen RC data, source identity and manifest; no remote or system writes."""
from pathlib import Path,PurePosixPath
import hashlib,json
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 root=Path(__file__).resolve().parents[1]
 rows=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'));names=[]
 for r in rows:
  n=r['file'];p=PurePosixPath(n);assert not p.is_absolute() and '..' not in p.parts and '\\' not in n and ':' not in n
  target=root/n;assert target.is_file() and not target.is_symlink() and target.resolve().is_relative_to(root)
  assert target.stat().st_size==r['bytes'] and sha(target)==r['sha256'],n;names.append(n)
 assert len(names)==len(set(names))
 hashes={}
 for line in (root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
  h,n=line.split('  ',1);assert n not in hashes;hashes[n]=h
 assert set(hashes)==set(names)|{'PACKAGE_MANIFEST.json'}
 assert all(sha(root/n)==h for n,h in hashes.items())
 source=json.loads((root/'SOURCE_MANIFEST.json').read_text());version=json.loads((root/'VERSION.json').read_text())
 actual={p.relative_to(root/'source').as_posix() for p in (root/'source').rglob('*') if p.is_file()}
 assert actual=={r['file'] for r in source} and len(actual)==104
 assert all(sha(root/'source'/r['file'])==r['sha256'] for r in source)
 digest=hashlib.sha256(json.dumps(source,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 assert version['source_snapshot_id']=='sha256:'+digest
 print(json.dumps({'version':version['version'],'source_snapshot_id':version['source_snapshot_id'],'package_data_files':len(rows),'all_hashes_match':True,'core_files':len(actual),'git_commit':version['git_commit']}))
if __name__=='__main__':main()
