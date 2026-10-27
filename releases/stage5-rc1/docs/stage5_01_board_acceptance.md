# 5.1 RK3576 实机回归、信号修复与正式验收

**验收结论：5.1 通过。** ARM64 构建、板端全部已注册 CTest、真实 TEXT/VISION 语音闭环、本人听音确认、自然退出、SIGINT/SIGTERM 和必要资源检查均已完成。具备进入 5.2 的条件；本轮没有开始 5.2 重构，也没有把修改发布到原稳定工程。

日期：2026-10-17，Asia/Hong_Kong。开发板 `cat@192.168.10.27`；所有部署、修改、构建和测试报告仅在：

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
```

结论针对下述有限时长回归，不代表长期稳定性、任意 SDK 故障下的硬截止取消或完整模型质量验收。

## 操作 1：证据、授权与版本

用户依次授权只读预检、隔离部署/ARM64 编译、第三阶段实机测试及必要最小修复。原工程、模型、SDK、驱动、设备树、系统配置未被覆盖；原 `build/stage5_full` 保留。

第二阶段不可变源码包为 `stage5_01_review_preflight_v2.tgz`，SHA256 `a653dd57e1ed5138170dd6d6ff7eb77a1518aa0e97c909402b662cab45c13c6e`，先完成 21/21 目标构建。第三阶段先保存原版的真实信号缺陷，再仅修改三个生产文件并重新构建。旧 SOURCE_SHA256SUMS 是包的历史清单，修复后不能再把它当成当前源码全部一致的证明；最终 77 项本地/板端源码与采集工具哈希另存 `phase3_final_20261017T110519Z/source_sha256.json`。

实际 RKLLM Runtime 1.3.1、RKNPU driver 0.9.8。Qwen 文件日志标示转换工具版本 1.2.3，SmolVLM2 文件标示 1.3.1；这属于模型制品版本差异，本轮没有重转模型。两者均完成下述真实推理。

完整本地证据根目录：

```text
reports/stage5_01_board/phase3_ssh_20261017_190524_321782/
  collected/reports/stage5_01_board/
```

板端对应日志保持在隔离根目录的 `reports/stage5_01_board/`。各次 SSH 的真实命令、载荷、stdout/stderr 和返回码还保留在本地 `phase3_ssh_*` 各执行目录；不能用汇总 JSON 代替原始终端输出。

## 操作 2：ARM64 CTest

执行命令（每项保留 CMake TIMEOUT 10～20 秒，总调用另设 120 秒保护）：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
source "$ROOT/tools/stage5_board_paths.sh"
timeout --signal=TERM --kill-after=10s 120s \
  ctest --test-dir "$ROOT/build/stage5_01_board" \
    --output-on-failure --timeout 30 --output-junit "$REPORT/ctest.xml"
```

`REPORT` 为当次新建的隔离报告目录；原始 command.json 保存的是实际绝对路径。

| 阶段 | 总数/通过/失败 | CTest 报告总耗时 | 真实退出码 |
|---|---|---|---|
| 修复前 | 4 / 4 / 0 | 0.26 s | 0 |
| 信号修复重编后 | 4 / 4 / 0 | 0.27 s | 0 |

| 测试 | 验证内容 | 后端性质 | 修复后耗时（JUnit） |
|---|---|---|---|
| `asr_pipeline_tests` | 队列关闭唤醒、空队列析构/异常退栈、排空、重复启动拒绝、识别与业务回调异常 | Fake ASRService，无模型/ALSA | 0.00957815 s |
| `audio_preprocessor_tests` | PCM 预处理输入、格式及转换断言 | 纯算法 | 0.00895747 s |
| `llm_worker_tests` | Mock 推理、Worker 队列/停止/异常及借用状态生命周期 | Mock Backend；链接真实库不等于调用真实推理 | 0.0120065 s |
| `camera_service_tests` | 启停、异常、重启、超时、保留帧生命周期、析构 join | Fake VideoCapture，无 V4L2 | 0.228979 s |

真实后端开启时，portable-only 的 `core_tests`/`cli_smoke` 不注册，因此 ARM64 的正确总数是 4，不是 Windows 的 6。上述测试均通过，没有需要修复的 CTest 失败项；SDK 与设备能力由下一项验证。

## 操作 3：真实完整语音闭环和听音

每次运行前读取 `/proc/asound/cards`、`arecord -l`、`aplay -l` 和 PCM 节点，确认唯一 HyperX Cloud III 双向设备。本轮实际为 card 1、device 0、ID `III`，程序参数使用动态发现的 `plughw:CARD=III,DEV=0`，未写死历史声卡编号。

