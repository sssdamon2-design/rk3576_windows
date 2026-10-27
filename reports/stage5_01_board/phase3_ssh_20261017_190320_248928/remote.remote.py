import base64,json,subprocess
from pathlib import Path
root=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert root.is_dir() and not root.is_symlink()
prior=root/'reports/stage5_01_board/voice_both_natural_01'
r=json.loads((prior/'result.json').read_text())
assert r['returncode']==0 and r['program_PASS'] and r['text_tts_completed'] and r['vision_tts_completed'] and r['devices_released']
confirmation=base64.b64decode('ew0KICAicmVhZGluZXNzIjogew0KICAgICJjb25maXJtZWQiOiB0cnVlLA0KICAgICJ1c2VyX21lc3NhZ2UiOiAi5YeG5aSH5aW95LqGIg0KICB9LA0KICAiYXVkaWJsZV9jb25maXJtYXRpb24iOiB7DQogICAgInJ1biI6ICJ2b2ljZV9ib3RoX25hdHVyYWxfMDEiLA0KICAgICJ1c2VyX21lc3NhZ2UiOiAi5Lik5Liq5Zue562U6YO95ZCs5Yiw5LqGIiwNCiAgICAidGV4dF9hbnN3ZXJfaGVhcmQiOiB0cnVlLA0KICAgICJ2aXNpb25fYW5zd2VyX2hlYXJkIjogdHJ1ZSwNCiAgICAic291cmNlIjogIkV4cGxpY2l0IHVzZXIgcmVwbHkgaW4gdGhpcyBjb252ZXJzYXRpb247IG5vdCBpbmZlcnJlZCBmcm9tIFRUUyBzdWNjZXNzIGxvZ3MiLA0KICAgICJ2aXN1YWxfYW5zd2VyX3NlbWFudGljX2FjY3VyYWN5X2NvbmZpcm1lZCI6IG51bGwNCiAgfSwNCiAgIm5vdGUiOiAiSGVhcmluZyBjb25maXJtYXRpb24gYXBwbGllcyB0byB0aGlzIG5hbWVkIHJ1biBvbmx5OyB2aXN1YWwgc2VtYW50aWMgYWNjdXJhY3kgd2FzIG5vdCBzZXBhcmF0ZWx5IGNvbmZpcm1lZC4iDQp9DQo=')
with (prior/'user_confirmation.json').open('xb') as f:f.write(confirmation)
cmd=['python3','-I',str(root/'tools/stage5_board_phase3_run.py'),'--name','voice_text_active_sigterm','--signal','SIGTERM','--trigger','llm','--delay','0.15','--seconds','120','--timeout','240','--grace','60']
r=subprocess.run(cmd,timeout=315)
raise SystemExit(r.returncode)
