# 5.5 重要命令及真实输出解析

以下命令来自保存的argv，复现应选不存在的新case和build目录。模型/SDK仅引用现有路径。SSH传输码和测试子进程退出码分别保存，故意非法路径必须非零且完成清理。

## build_final_v2 build

目的：用现有ARM64 SDK配置、全量构建或运行确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2 --parallel 3
```

参数逐项：`bash -c`执行保存的脚本，后续占位名为$0，再依次$1/$2/$3/$4；source只加载本次环境。`cmake -S`冻结源码、`-B`独立产物、`-DCMAKE_BUILD_TYPE=Release`优化、`BUILD_TESTING=ON`测试；`BUILD_WITH_RKLLM/BUILD_WITH_VLM/ENABLE_SHERPA_ASR=ON`链接真实SDK，ROOT/INCLUDE/RUNTIME_LIBRARY指定原路径，`BUILD_QT_GUI=ON`启用Qt5 Widgets/Test。`--build --parallel 3`最多3编译任务；`ctest --test-dir`选构建、`--timeout 30`逐项上限、`--output-on-failure`保留错误、`--output-junit`保存XML。

真实退出记录节选：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 156.08595781799886
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/build_final_v2/build.stdout.log`）：

```text
[ 97%] Building CXX object CMakeFiles/asr_llm_tts_smoke.dir/src/audio/asr_llm_tts_smoke.cpp.o
[ 98%] Linking CXX executable tts_worker_queue_smoke
[ 99%] Linking CXX executable gui_session_tests
[ 99%] Built target tts_worker_queue_smoke
[ 99%] Built target gui_session_tests
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## build_final_v2 configure

目的：用现有ARM64 SDK配置、全量构建或运行确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY" -DBUILD_QT_GUI="$4"' stage5_05 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_05_source_final_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2 ON
```

参数逐项：`bash -c`执行保存的脚本，后续占位名为$0，再依次$1/$2/$3/$4；source只加载本次环境。`cmake -S`冻结源码、`-B`独立产物、`-DCMAKE_BUILD_TYPE=Release`优化、`BUILD_TESTING=ON`测试；`BUILD_WITH_RKLLM/BUILD_WITH_VLM/ENABLE_SHERPA_ASR=ON`链接真实SDK，ROOT/INCLUDE/RUNTIME_LIBRARY指定原路径，`BUILD_QT_GUI=ON`启用Qt5 Widgets/Test。`--build --parallel 3`最多3编译任务；`ctest --test-dir`选构建、`--timeout 30`逐项上限、`--output-on-failure`保留错误、`--output-junit`保存XML。

真实退出记录节选：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 3.0020454799996514
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/build_final_v2/configure.stdout.log`）：

```text
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## build_final_v2 ctest

目的：用现有ARM64 SDK配置、全量构建或运行确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; QT_QPA_PLATFORM=offscreen exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_05 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/build_final_v2/ctest.xml
```

参数逐项：`bash -c`执行保存的脚本，后续占位名为$0，再依次$1/$2/$3/$4；source只加载本次环境。`cmake -S`冻结源码、`-B`独立产物、`-DCMAKE_BUILD_TYPE=Release`优化、`BUILD_TESTING=ON`测试；`BUILD_WITH_RKLLM/BUILD_WITH_VLM/ENABLE_SHERPA_ASR=ON`链接真实SDK，ROOT/INCLUDE/RUNTIME_LIBRARY指定原路径，`BUILD_QT_GUI=ON`启用Qt5 Widgets/Test。`--build --parallel 3`最多3编译任务；`ctest --test-dir`选构建、`--timeout 30`逐项上限、`--output-on-failure`保留错误、`--output-junit`保存XML。

真实退出记录节选：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 7.0067366089970164
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/build_final_v2/ctest.stdout.log`）：

```text
7/8 Test #7: camera_service_tests .............   Passed    0.22 sec
    Start 8: gui_session_tests
8/8 Test #8: gui_session_tests ................   Passed    5.50 sec

100% tests passed, 0 tests failed out of 8

Total Test time (real) =   6.43 sec
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## thermal_matrix mixed_1800s_2t_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --name mixed_1800s_2t --tts-threads 2 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_2t.tsv --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --timeout 1960 --grace 70 --seconds 1800 --stop-mode cancel_pending
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`mixed_1800s_2t`。 `--tts-threads`Kokoro线程数，实际值`2`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_2t.tsv`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--timeout`运行截止秒数，超时必须记失败，实际值`1960`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--seconds`有限输入监听秒数，实际值`1800`。 `--stop-mode`排空或取消等待，活动同步SDK不被强行中断，实际值`cancel_pending`。

真实退出记录节选：

