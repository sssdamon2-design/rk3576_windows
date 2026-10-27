# 5.2 实测性能数据

本表由 `tools/stage5_02_performance.py` 从采集的原始终端/JSON 生成。设备、模型、构建和限制见 [验收报告](stage5_02_board_acceptance.md)。日期 2026-10-17，RK3576 真机；Fake 测试不纳入这些性能数字。

统计均为毫秒（吞吐表除外），P50/P95 使用 nearest-rank，n=2 的 P50 为较小值，n≤4 的 P95 常等于最大值。每个 case 仅运行一次、请求数很小，没有置信区间或生产尾延迟结论；频率、温度、图像和生成长度未严格固定。

## 操作 1：NPU 实际 SDK 调用对照

| 调用方式（每类 n=3） | 指标 | 平均 ms | P50 ms | P95 ms |
|---|---|---:|---:|---:|
| 顺序 | Qwen 调用 | 945.432 | 867.519 | 1110.670 |
| 顺序 | RKNN+SmolVLM2 调用 | 1927.090 | 1989.400 | 2046.740 |
| 顺序 | 一对任务完成 | 2872.523 | 2856.920 | 2904.850 |
| 顺序 | SDK 调用区间交集 | 0.000 | 0.000 | 0.000 |
| 重叠 | Qwen 调用 | 2338.717 | 2306.140 | 2409.420 |
| 重叠 | RKNN+SmolVLM2 调用 | 2667.267 | 2656.390 | 2718.580 |
| 重叠 | 一对任务完成 | 2667.267 | 2656.390 | 2718.580 |
| 重叠 | SDK 调用区间交集 | 2338.717 | 2306.140 | 2409.420 |

6/6 对成功。重叠未观察到崩溃，但 Qwen 调用变慢；区间交集不是 NPU 硬件利用率。统一消费者是响应可预测性的选择，不是“并行已经被证明不安全”的结论。

## 操作 2：ASR 业务回调/受控提交阻塞

| case | n | 平均 ms | P50 ms | P95 ms |
|---|---:|---:|---:|---:|
| baseline_equal_work_pair | 2 | 868.872 | 0.014 | 1737.730 |
| baseline_replay_overload | 4 | 957.756 | 0.014 | 1920.580 |
| candidate_cancel_active_vision | 1 | 0.032 | 0.032 | 0.032 |
| candidate_equal_work_pair | 2 | 0.090 | 0.035 | 0.144 |
| candidate_idle_sigint | 0 | — | — | — |
| candidate_replay_overload | 4 | 0.128 | 0.047 | 0.367 |
| candidate_stop_cancel_pending | 4 | 0.075 | 0.024 | 0.183 |
| candidate_stop_drain | 4 | 0.078 | 0.037 | 0.195 |
| candidate_voice_burst | 4 | 0.031 | 0.031 | 0.039 |
| candidate_voice_natural | 2 | 0.310 | 0.023 | 0.597 |

baseline 的 VISION 耗时落在调用者线程；candidate 的 VISION 工作落在推理 Worker。表中混合 TEXT/VISION；过载 case 的 n 包括被拒绝请求，应同时读接受率。受控文本模式测同一个生产回调，不测 ASR 模型；真实 microphone case 才包含 USB/VAD/SenseVoice。

## 操作 3：各队列等待

| case | 推理排队 n / 平均 / P50 / P95 ms | TTS 终态 n / 平均 / P50 / P95 ms |
|---|---|---|
| baseline_equal_work_pair | 1 / 0.075 / 0.075 / 0.075 | 2 / 7852.470 / 0.039 / 15704.900 |
| baseline_replay_overload | 2 / 706.132 / 0.085 / 1412.180 | 3 / 22385.326 / 22963.900 / 44192.000 |
| candidate_cancel_active_vision | 1 / 0.086 / 0.086 / 0.086 | 0 / — / — / — |
| candidate_equal_work_pair | 2 / 460.445 / 0.088 / 920.802 | 2 / 10201.036 / 0.071 / 20402.000 |
| candidate_idle_sigint | 0 / — / — / — | 0 / — / — / — |
| candidate_replay_overload | 2 / 475.481 / 0.090 / 950.871 | 2 / 11021.560 / 0.020 / 22043.100 |
| candidate_stop_cancel_pending | 2 / 425.233 / 0.078 / 850.388 | 2 / 10222.646 / 0.092 / 20445.200 |
| candidate_stop_drain | 2 / 445.267 / 0.130 / 890.404 | 2 / 11128.593 / 0.087 / 22257.100 |
| candidate_voice_burst | 3 / 0.046 / 0.042 / 0.072 | 3 / 1274.973 / 0.095 / 3824.760 |
| candidate_voice_natural | 2 / 0.046 / 0.021 / 0.071 | 2 / 0.118 / 0.018 / 0.218 |

baseline 推理队列 n 只包含异步 TEXT，VISION 直接同步执行，没有相应 queue_ms；不能把缺失数据当零后混平均。TTS 统计包括过期/取消的真实驻留；取消回调兼容值 -1 已用 `[TTS cancelled]` 的实际驻留代替。过期出队时检查，实际驻留可超过配置期限。

## 操作 4：深度、接受/拒绝、成功率和完整交付

