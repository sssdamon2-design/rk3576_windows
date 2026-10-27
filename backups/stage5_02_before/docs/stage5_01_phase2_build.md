# 5.1 第二阶段：RK3576 隔离部署与 ARM64 编译实测

本文件记录第二阶段当时的部署和构建结果。**后续第三阶段已完成并正式通过5.1验收，见 [正式实机验收](stage5_01_board_acceptance.md)。** 下文“尚未执行/等待授权”属于第二阶段结束时的历史边界，原始日志与包保持不变。

## 操作 1：实际部署范围与完整性

开发板 `cat@192.168.10.27`，普通 cat（UID 1000），未使用 sudo 编译、安装依赖或修改系统配置。

唯一部署根目录：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
```

先检查目录及悬空符号链接均不存在，再以排他 mkdir 创建，权限受 umask 077 限制。若已经存在即退出，没有覆盖或清理分支。

实际 SCP 上传仅两个文件：

| 文件 | 大小/校验 |
|---|---|
| `stage5_01_review_preflight_v2.tgz` | 126256 bytes；SHA256 `a653dd57e1ed5138170dd6d6ff7eb77a1518aa0e97c909402b662cab45c13c6e` |
| `stage5_01_review_preflight_v2.tgz.sha256` | 包的 SHA256 校验文件，目标为同一目录 |

源码包保持上一阶段审核版本，没有重新打包。远端解压前检查 SHA256、87 个普通文件成员（86 个源文件/工具/文档及一份 SOURCE_SHA256SUMS）、重复成员、绝对路径、父目录跳转、成员类型、允许顶层目录、展开总大小及所有成员哈希。之后使用 `tar --keep-old-files`，再逐项执行 `sha256sum -c SOURCE_SHA256SUMS`，全部成功。

模型、SDK、运行库和旧构建不在包内。SDK 从原稳定 CMakeCache 读取，模型仍使用 [只读预检已核实路径](stage5_01_readonly_preflight.md)。所有程序仅编译，没有加载模型。

## 操作 2：实际配置和编译

日志时间：2026-10-17 18:45～18:46，UTC+08:00。板端 Linux aarch64、CMake 3.25.1、GNU C++ 12.2.0；Release，`BUILD_TESTING=ON`、`BUILD_WITH_RKLLM=ON`、`BUILD_WITH_VLM=ON`、`ENABLE_SHERPA_ASR=ON`。找到 ALSA 1.2.8、RKLLM 和 RKNN，配置与生成成功。

实际执行入口为：

```bash
timeout --signal=TERM --kill-after=15s 840s bash \
  /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_board_compile_only.sh
```

脚本中的配置和构建为：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
# stage5_board_paths.sh 已从原稳定 CMakeCache 读取下述 SDK 变量，并设置子进程 LD_LIBRARY_PATH。
timeout --signal=TERM --kill-after=15s 180s \
  cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"
timeout --signal=TERM --kill-after=15s 600s \
  cmake --build "$ROOT/build/stage5_01_board" --parallel 3
```

真实的逐步 SSH/SCP 参数及远端 Python 载荷保存在本地执行目录的 `*.command.json` / `*.remote.py`；不是用本页模板补写的运行日志。

| 阶段 | 结果 |
|---|---|
| 排他建目录及原工程基线比较 | SSH 退出 0 |
| SCP 上传 | 退出 0 |
| 安全检查、解压、文件校验 | SSH 退出 0 |
| 编译脚本、磁盘监督器 | 均退出 0；无超时、无停止事件 |
| 日志回收 | SSH 退出 0 |

配置成功的退出判据是 `set -euo pipefail` 下配置流水线返回后继续构建，并最终保存脚本退出码 0；原脚本没有单独的 configure 退出码文件。监督过程约 55.15 秒，包含依赖检查、配置、编译与 ldd，不作为推理性能数据。

21 个目标全部构建成功，失败目标为零：

| 类型 | 成功目标 |
|---|---|
| 静态库（4） | `multimodal_core`、`multimodal_audio`、`multimodal_camera`、`multimodal_tts` |
| 主程序/完整语音入口 | `rk3576_multimodal`、`asr_llm_tts_smoke` |
| LLM/ASR 工具 | `rkllm_worker_smoke`、`audio_capture_smoke`、`asr_live_smoke`、`asr_pipeline_smoke`、`asr_vad_smoke`、`asr_route_smoke`、`asr_llm_smoke` |
| TTS 工具 | `tts_smoke`、`tts_playback_smoke`、`tts_worker_smoke`、`tts_worker_queue_smoke` |
| 测试程序（仅构建） | `asr_pipeline_tests`、`audio_preprocessor_tests`、`llm_worker_tests`、`camera_service_tests` |

