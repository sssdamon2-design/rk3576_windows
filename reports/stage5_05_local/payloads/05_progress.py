from pathlib import Path
import json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board')
for n in ['thermal_matrix_launcher.log','thermal_matrix/progress.json','thermal_matrix/result.json']:
 p=r/n
 if p.exists():print(n,p.read_text()[-3000:])
for p in sorted(r.glob('mixed_*/terminal.log')):print(str(p.parent.name),p.read_text(errors='replace')[-1600:])
print('TEMPS',{str(p):p.read_text().strip() for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')})
