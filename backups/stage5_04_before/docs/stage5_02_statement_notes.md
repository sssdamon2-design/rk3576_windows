# 5.2 关键语句解释与接口审查

本文件与 `stage5_02_source_appendix.md` 配套：附录给出未经省略的当前完整文件及 SHA256；此处按实际语句执行顺序解释。一个跨多行的 `std::cout << ...;` 是一条表达式语句，不把每个输出操作误当独立控制流程。

## 操作 1：公共类型与 C++ 语法

- `#pragma once` 避免头文件在一个翻译单元中重复展开。`#include` 引入类型声明，不初始化设备。`std::` 指标准库 namespace，例如 `std::chrono::steady_clock` 属于嵌套 namespace；不是项目自建时钟。
- `enum class StopMode` 是强类型枚举，必须写 `StopMode::Drain`，避免与其他整数/枚举意外混用。`TaskDisposition` 的 Completed 表示执行路径正常进入，是否业务成功仍由 result.success 判断。
- `dispositionName(...) noexcept` 返回静态字符串字面量，生命周期覆盖整个进程，不返回局部 string.c_str()。嵌套条件表达式只选择三个固定名字。
- `using Clock=std::chrono::steady_clock` 是类型别名，不建立时钟对象。steady_clock 单调递增，适合等待和期限，系统校时不会改变结果。
- `Clock::time_point deadline=...::max()` 与 `milliseconds::max()` 表示默认不启用该限制。`milliseconds` 是 duration 的类型别名，实际模板包含计数表示类型和 `std::ratio<1,1000>` 周期。
- `std::shared_ptr<std::atomic<bool>> cancelled` 共享取消位的所有权。atomic 的 load/store 默认顺序一致性，保证主线程与 Worker 对标志的访问没有数据竞争；它不使其他对象自动线程安全。
- `disposition(enqueued,now,stopping) const noexcept` 不改变选项本身。先判停止/取消，再判 deadline 或 queue wait；因此同时发生时取消优先。短路 `&&` 在指针为空时不会解引用，毫秒最大值先判断再比较，避免不必要换算。
- `WorkerStats` 的 `{}` 和成员 `=0` 提供确定初始值；generation 区分显式重启轮次。size_t 是无符号容器计数类型，uint64_t 是固定宽度请求/轮次编号。统计只由 Worker mutex 保护，不能绕过 stats() 读成员。

## 操作 2：PipelineAdmission 逐句所有权解释

- `struct State;` 在类开头前置声明私有内部类型，使 Ticket 能先声明 `shared_ptr<State>`。完整 State 定义随后出现；没有在不完整类型上调用 sizeof 或 delete。
- `Stats` 为快照值类型，不包含 mutex。`class Ticket` 内 `friend class PipelineAdmission` 只允许外层类调用私有构造器，不把构造权限交给调用者。
- Ticket 构造器初始化列表按成员声明顺序建立 state、id、deadline 和新 atomic flag。`std::move(state)` 转移参数中的 shared_ptr 所有权，不移动底层 State 对象。
- `options(max_wait)` 创建独立 TaskOptions，把同一个 deadline 和 shared flag 复制到下游，允许不同阶段使用不同 max_queue_wait。它不把 Ticket 本身放进 flag，避免所有权环。
- `cancelled() const noexcept` 只读取 atomic，不锁 Admission mutex。调用者必须持有 Ticket，才能保证 flag 存活。
- Admission 构造器先 make_shared<State>(capacity) 建立状态，再检查 capacity 是否为零；抛 invalid_argument 时已经构造的 shared_ptr 自动析构，不泄漏。
- `tryAcquire` 的 `lock_guard<std::mutex> lock(state_->mutex)` 在构造时调用 mutex.lock()，离开块或异常退栈时析构调用 unlock()。模板参数 mutex 指定可锁对象类型，局部变量 lock 承担 RAII，不应误写成无名临时对象。
- closed、inflight>=capacity、tickets.count(id) 在同一临界区检查，拒绝时只增 rejected 并返回空 shared_ptr。重复 ID 不会覆盖已有取消标记。
- `shared_ptr<Ticket>(new Ticket(...))` 使用私有构造器，分配/控制块失败会释放已分配对象。此时 admitted_=false，因此析构不会错误扣减计数。
- `tickets.emplace(id,ticket->cancelled_)` 在所有 accepted/inflight 更新之前插入 weak flag，若 map 分配异常，Ticket 尚未计入额度，析构不会再次获取 State mutex。
- `admitted_=true` 后才增加 accepted/inflight 和 peak。`std::max` 比较历史峰值与当前在途数，不表示队列等待长度。成功返回前 lock_guard 已释放锁。
- `cancel(id)` 同锁查 map；找不到返回 false。weak_ptr.lock() 建立 flag 的临时强引用，存在时 atomic.store(true)。临时销毁的是 atomic flag 引用，不是 Ticket，因此不会锁内递归触发 Ticket 析构。
- `close(cancel_waiting)` 先设置 closed，拒绝此后新请求；若取消则逐个设置仍存活 flag。Drain 调用 close(false) 保留已有任务状态。
- `stats() const` 通过 shared State mutex 保护并按值返回快照，调用者不会持锁遍历生产对象。
- State 的 shared_ptr 由 Admission 和所有 Ticket 共享，Ticket 即使晚于 Admission 对象销毁，State mutex 仍存在。map 保存弱引用，既不保活 Ticket，也不形成循环。
- `Ticket::~Ticket()` 只有 admitted_ 为真时才锁状态、减 inflight、erase(id)。最后引用可来自推理或 TTS closure；Worker 在队列锁之外清除 closure，避免双锁反向依赖。

