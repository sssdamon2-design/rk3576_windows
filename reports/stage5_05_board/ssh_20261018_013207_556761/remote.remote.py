from pathlib import Path
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
for name in ['final_matrix/final_burst_audio_runner.log','post_matrix_launcher.log']:
 p=r/name
 if p.exists():print(name,p.read_text()[-5000:])
for p in Path('/sys/class/drm').iterdir():
 driver=p/'device/driver'
 if driver.exists():print('DRM',p.name,str(driver.resolve()))
