# 5.1 逐文件代码审查与 RK3576 隔离回归准备

状态：**5.1第三阶段正式验收已通过；5.2尚未开始。** 最新硬件结果、本人听音确认、三个生产文件的最小信号修复及剩余风险见 [正式实机验收](stage5_01_board_acceptance.md)。本文件下述逐文件表保留修复前审查版本，“无信号处理/待板端”是历史问题；不能替代最新结果，SDK极端故障与长期稳定性风险仍保留。

本文件以下保留上一轮代码审查/执行方案；该轮只编写本地工具和文档，没有改生产C++、模型参数、队列架构。原 `changes.patch`、`validation_summary.json`、文件清单和相等性结果先保存到 `reports/stage5_01_local/review_input/`。原补丁 SHA256 为 `a33d72676f6a8d476c51047c6273aa89325685a6cd5d0ce2f214af442f73ce41`，包含24个文件，清单见 `review_patch_inventory.json`。后续已授权的只读查询记录以最新链接为准。

## 操作 1：逐文件审查原24项修改

### 生产源码与 CMake

测试代号：A=`asr_pipeline_tests`，P=`audio_preprocessor_tests`，L=`llm_worker_tests`，C=`core_tests`，CLI=`cli_smoke`，CAM=`camera_service_tests`。这些均是 Windows 可移植测试，不是实机证据。表中“待板端”不算通过。