模型/SDK 均复用 [预检核实的原有路径](stage5_01_readonly_preflight.md)。Camera 为 `/dev/video11`，3840×2160 NV12、单 plane；RKNPU 节点 `/dev/dri/renderD129`。原 `rkaiq_3A_server`（PID 423）保持运行。

原始命令在 `voice_both_natural_01/command.json`；关键执行形式为：

```bash
python3 -I "$ROOT/tools/stage5_board_phase3_run.py" \
  --name voice_both_natural_01 --seconds 90 --timeout 240 --grace 45
```

该命令已经执行；报告目录已存在，不能用相同名称重跑。复测需换新的 run name。采集工具自己发现声卡、构造原 `asr_llm_tts_smoke` 的完整模型位置参数并保存 command.json。

用户先回复“准备好了”，程序进入监听后按要求说“一加一等于几？”和“前面有什么？”。真实数据如下，均为单次样本，不是 P50/P95：

| 指标 | TEXT | VISION |
|---|---|---|
| SenseVoice 文本 | 一加一等于几 | 前面有什么 |
| VAD 语音长度 | 1.482 s | 1.418 s |
| ASR 延迟 | 595.921 ms | 542.165 ms |
| 推理延迟 | Qwen 1152.91 ms；首文本 435.954 ms | VLM 1842.34 ms |
| Camera 帧 | 不适用 | frame_id 1263；frame_age 9.246 ms |
| TTS 合成 | 8524.3 ms | 16392.6 ms |
| ALSA 播放 | 1985.14 ms | 4485.63 ms |
| ASR 文本到播放结束 | 11662.8 ms | 22720.8 ms |

Qwen 实际回答“一加一等于二。”。VLM 实际回答：`A dark, blurry image that seems to be a silhouette or an indistinct shape.`。保留原英文视觉 Prompt；这里证明真实取帧、RKNN/RKLLM 推理和播报通路运行成功，没有据此声称场景语义准确或中文视觉问题已原样传入模型。

真实汇总：

```text
VAD segments: 2
ASR recognized: 2
Audio queue dropped: 0
LLM accepted/completed/success/failed/rejected: 1/1/1/0/0
TTS accepted/completed/success/failed/rejected/empty: 2/2/2/0/0/0
VISION completed/success/failed: 1/1/0
PASS
```

进程退出码 0，自然完成（没有发送信号），子进程持续 113.4595 秒，包含模型初始化与 90 秒录音窗口。采集 XRUN/Suspends/Recoveries/RecoveryFailures 均为 0，播放累计 XRUN 为 0。

**用户明确回复“两个回答都听到了”。** 这项确认来自本次会话本人反馈，不是从 `TTS success=true` 推断；原文保存在 `user_participation.json` 和板端 run 的 `user_confirmation.json`。视觉语义准确性没有单独获得确认。

## 操作 4：修复前信号缺陷与最小修复

先运行第二阶段的原版本，在 `[Listen]` 后两秒向已校验 PID 发送信号，保存原结果：

| 原版测试 | 子进程实际返回码 | 结果 |
|---|---|---|
| `baseline_sigint` | -2 | 被 SIGINT 直接终止，无应用级排空清理 |
| `baseline_sigterm` | -15 | 被 SIGTERM 直接终止，无应用级排空清理 |

两次都没有强制 kill。虽然操作系统关闭了进程 fd，这不构成 C++ Worker join、Runtime destroy 或优雅退出成功的证据。

### 三个生产文件的具体差异

| 文件 | 类/函数/成员变化 | 正确性依据与影响 |
|---|---|---|
| `src/audio/asr_llm_tts_smoke.cpp` | 新增局部 `StopSignals`；main 在 SDK 初始化前屏蔽 SIGINT/SIGTERM；专用线程用 `sigtimedwait` 接收并设置原子状态；主线程轮询生产者完成并请求停止；ASR join 后显式 shutdown；增加各层清理日志，信号成功输出 STOPPED | 没有异步 signal handler；不在 handler 中加锁、join、输出或分配。正常线程执行停止。信号线程比所有 SDK/Worker 先构造、后析构，避免借用状态提前销毁。新增 1 条控制线程，不改变 AI 调用/队列拓扑、Prompt、模型参数 |
| `include/audio/vad_audio_worker.h` | 新增私有 `finished_` 原子和公开只读 `isFinished()`（acquire） | 让主线程观察完成而无需一开始阻塞在 join；现有函数签名保持，类布局变化已 ARM64 重编相关目标 |
| `src/audio/vad_audio_worker.cpp` | run 结束 release 发布 finished；已停止时 runImpl 直接成功返回；完成正常停止/最终 flush 后 ok=true | finished 发布发生在 runImpl 局部 VAD、AudioCapture、QueueCloser 已析构之后；错误路径仍保留 ok=false/error。请求停止不再被误记为采集错误，最终仍 join 以回收线程 |

