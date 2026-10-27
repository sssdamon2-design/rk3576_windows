# 5.4 关键源码逐句说明与生命周期审查

本文与 [完整前后源码附录](stage5_04_source_appendix.md)、[性能报告](stage5_04_performance_profiling.md) 配套。附录从实际文件导出，不用伪代码替代生产入口。这里解释新增语句的语法、调用次序及边界；既有大段设备初始化和模型参数沿用 5.1～5.3。

## 操作 1：统一时钟、日志与请求所有权

`include/common/image_profile.h` 继续使用原来的单例、文件和互斥锁。`using Clock=std::chrono::steady_clock` 是类型别名，时间不随系统校时跳变。`time_since_epoch()` 仅供同一进程内相减，不解释为 UTC。`duration_cast<nanoseconds>` 后输出整数，分析器先做整数相减再转毫秒，避免大绝对值浮点数抵消。

`inline thread_local std::uint64_t image_profile_request_id=0` 为每个线程保存独立的请求编号；`inline` 允许头文件被多个翻译单元包含。它不是共享状态，不需要互斥。SDK 自建回调线程不会自动继承这个值，必须显式传 `RequestTracePtr`。

构造函数先查 `STAGE5_PROFILE`，不存在才查旧的 `STAGE5_IMAGE_PROFILE`。`background_=path==nullptr` 在回退前求值：旧图像诊断仍保留背景 Camera 采样；新请求诊断省去没有请求关联的每帧日志，避免每秒数百条日志干扰 CPU。它没有关闭 Camera 或改变帧池。

`request(id,event,at,value)` 在锁外把时点转成整数，在 `lock_guard` 作用域内写一整行再 flush。`request_id` 和图像样本的 `id` 分开：一次请求可以使用一帧，多次请求也可以使用同一帧。`value` 供队列深度、路由或样本数使用，不混作时间。事件名来自编译期常量，不接收未经转义的用户文本。

`enabled_`、`background_` 在单例构造后只读；`failed_` 和文件写入受同一把锁保护。写失败显式打印 ERROR，不编造零耗时；它是诊断失败，验收脚本将其列为失败条件。捕获异常避免诊断代码跨 SDK C 回调传播。日志 I/O 会影响相邻区间，微秒级 router 数据是带埋点的墙钟区间，并非无扰动纯计算时间。

`include/common/request_trace.h` 的 `RequestTrace` 只有不可变 ID，没有可变阶段表。`makeRequestTrace` 仅在诊断启用时分配一个控制块；没有中央 map 永久保留请求。`shared_ptr` 使音频段、排队任务和完成回调各持有自己的强引用，最后一个持有者释放时自动销毁。

`currentRequestTrace()` 返回函数局部 `thread_local shared_ptr` 的引用。首次实现用头文件中的 inline TLS shared_ptr，在 MinGW 链接时出现初始化符号重复；改为 accessor 后本地构建通过，原失败日志保留。ARM64 另行构建验证，不能从 Windows 结果推断。

`RequestTraceScope` 构造时 `std::move` 取走原 TLS 引用，设置本次引用和数字 ID；析构时恢复上一层。移动 shared_ptr 转移引用，不复制请求对象。禁止复制 scope，防止两次恢复。嵌套同步调用和异常展开均按栈次序恢复；回调需要跨线程时显式捕获 shared_ptr，不能捕获 scope 的地址。

## 操作 2：沿已有队列传递上下文

`include/common/work_control.h` 给 `TaskOptions` 增加 `RequestTracePtr trace`，未改变 `deadline`、`max_queue_wait`、原子取消标志或 disposition 优先级。`PipelineAdmission::Ticket::options(max_wait,trace={})` 的第二参数有默认值，旧调用仍有效；`std::move(trace)` 转移本次局部引用，票据的 deadline/cancelled 仍共享原状态。

`AudioSegment` 增加同类型成员。音频 vector 的所有权仍随原队列移动，不为埋点再复制音频。`AudioBufferQueue::push` 先保留一个 trace 引用和实际 enqueued_at；队列关闭时记拒绝，满载覆盖最旧段前记被替换请求。成功 push 仍在同一队列锁下，日志和唤醒沿原流程；分析按时间戳而非文件行出现顺序排序，因为出队线程可能先写日志。

`ASRWorker` 新增可选 `ContextCallback(text,const AudioSegment&)`，原 TextCallback 和原构造调用保留。若提供 context callback 就只调用它，避免一次识别发出两次业务请求。`const AudioSegment&` 只在同步 callback 执行期间有效；入口只复制 trace 引用，不保存 segment 引用，也不保存 samples 裸指针。