| 文件 | 修改前具体问题 | 类/函数/成员修改 | 正确性和接口/线程/生命周期影响 | 剩余风险 | 对应验证 |
|---|---|---|---|---|---|
| `CMakeLists.txt` | 原预处理测试未注册；真实VLM构建仍注册缺Runtime专用测试；TTS smoke重复编译Service实现 | 新增A/P target；audio库加入移出文件；core/CLI要求两后端均OFF；两个TTS smoke链接原multimodal_tts | 不加模型/线程；每个目标只链接一份所需实现；TTS库虽在后面定义，同目录生成阶段可解析 | SDK ON 分支尚未实际编译；目标系统依赖不能由本机结果证明 | A/P及原4项；TTS库与全开组合待板端 |
| `include/ai/llm_worker.h` | 借用Engine之外，回调引用状态的寿命约束不明确 | 只补owner串行start/join/destruction与捕获寿命注释 | 无API、ABI、线程或实现变化 | 使用者仍可违反契约；回调禁止self-join/重入Engine | L间接覆盖；契约主要靠调用端审查 |
| `include/audio/asr_pipeline.h` | ASR缺少停止入口；两Worker重复start可能覆盖joinable线程；非原子结果读取约束不足 | ASR新增公开requestStop；Audio/ASR新增私有runImpl、started_；补join后读状态约束 | requestStop关闭并排空，不强制取消推理；原签名保留；新增bool改变对象布局，必须全量重编，不能混用旧目标文件 | started_只适用于owner串行；Audio stop-before-start仍可创建线程，不等同LLM的NotRunning状态机 | A覆盖ASR；Audio生产者路径待板端/补专门测试 |
| `include/audio/tts_worker.h` | 捕获状态与Service的寿命说明不完整 | 只增契约注释 | 无公开接口、布局或线程变化 | 并发join、回调内销毁仍不支持 | 审查；真实TTS Worker测试待板端 |
| `include/audio/vad_audio_worker.h` | 重复start无保护；线程异常无统一边界 | 私有runImpl、started_ | 无新公开方法；布局变化需全量重编 | bool不是多owner并发保护；停止前初始化可能阻塞 | 只源码审查；VAD生产者待板端 |
| `src/ai/llm_worker_smoke.cpp` | Worker先于回调mutex/cv/结果构造，异常退栈存在引用失效 | main函数try-block；把状态放Worker之前；before_submit仍紧邻submit | 仅组装顺序改变，不新增线程、不改Prompt或计时窗口；Worker先析构join，状态后析构 | 依赖同步SDK回调完成；完成回调若先抛异常，done可能不更新 | 额外本机编译/无参退出2；L的通用生命周期测试；真实SDK待板端 |
| `src/ai/rk3576_vlm_backend.cpp` | outputs_get成功后vector分配抛异常会跳过手工release | 新增不可复制RknnOutputOwner；infer内嵌套作用域 | 成功取得才置acquired；退出作用域释放；embeddings已深复制，释放后不再使用result/ptr；公开接口和正常模型调用不变 | get失败是否部分分配、release失败语义依赖SDK；析构忽略release错误；GenerationState无锁仍依赖回调契约 | 相等性检查预处理/init/token；无本地RKNN故障测试，待真实SDK构建/回归 |
| `src/audio/asr_llm_smoke.cpp` | 回调状态晚于LLMWorker构造 | main try-block，队列/锁/cv/计数提前 | Worker引用原对象而非延长引用寿命；ASR先结束后LLM结束；原路由/Prompt/回调区间逐字相同 | 无协作SIGINT；完成计数异常可超时 | L/A间接；完整入口待板端 |
| `src/audio/asr_llm_tts_smoke.cpp` | LLM/TTS Worker先于其回调状态构造 | main try-block；音频队列、锁、cv、router、计数提前；修正过时注释 | 保持TTSWorker先构造、后于LLMWorker析构，保证LLM完成回调还能提交TTS；ASR/VAD销毁更早；正常链路和Prompt不变 | **无SIGINT/SIGTERM处理**；VLM仍阻塞ASR；超时后的join无上限；done抛异常会漏计数 | A/L覆盖局部；整条链路、信号、SDK待板端 |
| `src/audio/asr_pipeline.cpp` | ASR析构只join，开放空队列可永等；重复start可terminate；识别/分配异常可穿出线程 | 移出AudioWorker；ASR析构先close再join；新增requestStop、runImpl；run捕获异常；start置started_ | close在mutex内设状态后notify_all；pop谓词保证空队列返回；残留段排空，活跃识别自然返回；无新增线程和队列策略 | drain不是cancel，析构可执行回调；queue必须活到join后；SDK卡住仍等；OOM导致catch内构造error再次失败仍不保证恢复 | A中的queue/idle/unwind/drain/start/fault；SDK本身不覆盖 |
| `src/audio/audio_worker.cpp` | 原类在Pipeline文件内直接依赖ALSA，妨碍隔离测试；入口无捕获、重复start无保护 | 原AudioWorker移到新文件；run/runImpl和started_ | 捕获异常后ok=false/error并close；原QueueCloser、AudioCapture局部RAII和采集算法不变；同一采集线程管理设备 | blocking read/recover无法被atomic强制中断；stop-before-start仍可能先open；生产者回归未被A覆盖 | 原采集算法逐字检查；真实ALSA/异常/重复start待板端 |
| `src/audio/tts_worker_smoke.cpp` | Worker析构可能晚于done_mutex/cv/结果 | main try-block；把状态提前 | Worker析构stop/join时捕获对象仍活；Service早于Worker构造 | 无本机真实TTS测试；同步合成/播放可阻塞join | 待板端tts_worker_smoke与完整链路 |
| `src/audio/vad_audio_worker.cpp` | start重复赋值线程；分配/VAD异常无统一边界 | start检查started_；run捕获；原算法放runImpl | 原VAD/PCM/分段/计时未变；runImpl退栈时VAD unique_ptr、AudioCapture和QueueCloser清理 | 采集阻塞不能强制取消；catch内内存分配风险；状态只能join后读 | 算法相等性；实际生产者路径待板端 |
| `tests/asr_pipeline_tests.cpp` | 缺少无SDK的真实队列/ASRWorker异常与析构测试 | 新增testQueue、testIdleDestructionAndUnwind、testDrainAndStartContract、testFailures；测试专用ASRService定义 | 只在A target链接替身，不进入audio产品库；替身返回测试转写；不伪造推理性能 | 调度没有穷尽；idle测试未给cv内部加测试钩子，不能宣称强制覆盖所有“已睡眠”交错 | A本机通过；不测Audio/VAD/ALSA或模型 |
| `tests/llm_worker_tests.cpp` | 原测试自身捕获状态晚于Worker；无chunk/done异常后存活测试 | 调整测试对象顺序；新增testCallbackExceptionsAndUnwind | 第一回调先set_value后抛异常，第二任务成功，退出作用域验证join；仍仅GatedLLM | **没有证明业务计数在回调抛出前总会更新**；没有真实RKLLM callback userdata测试 | L本机通过 |
| `tools/stage5_review.py` | 无Git仓库，需要可审查差异/版本指纹和完整附录 | 新脚本sha256/main；生成patch/manifest/源码附录/10项相等性检查 | 只在本地读快照、写报告，不联网或部署；源码检查与编译/硬件证据分离 | 不替代语义审查；初版不包含删除文件检测；脚本依赖原快照存在 | 本地实际执行、hash核验、git apply --check；本轮扩充脚本附录类型 |

