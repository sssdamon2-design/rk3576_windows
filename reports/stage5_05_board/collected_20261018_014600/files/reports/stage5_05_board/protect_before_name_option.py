"""Read-only final protection and device/kernel/memory evidence, new report only."""
from pathlib import Path
import hashlib,json,os,shutil,sys
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_05_voice_run import discover_audio,devices,query
b=r/'reports/stage5_05_board';out=b/'protection_final';out.mkdir()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
original=json.loads((b/'original_before.json').read_text());after=fingerprint();save(out/'original_after.json',after)
accepted=json.loads((b/'accepted_binaries_before.json').read_text());binary={p:sha(r/p)==s for p,s in accepted.items()}
frozen={}
for source,rows in [('stage5_04_source_v3',json.loads((b/'source_before.json').read_text())),('stage5_05_source_thermal',json.loads((b/'build_thermal/source_manifest.json').read_text())),('stage5_05_source_final_v2',json.loads((b/'build_final_v2/source_manifest.json').read_text()))]:
 frozen[source]={x['file']:sha(r/source/x['file'])==x['sha256'] for x in rows}
audio=discover_audio();d=devices(audio);save(out/'devices.json',d)
status={'memory':query(['free','-b']),'disk':query(['df','-B1',str(r)]),'dmesg':query(['dmesg','--ctime']),'thermal':{str(p):p.read_text() for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}};save(out/'system.json',status)
# Raw dmesg is preserved. Filter only the new window since the first short test.
previous=json.loads((b/'mixed_180s_2t/system_after.json').read_text())['dmesg']['stdout'].splitlines();current=status['dmesg']['stdout'].splitlines();last=previous[-1] if previous else None
if last in current:new=current[len(current)-1-current[::-1].index(last)+1:];window='since end of first 180s short test'
else:new=current;window='baseline tail not found; entire available ring, cannot isolate new messages'
import re
suspicious=[s for s in new if re.search(r'out of memory|oom-kill|segfault|kernel panic|rknpu.*(error|failed)|hung task|blocked for more than',s,re.I)]
save(out/'kernel_window.json',{'scope':window,'lines':new,'suspicious':suspicious,'dmesg_returncode':status['dmesg']['exit_code']})
checks={'original321_exact':original==after,'four_accepted_binaries':all(binary.values()),'frozen_sources':all(all(x.values()) for x in frozen.values()),'devices_clear':d['clear'],'disk_above500MiB':shutil.disk_usage(r).free>=500*1024**2,'no_new_suspicious_kernel_messages':not suspicious and status['dmesg']['exit_code']==0}
result={'checks':checks,'accepted_binaries':binary,'frozen_source_file_counts':{k:len(v) for k,v in frozen.items()},'frozen_sources':frozen,'disk_free_bytes':shutil.disk_usage(r).free,'final_executable_SHA256':{p.name:sha(p) for p in (r/'build/stage5_05_final_v2').glob('*') if p.is_file() and p.name in {'asr_llm_tts_smoke','rk3576_multimodal_gui'}},'no_stable_promotion':True}
save(out/'result.json',result);print('PROTECTION_RESULT',json.dumps({k:v for k,v in result.items() if k!='frozen_sources'}));raise SystemExit(0 if all(checks.values()) else 1)