出队后创建 `RequestTraceScope(segment.trace)`，随后记 dequeue、ASR begin/end，并包住原业务 callback。原音频预处理、识别参数及队列关闭逻辑保留。ASRService 内部 stream 创建、AcceptWaveform、Decode 另设标记：外层 API 时间包含这些步骤及文本取回，Decode 区间也不是纯 ONNX 算子时间。

LLMWorker 和 TTSWorker 从既有 `TaskOptions` 取上下文。记录成功入队时的等待队列深度、真正出队、服务开始及终态；取消和过期在原 disposition 分支记录。工作函数在队列锁外执行，未把模型推理搬入队列临界区。拒绝路径记明确事件，原统计和终态 callback 仍执行。

循环末尾 `task=Task{}` 释放 inference/done 捕获的票据、上下文和其他对象；scope 的额外引用在本次循环离开时释放。测试通过 weak_ptr 检查 joined 后不再持有上下文。新增的唯一动态对象受原有界队列与在途上限约束，没有无界增长容器。

## 操作 3：VAD 时间的真实意义

`VadAudioWorker` 每次喂入原 512 样本窗口后观察 SDK 的 detected 状态，记录上升沿的主机 steady 时点。确认完整 segment 可取时，先记录 endpoint，再复制原有 pre-roll 和语音数据。segment 创建后才有 sequence，因此用 `trace->mark(event, earlier_time)` 回填已观察到的时点，而不是重新调用 now 冒充起点。

`audio_start_estimated` 和 `audio_end_estimated` 用最后一次 read 完成时点与采样索引差回推。只沿用原有无 XRUN/suspend 的 timing_valid 条件；不是声卡 ADC 时间戳，也不是精确人声起止。检测起点、估算起点和预滚起点分别解释，不能相互代替。

可选 `STAGE5_CAPTURE_AUDIO_FIXTURES` 只在专用测试打开，复制完 VAD 段后写出自有 float 样本及元数据。开始/结束独立计时；写文件会增加 vad_to_queue 和整请求延迟。报告区分留存语音的自然基线与不写 fixture 的后续测量，不拿这点额外 I/O 伪造加速。

## 操作 4：RKLLM callback 和 VLM 状态

Qwen 的 `RunContext` 增加 shared_ptr，在同步 `rkllm_run` 前复制当前上下文。原 mutex 保护 text、failed、first_text_ms。首次非空 chunk 时记录同一个 now；SDK callback 借用的 `result->text` 仍复制进 string，不能保留该指针。

SmolVLM2 的 `GenerationState` 增加 mutex、decoder_start、first_text_ms 和 trace。callback 的所有状态读取/写入置于 `lock_guard` 内；异常展开先销毁 guard，再进入 catch 重新加锁置 failed，避免同线程重复锁。同步 run 返回后主线程先记 decoder_end，再锁 state 检查 finished/failed/text 并移动文本。

state 仍为同步调用栈上的对象，SDK 参数保持 `is_async=false`。run 返回并确认回调结束之前 state 不析构；destroy 仍在 Worker join 之后。若未来换为异步 SDK，必须重审这一契约，不能照搬栈对象。

首回调是“首个非空文本 chunk”，可能包含多个 token；不宣称精确 token 级 TTFT。VISION 的 inference_begin 到首 chunk 包含预处理、RKNN 和语言 decoder；decoder_begin 到首 chunk 只含语言阶段，二者不混用。5.3 的 RGB/Embedding 缓存、输出 RAII、输入转换及固定英文视觉问题全部保留。

## 操作 5：TTS 和 ALSA 的测量边界

`TTSService::initialize` 仍仅启动时创建一次 SDK 对象。候选把默认 num_threads 从 2 改为 4，命令行显式传 2 可回退；speaker、speed、silence_scale、模型和 provider 的生产默认均未改变。没有新增 TTS 合成线程，也没有自动裁剪答案。

`AudioProgress` 持有 trace 与原子 seen 标记。首个 `n>0 && samples!=nullptr` 回调只记录时间和长度，始终返回 1；不持有 SDK 借用 PCM 指针，不在回调播放，不在回调停止或截断生成。`GenerateWithConfig` 是同步调用，progress 活到调用返回。

