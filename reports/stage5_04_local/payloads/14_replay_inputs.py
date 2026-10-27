from pathlib import Path
import hashlib,json,shutil
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');p=r/'reports/stage5_04_board/fixed_inputs';p.mkdir()
a=r/'reports/stage5_04_board/baseline_voice_2t/audio_fixtures/segment_1.f32';v=a.with_name('segment_2.f32');assert a.is_file() and v.is_file()
inputs={}
for name,rows in {'single_text':[(0,a)],'single_vision':[(0,v)],'pair_queue':[(0,v),(1000,a)],'spaced_six':[(0,a),(30000,v),(60000,a),(90000,v)],'burst_four':[(0,v),(1000,a),(2000,v),(3000,a)],'waiting':[(0,v),(100000,a)]}.items():
 f=p/(name+'.tsv');f.write_text(''.join(str(offset)+'\t'+str(file)+'\n' for offset,file in rows));inputs[name]={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'contents':f.read_text()}
inputs['audio']={str(f):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in (a,v)}
f=r/'reports/stage5_03_board/raw_5_2_baseline/frame_0.nv12';inputs['fixed_NV12']={'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'metadata':json.loads(f.with_suffix('.json').read_text())}
(p/'result.json').write_text(json.dumps(inputs,indent=2));print(json.dumps(inputs,indent=2))
feedback={'case':'baseline_voice_2t','statement':'两个回答都听到了','both_TEXT_VISION_audible':True,'visual_content_confirmation':None,'source':'User response in current Stage5.4 session'}
(r/'reports/stage5_04_board/baseline_voice_2t/user_feedback.json').write_text(json.dumps(feedback,ensure_ascii=False,indent=2))
