#!/usr/bin/env python3
"""Prepare an exclusive Stage5.4 source/build payload, never touch accepted builds."""
from pathlib import Path
import argparse,base64,hashlib,json
import stage5_phase2_deploy as transport
ROOT=Path(__file__).resolve().parents[1]
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--variant',choices=['baseline','candidate'],required=True);parser.add_argument('--revision',choices=['v1','v2','v3'],default='v1');args=parser.parse_args();suffix='' if args.revision=='v1' else '_'+args.revision
 baseline={r['file']:r['sha256'] for r in json.loads((ROOT/'reports/stage5_04_local/baseline_manifest.json').read_text(encoding='utf-8'))}
 selected=[Path('CMakeLists.txt')]
 for folder in ['include','src','tests']:
  selected.extend(p.relative_to(ROOT) for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in {'.h','.hpp','.cpp','.tsv','.txt','.cmake'})
 rows=[]
 snapshot=ROOT/'reports/stage5_04_local'/(('instrumented_baseline' if args.variant=='baseline' else 'candidate_snapshot')+suffix);snapshot.mkdir()
 for p in sorted(selected):
  b=(ROOT/p).read_bytes()
  if args.variant=='baseline' and args.revision in ('v2','v3'):
   if p.as_posix()=='include/audio/tts_service.h':b=b.replace(b'num_threads = 4',b'num_threads = 2')
   if p.as_posix()=='src/audio/asr_llm_tts_smoke.cpp':b=b.replace(b'int tts_threads = 4',b'int tts_threads = 2').replace(b'tts_threads=4',b'tts_threads=2')
  target=snapshot/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
  rows.append(dict(file=p.as_posix(),before=baseline.get(p.as_posix()),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
 report=ROOT/'reports/stage5_04_local'
 (report/(args.variant+suffix+'_deployment_manifest.json')).write_text(json.dumps([{k:v for k,v in r.items() if k!='data'} for r in rows],indent=2))
 source=transport.fingerprint_code()+'\nimport base64,signal,sys\nROWS='+repr(rows)+'\nVARIANT='+repr(args.variant)+'\nSUFFIX='+repr(suffix)+'\n'
 source+='''
assert os.getuid()==1000 and not REVIEW.is_symlink()
sys.path.insert(0,str(REVIEW/'tools'))
from stage5_02_board_run import discover_audio,devices
assert devices(discover_audio())['clear']
original=fingerprint();accepted={name:hashlib.sha256((REVIEW/name).read_bytes()).hexdigest() for name in ['build/stage5_01_board/asr_llm_tts_smoke','build/stage5_02_board/asr_llm_tts_smoke','build/stage5_03_board/asr_llm_tts_smoke']}
report=REVIEW/'reports/stage5_04_board'/(VARIANT+'_build'+SUFFIX);report.mkdir()
source=REVIEW/(('stage5_04_baseline_source' if VARIANT=='baseline' else 'stage5_04_source')+SUFFIX)
assert not source.exists() and not source.is_symlink()
shutil.copytree(REVIEW/'reports/stage5_04_board/baseline_5_3_source',source)
for row in ROWS:
 p=source/row['file'];assert p.resolve().is_relative_to(source) and not p.is_symlink()
 if p.exists():assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before'],row['file']
 data=base64.b64decode(row['data']);assert hashlib.sha256(data).hexdigest()==row['sha256']
 p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
(report/'source_manifest.json').write_text(json.dumps([{k:v for k,v in r.items() if k!='data'} for r in ROWS],indent=2))
results=[]
'''
 old=(ROOT/'reports/stage5_02_local/payloads/02_install_build.py').read_text(encoding='utf-8')
 source+=old[old.index('def step(label,cmd,limit):'):old.index('ok=True\nfor variant')]
 source+='''
build=REVIEW/(('build/stage5_04_baseline' if VARIANT=='baseline' else 'build/stage5_04_board')+SUFFIX);assert not build.exists()
config='source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"'
ok=step('configure',['bash','-c',config,'stage5_04',str(REVIEW),str(source),str(build)],180)
if ok:ok=step('build',['cmake','--build',str(build),'--parallel','3'],600)
if ok:
 config='source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"'
 ok=step('ctest',['bash','-c',config,'stage5_04',str(REVIEW),str(build),str(report/'ctest.xml')],120)
summary={'steps':results,'original_321_unchanged':original==fingerprint(),'accepted_binaries_unchanged':all(hashlib.sha256((REVIEW/p).read_bytes()).hexdigest()==h for p,h in accepted.items()),'disk_free_bytes':shutil.disk_usage(REVIEW).free,'successful':ok}
(report/'result.json').write_text(json.dumps(summary,indent=2));print('BUILD_SUMMARY',json.dumps(summary),flush=True)
raise SystemExit(0 if ok and summary['original_321_unchanged'] and summary['accepted_binaries_unchanged'] else 1)
'''
 payload=report/'payloads'/('03_build_'+args.variant+suffix+'.py');payload.write_text(source,encoding='utf-8');print(payload.relative_to(ROOT),len(rows),'files')
if __name__=='__main__':main()
