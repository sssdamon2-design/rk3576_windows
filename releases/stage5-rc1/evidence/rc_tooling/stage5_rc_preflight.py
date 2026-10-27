"""Board payload: read-only dependency/source checks; write new RC evidence only."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys
R=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert R.resolve()==R and os.getuid()==1000
assert not (R/'releases/stage5-rc1').exists(),'RC directory already exists; stop, never overwrite'
report=R/'reports/stage5_rc1_board/preflight_retry1';report.mkdir()
sys.path.insert(0,str(R/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_05_voice_run import discover_audio,devices
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def query(argv):
 r=subprocess.run(argv,capture_output=True,timeout=20);return {'argv':argv,'returncode':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}
original=fingerprint();assert original==json.loads((R/'reports/stage5_05_board/original_before.json').read_text())
frozen=json.loads((R/'reports/stage5_05_board/build_final_v2/source_manifest.json').read_text())
assert len(frozen)==104 and all(sha(R/'stage5_05_source_final_v2'/x['file'])==x['sha256'] for x in frozen)
accepted=json.loads((R/'reports/stage5_05_board/accepted_binaries_before.json').read_text())
assert all(sha(R/n)==h for n,h in accepted.items())
raw=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','rc',str(R)],timeout=15)
env=dict(s.decode().split('=',1) for s in raw.split(b'\0') if b'=' in s)
keys=['STAGE5_ASR','STAGE5_VAD','STAGE5_QWEN','STAGE5_KOKORO','STAGE5_VLM','STAGE5_VISION','STAGE5_SHERPA','STAGE5_RKLLM','STAGE5_RKNN_INCLUDE','STAGE5_RKNN_LIBRARY']
files=set()
for k in keys[:6]:
 p=Path(env[k]);assert p.exists()
 files.update(x for x in p.rglob('*') if x.is_file()) if p.is_dir() else files.add(p)
for p in [Path(env['STAGE5_SHERPA'])/'lib/libsherpa-onnx-c-api.so',Path(env['STAGE5_SHERPA'])/'lib/libonnxruntime.so',Path(env['STAGE5_SHERPA'])/'include/sherpa-onnx/c-api/c-api.h',Path(env['STAGE5_RKLLM'])/'rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so',Path(env['STAGE5_RKLLM'])/'rkllm-runtime/Linux/librkllm_api/include/rkllm.h',Path(env['STAGE5_RKNN_INCLUDE'])/'rknn_api.h',Path(env['STAGE5_RKNN_LIBRARY'])]:
 assert p.is_file(),p
 files.add(p)
dependencies=[{'path':str(p),'resolved_path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(files)]
try:
 audio=discover_audio();device=devices(audio)
except AssertionError as error:
 audio={'available':False,'reason':str(error),'cards':Path('/proc/asound/cards').read_text()};device={'clear':None,'scope':'not checked: required HyperX device unavailable; no hardware run authorized by this preflight result'}
result={'uid':os.getuid(),'uname':query(['uname','-a']),'os_release':Path('/etc/os-release').read_text(),'memory':query(['free','-b']),'cmake':query(['cmake','--version']),'compiler':query(['c++','--version']),'qt':query(['qmake','-query','QT_VERSION']),'disk_free_bytes':shutil.disk_usage(R).free,'paths':{k:env[k] for k in keys},'dependencies':dependencies,'original_321_unchanged':True,'accepted_binaries_unchanged':True,'frozen_104_match':True,'audio':audio,'devices':device,'RC_target_absent':True,'no_hardware_program_started':True}
assert result['disk_free_bytes']>700*1024**2
(report/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('RC_PREFLIGHT',json.dumps(result,ensure_ascii=False))