### 原补丁中的文档文件（逐项）

这些文件都不包含运行中的类、函数或成员修改，不改变公开接口、线程、资源寿命，也不产生运行时竞态/重复释放；风险是版本或证据描述误导。因此以UTF-8读取、链接/代码块、源码hash及实际日志核对验证，不用CTest替代文档审查。

| 文件 | 原问题与本轮内容 | 正确性与未覆盖边界 |
|---|---|---|
| `config/README.md` | 只介绍文本CLI，容易误认为覆盖语音位置参数；补入口区别 | 仍无统一JSON配置；模型路径必须现场核实 |
| `docs/architecture.md` | 历史“真实后端未实现”已过时；加版本提示 | 保留历史正文，当前状态指向新审计文档 |
| `docs/run.md` | 历史开关ON必然失败的说明过时；加版本提示 | 原命令输出不改写为本轮证据 |
| `docs/stage5_01_architecture_audit.md` | 新增实际架构、生命周期、修改、测试范围和学习题 | 本轮补审查结论；板端段落原为模板，以本文经历史日志核对的路径为准 |
| `docs/stage5_01_source_appendix.md` | 新增完整当前源码附录 | 每份文件有路径/hash；不是硬件通过证明；本轮刷新为含准备工具的版本 |
| `docs/stage5_plan.md` | 新增5.1～5.5文件、风险、验收路线 | 本轮用户增加5.1实机门槛，优先于旧“下一步5.2”表述 |
| `docs/validation.md` | 早期记录不能表示当前后端未实现；加版本提示 | 不修改当年真实测试结论，不与本轮混合 |
| `README_STAGE5.txt` | 新增正式任务/文档/补丁/日志入口；保留旧功能补丁说明 | “完成本地改进”不代表5.1验收；新门槛须看本轮审查结论 |

## 操作 2：关键安全结论和验收缺口

### RKLLM 回调状态的完整寿命

Qwen backend没有在首轮修改。`RunContext context` 位于 inferStreaming 栈帧；`context.on_chunk` 指向传入的std::function引用；Worker的Task/问题/回调在调用期间仍存在。`is_async=false`配置为同步，正常路径必须由SDK保证run返回时不再使用userdata/输入。文本、failed、first_text由RunContext mutex保护；调用上层时不持有该mutex。Engine mutex仍在infer期间持有，因此禁止上层重入同一个Engine。

实际析构顺序是末尾lock_guard先解锁，再销毁context，再返回上层；不是先销毁userdata再等待SDK。**本机GatedLLM不测试SDK是否确实不发生晚回调**，该前提仍需板端SDK版本/头文件和运行日志核实。SmolVLM2的GenerationState同样在run栈帧内，但没有mutex；同步run并不能单独证明SDK内部多个回调不会同时写它，不能给出无竞态保证。

语音入口外层捕获对象的逆序退栈：VAD producer→ASR consumer（关闭并排空/join）→on_text/相机/VLM→LLMWorker→TTSWorker→锁/cv/计数→Services。完成回调只使用仍然活着的依赖。正常路径先停止上游再停止下游；停止时不持有回调需要的print/state mutex。owner必须串行start/join/destruction；禁止self-join。