原未关闭空队列的 ASR 停止问题，已在首轮改动中通过 `close`、谓词 wait 和 notify 修正，本轮实际空闲信号测试再次覆盖了该路径。未让主线程提前关闭音频队列，以免生产者最后 flush 推送被误拒绝。

正常与信号退出均保持：停止/结束采集 → VAD/采集局部资源释放并 close 音频队列 → ASR 排空并 join（同步 VLM 也必须返回）→ 销毁 ASR → 等待 LLM 完成并停止/join → 销毁 Qwen → 等待 TTS 完成并停止/join → 关闭播放/TTS → stop/join Camera → 销毁 VLM → 最后回收信号等待线程。回调状态在这些 Worker 之前构造，直到 join 后才析构。

模型初始化或已运行的同步 SDK 调用没有被强行打断，信号请求会等其完成再清理。初始化期测试因此有约 22.54 秒响应延迟；这是实测限制，不声称即时取消。

### 修复后真实信号回归

| 测试 | 返回码 | 信号后耗时 | 清理/设备/强制终止 |
|---|---|---|---|
| 空闲监听 SIGINT | 0 | ≤2.157 s（旧采集器含事后检查的保守上界） | 完整清理；设备释放；未强制终止 |
| 空闲监听 SIGTERM | 0 | ≤2.202 s（同上） | 完整清理；设备释放；未强制终止 |
| RKLLM 初始化期间 SIGTERM | 0 | 22.5404 s | 初始化返回后协作清理；未强制终止 |
| TEXT 推理期间 SIGTERM | 0 | 12.8347 s | 完成已接收 Qwen/TTS 并播完；完整清理；未强制终止 |

后两项使用改正计时范围的采集器，时间截至子进程退出/输出 EOF，不含之后的 fuser/指纹检查。旧结果原文没有改写。

推理中 SIGTERM 在 TEXT 请求提交后约 0.15 秒发出，首文本为 521.09 ms；日志显示停止采集后，Qwen 继续完成，随后 Kokoro 合成/播放，LLM 和 TTS 各 `1/1/1/0/0`、`1/1/1/0/0/0`，最终 `STOPPED`、退出 0。用户再次明确回复“已提问，听到了回答”。这是排空退出，未将取消/丢失回答冒充正常完成。

所有运行都有总超时和信号后有限宽限期。若确实卡住，采集器先验证 `/proc/PID/exe` 和启动 token，只允许终止本次子进程，并写 `FORCED_KILL_EXIT_FAILURE`。本轮七次运行（修复前两次观察、修复后五次）均未触发超时或强制清理。

## 操作 5：资源、线程与原工程保护

每次记录 PID、线程数、fd 列表、VmRSS/VmHWM 和设备占用；退出后核实进程消失，fuser 查询 Camera、双向 ALSA PCM 和 RKNPU 无占用。最后一次检查时间为 19:05:19 +08:00：

| 检查 | 实测 |
|---|---|
| 隔离语音进程残留 | 0 |
| Camera/ALSA/RKNPU 目标节点 | 无占用者，ALSA 状态 closed |
| 原工程全部受检指纹 | 321/321 与第一阶段不可变基线一致，包括原 build/stage5_full |
| 本地/板端当前源码与采集器 | 77 项 SHA256 一致 |
| 内存 available | 3320414208 bytes，约 3.09 GiB；Swap 0 |
| 磁盘可用（验收前最终资源快照） | 2228097024 bytes，约 2.075 GiB；后续报告归档会再占用少量空间 |
| 完整自然闭环采样最高 RSS | 2704852 KiB，约 2.58 GiB；1 秒采样，不是精确瞬时峰值 |
| 完整闭环采样最高线程数 | 15；进程结束后无本次线程残留 |
| 系统原有 3A 服务 | PID 423 保持运行，未停止、重启或改配置 |
| 与首个原版信号样本比较的新增内核消息 | 150 条；指定 OOM/崩溃/RKNPU 错误关键字筛查命中 0 条 |

