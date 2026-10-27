"""Build a bounded evidence archive and an exclusive isolated-directory receiver."""
from pathlib import Path
from urllib.parse import unquote
import base64, hashlib, io, json, re, tarfile

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT / 'reports/stage5_04_local'
COLLECTION = ROOT / 'reports/stage5_04_board/collected_20261017_231748'
BASE = COLLECTION / 'files/reports/stage5_04_board'
sha = lambda data: hashlib.sha256(data).hexdigest()
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
assert load(LOCAL / 'validation_summary.json')['all_checks_passed']

files = set()
def add(path):
    path = path.resolve()
    assert path.is_relative_to(ROOT.resolve()) and path.is_file() and not path.is_symlink()
    files.add(path)

documents = sorted((ROOT / 'docs').glob('stage5_04*.md'))
qa, broken = [], []
for path in documents:
    add(path)
    text = path.read_text(encoding='utf-8')
    fences = len(re.findall(r'^```', text, re.M))
    assert fences % 2 == 0, path
    prose = re.sub(r'^```[^\n]*\n.*?^```[^\n]*$', '', text, flags=re.M | re.S)
    for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', prose):
        if target.startswith(('https:', 'http:', '#', 'mailto:')):
            continue
        target = unquote(target.strip('<>').split('#')[0])
        resolved = (path.parent / target).resolve()
        if not resolved.is_file():
            broken.append({'document': str(path), 'target': target})
        else:
            add(resolved)
    qa.append({'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
               'code_fences_even': True})
assert not broken, broken
qa_result = {'documents': qa, 'broken_local_links': broken,
             'plots_visually_inspected': ['tts_latency.png', 'tts_rtf_cdf.png',
                                          'tts_resources.png', 'pipeline_breakdown.png'],
             'manual_voice_pending': False, 'human_both_audible_confirmed': True}
