# 5.3 命令、参数与真实输出索引

本节命令均已由保存的 Python payload/command.json 实际执行，复现时必须换一个不存在的报告目录名。此页给出等价的可读形式，真实 argv、stdout、stderr、退出码仍以报告文件为准。不要直接重跑 exclusive 部署脚本覆盖已经冻结的版本。

## 1. 路径与影响

```bash
REVIEW=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
source "$REVIEW/tools/stage5_board_paths.sh"
```

变量 REVIEW 只指向已授权隔离目录。source 在当前 shell 导入已核实的 SDK/模型路径与 LD_LIBRARY_PATH，不修改系统环境文件；脚本只读原工程 CMakeCache 取得实际 SDK 位置。模型直接从原路径读取，没有复制或改写。后台启动使用普通 cat 用户；sudo -n 只用于只读 fuser 查询，不用于构建或程序运行。

`uname -a` 确认目标 ARM64；`free -b` 以字节给出系统内存；`df -B1 "$REVIEW"` 以字节检查当前文件系统可用空间。构建脚本逐秒取 statvfs，低于 500 MiB 即停止。`v4l2-ctl -d /dev/video11 --get-fmt-video` 中 -d 选择设备、--get-fmt-video 查询实际格式，不改设备树或驱动。--get-parm 本轮返回 255、不支持；FPS 使用发布帧数/单调时钟计算。

## 2. 基线和候选版本构建

```bash
cmake -S "$REVIEW/stage5_03_source" -B "$REVIEW/build/stage5_03_board" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
  -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
  -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
  -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"
cmake --build "$REVIEW/build/stage5_03_board" --parallel 3
ctest --test-dir "$REVIEW/build/stage5_03_board" --output-on-failure \
  --timeout 30 --output-junit "$REVIEW/reports/stage5_03_board/NEW_NAME/ctest.xml"
```

- -S/-B 把源码和产物明确分离；这里是板端原生 ARM64 编译，没有伪称 Windows 交叉验证。
- Release 保持基线与优化版相同的构建类型；三个并行编译任务避免不受控内存占用。
- 三个 ON 启用真实 RKLLM、VLM 和 sherpa 接口；ROOT/INCLUDE/LIBRARY 只指向现有 SDK，未改其内容。
- BUILD_TESTING 注册确定性测试和手动硬件探针；手动探针没有作为 CTest 自动启动硬件。
- --output-on-failure 显示失败细节，--timeout 30 给每项测试兜底，--output-junit 保存机器可读结果。测试名称自己的 TIMEOUT 若更短仍生效。

细分基线采用同样命令，只替换为 stage5_03_baseline_source、build/stage5_03_baseline。初次候选构建成功 26 个 Target；最终生产源码复测 ARM64 6/6、本地 SDK 关闭的 portable 8/8。不能把目标数量或 SDK 链接解释为全部测试实际执行过 NPU。初次/修复后的完整配置、编译和 CTest 日志分别在 candidate_build、candidate_retirement_review、candidate_counter_instrumentation、candidate_config_review，失败记录从不覆盖。

## 3. Camera 和固定帧探针

```bash
python3 "$REVIEW/tools/stage5_03_probe_run.py" --name NEW_LIVE \
  --variant candidate --samples 12
python3 "$REVIEW/tools/stage5_03_probe_run.py" --name NEW_FIXED \
  --variant candidate --samples 6 --fixed
python3 "$REVIEW/tools/stage5_03_probe_run.py" --name NEW_FALLBACK \
  --variant candidate --samples 6 --fixed --fallback
```

name 为独占新报告目录；variant 选择冻结细分基线或候选二进制；samples 限制 1～64，避免无限采样。fixed 循环使用 raw_5_2_baseline 保存的三个真实 NV12 帧，六次包含每帧两次。fallback 同时设置 CAMERA_POOL=0 和 VISION_PREPROCESS=reference。每个子进程 180 秒上限，检查 exe 和 PID start token 后才向本次子进程发信号；超时或强制终止会明确判失败。

核心等价命令为：

```bash
STAGE5_IMAGE_PROFILE="$REVIEW/reports/stage5_03_board/NEW_LIVE/image_profile.jsonl" \
  "$REVIEW/build/stage5_03_board/stage5_03_memory_probe" \
  "$STAGE5_VLM" "$STAGE5_VISION" /dev/video11 \
  "$REVIEW/reports/stage5_03_board/NEW_LIVE" 12
```

这是单次进程执行 12 次“按需获取最新帧→VLM”；Camera 持续采集，不是每帧执行 VLM。requests.csv 的 success=1 表示本次引擎成功，result.json 的 returncode=0、devices_released=true、process_gone=true 是进程与设备检查。camera.json 在 stop 前取 FPS；终端 CameraCounters 在 stop 后计算，分母多了一点退出时间，不能混用。

