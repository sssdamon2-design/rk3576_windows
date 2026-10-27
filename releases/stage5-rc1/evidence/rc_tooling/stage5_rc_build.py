"""Board-only RC rebuild with finite limits and a 500 MiB disk guard."""
from pathlib import Path
import hashlib,json,os,signal,subprocess,time

def main():
 root=Path(__file__).resolve().parents[1];allowed=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
 assert root==allowed/'releases/stage5-rc1' and root.resolve()==root and os.getuid()==1000
 manifest=json.loads((root/'SOURCE_MANIFEST.json').read_text())
 assert all(hashlib.sha256((root/'source'/r['file']).read_bytes()).hexdigest()==r['sha256'] for r in manifest)
 report=allowed/'reports/stage5_rc1_board/build';report.mkdir();build=root/'build';assert not build.exists()
 steps=[]
 def step(name,cmd,limit):
  minimum=os.statvfs(root).f_bavail*os.statvfs(root).f_frsize;assert minimum>=500*1024**2
  start=time.monotonic();reason=None
  with (report/(name+'.stdout.log')).open('xb') as out,(report/(name+'.stderr.log')).open('xb') as err:
   child=subprocess.Popen(cmd,stdout=out,stderr=err,start_new_session=True)
   while child.poll() is None:
    v=os.statvfs(root);free=v.f_bavail*v.f_frsize;minimum=min(minimum,free)
    if free<500*1024**2:reason='disk_below_500MiB'
    if time.monotonic()-start>limit:reason='timeout'
    if reason:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=10)
     break
    time.sleep(.5)
  r={'name':name,'argv':cmd,'returncode':child.returncode,'reason':reason,'seconds':time.monotonic()-start,'minimum_disk_free_bytes':minimum};steps.append(r)
  (report/'steps.json').write_text(json.dumps(steps,indent=2)+'\n');print(json.dumps(r),flush=True)
  return child.returncode==0 and reason is None
 shell='source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$1/source" -B "$1/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_QT_GUI=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"'
 ok=step('configure',['bash','-c',shell,'rc',str(root)],90)
 if ok:ok=step('build',['cmake','--build',str(build),'--parallel','3'],600)
 if ok:ok=step('ctest',['bash','-c','source "$1/tools/stage5_board_paths.sh"; QT_QPA_PLATFORM=offscreen exec ctest --test-dir "$1/build" --output-on-failure --timeout 30 --output-junit "$2"','rc',str(root),str(report/'ctest.xml')],150)
 bins={}
 for n in ['asr_llm_tts_smoke','rk3576_multimodal_gui']:
  p=build/n
  if p.is_file():bins[n]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
 result={'successful':ok,'steps':steps,'binaries':bins,'source_files':len(manifest),'hardware_run':False,'disk_free_bytes':os.statvfs(root).f_bavail*os.statvfs(root).f_frsize}
 (report/'result.json').write_text(json.dumps(result,indent=2)+'\n');return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