```json
{
  "pid": 32878,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 1839.8901995140004,
  "input_closed_to_exit_seconds": 17.66012788200169,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": true,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "cancel_pending"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/thermal_matrix/mixed_1800s_2t_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=121 completed=121 started=121 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=265455 queue_max_ms=5738.32 service_sum_ms=1.72508e+06
[PipelineStats] dispatched=121 accepted=121 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=60 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=54595 reused=54593 exhausted=0
[CameraCounters] published=54594 fps=29.997 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 32878, "returncode": 0, "termination_reason": null, "sent_signal": null, "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 1839.8901995140004, "input_closed_to_exit_seconds": 17.66012788200169, "signal_to_exit_seconds": null, "timing_scope": "child exit/output EOF, excludes subsequent device/fi
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/mixed_1800s_2t
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## thermal_matrix mixed_1800s_4t_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --name mixed_1800s_4t --tts-threads 4 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_4t.tsv --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --timeout 1960 --grace 70 --seconds 1800 --stop-mode cancel_pending
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`mixed_1800s_4t`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_4t.tsv`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--timeout`运行截止秒数，超时必须记失败，实际值`1960`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--seconds`有限输入监听秒数，实际值`1800`。 `--stop-mode`排空或取消等待，活动同步SDK不被强行中断，实际值`cancel_pending`。

真实退出记录节选：

```json
{
  "pid": 34293,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 1833.323821127,
  "input_closed_to_exit_seconds": 11.171650347998366,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": true,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "cancel_pending"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/thermal_matrix/mixed_1800s_4t_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=121 completed=121 started=121 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=2277.11 queue_max_ms=279.053 service_sum_ms=1.40214e+06
[PipelineStats] dispatched=121 accepted=121 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=60 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=54394 reused=54392 exhausted=0
[CameraCounters] published=54393 fps=29.997 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 34293, "returncode": 0, "termination_reason": null, "sent_signal": null, "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 1833.323821127, "input_closed_to_exit_seconds": 11.171650347998366, "signal_to_exit_seconds": null, "timing_scope": "child exit/output EOF, excludes subsequent device/finge
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/mixed_1800s_4t
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## thermal_matrix mixed_180s_2t_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --name mixed_180s_2t --tts-threads 2 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_180s_2t.tsv --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --timeout 340 --grace 70 --seconds 180 --stop-mode cancel_pending
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`mixed_180s_2t`。 `--tts-threads`Kokoro线程数，实际值`2`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_180s_2t.tsv`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--timeout`运行截止秒数，超时必须记失败，实际值`340`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--seconds`有限输入监听秒数，实际值`180`。 `--stop-mode`排空或取消等待，活动同步SDK不被强行中断，实际值`cancel_pending`。

真实退出记录节选：

```json
{
  "pid": 32366,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 221.52749982000023,
  "input_closed_to_exit_seconds": 19.741377784001088,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": true,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "cancel_pending"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/thermal_matrix/mixed_180s_2t_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=10 completed=10 started=10 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=1.14062 queue_max_ms=0.30825 service_sum_ms=138970
[PipelineStats] dispatched=10 accepted=10 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=5 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=6042 reused=6040 exhausted=0
[CameraCounters] published=6041 fps=29.9736 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 32366, "returncode": 0, "termination_reason": null, "sent_signal": null, "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 221.52749982000023, "input_closed_to_exit_seconds": 19.741377784001088, "signal_to_exit_seconds": null, "timing_scope": "child exit/output EOF, excludes subsequent device/f
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/mixed_180s_2t
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## thermal_matrix mixed_180s_4t_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --name mixed_180s_4t --tts-threads 4 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_180s_4t.tsv --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --timeout 340 --grace 70 --seconds 180 --stop-mode cancel_pending
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`mixed_180s_4t`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_180s_4t.tsv`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--timeout`运行截止秒数，超时必须记失败，实际值`340`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--seconds`有限输入监听秒数，实际值`180`。 `--stop-mode`排空或取消等待，活动同步SDK不被强行中断，实际值`cancel_pending`。

真实退出记录节选：

```json
{
  "pid": 32558,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 218.62452942800155,
  "input_closed_to_exit_seconds": 16.46599648800111,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": true,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "cancel_pending"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/thermal_matrix/mixed_180s_4t_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=10 completed=10 started=10 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=1.32898 queue_max_ms=0.259145 service_sum_ms=108754
[PipelineStats] dispatched=10 accepted=10 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=5 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=5948 reused=5946 exhausted=0
[CameraCounters] published=5947 fps=29.9741 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 32558, "returncode": 0, "termination_reason": null, "sent_signal": null, "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 218.62452942800155, "input_closed_to_exit_seconds": 16.46599648800111, "signal_to_exit_seconds": null, "timing_scope": "child exit/output EOF, excludes subsequent device/fi
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/mixed_180s_4t
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## gui_microphone_final_v2 command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/rk3576_multimodal_gui --capture plughw:CARD=III,DEV=0 --playback plughw:CARD=III,DEV=0 --report-root /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_microphone_final_v2 --seconds 180 --threads 4 --auto-start --stop-after-answers 2 --cycles 1
```