| case | 推理峰值 / TTS 峰值 | 跨阶段峰值 | 推理成功/实际执行 | 播放/输入请求 | Admission 拒绝 | TTS 过期/取消 | 子进程码 |
|---|---|---|---|---|---:|---|---:|
| baseline_equal_work_pair | 1/1 | 无跨阶段限制 | 2/2 | 2/2 | 不适用 | 无该策略 | 0 |
| baseline_replay_overload | 1/2 | 无跨阶段限制 | 4/4 | 3/4 | 不适用 | 无该策略 | 1 |
| candidate_cancel_active_vision | 1/0 | 1 | 1/1 | 0/1 | 0 | 0/0 | 0 |
| candidate_equal_work_pair | 1/1 | 2 | 2/2 | 2/2 | 0 | 0/0 | 0 |
| candidate_idle_sigint | 0/0 | 0 | 0/0 | 0/0 | 0 | 0/0 | 0 |
| candidate_replay_overload | 1/1 | 2 | 2/2 | 1/4 | 2 | 1/0 | 0 |
| candidate_stop_cancel_pending | 1/1 | 2 | 2/2 | 1/4 | 2 | 0/1 | 0 |
| candidate_stop_drain | 1/1 | 2 | 2/2 | 2/4 | 2 | 0/0 | 0 |
| candidate_voice_burst | 1/1 | 2 | 3/3 | 3/4 | 1 | 0/0 | 0 |
| candidate_voice_natural | 1/1 | 1 | 2/2 | 2/2 | 0 | 0/0 | 0 |

baseline_replay_overload 另有 1 次 TTS 队列满拒绝，退出 1；其余子程序返回 0。candidate_cancel_active_vision 下游取消 1，不启动 TTS。不能把推理成功率当请求最终交付率；没有执行的请求不计进模型成功分母。音频队列两轮真实 microphone 均峰值 1、dropped 0。

## 操作 5：有限批次吞吐和自然排空退出

| case | ready 至退出 s | 成功推理 / s | 完成播放 / s | 输入关闭至退出 s |
|---|---:|---:|---:|---:|
| baseline_equal_work_pair | 30.981 | 0.065 | 0.065 | 29.114 |
| baseline_replay_overload | 61.218 | 0.065 | 0.049 | — |
| candidate_equal_work_pair | 36.158 | 0.055 | 0.055 | 34.973 |
| candidate_idle_sigint | 3.918 | 0.000 | 0.000 | — |
| candidate_replay_overload | 27.033 | 0.074 | 0.037 | — |
| candidate_voice_burst | 82.621 | 0.036 | 0.036 | — |
| candidate_voice_natural | 92.016 | 0.022 | 0.022 | — |

吞吐分母包含 drain/退出；真实 microphone case 还包含等待用户和静音窗口，不能称持续最大吞吐。两请求 equal_work_pair 都接受并播放 2/2，TTL 放宽到 60 s 排队/120 s 生命周期以避免策略丢弃。源输入相同，但 VLM 分别生成12 与 17 个英文词，PCM 帧数 80696 与 107578，未保持计算工作量完全相同；candidate 的批次排空实际更慢，不能宣称端到端加速。其主要收益是 VISION 回调不再占用 ASR。

## 操作 6：停止模式和资源采样

| case | 信号 | 模式 | 信号至退出 s | 采样峰值 RSS KiB | 采样线程峰值 |
|---|---|---|---:|---:|---:|
| baseline_equal_work_pair | 自然结束 | drain | — | 2511620 | 12 |
| baseline_replay_overload | 自然结束 | drain | — | 2582112 | 13 |
| candidate_cancel_active_vision | SIGTERM | cancel_pending | 3.413 | 2505916 | 7 |
| candidate_equal_work_pair | 自然结束 | drain | — | 2507400 | 9 |
| candidate_idle_sigint | SIGINT | drain | 1.907 | 2496948 | 9 |
| candidate_replay_overload | 自然结束 | drain | — | 2514388 | 10 |
| candidate_stop_cancel_pending | SIGTERM | cancel_pending | 1.532 | 2519368 | 10 |
| candidate_stop_drain | SIGTERM | drain | 12.229 | 2522504 | 10 |
| candidate_voice_burst | 自然结束 | drain | — | 2638328 | 12 |
| candidate_voice_natural | 自然结束 | drain | — | 2634780 | 12 |

信号延迟从 harness 发送时刻至子进程退出/输出 EOF，排除后续 fuser/指纹查询。Drain 与 CancelPending 完成工作量不同，不是同等计算加速。采样周期约 1 s，可能漏过短峰值；RSS 包含 SDK、模型映射和工作缓冲，不能当 C++ heap 泄漏大小。全部 case 无超时/强制终止且设备释放。长期稳定性留后续独立验收。

## 操作 7：模型计算时间与局限

| case | 成功 TTS n | 合成平均 ms | P50 ms | P95 ms |
|---|---:|---:|---:|---:|
| baseline_equal_work_pair | 2 | 11365.685 | 8659.770 | 14071.600 |
| baseline_replay_overload | 3 | 15382.090 | 17654.400 | 19986.900 |
| candidate_cancel_active_vision | 0 | — | — | — |
| candidate_equal_work_pair | 2 | 13256.445 | 8842.090 | 17670.800 |
| candidate_idle_sigint | 0 | — | — | — |
| candidate_replay_overload | 1 | 18855.800 | 18855.800 | 18855.800 |
| candidate_stop_cancel_pending | 1 | 17753.000 | 17753.000 | 17753.000 |
| candidate_stop_drain | 2 | 13819.420 | 8643.440 | 18995.400 |
| candidate_voice_burst | 3 | 14853.563 | 16361.800 | 18687.700 |
| candidate_voice_natural | 2 | 12545.760 | 8656.320 | 16435.200 |

回答文本长度、CPU 竞争和 Camera 场景不同，合成数值波动不能归因为异步化提升模型速度。本节未改变 Kokoro 模型或合成算法。5.4 再按固定语料、更多样本和统一时间链路分析计算性能。
