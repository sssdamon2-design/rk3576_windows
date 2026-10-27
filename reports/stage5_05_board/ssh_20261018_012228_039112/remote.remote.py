from pathlib import Path
import json,re,os
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');out=r/'reports/stage5_05_board/final_gui_mid';out.mkdir();rows=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:
  exe=(proc/'exe').resolve()
  if not str(exe).startswith(str(r/'build/stage5_05_final_v2')):continue
  status=(proc/'status').read_text();fds={p.name:os.readlink(p) for p in (proc/'fd').iterdir()}
  row={'pid':int(proc.name),'exe':str(exe),'status':status,'hardware_fds':{k:v for k,v in fds.items() if v.startswith(('/dev/dri','/dev/video','/dev/snd'))},'smaps_rollup':(proc/'smaps_rollup').read_text()};rows.append(row)
 except OSError:pass
(out/'processes.json').write_text(json.dumps(rows,indent=2));(out/'result.json').write_text(json.dumps({'complete':True,'processes':len(rows),'scope':'read-only mid-run snapshot; no change to masks or processes'}))
for row in rows:print('MID',row['pid'],Path(row['exe']).name,re.search(r'^SigBlk:.*$',row['status'],re.M)[0],row['hardware_fds'])