参数逐项：`--capture`当轮动态发现的HyperX采集设备，实际值`plughw:CARD=III,DEV=0`。 `--playback`当轮动态发现的HyperX播放设备，实际值`plughw:CARD=III,DEV=0`。 `--report-root`已存在的隔离日志根，每次创建UUID子目录，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_microphone_final_v2`。 `--seconds`有限输入监听秒数，实际值`180`。 `--threads`Kokoro线程数，实际值`4`。 `--auto-start`测试时进入事件循环后点击开始。 `--stop-after-answers`测试收到指定成功完成数后停止，0表示不按回答数停止，实际值`2`。 `--cycles`fresh子进程会话轮数，不是在同SDK句柄内重启，实际值`1`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 79.4961776759992,
  "signal_to_exit_seconds": null,
  "sent_signal": null,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "microphone",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_microphone_final_v2/terminal.log`）：

```text
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.166924 queue_max_ms=0.103264 service_sum_ms=2998.84
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.17605 queue_max_ms=0.098023 service_sum_ms=24328.9
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=3 in_use=0 acquired=1689 reused=1686 exhausted=0
[CameraCounters] published=1688 fps=29.9073 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=1 heartbeat=756
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## gui_paired_restart_final_v2 command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/rk3576_multimodal_gui --capture plughw:CARD=III,DEV=0 --playback plughw:CARD=III,DEV=0 --report-root /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_paired_restart_final_v2 --seconds 180 --threads 4 --auto-start --stop-after-answers 2 --cycles 2
```

参数逐项：`--capture`当轮动态发现的HyperX采集设备，实际值`plughw:CARD=III,DEV=0`。 `--playback`当轮动态发现的HyperX播放设备，实际值`plughw:CARD=III,DEV=0`。 `--report-root`已存在的隔离日志根，每次创建UUID子目录，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_paired_restart_final_v2`。 `--seconds`有限输入监听秒数，实际值`180`。 `--threads`Kokoro线程数，实际值`4`。 `--auto-start`测试时进入事件循环后点击开始。 `--stop-after-answers`测试收到指定成功完成数后停止，0表示不按回答数停止，实际值`2`。 `--cycles`fresh子进程会话轮数，不是在同SDK句柄内重启，实际值`2`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 102.26650997400066,
  "signal_to_exit_seconds": null,
  "sent_signal": null,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "paired_restart",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_paired_restart_final_v2/terminal.log`）：

```text
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=661.045 queue_max_ms=660.968 service_sum_ms=3666.03
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12502.3 queue_max_ms=12502.2 service_sum_ms=22752.7
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=850 reused=848 exhausted=0
[CameraCounters] published=849 fps=29.8017 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=2 heartbeat=976
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## gui_sigterm_vision_final_v2 command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/rk3576_multimodal_gui --capture plughw:CARD=III,DEV=0 --playback plughw:CARD=III,DEV=0 --report-root /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_sigterm_vision_final_v2 --seconds 180 --threads 4 --auto-start --stop-after-answers 0 --cycles 1
```

参数逐项：`--capture`当轮动态发现的HyperX采集设备，实际值`plughw:CARD=III,DEV=0`。 `--playback`当轮动态发现的HyperX播放设备，实际值`plughw:CARD=III,DEV=0`。 `--report-root`已存在的隔离日志根，每次创建UUID子目录，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_sigterm_vision_final_v2`。 `--seconds`有限输入监听秒数，实际值`180`。 `--threads`Kokoro线程数，实际值`4`。 `--auto-start`测试时进入事件循环后点击开始。 `--stop-after-answers`测试收到指定成功完成数后停止，0表示不按回答数停止，实际值`0`。 `--cycles`fresh子进程会话轮数，不是在同SDK句柄内重启，实际值`1`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 53.1265482710005,
  "signal_to_exit_seconds": 27.24281331900056,
  "sent_signal": "SIGTERM",
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "sigterm_vision",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_sigterm_vision_final_v2/terminal.log`）：

```text
[QueueStats] stage=inference generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.097333 queue_max_ms=0.097333 service_sum_ms=1945.74
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.078494 queue_max_ms=0.078494 service_sum_ms=24007
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=3 in_use=0 acquired=869 reused=866 exhausted=0
[CameraCounters] published=868 fps=29.8142 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=1 heartbeat=485
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## gui_mixed_1800s_4t_final_v2 command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/rk3576_multimodal_gui --capture plughw:CARD=III,DEV=0 --playback plughw:CARD=III,DEV=0 --report-root /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_mixed_1800s_4t_final_v2 --seconds 1800 --threads 4 --auto-start --stop-after-answers 0 --cycles 1
```

参数逐项：`--capture`当轮动态发现的HyperX采集设备，实际值`plughw:CARD=III,DEV=0`。 `--playback`当轮动态发现的HyperX播放设备，实际值`plughw:CARD=III,DEV=0`。 `--report-root`已存在的隔离日志根，每次创建UUID子目录，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/gui_mixed_1800s_4t_final_v2`。 `--seconds`有限输入监听秒数，实际值`1800`。 `--threads`Kokoro线程数，实际值`4`。 `--auto-start`测试时进入事件循环后点击开始。 `--stop-after-answers`测试收到指定成功完成数后停止，0表示不按回答数停止，实际值`0`。 `--cycles`fresh子进程会话轮数，不是在同SDK句柄内重启，实际值`1`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 1837.7822822689996,
  "signal_to_exit_seconds": null,
  "sent_signal": null,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "stability",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_mixed_1800s_4t_final_v2/terminal.log`）：

