"""Final exact-source GUI and CLI regression matrix; never modifies SDK/system."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');base=r/'reports/stage5_05_board';out=base/'final_matrix_retry1';out.mkdir()
results=[]
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def run(name,command,timeout):
 save(out/(name+'_command.json'),command)
 with (out/(name+'_runner.log')).open('xb') as f:rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
 result=json.loads((base/name/'result.json').read_text());results.append(dict(case=name,runner_returncode=rc,result=result));save(out/'progress.json',results)
 assert rc==0 and result['returncode']==0 and not result.get('forced_kill') and result['devices_released'] and result['original_321_unchanged'],(name,result)
 return result
def gui(name,mode,extra=(),timeout=400):
 return run(name,[sys.executable,'-I','-B',str(r/'tools/stage5_05_gui_run.py'),'--name',name,'--build','stage5_05_final_v2','--mode',mode,*extra],timeout)
# Deterministic real-ASR load, shutdown and expiry cases on the exact final CLI.
f=r/'reports/stage5_04_board/baseline_voice_2t/audio_fixtures';vision=f/'segment_2.f32';text=f/'segment_1.f32'
fixtures={'burst':[(0,vision),(1000,text),(2000,vision),(3000,text)],'pair':[(0,vision),(1000,text),(100000,vision)],'single':[(0,vision),(100000,text)]}
for name,rows in fixtures.items():
 with (out/(name+'.tsv')).open('x') as f:f.write(''.join(str(t)+'\t'+str(p)+'\n' for t,p in rows))
common=[sys.executable,'-I','-B',str(r/'tools/stage5_05_voice_run.py'),'--build-name','stage5_05_final_v2','--tts-threads','4','--seconds','120','--timeout','180','--grace','70','--fixed-frame-dir',str(r/'reports/stage5_03_board/raw_5_2_baseline')]
for name,fixture,options in [
 ('final_burst_audio_retry1','burst',['--tts-queue-ms','60000','--request-lifetime-ms','180000','--signal','SIGINT','--trigger','both_done','--delay','0.1']),
 ('final_expiry_audio','pair',['--tts-queue-ms','1','--signal','SIGTERM','--trigger','ready','--delay','25']),
 ('final_sigint_drain','single',['--signal','SIGINT','--trigger','vision','--delay','0.1']),
 ('final_sigterm_cancel_waiting','pair',['--signal','SIGTERM','--trigger','vision','--delay','5','--stop-mode','cancel_pending']),
 ('final_sigterm_initialization','single',['--signal','SIGTERM','--trigger','init','--delay','0.2']),
 ('final_sigint_asr','single',['--signal','SIGINT','--trigger','ready','--delay','0.2'])]:
 run(name,common+['--name',name,'--audio-replay-file',str(out/(fixture+'.tsv'))]+options,280)
for tool in ['stage5_05_faults.py','stage5_05_protect.py']:
 with (out/(tool+'_runner.log')).open('xb') as f:rc=subprocess.run([sys.executable,'-I','-B',str(r/'tools'/tool)],stdout=f,stderr=subprocess.STDOUT,timeout=900).returncode
 assert rc==0,tool
save(out/'result.json',{'complete':True,'cases':results,'scope':'continuation after corrected primary DRM baseline; original GUI long passed separately'})
