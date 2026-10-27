from pathlib import Path
import json,hashlib,shutil,subprocess,sys,os
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');assert r.is_dir() and not r.is_symlink()
p=r/'reports/stage5_04_board';p.mkdir()
sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_03_voice_run import discover_audio,devices,query
expected=json.loads((r/'reports/stage5_03_board/final_state/source_sha256.json').read_text())
assert all(hashlib.sha256((r/'stage5_03_source'/n).read_bytes()).hexdigest()==v for n,v in expected.items())
assert all(not (r/n).exists() for n in ['stage5_04_source','stage5_04_baseline_source','build/stage5_04_board','build/stage5_04_baseline'])
assert shutil.disk_usage(r).free>=500*1024**2
snapshot=p/'baseline_5_3_source';snapshot.mkdir()
for n in expected:
 target=snapshot/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(r/'stage5_03_source'/n,target)
(p/'source_before.json').write_text(json.dumps(expected,indent=2))
(p/'original_before.json').write_text(json.dumps(fingerprint(),indent=2))
executables=['build/stage5_01_board/asr_llm_tts_smoke','build/stage5_02_board/asr_llm_tts_smoke','build/stage5_03_board/asr_llm_tts_smoke']
(p/'accepted_binaries_before.json').write_text(json.dumps({n:hashlib.sha256((r/n).read_bytes()).hexdigest() for n in executables},indent=2))
audio=discover_audio();dev=devices(audio)
commands=[['uname','-a'],['free','-b'],['df','-B1',str(r)],['lscpu'],['bash','-c','command -v pidstat; command -v perf; command -v top; command -v taskset'],['/sbin/ldconfig','-p']]
results=[query(c) for c in commands]
for x in results:
 if x['command'][0]=='/sbin/ldconfig':x['stdout']='\n'.join(s for s in x['stdout'].splitlines() if any(t in s for t in ['onnx','sherpa','rknn','rkllm']))
envout=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','stage5_04',str(r)],timeout=15)
env=dict(x.decode().split('=',1) for x in envout.split(b'\0') if b'=' in x)
sdk=Path(env['STAGE5_SHERPA'])
header=sdk/'include/sherpa-onnx/c-api/c-api.h';(p/'sherpa_c_api.h').write_bytes(header.read_bytes())
monitor={}
for pattern in ['/sys/devices/system/cpu/cpu*/cpu_capacity','/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq','/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor','/sys/class/devfreq/*/cur_freq','/sys/class/devfreq/*/load','/sys/class/thermal/thermal_zone*/temp','/sys/class/thermal/thermal_zone*/type']:
 import glob
 for name in glob.glob(pattern):
  try:monitor[name]=Path(name).read_text().strip()
  except OSError as e:monitor[name]={'error':str(e)}
fixtures=[]
for folder in [Path('/home/cat/projects/RK3576/asr_runtime'),r/'tests']:
 for f in folder.rglob('*.wav'):
  fixtures.append({'path':str(f),'bytes':f.stat().st_size})
  if len(fixtures)>=32:break
 if len(fixtures)>=32:break
value={'commands':results,'audio':audio,'devices':dev,'sdk_path':str(sdk),'sdk_libraries':[{'path':str(f),'bytes':f.stat().st_size} for f in (sdk/'lib').glob('*') if f.is_file()],'monitor':monitor,'wav_fixtures':fixtures,'disk_free_bytes':shutil.disk_usage(r).free,'original_source_count':len(expected)}
(p/'inventory.json').write_text(json.dumps(value,indent=2)+'\n')
print('INVENTORY',json.dumps({k:v for k,v in value.items() if k not in ['sdk_libraries','monitor','commands']}),flush=True)
print('MONITOR',json.dumps(monitor),flush=True)
for x in results:print('QUERY',json.dumps(x),flush=True)
assert dev['clear'],'devices occupied: stop hardware tests'
