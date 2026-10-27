# 5.3 关键 C++ 逐句解释与审查

完整文件见 `stage5_03_source_appendix.md`，此处解释新增或改变的关键语句；原有长篇注释保留在完整源码，不以本表代替源码。行号以最终附录为准。所有权安全依据是 C++ 强引用和锁的规则，实测只是有限场景证据。

## OwnedFramePool：有界所有权，不能用 use_count 猜测独占

| 语句 | 解释与约束 |
|---|---|
| `struct State` | 独立于 CameraService 的池状态，外部 lease 可以跨 Camera 停止存活，不能捕获 Camera 的裸 `this`。 |
| `std::array<std::unique_ptr<ImageFrame>,3> free` | 最多三个自有帧对象。unique_ptr 表示空闲对象只有池拥有；不是三个驱动 MMAP Buffer。 |
| `allocated/in_use/acquired/reused/exhausted` | 分别统计当前代创建过的帧、未归还 lease、取得次数、复用次数和满池次数；都由同一个 mutex 保护。 |
| `bool retired` | 停止后拒绝新 lease，归还帧改为释放，不能把旧帧加入下一代池。 |
| `state_(make_shared<State>())` | 让状态可被 lease 的 deleter 延长寿命；池对象自身的生命周期与状态生命周期分离。 |
| 删除拷贝构造和赋值 | 禁止两个外层池意外共享同一停止职责。 |
| `~OwnedFramePool(){retire();}` | 析构关闭入口、释放空闲缓存，不销毁仍被消费者持有的像素。 |
| `unique_ptr<ImageFrame> owned` | 从空闲列表取出到局部独占对象，后续控制块创建失败也有明确回收方式。 |
| `lock_guard lock(state_->mutex)` | 只保护池管理数据，不包住预处理、RKNN 或像素拷贝。 |
| `if(retired)return {}` | 已关闭的池不能重新发放帧。Camera 重启创建新 State。 |
| `for(slot) if(slot){owned=move(slot);...}` | 将空闲对象转移出来，不复制 ImageFrame 的 vector，空槽不会与使用者同时写同一帧。 |
| `if(allocated==free.size()){++exhausted;return {};}` | 满池返回空而不额外分配第 4 帧。Camera 对应 DQ/QBUF 丢弃并计数。 |
| `owned=make_unique<ImageFrame>();++allocated` | 仅没有空闲对象且未达到三帧时创建对象；分配抛异常则尚未递增成功分配数。 |
| `++in_use;++acquired` | 已获得一个将交付给调用方的独占帧，强引用控制块创建失败的 deleter 也会减少 in_use。 |
| `shared_ptr(owned.release(), [state=state_](...) mutable noexcept {...})` | 每次 lease 创建新控制块。帧地址可以复用，旧 weak_ptr 却不能锁定下一次 lease。shared_ptr 构造分配失败也会调用传入 deleter；因此必须在池锁外构造。 |
| `auto owner=move(state)` | 最后一个强引用释放时把 deleter 捕获的状态转移到局部。旧 weak_ptr 的控制块即使仍在，也不会把整个池缓存长期留住。不是等待所有 weak_ptr 析构才回收帧。 |
| `unique_ptr returning(frame)` | 原始指针重新进入独占 RAII 所有权；退出函数时若没有放回池就自动释放。 |
| `--owner->in_use` | 归还数与取得数配对，锁内修改。 |
| `if(!retired) for(empty slot) slot=move(returning)` | 活跃池接收归还对象，保留 data/stride/size vector 容量，下次取得时才允许写入。 |
| `std::terminate()` | 仅表示内部不变量被破坏：最多三个已分配对象的池不可能在归还时没有空槽。不是正常满池策略，满池发生在 acquire。 |
| retire 分支离开锁后 `returning` 析构 | 大块像素存储释放不在池 mutex 内，减少持锁时间。 |
| `discarded.swap(state_->free)` | retire 锁内仅交换 unique_ptr 数组；局部数组在解锁后析构。正在被 VLM 持有的帧不在 free 数组。 |
| `Stats stats() const` | 加同一 mutex 后按值复制计数，不暴露可变内部引用。 |

边界：池构造/销毁必须遵守外层生命周期，不能在另一个线程销毁同一个 Pool 对象的同时调用它的成员；外部 lease 可以晚于 Pool 对象销毁。Camera 的 start/stop 由已有 lifecycle_mutex 串行化，stop join 后才 retire。

## VideoCapture：减少分配，保留 QBUF 前的所有权边界