日志显示清理函数已返回，加上进程、fd、设备和内存恢复检查，未发现本轮新增明显泄漏、死锁或异常退出。`rkllm_destroy`/`rknn_destroy` 的内部状态和错误返回仍没有独立故障注入验证；不把进程消失解释为数学意义上的无泄漏证明。

## 操作 6：代码差异、工具和可重现性

工作区没有 `.git`。保留了原始/修复快照，并实际执行 `git diff --no-index original repaired`：返回 1 表示存在差异，不是构建失败。没有编造 commit。

- 三个生产文件的标准补丁：`reports/stage5_01_local/phase3_signal_fix/signal_fix.patch`。
- 原样 Git 差异：`reports/stage5_01_local/phase3_signal_fix/signal_fix.git.diff`；路径带 `original/`、`repaired/` 快照前缀。
- 第五阶段 5.1 累计完整源码/工具/文档差异：`reports/stage5_01_local/changes.patch`，对应 `change_manifest.json`。
- 实际 Git 生成的累计完整差异：`reports/stage5_01_local/changes.git.diff`，从原始/当前快照执行 `git diff --no-index`，路径带快照前缀；标准 `changes.patch` 已用 `git apply --check` 验证可应用。
- 完整当前源码附录：`docs/stage5_01_source_appendix.md`。

新增工具：`stage5_board_phase3_run.py` 做动态声卡发现、PID 校验、超时/信号、原始日志及资源采样；`stage5_phase3_ssh.py` 保存每次 SSH 和安全回收；`stage5_summarize_phase3.py` 从原始日志、JUnit、设备/源码/原工程指纹及本人反馈机械核对验收结论。采集器运输成功返回 0 与应用返回码分开保存，原版 -2/-15 没有被掩盖。

`stage5_review.py` 不再声称 VAD 整个 runImpl 逐字不变，而是严格归一化两处明确的停止语义改动后比较原有 PCM/VAD/预滚/时间估计/入队算法；10 项源码边界检查通过。Qwen 后端、Camera Capture、预处理、VLM 特殊 token/推理参数及路由/Prompt/业务回调内容继续保持。

一次本地控制台重打印因 GBK 无法显示原模型词表中的 `❓` 而退出 1；SSH 本身退出 0，原始 UTF-8 stdout/stderr 已完整保存。之后仅修正本地重打印编码；没有把它记成板端应用失败或删除记录。

## 操作 7：剩余风险、学习问题与下一步

仍需后续阶段覆盖：同进程长期循环的内存增长、极端 SDK 卡死/返回失败、回调并发/延迟契约、完成回调抛异常导致漏计数、NPU 并行仲裁和性能分布。当前同步初始化/推理/ALSA 调用采用排空，不提供任意故障下的硬截止取消；外部测试守护若超时只能判失败，不能替代应用成功退出。

模型原有 Kokoro `Unknown token: ❓` 与 RKLLM 自定义模板提示仍保留，本轮没有改模型。没有验证视觉语义准确率、多种中文视觉指令或长时间连续对话；TTS 合成仍明显占用本次端到端时间，属于后续 profiling 的实际优化候选，尚无受控前后对照，不能宣称性能提升。

学习要点：

1. 为什么“退出后设备空闲”不能单独证明优雅退出？默认信号终止也会让内核回收 fd，必须同时核对正常返回码、join/destroy 路径和完整日志。
2. 为什么使用 sigtimedwait？信号先在创建 SDK/Worker 前屏蔽，由普通线程同步消费，因此可以避免异步 handler 中使用不安全的 C++ 操作；等待线程析构也有有限的 100 ms 轮询间隔。
3. finished 原子为何不替代 join？release/acquire 仅发布完成状态，join 仍负责回收 std::thread 并保证其彻底结束。
4. 为什么先等 LLM 再停 TTS？LLM 完成回调还会提交 TTS，提前停止下游会丢掉已接收回答；推理中 SIGTERM 实测证明本轮仍播完回答。
5. 为什么本轮通过仍保留风险？有限正常/信号样本不能证明所有 SDK 失败路径、长期无泄漏或并行 NPU 安全，这些是后续测试边界，不应补造结果。

下一步可以按任务书进入 5.2 的最小异步调度实施，继续复用现有 Engine/Worker，并用本节的真实闭环与退出测试作回归门槛。**本轮结束于 5.1 正式验收，没有开始 5.2 的线程/队列重构。** 最终覆盖 5.1～5.5 的 Word 与 Markdown 完整工程手册仍按任务书在第五阶段最终交付时统一生成。
