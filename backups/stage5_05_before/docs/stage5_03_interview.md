# 5.3 面试题与完整参考答案

## 1. mmap 摄像头是否就是零拷贝？

不是。mmap 把驱动 Buffer 映射到用户虚拟地址，减少 read 系统调用搬运，但本工程在 DQBUF 和 QBUF 之间仍把 NV12 复制到 ImageFrame::data。此后 SDK 的 inputs_set 还可能转换/传送。要声称端到端零拷贝，必须证明各消费者共享同一合适的存储、同步与所有权都成立，且没有暗含 staging memcpy；不能仅凭一个 mmap 或 DMA-BUF FD。

## 2. 为什么不直接把 V4L2 指针交给异步 VLM？

QBUF 之后驱动可以立即重写 Buffer，而推理可能持续数秒。shared_ptr 只管理包装对象，不能约束驱动重用。可以建立 dequeue lease 并延迟 QBUF，但这会占用有限驱动槽、影响采集；还需要停止时处理所有外借 Buffer。5.3 选择保留一次所有权拷贝，池化自有帧，风险更小。

## 3. shared_ptr 的 use_count()==1 能证明可以覆盖吗？

不能用一次计数观察替代同步协议，其他线程可能从 weak_ptr.lock 取得强引用。若复用同一个控制块，旧 weak_ptr 甚至可能在帧被重新填充后读到另一代数据。本实现每次 lease 生成新控制块，只有最后一个强引用消失、deleter 执行后才回池；旧 weak_ptr 永久过期，地址复用不会复活旧 lease。

## 4. 有界三帧池如何避免读写竞态？

空闲帧由 unique_ptr 独占，acquire 将它移出池后才填像素，发布后只交付 shared_ptr<const ImageFrame>。采集线程不保留可写别名。latest 与 VLM 可以共享一帧，最后强引用释放才归还。三槽支持一个推理持有帧、一个 latest 和一个正在采集的帧；若额外消费者保留更多帧，池满只 DQ/QBUF、计数丢弃，不无界分配。池大小是应用策略，不能假定任意消费者都不触发背压。

## 5. 为什么 shared_ptr 自定义 deleter 要在 mutex 外构造？

shared_ptr 的控制块分配可能抛 bad_alloc；接受裸指针和 deleter 的构造失败时会调用 deleter。如果此时仍持池 mutex，deleter 再锁池会死锁。因此在锁内完成槽位和计数转换，锁外构造控制块；失败也由同一归还逻辑恢复 in_use。

## 6. Camera.stop 后，正在读旧帧的线程怎么办？

停止采集、join、关闭驱动、clear latest 后 retire 池。空闲像素立即释放；外部强引用仍保护已取得的自有帧。State 被 lease 延长寿命，归还时发现 retired 就直接删除。Camera 重启用新 State，不接纳旧代帧。消费者必须持有 FramePtr，不能只提取 data() 裸指针后丢掉所有者。

## 7. stride 与 width 为什么不能互换？

width 是有效像素宽度，stride 是相邻行起点间的字节跨度，可能包含 padding。当前单 plane NV12 的 Y 起点 y*stride，UV 起点 stride*height，UV 同样按 stride 走行。本板实测 stride=3840=width，但测试额外验证 padding=16。多 plane、独立 UV stride、垂直 padding 不能套用这个公式，需要新的格式元数据和验证。

## 8. RGB 复用为什么必须考虑 Engine 锁与 SDK？

一个 vector 复用意味着其内容会在下次请求覆盖；若两个推理同时使用它，SDK 可能读取正在改变的输入。当前 VLMEngine mutex 串行化 backend infer，inputs_set→run→outputs_get 都在本次调用内完成；RGB 在 SDK 使用期间不 resize/reassign。Embeddings 独立复制后同步 rkllm_run，直到返回才允许下一次覆盖。若未来改 SDK async，必须重新设计事件和多 buffer 生命周期，现有结论不能直接继承。

## 9. NV12 转 RGB 优化后尺寸相同，为何还要逐像素比较？

矩阵 BT.601/709、limited/full、RGB/BGR、插值半像素坐标、UV 采样、饱和与舍入都能改变结果。相同 512×512 不等于相同模型输入。5.3 先比较固定原始帧的 RGB 字节，再比较 64×576 float Embeddings 和回答；还用合成红色/方向图确认通道与上下关系。真实画面用户确认补充语义证据，但不替代色彩标定。

## 10. 如何判断缓存坐标是有效优化？

先在旧算术上建立基线，保持模型、帧、编译模式一致，分离 poll 等待和预处理计算。缓存每个输出行/列的坐标，消除重复的浮点除法/边界计算；对相同输入验证像素。报告样本数、平均、nearest-rank P50/P95、最小/最大，并承认小样本和系统负载影响。总延迟还受约秒级 RKNN、语言生成和 TTS 影响，不能把几毫秒预处理改善说成完整交互等比例加速。

## 11. DMA-BUF、物理连续内存和缓存一致性是什么关系？

DMA-BUF 是共享内存对象及其 FD/同步约定，不自动保证物理连续；system heap 通常提供可通过 IOMMU 映射的页，是否支持要由实际硬件驱动/Runtime 确认。CPU 映射读写 DMA 缓冲要遵守 begin/end CPU access 或相应 sync ioctl。导入 FD 成功只说明对象被接受，不证明硬件处理成功。本节 system heap FD 实验仍在首个 RGA job 失败，不能把它描述为完成 DMA 摄像头链路。

## 12. RGA 校验和 import 成功，为什么运行仍失败？

参数校验和导入是不同阶段，硬件提交还依赖实际驱动、地址映射、格式组合、stride/缩放能力和运行状态。本板虚拟地址、DMA fused、DMA resize 三条路径均在第一个 job 报错，并有内核硬件超时。证据不足以指定唯一根因；正确做法是保留日志、停止扩大试验、保持 CPU 生产路径，不把驱动自己 soft reset 当作应用修复成功。

## 13. 为什么 RSS 上升不一定是泄漏，但也不能忽略？

池保留三帧容量和 RGB/embedding 缓存，允许以常驻内存换取分配减少；allocator 与 SDK 也可能缓存。泄漏指不可达或不再需要的资源未释放，不能仅凭单个 RSS 值判断。需要观察 bounded 峰值、停止时归还计数、设备 FD 关闭、重复生命周期和长期趋势。5.3 只有有限轮次采样和生命周期测试，没有长期泄漏工具证据，因此明确保留风险，并公开峰值增加的代价。

## 14. 如何保证统计不“美化”结果？

保留原始版本、所有失败轮次、退出码、输入元数据和测量脚本。区分源代码可见分配事件与 malloc 总次数；区分 Host Frame Age 与曝光时间；融合操作不拆出虚构独立耗时；P95 小样本常等于最大值。排除前三个保存 fixture 的 Frame Age 时必须写明规则并保留原数据。RGA 没有成功样本就标未测量，SDK 内部未知就标未知。

## 15. drain 与 cancel_pending 的安全退出区别是什么？

两者先关闭新输入，再处理已接收工作。drain 排空有效的已接收任务；cancel_pending 取消等待执行或尚未提交到下游的任务，同时允许已经进入 SDK 的调用返回。取消不是在任意指令点破坏 Runtime。之后按 ASR→推理 Worker→TTS→设备/模型销毁的依赖顺序 join；信号处理机制沿用 5.1，不在异步 signal handler 中调用 mutex、日志、析构或 SDK。强杀只能是超时后的失败保护，不能证明优雅退出。
