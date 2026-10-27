#!/usr/bin/env python3
"""Portable-only validation, explicitly not RK3576/SDK verification."""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args();assert args.label.isidentifier()
    report=ROOT/'reports/stage5_05_local'/args.label;report.mkdir()
    scratch=Path(tempfile.mkdtemp(prefix='rk3576_stage5_05_'));source=scratch/'source';source.mkdir();build=scratch/'build'
    selected=[ROOT/'CMakeLists.txt']
    for name in ['include','src','tests']:
        selected.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and p.suffix in {'.h','.hpp','.cpp','.cmake','.tsv','.txt'})
    manifest=[]
    for path in selected:
        rel=path.relative_to(ROOT);p=source/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,p);manifest.append({'file':rel.as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (report/'source_manifest.json').write_text(json.dumps(manifest,indent=2))
    commands=[('configure',['cmake','-S',str(source),'-B',str(build),'-G','MinGW Makefiles','-DCMAKE_BUILD_TYPE=Debug','-DBUILD_TESTING=ON','-DBUILD_WITH_RKLLM=OFF','-DBUILD_WITH_VLM=OFF','-DENABLE_SHERPA_ASR=OFF'],90),('build',['cmake','--build',str(build),'--parallel','3'],240),('ctest',['ctest','--test-dir',str(build),'--output-on-failure','--timeout','30','--output-junit',str(report/'ctest.xml')],120)]
    results=[]
    for label,command,limit in commands:
        start=time.monotonic()
        with (report/(label+'.stdout.log')).open('wb') as out,(report/(label+'.stderr.log')).open('wb') as err:
            code=subprocess.run(command,stdout=out,stderr=err,timeout=limit).returncode
        value={'command':command,'returncode':code,'seconds':time.monotonic()-start};results.append(value);(report/(label+'.result.json')).write_text(json.dumps(value,indent=2))
        print(label,code,round(value['seconds'],3),flush=True)
        if code:
            print((report/(label+'.stdout.log')).read_text(encoding='utf-8',errors='replace')[-6000:]);print((report/(label+'.stderr.log')).read_text(encoding='utf-8',errors='replace')[-5000:]);break
    (report/'result.json').write_text(json.dumps({'platform':'Windows portable SDK off','hardware_verification':False,'steps':results,'successful':len(results)==3 and all(x['returncode']==0 for x in results)},indent=2))
    return 0 if len(results)==3 and all(x['returncode']==0 for x in results) else 1
if __name__=='__main__':raise SystemExit(main())