`AudioOwner` 仍用 unique_ptr 和 sherpa 删除器托管返回音频。无效输出直接失败，PCM vector::assign 异常返回明确错误，owner 随作用域释放，成功也先复制再释放。分别记录 SDK Generate、应用 PCM copy、完整自有音频 ready。callback 给出第一批音频可用时间，但当前播放路径仍等待整个 Generate 返回；不能把 callback 时间当首个 ALSA 提交时间。

诊断开关 `STAGE5_TTS_ORT_PROFILE_CONFIG` 只用于独立 ORT 实验；配置必须存在，所有输出位于新报告目录。它不是生产默认配置，也不进入主公平对照。ORT model_run 能看到模型会话区间，API 减去 model_run 的剩余值包含文本前端、输出处理、调度及诊断开销，不能直接命名为“纯音素化时间”。

ALSA 沿原 float→S16 转换和写入循环。对首次成功 writei 保存“调用前”时点和成功返回时点；只有 written>0 才记首次提交，错误返回不冒充已提交。全段 writei 完成后的旧 `[ALSA write]` 日志仍保留，但不用于首次提交指标。

`snd_pcm_drain` 前后另记事件。`alsa_drain_complete` 表示驱动/ALSA 排空语义，不是麦克风测到的实际声学尾音。buffer=12000、period=3000、start_threshold=6000 的现有配置不改；首次 write 成功也不代表耳机那一刻已经发声。

## 操作 6：固定输入、回放与信号等待

`include/app/profiling_inputs.h` 仅在显式测试环境变量启用。NV12 元数据检查非零偶数尺寸、stride≥width、上限、最少 NV12 字节数及文件长度，再读入自有 ImageFrame。没有伪造 received_at，所以固定帧 Frame Age 不可用。该强引用在入口作用域活到异步 Worker join 之后，后台 Camera 的 V4L2 重用不会覆盖这个独立 vector。

音频加载限制 16kHz 单声道 float、最长 16 秒、字节数整除 sizeof(float)，并逐样本检查有限数和范围。部署机 ARM64/Windows 均为小端，文件声明 f32le；不能把其他编码直接送入此接口。fixture 写入拒绝已存在的相同 ID 文件。它用于当前受控新建目录，不是面向不可信并发写者的通用存储服务。

完整入口的 `on_text(recognized,supplied_trace={})` 在路由前继承 ASR ID。原文本回放没有 trace 时仍分配 next_id。音频回放生产者使用独立 `audio_replay_sequence`，不与 ASR callback 线程同时修改 next_id，避免新数据竞争。

`STAGE5_REPLAY_AUDIO_FILE` 走原 ASRWorker、IntentRouter、InferenceWorker、TTSWorker 和真实 ALSA；绕过麦克风与 VAD，必须在输出和报告中注明。固定帧只允许与显式回放和 VISION 一起使用，普通自然语音仍取最新 Camera 帧。

原文本回放等待使用 sleep_until，长达 100 秒的未来输入会推迟信号响应。候选改为每 20ms 检查既有 StopSignals，再处理原定时刻；没有在信号 handler 做锁、iostream、join 或 destroy。main 退出仍先停生产者/ASR，再排空或取消推理，join 后释放 Qwen，再完成/取消 TTS，最后关闭播放、Camera 与 VLM。取消只作用未开始任务，正在执行的 SDK 调用仍等待其返回；有限超时由测试守护独立记录，强制终止不能算优雅退出。

## 操作 7：验证如何覆盖这些语句

- request_profile_tests：同一 request_id、不同 frame_id、跨真实 std::thread 的显式回调、TLS 恢复、JSONL flush；固定 PCM roundtrip、NaN 拒绝、覆盖拒绝、NV12 stride 检查及无伪造采集时间。
- async_pipeline_tests：保留原满载/取消/到期/交替任务/停止重启测试，增加 trace 在推理、完成回调、Fake TTS、ASR context callback 间传递及 weak_ptr 最终释放。
- image_pipeline_tests/camera_service_tests：继续验证 5.3 Buffer 所有权、复用与并发读取；使用 Fake，不能当真实摄像头或 NPU 结果。
- 独立手动 benchmark：原 SDK 的真实 ASR/VLM/TTS，固定输入、warm-up 和 CSV；不注册为自动 CTest，避免普通 ctest 隐式占硬件或运行数十分钟。
- 板端完整入口：真实设备释放、信号、排空/取消、队列过期与拒绝；自然语音的耳机效果由当前用户确认，不由 success=true 推断。

测试逐项结果、退出码和剩余边界见主报告及 validation_summary.json。没有 ASan/TSan/Valgrind 的全进程硬件证明，不把本轮有限回归写成任意运行时长下绝无泄漏。

