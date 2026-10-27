# 5.2 RK3576 正式回归验收

**结论：5.2 在本报告明确的有限回归范围内通过。具备进入 5.3 的技术条件，本轮按用户要求暂停，不启动 5.3。**

日期：2026-10-17（Asia/Hong_Kong）。实现、线程图和设计取舍见 [异步 Pipeline 报告](stage5_02_async_pipeline.md)；完整实际源码见 [源码附录](stage5_02_source_appendix.md)，逐句语义、RAII、模板、锁、捕获与面试题见 [语句解释](stage5_02_statement_notes.md)。最终完整 Word/Markdown 工程手册依任务书在 5.1～5.5 完成后统一汇编；本轮交付可直接汇编的 Markdown 正文和源码，未声称已生成最终 Word。

## 操作 1：证据及版本

本地完整、已结束测试的证据：`reports/stage5_02_board/collected_20261017_195843/files/reports/stage5_02_board/`，390 文件，5,182,449 字节。此前 `collected_20261017_195156`、`collected_20261017_195251` 为较早采集快照，不作为最后一项信号测试完整性的证据。

板端同名报告位于 `/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_02_board/`。每个 case 含 command.json、test_parameters.json、pid.json、terminal.log、events.jsonl、resources.jsonl、result.json、设备和系统前后快照、原工程前后指纹。SSH 传输退出码与子进程退出码分开保留；不能因 harness 返回 0 就断言子程序成功。

环境：RK3576 aarch64，Linux 6.1.99-rk3576，Debian GCC 12.2.0，CMake/CTest 3.25.1，RKLLM Runtime 1.3.1，RKNPU driver 0.9.8，Sherpa ONNX 1.13.8 CPU SDK。原有 Qwen2.5-1.5B W4A16 制品标示 toolkit 1.2.3；SmolVLM2-256M W4A16 标示 1.3.1；Vision 使用 scatterfix RKNN。复用 SenseVoice int8、Silero VAD、Kokoro multi-lang v1_1、speaker 17、TTS 两线程，没有重转模型或改 SDK。

每次运行动态读取 HyperX Cloud III，本轮实际 card 1/device 0/ID III，使用 `plughw:CARD=III,DEV=0`。没有写死数值声卡。Camera `/dev/video11`、3840×2160 NV12，NPU `/dev/dri/renderD129`。原 3A 服务保留。

## 操作 2：ARM64 构建与 CTest

原 5.1 隔离构建和已验收可执行文件保留。新建 `build/stage5_02_baseline` 和 `build/stage5_02_board`。前者从冻结的 5.1 源码复制，只加同样的计时、队列峰值和显式文本回放；同步 VLM、容量、停止语义不变，差异保存为 `reports/stage5_02_local/baseline_instrumentation.patch`。

实际构建方式（完整展开后的命令以各 command.json 为准）：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
source "$ROOT/tools/stage5_board_paths.sh"
timeout --signal=TERM --kill-after=15s 180s \
  cmake -S "$ROOT" -B "$ROOT/build/stage5_02_board" \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
    -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
    -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
    -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" \
    -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"
timeout --signal=TERM --kill-after=15s 600s \
  cmake --build "$ROOT/build/stage5_02_board" --parallel 3
```

ROOT 指隔离项目，不是原工程；source 只配置当前进程环境和读取原构建缓存，不改系统。`-S/-B` 分别固定源码与新构建目录；三个后端开关启用真实 SDK；路径变量来自已有已验证依赖。Release 是实际板端优化配置。parallel 3 限制同时编译数。监控器另每秒采样磁盘，低于 500 MiB 终止本次构建并记失败；构建异常不会清理其他目录。

首次 candidate 构建返回 2：公共头前置声明后，`tts_smoke.cpp` 使用 SherpaOnnxWriteWave 缺显式 include。原日志在 `implementation_build/candidate_build.*`。补 include 后 `repair_build_01/candidate_rebuild` 返回 0，23 个目标全部完成；不掩盖首次失败。baseline 21 个目标、CTest 4/4 成功。

```bash
REPORT="$ROOT/reports/stage5_02_board/repair_build_01"
timeout --signal=TERM --kill-after=10s 120s \
  ctest --test-dir "$ROOT/build/stage5_02_board" \
    --output-on-failure --timeout 30 --output-junit "$REPORT/candidate_ctest.xml"
