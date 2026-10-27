from pathlib import Path
import subprocess,time,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');base=r/'reports/stage5_05_board';start=time.monotonic()
while not (base/'final_matrix/result.json').exists():
 assert time.monotonic()-start<4000,'matrix did not finish'
 proc=Path('/proc/37240/cmdline')
 assert proc.exists() and 'stage5_05_matrix.py' in proc.read_bytes().decode(errors='replace'),'matrix coordinator exited early; inspect original logs'
 time.sleep(5)
for tool in ['stage5_05_faults.py','stage5_05_protect.py']:
 with (base/(tool+'_runner.log')).open('xb') as f:code=subprocess.run(['python3','-I','-B',str(r/'tools'/tool)],stdout=f,stderr=subprocess.STDOUT,timeout=900).returncode
 print(tool,'returncode',code,flush=True);assert code==0,tool