| 语句/函数 | 逐句含义 |
|---|---|
| `captureFrame(...) -> captureFrameImpl(&output,false,...)` | 保留旧接口成功后才替换输出的语义，供回退路径与原调用者使用。 |
| `captureReusableFrame(...) -> captureFrameImpl(&output,true,...)` | 调用者保证 frame lease 独占；直接填入其已有容量，失败可能留下半成品，Camera 不得发布失败帧。 |
| `discardFrame(...) -> captureFrameImpl(nullptr,true,...)` | 仍正常 poll、DQBUF、QBUF，避免驱动停止流转，但不复制像素；只用于池满时。 |
| `poll` 的开始/结束埋点 | 单独记录等下一帧的时间，不混入图像计算时间。超时仍沿用原错误/超时分类。 |
| `std::array<v4l2_plane,VIDEO_MAX_PLANES>` | 固定描述数组放栈上，消除旧 vector 的每帧堆分配；不是把 12 MB 像素放在线程栈上。 |
| DQBUF 成功后 sequence 差值 | 无符号差值可处理序号回绕；只统计连续捕获中的驱动序号缺口，不把主动 pool discard 和 latest 替换混成一个数。 |
| `ImageFrame temporary; ImageFrame& frame=reuse?*output:temporary` | 旧语义使用临时对象，新语义直接使用独占 lease。没有把一个 ImageFrame move 赋值给自身。 |
| `clear()` metadata/data | 清 size，保留 capacity，不清空底层整幅数据。随后重新填入全部有效字节，旧帧不能在这时还有读者。 |
| `reserve(total_bytes)` | 只有容量不足才扩容；首次三个池槽分别热身，后续通常不增长。capacity 指标不等于全进程 malloc 总数。 |
| `insert(end,start,start+used)` | 每个有效 plane 的 CPU 显式拷贝仍然存在；mmap 指针不能跨 QBUF 借给 VLM。 |
| `bytesused-data_offset` 与 plane 记录 | 按有效负载复制，不使用映射最大长度当作有效图像大小；保留 stride 和 plane_sizes 作后续校验。 |
| QBUF | 只有数据已复制到自有帧才把驱动 Buffer 归还；discard 分支不读取像素，直接归还。 |
| `if(!reuse) *output=move(temporary)` | 旧接口只在成功后提交结果，vector 的存储转移，不发生第二次整帧拷贝。 |
| `capture_stats_={}` | 每次初始化清除上一代驱动计数，防止重启把不同流的序号连接起来。 |

## CameraService、LatestFrameBuffer 与退出

start 先锁生命周期、join 已退出的旧线程、shutdown 旧设备、clear latest、清统计。在 try 内解析 `STAGE5_CAMERA_POOL`，只接受 `0` 和 `1`，然后创建新池、初始化设备、设置 running、创建线程。非法配置成为可观察的 start=false/last_error；不在工作线程中才抛一个启动配置错误。

captureLoop 每次 acquire 独占可写 lease，成功才 captureReusableFrame；池满调用 discardFrame，并增加 pool_discarded。捕获成功后转换为 `shared_ptr<const ImageFrame>` 发布，不再通过可写别名继续修改。回退使用旧 captureFrame 和 make_shared(move(frame))。Stats 在采集线程写，外部按已有 stats_mutex 读；底层 CaptureStats 只有采集线程或 join 后的 stop 访问。

LatestFrameBuffer::update 的 `swap` 和 getLatest 的 shared_ptr 复制在 mutex 内；旧引用 reset 在锁外。getLatest 取得的是强引用，不是某个像素裸指针。重置 latest 不会使 VLM 已取得的 frame 失效。这里原本没有 NV12 memcpy，本节没有宣称消除一个并不存在的拷贝。

stop 保持 running=false→join→shutdown→clear→统计→retire 的顺序。循环尾也会 clear/shutdown，依赖 5.1 已验证的幂等关闭。池停止时空闲对象立即释放；外部 lease 可以继续读，最后归还时因 retired 被释放。重启不会重新使用旧 State。没有新增 Worker，也没有改变 5.2 的推理 FIFO 或信号处理线程。

## Rgb512Preprocessor：算术保持一致，缓存坐标

