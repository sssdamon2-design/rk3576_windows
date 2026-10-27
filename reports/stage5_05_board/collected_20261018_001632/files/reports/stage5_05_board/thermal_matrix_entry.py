from pathlib import Path
import json,subprocess,time,os,sys
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');p=r/'reports/stage5_05_board/thermal_matrix';p.mkdir()
runner=r/'tools/stage5_05_voice_run.py'
f=r/'reports/stage5_04_board/baseline_voice_2t/audio_fixtures';audio=[f/'segment_1.f32',f/'segment_2.f32']
sequence=[0,0,1,1,0,1]
results=[]
def thermal():return {str(x):int(x.read_text())/1000 for x in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
for seconds,threads in [(180,2),(180,4),(1800,2),(1800,4)]:
 name=f"mixed_{seconds}s_{threads}t";cool=p/(name+'_cooldown.jsonl');start=time.monotonic()
 with cool.open('x') as log:
  while True:
   values=thermal();log.write(json.dumps({'monotonic':time.monotonic(),'temperatures_C':values})+'\n');log.flush()
   if max(values.values())<=55:break
   if time.monotonic()-start>600:raise RuntimeError('cooldown failed within 600s')
   time.sleep(20)
 offsets=list(range(0,seconds*1000,20000 if seconds==180 else 15000))+[seconds*1000]
 tsv=p/(name+'.tsv');tsv.write_text(''.join(str(t)+'\t'+str(audio[sequence[i%6]])+'\n' for i,t in enumerate(offsets)))
 command=['python3','-I','-B',str(runner),'--name',name,'--tts-threads',str(threads),'--audio-replay-file',str(tsv),'--fixed-frame-dir',str(r/'reports/stage5_03_board/raw_5_2_baseline'),'--timeout',str(seconds+160),'--grace','70','--seconds',str(seconds),'--stop-mode','cancel_pending']
 (p/(name+'_command.json')).write_text(json.dumps(command,indent=2))
 with (p/(name+'_runner.log')).open('xb') as out:
  code=subprocess.run(command,stdout=out,stderr=subprocess.STDOUT,timeout=seconds+260).returncode
 result=json.loads((p.parent/name/'result.json').read_text());results.append({'case':name,'runner_returncode':code,'result':result});(p/'progress.json').write_text(json.dumps(results,indent=2))
 if code or result['returncode'] or result['timeout'] or result['forced_kill'] or result['termination_reason'] or not result['devices_released'] or not result['original_321_unchanged']:
  (p/'result.json').write_text(json.dumps({'complete':False,'stopped_after':name,'cases':results},indent=2));raise SystemExit(1)
(p/'result.json').write_text(json.dumps({'complete':True,'cases':results,'note':'2/4 thread short tests then two matched nominal 30 minute mixed runs; no 60 minute claim'},indent=2))
