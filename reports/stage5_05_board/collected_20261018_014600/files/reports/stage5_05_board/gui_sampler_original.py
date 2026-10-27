"""Run actual Qt/CLI processes on the existing X11 display, guarded and PID-owned."""
from pathlib import Path
import argparse,hashlib,json,os,queue,re,resource,signal,subprocess,sys,threading,time
ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_04_voice_run import discover_audio,devices,query
from stage5_board_readonly_inventory import fingerprint
from stage5_04_run import sample

def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--build',required=True)
 p.add_argument('--mode',choices=['paired_restart','sigterm_vision','microphone','stability'],required=True)
 p.add_argument('--timeout',type=int,default=260);p.add_argument('--threads',type=int,default=4);p.add_argument('--seconds',type=int,default=180);p.add_argument('--audio-replay-file')
 a=p.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]+',a.name) and re.fullmatch(r'stage5_05_\w+',a.build)
 assert 30<=a.timeout<=2400 and 1<=a.seconds<=3600 and a.threads in {2,4} and ROOT.resolve()==ROOT
 report=ROOT/'reports/stage5_05_board'/a.name;report.mkdir()
 audio=discover_audio();pre=devices(audio);save(report/'audio_detection.json',audio);save(report/'devices_before.json',pre);assert pre['clear']
 original=fingerprint();save(report/'stable_before.json',original)
 raw=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','stage5_05',str(ROOT)],timeout=15)
 env=dict(x.decode().split('=',1) for x in raw.split(b'\0') if b'=' in x)
 env.update(DISPLAY=':0',XAUTHORITY='/run/user/1000/gdm/Xauthority',XDG_RUNTIME_DIR='/run/user/1000',QT_QPA_PLATFORM='xcb')
 for key,leaf in [('XDG_CACHE_HOME','cache'),('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('TMPDIR','tmp'),('QT_SHADER_CACHE_DIR','shader_cache')]:
  path=report/leaf;path.mkdir();env[key]=str(path)
 for key in ['STAGE5_REPLAY_FILE','STAGE5_REPLAY_AUDIO_FILE','STAGE5_REPLAY_FRAME_DIR','STAGE5_CAPTURE_AUDIO_FIXTURES','STAGE5_PROFILE']:env.pop(key,None)
 env['STAGE5_TTS_QUEUE_MS']='12000' if a.mode=='stability' else '60000';env['STAGE5_REQUEST_LIFETIME_MS']='45000' if a.mode=='stability' else '180000'
 if a.mode=='stability':env['STAGE5_STOP_MODE']='cancel_pending'
 if a.mode!='microphone':
  f=ROOT/'reports/stage5_04_board/baseline_voice_2t/audio_fixtures'
  replay=report/'input.tsv';replay.write_text('0\t'+str(f/'segment_2.f32')+'\n1000\t'+str(f/'segment_1.f32')+'\n100000\t'+str(f/'segment_2.f32')+'\n')
  if a.audio_replay_file:
   replay=Path(a.audio_replay_file);assert replay.resolve().is_relative_to(ROOT) and replay.is_file()
  env['STAGE5_REPLAY_AUDIO_FILE']=str(replay)
  if a.mode in {'paired_restart','stability'}:env['STAGE5_REPLAY_FRAME_DIR']=str(ROOT/'reports/stage5_03_board/raw_5_2_baseline')
  save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'contents':replay.read_text()})
 command=[str(ROOT/'build'/a.build/'rk3576_multimodal_gui'),'--capture',audio['alsa_device'],'--playback',audio['alsa_device'],'--report-root',str(report),'--seconds',str(a.seconds),'--threads',str(a.threads),'--auto-start','--stop-after-answers','2' if a.mode in {'paired_restart','microphone'} else '0','--cycles','2' if a.mode=='paired_restart' else '1']
 save(report/'command.json',command);save(report/'parameters.json',vars(a));save(report/'system_before.json',{'clock_ticks':os.sysconf('SC_CLK_TCK'),'memory':query(['free','-b'])})
 save(report/'environment.json',{k:v for k,v in env.items() if k.startswith(('STAGE5_','XDG_','QT_')) or k in {'DISPLAY','XAUTHORITY','LD_LIBRARY_PATH','TMPDIR'}})
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 child=subprocess.Popen(command,env=env,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
 token=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
 save(report/'pid.json',{'pid':child.pid,'exe':command[0],'token':token})
 messages=queue.Queue()
 def reader():
  for line in iter(child.stdout.readline,b''):messages.put(line)
  messages.put(None)
 thread=threading.Thread(target=reader,daemon=True);thread.start()
 start=time.monotonic();eof=False;sent=None;reason=None;forced=False;trigger=None;last_sample=0;index=0;lines=[];owned_children={};active_run=None
 def checked(pid,exe,start_token,value):
  proc=Path('/proc')/str(pid)
  assert (proc/'exe').resolve()==Path(exe).resolve() and (proc/'stat').read_text().split()[21]==start_token
  os.kill(pid,value)
 with (report/'terminal.log').open('xb') as log,(report/'resources.jsonl').open('x') as resources:
  while child.poll() is None or not eof:
   try:
    item=messages.get(timeout=.1)
    if item is None:eof=True
    else:
     log.write(item);log.flush();sys.stdout.buffer.write(item);sys.stdout.buffer.flush();text=item.decode(errors='replace');lines.append(text)
     if '[GUI run] ' in text:
      active_run=Path(text.strip().split('[GUI run] ',1)[1]);assert active_run.resolve().is_relative_to(report)
      save(active_run/'system_before.json',{'clock_ticks':os.sysconf('SC_CLK_TCK'),'scope':'backend process samples; GUI process resource log is separate'})
     if '[ASR->VISION #' in text and trigger is None:trigger=time.monotonic()
   except queue.Empty:pass
   now=time.monotonic()
   if child.poll() is None and now-last_sample>=1:
    last_sample=now;resources.write(json.dumps(sample(child.pid,index))+'\n');resources.flush();index+=1
    # Record only this GUI's direct child, for bounded last-resort failure cleanup.
    children=Path(f'/proc/{child.pid}/task/{child.pid}/children')
    for value in children.read_text().split() if children.exists() else []:
     proc=Path('/proc')/value
     try:
      exe=str((proc/'exe').resolve());tok=(proc/'stat').read_text().split()[21]
      if Path(exe).is_relative_to(ROOT/'build'/a.build):
       owned_children[int(value)]={'exe':exe,'token':tok}
       if active_run:
        reading=sample(int(value),index)
        reading['cooling_and_maxfreq']={str(x):x.read_text().strip() for pattern in ['sys/class/thermal/cooling_device*/cur_state','sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq'] for x in Path('/').glob(pattern)}
        with (active_run/'resources.jsonl').open('a') as backend_samples:backend_samples.write(json.dumps(reading)+'\n')
     except OSError:pass
    temps=[int(x.read_text())/1000 for x in Path('/sys/class/thermal').glob('thermal_zone*/temp')]
    if max(temps)>=90:reason='conservative_90C_guard'
    available=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
    if available<256*1024:reason='MemAvailable_below_256MiB'
    if os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize<500*1024**2:reason='disk_below_500MiB'
   if child.poll() is None and sent is None and (reason or now-start>a.timeout or a.mode=='sigterm_vision' and trigger is not None and now-trigger>=.2):
    if now-start>a.timeout:reason='timeout'
    checked(child.pid,command[0],token,signal.SIGTERM);sent=now
   if child.poll() is None and sent is not None and now-sent>90:
    # Failure only, never used to claim orderly shutdown. Every PID is rechecked.
    for pid,info in owned_children.items():
     if Path(f'/proc/{pid}').exists():checked(pid,info['exe'],info['token'],signal.SIGKILL)
    checked(child.pid,command[0],token,signal.SIGKILL);forced=True;child.wait(timeout=10)
   if child.poll() is not None and not eof and now-start>a.timeout+110:raise RuntimeError('Qt child output not closed')
 ended=time.monotonic();code=child.wait();thread.join(timeout=5)
 post=devices(audio);save(report/'devices_after.json',post);save(report/'stable_after.json',fingerprint())
 sessions=[json.loads(x.read_text()) for x in sorted(report.glob('run_*/result.json'))]
 expected=2 if a.mode=='paired_restart' else 1
 result={'returncode':code,'duration_seconds':ended-start,'signal_to_exit_seconds':None if sent is None else ended-sent,'sent_signal':None if sent is None else 'SIGTERM','termination_reason':reason,'forced_kill':forced,'timeout':reason=='timeout','process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':original==fingerprint(),'sessions':sessions,'all_sessions_orderly':len(sessions)==expected and all(x['orderly'] and x['returncode']==0 for x in sessions),'platform':'xcb DISPLAY :0 actual existing desktop','input_mode':a.mode,'owned_children':owned_children,'user_audible_confirmation':None}
 save(report/'result.json',result);print('GUI_RUN_RESULT',json.dumps(result),flush=True)
 return 0 if code==0 and not forced and not reason and result['all_sessions_orderly'] and post['clear'] and result['original_321_unchanged'] else 1
if __name__=='__main__':raise SystemExit(main())
