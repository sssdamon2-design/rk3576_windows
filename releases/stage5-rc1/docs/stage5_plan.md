# 第五阶段 5.1～5.5 源码实施计划

审计日期：2026-10-17（Asia/Hong_Kong）。正式约束来自工程根目录 `STAGE5_CODEX_TASK.md`，已完整阅读。本文件针对当前工作区源码；任务书中的 Windows `D:` 路径不适用于本次 `Z:` 工作区。原计划在本地审计时制定；后续已按三阶段授权完成隔离部署和实机回归。

当前进度：**5.1正式验收通过，5.2～5.5未实施。** 真实构建、CTest、TEXT/VISION语音、本人听音、信号修复、资源/原工程检查与剩余风险见 [5.1正式验收](stage5_01_board_acceptance.md)。以下为各节原实施计划及历史资料边界。

## 操作 1：建立证据和版本基线

### 已阅读的材料及适用范围

- 当前 `CMakeLists.txt`，`include/` 全部接口，`src/main.cpp`、`src/app/`、`src/router/`、`src/ai/`、`src/video/` 的实现，以及音频 Service、Worker、Pipeline 和主要集成 smoke。
- `tests/core_tests.cpp`、`llm_worker_tests.cpp`、Camera 故障替身及测试、CLI 测试、音频预处理测试；检查 VLM 独立 smoke 的模型输入/特殊 token 和构建归属。
- 根目录第一节 ASR、第二阶段、第三阶段手册的背景、模型/SDK、历史验收和源码说明；`4.md` 的 Stage4 模型选型/转换、Stage5 闭环及日志摘录。历史大体积源码附录没有取代当前 `.cpp` 审查。
- `README_STAGE5.txt`、`docs/` 旧架构/构建/验收和 Stage4 集成记录、`config/README.md`；`reports/op10_*` 的日志和统计；`tools/asr_profile.py`、`op10_timing_report.py` 的观测口径。

【源码确认】当前副本没有 `.git`，因此不能给出 Git commit 或声称已有提交。修改前文件保存在 `backups/stage5_01_before/`；变更用 `reports/stage5_01_local/changes.patch` 和 SHA256 清单审查。

【历史记录】`4.md` 中 `[VLM done #1] ... latency_ms=1734.33`、`[VISION TTS done #1] ... synth_ms=17047.8 ... asr_text_to_end_ms=22893.7` 以及 2 TEXT / 1 VISION、3 TTS 的 PASS，与任务书对应。它们是历史文档保存的终端摘录，本轮没有重新执行。单次样本不得扩展为 P50/P95 或长期稳定性。

【历史日志】`reports/op10_20261014_080036/run_01.log` 明确同时打印 LLM/VLM Runtime 不可用。因此这里的 PASS 只证明 ASR/路由/取帧。`073510/summary.json` 的 33 段 ASR 统计也不能作为完整语音回答或当前全部模型共存 RSS。

## 操作 2：按依赖顺序实施五节

### 5.1 统一架构和生命周期

文件：`src/audio/asr_llm_tts_smoke.cpp`、`asr_llm_smoke.cpp`、`src/ai/llm_worker_smoke.cpp`、`src/audio/tts_worker_smoke.cpp`；`include/audio/asr_pipeline.h`、`vad_audio_worker.h`；`src/audio/asr_pipeline.cpp`、`audio_worker.cpp`、`vad_audio_worker.cpp`；`src/ai/rk3576_vlm_backend.cpp`；Worker 契约头文件；CMake 和对应测试。

最小方案：复用原类和 Runtime，修正回调状态与 Worker 的逆序析构依赖，关闭空队列唤醒 ASR 消费者，加入线程入口异常边界及一次启动约束，RKNN 输出用 RAII；恢复遗漏的预处理测试，避免缺 Runtime 专用测试误用于真实 VLM 构建，复用已有 TTS 静态库。

风险：误改正常清空/排队行为，源码拆分漏入 CMake，真实 SDK ABI 未在 Windows 构建，Runtime 阻塞导致 join 无界。验收：原可移植回归 + 队列关闭/析构/异常/重复启动测试；目标端编译、原 CLI、原完整语音命令、失败路径仍须板端确认。架构/生命周期/接口契约与学习题见 `stage5_01_architecture_audit.md`。

### 5.2 可控异步 Pipeline

文件：现有 `RequestProcessor`、Router、LLMWorker、TTSWorker、ASR Pipeline、语音组装入口；必要时在 `app/` 增加很小的请求调度实现，必须调用现有 Engine/Service，不重复实现模型。

依次实施：先把入口特有的 Prompt 策略明确为兼容配置，再将 VLM 从 ASR 回调移入受控任务；统一请求 ID、完成/取消状态；暴露队列深度、拒绝、丢弃和过期计数。保留 FIFO 的可解释结果，音频丢旧策略必须记录被丢请求，不能仅用 bool 表示一切正常。评估采集/播放重叠和误触发，明确没有 AEC。为生命周期操作规定一个 owner，锁和等待谓词保持简单。