## 操作 3：LLMWorker 的构造、提交与线程语句

- 带 Engine 构造器委托给容量构造器，再保存非拥有指针 `engine_=&engine`。别名 `InferenceWorker=LLMWorker` 没有新对象布局和新队列。容量零抛 invalid_argument。
- 析构器依次 requestStop()、join()，不能由自身回调销毁 Worker。Engine、callback 引用和同步对象均必须晚于 join 才销毁。
- start 在 mutex 内清理 error、检查 started/stop_requested；创建 `std::thread(&LLMWorker::run,this)` 将成员函数指针和对象地址传给新线程。新线程需要同锁，直到创建者设置 started/generation 并解锁后才能操作队列。
- thread 创建异常被转换为 error + false，没有假装线程已启动。restart 在同锁检查已停止、已 join、队列空，重置本轮状态再调用 start；这依赖 start/join/restart 由同一 owner 串行执行。
- submit(text) 检查 engine_，无 Engine 的通用 Worker 不允许错误调用 TEXT 便捷接口。lambda `[this,question=std::move(question)]` 捕获 Worker 地址与自有文本，调用已有 inferStreaming；不引用提交栈上的 question。
- submitTask 检查 inference 非空；锁内检查 running/容量，分别增加 stopped/full 拒绝计数。创建 Task，移动函数对象和回调、写 enqueue 时间和 options，再 push_back。push 成功后增加 accepted/peak；异常前不虚增 accepted。
- 解锁后 notify_one，减少被唤醒线程立即争锁。通知不是条件本身；即使 notify 早于 wait，队列谓词仍可防丢唤醒。
- requestStop 在锁内设置 stop_requested。已经取消后不允许 Drain 降级回排空；随后 notify_all 唤醒空队列等待。该 noexcept 函数仍依赖有效 mutex，不可放进异步 signal handler。
- join 只在 joinable 时等待，不能同时由两个 owner 调用。stats/pendingCount/rejectedCount 都在锁内读取；stats 按值返回，并用当前 deque.size() 更新 pending。
- waitIdleFor 使用 unique_lock，因为 condition_variable 在等待时必须暂时解锁、醒来重新加锁。谓词要求 pending.empty 且 active==0，虚假唤醒不会提前成功。

## 操作 4：推理 run 循环的每个执行阶段

