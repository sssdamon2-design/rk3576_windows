from pathlib import Path
import hashlib,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');p=r/'reports/stage5_04_board/paired_inputs';p.mkdir()
f=r/'reports/stage5_04_board/baseline_voice_2t/audio_fixtures';a=f/'segment_1.f32';v=f/'segment_2.f32'
rows=[(0,v),(1000,a),(40000,v),(41000,a),(80000,v),(81000,a)]
tsv=p/'paired_six.tsv';tsv.write_text(''.join(str(t)+'\t'+str(file)+'\n' for t,file in rows))
(p/'result.json').write_text(json.dumps({'path':str(tsv),'sha256':hashlib.sha256(tsv.read_bytes()).hexdigest(),'contents':tsv.read_text(),'conditions':'same fixed presegmented actual speech + frame_0; no microphone or VAD in offline replay; three VISION/TEXT pairs; 60s TTS max wait, 180s request lifetime'},indent=2));print('Created paired inputs',tsv)
