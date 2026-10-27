from pathlib import Path
import json,os
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');b=r/'reports/stage5_05_board'
p=b/'gui_microphone_final_v2/user_feedback.json';assert not p.exists()
p.write_text(json.dumps({'both_TEXT_VISION_audible':True,'vision_roughly_matches':True,'GUI_recognition_route_answer_visible':True,'user_exact_reply':'是的，和你描述的一样','confirmed_at_local':'2026-10-18 Asia/Hong_Kong','scope':'current gui_microphone_final_v2 actual HyperX and existing display'},ensure_ascii=False,indent=2))
for q in [b/'final_matrix/progress.json',b/'final_matrix_launcher.log']:
 if q.exists():print(q.name,q.read_text()[-7000:])
for x in Path('/proc').iterdir():
 if x.name.isdigit():
  try:
   exe=(x/'exe').resolve()
   if str(exe).startswith(str(r/'build/stage5_05_final_v2')):
    print('PROCESS',x.name,exe,(x/'status').read_text().splitlines()[:8]);print('TASKCHILDREN',[(str(t),t.read_text()) for t in (x/'task').glob('*/children')])
  except OSError:pass
