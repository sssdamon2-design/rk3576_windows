from pathlib import Path
import base64,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board')
print(json.dumps({'header':base64.b64encode((r/'sherpa_c_api.h').read_bytes()).decode(),'inventory':json.loads((r/'inventory.json').read_text())}))