| 语句 | 含义 |
|---|---|
| 验证 NV12、非零偶数宽高 | UV 为 2×2 子采样，奇数布局不在当前支持范围。 |
| 验证单 plane、stride、尺寸、data 与 plane_sizes | 只接受一块打包 NV12，限制尺寸避免不受控索引；candidate 比 reference 多检查 plane_sizes 有效界限。 |
| `if(width_!=width || height_!=height)` | 输入尺寸不变时不重复为每个输出像素计算坐标。stride 不进入坐标表，真正读取时仍使用本帧 stride。 |
| `(dx+0.5f)*width/512-0.5f` | 保留半像素中心变换和原 float 运算顺序，不能用另一个插值库替换后假定像素相同。 |
| `max(0, sx)`、`min(width-1,...)` | 边界采样钳制；x1/y1 不越界。 |
| 缓存 `x0/x1/weight/uv` 与对应 y 字段 | 每个方向 512 项 std::array，无额外堆分配；UV 仍用旧算法的最近邻规则。 |
| `rgb.resize(512*512*3)` | 复用 Impl 的 vector 容量；首次增长初始化的成本包含在融合预处理里，热身后 size 不变。 |
| yy 双线性表达式 | 按原次序混合 Y，保留 float 精度、舍入与编译选项；测试在本地与 ARM 分别比较，不把跨编译器相同当成无需验证的保证。 |
| `u/v -128`, `1.164383*(yy-16)` | BT.709 limited-range 数值约定，仍与旧路径一致。与设备 Full Range 元数据的既有差异另记。 |
| 三个 `toByte` 写入 RGB | R/G/B 顺序、饱和/舍入沿用旧函数，没有中间全尺寸 RGB，也没有 crop。 |

## RK3576VLMBackend：输入与输出寿命

Impl 新增 cached 开关、坐标表和两个复用 vector；由 VLMEngine 已有 mutex 串行保护。initialize 在 Runtime 创建前拒绝未知预处理模式。reference 模式使用局部 RGB/embeddings vector，保留旧分配路径。

`auto& rgb=...` 选择持久或局部存储；`capacity()<kImageBytes` 只记录容量增长。预处理完成后栈上 `rknn_input img{}` 零初始化使 pass_through 保持 0；设置 UINT8、NHWC、786432 B、buf=rgb.data()。应用没有另一个 RGB memcpy。rknn_inputs_set 与 rknn_run 各自计时，闭源 SDK 的转换/拷贝不被当成“没有”。

`RknnOutputOwner` 先构造，outputs_get 成功才 acquired=true；校验 result.buf 和浮点输出精确大小。`embeddings.assign(ptr,ptr+36864)` 在 owner 存活时复制，随后检查所有元素 finite。正常、早返回和 assign 抛异常都沿用 5.1 的 RAII 输出释放；释放后不再使用 ptr。持久 embedding vector 不因 SDK 输出释放失效。诊断 dump 检查文件状态，失败返回错误，不伪造比较文件。

RKLLM 同步调用借用 embedding.data()；n_image_tokens=64、n_image=1、height/width=512、提示模板保持不变。栈上的 GenerationState 覆盖整个同步 rkllm_run，未改为异步回调；5.1 的 callback/destroy 顺序保持。Worker 停止并 join 后 Engine 才 shutdown，Impl close 依次 destroy LLM 和 RKNN 后成员 vector 才析构。

## 埋点、诊断与测试的界限

ImageProfile 的静态初始化由 C++ 保证只完成一次。enabled 在构造后不再改变，多个线程用同一 mutex 写 JSONL；计时结束后才序列化和 flush。诊断 I/O 仍可能影响整个系统负载，上层 wall time不能与内层计时直接相减得到“纯计算”。打不开或写失败有 ERROR，测试 harness 明确检查，不把诊断失败当成功。该 logger 不保存 frame 引用。

memory_probe 复用生产 CameraService 和 VLMEngine，不另建推理框架；固定帧从原始 fixture 读入，真实 Camera 模式保存前三帧。首次保存会增加 Frame Age，因此主比较剔除前三个请求。rga_probe 是独立手动实验目标，不被完整语音调用；其三条硬件路径实际失败，不能以编译或 imcheck 成功替代图像正确性。

## 与实现对应的测试

image_pipeline_tests 在 Fake Camera 与实际 CPU 代码上检查：尺寸/padding/非法布局、RGB 与 reference 精确相等、颜色通道与上下方向、复用 capacity、三槽满载、旧 weak_ptr、持有帧期间更新、池析构后 lease、retire、Camera stop/restart、非法启动配置与主动 discard。它不包含 V4L2 ioctl、真实 DMA 或 RKNN 硬件。

async_pipeline_tests、llm_worker_tests、asr_pipeline_tests 保留原确定性 Fake Worker/队列测试；ARM64 CTest 的真实 SDK 链接并不把这些 Fake 变成 NPU 推理测试。另以 memory_probe、固定帧 SDK 推理、真实语音与信号测试提供硬件证据。没有运行 ASan/TSan 或长期泄漏检测，不给出数学意义上的无竞态/无泄漏证明。
