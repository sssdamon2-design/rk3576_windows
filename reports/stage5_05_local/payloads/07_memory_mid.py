from pathlib import Path
import json,re,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');base=r/'reports/stage5_05_board'
pid=json.loads((base/'mixed_1800s_4t/pid.json').read_text())['pid'];proc=Path('/proc')/str(pid)
assert (proc/'exe').resolve()==r/'build/stage5_05_thermal/asr_llm_tts_smoke'
p=base/'memory_4t_mid';p.mkdir();text=(proc/'smaps').read_text();(p/'smaps.txt').write_text(text)
rollup=(proc/'smaps_rollup').read_text();(p/'smaps_rollup.txt').write_text(rollup)
groups={};name=None
for line in text.splitlines():
 if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',line):
  parts=line.split(maxsplit=5);name=parts[5] if len(parts)>5 else '[anonymous]';groups.setdefault(name,{'Rss':0,'Private_Dirty':0,'Private_Clean':0,'Anonymous':0})
 elif name and ':' in line:
  key,value=line.split(':',1)
  if key in groups[name]:groups[name][key]+=int(value.split()[0])
result={'pid':pid,'sampled_at_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'scope':'one read-only own-process smaps snapshot during the 4-thread comparison; no allocator injection','groups_kB':dict(sorted(groups.items(),key=lambda x:-x[1]['Rss'])),'status':(proc/'status').read_text()}
(p/'result.json').write_text(json.dumps(result,indent=2));print('MEMORY_MID',json.dumps({'pid':pid,'top':list(result['groups_kB'].items())[:8]}))
