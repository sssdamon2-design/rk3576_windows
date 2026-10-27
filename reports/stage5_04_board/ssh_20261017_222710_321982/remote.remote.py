from pathlib import Path
import subprocess,json,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');gate=r/'reports/stage5_04_board/raw_tts_final_4t/result.json';start=time.monotonic()
while not gate.exists():
 assert time.monotonic()-start<2400
 time.sleep(1)
a=json.loads(gate.read_text());assert a['returncode']==0 and not a['termination_reason'] and a['devices_released'],a
base='/home/cat/projects/RK3576';fixed=str(r/'reports/stage5_03_board/raw_5_2_baseline');inputs=r/'reports/stage5_04_board/fixed_inputs'
def bench(name,target,argv,extra=()):
 cmd=['python3',str(r/'tools/stage5_04_run.py'),'--name',name,'--exe',str(r/'build/stage5_04_board_v2'/target),'--timeout','360','--env','STAGE5_PROFILE={REPORT}/profile.jsonl',*extra,'--',*argv]
 assert subprocess.run(cmd,timeout=410).returncode==0
bench('candidate_asr_30','stage5_04_asr_bench',[base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/test_wavs/zh.wav','{REPORT}','30'])
bench('candidate_vision_30','stage5_04_vision_bench',[base+'/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm',base+'/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn',fixed,'{REPORT}','30'],['--env','STAGE5_VISION_DUMP_DIR={REPORT}'])
bench('candidate_tts_profile_4t','stage5_04_tts_bench',['{KOKORO}','{REPORT}','4','3'])
def voice(name,variant,threads,file,extra=()):
 cmd=['python3','-u',str(r/'tools/stage5_04_voice_run.py'),'--name',name,'--variant',variant,'--revision','v2','--tts-threads',str(threads),'--audio-replay-file',str(file),'--fixed-frame-dir',fixed,'--tts-queue-ms','60000','--request-lifetime-ms','180000','--seconds','120','--timeout','260','--grace','70',*extra]
 assert subprocess.run(cmd,timeout=350).returncode==0
 result=json.loads((r/'reports/stage5_04_board'/name/'result.json').read_text())
 assert not result['timeout'] and not result['forced_kill'] and result['devices_released'] and result['shutdown_complete_marker'] and result['original_321_unchanged'],result
voice('baseline_pipeline_pairs_2t','baseline',2,r/'reports/stage5_04_board/paired_inputs/paired_six.tsv')
voice('candidate_pipeline_pairs_4t','candidate',4,r/'reports/stage5_04_board/paired_inputs/paired_six.tsv')
voice('candidate_burst_audio','candidate',4,inputs/'burst_four.tsv')
voice('candidate_expiry_audio','candidate',4,inputs/'pair_queue.tsv',['--tts-queue-ms','1'])
voice('candidate_sigint_drain','candidate',4,inputs/'waiting.tsv',['--signal','SIGINT','--trigger','ready','--delay','0.2'])
voice('candidate_sigterm_cancel_tts','candidate',4,inputs/'pair_queue.tsv',['--stop-mode','cancel_pending','--signal','SIGTERM','--trigger','vision','--delay','5'])
voice('candidate_sigterm_cancel_waiting','candidate',4,inputs/'waiting.tsv',['--stop-mode','cancel_pending','--signal','SIGTERM','--trigger','vision','--delay','0.1'])
print('AUTOMATED_MATRIX_COMPLETE',flush=True)
