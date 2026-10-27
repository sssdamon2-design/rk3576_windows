from pathlib import Path
import subprocess,json,time
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review');done=r/'reports/stage5_04_board/candidate_build/result.json';start=time.monotonic()
while not done.exists():
 assert time.monotonic()-start<500
 time.sleep(1)
assert json.loads(done.read_text())['successful']
base='/home/cat/projects/RK3576'
cases=[('baseline_asr_30',r/'build/stage5_04_baseline/stage5_04_asr_bench',[base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/test_wavs/zh.wav','{REPORT}','30'],False),('baseline_vision_30',r/'reports/stage5_04_board/profile_tool_setup/vision_bench',[base+'/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm',base+'/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn',str(r/'reports/stage5_03_board/raw_5_2_baseline'),'{REPORT}','30'],False),('baseline_tts_ort_detail',r/'build/stage5_04_baseline/stage5_04_tts_bench',['{KOKORO}','{REPORT}','2','1'],True)]
for name,exe,argv,ort in cases:
 cmd=['python3',str(r/'tools/stage5_04_run.py'),'--name',name,'--exe',str(exe),'--timeout','360','--env','STAGE5_PROFILE={REPORT}/profile.jsonl']
 if 'vision' in name:cmd+=['--env','STAGE5_VISION_DUMP_DIR={REPORT}']
 if ort:cmd+=['--ort-profile']
 cmd+=['--',*argv]
 code=subprocess.run(cmd,timeout=400).returncode
 if code:raise SystemExit(code)