```

REPORT 是该次实际独立目录；--test-dir 指定 ARM64 构建；--output-on-failure 保留失败内容；CTest 属性 TIMEOUT 为 10～20 秒，命令总保护 120 秒；JUnit 可机读，但此版本 testsuite.time=0，真实总耗时采用 CTest stdout 的 0.29 s，不伪造 XML 总耗时。全部 5/5、失败 0、退出码 0。本地 Windows portable CTest 7/7、0.53 s、退出码 0，明确不算 ARM64 验证。

| CTest | 实际验证 | 后端与限制 |
|---|---|---|
| async_pipeline_tests | 第一个推理闸门阻塞时 ASR 已处理后续三段；FIFO/异线程；队满；取消/过期不执行任务体；Drain/CancelPending；显式重启；done 异常；200 轮 Ticket 最后释放/close 竞争；Fake TTS | 真实 Worker/Queue + Fake Service，无模型及设备；通用 FIFO 的 ID 顺序不冒充实际路由识别 |
| asr_pipeline_tests | 空队列关闭唤醒、析构及异常退栈、排空、重复启动拒绝、识别/回调异常 | Fake ASR，无麦克风/模型 |
| audio_preprocessor_tests | PCM 转换和格式边界 | 纯算法 |
| llm_worker_tests | Mock 流式推理、FIFO、容量、停止和回调故障 | Mock Backend；故障注入的 error/cancel 日志是测试预期 |
| camera_service_tests | 启停重启、异常、超时、保留帧生命周期、析构 join | Fake VideoCapture，无 V4L2 |

## 操作 3：NPU 调度实验与根因

`baseline_and_npu_probe/probe.stdout.log` 保存同一进程加载 Qwen+SmolVLM2 后的 3 轮顺序、3 轮重叠调用。6/6 对均成功，没有观测到 SDK 崩溃，因此不能宣称已证明并行“不安全”。重叠的 Qwen 调用明显变慢，总对耗时仅小幅缩短。本入口采用一个现有 FIFO 消费者串行两种 AI 推理，以换取响应可预测性。

sdk_call_overlap_ms 测的是主机 SDK 调用时间区间交集，不是 NPU 利用率或硬件同时执行证明。Camera 实际场景、频率、温度未严格控制，首轮有热身差异；每模式 n=3，不构成广泛性能基准。结果数值表见后文。

## 操作 4：受控文本 A/B 与真实麦克风

受控回放 TSV 在 0/1000/2000/3000 ms 提交 VISION/TEXT/VISION/TEXT。若旧同步回调阻塞，后续实际提交自然延迟；这是被测行为。两版本调用同一个生产 on_text，显式输出 `NO_MICROPHONE_ASR_OR_VAD_INFERENCE`，不能称为 ASR 性能回放。模型输出长度和 Camera 场景并非逐字节固定；两种背压导致接受数不同，不能把该实验当等量任务模型加速对照。

```bash
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name baseline_replay_overload --variant baseline --replay \
  --seconds 30 --timeout 200 --grace 60
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_replay_overload --variant candidate --replay \
  --seconds 30 --timeout 200 --grace 60