(LOCAL / 'document_qa.json').write_text(json.dumps(qa_result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
state = load(LOCAL / 'continuation_state.json')
state.update(status='recorded verification complete; user Stage5.4 acceptance pending',
             user_prompt_pending=None, selected_live_case='candidate_voice_4t_final_retry1',
             next_steps=['Verify final delivery receipt', 'Pause for user acceptance; do not start5.5'])
(LOCAL / 'continuation_state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

for row in load(LOCAL / 'candidate_v3_deployment_manifest.json'):
    add(ROOT / row['file'])
for row in load(LOCAL / 'change_manifest.json'):
    add(ROOT / row['file'])
for path in (ROOT / 'backups/stage5_04_before').rglob('*'):
    if path.is_file(): add(path)
for path in (ROOT / 'tools').glob('stage5_04*.py'): add(path)
add(ROOT / 'STAGE5_CODEX_TASK.md')
add(Path(__file__))
for path in LOCAL.iterdir():
    if path.is_file() and path.suffix in {'.json', '.patch', '.h'}: add(path)
for folder in ['analysis', 'plots']:
    for path in (LOCAL / folder).iterdir():
        if path.is_file(): add(path)
for path in BASE.rglob('*'):
    if path.is_file() and (path.suffix in {'.log', '.csv', '.tsv', '.xml'} or
                          path.name in {'result.json', 'user_feedback.json', 'command.json',
                                        'test_parameters.json', 'environment.json',
                                        'events.jsonl', 'profile.jsonl', 'source_manifest.json'}):
        assert path.stat().st_size < 2*1024**2
        add(path)

records = []
stream = io.BytesIO()
with tarfile.open(fileobj=stream, mode='w:gz') as archive:
    for path in sorted(files):
        content = path.read_bytes(); name = path.relative_to(ROOT).as_posix()
        record = {'file': name, 'bytes': len(content), 'sha256': sha(content)}
        records.append(record)
        info = tarfile.TarInfo(name); info.size = len(content); info.mode = 0o644
        archive.addfile(info, io.BytesIO(content))
content = stream.getvalue()
assert len(content) < 16*1024**2 and sum(x['bytes'] for x in records) < 64*1024**2
archive_path = LOCAL / 'stage5_04_acceptance.tgz'
with archive_path.open('xb') as output: output.write(content)
manifest = {'archive_sha256': sha(content), 'archive_bytes': len(content),
            'file_count': len(records), 'uncompressed_bytes': sum(x['bytes'] for x in records),
            'files': records,
            'raw_evidence_location': str(BASE.relative_to(ROOT)),
            'raw_evidence_board': 'reports/stage5_04_board/<case> (unchanged)',
            'note': 'Large raw frames, ORT profiles and resource samples already exist locally and on board; not duplicated here. Manifest excludes receiver-generated receipts.'}
(LOCAL / 'final_delivery_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
receiver = '''from pathlib import Path,PurePosixPath
import base64,hashlib,io,json,os,shutil,sys,tarfile
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert not r.is_symlink() and r.resolve()==r and os.getuid()!=0
p=r/'reports/stage5_04_board/final_acceptance'
assert not p.exists() and not p.is_symlink(),'Existing destination: stop without overwrite'
assert p.parent.resolve()==r/'reports/stage5_04_board'
assert shutil.disk_usage(r).free>=500*1024**2
sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
before=json.loads((p.parent/'original_before.json').read_text())
accepted=json.loads((p.parent/'accepted_binaries_before.json').read_text())
digest=lambda b:hashlib.sha256(b).hexdigest()
assert fingerprint()==before
assert all(digest((r/n).read_bytes())==v for n,v in accepted.items())
manifest=MANIFEST
data=base64.b64decode(DATA,validate=True)
assert digest(data)==manifest['archive_sha256'] and len(data)==manifest['archive_bytes']
expected={row['file']:row for row in manifest['files']};members={}
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
 for item in archive:
  n=PurePosixPath(item.name)
  assert item.isfile() and not n.is_absolute() and '..' not in n.parts
  assert item.name in expected and item.name not in members
  assert item.size==expected[item.name]['bytes'] and item.size<2*1024**2
  b=archive.extractfile(item).read()
  assert digest(b)==expected[item.name]['sha256'];members[item.name]=b
assert members.keys()==expected.keys()
assert shutil.disk_usage(r).free-len(data)-manifest['uncompressed_bytes']>=500*1024**2
p.mkdir()
with (p/'stage5_04_acceptance.tgz').open('xb') as f:f.write(data)
for n,b in members.items():
 q=p/n;assert q.resolve().is_relative_to(p)
 q.parent.mkdir(parents=True,exist_ok=True)
 with q.open('xb') as f:f.write(b)
assert all(digest((p/n).read_bytes())==row['sha256'] for n,row in expected.items())
assert fingerprint()==before
assert all(digest((r/n).read_bytes())==v for n,v in accepted.items())
result={'returncode':0,'destination':str(p),'archive_sha256':manifest['archive_sha256'],
 'archive_bytes':len(data),'files_verified':len(members),'original_321_unchanged':True,
 'accepted_binaries_unchanged':True,'disk_free_bytes':shutil.disk_usage(r).free,
 'scope':'new reports/final_acceptance only; no build/test/model/system modification',
 'receipt_scope':'archive manifest covers input files; result and receipt are receiver-generated'}
for path,value in [(p/'manifest.json',manifest),(p/'result.json',result),
 (p/'reports/stage5_04_local/final_delivery_receipt.json',result)]:
 with path.open('x',encoding='utf-8') as f:json.dump(value,f,indent=2)
print('FINAL_DELIVERY',json.dumps(result),flush=True)
'''.replace('MANIFEST', repr(manifest), 1).replace('DATA', repr(base64.b64encode(content).decode()), 1)
(LOCAL / 'payloads/30_delivery.py').write_text(receiver, encoding='utf-8')
print('DELIVERY_PREPARED', manifest['file_count'], 'files;', len(content), 'compressed bytes; QA clean')
