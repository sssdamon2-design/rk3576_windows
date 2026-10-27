from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
assert r.resolve()==r and not r.is_symlink() and os.getuid()!=0
p=r/'reports/stage5_05_board';p.mkdir()
report=p/'inventory';report.mkdir()
sys.path.insert(0,str(r/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_04_voice_run import discover_audio,devices,query
original=json.loads((r/'reports/stage5_04_board/original_before.json').read_text())
assert original==fingerprint()
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
accepted={n:sha(r/n) for n in ['build/stage5_01_board/asr_llm_tts_smoke','build/stage5_02_board/asr_llm_tts_smoke','build/stage5_03_board/asr_llm_tts_smoke','build/stage5_04_board_v3/asr_llm_tts_smoke']}
source=json.loads((r/'reports/stage5_04_board/candidate_build_v3/source_manifest.json').read_text())
assert all(sha(r/'stage5_04_source_v3'/row['file'])==row['sha256'] for row in source)
(p/'original_before.json').write_text(json.dumps(original,indent=2))
(p/'accepted_binaries_before.json').write_text(json.dumps(accepted,indent=2))
(p/'source_before.json').write_text(json.dumps(source,indent=2))
thermal={}
for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
 thermal[str(zone)]={x.name:x.read_text().strip() for x in zone.iterdir() if x.name in {'type','temp','mode','policy'} or x.name.startswith('trip_point_') and x.is_file()}
cooling={}
for path in Path('/sys/class/thermal').glob('cooling_device*'):
 cooling[str(path)]={x.name:x.read_text().strip() for x in path.iterdir() if x.name in {'type','cur_state','max_state'}}
commands=[['uname','-a'],['free','-b'],['df','-B1',str(r)],['bash','-c','command -v qmake qmake6 qtpaths qtpaths6 cmake Xvfb xwd import scrot weston wayland-info || true'],['bash','-c','printf "DISPLAY=%s WAYLAND_DISPLAY=%s XDG_RUNTIME_DIR=%s\n" "$DISPLAY" "$WAYLAND_DISPLAY" "$XDG_RUNTIME_DIR"'],['dpkg-query','-W','-f=${binary:Package} ${Version}\n','*qt*','*xserver*','*wayland*','*libreoffice*'],['ps','-eo','pid,user,comm,args'],['bash','-c','ls -ld /tmp/.X11-unix /run/user/1000 /usr/lib/aarch64-linux-gnu/cmake/Qt5* /usr/lib/aarch64-linux-gnu/qt5/plugins/platforms 2>/dev/null || true']]
audio=discover_audio();device=devices(audio)
result={'checked_at_UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'commands':[query(c) for c in commands],'thermal':thermal,'cooling_devices':cooling,'cpufreq':{str(x):x.read_text().strip() for pattern in ['cpu*/cpufreq/scaling_governor','cpu*/cpufreq/scaling_cur_freq','cpu*/cpufreq/scaling_available_frequencies','cpu*/cpufreq/cpuinfo_max_freq'] for x in Path('/sys/devices/system/cpu').glob(pattern)},'drm':{str(x):x.read_text().strip() for x in Path('/sys/class/drm').glob('card*-*/status')},'audio':audio,'devices':device,'accepted_binaries':accepted,'original_321_unchanged':True,'final_5_4_source_matches':True,'disk_free_bytes':shutil.disk_usage(r).free,'scope':'read-only environment query; new reports55 metadata only'}
(report/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print('STAGE5_05_INVENTORY',json.dumps(result,ensure_ascii=False),flush=True)
assert device['clear'] and result['disk_free_bytes']>=500*1024**2
