"""Targeted live Camera/VLM check after one driver sequence gap; no source change."""
from pathlib import Path
import hashlib,json,os,re,resource,signal,subprocess,sys,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(r/'tools'))
from stage5_05_voice_run import discover_audio,devices,query
from stage5_board_readonly_inventory import fingerprint
from stage5_04_run import sample
out=r/'reports/stage5_05_board/camera_gap_recheck';out.mkdir()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
audio=discover_audio();pre=devices(audio);save(out/'devices_before.json',pre);assert pre['clear'];original=fingerprint();save(out/'stable_before.json',original)
raw=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','recheck',str(r)],timeout=15);env=dict(x.decode().split('=',1) for x in raw.split(b'\0') if b'=' in x)
for key in list(env):
 if key.startswith('STAGE5_REPLAY') or key in {'STAGE5_PROFILE','STAGE5_IMAGE_PROFILE','STAGE5_FIXED_FRAMES'}:env.pop(key)
env['STAGE5_CAPTURE_FIXTURES']='0'
command=[str(r/'build/stage5_05_final_v2/stage5_03_memory_probe'),env['STAGE5_VLM'],env['STAGE5_VISION'],'/dev/video11',str(out),'64'];save(out/'command.json',command);save(out/'system_before.json',{'clock_ticks':os.sysconf('SC_CLK_TCK'),'dmesg':query(['dmesg','--ctime'])})
resource.setrlimit(resource.RLIMIT_CORE,(0,0));start=time.monotonic();sent=None;reason=None;forced=False
with (out/'terminal.log').open('xb') as log,(out/'resources.jsonl').open('x') as readings:
 child=subprocess.Popen(command,cwd=r,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);token=Path(f'/proc/{child.pid}/stat').read_text().split()[21];index=0
 while child.poll() is None:
  row=sample(child.pid,index);index+=1;readings.write(json.dumps(row)+'\n');readings.flush();now=time.monotonic()
  temps=[int(x.read_text())/1000 for x in Path('/sys/class/thermal').glob('thermal_zone*/temp')]
  if not temps or max(temps)>=90:reason='thermal_guard'
  if os.statvfs(r).f_bavail*os.statvfs(r).f_frsize<500*1024**2:reason='disk_guard'
  available=int(re.search(r'^MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text(),re.M)[1])
  if available<256*1024:reason='memory_guard'
  if now-start>240:reason=reason or 'timeout'
  def checked(sig):
   assert Path(f'/proc/{child.pid}/exe').resolve()==Path(command[0]) and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==token
   os.kill(child.pid,sig)
  if reason and sent is None:checked(signal.SIGTERM);sent=now
  if sent and now-sent>30:checked(signal.SIGKILL);forced=True;child.wait(timeout=10)
  time.sleep(1)
code=child.wait();post=devices(audio);save(out/'devices_after.json',post);after=fingerprint();save(out/'stable_after.json',after);save(out/'system_after.json',{'dmesg':query(['dmesg','--ctime']),'memory':query(['free','-b'])})
import csv
rows=list(csv.DictReader((out/'requests.csv').open())) if (out/'requests.csv').exists() else []
result={'returncode':code,'duration_seconds':time.monotonic()-start,'termination_reason':reason,'forced_kill':forced,'timeout':reason=='timeout','process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':original==after,'samples':len(rows),'all_VLM_success':len(rows)==64 and all(x['success']=='1' for x in rows),'input_mode':'LIVE Camera and real VLM only; no ASR, Qwen or TTS; no pixel/semantic ground truth for every frame','scope':'counter and kernel-log recheck, not a claimed fix of the isolated sequence gap'}
save(out/'result.json',result);print('CAMERA_RECHECK',json.dumps(result));raise SystemExit(0 if code==0 and not reason and not forced and post['clear'] and result['all_VLM_success'] and result['original_321_unchanged'] else 1)