1. 每轮创建局部 Task 和 cancel 标记。unique_lock 后 wait(stop||非空)。空且 stop 时 return；否则 move 队首并 pop，设置 active=1，在同锁读本轮停止模式。
2. begin-enqueued_at 转为 `duration<double,std::milli>` 得毫秒浮点等待时间；TaskOptions 根据队列时刻、当前时刻、stop 决定终态。
3. 取消/过期路径只填 error_message、输出 ID/queue_ms，不执行推理体。它们仍走后面的 done 和统计，不能静默丢失。
4. 可执行路径先增加 started。局部 atomic chunk_failed 供 SDK 回调报告用户 chunk 异常；回调 lambda 引用本轮 Task 和 flag，只在同步 inferStreaming 有效期内使用。
5. task.inference 返回 InferenceResult。std::exception 和未知异常都转为 success=false、清空 text 并记录原因，防止半段答案被当完整成功结果。chunk 回调异常同样使本次失败，不让异常穿过 C SDK 边界。
6. service 计时在 done 之前截止，因此表示任务体及必要包装耗时，不包括业务 done 的转交时间。waitIdle 则包含 done 完成，不会用这两种口径混称同一指标。
7. done 在队列锁外调用。Cancelled 为兼容旧接口传 -1 等待值；统计保留实际等待。done 抛异常单独计 callback_errors 并打印 ID，继续清理，不吞成成功。
8. failed 仅对真实执行且 result.success=false 计入。`task=Task{}` 在队列锁外清空函数对象及 Ticket 捕获；随后锁内增加 completed、归零 active、累积失败/取消/过期/回调异常/等待和服务时间。最后 notify_all 允许主线程观察完整终态。

## 操作 5：TTSWorker 及不变的设备路径

TTSWorker 的 start/submit/stop/stats/waitIdle/restart 与推理 Worker 的锁和谓词相同，但 start 先检查 tts.ready 与 playback.ready。它借用两个 Service，仍不拥有设备。

run 将队首 Task move 到局部，锁外判取消/过期。执行分支先增加 started，调用原 `tts_.synthesize(task.text,audio,error)`；失败填合成错误，成功仍验证 sample_rate>0 和 samples 非空。audio 是局部 TTSAudio，vector<float> 自动释放 PCM。

随后保存 synthesis_ms、sample_rate、audio_seconds，读取 XRUN 基线，记录 play_start，调用原 `playback_.play(audio.samples.data(),audio.samples.size(),error)`。data() 的借用指针只在同步 play 期间有效，audio 作用域覆盖该调用。play_end-play_start 转毫秒，XRUN 用调用前后计数差。写失败、XRUN 非零分别填错误；只有两者都正常才 success=true。

完成回调在锁外执行并捕获异常。service 和 waited 分别累计；与推理 Worker 一样，先清除 task 再发布 active=0。过期/取消时 synthesis_ms/playback_ms 保持默认零，不伪造模型执行。

TTS/ALSA 公共头改为不完整 C 类型指针，只需声明就能存储指针；具体 SDK include 在 cpp 中，析构器也在 cpp 中实现。`tts_smoke.cpp` 自己调用 SherpaOnnxWriteWave，因此必须自己 include C API；这是首次 ARM64 编译暴露并修复的具体依赖。

## 操作 6：完整语音入口的语句与捕获

初始化顺序继承 5.1：StopSignals 在 SDK 线程之前阻塞信号；初始化 Qwen、SenseVoice、Kokoro、ALSA，然后建立状态/互斥量/Admission/帧缓冲与 Worker。VLM/Camera 指针声明提前，但模型初始化步骤不变。异常反向析构先停止借用它们的 Worker。

每次 on_text 创建 DispatchTimer，router.route 产生 RouteDecision，next_id++ 分配唯一 ID，tryAcquire 申请 Ticket。额度失败增加 pipeline_rejected、打印 route/limit 并 return；局部计时析构仍输出本次提交耗时。计时包含同步日志开销，不是纯 CPU 指令耗时。

VISION 禁用时保持原 skipped 行为。启用时保留英文短问句，submitTask 的 `[&,vlm_question]` 按值保留问题，只按引用借用 owner 的 vlm/frames。执行时 frames.getLatest() 返回有所有权的共享帧；infer 同步结束后才释放局部帧，不捕获 ASR 的 recognized 引用。

VISION done 按值捕获 question_at 和 ticket，先在 state_mutex 下更新 completed/成功/失败/取消/过期，再单独在 print_mutex 下输出。没有同时持 state_mutex 和 print_mutex。成功非空但 ticket 已取消时只记 downstream_cancelled；未取消才向 TTS 提交，TTS done 再按值持 Ticket。submit 返回 Accepted 后计业务 accepted；失败路径记录，不泄漏额度。

TEXT 分支复用原 prompt。prefix_printed 为每请求 shared_ptr<bool>，所有流式和 done 对它的访问由 print_mutex 保护。问题和时间不是借用提交栈。TEXT done 依据 disposition 区分运行错误与取消/过期，成功答案交给已有 TTSWorker；下游捕获同一 Ticket 和原始时刻，用 steady_clock 计算 ASR 文本至播放结束时间。