风险：在 3.8 GiB 内存上增加队列、并发模型和额外 PCM 缓冲；取消语义导致已接受任务漏通知；Qt/回调重入死锁。NPU 公共调度只在板端出现并确认冲突后决定，不能把两个 Engine 的局部 mutex 当成全局保护。

验收：门闩控制的并发测试覆盖容量、FIFO、停止、回调异常和完成恰一次；目标端 TEXT/VISION 交替、ASR/TTS 重叠、队列饱和及退出日志。不得声称普通抑制录音等同 AEC。

### 5.3 Camera 数据链路和内存

文件：`video_capture.cpp`、`camera_service.cpp`、`latest_frame_buffer.cpp`、`common/types.h`、`rk3576_vlm_backend.cpp`；必要时提取原 CPU 预处理以独立测试，算法和模型输入默认保持原样。

先测量 V4L2 plane/stride、复制字节、每帧分配、RGB 预处理和 RKNN 输入/输出开销，再选可回退方案。当前一次 MMAP→vector 复制是 QBUF 后有效持帧的基础。LatestFrameBuffer 已用 move/shared_ptr，没有必要为它再建整帧队列。评估重复使用 RGB/embedding 缓冲；RGA/DMA-BUF 先确认 SDK/驱动导入和缓存同步条件。

风险：ISP 颜色范围、stride、裁剪比例和模型参考预处理不一致；过早 QBUF；复用仍被消费者持有的内存；占用更多 Camera buffer。验收：固定图输入及参考输出对比、真实摄像头回答、预处理前后延迟、RSS/VmHWM、持续内存曲线及回退。保留 CPU memcpy 时不得写全链路 zero-copy。

### 5.4 统一 Profiling，优先 TTS

文件：`common/timing.h`、结果/音频段/请求数据类型、ASR/LLM/VLM/TTS Worker 和 Service、播放服务、`tools/`、`reports/`。

先以 steady_clock + Request ID 关联采集/语音段起止估算、VAD 就绪、各阶段入队/出队/推理、首文本、完整文本、首音频就绪、首写入/实际播放观测及 drain 结束；不可获得的硬件首声音时间标为不可测或估算。输出 CSV/JSON 和固定实验元数据；统计 mean/P50/P95/min/max/n、成功/失败/拒绝，区分冷启动、warm-up、单次、连续和长期。

先原样测 Kokoro，不替换模型。比较线程数和 CPU 压力、文本长度、模型重复初始化、分句合成/播放重叠的条件；选一个真实收益明确的方案，保留原路径、版本、命令、原始日志及副作用。

风险：把不同口径的时间相加；不完整请求混入分位数；将首次 PCM 就绪冒充首次听到声音；过多线程反而挤压 ASR。验收：建议每组 ≥30 次，少样本明确标注；`/proc` CPU/RSS 与可用 NPU 接口原始采样；至少一项板端优化前后对照。无硬件证据则该节实测验收不通过。

### 5.5 Qt、稳定性和最终交付

文件：统一业务接口、CMake 可选 Qt target、UI 文件（仅在具备依赖时新增）、稳定性脚本及报告。

【源码确认】当前没有 Qt GUI。保持 CLI 独立可构建；UI 不直接执行阻塞推理，通过工作线程和信号槽更新结果，关闭窗口按生产者→消费者→Runtime 的顺序退出。

验收：多轮 TEXT/VISION/语音播报、摄像头无帧/故障、麦克风断开、模型初始化失败、播放失败、队列上限、启停、SIGINT/SIGTERM、内存增长和 NPU 资源冲突；记录实际持续时长、请求数、失败和资源数据。预定时长与实际时长都必须记录，不以 15 秒 smoke 代替稳定性测试。

最后生成 `docs/stage5_final_engineering_manual.md` 与 `.docx`，正文一致，包含任务书的 20 项结构、完整关键源码和逐句解析、每条重要命令和真实输出、20～30 道完整参考题、复现手册与术语表。Word 按 A4/中文字体/等宽代码/可更新目录排版，并渲染核验。它是 5.1～5.5 完成后的交付物，本轮不生成一个冒充最终验收的占位手册。

## 操作 3：验证和部署边界

### 本轮能完成的工作

Windows 源码修改、真实本机 C++ 构建和可移植测试、故障注入、差异/快照/文档。Windows 无 V4L2、ALSA 或 NPU 验证；未使用假的 SDK 头文件冒充真实目标端构建。

### 目标端操作

涉及上传、部署、覆盖源文件、启动修改后硬件程序和系统配置前，需要用户批准；必须先提供具体变更和本地检查记录。批准后先只读检查连通性、环境、SDK 版本、现有文件 hash 和资源，再使用独立源码/构建目录与日志目录。实机回归命令和原参数说明列在 5.1 文档。当前没有执行 SSH，也没有远程变更。
