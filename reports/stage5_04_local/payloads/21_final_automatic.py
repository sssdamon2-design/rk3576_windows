from pathlib import Path
import subprocess,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
fixed=str(r/'reports/stage5_03_board/raw_5_2_baseline');inputs=r/'reports/stage5_04_board/fixed_inputs'
for name,file,extra in [('candidate_final_sigterm_drain','waiting.tsv',['--signal','SIGTERM','--trigger','vision','--delay','0.1']),('candidate_default_queue_audio','pair_queue.tsv',[])]:
 cmd=['python3','-u',str(r/'tools/stage5_04_voice_run.py'),'--name',name,'--variant','candidate','--revision','v3','--tts-threads','4','--audio-replay-file',str(inputs/file),'--fixed-frame-dir',fixed,'--tts-queue-ms','12000','--request-lifetime-ms','45000','--seconds','120','--timeout','240','--grace','70',*extra]
 assert subprocess.run(cmd,timeout=330).returncode==0
 result=json.loads((r/'reports/stage5_04_board'/name/'result.json').read_text());assert result['returncode']==0 and result['devices_released'] and not result['timeout'] and not result['forced_kill'],result
print('FINAL_V3_AUTOMATED_SIGNALS_COMPLETE',flush=True)