原 ASRWorker 和 VAD 模型处理保持。仅测试环境指定 STAGE5_REPLAY_FILE 时，显式打印 NO_MICROPHONE_ASR_OR_VAD_INFERENCE，按 TSV 绝对偏移 sleep_until 后调用同一个 on_text；不启动生产者/识别者，也不把其 ok 计作通过。正常麦克风路径仍启动 consumer、producer，20ms 轮询完成/信号，停止捕获后 join 二者。

ASR join 后关闭 Admission，禁止再提交。wait_for_jobs 用 Worker waitIdleFor(100ms)，不是 accepted/completed 业务条件变量。CancelPending 信号设置所有 Ticket 标志并停止接收推理；TTS 当前执行不受强制打断。等待期限到只报告失败，后续 join 仍需 SDK 协作，外层测试保护负责记录无限等待风险。

推理 join 后才 shutdown Qwen，TTS join 后才 close playback 和 shutdown TTS，Camera stop 后才 VLM shutdown。最后输出每级统计。passed 检查资源计数、终态完整、零运行/回调错误和零额度泄漏；允许有显式策略拒绝/过期，所以 PASS 是调度一致性结果，完整回答率要另看 successful。

## 操作 7：测试语句及可证明范围

Gate 使用 promise/shared_future：entered 通知任务已进入，release 阻塞执行直到测试主动释放，不用碰运气的 sleep 模拟重推理。OpenOnExit 在测试抛异常时释放 gate，避免析构 Worker join 死锁。ASR 测试用真实 ASRWorker/AudioBufferQueue 加 Fake recognize，第一推理阻塞时断言三段都已识别提交，随后检查 FIFO 和不同线程 ID。

满载测试容量一，先闸住活动任务，第二入队，第三必须 QueueFull；取消 flag 后断言第二执行体绝不调用。过期 deadline 在过去，同样不得执行任务体，但都要完成终态回调。restart 检查 generation=2；throwing done 必须 callback_errors=1 且 waitIdle 成功。

停止模式分别验证 Drain 执行两项、CancelPending 只执行活动一项且两项都有终态。Admission 检查总额度、按 ID 取消、归还和关闭，再运行 200 轮末引用释放与 close 竞争。Fake TTS 模拟同步 synth/play、队列满和过期/重启。它们证明指定并发交错，不证明真实 Runtime 无内部问题，也不是模型质量测试。

## 操作 8：面试题与参考答案

1. 为什么两个 Engine 各自 mutex 还不能证明 NPU 并行安全？锁的互斥域不同，共用 Runtime/driver 资源仍可能争用。本项目先实测调用重叠代价，再用一个消费者统一调度，不声称已证明并行崩溃。
2. 队列有界为什么还会积压？局部容量不包含其他阶段与活动任务。跨阶段 Ticket 才能限制尚未结束回答总数；PCM、音频段和最新帧仍须分别有界。
3. 为什么 condition_variable 要谓词？通知可能先于等待、也可能虚假唤醒；锁保护状态，谓词决定是否继续。停止必须改变谓词并 notify_all。
4. 为什么 done 后才 active=0？done 可能向 TTS 提交。先宣告空闲，main 会过早关闭 TTS 或销毁 callback 引用。
5. shared_ptr 能消灭死锁吗？不能。最后引用析构可能获得另一把锁；本项目将 Ticket 释放放到队列锁外，取消表只弱持 flag。
6. 为什么 cancellation 不等于中断？flag 只能影响协作检查点；硬中断 SDK 会破坏回调和模型状态。活跃阶段完成、等待阶段取消是明确可测试的语义。
7. ASR 异步化会使 NPU 更快吗？不会必然加速模型计算；它减少 ASR 被业务回调占用的时间。总吞吐和成功播放率必须单独报告。
8. 如何解释 P95？先说明样本数、nearest-rank 等算法和条件；4 个样本的 P95 等于最大值，不能宣传生产尾延迟已稳定。
9. 如何验证设备释放？Worker join、Runtime shutdown 日志之外，还查进程消失、Camera/ALSA/NPU fuser、ALSA status 和原工程指纹。仅打印 success 不够。
10. 为什么不用 TTS 播放期间关闭 ASR？会破坏连续输入。耳机环境本节保留输入并背压；AEC、PTT 和打断属于另需定义的能力。
