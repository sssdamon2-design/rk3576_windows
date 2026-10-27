"""Freeze an exclusive Stage5.5 source, deploy within review, and build with existing SDKs."""
from pathlib import Path
import argparse,base64,hashlib,json
import stage5_phase2_deploy as transport
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--qt',action='store_true');a=p.parse_args();assert a.label.isidentifier()
 previous={x['file']:x['sha256'] for x in json.loads((ROOT/'reports/stage5_04_local/candidate_v3_deployment_manifest.json').read_text())}
 selected=[Path('CMakeLists.txt')]
 for folder in ['include','src','tests']:
  selected.extend(p.relative_to(ROOT) for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.h','.hpp','.cpp','.cmake','.tsv','.txt'})
 snap=ROOT/'reports/stage5_05_local'/('snapshot_'+a.label);snap.mkdir();rows=[]
 for path in sorted(selected):
  content=(ROOT/path).read_bytes();target=snap/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
  rows.append({'file':path.as_posix(),'before':previous.get(path.as_posix()),'sha256':hashlib.sha256(content).hexdigest(),'data':base64.b64encode(content).decode()})
 local=ROOT/'reports/stage5_05_local'
 (local/(a.label+'_deployment_manifest.json')).write_text(json.dumps([{k:v for k,v in x.items() if k!='data'} for x in rows],indent=2))
 source=transport.fingerprint_code()+'\nimport base64,sys\nROWS='+repr(rows)+'\nLABEL='+repr(a.label)+'\nQT='+repr(a.qt)+'\n'
 source+='''
assert os.getuid()==1000 and not REVIEW.is_symlink()
sys.path.insert(0,str(REVIEW/'tools'))
from stage5_04_voice_run import discover_audio,devices
assert devices(discover_audio())['clear']
original=fingerprint()
accepted=json.loads((REVIEW/'reports/stage5_05_board/accepted_binaries_before.json').read_text())
report=REVIEW/'reports/stage5_05_board'/('build_'+LABEL);report.mkdir()
source=REVIEW/('stage5_05_source_'+LABEL);assert not source.exists()
shutil.copytree(REVIEW/'stage5_04_source_v3',source)
for row in ROWS:
 p=source/row['file'];assert p.resolve().is_relative_to(source) and not p.is_symlink()
 if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before'],row['file']
 data=base64.b64decode(row['data']);assert hashlib.sha256(data).hexdigest()==row['sha256']
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
(report/'source_manifest.json').write_text(json.dumps([{k:v for k,v in x.items() if k!='data'} for x in ROWS],indent=2))
results=[]
'''
 old=(ROOT/'reports/stage5_02_local/payloads/02_install_build.py').read_text(encoding='utf-8')
 source+=old[old.index('def step(label,cmd,limit):'):old.index('ok=True\nfor variant')]
 source+='''
build=REVIEW/'build'/('stage5_05_'+LABEL);assert not build.exists()
config='source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" -DBUILD_QT_GUI="$4"'
ok=step('configure',['bash','-c',config,'stage5_05',str(REVIEW),str(source),str(build),'ON' if QT else 'OFF'],180)
if ok:ok=step('build',['cmake','--build',str(build),'--parallel','3'],600)
if ok:
 config='source "$1/tools/stage5_board_paths.sh"; QT_QPA_PLATFORM=offscreen exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"'
 ok=step('ctest',['bash','-c',config,'stage5_05',str(REVIEW),str(build),str(report/'ctest.xml')],180)
summary={'steps':results,'original_321_unchanged':original==fingerprint(),'accepted_binaries_unchanged':all(hashlib.sha256((REVIEW/p).read_bytes()).hexdigest()==h for p,h in accepted.items()),'disk_free_bytes':shutil.disk_usage(REVIEW).free,'successful':ok}
(report/'result.json').write_text(json.dumps(summary,indent=2));print('BUILD_SUMMARY',json.dumps(summary),flush=True)
raise SystemExit(0 if ok and summary['original_321_unchanged'] and summary['accepted_binaries_unchanged'] else 1)
'''
 payload=local/'payloads'/('02_build_'+a.label+'.py');payload.write_text(source,encoding='utf-8');print(payload.relative_to(ROOT),len(rows),'files')
if __name__=='__main__':main()
