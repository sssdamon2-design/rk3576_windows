#!/usr/bin/env python3
"""Run bounded Stage5.3 live/fixed Camera/VLM diagnostics inside the review root."""
from pathlib import Path
import argparse,hashlib,json,os,signal,subprocess,sys,time
ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_02_board_run import discover_audio,devices,sample
from stage5_board_readonly_inventory import fingerprint

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--variant',choices=['baseline','candidate'],required=True);parser.add_argument('--fixed',action='store_true');parser.add_argument('--samples',type=int,default=12);args=parser.parse_args()
 assert all(c.isalnum() or c in '_-' for c in args.name) and 1<=args.samples<=64
 assert Path(__file__).resolve().parents[1]==ROOT and not ROOT.is_symlink()
 report=ROOT/'reports/stage5_03_board'/args.name;report.mkdir()
 original=fingerprint();audio=discover_audio();pre=devices(audio);assert pre['clear']
 (report/'devices_before.json').write_text(json.dumps(pre,indent=2));(report/'parameters.json').write_text(json.dumps(vars(args),indent=2))
 envout=subprocess.check_output(['bash','-c','source "$1/tools/stage5_board_paths.sh"; env -0','stage5_03',str(ROOT)],timeout=15)
 env=dict(part.decode().split('=',1) for part in envout.split(b'\0') if b'=' in part)
 env['STAGE5_IMAGE_PROFILE']=str(report/'image_profile.jsonl')
 if args.fixed:
  env['STAGE5_FIXED_FRAMES']=str(ROOT/'reports/stage5_03_board/raw_5_2_baseline')
  env['STAGE5_VISION_DUMP_DIR']=str(report)
 else:env.pop('STAGE5_VISION_DUMP_DIR',None)
 binary=ROOT/('build/stage5_03_baseline/stage5_03_memory_probe' if args.variant=='baseline' else 'build/stage5_03_board/stage5_03_memory_probe')
 command=[str(binary),env['STAGE5_VLM'],env['STAGE5_VISION'],'fixed' if args.fixed else '/dev/video11',str(report),str(args.samples)]
 (report/'command.json').write_text(json.dumps(command,indent=2))
 with (report/'terminal.log').open('wb') as out,(report/'stderr.log').open('wb') as err,(report/'resources.jsonl').open('w') as resources:
  process=subprocess.Popen(command,env=env,cwd=ROOT,stdout=out,stderr=err,start_new_session=True);started=time.monotonic();forced=False;reason=None
  token=Path(f'/proc/{process.pid}/stat').read_text().split()[21]
  (report/'pid.json').write_text(json.dumps(dict(pid=process.pid,start_token=token,binary=str(binary))))
  while process.poll() is None:
   resources.write(json.dumps(sample(process.pid))+'\n');resources.flush()
   free=os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize
   if time.monotonic()-started>180 or free<500*1024**2:
    reason='timeout' if time.monotonic()-started>180 else 'disk_below_500MiB'
    assert Path(f'/proc/{process.pid}/exe').resolve()==binary and Path(f'/proc/{process.pid}/stat').read_text().split()[21]==token
    os.kill(process.pid,signal.SIGTERM)
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:os.kill(process.pid,signal.SIGKILL);forced=True;process.wait(timeout=10)
    break
   time.sleep(.25)
  code=process.wait();elapsed=time.monotonic()-started
 post=devices(audio);(report/'devices_after.json').write_text(json.dumps(post,indent=2))
 (report/'memory_after.txt').write_bytes(subprocess.check_output(['free','-b'],timeout=10))
 stderr=(report/'stderr.log').read_text(errors='replace')
 rows=sum(1 for _ in (report/'image_profile.jsonl').open()) if (report/'image_profile.jsonl').exists() else 0
 result=dict(returncode=code,seconds=elapsed,termination_reason=reason,forced_kill=forced,devices_released=post['clear'],process_gone=not Path(f'/proc/{process.pid}').exists(),original_321_unchanged=original==fingerprint(),profile_rows=rows,profile_errors='[ImageProfile ERROR]' in stderr)
 (report/'result.json').write_text(json.dumps(result,indent=2))
 print('PROBE_RESULT',args.name,json.dumps(result),flush=True);print((report/'terminal.log').read_text(errors='replace'),flush=True);print(stderr,flush=True)
 return 0 if code==0 and not reason and post['clear'] and rows and not result['profile_errors'] else 1
if __name__=='__main__':raise SystemExit(main())
