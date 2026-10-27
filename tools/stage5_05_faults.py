"""Bounded invalid-path fault tests; expected failures retain actual exit codes."""
from pathlib import Path
import json,os,re,resource,signal,subprocess,sys,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(r/'tools'))
from stage5_05_voice_run import discover_audio,devices,query
from stage5_board_readonly_inventory import fingerprint
from stage5_04_run import sample
base=r/'reports/stage5_05_board';report=base/'real_invalid_paths';report.mkdir()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
audio=discover_audio();save(report/'audio_detection.json',audio);before=fingerprint();save(report/'stable_before.json',before)
raw=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','faults',str(r)],timeout=15)
env=dict(x.decode().split('=',1) for x in raw.split(b'\0') if b'=' in x)
for key in list(env):
 if key.startswith('STAGE5_REPLAY') or key in {'STAGE5_PROFILE','STAGE5_IMAGE_PROFILE'}:env.pop(key)
resource.setrlimit(resource.RLIMIT_CORE,(0,0));out=[]
original=[str(r/'build/stage5_05_final_v2/asr_llm_tts_smoke'),audio['alsa_device'],env['STAGE5_ASR'],env['STAGE5_VAD'],env['STAGE5_QWEN'],env['STAGE5_KOKORO'],audio['alsa_device'],'2','4','17',env['STAGE5_VLM'],env['STAGE5_VISION'],'/dev/video11']
for name,index,value in [('microphone_missing',1,'stage5_missing_capture'),('camera_missing',12,str(r/'reports/stage5_05_board/does_not_exist_video')),('playback_missing',6,'stage5_missing_playback'),('asr_model_missing',2,str(r/'reports/stage5_05_board/does_not_exist_asr'))]:
 case=report/name;case.mkdir();pre=devices(audio);save(case/'devices_before.json',pre);assert pre['clear']
 command=original.copy();command[index]=value;save(case/'command.json',command)
 start=time.monotonic();reason=None;sent=None;forced=False;last=0
 with (case/'terminal.log').open('xb') as log,(case/'resources.jsonl').open('x') as metrics:
  child=subprocess.Popen(command,env=env,cwd=r,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  token=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
  while child.poll() is None:
   now=time.monotonic()
   if now-last>=1:
    row=sample(child.pid,0);metrics.write(json.dumps(row)+'\n');metrics.flush();last=now
    temps=[int(x.read_text())/1000 for x in Path('/sys/class/thermal').glob('thermal_zone*/temp')]
    if not temps or max(temps)>=90:reason='thermal_guard'
    if os.statvfs(r).f_bavail*os.statvfs(r).f_frsize<500*1024**2:reason='disk_guard'
    available=int(re.search(r'^MemAvailable:\s+(\d+)',Path('/proc/meminfo').read_text(),re.M)[1])
    if available<256*1024:reason='memory_guard'
   if now-start>120:reason=reason or 'timeout'
   def checked(sig):
    assert (Path(f'/proc/{child.pid}/exe')).resolve()==Path(command[0]) and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==token
    os.kill(child.pid,sig)
   if reason and sent is None:checked(signal.SIGTERM);sent=now
   if sent and now-sent>70:checked(signal.SIGKILL);forced=True;child.wait(timeout=10)
   time.sleep(.1)
 post=devices(audio);save(case/'devices_after.json',post)
 result={'returncode':child.returncode,'expected_nonzero':True,'duration_seconds':time.monotonic()-start,'termination_reason':reason,'forced_kill':forced,'devices_released':post['clear'],'process_gone':not Path(f'/proc/{child.pid}').exists(),'scope':'invalid device/model name, not physical disconnection or SDK internal corruption'}
 result['expected_failure_clean']=result['returncode']!=0 and not reason and not forced and post['clear'] and result['process_gone'];save(case/'result.json',result);out.append({'case':name,**result});assert result['expected_failure_clean'],result
save(report/'result.json',{'complete':True,'cases':out,'original_321_unchanged':before==fingerprint(),'devices_released':devices(audio)['clear']});print('REAL_INVALID_PATHS_RESULT',json.dumps(out))