### RKNN 输出各路径

| 路径 | owner动作 | 使用关系与证据 |
|---|---|---|
| inputs_set或run失败 | 尚无输出owner需要释放 | 不访问输出；原有返回错误 |
| outputs_get返回失败 | acquired=false，不调用release | 以SDK失败不转交输出所有权为前提；若SDK允许部分分配，需按真实SDK契约调整；本轮未验证 |
| get成功但null/size错误 | acquired=true，离开作用域release一次 | embeddings不用于后续RKLLM，返回错误 |
| get成功，assign抛异常 | 栈退栈release一次，Engine转换错误 | 无SDK本地故障注入证据，仅源码确认 |
| 含NaN/Inf | 深复制后校验失败，release后返回错误 | SDK指针不越过作用域 |
| 全部成功 | scope结束release一次，后续只用vector副本 | result引用/ptr都在内部作用域；vector活到同步rkllm_run返回 |
| release自己失败 | 返回值被忽略 | 不能宣称释放成功已确认，也缺少诊断；需真实SDK测试/后续日志改进 |

删除owner复制构造/赋值阻止重复所有权；没有保存释放后原始buf给RKLLM。Runtime句柄仍由backend PImpl释放，且Engine要求infer结束后才能shutdown。

### 异常是否被吞掉

- ASR/VAD/Audio入口将普通异常转为ok=false/error并close，join后读取；完整入口把producer/consumer.ok纳入最终判据，因此识别成功但业务回调失败不会仅凭processed计数误判成功。
- LLM chunk异常被atomic标记并转换为失败结果。LLM/TTS **on_done异常被吞掉且没有异常计数**：业务可能漏更新completed，main可等到180/600秒；之后join仍可能无界。L测试恰好先set_value再抛出，不能覆盖“抛出早于计数”的场景。
- bad_alloc在catch里构造error_时可能再次抛出；不是绝对OOM恢复保证。C ABI回调也不能让C++异常穿出；目前Qwen ERROR分支的mutex加锁在try外，极端system_error并无完整noexcept边界。
- 普通error返回的初始化清理按源码存在，但没有本轮SDK故障实测。没有把理论资源释放路径当成实际已执行。

### 重复启动和停止

ASR/Audio/VAD成功创建thread后才置started_=true；成功后再次start（包括join之后）抛logic_error，不覆盖线程，不重复open设备。线程创建本身失败时未置true，可在owner控制下重试。ASR requestStop关闭输入并排空，不可重新打开同一队列。Audio/VAD requestStop只置atomic，**在首次start之前调用stop，之后start仍可能先初始化模型/设备**；这一状态语义尚未统一，也没有生产者测试。普通结果getter不加锁，只允许join后读。

### Ctrl+C：明确未通过

完整语音入口当前没有协作信号处理，main直接producer.join。默认SIGINT终止不会保证执行C++析构；内核最终回收fd/进程内存不等同于应用执行stop/join/Runtime destroy。当前版本无法满足用户要求的“Ctrl+C正常停止”。本轮不隐蔽加入5.2架构改动；该项列为5.1验收阻塞，需后续小范围修复并重新审查/实机验证。

## 操作 3：两项新增 CTest 的实际含义

**asr_pipeline_tests**：新增的测试文件，直接编译生产asr_pipeline.cpp与audio_preprocessor.cpp，仅ASRService识别函数是测试替身。覆盖容量2丢最旧段和计数、close后拒绝输入/排空/EOF、空队列close和无生产者析构、owner异常退栈、Float32与S16两种输入、活动/已join后重复start、标准/未知服务异常、标准/未知业务回调异常、空音频拒绝。它不链接ALSA/VAD，不加载SenseVoice，不验证SDK线程/设备句柄。

**audio_preprocessor_tests**：原测试文件未新增算法，本次仅注册入CTest。验证-32768/-16384/0/16384/32767对应归一化值与样本数；拒绝48kHz、双声道、空输入，且失败时清空输出并给错误。没有实现/测试重采样或真实麦克风。

