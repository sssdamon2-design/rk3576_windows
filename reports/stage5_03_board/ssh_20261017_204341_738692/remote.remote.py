from pathlib import Path
import json,subprocess,sys,time,os,signal
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(root/'tools'))
from stage5_02_board_run import discover_audio,devices,sample
assert devices(discover_audio())['clear']
report=root/'reports/stage5_03_board/rga_diagnostic';report.mkdir()
exe=root/'build/stage5_03_board/stage5_03_rga_probe'
cmd=['bash','-c','source "$1/tools/stage5_board_paths.sh"; export STAGE5_RGA_ONLY_DMA=1; exec "$1/build/stage5_03_board/stage5_03_rga_probe" "$1/reports/stage5_03_board/raw_5_2_baseline" "$2" "$STAGE5_VISION"','stage5_03',str(root),str(report)]
(report/'command.json').write_text(json.dumps(cmd,indent=2))
with (report/'terminal.log').open('wb') as o,(report/'stderr.log').open('wb') as e,(report/'resources.jsonl').open('w') as samples:
 p=subprocess.Popen(cmd,stdout=o,stderr=e,start_new_session=True);start=time.monotonic();timed_out=False
 while p.poll() is None:
  samples.write(json.dumps(sample(p.pid))+'\n');samples.flush()
  if time.monotonic()-start>180:
   assert Path(f'/proc/{p.pid}/exe').resolve()==exe;os.kill(p.pid,signal.SIGTERM);p.wait(timeout=10);timed_out=True;break
  time.sleep(.25)
 result={'returncode':p.wait(),'seconds':time.monotonic()-start,'timeout':timed_out,'devices_released':devices(discover_audio())['clear']}
(report/'result.json').write_text(json.dumps(result,indent=2));print('RGA_RESULT',json.dumps(result),flush=True)
print((report/'terminal.log').read_text(errors='replace'),flush=True);print((report/'stderr.log').read_text(errors='replace'),flush=True)
raise SystemExit(result['returncode'])
