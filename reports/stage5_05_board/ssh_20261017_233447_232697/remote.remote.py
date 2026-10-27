from pathlib import Path
import json,subprocess
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
p=r/'reports/stage5_05_board/build_thermal'
for n in ['configure.stdout.log','configure.stderr.log','build.stdout.log','build.stderr.log','result.json']:
 f=p/n
 if f.exists():print(n,f.read_text(errors='replace')[-2200:])
for proc in Path('/proc').glob('[0-9]*'):
 try:
  if proc.stat().st_uid==1000 and (proc/'comm').read_text().strip() in {'gnome-shell','Xorg'}:
   env=dict(x.split('=',1) for x in (proc/'environ').read_bytes().decode().split('\0') if '=' in x)
   print('DISPLAY_ENV',proc.name,{k:env[k] for k in ['DISPLAY','XAUTHORITY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR'] if k in env})
 except OSError:pass
print('QMAKE',subprocess.run(['qmake','-v'],capture_output=True,text=True,timeout=10).stdout)
