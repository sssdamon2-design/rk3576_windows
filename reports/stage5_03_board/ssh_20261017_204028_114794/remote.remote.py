from pathlib import Path
import subprocess,json
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');report=root/'reports/stage5_03_board/rga_diagnostic'
r=subprocess.run(['dmesg','--ctime'],capture_output=True,timeout=15)
(report/'dmesg.stdout.log').write_bytes(r.stdout);(report/'dmesg.stderr.log').write_bytes(r.stderr)
print('DMESG_EXIT',r.returncode,flush=True);print('\n'.join(r.stdout.decode(errors='replace').splitlines()[-100:]),flush=True)
for cmd in [['id'],['/sbin/ldconfig','-p']]:
 r=subprocess.run(cmd,capture_output=True,timeout=15)
 text=r.stdout.decode(errors='replace')
 if cmd[0].endswith('ldconfig'):text='\n'.join(x for x in text.splitlines() if 'rga' in x.lower())
 print('READONLY',cmd,r.returncode,text,flush=True)
paths=['/home/cat/rknn_workspace/rknn-llm-stage4/examples/multimodal_model_demo/export/export_vision_rknn.py','/home/cat/projects/RK3576/rknn-llm/examples/multimodal_model_demo/export/export_vision_rknn.py']
for name in paths:
 p=Path(name)
 if p.is_file():print('CONVERSION_CONFIG',name,p.read_text(),flush=True)
 else:print('CONVERSION_CONFIG_ABSENT',name,flush=True)