## 操作 8：手动 benchmark、CMake 与分析脚本

`stage5_04_tts_bench.cpp` 的 argv 长度必须为5，包括程序名；stoi 后限制线程1～8、有效重复1～64。initialize 在循环外调用一次；双层循环外层 iteration，内层中文/英文，顺序固定。iteration0 与1分别记录 first_use/warmup，剩余 N 才是 measured。`TTSAudio` 每轮为局部对象，合成返回后按实际样本数/采样率求音频秒数；RTF 使用毫秒除以音频秒数×1000。逐样本检查 finite、abs最大值、平方和均方根和逐字节FNV，不能由hash不同直接推断退化。仅首个 measured 保存实际PCM，其余仍逐行flush CSV。

`stage5_04_asr_bench.cpp` 用 SDK Wave 读取器和自定义删除器持有固定16kHz单声道输入，同一 ASRService 循环使用，保存识别文本并检查一致。wall 包含调用外层开销，ASR API时间来自原服务内部。CSV helper 将引号变为双引号，符合CSV约定，不用C++ quoted的反斜杠逃逸冒充CSV。

`stage5_04_vision_bench.cpp` 启动时加载三个固定NV12自有帧，循环 `i%3` 选择fixture，避免每轮读盘混进模型耗时。2轮初始调用后30个样本，恰好每fixture10个；这不代表每张图都独立做两次预热。真实VLMEngine和既有模型路径保持。输入RGB和64×576 float输出可选保存，文件以递增sample编号命名，重复使用frame_id不会覆盖其他样本。

CMake 复用 multimodal_core/audio/tts 及现有SDK传递依赖；target_link_libraries PRIVATE表示仅该手动程序使用依赖，原库的PUBLIC头文件/链接传播仍保留。TTS target 的 STAGE5_BENCH_TRACE=1 只启用诊断探针的上下文，不改变库的模型参数。手动探针只 add_executable，不 add_test，因此 ctest 不会隐式占用麦克风、Camera/NPU或运行30轮大模型。request_profile_tests 才注册为带超时的确定性测试。

`stage5_04_prepare.py` 把实际字节和SHA放入payload，源目录/快照必须不存在。先从冻结5.3副本复制，再逐项核对before哈希后覆盖**新的本节副本**；不会覆盖已验收路径。revision支持v1/v2/v3，旧产物全保留。baseline v2仅把默认线程退回2，其他测量路径保持同源。每个构建step记录argv/stdout/stderr/退出码/磁盘采样；余量低于500MiB或超时才终止本次新建编译进程组。

`stage5_04_run.py` 和 voice_run 逐次发现HyperX，查询四个实际设备节点是否空闲。采样器只读/proc和sysfs，CLK_TCK来自sysconf。设备权限不靠更改系统配置；sudo仅只读fuser。每个case目录独占创建。信号守护核对exe和/proc启动token后只对本次PID发信号，异常强杀单独标失败。voice_run 的SSH传输成功与child.returncode分别记录，不相互覆盖。

`stage5_04_analyze.py` 先按case+request_id关联事件，再以整数纳秒差求毫秒；按语言、fixture、phase、route、status分组，缺少事件保持None。quantile采用nearest-rank，不对稀疏失败样本补零。资源统计分别保存CPU单核口径、RSS/HWM、频率和原始NPU字符串；不能靠读到100就声称硬件满载。ORT诊断是另一case，算子dur之和不等同总墙钟。

`stage5_04_plot.py` 从原始统计绘制散点/箱线、RTF经验CDF、CPU曲线/RSS及请求阶段分解，写PNG/SVG可分享文件；不用虚构平滑采样。Gantt各请求从各自首次事件归零，图题明确这不是所有请求共享的全局起点。

## 操作 9：最终音频回放错误检查的最小修正

文本回放原本不启动 ASR，因此旧 `replay_mode || consumer.ok()` 的意图成立；加入真实音频回放后不能继续对所有replay跳过ASR状态。v3把通过条件改为 `replay_mode ? (!audio_replay_path || consumer.ok()) : (producer.ok() && consumer.ok())`：文本回放仍免检查，音频回放必须consumer.ok，自然语音同时检查生产者/消费者。对应错误输出条件也加入audio_replay_path。

这只修复新测试入口可能出现的假阳性，不改变正常识别、模型调用或队列。之前有效输入v2的性能证据保持有效，但不能冒称v3执行；最终自然语音、信号和完整构建另用v3复测。未对真实SDK注入所有内部故障，故不宣称所有错误路径已实机覆盖。
