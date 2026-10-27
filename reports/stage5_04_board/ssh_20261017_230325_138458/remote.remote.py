from pathlib import Path
import os,sys,json,hashlib,shutil,subprocess,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_04_voice_run import discover_audio,devices,query
p=r/'reports/stage5_04_board/protection_final';p.mkdir();base=r/'reports/stage5_04_board'
load=lambda f:json.loads(f.read_text())
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
original=load(base/'original_before.json');accepted=load(base/'accepted_binaries_before.json');source=load(base/'source_before.json')
checks={'original_321_unchanged':original==fingerprint(),'accepted_5_1_5_2_5_3_binaries_unchanged':all(sha(r/n)==v for n,v in accepted.items()),'accepted_5_3_source_86_unchanged':all(sha(r/'stage5_03_source'/n)==v for n,v in source.items()),'frozen_baseline_5_3_source_86_unchanged':all(sha(base/'baseline_5_3_source'/n)==v for n,v in source.items())}
frozen={}
for label,folder in [('baseline_build','stage5_04_baseline_source'),('baseline_build_v2','stage5_04_baseline_source_v2'),('candidate_build','stage5_04_source'),('candidate_build_v2','stage5_04_source_v2'),('candidate_build_v3','stage5_04_source_v3')]:
 manifest=load(base/label/'source_manifest.json');frozen[label]={'files':len(manifest),'all_sha_match':all(sha(r/folder/x['file'])==x['sha256'] for x in manifest)}
# Stage5.3 keeps the old review root source fingerprint from before its own work.
old_manifest=r/'reports/stage5_03_board/source_before.json'
if old_manifest.exists():
 old=load(old_manifest);checks['review_root_source_from_5_2_unchanged']=all(sha(r/n)==v for n,v in old.items())
audio=discover_audio();dev=devices(audio);(p/'devices.json').write_text(json.dumps(dev,indent=2));checks['devices_clear']=dev['clear']
result={'checked_at_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':'after_automated_tests_before_manual_retry','checks':checks,'frozen_stage5_04_sources':frozen,'disk_free_bytes':shutil.disk_usage(r).free,'memory':query(['free','-b']),'original_fingerprint_count':len(original),'accepted_binaries':accepted,'stage5_03_source_files':len(source),'scope':'read-only fingerprint and device check; ordinary cat user','models_SDK_system_config_writes':False}
(p/'original_after.json').write_text(json.dumps(fingerprint(),indent=2));(p/'result.json').write_text(json.dumps(result,indent=2));print('PROTECTION_FINAL',json.dumps(result),flush=True)
assert all(checks.values()) and all(x['all_sha_match'] for x in frozen.values()) and result['disk_free_bytes']>=500*1024**2