17 个可执行文件均经 `file` 识别为 ARM aarch64 ELF；没有运行它们。完整入口的 `ldd` 成功，无 `not found`。这证明本轮真实 SDK 分支已编译和链接，不证明 SDK 回调、设备运行或资源释放行为正确。

编译日志有 0 条 `error:`、1 条 `warning:`：`src/ai/rk_backends_unavailable.cpp:21` 的备用 `unavailable()` 在实际后端开启时未使用。该文件未被本轮修改；没有为消除该警告改变功能代码。

## 操作 3：磁盘阈值及原工程保护

编译监督器每秒采样可用空间，日志为 `disk_samples.jsonl`。低于 524288000 bytes（500 MiB）会向本次构建独立进程组发送 TERM，15 秒后仍未结束才强制终止，并记录停止原因、子进程实际退出码及监督器错误码。不会向其他进程发送信号；本次没有触发停止，也没有进行优雅退出测试。

| 指标 | 实测 |
|---|---|
| 编译期间采样最低可用空间 | 2231934976 bytes，约 2.079 GiB |
| 编译结束可用空间 | 2231988224 bytes，约 2.079 GiB |
| 500 MiB 阈值触发 | 否 |

编译前后读取原工程全部 321 项基线，与第一阶段保存的不可变基线完全一致，包括源码/配置/测试与 `build/stage5_full` 全部受检文件、符号链接。旧完整入口仍为：

```text
/home/cat/projects/RK3576/rk3576_multimodal/build/stage5_full/asr_llm_tts_smoke
SHA256 c22de21ef6b82b4aee4cc2d0e4f2e1850960c23c356df2f3fc033b9d1c61fcc4
```

模型权重没有复制、删除或改写，也没有为本阶段重新计算整份模型哈希。未操作驱动、设备树或系统配置。

## 操作 4：本轮代码差异与学习记录

**无编译错误，不需要生产 C++ 或 CMake 修复。** 已部署的 76 项 CMake/源码/头文件/测试内容与当前本地对应文件哈希一致。实际部署版本以不可变 `.tgz.manifest.json` 和板端 SOURCE_SHA256SUMS 为准；后续本地文档更新不代表远端源码变化。

本轮新增本地工具 `tools/stage5_phase2_deploy.py`，用于执行已经获批的固定步骤。它不在已审核源码包内，也没有作为文件上传：

- `payloads()` 生成语法检查过的远端 Python 载荷，经 SSH stdin 执行；建目录前比较 321 项基线。
- 上传固定 SHA256 的不可变包；解压前逐成员校验，拒绝已有目标成员。
- `subprocess.Popen(..., start_new_session=True)` 给构建创建独立进程组，以限定超时/空间不足时的停止范围；这与应用 Worker 的安全退出验收无关。
- `run_step()` 保留原始 stdout、stderr、退出码、客户端超时和远端返回码是否已知，避免将 SSH 255 或客户端超时当作构建结果。
- 远端监督器保存空间采样、原工程前后指纹和结果 JSON；本地回收日志时只接受普通、安全相对路径成员。

原 `stage5_board_build.sh` 会在构建后自动跑 CTest，本次没有使用。`BUILD_TESTING=ON` 只生成测试程序，不等于运行测试。真实后端配置只注册上述四项 CTest，portable-only 的 `core_tests` 和 `cli_smoke` 未注册，因此后续不能机械沿用 Windows 的“6/6”。

## 操作 5：完整证据和下一步

本地完整执行目录：

```text
reports/stage5_01_board/phase2_20261017_184503_994558/
  01_create.* / 02_upload.* / 03_validate_extract.*
  04_compile.stdout.log / 04_compile.stderr.log / 04_compile.execution.json
  05_collect.* / result.json / evidence_manifest.json
  collected/reports/stage5_01_board/
    phase2_archive_validation.json / phase2_elf_files.json / phase2_targets_help.log
    compile_only_20261017T104508Z/
      configure.log / build.log / ldd.log / session.log / exit_code.txt
      stable_before.sha256 / stable_after.sha256 / phase_scope.txt
    supervisor_20261017T104508Z/
      command.json / disk_samples.jsonl / result.json
      stable_before.json / stable_after.json
```

板端编译及监督日志也保留在隔离根目录的 `reports/stage5_01_board/` 对应子目录，未删除构建产物或日志。本地另有 `phase2_summary.json` 汇总；本轮修改前补丁和验证摘要保存在 `reports/stage5_01_local/phase2_input/`。

已具备进入第三阶段实机回归的构建条件。**现在暂停，等待第三阶段授权。** 执行前重新检查设备占用和空间，随后按用户指定顺序运行有超时的 CTest、两条硬件闭环、耳机播放、XRUN、Worker/模型生命周期及 SIGINT/SIGTERM 测试。已知信号缺陷仍未修复或实测；应先记录原行为，再作隔离最小修复、重编和验证。完成这些必要验证前不能正式接受 5.1，也不进入 5.2。