其余4项是原target；LLM测试增加chunk/done异常和退栈，Camera使用测试替身，core/CLI使用不可用后端。在ARM64三个真实开关均ON时，core/CLI不可用后端专用测试不注册，所以预计是**4个可移植CTest target**；这四个通过仍不算ASR/VLM/TTS实机闭环。

## 操作 4：本地准备包与板端目录边界

### 唯一写入范围（需用户批准后执行）

```text
/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/
  CMakeLists.txt, src/, include/, tests/, tools/, README_STAGE5.txt
  docs/stage5_01_board_review.md
  SOURCE_SHA256SUMS
  build/stage5_01_board/
  reports/stage5_01_board/
```

不覆盖 `/home/cat/projects/RK3576/rk3576_multimodal`，不替换其中 `build/stage5_full/asr_llm_tts_smoke`，不修改设备树/驱动/系统配置，不删除或复制已有模型。测试程序会实际打开麦克风/耳机/Camera/NPU；它们不能同时被原稳定程序占用。若有占用先报告，不擅自杀死其他进程。

本地 `python tools/stage5_prepare_board_bundle.py` 只产生源代码归档；**不会调用ssh/scp**。同步的精确逐文件列表、大小和SHA256见 `reports/stage5_01_local/board_package/bundle_manifest.json`。包含CMake及src/include/tests中全部需要的`.cpp/.h/.hpp/.cmake/.txt`，保证独立工程完整；包含board工具和本文，不包含ELF、模型、SDK、旧build或backups。用同一版本完整重编，避免新类布局与旧对象混用。

### 本轮新增准备工具的审查

| 文件 | 功能、接口及影响 | 本地检查与限制 |
|---|---|---|
| `tools/stage5_board_paths.sh` | 只读解析稳定CMake缓存和已知路径、依赖检查、稳定源码/程序hash；不写模型和配置 | Bash语法；实际路径/动态库存在性待板端 |
| `tools/stage5_board_preflight.sh` | SSH标准输入执行的只读脚本；不打开采集/播放设备 | Bash语法；尚未连接主机 |
| `tools/stage5_board_build.sh` | 仅规范化独立根目录运行；新build/log；保留原工程hash和退出码 | Bash语法；CMake/ldd/四项CTest待ARM64 |
| `tools/stage5_board_voice.sh` | 四个显式模式；只启动新程序；同名日志拒绝覆盖；前后稳定hash | Bash语法；实际设备和shell退出流程待板端 |
| `tools/stage5_board_capture.py` | 子进程采集、/proc统计、信号观测、看门狗；只允许固定独立exe；默认只打印计划，--execute才运行 | Python语法及合成输入解析/拒绝误判测试；没有实测子进程/设备行为 |
| `tools/stage5_prepare_board_bundle.py` | 本地源包、manifest、checksum；拒绝覆盖已有归档；不调用网络工具 | Python语法、成员筛选单测、归档成员/hash核验 |
| `tests/stage5_board_tools_tests.py` | 7项合成输入单测，验证解析判据/拒绝信号死亡假PASS/包排除规则 | 与原6项CTest分开记录；fixture不进入board报告 |
| `tools/stage5_review.py`（本轮增补） | 将新增.sh纳入差异及完整附录，使用bash代码块 | 本地执行及manifest/patch检查；生产源码相等性判据不变 |

这些工具不会改变产品公开接口、线程队列或资源所有权。子进程捕获器在未来获准运行时会新增一个观察进程及日志读取线程；它们只用于测试，不是5.2 Pipeline。看门狗仅针对自己启动的新测试进程组；错误和强制清理均明确记失败。

### 真实历史路径及现场确认

以下来自 `4.md` 成功命令，而不是此前文档的models/asr模板；当前板端存在性尚未读取：