```

这是已经执行的名称，脚本使用 mkdir 独占创建报告；重跑应换唯一 name，不覆盖历史。variant 选择两套独立构建。replay 明确不启动麦克风/VAD/ASR；seconds 是 CLI 参数，不代表本模式真的录音。timeout/grace 是进程总运行及收到停止信号后的有限等待保护。

5.1 两个 VISION 回调分别阻塞 1910.42、1920.58 ms；5.2 首个已接受 VISION 提交 0.036826 ms。新版本对 ID 3/4 明确拒绝，ID 2 的 TTS 过期，只有 ID 1 播放，不能把 4 次都算成功。旧版本 TTS 满拒绝 1 次，返回 1；这是保留的基线缺陷，不是省略失败项。

12 秒 TTS 等待限制是在出队时惰性判断，不是 12 秒定时清理。该次过期实际队列驻留 22043.1 ms，跳过了后续合成；不能声称所有请求等候均小于 12 秒。期限提高到 60 秒的 Drain 实验第二回答实际等候 22257.1 ms，说明慢合成本身仍能造成较长等待。

真实麦克风命令由 harness 动态发现声卡、检查 Camera/ALSA/NPU 空闲后启动：

```bash
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_voice_natural --seconds 90 --timeout 180 --grace 60
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_voice_burst --seconds 60 --timeout 160 --grace 60
```

第一轮使用 USB 麦克风、Silero VAD、SenseVoice、Qwen、IMX415/RKNN/SmolVLM2、Kokoro、ALSA。TEXT 1、VISION 1、TTS 2 全成功；用户反馈“两个都听到了”。第二轮实际采集 4 段并全部识别，TEXT/VISION 交替；接受 3、拒绝 1、播放 3；用户反馈“三个回答”。用户第一句后实际有较长停顿，不能把这轮描述为严格每秒一条的压力；后续存在 TTS 忙时继续识别/提交，忙载拒绝有日志。两次听音是 5.2 新确认，未复用 5.1 确认；用户未明确确认画面描述准确率。

原始自然语音子命令完整见 command.json：capture/playback 为动态 ID，随后依次传 SenseVoice 目录、Silero 文件、Qwen 文件、Kokoro 目录、录音秒数、TTS 线程 2、speaker 17、SmolVLM2 RKLLM、Vision RKNN 和 `/dev/video11`。所有模型复用原路径，不复制大型文件。

## 操作 5：安全停止和资源释放

```bash
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_stop_drain --replay --stop-mode drain \
  --signal SIGTERM --trigger tts --delay 0.1 \
  --tts-queue-ms 60000 --request-lifetime-ms 120000 \
  --seconds 30 --timeout 180 --grace 70
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_stop_cancel_pending --replay --stop-mode cancel_pending \
  --signal SIGTERM --trigger tts --delay 0.1 \
  --tts-queue-ms 60000 --request-lifetime-ms 120000 \
  --seconds 30 --timeout 180 --grace 70
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_idle_sigint --signal SIGINT --trigger ready --delay 2 \
  --seconds 30 --timeout 100 --grace 45
python3 "$ROOT/tools/stage5_02_board_run.py" \
  --name candidate_cancel_active_vision --replay --stop-mode cancel_pending \
  --signal SIGTERM --trigger vision --delay 0.2 \
  --seconds 30 --timeout 100 --grace 40