```text
[QueueStats] stage=inference generation=1 accepted=121 completed=121 started=121 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=10.3541 queue_max_ms=1.62733 service_sum_ms=144120
[QueueStats] stage=tts generation=1 accepted=121 completed=121 started=121 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=5207.94 queue_max_ms=352.063 service_sum_ms=1.41204e+06
[PipelineStats] dispatched=121 accepted=121 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=60 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=54398 reused=54396 exhausted=0
[CameraCounters] published=54397 fps=29.9952 timeouts=0 driver_sequence_gaps=1 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=1 heartbeat=18340
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix final_burst_audio_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_burst_audio --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix/burst.tsv --signal SIGINT --trigger both_done --delay 0.1
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_burst_audio`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix/burst.tsv`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGINT`。 `--trigger`从真实日志定位发送阶段，实际值`both_done`。 `--delay`触发后等待秒数，实际值`0.1`。

真实退出记录节选：

```json
{
  "returncode": null,
  "runner_returncode": 1,
  "program_started": false,
  "stage": "preflight",
  "input_mode": "NOT_EXECUTED protection refused preexisting seat DRM owners"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix/final_burst_audio_runner.log`）：

```text
Traceback (most recent call last):
  File "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py", line 231, in <module>
    raise SystemExit(main())
                     ^^^^^^
  File "/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py", line 107, in main
    assert pre['clear'],'target device occupied'
AssertionError: target device occupied
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix gui_mixed_1800s_4t_final_v2_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_gui_run.py --name gui_mixed_1800s_4t_final_v2 --build stage5_05_final_v2 --mode stability --seconds 1800 --timeout 1990 --threads 4 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_4t.tsv
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`gui_mixed_1800s_4t_final_v2`。 `--build`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--mode`区分microphone真实输入、paired_restart重启、sigterm_vision推理中退出或stability长测，实际值`stability`。 `--seconds`有限输入监听秒数，实际值`1800`。 `--timeout`运行截止秒数，超时必须记失败，实际值`1990`。 `--threads`Kokoro线程数，实际值`4`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/thermal_matrix/mixed_1800s_4t.tsv`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 1837.7822822689996,
  "signal_to_exit_seconds": null,
  "sent_signal": null,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "stability",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix/gui_mixed_1800s_4t_final_v2_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=121 completed=121 started=121 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=5207.94 queue_max_ms=352.063 service_sum_ms=1.41204e+06
[PipelineStats] dispatched=121 accepted=121 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=60 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=54398 reused=54396 exhausted=0
[CameraCounters] published=54397 fps=29.9952 timeouts=0 driver_sequence_gaps=1 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=1 heartbeat=18340
GUI_RUN_RESULT {"returncode": 0, "duration_seconds": 1837.7822822689996, "signal_to_exit_seconds": null, "sent_signal": null, "termination_reason": null, "forced_kill": false, "timeout": false, "process_gone": true, "devices_released": true, "original_321_unchanged": true, "sessions": [{"answers_completed": 121, "cycles_completed": 1, "heartbeat": 18340, "or
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix gui_paired_restart_final_v2_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_gui_run.py --name gui_paired_restart_final_v2 --build stage5_05_final_v2 --mode paired_restart
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`gui_paired_restart_final_v2`。 `--build`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--mode`区分microphone真实输入、paired_restart重启、sigterm_vision推理中退出或stability长测，实际值`paired_restart`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 102.26650997400066,
  "signal_to_exit_seconds": null,
  "sent_signal": null,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "paired_restart",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix/gui_paired_restart_final_v2_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12502.3 queue_max_ms=12502.2 service_sum_ms=22752.7
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=850 reused=848 exhausted=0
[CameraCounters] published=849 fps=29.8017 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=2 heartbeat=976
GUI_RUN_RESULT {"returncode": 0, "duration_seconds": 102.26650997400066, "signal_to_exit_seconds": null, "sent_signal": null, "termination_reason": null, "forced_kill": false, "timeout": false, "process_gone": true, "devices_released": true, "original_321_unchanged": true, "sessions": [{"answers_completed": 2, "cycles_completed": 1, "heartbeat": 484, "orderl
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix gui_sigterm_vision_final_v2_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_gui_run.py --name gui_sigterm_vision_final_v2 --build stage5_05_final_v2 --mode sigterm_vision --timeout 240
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`gui_sigterm_vision_final_v2`。 `--build`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--mode`区分microphone真实输入、paired_restart重启、sigterm_vision推理中退出或stability长测，实际值`sigterm_vision`。 `--timeout`运行截止秒数，超时必须记失败，实际值`240`。

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 53.1265482710005,
  "signal_to_exit_seconds": 27.24281331900056,
  "sent_signal": "SIGTERM",
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "all_sessions_orderly": true,
  "platform": "xcb DISPLAY :0 actual existing desktop",
  "input_mode": "sigterm_vision",
  "user_audible_confirmation": null
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix/gui_sigterm_vision_final_v2_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.078494 queue_max_ms=0.078494 service_sum_ms=24007
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=3 in_use=0 acquired=869 reused=866 exhausted=0
[CameraCounters] published=868 fps=29.8142 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[GUI finished] code=0 orderly=1 cycles=1 heartbeat=485
GUI_RUN_RESULT {"returncode": 0, "duration_seconds": 53.1265482710005, "signal_to_exit_seconds": 27.24281331900056, "sent_signal": "SIGTERM", "termination_reason": null, "forced_kill": false, "timeout": false, "process_gone": true, "devices_released": true, "original_321_unchanged": true, "sessions": [{"answers_completed": 1, "cycles_completed": 1, "heartbea
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_burst_audio_retry1_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_burst_audio_retry1 --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/burst.tsv --tts-queue-ms 60000 --request-lifetime-ms 180000 --signal SIGINT --trigger both_done --delay 0.1
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_burst_audio_retry1`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/burst.tsv`。 `--tts-queue-ms`TTS最大等待毫秒数，实际值`60000`。 `--request-lifetime-ms`请求绝对寿命毫秒数，实际值`180000`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGINT`。 `--trigger`从真实日志定位发送阶段，实际值`both_done`。 `--delay`触发后等待秒数，实际值`0.1`。

真实退出记录节选：

```json
{
  "pid": 39930,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGINT",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 47.81705280100141,
  "input_closed_to_exit_seconds": 22.62389257000177,
  "signal_to_exit_seconds": 0.9888364610014833,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": true,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_burst_audio_retry1_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12064.2 queue_max_ms=12064.1 service_sum_ms=22460.8
[PipelineStats] dispatched=4 accepted=2 rejected=2 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=833 reused=831 exhausted=0
[CameraCounters] published=832 fps=29.8147 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 39930, "returncode": 0, "termination_reason": null, "sent_signal": "SIGINT", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 47.81705280100141, "input_closed_to_exit_seconds": 22.62389257000177, "signal_to_exit_seconds": 0.9888364610014833, "timing_scope": "child exit/output EOF, excludes sub
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_burst_audio_retry1
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_expiry_audio_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_expiry_audio --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/pair.tsv --tts-queue-ms 1 --signal SIGTERM --trigger ready --delay 25
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_expiry_audio`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/pair.tsv`。 `--tts-queue-ms`TTS最大等待毫秒数，实际值`1`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGTERM`。 `--trigger`从真实日志定位发送阶段，实际值`ready`。 `--delay`触发后等待秒数，实际值`25`。

真实退出记录节选：

```json
{
  "pid": 40011,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 48.21312145699994,
  "input_closed_to_exit_seconds": 1.7845582139998442,
  "signal_to_exit_seconds": 1.8983000090011046,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_expiry_audio_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=1 failed=0 cancelled=0 expired=1 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12435.3 queue_max_ms=12435.2 service_sum_ms=14110.4
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=1
STOPPED
[FramePool] allocated=2 in_use=0 acquired=844 reused=842 exhausted=0
[CameraCounters] published=843 fps=29.8136 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 40011, "returncode": 0, "termination_reason": null, "sent_signal": "SIGTERM", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 48.21312145699994, "input_closed_to_exit_seconds": 1.7845582139998442, "signal_to_exit_seconds": 1.8983000090011046, "timing_scope": "child exit/output EOF, excludes s
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_expiry_audio
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_sigint_asr_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_sigint_asr --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv --signal SIGINT --trigger ready --delay 0.2
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_sigint_asr`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGINT`。 `--trigger`从真实日志定位发送阶段，实际值`ready`。 `--delay`触发后等待秒数，实际值`0.2`。

真实退出记录节选：

```json
{
  "pid": 40441,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGINT",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 38.448516194999684,
  "input_closed_to_exit_seconds": 16.067495203998988,
  "signal_to_exit_seconds": 16.53417446199819,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_sigint_asr_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.092682 queue_max_ms=0.092682 service_sum_ms=13181.3
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=540 reused=538 exhausted=0
[CameraCounters] published=539 fps=29.7063 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 40441, "returncode": 0, "termination_reason": null, "sent_signal": "SIGINT", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 38.448516194999684, "input_closed_to_exit_seconds": 16.067495203998988, "signal_to_exit_seconds": 16.53417446199819, "timing_scope": "child exit/output EOF, excludes su
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_sigint_asr
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_sigint_drain_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_sigint_drain --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv --signal SIGINT --trigger vision --delay 0.1
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_sigint_drain`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGINT`。 `--trigger`从真实日志定位发送阶段，实际值`vision`。 `--delay`触发后等待秒数，实际值`0.1`。

真实退出记录节选：

```json
{
  "pid": 40218,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGINT",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 38.95098321399928,
  "input_closed_to_exit_seconds": 15.998059295998246,
  "signal_to_exit_seconds": 16.129876066999714,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_sigint_drain_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.069346 queue_max_ms=0.069346 service_sum_ms=13283.1
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=542 reused=540 exhausted=0
[CameraCounters] published=541 fps=29.7076 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 40218, "returncode": 0, "termination_reason": null, "sent_signal": "SIGINT", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 38.95098321399928, "input_closed_to_exit_seconds": 15.998059295998246, "signal_to_exit_seconds": 16.129876066999714, "timing_scope": "child exit/output EOF, excludes su
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_sigint_drain
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_sigterm_cancel_waiting_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_sigterm_cancel_waiting --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/pair.tsv --signal SIGTERM --trigger vision --delay 5 --stop-mode cancel_pending
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_sigterm_cancel_waiting`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/pair.tsv`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGTERM`。 `--trigger`从真实日志定位发送阶段，实际值`vision`。 `--delay`触发后等待秒数，实际值`5`。 `--stop-mode`排空或取消等待，活动同步SDK不被强行中断，实际值`cancel_pending`。

真实退出记录节选：

```json
{
  "pid": 40293,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 39.597558984998614,
  "input_closed_to_exit_seconds": 11.768925509997644,
  "signal_to_exit_seconds": 12.02652530100022,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "cancel_pending"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_sigterm_cancel_waiting_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=1 failed=0 cancelled=1 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12414.8 queue_max_ms=12414.7 service_sum_ms=14112.2
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=1 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=566 reused=564 exhausted=0
[CameraCounters] published=565 fps=29.7285 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 40293, "returncode": 0, "termination_reason": null, "sent_signal": "SIGTERM", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 39.597558984998614, "input_closed_to_exit_seconds": 11.768925509997644, "signal_to_exit_seconds": 12.02652530100022, "timing_scope": "child exit/output EOF, excludes s
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_sigterm_cancel_waiting
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_matrix_retry1 final_sigterm_initialization_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_voice_run.py --build-name stage5_05_final_v2 --tts-threads 4 --seconds 120 --timeout 180 --grace 70 --fixed-frame-dir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline --name final_sigterm_initialization --audio-replay-file /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv --signal SIGTERM --trigger init --delay 0.2
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--build-name`指定冻结ARM64构建，实际值`stage5_05_final_v2`。 `--tts-threads`Kokoro线程数，实际值`4`。 `--seconds`有限输入监听秒数，实际值`120`。 `--timeout`运行截止秒数，超时必须记失败，实际值`180`。 `--grace`信号后协作清理宽限秒数，超出强制终止只算失败，实际值`70`。 `--fixed-frame-dir`固定NV12夹具目录，Camera仍真实采集，Frame Age不可用，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline`。 `--name`独占case目录，存在则拒绝覆盖，实际值`final_sigterm_initialization`。 `--audio-replay-file`预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_matrix_retry1/single.tsv`。 `--signal`实际发出的SIGINT或SIGTERM，实际值`SIGTERM`。 `--trigger`从真实日志定位发送阶段，实际值`init`。 `--delay`触发后等待秒数，实际值`0.2`。

真实退出记录节选：

```json
{
  "pid": 40369,
  "returncode": 0,
  "termination_reason": null,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 23.79481105800005,
  "input_closed_to_exit_seconds": 1.6658188299988979,
  "signal_to_exit_seconds": 23.54417397299767,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": false,
  "text_tts_completed": false,
  "vision_tts_completed": false,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_matrix_retry1/final_sigterm_initialization_runner.log`）：

```text
[QueueStats] stage=tts generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[PipelineStats] dispatched=0 accepted=0 rejected=0 inflight=0 peak=0 limit=2 vision_accepted=0 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=92 reused=90 exhausted=0
[CameraCounters] published=91 fps=28.3853 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
STAGE5_05_RUN_RESULT {"pid": 40369, "returncode": 0, "termination_reason": null, "sent_signal": "SIGTERM", "trigger_observed": true, "forced_kill": false, "timeout": false, "duration_seconds": 23.79481105800005, "input_closed_to_exit_seconds": 1.6658188299988979, "signal_to_exit_seconds": 23.54417397299767, "timing_scope": "child exit/output EOF, excludes su
REMOTE_REPORT /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/final_sigterm_initialization
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_camera_followup camera64_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_camera_recheck.py
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。

真实退出记录节选：

```json
{
  "complete": true,
  "steps": [
    {
      "step": "camera64",
      "returncode": 0
    },
    {
      "step": "NPU_inventory",
      "returncode": 0
    },
    {
      "step": "protection_after_camera",
      "returncode": 0
    }
  ],
  "scope": "followup of one Camera driver sequence gap; original gap not rewritten as fixed"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_camera_followup/camera64_runner.log`）：

```text
CAMERA_RECHECK {"returncode": 0, "duration_seconds": 112.84128189699913, "termination_reason": null, "forced_kill": false, "timeout": false, "process_gone": true, "devices_released": true, "original_321_unchanged": true, "samples": 64, "all_VLM_success": true, "input_mode": "LIVE Camera and real VLM only; no ASR, Qwen or TTS; no pixel/semantic ground truth f
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_camera_followup NPU_inventory_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_npu_inventory.py --output /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/npu_desktop_owner_recheck.json
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--output`全新且位于隔离reports下的NPU桌面身份基线JSON，不覆盖旧记录，实际值`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/npu_desktop_owner_recheck.json`。

真实退出记录节选：

```json
{
  "complete": true,
  "steps": [
    {
      "step": "camera64",
      "returncode": 0
    },
    {
      "step": "NPU_inventory",
      "returncode": 0
    },
    {
      "step": "protection_after_camera",
      "returncode": 0
    }
  ],
  "scope": "followup of one Camera driver sequence gap; original gap not rewritten as fixed"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_camera_followup/NPU_inventory_runner.log`）：

```text
DRM_BASELINE_SAVED /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/npu_desktop_owner_recheck.json {"primary_nodes": {"/dev/dri/card1": {"query": {"command": ["sudo", "-n", "--", "/usr/bin/fuser", "-v", "/dev/dri/card1"], "exit_code": 0, "stdout": "     1   932  1619", "stderr": "                     \u7528\u6237     \u8fdb\u
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## final_camera_followup protection_after_camera_command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/usr/bin/python3 -I -B /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_05_protect.py --name protection_final_after_camera
```

参数逐项：`python3 -I -B`隔离用户Python环境并禁止字节码写入。 `--name`独占case目录，存在则拒绝覆盖，实际值`protection_final_after_camera`。

真实退出记录节选：

```json
{
  "complete": true,
  "steps": [
    {
      "step": "camera64",
      "returncode": 0
    },
    {
      "step": "NPU_inventory",
      "returncode": 0
    },
    {
      "step": "protection_after_camera",
      "returncode": 0
    }
  ],
  "scope": "followup of one Camera driver sequence gap; original gap not rewritten as fixed"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/final_camera_followup/protection_after_camera_runner.log`）：

```text
PROTECTION_RESULT {"checks": {"original321_exact": true, "four_accepted_binaries": true, "frozen_sources": true, "devices_clear": true, "disk_above500MiB": true, "no_new_suspicious_kernel_messages": true}, "accepted_binaries": {"build/stage5_01_board/asr_llm_tts_smoke": true, "build/stage5_02_board/asr_llm_tts_smoke": true, "build/stage5_03_board/asr_llm_tts
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## camera_gap_recheck command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/stage5_03_memory_probe /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/camera_gap_recheck 64
```

参数逐项：

真实退出记录节选：

```json
{
  "returncode": 0,
  "duration_seconds": 112.84128189699913,
  "termination_reason": null,
  "forced_kill": false,
  "timeout": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "samples": 64,
  "all_VLM_success": true,
  "input_mode": "LIVE Camera and real VLM only; no ASR, Qwen or TTS; no pixel/semantic ground truth for every frame",
  "scope": "counter and kernel-log recheck, not a claimed fix of the isolated sequence gap"
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/camera_gap_recheck/terminal.log`）：

```text
[MemoryProbe] sample=62 success=1 frame=3234 vlm_ms=1716.63 answer= A computer screen with a blue screen and some text on it. error=
[MemoryProbe] sample=63 success=1 frame=3285 vlm_ms=1702.74 answer= A computer screen with a blue screen and some text on it. error=
[FramePool] allocated=3 in_use=0 acquired=3338 reused=3335 exhausted=0
[CameraCounters] published=3337 fps=29.9528 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
[MemoryProbe] stopped fps=29.9836 frames=3337 timeouts=0
[FramePool] allocated=3 in_use=0 acquired=3338 reused=3335 exhausted=0
[CameraCounters] published=3337 fps=29.9528 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## asr_model_missing command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/does_not_exist_asr /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 2 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数逐项：CLI位置参数1～12依次为采集设备、SenseVoice目录、Silero VAD模型、Qwen RKLLM模型、Kokoro目录、播放设备、有限监听秒数、TTS线程数、sid、SmolVLM2语言模型、RKNN Vision模型、Camera节点。本case故意将一个设备或模型路径改为不存在值，预期返回1并清理，不能当成正常模型请求成功。

真实退出记录节选：

```json
{
  "returncode": 1,
  "expected_nonzero": true,
  "duration_seconds": 0.48137249600040377,
  "termination_reason": null,
  "forced_kill": false,
  "devices_released": true,
  "process_gone": true,
  "scope": "invalid device/model name, not physical disconnection or SDK internal corruption",
  "expected_failure_clean": true
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/real_invalid_paths/asr_model_missing/terminal.log`）：

```text
[Init] Cannot read model file: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/does_not_exist_asr/model.int8.onnx
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## camera_missing command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 2 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/does_not_exist_video
```

参数逐项：CLI位置参数1～12依次为采集设备、SenseVoice目录、Silero VAD模型、Qwen RKLLM模型、Kokoro目录、播放设备、有限监听秒数、TTS线程数、sid、SmolVLM2语言模型、RKNN Vision模型、Camera节点。本case故意将一个设备或模型路径改为不存在值，预期返回1并清理，不能当成正常模型请求成功。

真实退出记录节选：

```json
{
  "returncode": 1,
  "expected_nonzero": true,
  "duration_seconds": 21.548740857000666,
  "termination_reason": null,
  "forced_kill": false,
  "devices_released": true,
  "process_gone": true,
  "scope": "invalid device/model name, not physical disconnection or SDK internal corruption",
  "expected_failure_clean": true
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/real_invalid_paths/camera_missing/terminal.log`）：

```text
[Init] Loading SenseVoice...
[Init] Loading Kokoro...
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
[ALSA config] buffer_frames=12000 period_frames=3000 start_threshold=6000 buffer_ms=500
[Init] Camera failed: Camera initialization failed: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/does_not_exist_video: open /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_05_board/does_not_exist_video: No such file or directory
[FramePool] allocated=0 in_use=0 acquired=0 reused=0 exhausted=0
[CameraCounters] published=0 fps=0 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## microphone_missing command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/asr_llm_tts_smoke stage5_missing_capture /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 2 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数逐项：CLI位置参数1～12依次为采集设备、SenseVoice目录、Silero VAD模型、Qwen RKLLM模型、Kokoro目录、播放设备、有限监听秒数、TTS线程数、sid、SmolVLM2语言模型、RKNN Vision模型、Camera节点。本case故意将一个设备或模型路径改为不存在值，预期返回1并清理，不能当成正常模型请求成功。

真实退出记录节选：

```json
{
  "returncode": 1,
  "expected_nonzero": true,
  "duration_seconds": 23.901485121001315,
  "termination_reason": null,
  "forced_kill": false,
  "devices_released": true,
  "process_gone": true,
  "scope": "invalid device/model name, not physical disconnection or SDK internal corruption",
  "expected_failure_clean": true
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/real_invalid_paths/microphone_missing/terminal.log`）：

```text
[AudioQueueStats] pushed=0 popped=0 dropped=0 rejected_closed=0 peak=0 pending=0
[QueueStats] stage=inference generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[QueueStats] stage=tts generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[PipelineStats] dispatched=0 accepted=0 rejected=0 inflight=0 peak=0 limit=2 vision_accepted=0 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
FAIL
[FramePool] allocated=2 in_use=0 acquired=95 reused=93 exhausted=0
[CameraCounters] published=94 fps=28.4152 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## playback_missing command

目的：在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_05_final_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 stage5_missing_playback 2 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数逐项：CLI位置参数1～12依次为采集设备、SenseVoice目录、Silero VAD模型、Qwen RKLLM模型、Kokoro目录、播放设备、有限监听秒数、TTS线程数、sid、SmolVLM2语言模型、RKNN Vision模型、Camera节点。本case故意将一个设备或模型路径改为不存在值，预期返回1并清理，不能当成正常模型请求成功。

真实退出记录节选：

```json
{
  "returncode": 1,
  "expected_nonzero": true,
  "duration_seconds": 19.738559864999843,
  "termination_reason": null,
  "forced_kill": false,
  "devices_released": true,
  "process_gone": true,
  "scope": "invalid device/model name, not physical disconnection or SDK internal corruption",
  "expected_failure_clean": true
}
```

真实输出节选（完整`reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/real_invalid_paths/playback_missing/terminal.log`）：

```text
I rkllm: Enabled cpus: [4, 5, 6, 7]
I rkllm: Enabled cpus num: 4
[Init] Loading SenseVoice...
[Init] Loading Kokoro...
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
ALSA lib pcm.c:2666:(snd_pcm_open_noupdate) Unknown PCM stage5_missing_playback
[Init] ALSA playback failed: snd_pcm_open: No such file or directory
```

解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。

## 主机收集统计与文档生成

```powershell
python tools/stage5_05_collect.py --complete-only
python tools/stage5_05_analyze.py --collection reports/stage5_05_board/collected_20261018_014600
python tools/stage5_05_stability.py --collection reports/stage5_05_board/collected_20261018_014600
python tools/stage5_05_plots.py
python tools/stage5_05_export.py
python tools/stage5_05_validate.py --collection reports/stage5_05_board/collected_20261018_014600
python tools/stage5_05_manual.py
```

collect只读打包本节完成目录，--complete-only跳过活动case，逐个验证普通文件/安全相对路径和总字节上限，保留SHA。analyze按case+request_id关联steady ns，缺失值为null；stability排除前5分钟并计算RSS趋势和逐条RTF；plots只用真实CSV，不生成假数据。export用真实git diff --no-index --binary，core.autocrlf=false避免换行转换，再在临时树apply后逐文件SHA。validate核对全部证据，不把本地测试替代ARM。manual从最终报告和当前源码抽取完整函数。成功输出和结果分别在collection manifest、analysis、patch_roundtrip、validation_summary及manual_source_manifest。

文档创建使用已解析的Codex bundled Python运行stage5_05_build_docx.py，字体为楷体/Times New Roman 12pt、1.5倍行距、两字符缩进，代码等宽。packaged renderer因缺少LibreOffice失败的日志保留；原生Word只打开本次文档、更新目录并导出PDF，然后复用packaged rasterizer生成PNG。仅关闭本任务新建且无其他文档的Word实例，不结束用户Word。每页视觉核对与代码逐行回读在document_build、render结果与document_QA保存，不能只靠XML检查声称排版成功。