| 用途 | 历史路径 |
|---|---|
| ASR目录 | `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17` |
| VAD | `/home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx` |
| Qwen | `/home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm` |
| Kokoro | `/home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1` |
| SmolVLM2 | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm` |
| Vision RKNN | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn` |
| sherpa SDK/runtime | `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu` |
| RKLLM SDK | `/home/cat/projects/RK3576/rkllm_sdk` |
| RKNN头文件/库 | `/home/cat/projects/RK3576/rknn_test/include`、`/usr/lib/librknnrt.so`（CMake默认，优先核对稳定build缓存） |

`stage5_board_paths.sh`优先读取原build缓存四项SDK路径；只读取字符串，不eval缓存。验证所有模型/词表/动态库/头文件可读；缺失就失败，不搜索后随意选择其他版本。`LD_LIBRARY_PATH`仅作用于当前脚本及子进程，不写profile、不运行ldconfig。设备历史为plughw:1,0和/dev/video11，预检列设备后必须核对实际卡号。

## 操作 5：申请批准后执行的完整步骤

**本节是此前执行方案，不是日志；上传、编译和硬件测试仍未执行。** 已通过获准的系统OpenSSH完成只读查询，当前连通性和路径见最新报告。分阶段授权优先：第二阶段不得直接调用下文会自动运行CTest的旧build脚本，应使用最新的`stage5_board_compile_only.sh`。

### A. 只读预检

Windows工作区执行：

```powershell
Get-Content -Raw -Encoding UTF8 tools/stage5_board_preflight.sh |
    ssh -T -o BatchMode=yes -o ConnectTimeout=5 cat@192.168.10.27 'bash -s' 2>&1 |
    Tee-Object -FilePath reports/stage5_01_board/preflight.log
$LASTEXITCODE
```

`-T`不分配TTY；BatchMode避免无人值守密码等待；ConnectTimeout仅限制连接阶段。ASCII shell脚本从标准输入交给bash，只读身份/工具/内存/磁盘/设备列表/原文件hash/缓存/模型metadata。设备列表不开始录音/采集。Tee仅写本地reports。检查返回码、aarch64、SDK版本/路径、可用内存及独立目标目录是否不存在；任何不符先报告，不继续上传。

### B. 创建新目录和上传（确认预检后）

```powershell
ssh -T cat@192.168.10.27 'set -eu; test ! -e /home/cat/projects/RK3576/rk3576_multimodal_stage5_review; mkdir /home/cat/projects/RK3576/rk3576_multimodal_stage5_review'
scp reports/stage5_01_local/board_package/stage5_01_review.tgz reports/stage5_01_local/board_package/stage5_01_review.tgz.sha256 cat@192.168.10.27:/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/
ssh -T cat@192.168.10.27 'set -eu; cd /home/cat/projects/RK3576/rk3576_multimodal_stage5_review; sha256sum -c stage5_01_review.tgz.sha256; tar -xzf stage5_01_review.tgz; sha256sum -c SOURCE_SHA256SUMS'
```

每行成功后才执行下一行，分别检查退出码并保存终端输出。`test ! -e`拒绝已存在目录，避免覆盖此前测试；`mkdir`没有-p，不复用旧目录；SCP只发送两个本地工件。先校验archive hash，再解压已在本地验证路径安全的成员；包不包含build/models等目录和符号链接。解压后逐文件核对。中途失败保留现场，不自动删除、不重用目录；需要时另选新名字并重审脚本。没有任何命令指向稳定工程写入。

### C. ARM64 构建和 CTest

```powershell
ssh -T cat@192.168.10.27 'bash /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_board_build.sh' 2>&1 |
    Tee-Object -FilePath reports/stage5_01_board/build_session.log
$LASTEXITCODE
```

脚本先核对自身规范化根目录、uname、稳定程序、包校验和，再写**独立build/report目录**。实际CMake命令为：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
source "$ROOT/tools/stage5_board_paths.sh"
cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
  -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" \
  -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"