```

trigger tts 是 `[ALSA write]`，即合成完成后的播放写入阶段；不是 TTS 刚开始合成。signal 是主机发送至已校验 executable/PID/start token 的本次子进程，既没有按共享进程名批量 kill，也不以 kill -9 证明优雅停止。所有保护均未触发强制终止。

Drain 接收 SIGTERM 后保留第二个 TTS，返回 0、12.229 s 退出；CancelPending 当前播放结束并将等待的第二 TTS 记为 cancelled，返回 0、1.532 s 退出。两者语义和完成工作量不同，耗时不能视为同等工作加速。Cancelled 回调为兼容旧接口传 -1，实际驻留从 `[TTS cancelled]` 及 QueueStats 读取，不把 -1 纳入平均等待时间。

SIGINT 空闲麦克风退出 1.907 s。VLM 在途 SIGTERM 取消退出 3.413 s：当前 VLM 成功结束，downstream_cancelled=1，TTS 未启动，再 join/destroy。测试未覆盖所有 SDK 异常、任何时刻信号排列，也未实现硬中断活跃 NPU。

所有 10 个程序 case（含两组基线及其中一次失败）均保留真实退出码、shutdown complete、process_gone、devices_released=true、原工程指纹一致；各 case 无 forced_kill/timeout。候选 8 个 case 全返回 0，推理 Worker 总计实际执行 14 次、成功 14 次；TTS 终态 13 次，其中成功播放 11、过期 1、取消等待 1，另有在途推理结束后取消下游 1。7 次 Admission 拒绝跨不同受控场景明确统计，不能合并称为“所有请求成功率 100%”。

两轮真实录音 capture XRUN=0，所有候选 playback_xruns=0，音频段 dropped=0、最终 pending=0、inflight=0、active=0、callback_errors=0。dmesg 快照未检出 OOM、segfault、RKNPU fail/error、hung/blocked-task 匹配；保留全文，不代表内核所有告警均无问题。Kokoro 打印未知 token/phoneme 的既有告警，非静默隐藏；本轮没有改字典或模型。

最终原稳定工程源码/配置/原构建目录共 321 项指纹完全一致；不是整个磁盘逐文件审计。另保留 5.1 隔离程序 SHA256 `7b44730ad55cdb49f252de3e801b3e6680169a93ed0cb59d80fdc8f6720a10b7`。80 项当前源码/测试及运行工具文件与本地一致，候选主程序 SHA256 `1bf59ddf68cb0290e30df3ed945347dc73b7ff477a44d69c8f1f80a51f49d9b7`。无模型/系统写入命令。

最终设备查询为空，ALSA 状态关闭；板端可用内存 3,324,506,112 字节，磁盘可用约 2.06 GiB（final_state 记录 2,207,715,328 字节，df 采样时略有变化）。候选进程采样峰值 RSS 约 2.38～2.52 GiB，不能用退出后内存恢复来代替堆泄漏工具或长测。CMake 全目标成功与原链路没有新增明显退出/资源故障，仅针对本轮有限证据。

## 操作 6：剩余风险与后续边界

- TTS 是主要计算瓶颈；额度/期限以显式少接收、过期或取消换取积压可控，过载回答率下降需要产品策略确认。没有声称 TTS 模型加速。
- 过期惰性检查，等待项可驻留超过期限，额度在终态后才回收；若要更快接受新问题，需另设计定时清理和打断，而非隐藏丢弃。
- NPU 调度只统一本入口两模型；其他程序依靠启动前资源检查，未增加跨进程锁或修改 Runtime。
- 活跃 SDK 不支持硬截止；测试保护能识别失败，不等于 SDK 永久挂死时总可优雅退出。
- restart 在 Fake 单元测试验证；板端反复创建新进程验证模型/设备重新初始化，没有把它称为真实 SDK 进程内 restart 的专项验证。
- 耳机环境未观察到额外回灌语音段，但没有 AEC、PTT 或口头打断功能。视觉描述质量和长期稳定性未作充分统计。
- 无 TSan/ASan、小时级压力、频率/温度控制或生产 P95 结论；这些不以本轮有限样本冒充。下一节仅在用户继续授权时进入 5.3 Camera/内存分析；大规模 TTS 计算优化留 5.4。


## 操作 7：补充等接受数量对照与性能表

完整平均/P50/P95、样本数、队列峰值、拒绝/过期/取消、吞吐及退出数据见 [实测性能表](stage5_02_performance.md)，机器可读为 `reports/stage5_02_board/metrics.json`、`metrics.csv`、`npu_metrics.json`。

为避免只比较不同背压结果，额外执行 `baseline_equal_work_pair` 与 `candidate_equal_work_pair`：同一两请求 TSV、双方均完整接受/播放 2/2、无拒绝/过期。参数在上述 replay 命令中增加 `--replay-source pair --tts-queue-ms 60000 --request-lifetime-ms 120000`。测试工具新增输入关闭时刻；未修改生产推理代码。

该组 VISION 回调由 1737.73 ms 变为 0.034758 ms。停止输入至退出分别 29.114/34.973 s，候选没有更快排空：VLM 回答分别 12/17 个英文词，对应 PCM 80696/107578 帧，合成及播放工作量不同。不能把较早停止输入、不同生成长度或过载丢弃描述为模型计算加速。异步调度的目标已验证，TTS 本身仍是后续瓶颈。

完整 diff 为 `reports/stage5_02_local/changes.patch`，SHA/文件清单为 `change_manifest.json`；通过真实 Git no-index 生成、git apply --check，再在临时基线树实际应用并对所有修改文件逐字节 SHA 比对。Windows Git 的自动行尾转换已在导出命令中显式关闭，不用仅语法可应用的补丁冒充字节一致。源代码算法不变检查另见 `source_invariants.json`。
