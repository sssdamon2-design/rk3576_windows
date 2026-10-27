from pathlib import Path
import subprocess,json,time,sys
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');base=r/'reports/stage5_05_board';out=base/'final_camera_followup';out.mkdir();start=time.monotonic()
while not (base/'final_matrix_retry1/result.json').exists():
 assert time.monotonic()-start<1200,'retry matrix did not finish'
 proc=Path('/proc/39883/cmdline');assert proc.exists() and 'stage5_05_matrix_retry1.py' in proc.read_bytes().decode(errors='replace'),'matrix failed; inspect logs before camera followup'
 time.sleep(3)
assert json.loads((base/'final_matrix_retry1/result.json').read_text())['complete']
commands=[('camera64',[sys.executable,'-I','-B',str(r/'tools/stage5_05_camera_recheck.py')],390),('NPU_inventory',[sys.executable,'-I','-B',str(r/'tools/stage5_05_npu_inventory.py'),'--output',str(base/'npu_desktop_owner_recheck.json')],30),('protection_after_camera',[sys.executable,'-I','-B',str(r/'tools/stage5_05_protect.py'),'--name','protection_final_after_camera'],120)]
results=[]
for name,command,timeout in commands:
 (out/(name+'_command.json')).write_text(json.dumps(command,indent=2))
 with (out/(name+'_runner.log')).open('xb') as f:rc=subprocess.run(command,stdout=f,stderr=subprocess.STDOUT,timeout=timeout).returncode
 results.append({'step':name,'returncode':rc});(out/'progress.json').write_text(json.dumps(results,indent=2));assert rc==0,name
(out/'result.json').write_text(json.dumps({'complete':True,'steps':results,'scope':'followup of one Camera driver sequence gap; original gap not rewritten as fixed'},indent=2))
