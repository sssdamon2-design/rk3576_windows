# 5.4 命令、逐项参数及真实输出

全部操作仅cat用户和已授权隔离目录；`sudo -n fuser -v`仅查询，不含-k。复现必须选新case名和不存在的源码/构建目录，不覆盖冻结证据。以下argv来自实际command.json，shell形式用shlex.join转义；运行前使用`set -a; source "$REVIEW/tools/stage5_board_paths.sh"`导出原SDK/模型路径，环境快照在对应case/environment.json。source只改变本次shell，不编辑系统文件。

## 操作 baseline_asr_30/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2/stage5_04_asr_bench /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/test_wavs/zh.wav /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/baseline_asr_30 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 69.57738432000042,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1974579200
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_asr_30/terminal.log)）：

```text
[ASRBench] sample=0 ms=1961.19 text=开饭时间早上九点至下午五点
[ASRBench] sample=1 ms=1984.06 text=开饭时间早上九点至下午五点
[ASRBench] sample=2 ms=1987.9 text=开饭时间早上九点至下午五点
[ASRBench] sample=3 ms=1987.42 text=开饭时间早上九点至下午五点
[ASRBench] sample=4 ms=1987.93 text=开饭时间早上九点至下午五点
[此处省略，完整原始文件见链接]
[ASRBench] sample=24 ms=1987.64 text=开饭时间早上九点至下午五点
[ASRBench] sample=25 ms=1989.57 text=开饭时间早上九点至下午五点
[ASRBench] sample=26 ms=1988.47 text=开饭时间早上九点至下午五点
[ASRBench] sample=27 ms=1987.51 text=开饭时间早上九点至下午五点
[ASRBench] sample=28 ms=1987.53 text=开饭时间早上九点至下午五点
[ASRBench] sample=29 ms=1986.33 text=开饭时间早上九点至下午五点
[ASRBench] sample=30 ms=1986.39 text=开饭时间早上九点至下午五点
[ASRBench] sample=31 ms=1985.69 text=开饭时间早上九点至下午五点
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_asr_30/stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build/build

目的：独立ARM64配置/构建/确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline --parallel 3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 98.04480878399954
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/build.stdout.log)）：

```text
[  1%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_capture.cpp.o
[  3%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/latest_frame_buffer.cpp.o
[  3%] Building CXX object CMakeFiles/asr_pipeline_tests.dir/tests/asr_pipeline_tests.cpp.o
[  4%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_preprocessor.cpp.o
[  5%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/image_preprocessor.cpp.o
[此处省略，完整原始文件见链接]
[ 95%] Building CXX object CMakeFiles/asr_route_smoke.dir/src/audio/asr_route_smoke.cpp.o
[ 96%] Building CXX object CMakeFiles/rk3576_multimodal.dir/src/app/cli.cpp.o
[ 97%] Linking CXX executable asr_route_smoke
[ 98%] Linking CXX executable rk3576_multimodal
[ 98%] Built target asr_route_smoke
[ 98%] Built target rk3576_multimodal
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/build.stderr.log)）：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source/src/ai/rk_backends_unavailable.cpp:21:17: warning: ‘InferenceResult {anonymous}::unavailable(const char*)’ defined but not used [-Wunused-function]
   21 | InferenceResult unavailable(const char* message)
      |                 ^~~~~~~~~~~
In file included from /usr/include/rga/im2d.h:24,
                 from /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source/tests/stage5_03_rga_probe.cpp:3:
/usr/include/rga/im2d_type.h:355:16: warning: ISO C++ prohibits anonymous structs [-Wpedantic]
  355 |         struct {
      |                ^
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build/configure

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 2.001716832000966
}
```

真实stdout节选（完整[configure.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/configure.stdout.log)）：

```text
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
[此处省略，完整原始文件见链接]
-- RKLLM SDK library available
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline
```

真实stderr节选（完整[configure.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/configure.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build/ctest

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/baseline_build/ctest.xml
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 2.0022357890011335
}
```

真实stdout节选（完整[ctest.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/ctest.stdout.log)）：

```text
Internal ctest changing into directory: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline
Test project /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline
    Start 1: request_profile_tests
1/7 Test #1: request_profile_tests ............   Passed    0.01 sec
    Start 2: image_pipeline_tests
[此处省略，完整原始文件见链接]
    Start 6: llm_worker_tests
6/7 Test #6: llm_worker_tests .................   Passed    0.01 sec
    Start 7: camera_service_tests
7/7 Test #7: camera_service_tests .............   Passed    0.22 sec

100% tests passed, 0 tests failed out of 7

Total Test time (real) =   0.91 sec
```

真实stderr节选（完整[ctest.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build/ctest.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build_v2/build

目的：独立ARM64配置/构建/确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2 --parallel 3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 115.05668157199943
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/build.stdout.log)）：

```text
[  1%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/latest_frame_buffer.cpp.o
[  2%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_capture.cpp.o
[  3%] Building CXX object CMakeFiles/asr_pipeline_tests.dir/tests/asr_pipeline_tests.cpp.o
[  4%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_preprocessor.cpp.o
[  5%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/image_preprocessor.cpp.o
[此处省略，完整原始文件见链接]
[ 95%] Built target rk3576_multimodal
[ 96%] Building CXX object CMakeFiles/stage5_02_npu_probe.dir/tests/stage5_02_npu_probe.cpp.o
[ 97%] Linking CXX executable stage5_02_npu_probe
[ 97%] Built target stage5_02_npu_probe
[ 98%] Linking CXX executable stage5_03_memory_probe
[ 98%] Built target stage5_03_memory_probe
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/build.stderr.log)）：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source_v2/src/ai/rk_backends_unavailable.cpp:21:17: warning: ‘InferenceResult {anonymous}::unavailable(const char*)’ defined but not used [-Wunused-function]
   21 | InferenceResult unavailable(const char* message)
      |                 ^~~~~~~~~~~
In file included from /usr/include/rga/im2d.h:24,
                 from /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source_v2/tests/stage5_03_rga_probe.cpp:3:
/usr/include/rga/im2d_type.h:355:16: warning: ISO C++ prohibits anonymous structs [-Wpedantic]
  355 |         struct {
      |                ^
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build_v2/configure

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_baseline_source_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 2.0014260560001276
}
```

真实stdout节选（完整[configure.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/configure.stdout.log)）：

```text
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
[此处省略，完整原始文件见链接]
-- RKLLM SDK library available
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2
```

真实stderr节选（完整[configure.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/configure.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_build_v2/ctest

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/baseline_build_v2/ctest.xml
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 2.002897179001593
}
```

真实stdout节选（完整[ctest.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/ctest.stdout.log)）：

```text
Internal ctest changing into directory: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2
Test project /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2
    Start 1: request_profile_tests
1/7 Test #1: request_profile_tests ............   Passed    0.01 sec
    Start 2: image_pipeline_tests
[此处省略，完整原始文件见链接]
    Start 6: llm_worker_tests
6/7 Test #6: llm_worker_tests .................   Passed    0.01 sec
    Start 7: camera_service_tests
7/7 Test #7: camera_service_tests .............   Passed    0.22 sec

100% tests passed, 0 tests failed out of 7

Total Test time (real) =   0.91 sec
```

真实stderr节选（完整[ctest.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_build_v2/ctest.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_pipeline_pairs_2t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 2 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 27609,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 130.982279464999,
  "input_closed_to_exit_seconds": 29.880976672000543,
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
  "variant": "baseline",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_pipeline_pairs_2t/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 3/3/0
[AudioQueueStats] pushed=6 popped=6 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=6 completed=6 started=6 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=1707.57 queue_max_ms=752.681 service_sum_ms=8445.13
[QueueStats] stage=tts generation=1 accepted=6 completed=6 started=6 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=49635 queue_max_ms=16622.8 service_sum_ms=85230.9
[PipelineStats] dispatched=6 accepted=6 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=3 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=3381 reused=3379 exhausted=0
[CameraCounters] published=3380 fps=29.9535 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_tts_ort_detail/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2/stage5_04_tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/baseline_tts_ort_detail 2 1
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 93.12210873000004,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1928675328
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_tts_ort_detail/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=7626.07 threads=2 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=10050 wall_ms=10050.1 audio_seconds=1.958 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=17984.7 wall_ms=17984.9 audio_seconds=4.11417 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=9907.67 wall_ms=9907.77 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=1 language=en phase=warmup synth_ms=18087 wall_ms=18087.2 audio_seconds=4.11404 nonfinite=0
[TTSBench] iteration=2 language=zh phase=measured synth_ms=9859.08 wall_ms=9859.14 audio_seconds=1.958 nonfinite=0
[TTSBench] iteration=2 language=en phase=measured synth_ms=18148.3 wall_ms=18148.4 audio_seconds=4.11421 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_tts_ort_detail/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_vision_30/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2/stage5_04_vision_bench /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/baseline_vision_30 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 60.174319441999614,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1944166400
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_vision_30/terminal.log)）：

```text
[VisionTensor] input_type=1 input_fmt=1 input_elems=786432 input_w_stride=512 input_size=1572864 input_size_with_stride=1572864 output_elems=36864 output_type=1 input_dims=1,512,512,3, output_dims=1,64,576,
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm
I rkllm: rkllm-toolkit version: 1.3.1, max_context_limit: 2048, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
[VisionBench] sample=24 fixture=0 success=1 ms=1657.82 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=25 fixture=1 success=1 ms=1728.84 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=26 fixture=2 success=1 ms=1878.87 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=27 fixture=0 success=1 ms=1740.9 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=28 fixture=1 success=1 ms=1843.5 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=29 fixture=2 success=1 ms=1794.82 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=30 fixture=0 success=1 ms=1717.08 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=31 fixture=1 success=1 ms=1753.21 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_vision_30/stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 baseline_voice_2t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_baseline_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 2 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 24979,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 143.16462742899967,
  "input_closed_to_exit_seconds": 3.901897056999587,
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
  "variant": "baseline",
  "input_mode": "real_microphone_ASR",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/baseline_voice_2t/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=7 popped=7 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=5 completed=5 started=5 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.233686 queue_max_ms=0.09604 service_sum_ms=7076.09
[QueueStats] stage=tts generation=1 accepted=5 completed=5 started=5 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=22951.2 queue_max_ms=11765.6 service_sum_ms=84232.4
[PipelineStats] dispatched=7 accepted=5 rejected=2 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=3 in_use=0 acquired=3744 reused=3741 exhausted=0
[CameraCounters] published=3743 fps=29.9587 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_asr_30/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/stage5_04_asr_bench /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/test_wavs/zh.wav /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_asr_30 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 69.7539006099978,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1924702208
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_asr_30/terminal.log)）：

```text
[ASRBench] sample=0 ms=1965.02 text=开饭时间早上九点至下午五点
[ASRBench] sample=1 ms=1994.72 text=开饭时间早上九点至下午五点
[ASRBench] sample=2 ms=1994.78 text=开饭时间早上九点至下午五点
[ASRBench] sample=3 ms=1994.37 text=开饭时间早上九点至下午五点
[ASRBench] sample=4 ms=1992.21 text=开饭时间早上九点至下午五点
[此处省略，完整原始文件见链接]
[ASRBench] sample=24 ms=2086.83 text=开饭时间早上九点至下午五点
[ASRBench] sample=25 ms=2084.45 text=开饭时间早上九点至下午五点
[ASRBench] sample=26 ms=2029.31 text=开饭时间早上九点至下午五点
[ASRBench] sample=27 ms=1993.18 text=开饭时间早上九点至下午五点
[ASRBench] sample=28 ms=1992.23 text=开饭时间早上九点至下午五点
[ASRBench] sample=29 ms=1993.21 text=开饭时间早上九点至下午五点
[ASRBench] sample=30 ms=1994.8 text=开饭时间早上九点至下午五点
[ASRBench] sample=31 ms=1992.47 text=开饭时间早上九点至下午五点
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_asr_30/stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build/build

目的：独立ARM64配置/构建/确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board --parallel 3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 111.05653243300003
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/build.stdout.log)）：

```text
[  1%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_capture.cpp.o
[  2%] Building CXX object CMakeFiles/asr_pipeline_tests.dir/tests/asr_pipeline_tests.cpp.o
[  3%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/latest_frame_buffer.cpp.o
[  4%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_preprocessor.cpp.o
[  5%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/image_preprocessor.cpp.o
[此处省略，完整原始文件见链接]
[ 95%] Built target rk3576_multimodal
[ 96%] Building CXX object CMakeFiles/stage5_02_npu_probe.dir/tests/stage5_02_npu_probe.cpp.o
[ 97%] Linking CXX executable asr_llm_tts_smoke
[ 97%] Built target asr_llm_tts_smoke
[ 98%] Linking CXX executable stage5_02_npu_probe
[ 98%] Built target stage5_02_npu_probe
[100%] Linking CXX executable stage5_03_memory_probe
[100%] Built target stage5_03_memory_probe
```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/build.stderr.log)）：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source/src/ai/rk_backends_unavailable.cpp:21:17: warning: ‘InferenceResult {anonymous}::unavailable(const char*)’ defined but not used [-Wunused-function]
   21 | InferenceResult unavailable(const char* message)
      |                 ^~~~~~~~~~~
In file included from /usr/include/rga/im2d.h:24,
                 from /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source/tests/stage5_03_rga_probe.cpp:3:
/usr/include/rga/im2d_type.h:355:16: warning: ISO C++ prohibits anonymous structs [-Wpedantic]
  355 |         struct {
      |                ^
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build/configure

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 2.001456617999793
}
```

真实stdout节选（完整[configure.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/configure.stdout.log)）：

```text
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
[此处省略，完整原始文件见链接]
-- RKLLM SDK library available
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board
```

真实stderr节选（完整[configure.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/configure.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build/ctest

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_build/ctest.xml
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 2.002221003000159
}
```

真实stdout节选（完整[ctest.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/ctest.stdout.log)）：

```text
Internal ctest changing into directory: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board
Test project /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board
    Start 1: request_profile_tests
1/7 Test #1: request_profile_tests ............   Passed    0.01 sec
    Start 2: image_pipeline_tests
[此处省略，完整原始文件见链接]
    Start 6: llm_worker_tests
6/7 Test #6: llm_worker_tests .................   Passed    0.01 sec
    Start 7: camera_service_tests
7/7 Test #7: camera_service_tests .............   Passed    0.22 sec

100% tests passed, 0 tests failed out of 7

Total Test time (real) =   0.93 sec
```

真实stderr节选（完整[ctest.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build/ctest.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v2/build

目的：独立ARM64配置/构建/确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2 --parallel 3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 122.05690272399988
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/build.stdout.log)）：

```text
[  2%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_capture.cpp.o
[  2%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/latest_frame_buffer.cpp.o
[  3%] Building CXX object CMakeFiles/asr_pipeline_tests.dir/tests/asr_pipeline_tests.cpp.o
[  4%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_preprocessor.cpp.o
[  5%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/image_preprocessor.cpp.o
[此处省略，完整原始文件见链接]
[ 95%] Built target rk3576_multimodal
[ 96%] Building CXX object CMakeFiles/stage5_02_npu_probe.dir/tests/stage5_02_npu_probe.cpp.o
[ 97%] Linking CXX executable stage5_02_npu_probe
[ 97%] Built target stage5_02_npu_probe
[ 98%] Linking CXX executable stage5_03_memory_probe
[ 98%] Built target stage5_03_memory_probe
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/build.stderr.log)）：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2/src/ai/rk_backends_unavailable.cpp:21:17: warning: ‘InferenceResult {anonymous}::unavailable(const char*)’ defined but not used [-Wunused-function]
   21 | InferenceResult unavailable(const char* message)
      |                 ^~~~~~~~~~~
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2/tests/request_profile_tests.cpp: In function ‘void {anonymous}::fixtureChecks(const std::filesystem::__cxx11::path&)’:
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2/tests/request_profile_tests.cpp:25:5: warning: this ‘for’ clause does not guard... [-Wmisleading-indentation]
[此处省略，完整原始文件见链接]
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2/tests/request_profile_tests.cpp:25:107: note: ...this statement, but the latter is misleadingly indented as if it were guarded by the ‘for’
   25 |     for(const auto& file:std::filesystem::directory_iterator(folder))std::filesystem::remove(file.path());std::filesystem::remove(folder);
      |                                                                                                           ^~~
In file included from /usr/include/rga/im2d.h:24,
                 from /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2/tests/stage5_03_rga_probe.cpp:3:
/usr/include/rga/im2d_type.h:355:16: warning: ISO C++ prohibits anonymous structs [-Wpedantic]
  355 |         struct {
      |                ^
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v2/configure

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 2.0024137450000126
}
```

真实stdout节选（完整[configure.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/configure.stdout.log)）：

```text
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
[此处省略，完整原始文件见链接]
-- RKLLM SDK library available
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2
```

真实stderr节选（完整[configure.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/configure.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v2/ctest

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_build_v2/ctest.xml
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 2.002436327999021
}
```

真实stdout节选（完整[ctest.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/ctest.stdout.log)）：

```text
Internal ctest changing into directory: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2
Test project /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2
    Start 1: request_profile_tests
1/7 Test #1: request_profile_tests ............   Passed    0.01 sec
    Start 2: image_pipeline_tests
[此处省略，完整原始文件见链接]
    Start 6: llm_worker_tests
6/7 Test #6: llm_worker_tests .................   Passed    0.01 sec
    Start 7: camera_service_tests
7/7 Test #7: camera_service_tests .............   Passed    0.22 sec

100% tests passed, 0 tests failed out of 7

Total Test time (real) =   0.90 sec
```

真实stderr节选（完整[ctest.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v2/ctest.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v3/build

目的：独立ARM64配置/构建/确定性测试。

```bash
cmake --build /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3 --parallel 3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "build",
  "returncode": 0,
  "reason": null,
  "seconds": 124.05940258299961
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/build.stdout.log)）：

```text
[  1%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_capture.cpp.o
[  3%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/latest_frame_buffer.cpp.o
[  3%] Building CXX object CMakeFiles/asr_pipeline_tests.dir/tests/asr_pipeline_tests.cpp.o
[  4%] Building CXX object CMakeFiles/multimodal_audio.dir/src/audio/audio_preprocessor.cpp.o
[  5%] Building CXX object CMakeFiles/multimodal_core.dir/src/video/image_preprocessor.cpp.o
[此处省略，完整原始文件见链接]
[ 95%] Built target rk3576_multimodal
[ 96%] Building CXX object CMakeFiles/stage5_02_npu_probe.dir/tests/stage5_02_npu_probe.cpp.o
[ 97%] Linking CXX executable stage5_02_npu_probe
[ 97%] Built target stage5_02_npu_probe
[ 98%] Linking CXX executable stage5_03_memory_probe
[ 98%] Built target stage5_03_memory_probe
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/build.stderr.log)）：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3/src/ai/rk_backends_unavailable.cpp:21:17: warning: ‘InferenceResult {anonymous}::unavailable(const char*)’ defined but not used [-Wunused-function]
   21 | InferenceResult unavailable(const char* message)
      |                 ^~~~~~~~~~~
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3/tests/request_profile_tests.cpp: In function ‘void {anonymous}::fixtureChecks(const std::filesystem::__cxx11::path&)’:
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3/tests/request_profile_tests.cpp:25:5: warning: this ‘for’ clause does not guard... [-Wmisleading-indentation]
[此处省略，完整原始文件见链接]
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3/tests/request_profile_tests.cpp:25:107: note: ...this statement, but the latter is misleadingly indented as if it were guarded by the ‘for’
   25 |     for(const auto& file:std::filesystem::directory_iterator(folder))std::filesystem::remove(file.path());std::filesystem::remove(folder);
      |                                                                                                           ^~~
In file included from /usr/include/rga/im2d.h:24,
                 from /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3/tests/stage5_03_rga_probe.cpp:3:
/usr/include/rga/im2d_type.h:355:16: warning: ISO C++ prohibits anonymous structs [-Wpedantic]
  355 |         struct {
      |                ^
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v3/configure

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec cmake -S "$2" -B "$3" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/stage5_04_source_v3 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "configure",
  "returncode": 0,
  "reason": null,
  "seconds": 3.00206210900069
}
```

真实stdout节选（完整[configure.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/configure.stdout.log)）：

```text
-- The CXX compiler identification is GNU 12.2.0
-- Detecting CXX compiler ABI info
-- Detecting CXX compiler ABI info - done
-- Check for working CXX compiler: /usr/bin/c++ - skipped
-- Detecting CXX compile features
[此处省略，完整原始文件见链接]
-- RKLLM SDK library available
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Real SmolVLM2 RKNN + RKLLM backend enabled
-- Found ALSA: /usr/lib/aarch64-linux-gnu/libasound.so (found version "1.2.8") 
-- Configuring done
-- Generating done
-- Build files have been written to: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3
```

真实stderr节选（完整[configure.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/configure.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_build_v3/ctest

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec ctest --test-dir "$2" --output-on-failure --timeout 30 --output-junit "$3"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_build_v3/ctest.xml
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "step": "ctest",
  "returncode": 0,
  "reason": null,
  "seconds": 2.002280110002175
}
```

真实stdout节选（完整[ctest.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/ctest.stdout.log)）：

```text
Internal ctest changing into directory: /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3
Test project /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3
    Start 1: request_profile_tests
1/7 Test #1: request_profile_tests ............   Passed    0.01 sec
    Start 2: image_pipeline_tests
[此处省略，完整原始文件见链接]
    Start 6: llm_worker_tests
6/7 Test #6: llm_worker_tests .................   Passed    0.01 sec
    Start 7: camera_service_tests
7/7 Test #7: camera_service_tests .............   Passed    0.22 sec

100% tests passed, 0 tests failed out of 7

Total Test time (real) =   0.91 sec
```

真实stderr节选（完整[ctest.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_build_v3/ctest.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_burst_audio/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 27731,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 52.626239409000846,
  "input_closed_to_exit_seconds": 27.986260443998617,
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
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_burst_audio/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=4 popped=4 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=4043.32 queue_max_ms=4043.23 service_sum_ms=11992.5
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=9433.84 queue_max_ms=9433.75 service_sum_ms=24931.5
[PipelineStats] dispatched=4 accepted=2 rejected=2 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=993 reused=991 exhausted=0
[CameraCounters] published=992 fps=29.8434 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_default_queue_audio/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 29641,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 38.80303973499758,
  "input_closed_to_exit_seconds": 15.91741647299932,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_default_queue_audio/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=2 popped=2 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=741.248 queue_max_ms=741.173 service_sum_ms=3507.55
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=1 failed=0 cancelled=0 expired=1 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12520.9 queue_max_ms=12520.8 service_sum_ms=14179.3
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=1
PASS
[FramePool] allocated=2 in_use=0 acquired=561 reused=559 exhausted=0
[CameraCounters] published=560 fps=29.7213 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_expiry_audio/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 27920,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 40.12501881699791,
  "input_closed_to_exit_seconds": 16.536609246999433,
  "signal_to_exit_seconds": null,
  "timing_scope": "child exit/output EOF, excludes subsequent device/fingerprint queries",
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "image_profile_errors": false,
  "shutdown_complete_marker": true,
  "program_PASS": true,
  "text_tts_completed": false,
  "vision_tts_completed": true,
  "user_audible_confirmation": null,
  "variant": "candidate",
  "input_mode": "fixed_audio_REAL_ASR_no_microphone_VAD",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_expiry_audio/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=2 popped=2 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=684.149 queue_max_ms=684.068 service_sum_ms=3501.46
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=1 failed=0 cancelled=0 expired=1 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=13110.7 queue_max_ms=13110.6 service_sum_ms=14811.2
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=1
PASS
[FramePool] allocated=2 in_use=0 acquired=590 reused=588 exhausted=0
[CameraCounters] published=589 fps=29.7299 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_final_sigterm_drain/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 29584,
  "returncode": 0,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 37.23214941799961,
  "input_closed_to_exit_seconds": 16.05906800199955,
  "signal_to_exit_seconds": 16.22492846199748,
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

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_final_sigterm_drain/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=1 popped=1 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.09316 queue_max_ms=0.09316 service_sum_ms=1760.86
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.090997 queue_max_ms=0.090997 service_sum_ms=13387.6
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=540 reused=538 exhausted=0
[CameraCounters] published=539 fps=29.7086 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_pipeline_pairs_4t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 27671,
  "returncode": 0,
  "sent_signal": null,
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 127.46573636999892,
  "input_closed_to_exit_seconds": 24.58669599299901,
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
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_pipeline_pairs_4t/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 3/3/0
[AudioQueueStats] pushed=6 popped=6 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=6 completed=6 started=6 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=1557.8 queue_max_ms=653.118 service_sum_ms=9136.21
[QueueStats] stage=tts generation=1 accepted=6 completed=6 started=6 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=39326 queue_max_ms=13268 service_sum_ms=69501.3
[PipelineStats] dispatched=6 accepted=6 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=3 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
PASS
[FramePool] allocated=2 in_use=0 acquired=3222 reused=3220 exhausted=0
[CameraCounters] published=3221 fps=29.9508 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_sigint_drain/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 27979,
  "returncode": 0,
  "sent_signal": "SIGINT",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 38.12054239999998,
  "input_closed_to_exit_seconds": 16.634520070998406,
  "signal_to_exit_seconds": 17.141003931999876,
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

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_sigint_drain/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=1 popped=1 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.098179 queue_max_ms=0.098179 service_sum_ms=1776.21
[QueueStats] stage=tts generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.082823 queue_max_ms=0.082823 service_sum_ms=13732.2
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=555 reused=553 exhausted=0
[CameraCounters] published=554 fps=29.7257 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_sigterm_cancel_tts/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 28038,
  "returncode": 0,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 39.03016719599691,
  "input_closed_to_exit_seconds": 16.496753935000015,
  "signal_to_exit_seconds": 12.712056828997447,
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

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_sigterm_cancel_tts/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=2 popped=2 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=682.704 queue_max_ms=682.633 service_sum_ms=3612.95
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=1 failed=0 cancelled=1 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=12958.3 queue_max_ms=12958.2 service_sum_ms=14778.6
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=2 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=1 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=587 reused=585 exhausted=0
[CameraCounters] published=586 fps=29.7317 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_sigterm_cancel_waiting/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 28097,
  "returncode": 0,
  "sent_signal": "SIGTERM",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 24.965682723999635,
  "input_closed_to_exit_seconds": 3.291977782999311,
  "signal_to_exit_seconds": 3.4163192809974134,
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
  "stop_mode": "cancel_pending"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_sigterm_cancel_waiting/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=1 popped=1 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=1 completed=1 started=1 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.073589 queue_max_ms=0.073589 service_sum_ms=1786.02
[QueueStats] stage=tts generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[PipelineStats] dispatched=1 accepted=1 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=1 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=2 in_use=0 acquired=159 reused=157 exhausted=0
[CameraCounters] published=158 fps=29.0352 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_tts_profile_4t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/stage5_04_tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_tts_profile_4t 4 3
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 104.15424659800192,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1893031936
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_tts_profile_4t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=5907.12 threads=4 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=6618.54 wall_ms=6618.61 audio_seconds=1.94637 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=12201.5 wall_ms=12201.6 audio_seconds=4.11525 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=6813.56 wall_ms=6813.66 audio_seconds=1.9475 nonfinite=0
[TTSBench] iteration=1 language=en phase=warmup synth_ms=12503.4 wall_ms=12503.5 audio_seconds=4.11129 nonfinite=0
[TTSBench] iteration=2 language=zh phase=measured synth_ms=6891.87 wall_ms=6891.94 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=2 language=en phase=measured synth_ms=12670.5 wall_ms=12670.6 audio_seconds=4.11421 nonfinite=0
[TTSBench] iteration=3 language=zh phase=measured synth_ms=7047.41 wall_ms=7047.48 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=3 language=en phase=measured synth_ms=12774.1 wall_ms=12774.2 audio_seconds=4.11342 nonfinite=0
[TTSBench] iteration=4 language=zh phase=measured synth_ms=7140.58 wall_ms=7140.65 audio_seconds=1.95013 nonfinite=0
[TTSBench] iteration=4 language=en phase=measured synth_ms=12827.7 wall_ms=12827.8 audio_seconds=4.11621 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_tts_profile_4t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_vision_30/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v2/stage5_04_vision_bench /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_03_board/raw_5_2_baseline /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/candidate_vision_30 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 60.06542742000238,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1894289408
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_vision_30/terminal.log)）：

```text
[VisionTensor] input_type=1 input_fmt=1 input_elems=786432 input_w_stride=512 input_size=1572864 input_size_with_stride=1572864 output_elems=36864 output_type=1 input_dims=1,512,512,3, output_dims=1,64,576,
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm
I rkllm: rkllm-toolkit version: 1.3.1, max_context_limit: 2048, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
[VisionBench] sample=24 fixture=0 success=1 ms=1630.68 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=25 fixture=1 success=1 ms=1767.57 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=26 fixture=2 success=1 ms=1798.97 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=27 fixture=0 success=1 ms=1605.21 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=28 fixture=1 success=1 ms=2087.37 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=29 fixture=2 success=1 ms=1752.34 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
[VisionBench] sample=30 fixture=0 success=1 ms=1621.87 answer= A computer monitor with a blue screen and some text on it.
[VisionBench] sample=31 fixture=1 success=1 ms=1785.57 answer= A computer monitor with a blue screen, and a black stand holding it up to the camera.
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_vision_30/stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_voice_4t_final/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 29394,
  "returncode": 1,
  "sent_signal": null,
  "trigger_observed": false,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 143.2196699729975,
  "input_closed_to_exit_seconds": 1.7274548940004024,
  "signal_to_exit_seconds": null,
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
  "input_mode": "real_microphone_ASR",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_voice_4t_final/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 0/0/0
[AudioQueueStats] pushed=0 popped=0 dropped=0 rejected_closed=0 peak=0 pending=0
[QueueStats] stage=inference generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[QueueStats] stage=tts generation=1 accepted=0 completed=0 started=0 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=0 pending=0 active=0 callback_errors=0 queue_sum_ms=0 queue_max_ms=0 service_sum_ms=0
[PipelineStats] dispatched=0 accepted=0 rejected=0 inflight=0 peak=0 limit=2 vision_accepted=0 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
FAIL
[FramePool] allocated=2 in_use=0 acquired=3696 reused=3694 exhausted=0
[CameraCounters] published=3695 fps=29.9579 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 candidate_voice_4t_final_retry1/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
stdbuf -oL -eL /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/build/stage5_04_board_v3/asr_llm_tts_smoke plughw:CARD=III,DEV=0 /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17 /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 plughw:CARD=III,DEV=0 120 4 17 /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm /home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn /dev/video11
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "pid": 30229,
  "returncode": 0,
  "sent_signal": "SIGINT",
  "trigger_observed": true,
  "forced_kill": false,
  "timeout": false,
  "duration_seconds": 90.74691659900054,
  "input_closed_to_exit_seconds": 1.7606734760011022,
  "signal_to_exit_seconds": 1.9651587600019411,
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
  "input_mode": "real_microphone_ASR",
  "stop_mode": "drain"
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/candidate_voice_4t_final_retry1/terminal.log)）：

```text
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
[此处省略，完整原始文件见链接]
VISION completed/success/failed: 1/1/0
[AudioQueueStats] pushed=2 popped=2 dropped=0 rejected_closed=0 peak=1 pending=0
[QueueStats] stage=inference generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.115197 queue_max_ms=0.08329 service_sum_ms=2985.96
[QueueStats] stage=tts generation=1 accepted=2 completed=2 started=2 failed=0 cancelled=0 expired=0 rejected_full=0 rejected_stopped=0 peak=1 pending=0 active=0 callback_errors=0 queue_sum_ms=0.29903 queue_max_ms=0.275741 service_sum_ms=25044.9
[PipelineStats] dispatched=2 accepted=2 rejected=0 inflight=0 peak=1 limit=2 vision_accepted=1 vision_rejected=0 llm_cancelled=0 llm_expired=0 vision_cancelled=0 vision_expired=0 cancelled_before_submit=0 downstream_cancelled=0 tts_cancelled=0 tts_expired=0
STOPPED
[FramePool] allocated=3 in_use=0 acquired=2113 reused=2110 exhausted=0
[CameraCounters] published=2112 fps=29.9249 timeouts=0 driver_sequence_gaps=0 pool_discarded=0
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 profile_tool_setup/build

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -I"$1/stage5_04_baseline_source/include" "$2/vision_bench.cpp" "$1/build/stage5_04_baseline/libmultimodal_core.a" "$STAGE5_RKNN_LIBRARY" "$STAGE5_RKLLM_LIB/librkllmrt.so" -pthread -o "$2/vision_bench"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/profile_tool_setup
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "diagnostic_links_frozen_instrumented_baseline": true
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/profile_tool_setup/build.stdout.log)）：

```text

```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/profile_tool_setup/build.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_baseline_build/build

目的：独立ARM64配置/构建/确定性测试。

```bash
bash -c 'source "$1/tools/stage5_board_paths.sh"; exec g++ -std=c++17 -O3 -Wall -Wextra -Wpedantic -I"$1/reports/stage5_04_board/baseline_5_3_source/include" -I"$STAGE5_SHERPA/include" "$2/tts_bench.cpp" "$1/build/stage5_03_board/libmultimodal_tts.a" -L"$STAGE5_SHERPA/lib" -lsherpa-onnx-c-api -lasound -pthread -Wl,-rpath,"$STAGE5_SHERPA/lib" -o "$2/tts_bench"' stage5_04 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build
```

参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "links_unchanged_5_3_tts_library": true
}
```

真实stdout节选（完整[build.stdout.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_baseline_build/build.stdout.log)）：

```text

```

真实stderr节选（完整[build.stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_baseline_build/build.stderr.log)）：

```text

```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_tts_baseline_2t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build/tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_baseline_2t 2 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 893.7276720030004,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 2030051328
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_baseline_2t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=6765 threads=2 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=10006.9 wall_ms=10006.9 audio_seconds=1.95817 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=17363.6 wall_ms=17363.6 audio_seconds=4.11479 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=9857.1 wall_ms=9857.12 audio_seconds=1.95521 nonfinite=0
[此处省略，完整原始文件见链接]
[TTSBench] iteration=28 language=en phase=measured synth_ms=17413 wall_ms=17413.1 audio_seconds=4.11692 nonfinite=0
[TTSBench] iteration=29 language=zh phase=measured synth_ms=9983.86 wall_ms=9983.88 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=29 language=en phase=measured synth_ms=17723.8 wall_ms=17723.9 audio_seconds=4.11613 nonfinite=0
[TTSBench] iteration=30 language=zh phase=measured synth_ms=9888.89 wall_ms=9888.91 audio_seconds=1.95633 nonfinite=0
[TTSBench] iteration=30 language=en phase=measured synth_ms=18168.5 wall_ms=18168.5 audio_seconds=4.11417 nonfinite=0
[TTSBench] iteration=31 language=zh phase=measured synth_ms=10112.5 wall_ms=10112.5 audio_seconds=1.95029 nonfinite=0
[TTSBench] iteration=31 language=en phase=measured synth_ms=17838.5 wall_ms=17838.6 audio_seconds=4.1115 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_baseline_2t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
[此处省略，完整原始文件见链接]
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_tts_final_4t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build/tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_final_4t 4 30
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 625.5646094240001,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 1925214208
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_final_4t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=6129.75 threads=4 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=6615.46 wall_ms=6615.49 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=11755.1 wall_ms=11755.2 audio_seconds=4.11412 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=6500.74 wall_ms=6500.77 audio_seconds=1.95804 nonfinite=0
[此处省略，完整原始文件见链接]
[TTSBench] iteration=28 language=en phase=measured synth_ms=12486.6 wall_ms=12486.6 audio_seconds=4.11471 nonfinite=0
[TTSBench] iteration=29 language=zh phase=measured synth_ms=6928.58 wall_ms=6928.6 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=29 language=en phase=measured synth_ms=12544.1 wall_ms=12544.2 audio_seconds=4.11479 nonfinite=0
[TTSBench] iteration=30 language=zh phase=measured synth_ms=7042.74 wall_ms=7042.77 audio_seconds=1.95392 nonfinite=0
[TTSBench] iteration=30 language=en phase=measured synth_ms=12583.6 wall_ms=12583.6 audio_seconds=4.11067 nonfinite=0
[TTSBench] iteration=31 language=zh phase=measured synth_ms=6975.86 wall_ms=6975.88 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=31 language=en phase=measured synth_ms=12581.4 wall_ms=12581.5 audio_seconds=4.11417 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_final_4t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
[此处省略，完整原始文件见链接]
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_tts_screen_1t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build/tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_screen_1t 1 3
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 248.2299812250003,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 2028441600
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_1t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=5572.75 threads=1 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=17303.1 wall_ms=17303.1 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=30914.1 wall_ms=30914.1 audio_seconds=4.11408 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=17108.5 wall_ms=17108.5 audio_seconds=1.95612 nonfinite=0
[TTSBench] iteration=1 language=en phase=warmup synth_ms=31224.5 wall_ms=31224.6 audio_seconds=4.11417 nonfinite=0
[TTSBench] iteration=2 language=zh phase=measured synth_ms=17188.2 wall_ms=17188.2 audio_seconds=1.958 nonfinite=0
[TTSBench] iteration=2 language=en phase=measured synth_ms=31082 wall_ms=31082.1 audio_seconds=4.11621 nonfinite=0
[TTSBench] iteration=3 language=zh phase=measured synth_ms=17165 wall_ms=17165 audio_seconds=1.95621 nonfinite=0
[TTSBench] iteration=3 language=en phase=measured synth_ms=31144.7 wall_ms=31144.7 audio_seconds=4.11421 nonfinite=0
[TTSBench] iteration=4 language=zh phase=measured synth_ms=17150.8 wall_ms=17150.8 audio_seconds=1.95804 nonfinite=0
[TTSBench] iteration=4 language=en phase=measured synth_ms=30975 wall_ms=30975 audio_seconds=4.11287 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_1t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_tts_screen_4t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build/tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_screen_4t 4 3
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 98.59303896799975,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 2027208704
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_4t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=5713.4 threads=4 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=6527.41 wall_ms=6527.44 audio_seconds=1.95617 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=11607.5 wall_ms=11607.5 audio_seconds=4.11483 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=6437.49 wall_ms=6437.51 audio_seconds=1.95621 nonfinite=0
[TTSBench] iteration=1 language=en phase=warmup synth_ms=11649.3 wall_ms=11649.4 audio_seconds=4.11479 nonfinite=0
[TTSBench] iteration=2 language=zh phase=measured synth_ms=6435.21 wall_ms=6435.23 audio_seconds=1.95029 nonfinite=0
[TTSBench] iteration=2 language=en phase=measured synth_ms=11717.1 wall_ms=11717.1 audio_seconds=4.11446 nonfinite=0
[TTSBench] iteration=3 language=zh phase=measured synth_ms=6683.42 wall_ms=6683.44 audio_seconds=1.95621 nonfinite=0
[TTSBench] iteration=3 language=en phase=measured synth_ms=11870.5 wall_ms=11870.5 audio_seconds=4.11421 nonfinite=0
[TTSBench] iteration=4 language=zh phase=measured synth_ms=6730.53 wall_ms=6730.55 audio_seconds=1.95517 nonfinite=0
[TTSBench] iteration=4 language=en phase=measured synth_ms=12002.4 wall_ms=12002.4 audio_seconds=4.11525 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_4t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 raw_tts_screen_6t/run

目的：在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。

```bash
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_baseline_build/tts_bench /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1 /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_04_board/raw_tts_screen_6t 6 3
```

参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。

真实退出/守护记录：

```json
{
  "returncode": 0,
  "seconds": 94.81884302400067,
  "termination_reason": null,
  "forced_kill": false,
  "process_gone": true,
  "devices_released": true,
  "original_321_unchanged": true,
  "disk_free_bytes": 2025934848
}
```

真实stdout节选（完整[terminal.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_6t/terminal.log)）：

```text
[SDK] sherpa=1.13.8 git=11afbd00 ort=1.28.2
[TTSInit] ms=6044.68 threads=6 sid=17 sample_rate=24000
[TTSBench] iteration=0 language=zh phase=first_use synth_ms=5899.53 wall_ms=5899.56 audio_seconds=1.94233 nonfinite=0
[TTSBench] iteration=0 language=en phase=first_use synth_ms=10603.2 wall_ms=10603.2 audio_seconds=4.11412 nonfinite=0
[TTSBench] iteration=1 language=zh phase=warmup synth_ms=6111.11 wall_ms=6111.14 audio_seconds=1.9465 nonfinite=0
[TTSBench] iteration=1 language=en phase=warmup synth_ms=10849.7 wall_ms=10849.7 audio_seconds=4.11392 nonfinite=0
[TTSBench] iteration=2 language=zh phase=measured synth_ms=6889.96 wall_ms=6889.98 audio_seconds=1.94633 nonfinite=0
[TTSBench] iteration=2 language=en phase=measured synth_ms=11274.5 wall_ms=11274.6 audio_seconds=4.1115 nonfinite=0
[TTSBench] iteration=3 language=zh phase=measured synth_ms=6917.03 wall_ms=6917.05 audio_seconds=1.95513 nonfinite=0
[TTSBench] iteration=3 language=en phase=measured synth_ms=11402 wall_ms=11402 audio_seconds=4.11479 nonfinite=0
[TTSBench] iteration=4 language=zh phase=measured synth_ms=6945.2 wall_ms=6945.23 audio_seconds=1.95804 nonfinite=0
[TTSBench] iteration=4 language=en phase=measured synth_ms=11296.1 wall_ms=11296.2 audio_seconds=4.11508 nonfinite=0
[TTSBench] complete
```

真实stderr节选（完整[stderr.log](../reports/stage5_04_board/collected_20261017_231748/files/reports/stage5_04_board/raw_tts_screen_6t/stderr.log)）：

```text
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/piper-phonemize-lexicon.cc:PiperPhonemesToIdsKokoroOrKitten:261 Skip unknown phonemes. Unicode codepoint: \U+025a.
```

输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。

## 操作 本地分析、绘图、差异与证据收集

```powershell
python tools/stage5_04_collect.py --complete-only
python tools/stage5_04_analyze.py --collection Z:/master_T/Linux/资料/code/rk3576_multimodal_stage5_source/rk3576_multimodal/reports/stage5_04_board/collected_20261017_231748
python tools/stage5_04_plot.py --before raw_tts_baseline_2t --after raw_tts_final_4t --pipeline-case candidate_pipeline_pairs_4t
python tools/stage5_04_export.py
```

collect仅SSH只读打包reports04，--complete-only跳过未完成case，验证普通文件/安全相对路径、文件和总字节上限，SHA清单保留；不收模型。analyze按case+request_id关联steady事件，按原CSV阶段/语言/fixture分组，nearest-rank统计。plot只读真实数据生成PNG/SVG，未生成示意数据。export生成完整前后源码和git diff --no-index；--binary保留换行字节差异，core.autocrlf=false不转换；在新临时树git apply --check、实际apply后逐文件SHA比对，不在真实工作树执行apply。成功输出、SHA及验证在本地报告目录。

## 操作 最终材料归档

目的：将本节完整源码、差异、报告和量化结果保存到隔离reports目录，不更新任何运行版本。

```powershell
python tools/stage5_04_ssh.py --payload reports/stage5_04_local/payloads/30_delivery.py --timeout 120
```

`--payload`指定已保存在本地的完整远程Python脚本（含归档SHA）；`--timeout 120`限定SSH命令等待。远程先检查目标不存在、普通文件/安全相对路径、SHA与500MiB剩余空间，再用普通cat权限在`reports/stage5_04_board/final_acceptance/`新建归档及材料树；不覆盖已有目录，不启动测试，不写模型或稳定版本。实际退出码、文件数、SHA、空间与保护核验以`reports/stage5_04_local/final_delivery_receipt.json`及SSH原始日志为准。已有完整原始测试帧/ORT trace保留原reports路径，不重复复制模型或大型数据；材料内命令所链接的日志另保留副本。回退只需继续使用未变的旧版本，不需要删除任何文件。