image_profile.jsonl 每行 stage/ms/id/bytes/allocations 分别表示操作边界、毫秒、帧 ID、该操作的数据量和源码可见扩容/控制块事件。capture_alloc_prepare 包含 reserve，capture_payload_reserve 是其中嵌套计时，不应相加。preprocess_fused 同时包含转换与 resize；两者没有单独可靠时间。rknn_inputs_set 是 SDK 输入准备，不是零成本指针传递。

## 4. 真实麦克风和回放退出

```bash
python3 "$REVIEW/tools/stage5_03_voice_run.py" --name NEW_VOICE \
  --seconds 120 --timeout 240 --grace 70
python3 "$REVIEW/tools/stage5_03_voice_run.py" --name NEW_INT \
  --signal SIGINT --trigger ready --delay 2 --seconds 30 --timeout 100 --grace 50
python3 "$REVIEW/tools/stage5_03_voice_run.py" --name NEW_TERM_CANCEL \
  --replay --replay-source pair --stop-mode cancel_pending \
  --signal SIGTERM --trigger vision --delay 0.2 --seconds 30 --timeout 130 --grace 70
python3 "$REVIEW/tools/stage5_03_voice_run.py" --name NEW_TERM_DRAIN \
  --replay --replay-source pair --tts-queue-ms 60000 --request-lifetime-ms 120000 \
  --signal SIGTERM --trigger tts --delay 0.2 --seconds 30 --timeout 170 --grace 80
```

每轮重新从 /proc/asound/cards 与 pcm 节点匹配 HyperX Cloud III，不写死历史数字声卡号。实际 argv 保存 command.json；ALSA 使用 plughw:CARD=识别出的ID,DEV=识别出的设备。voice 自然输入才验证 USB 麦克风、Silero、SenseVoice；replay 明确跳过它们，只用于可控调度/信号时机。pair 是原 5.2 固定的视觉/文本输入文件，不是伪造 ASR 日志。

signal 选择被测信号，trigger 在日志中观察指定里程碑后才计 delay；tts 观察 ALSA write，意味着播放已提交。grace 只用于本次新子进程的安全等待上限。强制 SIGKILL 保护即使触发也不能算优雅退出；真实测试 result.forced_kill=false 才支持本轮安全退出结论。drain 完成已接收工作；cancel_pending 取消尚未开始或尚未提交的下游工作，不强行中断正在 RKNN/RKLLM 中执行的调用。

退出检查按顺序看 signal 事件及 PID→ASR joined→LLM joined→TTS joined→FramePool in_use=0→Camera stopped/VLM destroyed→shutdown complete。STOPPED 是收到信号后的成功状态，不要求字面 PASS。真正的子进程退出码在 result.json；SSH/Python wrapper 的 0 只表示证据传输完成。

```bash
sudo -n -- /usr/bin/fuser -v /dev/video11 /dev/snd/实际采集节点 /dev/snd/实际播放节点 /dev/dri/实际NPU节点
```

此命令只查占用，没有 -k。没有占用时 fuser 通常退出 1，且 stdout/stderr 为空；这是检查通过，不是程序错误。ALSA status 应为 closed，子进程 /proc/PID 消失。最终另查 /dev/rga，没有对共享进程发信号。

## 5. RGA 失败实验的复现边界

独立 stage5_03_rga_probe 手动目标分别试过虚拟地址导入、system DMA-BUF 导入、DMA 分步 resize→CSC；原始 argv、result、stdout/stderr 及 dmesg 在 rga_diagnostic、rga_diagnostic_dma、rga_diagnostic_split。三次均在第一个硬件 job 失败，不能输出 RGA P50/P95 或质量通过结论。不应盲目循环重试导致共享设备更多超时；本节已经停止 RGA 实验，生产选择 CPU。驱动自己报告 soft reset，不是本次脚本修改/重置驱动。

只读 `dpkg-query -W '*rga*'`、`/sbin/ldconfig -p` 和头文件检查用于区分包版本、SO 文件名、Runtime API 版本；没有执行 ldconfig 更新。reserved heap 不具备普通用户访问权限，没有 chmod、sudo 分配或配置修改。

## 6. 本地证据整理与补丁验证

```powershell
python tools/stage5_03_collect.py
python tools/stage5_03_analyze.py --collection reports/stage5_03_board/collected_实际时间
python tools/stage5_03_export.py
```

collect 只打包隔离 reports/stage5_03_board 内普通文件，拒绝符号链接、目录穿越和超大成员；解压到独占的新本地目录。analyze 只读取真实 JSONL/CSV；P50/P95 使用 nearest-rank，保留全部原始样本；空项保持未测量。export 使用 git diff --no-index --binary、core.autocrlf=false 生成完整补丁，并在临时复制的精确基线做 git apply --check、实际 apply 和逐文件 SHA256 回环检查；不在真实工作区试贴补丁。目录不是 Git 仓库，不伪造 commit ID。

每次 SSH 的 payload.py、命令、原始 stdout/stderr 和传输退出码位于本地 reports/stage5_03_board/ssh_时间；每个板端进程的真实退出码在采集目录对应 result.json。完整文件映射由 collection manifest 的 SHA256 连接起来。
