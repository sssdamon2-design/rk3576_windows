from pathlib import Path
import sys,json,subprocess,hashlib,os,shutil
R=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');rc=R/'releases/stage5-rc1'
assert R.resolve()==R and rc.resolve()==rc and os.getuid()==1000
report=R/'reports/stage5_rc1_board'/'rc1_release_smoke_20261018_135845_retry1';report.mkdir()
def save(n,d):
 with (report/n).open('x') as f:json.dump(d,f,indent=2)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
ver=json.loads((rc/'VERSION.json').read_text());assert ver['version']=='stage5-rc1' and ver['source_snapshot_id']=='sha256:2b19cd571f87e083b506da586aa1f1a772cd76ed253b1fe848337ff524fe6f87'
v=subprocess.run(['python3','-I','-B',str(rc/'tools/verify.py')],capture_output=True,timeout=90)
save('RC_verify_before.json',{'returncode':v.returncode,'stdout':v.stdout.decode(),'stderr':v.stderr.decode()});assert v.returncode==0
built=json.loads((R/'reports/stage5_rc1_board/build/result.json').read_text())['binaries']
assert all(sha(rc/'build'/n)==d['sha256'] for n,d in built.items())
sys.path.insert(0,str(R/'tools'));from stage5_05_voice_run import discover_audio,devices
from stage5_board_readonly_inventory import fingerprint
original=fingerprint();assert original==json.loads((R/'reports/stage5_05_board/original_before.json').read_text())
save('original_before.json',original);save('RC_identity.json',{'version':ver,'binaries':built,'manifest_sha256':sha(rc/'PACKAGE_MANIFEST.json'),'SHA256SUMS_sha256':sha(rc/'SHA256SUMS'),'harness_source_sha256':sha(R/'tools/stage5_05_gui_run.py')})
audio=discover_audio();save('audio_detection.json',audio);state=devices(audio);save('devices_initial.json',state)
baseline=None
if not state['clear'] and not state['primary_owner_queries']=={}:
 baseline=R/'reports/stage5_05_board'/('rc1_release_smoke_20261018_135845_retry1'+'_desktop_owners.json')
 q=subprocess.run(['python3','-I','-B',str(R/'tools/stage5_05_npu_inventory.py'),'--output',str(baseline)],capture_output=True,timeout=45)
 save('desktop_inventory.json',{'argv':q.args,'returncode':q.returncode,'stdout':q.stdout.decode(errors='replace'),'stderr':q.stderr.decode(errors='replace')});assert q.returncode==0
 os.environ['STAGE5_NPU_OWNER_BASELINE']=str(baseline);state=devices(audio);save('devices_after_desktop_inventory.json',state)
assert state['clear'],'Camera/ALSA/NPU occupied or owner check failed; do not launch'
assert shutil.disk_usage(R).free>524288000
save('preflight.json',{'passed':True,'audio_device':audio['alsa_device'],'disk_free_bytes':shutil.disk_usage(R).free,'owner_baseline':str(baseline) if baseline else None,'run_name':'rc1_release_smoke_20261018_135845_retry1','hardware_started':False})
print('PREFLIGHT_PASSED',json.dumps({'audio_device':audio['alsa_device'],'owner_baseline':str(baseline) if baseline else None,'name':'rc1_release_smoke_20261018_135845_retry1'}),flush=True)