cmake --build "$ROOT/build/stage5_01_board" --parallel 3
ctest --test-dir "$ROOT/build/stage5_01_board" --output-on-failure -V
```

`-S/-B`隔离源码和新构建树；三个真实开关开启实际SDK；SDK参数绝对路径避免独立目录相对引用出错；并行3限制编译资源，不修改模型线程配置。`-V`保留每个CTest输出；脚本使用pipefail和每步日志，退出trap保留真实退出码、原工程前后指纹与比较结果；`ldd`遇not found判失败。全部target构建，才能覆盖两个TTS smoke改用静态库后的链接。

### D. 完整语音回归与日志采集

登录开发板，在独立目录中顺序执行，一次只运行一个程序：

```bash
cd /home/cat/projects/RK3576/rk3576_multimodal_stage5_review
bash tools/stage5_board_voice.sh text text_01
bash tools/stage5_board_voice.sh vision vision_01
bash tools/stage5_board_voice.sh both mixed_01
```

text模式使用兼容旧argc，不加载VLM/Camera，问“你是谁”；vision模式用完整参数，问“前面有什么”；mixed模式至少一条TEXT和一条VISION，避免连续抢话造成队列饱和。每轮先等Listen再说话，记录本人是否确实听到声音。单独text/vision成功后才做mixed；自动程序计数通过不替代实听。

完整参数展开如下（与脚本一致）：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
source "$ROOT/tools/stage5_board_paths.sh"
"$ROOT/build/stage5_01_board/asr_llm_tts_smoke" \
  plughw:1,0 "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" \
  "$STAGE5_KOKORO" plughw:1,0 15 2 17 \
  "$STAGE5_VLM" "$STAGE5_VISION" /dev/video11
```

前6项为采集/ASR/VAD/Qwen/Kokoro/播放；15为录音秒数，2为TTS线程，17为音色；后三项为VLM语言模型、Vision编码模型、Camera。不改已验证Prompt和特殊token。

voice脚本调用 `stage5_board_capture.py --execute` 保存实际命令、二进制stdout/stderr合并原始流、每秒/proc的RSS/HWM/Threads/fd数量/task ID、退出码、错误行和分支统计。报告路径为独立工程 `reports/stage5_01_board/<RUN_NAME>/`。同名运行拒绝覆盖。正常回归必须退出0、程序PASS、无丢段、计数一致且覆盖所需分支；mixed必须同时TEXT和VISION成功。音频时长、模型延迟沿用真实日志，不填假指标。

300秒是测试看门狗，不是程序正常退出保证；到期向**本次启动的子进程组**发SIGTERM，15秒后仍不退出才SIGKILL，均标记失败。不能把看门狗清理说成正常stop/join，也不碰其他进程。

### E. 信号退出观测（当前版本预计不能验收）

```bash
bash tools/stage5_board_voice.sh sigint sigint_idle_01
```

该命令用120秒录音窗口，在Listen后2秒只向测试子进程组发送SIGINT，记录真实返回码和输出。由于当前没有协作handler，结果不能计为正常退出。`-2`、`130`、PID消失都不能单独算PASS。当前collector有意不给信号用例graceful通过，需完成生产代码小修并补可观测退出事件后再更新验收逻辑。

人工Ctrl+C应在真实交互SSH终端运行同一voice脚本，分别检查等待录音、推理/播放时的行为；collector只把信号转给它自己创建的子进程组。须记录信号发送时刻、退出耗时和阶段。当前版本不应把多按Ctrl+C或外部kill后退出当成正常释放。

## 操作 6：线程、释放、错误和稳定工程检查

### 活跃线程与资源

collector的resources.jsonl记录pid；另一终端对该pid只读执行：

```bash
ps -L -p "$pid" -o pid,tid,stat,wchan:32,comm
cat "/proc/$pid/status"
ls -l "/proc/$pid/fd"
```

`$pid`必须从当前报告读取，不随意选系统进程。观察等待线程与Runtime线程、RSS/HWM和fd是否异常增长；单次采样不证明泄漏。结束后PID不存在仅证明进程退出；还应检查无遗留子进程、设备可由下一轮重新打开、原稳定程序hash未变。

如板端已有strace且获准做额外观测，可对新可执行文件运行：

```bash
mkdir -p reports/stage5_01_board/cleanup_trace_01
strace -f -tt -yy -e trace=clone,exit,exit_group,close,munmap,ioctl \
  -o reports/stage5_01_board/cleanup_trace_01/cleanup.strace \
  ./build/stage5_01_board/asr_llm_tts_smoke \
  plughw:1,0 "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" "$STAGE5_KOKORO" \
  plughw:1,0 15 2 17 "$STAGE5_VLM" "$STAGE5_VISION" /dev/video11
```

source paths后执行；strace只附着本次新进程，跟随线程，显示时间和fd路径，关注join后STREAMOFF/close/munmap与正常exit；它会增加开销，不将trace轮用作性能基线。Runtime destroy不一定直接可见为一个系统调用，不能据系统调用日志虚构SDK函数执行事实。未安装则标未测，不在本轮安装系统软件。

### 非破坏性错误用例

在新目录，沿用上述参数数组，单独将ASR目录改为一个不存在目录，预期初始化诊断+退出1；将Camera参数改为 `/dev/stage5_review_missing_camera`，覆盖部分模型/Worker已加载后的Camera失败清理；将playback改为不存在的PCM名称，覆盖播放设备初始化失败。每轮保存原始输出、实际退出码和下一次正常启动是否成功，不拔设备、不篡改模型、不改系统ALSA配置。缺路径早退仅覆盖早期失败，不等同模型SDK加载中途失败；不要将预期退出1算成崩溃，也不要将无日志的死锁算成预期失败。

检查 `[Fatal]`、`[Timeout]`、`[ASR]`失败、LLM/VLM/TTS错误、XRUN、Segmentation fault、bad_alloc、OOM。voice脚本尝试只读保存dmesg；若权限不足，保存错误原文并标记内核日志未取得，不sudo、不更改dmesg限制。比较各轮日志，不凭一次PASS断言稳定。

### 日志回收

```powershell
scp -r cat@192.168.10.27:/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_01_board reports/stage5_01_board/collected
```

只下载独立目录日志；本地collected首次必须不存在，避免混入旧轮次。原始文件不改写，板端测试结果再写入validation_summary的独立board字段。当前本地board目录只有准备状态/说明，不存在冒充实测的terminal、build或性能数据。

## 操作 7：本轮通过项、未验证项与进入5.2条件

本轮【真实执行】Python准备工具语法检查退出0，工具单元测试7/7通过。Git Bash在沙箱内启动失败（`couldn't create signal pipe, Win32 error 5`）；按工具权限要求获准后，仅在沙箱外执行四个本地脚本各自的`bash -n`，四项均退出0。没有运行脚本正文，没有因此获得或使用任何开发板授权。collector默认dry-run输出`NOT_EXECUTED`，未启动Linux路径下的任何程序。

本轮新增工具的这些测试不是新增ARM64 CTest，也不能据此把原6/6的本机结果升级为板端通过。源包和新版patch另有本地hash/成员/可应用性核验日志；准备工具完整源代码已刷新到source appendix。

- 已通过（本地）：原补丁逐文件阅读、生产源码版本核对、原6项CTest证据复核；准备工具的Python语法、合成输入单元测试、Bash语法检查与源包成员/hash验证见本轮local日志。
- 尚未执行：SSH连通性、真实路径/SDK版本预检、隔离上传、ARM64编译/链接、板端CTest、普通/视觉语音实听回归、线程退出/释放与资源曲线、错误恢复。
- 源码确认的验收缺口：完整语音入口无协作SIGINT；Runtime卡住的join仍无硬上限；完成回调异常缺少上层可靠报告；SDK回调和输出失败所有权契约仍待核对。
- 结论：**5.1仅本地部分通过，不具备宣布5.1验收完成或进入大规模5.2修改的条件。** 先获得用户对上述范围的明确批准，执行只读预检和隔离回归，修复5.1退出等必要缺口并重新验收。最终通过必须以真实板端日志和用户实听记录为依据。
