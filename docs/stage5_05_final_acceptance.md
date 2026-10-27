# 5.5 Qt 集成与最终系统工程验收报告

本报告记录2026年10月17日至18日香港时间在同一台RK3576隔离工程的真实开发与验证。5.1～5.4已经用户验收；本节工程检查结果以validation_summary.json为准，最终用户审核仍待确认。没有将隔离版本覆盖为原稳定工程。有限长测只支持记录工况内结论。

## 1 继承版本与实际改动

先以SHA256核对5.4最终v3的96项源码，再冻结171项源码、工具、测试、配置与文档至backups/stage5_05_before。原稳定目录321项、5.1～5.4四个已验收程序和5.4源码分别留存清单。最终生产源码104项位于stage5_05_source_final_v2，构建为build/stage5_05_final_v2。较早stage5_05_source_thermal仅放宽原CLI记录秒数及回放偏移上限，用于同版本2/4线程热对照；不能拿它冒充最后Qt与结构化日志版本。final_v1、qt_v1是未部署的本地中间快照。

最小改动：CMake增加默认关闭的BUILD_QT_GUI；StopSignals类正文从CLI原样移到共用头文件；CLI监听上限120→3600秒、回放偏移上限120000→3600000ms，默认12秒和20ms信号轮询不变；复用ImageProfile的steady_clock、mutex和JSONL新增完整识别/回答字符串事件。5.3池、图像预处理、RKNN/RKLLM后端、TTS合成与播放算法及5.2队列保持字节不变，未更换模型或生成参数。

实际语音入口VADAudioWorker→音频段队列→ASRWorker→IntentRouter→额度管理→单消费者InferenceWorker→Qwen或Camera/RKNN/SmolVLM2→TTSWorker/Kokoro/ALSA，没有经过另一个CLI入口的RequestProcessor。Qt通过QProcess复用完整入口，后台原线程运行模型与设备；Qt主线程只处理事件、有限日志和控件，不进行SDK加载、推理或等待音频。

![最终线程架构](../reports/stage5_05_local/plots/system_architecture.png)

![Camera Buffer 生命周期](../reports/stage5_05_local/plots/buffer_lifecycle.png)

![退出与销毁顺序](../reports/stage5_05_local/plots/shutdown_order.png)

## 2 Qt 运行环境与实际验收

板端已有Qt5.15.8 Widgets/Test、头文件、平台插件和GNOME/X11 DISPLAY :0；DSI已连接。本节没有安装系统软件、迁移车载工程、修改显示或权限配置。实际运行采用xcb与现有cat认证。QWidget::grab截取本次真实窗口，未生成模拟截图。启动时libGL报告rockchip DRI加载失败，但普通Widgets页面正常显示；这不能视为硬件OpenGL渲染已验证。Kokoro已有未知token/phoneme警告如实保留，不等于本节新引入崩溃。

GUI显示五模块、识别、TEXT/VISION、完整回答、阶段、队列事件快照、错误、ASR/推理/TTS/首次提交延迟。选项支持2/4线程及排空/取消等待。活动时禁止更改配置，关闭事件先ignore→SIGINT→等待QProcess finished→关闭窗口；90秒未退出报告失败，不把强杀算作成功。信号在QApplication及SDK线程创建前阻塞，由普通sigwait线程接收；没有异步handler调用Qt或锁。QProcess连接带QObject context，正常窗口关闭先等待后台，避免回调触达已销毁对象。重新开始是新进程和新UUID目录，并非宣称闭源SDK实例内重启。

实际case `gui_microphone_final_v2`：退出码0，持续79.496秒，所有会话有序退出=True，强制终止=False，设备释放=True。原始记录：`Z:/master_T/Linux/资料/code/rk3576_multimodal_stage5_source/rk3576_multimodal/reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_microphone_final_v2/result.json`。

实际case `gui_paired_restart_final_v2`：退出码0，持续102.267秒，所有会话有序退出=True，强制终止=False，设备释放=True。原始记录：`Z:/master_T/Linux/资料/code/rk3576_multimodal_stage5_source/rk3576_multimodal/reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_paired_restart_final_v2/result.json`。

实际case `gui_sigterm_vision_final_v2`：退出码0，持续53.127秒，所有会话有序退出=True，强制终止=False，设备释放=True。原始记录：`Z:/master_T/Linux/资料/code/rk3576_multimodal_stage5_source/rk3576_multimodal/reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_sigterm_vision_final_v2/result.json`。

实际case `gui_mixed_1800s_4t_final_v2`：退出码0，持续1837.782秒，所有会话有序退出=True，强制终止=False，设备释放=True。原始记录：`Z:/master_T/Linux/资料/code/rk3576_multimodal_stage5_source/rk3576_multimodal/reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/gui_mixed_1800s_4t_final_v2/result.json`。

| 最终进程 | CPU平均/P95 %（80s后） | RSS峰值MiB | VmHWM观测峰值MiB | 线程峰值 | 温度峰值℃ |
|---|---|---|---|---|---|
| Qt父进程 | 1.44/8.89 | 89.059 | 89.059 | 4 | 85.888 |
| 后台AI | 280.23/423.24 | 2715.125 | 2715.324 | 13 | 85.0 |

本次人工确认原文：“是的，和你描述的一样”。针对该轮明确问题，已记录两个回答均通过HyperX实际听到、视觉描述大致相符、Qt显示识别文本/路由/回答。不能将程序success=true替代这份确认。自然语音仅TEXT/VISION各1条，不能据此推导大样本音质或识别率。

![本次真实xcb界面进入监听](../reports/stage5_05_local/figures/gui_listening.png)

![本次真实视觉回答和延迟](../reports/stage5_05_local/figures/gui_answer_2.png)

![本次有序停止后的真实界面](../reports/stage5_05_local/figures/gui_finished.png)

## 3 ARM64 构建和确定性测试

`build_thermal`：成功=True，去重目标30个；各步骤真实记录：`[{"step": "configure", "returncode": 0, "reason": null, "seconds": 3.0020763280008396}, {"step": "build", "returncode": 0, "reason": null, "seconds": 121.05928409899934}, {"step": "ctest", "returncode": 0, "reason": null, "seconds": 2.0026842519982893}]`。

`build_final_v2`：成功=True，去重目标36个；各步骤真实记录：`[{"step": "configure", "returncode": 0, "reason": null, "seconds": 3.0020454799996514}, {"step": "build", "returncode": 0, "reason": null, "seconds": 156.08595781799886}, {"step": "ctest", "returncode": 0, "reason": null, "seconds": 7.0067366089970164}]`。

| 注册测试 | 具体验证 | 实际SDK边界 |
|---|---|---|
| request_profile_tests | 固定音频输入与请求计时、UTF8/控制字符转义、并发完整文本事件 | 无模型 |
| image_pipeline_tests | stride、池复用、weak_ptr生命周期、缓存RGB与像素一致 | CPU/Fake帧 |
| async_pipeline_tests | 连续/交替、满载、取消、过期、停止重启、推理和TTS/播放异常后恢复 | Fake Backend/Service |
| asr_pipeline_tests | 空队列停止唤醒、ASR异常与回调异常、队列终态 | Fake ASR |
| audio_preprocessor_tests | 音频转换与边界 | CPU |
| llm_worker_tests | 生命周期、停止/重启、异常和回调 | Fake LLM |
| camera_service_tests | 打开失败、超时、异常、停止、重启和帧所有权 | Fake Camera |
| gui_session_tests | 主线程心跳、显示、无覆盖启动、错误恢复、停止/重启、活跃窗口关闭、关闭优先于自动重启 | offscreen Qt与明确Fake子进程 |

最终ARM64 CTest的8项通过与Windows portable 9项分别保存；它们是确定性逻辑测试，真实SDK和硬件回归另列。编译残留未使用函数、测试缩进和RGA SDK匿名struct警告保留，不能改写成零警告。

## 4 热测试条件与安全边界

同板、同模型/Runtime、相同真实语音段和固定NV12、相同推理参数，2/4线程依次180秒短测、1800秒混合输入长测。所有读到的zone低于55℃才开始，最长冷却600秒；保持ondemand、不改CPU频率、亲和性或风扇。长测每15秒一个输入，TEXT/TEXT/VISION/VISION/TEXT/VISION循环，共121条；生产TTS等待12秒、请求期限45秒，排队满载明确拒绝。固定音频绕过麦克风/VAD，Camera真实持续采集，但Vision读取同一固定帧，因此固定场景Frame Age未测量。

实际thermal_zone2 little passive为75℃/85℃，critical为115℃。这些是Linux当前配置，不是芯片额定安全温度证明。测试护栏为任一温度≥90℃、温度不可读、MemAvailable<256MiB或磁盘<500MiB立即向确认PID发SIGTERM；有限宽限后若仍卡住，只能强制终止本次确认PID并记失败。实际没有修改thermal/sysfs配置。采样每秒，smaps约每5次；CPU按一核100%，HZ来自本板sysconf。

| 真实case | 进程秒数 | 输入/完成 | 峰值温度℃ |
|---|---|---|---|
| mixed_180s_2t | 221.527 | 10/10 | 75.769 |
| mixed_180s_4t | 218.625 | 10/10 | 84.076 |
| mixed_1800s_2t | 1839.890 | 121/121 | 86.777 |
| mixed_1800s_4t | 1833.324 | 121/121 | 85.888 |
| 同一case资源 | 峰值RSS MiB | CPU均值/P95 %（80s后） | 峰值线程 |
|---|---|---|---|
| mixed_180s_2t | 2718.359 | 151.18/220.77 | 11 |
| mixed_180s_4t | 2647.305 | 210.63/422.44 | 13 |
| mixed_1800s_2t | 2647.316 | 193.23/310.17 | 11 |
| mixed_1800s_4t | 2711.289 | 280.74/423.20 | 13 |

2/4线程长测TSV的SHA均为`5e9f356f3647cdcdbbb31117e0a312f65bee2f9abe58d43e4bf570dd932585b7`，121行。两轮每条成功完成，失败/超时/拒绝/丢弃均为0，队列峰值1、在途峰值2，Camera均29.997FPS。原始队列计数、资源样本及统计口径在CSV/JSON。2线程最高86.777℃，4线程85.888℃；此节奏混合负载不能据此推论4线程总是更凉。5.4连续独立合成中4线程更热，两类负载占空比与DVFS不同。

## 5 热对照的暖态延迟分布

请求暖态边界从首个asr_enqueued起算5分钟，RSS趋势则从进程首次资源采样起算，二者不混用。每轮前5分钟请求单列，以下仅warm_after_5min：TEXT n50、VISION n51。时间单位ms，格式为均值/P50/P95/最小/最大(n)。合成输出长度可能略变，额外按每条实际PCM长度计算RTF；不混合中英文回答直接算模型加速。首次提交是ALSA write调用边界，drain是软件排空，均非直接声学测量。

### TEXT 同输入路线对照

| 指标 | 2线程 | 4线程 |
|---|---|---|
| asr_rtf | 0.446/0.468/0.473/0.365/0.478 (n=50) | 0.370/0.370/0.373/0.365/0.376 (n=50) |
| asr_decode_ms | 696.501/733.803/741.115/567.763/748.935 (n=50) | 568.772/568.446/570.763/566.119/577.503 (n=50) |
| asr_api_ms | 703.403/739.109/746.828/575.254/754.578 (n=50) | 583.846/583.599/588.056/575.318/593.311 (n=50) |
| inference_queue_ms | 0.054/0.044/0.098/0.027/0.105 (n=50) | 0.057/0.046/0.091/0.025/0.119 (n=50) |
| inference_service_ms | 961.287/939.296/1158.782/842.889/1241.240 (n=50) | 859.151/857.444/881.882/819.899/981.546 (n=50) |
| tts_queue_ms | 3552.556/4501.187/5649.373/31.550/5738.318 (n=50) | 45.451/0.255/201.833/0.068/279.053 (n=50) |
| tts_generate_api_ms | 8960.022/8889.523/9351.944/8721.889/9597.135 (n=50) | 6978.146/7031.840/7109.401/6747.804/7128.426 (n=50) |
| tts_rtf | 4.587/4.550/4.800/4.460/4.906 (n=50) | 3.571/3.596/3.644/3.455/3.652 (n=50) |
| synthesis_to_first_submit_ms | 8960.655/8890.432/9352.623/8722.441/9598.121 (n=50) | 6978.775/7032.429/7110.004/6748.446/7129.028 (n=50) |
| asr_enqueue_to_first_submit_ms | 14178.500/15204.241/16710.412/10204.839/16832.826 (n=50) | 8468.012/8481.115/8733.416/8181.179/8819.027 (n=50) |
| asr_enqueue_to_playback_end_ms | 16163.164/17189.055/18695.093/12189.038/18817.730 (n=50) | 10452.713/10466.217/10718.062/10165.500/10803.763 (n=50) |

### VISION 同输入路线对照

| 指标 | 2线程 | 4线程 |
|---|---|---|
| asr_rtf | 0.465/0.495/0.510/0.391/0.511 (n=51) | 0.399/0.398/0.407/0.394/0.409 (n=51) |
| asr_decode_ms | 621.921/665.597/685.351/520.897/686.872 (n=51) | 525.840/524.469/539.727/522.468/543.218 (n=51) |
| asr_api_ms | 629.708/670.321/690.023/529.719/691.574 (n=51) | 540.166/539.342/550.928/533.034/553.677 (n=51) |
| inference_queue_ms | 0.053/0.045/0.090/0.031/0.094 (n=51) | 0.068/0.079/0.098/0.028/0.110 (n=51) |
| inference_service_ms | 1531.360/1525.825/1593.761/1485.090/1638.762 (n=51) | 1512.997/1509.831/1540.678/1484.732/1546.813 (n=51) |
| tts_queue_ms | 1026.583/1011.173/2212.289/0.023/2247.175 (n=51) | 0.046/0.033/0.079/0.024/0.116 (n=51) |
| tts_generate_api_ms | 14310.385/14434.488/14861.235/13718.288/15315.634 (n=51) | 10987.520/10955.498/11215.317/10727.668/11281.751 (n=51) |
| tts_rtf | 4.253/4.290/4.417/4.077/4.552 (n=51) | 3.266/3.255/3.333/3.188/3.353 (n=51) |
| synthesis_to_first_submit_ms | 14311.316/14435.358/14862.307/13719.105/15316.674 (n=51) | 10988.514/10956.430/11216.311/10728.574/11282.700 (n=51) |
| asr_enqueue_to_first_submit_ms | 17499.590/17803.004/19063.752/15779.523/19368.789 (n=51) | 13042.522/13010.222/13283.013/12777.380/13362.490 (n=51) |
| asr_enqueue_to_playback_end_ms | 20864.221/21174.492/22423.408/19138.686/22728.259 (n=51) | 16404.723/16369.595/16642.841/16136.804/16721.965 (n=51) |

4线程在本次混合工况下ASR没有出现饥饿：TEXT平均ASR RTF约0.446→0.370，VISION约0.465→0.399。模型计算、调度、温度和输入节奏共同作用，不能从这些非随机交叉的整系统数据归因每个子系统必然加速。两边都是每15秒到达，30分钟总体完成数相同，不宣称吞吐提升30%。TTS纯同条件计算收益仍引用5.4固定文本各语言n30的30.42%/29.74%，不篡改比较条件。

![实际热与CPU及频率时间序列](../reports/stage5_05_local/plots/thermal_cpu_memory.png)

![暖态请求RTF分布](../reports/stage5_05_local/plots/warm_rtf.png)

![预热后的RSS分段变化](../reports/stage5_05_local/plots/warmed_rss.png)

## 6 RSS趋势与Linux降频证据

`mixed_1800s_2t`：5～30分钟RSS斜率-0.110404 MiB/min，5～10分钟中位数2647.047 MiB，25～30分钟中位数2645.305 MiB。排除初次模型页驻留与退出下降，不用开始/结束两个点证明无泄漏。

| cooling设备或频率 | 实际读数 |
|---|---|
| /sys/class/thermal/cooling_device1/cur_state | 最大state=2，positive=86/1788 |
| /sys/class/thermal/cooling_device4/cur_state | 最大state=0，positive=0/1788 |
| /sys/class/thermal/cooling_device2/cur_state | 最大state=6，positive=922/1788 |
| /sys/class/thermal/cooling_device0/cur_state | 最大state=8，positive=161/1788 |
| /sys/class/thermal/cooling_device3/cur_state | 最大state=0，positive=0/1788 |
| /sys/devices/system/cpu/cpu4/cpufreq/scaling_max_freq | min=1800000，max=2208000 kHz |
| /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq | min=408000，max=2016000 kHz |

`mixed_1800s_4t`：5～30分钟RSS斜率0.026513 MiB/min，5～10分钟中位数2710.434 MiB，25～30分钟中位数2710.949 MiB。排除初次模型页驻留与退出下降，不用开始/结束两个点证明无泄漏。

| cooling设备或频率 | 实际读数 |
|---|---|
| /sys/class/thermal/cooling_device1/cur_state | 最大state=2，positive=959/1771 |
| /sys/class/thermal/cooling_device4/cur_state | 最大state=0，positive=0/1771 |
| /sys/class/thermal/cooling_device2/cur_state | 最大state=6，positive=978/1771 |
| /sys/class/thermal/cooling_device0/cur_state | 最大state=8，positive=961/1771 |
| /sys/class/thermal/cooling_device3/cur_state | 最大state=0，positive=0/1771 |
| /sys/devices/system/cpu/cpu4/cpufreq/scaling_max_freq | min=1800000，max=2208000 kHz |
| /sys/devices/system/cpu/cpu0/cpufreq/scaling_max_freq | min=408000，max=2016000 kHz |

cooling_device0/1对应cpufreq-cpu0/cpu4，2对应devfreq GPU，3为devfreq-dmc，4为devfreq NPU，以实际inventory type为准。CPU cooling为正并伴随scaling_max_freq收紧，支持发生Linux热管理限频；仅ondemand的scaling_cur_freq变化不能单独证明热降频。GPU cooling为正不能冒充CPU降频。本轮有热管理活动，但未出现90℃护栏、崩溃、明显ASR饥饿或持续RSS增长，默认保留4线程，2线程可回退。这个选择仅适用于现有散热与记录负载，更高占空比应再测。

4线程较早加载后的RSS增加不直接判为泄漏。中段与末段真实smaps映射比较：DRI RSS 1,369,584kB、heap 903,064kB、匿名映射424,592kB、video11 48,608kB保持一致，小量变化集中于文件映射页；暖态中位数仅约0.516MiB变化，未见该窗口持续堆/匿名增长。4线程比2线程峰值约多64MiB。没有LeakSanitizer/闭源SDK泄漏证明，不能写“系统绝无内存泄漏”。

## 7 最终源码性能与自然输入复核

### gui_microphone_final_v2/run_20261017_165440_871_7225107cc44646f68a19282099119fd5

实际最终计数：`{"ALSA": {"XRUN": 0, "Suspends": 0, "Recoveries": 0, "RecoveryFailures": 0}, "FramePool": {"allocated": 3, "in_use": 0, "acquired": 1689, "reused": 1686, "exhausted": 0}, "CameraCounters": {"published": 1688, "fps": 29.9073, "timeouts": 0, "driver_sequence_gaps": 0, "pool_discarded": 0}, "AudioQueueStats": {"pushed": 2, "popped": 2, "dropped": 0, "rejected_closed": 0, "peak": 1, "pending": 0}, "QueueStats/inference": {"stage": "inference", "generation": 1, "accepted": 2, "completed": 2, "started": 2, "failed": 0, "cancelled": 0, "expired": 0, "rejected_full": 0, "rejected_stopped": 0, "peak": 1, "pending": 0, "active": 0, "callback_errors": 0, "queue_sum_ms": 0.166924, "queue_max_ms": 0.103264, "service_sum_ms": 2998.84}, "QueueStats/tts": {"stage": "tts", "generation": 1, "accepted": 2, "completed": 2, "started": 2, "failed": 0, "cancelled": 0, "expired": 0, "rejected_full": 0, "rejected_stopped": 0, "peak": 1, "pending": 0, "active": 0, "callback_errors": 0, "queue_sum_ms": 0.17605, "queue_max_ms": 0.098023, "service_sum_ms": 24328.9}, "PipelineStats": {"dispatched": 2, "accepted": 2, "rejected": 0, "inflight": 0, "peak": 1, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0}}`。

| 指标 | 真实统计 |
|---|---|
| TEXT/all_observed/success asr_rtf | 0.420/0.420/0.420/0.420/0.420 (n=1) |
| TEXT/all_observed/success inference_service_ms | 1165.693/1165.693/1165.693/1165.693/1165.693 (n=1) |
| TEXT/all_observed/success tts_generate_api_ms | 6290.531/6290.531/6290.531/6290.531/6290.531 (n=1) |
| TEXT/all_observed/success tts_rtf | 3.232/3.232/3.232/3.232/3.232 (n=1) |
| TEXT/all_observed/success tts_queue_ms | 0.098/0.098/0.098/0.098/0.098 (n=1) |
| TEXT/all_observed/success asr_enqueue_to_first_submit_ms | 8027.404/8027.404/8027.404/8027.404/8027.404 (n=1) |
| TEXT/all_observed/success asr_enqueue_to_playback_end_ms | 10011.762/10011.762/10011.762/10011.762/10011.762 (n=1) |
| VISION/all_observed/success frame_age_ms | 34.146/34.146/34.146/34.146/34.146 (n=1) |
| VISION/all_observed/success asr_rtf | 0.416/0.416/0.416/0.416/0.416 (n=1) |
| VISION/all_observed/success inference_service_ms | 1832.893/1832.893/1832.893/1832.893/1832.893 (n=1) |
| VISION/all_observed/success tts_generate_api_ms | 11817.045/11817.045/11817.045/11817.045/11817.045 (n=1) |
| VISION/all_observed/success tts_rtf | 2.789/2.789/2.789/2.789/2.789 (n=1) |
| VISION/all_observed/success tts_queue_ms | 0.078/0.078/0.078/0.078/0.078 (n=1) |
| VISION/all_observed/success asr_enqueue_to_first_submit_ms | 14121.722/14121.722/14121.722/14121.722/14121.722 (n=1) |
| VISION/all_observed/success asr_enqueue_to_playback_end_ms | 18356.414/18356.414/18356.414/18356.414/18356.414 (n=1) |
| latest_get | 0.001/0.001/0.001/0.001/0.001 (n=1) |
| preprocess_fused | 8.695/8.695/8.695/8.695/8.695 (n=1) |
| rknn_input_descriptor | 0.000/0.000/0.000/0.000/0.000 (n=1) |
| rknn_inputs_set | 17.151/17.151/17.151/17.151/17.151 (n=1) |
| rknn_run | 1184.460/1184.460/1184.460/1184.460/1184.460 (n=1) |
| rknn_outputs_get | 1.283/1.283/1.283/1.283/1.283 (n=1) |
| embedding_alloc_copy | 0.176/0.176/0.176/0.176/0.176 (n=1) |
| rknn_outputs_release | 0.006/0.006/0.006/0.006/0.006 (n=1) |

### gui_mixed_1800s_4t_final_v2/run_20261017_165918_816_a1845db32d1644028f53ab0f0eb2d172

实际最终计数：`{"FramePool": {"allocated": 2, "in_use": 0, "acquired": 54398, "reused": 54396, "exhausted": 0}, "CameraCounters": {"published": 54397, "fps": 29.9952, "timeouts": 0, "driver_sequence_gaps": 1, "pool_discarded": 0}, "AudioQueueStats": {"pushed": 121, "popped": 121, "dropped": 0, "rejected_closed": 0, "peak": 1, "pending": 0}, "QueueStats/inference": {"stage": "inference", "generation": 1, "accepted": 121, "completed": 121, "started": 121, "failed": 0, "cancelled": 0, "expired": 0, "rejected_full": 0, "rejected_stopped": 0, "peak": 1, "pending": 0, "active": 0, "callback_errors": 0, "queue_sum_ms": 10.3541, "queue_max_ms": 1.62733, "service_sum_ms": 144120}, "QueueStats/tts": {"stage": "tts", "generation": 1, "accepted": 121, "completed": 121, "started": 121, "failed": 0, "cancelled": 0, "expired": 0, "rejected_full": 0, "rejected_stopped": 0, "peak": 1, "pending": 0, "active": 0, "callback_errors": 0, "queue_sum_ms": 5207.94, "queue_max_ms": 352.063, "service_sum_ms": 1412040.0}, "PipelineStats": {"dispatched": 121, "accepted": 121, "rejected": 0, "inflight": 0, "peak": 2, "limit": 2, "vision_accepted": 60, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0}}`。

| 指标 | 真实统计 |
|---|---|
| TEXT/initial_5min/success asr_rtf | 0.371/0.369/0.386/0.367/0.386 (n=11) |
| TEXT/initial_5min/success inference_service_ms | 887.970/869.762/1139.843/824.914/1139.843 (n=11) |
| TEXT/initial_5min/success tts_generate_api_ms | 6656.969/6701.316/6910.119/6281.554/6910.119 (n=11) |
| TEXT/initial_5min/success tts_rtf | 3.406/3.441/3.535/3.213/3.535 (n=11) |
| TEXT/initial_5min/success tts_queue_ms | 0.231/0.127/1.172/0.061/1.172 (n=11) |
| TEXT/initial_5min/success asr_enqueue_to_first_submit_ms | 8132.759/8144.167/8365.260/7766.734/8365.260 (n=11) |
| TEXT/initial_5min/success asr_enqueue_to_playback_end_ms | 10117.413/10128.731/10349.876/9751.509/10349.876 (n=11) |
| VISION/initial_5min/success asr_rtf | 0.398/0.398/0.402/0.395/0.402 (n=9) |
| VISION/initial_5min/success inference_service_ms | 1555.750/1530.691/1754.321/1483.225/1754.321 (n=9) |
| VISION/initial_5min/success tts_generate_api_ms | 10591.360/10579.876/10827.245/10182.274/10827.245 (n=9) |
| VISION/initial_5min/success tts_rtf | 3.148/3.144/3.218/3.025/3.218 (n=9) |
| VISION/initial_5min/success tts_queue_ms | 0.041/0.035/0.085/0.023/0.085 (n=9) |
| VISION/initial_5min/success asr_enqueue_to_first_submit_ms | 12687.884/12643.812/12916.998/12480.087/12916.998 (n=9) |
| VISION/initial_5min/success asr_enqueue_to_playback_end_ms | 16047.637/16004.367/16277.438/15839.690/16277.438 (n=9) |
| VISION/warm_after_5min/success asr_rtf | 0.397/0.397/0.404/0.391/0.406 (n=51) |
| VISION/warm_after_5min/success inference_service_ms | 1514.684/1514.735/1547.570/1474.182/1564.324 (n=51) |
| VISION/warm_after_5min/success tts_generate_api_ms | 11115.807/11096.835/11334.229/10754.742/11392.743 (n=51) |
| VISION/warm_after_5min/success tts_rtf | 3.304/3.300/3.371/3.196/3.388 (n=51) |
| VISION/warm_after_5min/success tts_queue_ms | 0.061/0.070/0.092/0.024/0.107 (n=51) |
| VISION/warm_after_5min/success asr_enqueue_to_first_submit_ms | 13170.243/13150.932/13382.171/12812.704/13421.172 (n=51) |
| VISION/warm_after_5min/success asr_enqueue_to_playback_end_ms | 16532.403/16510.774/16742.080/16172.781/16780.728 (n=51) |
| TEXT/warm_after_5min/success asr_rtf | 0.370/0.370/0.372/0.364/0.377 (n=50) |
| TEXT/warm_after_5min/success inference_service_ms | 861.943/856.393/893.807/826.657/1005.577 (n=50) |
| TEXT/warm_after_5min/success tts_generate_api_ms | 7073.613/7126.916/7199.977/6831.765/7311.876 (n=50) |
| TEXT/warm_after_5min/success tts_rtf | 3.620/3.644/3.682/3.489/3.740 (n=50) |
| TEXT/warm_after_5min/success tts_queue_ms | 104.038/58.049/304.655/0.042/352.063 (n=50) |
| TEXT/warm_after_5min/success asr_enqueue_to_first_submit_ms | 8624.309/8636.503/8940.160/8259.332/8970.232 (n=50) |
| TEXT/warm_after_5min/success asr_enqueue_to_playback_end_ms | 10608.991/10621.673/10924.451/10243.597/10955.437 (n=50) |
| preprocess_fused | 7.734/7.698/7.972/7.629/8.246 (n=60) |
| rknn_input_descriptor | 0.000/0.000/0.000/0.000/0.001 (n=60) |
| rknn_inputs_set | 10.291/10.214/10.260/10.168/14.769 (n=60) |
| rknn_run | 1171.226/1169.580/1180.930/1165.410/1184.310 (n=60) |
| rknn_outputs_get | 0.759/0.794/0.913/0.168/1.335 (n=60) |
| embedding_alloc_copy | 0.108/0.107/0.138/0.031/0.473 (n=60) |
| rknn_outputs_release | 0.003/0.003/0.005/0.001/0.010 (n=60) |

后台CPU/RSS/线程/温度完整统计记录在analysis/performance.json和stability_resources.csv，GUI父进程另有资源样本，不能只报GUI几十MiB来冒充整机占用。

### Camera序号缺口复核

最终Qt长测Camera发布54397帧，29.9952FPS，记录1次driver_sequence_gaps，pool_discarded=0、timeout=0，不能称零丢帧。源码video_capture.cpp在DQBUF成功后比较驱动sequence差值，大于1才计缺口；pool满时的显式discard另外计数，重启时have_sequence重置。现有代码没有记录每次缺口的发生时间，因此无法从总计数定位唯一时刻，更不能编造CPU饥饿或硬件故障根因。

追加使用最终已有stage5_03_memory_probe，不改生产源码、内核或设备配置，64次真实最新Camera/VLM调用全部成功，持续112.841秒，3337帧29.9528FPS，驱动序号缺口0、pool满丢弃0、timeout0。较早长测1次缺口保留为未确定具体原因的非致命风险，不把未复现写成已修复；功能闭环成功不等于严格零丢帧。

| 64次真实最新帧指标 | 均值/P50/P95/最小/最大(n) ms |
|---|---|
| frame_age_ms | 24.797/26.313/39.243/7.905/42.910 (n=64) |
| get_latest_wall_ms | 0.001/0.001/0.001/0.001/0.002 (n=64) |
| vlm_ms | 1705.083/1691.650/1838.400/1633.260/1901.170 (n=64) |

该复核只测真实Camera与VLM，不包含ASR/Qwen/TTS，也没有每帧语义人工标注。内核日志完整保留于camera_gap_recheck与protection_final_after_camera，未发现该窗口新增OOM、segfault、RKNPU失败等匹配项；Camera具体单帧缺口仍未归因。

ASR打印RTF按ASRService内部创建stream至结果文本复制后的latency_ms除以16kHz语音时长计算，结束点在unique_ptr清理前；asr_begin→asr_end是外层recognize调用墙钟，包含返回前Result/Stream清理，因此两者不应强行相等。纯Decode区间另列asr_decode_ms，不把整个API耗时冒充单个NPU或CPU算子。自然麦克风的VAD语音起/止是主机估计，不是ADC硬件时间戳；完整阶段见requests.csv。固定输入没有VAD事件时保持空。真实声学输出延迟、精确单token TTFT、可信NPU利用率/带宽/功耗仍未测量。RKNN run与整体VLM时长分列，首次文本chunk不能改称精确首token。

## 8 退出背压异常及设备释放

| 实际case | 退出码 | 信号到退出秒数 | 终态与清理 |
|---|---|---|---|
| final_burst_audio | None | None | devices=None forced=None；{} |
| final_burst_audio_retry1 | 0 | 0.9888364610014833 | devices=True forced=False；{"dispatched": 4, "accepted": 2, "rejected": 2, "inflight": 0, "peak": 2, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0} |
| final_expiry_audio | 0 | 1.8983000090011046 | devices=True forced=False；{"dispatched": 2, "accepted": 2, "rejected": 0, "inflight": 0, "peak": 2, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 1} |
| final_sigint_asr | 0 | 16.53417446199819 | devices=True forced=False；{"dispatched": 1, "accepted": 1, "rejected": 0, "inflight": 0, "peak": 1, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0} |
| final_sigint_drain | 0 | 16.129876066999714 | devices=True forced=False；{"dispatched": 1, "accepted": 1, "rejected": 0, "inflight": 0, "peak": 1, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0} |
| final_sigterm_cancel_waiting | 0 | 12.02652530100022 | devices=True forced=False；{"dispatched": 2, "accepted": 2, "rejected": 0, "inflight": 0, "peak": 2, "limit": 2, "vision_accepted": 1, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 1, "tts_expired": 0} |
| final_sigterm_initialization | 0 | 23.54417397299767 | devices=True forced=False；{"dispatched": 0, "accepted": 0, "rejected": 0, "inflight": 0, "peak": 0, "limit": 2, "vision_accepted": 0, "vision_rejected": 0, "llm_cancelled": 0, "llm_expired": 0, "vision_cancelled": 0, "vision_expired": 0, "cancelled_before_submit": 0, "downstream_cancelled": 0, "tts_cancelled": 0, "tts_expired": 0} |
| 真实故障输入 | 真实退出码 | 秒数 | 设备释放与预期失败 |
|---|---|---|---|
| microphone_missing | 1 | 23.901 | True / True |
| camera_missing | 1 | 21.549 | True / True |
| playback_missing | 1 | 19.739 | True / True |
| asr_model_missing | 1 | 0.481 | True / True |

真实非法路径只验证打开/初始化失败的清理，不模拟拔掉设备、内核故障或SDK内存破坏。ASR推理异常、Camera超时/异常、TTS失败/抛异常/无效PCM、播放失败和后续恢复通过Fake验证；真实运行期间没有人为破坏设备。取消等待不强行打断已进入SDK的活动请求；排空停止输入后完成已经接收任务。超时和拒绝不算推理成功。生命周期检查结合完整shutdown日志、队列pending/active=0、pool in_use=0、进程消失与fuser/ALSA状态，不能只看exit0。

## 9 实际问题与修复记录

真实长测中2线程请求86/104、4线程41/107等stdout诊断插入流式回答；后台完整字符串和合成内容未受影响，但直接用终端解析GUI会错。修复是在既有ImageProfile互斥JSONL中一次写入完整UTF8识别/回答，明确input_text与asr_text，GUI读取该结构化通道；原始stdout保留诊断。控制字符转义、50并发文本和模型真实回答均检查，未改变模型输出。

最终文档复核还发现一处历史检查脚本的空路径漏洞：5.4的source_invariants列过并不存在的src/ai/inference_worker.cpp，前后都不存在时旧sha辅助函数都返回null，误显示unchanged。真实InferenceWorker是include/ai/llm_worker.h中LLMWorker的using别名，实现在llm_worker.cpp；5.5已改为校验这两个真实文件并强制两侧存在。历史JSON保留原样，并未借此否定另有96项真实SHA匹配的5.4验收；本节记录这个检查自身的局限并修正。

长测中段真实fd快照还显示RKNN/RKLLM打开/dev/dri/card1，GUI自身没有Camera/ALSA/NPU句柄；早期fuser仅查对应renderD129，NPU占用检查范围不足。保留旧工具，5.5统一补查同rknpu驱动的card和render节点。新增primary检查先拒绝了systemd/logind/Xorg既有桌面句柄，AI程序尚未启动；保留这次工具保护中止。随后只读核实PID1/932/1619，固定PID、启动标识、UID及命令行，Xorg真实UID为1000而fuser显示其有效root身份。Camera/ALSA/render必须为空，primary只允许这组精确基线，未知进程仍拒绝；不结束系统服务。最终CLI故障/生命周期与保护检查使用这一严格前后对照，资源释放指本次AI句柄消失并恢复桌面基线，不能说所有primary句柄都关闭。较早退出进程已消失、销毁日志仍有效，但不能声称当时已经查询过card1。GUI与后台主线程实际SigBlk均0x4002，即SIGINT与SIGTERM被阻塞，由普通sigwait线程处理。

首轮GUI监控使用/proc/PID/task/PID/children，但本内核没有该文件，首轮mic及首轮paired无后台资源采样；不填造这些数据。修复监控工具为PPid查询并核实exe/start-token，原工具保存在gui_sampler_original.py，最终长测包含GUI和后台分开采样。这个工具修复没有更改已构建生产源码。

主机绘图旧matplotlib不支持tick_labels，改labels后重跑；Git全局docx textconv曾使差异变成文本抽取，字节回放失败，保留失败JSON后禁用--no-textconv/--no-ext-diff，二进制补丁回放成功；Word沙箱COM失败，使用已授权原生Word导出；初次Word对象HWND为空改用Document.ActiveWindow.Hwnd。打包renderer缺少LibreOffice，保留错误并用现有Word生成PDF后复用同一renderer光栅化。没有安装软件，不终止用户原Word进程。所有失败实验保留，不能作为成功运行计数。

## 10 保护复现与交付结论

最终保护核对原稳定321项SHA/大小/mtime、四个历史可执行文件、冻结5.4和本节源码、设备、内存/磁盘及内核错误窗口。最新保护结果以protection_final_after_camera/result.json为准，较早protection_final保留。Camera/ALSA/render无持有者，primary恢复精确桌面基线；原稳定321项及四个历史程序均一致。测试结束磁盘剩余1,740,128,256字节，归档后的空间另见final_delivery_receipt.json。所有写入仅隔离目录；SDK/模型按原有路径读取，没有删除、覆盖模型或修改系统配置。

运行说明见README_STAGE5_FINAL.md和tools/stage5_05_launch_gui.sh；重要命令逐项说明见stage5_05_commands.md；完整前后源码见stage5_05_source_appendix.md；关键语句与寿命见stage5_05_statement_notes.md；12道完整问答见stage5_05_interview.md。最终Word和Markdown手册共同源自RK3576_STAGE5_ENGINEERING_MANUAL.md，包含5.1～5.5及可复核性能成果、真实局限和简历表述。Git格式patch通过全新临时树apply和逐字节SHA回放，不虚构Git提交。

考虑到已出现Linux热限频，本轮不继续扩大为单进程60分钟负载。没有单进程60分钟验收；本节完成记录中的2/4线程各约30分钟对照和最终GUI约30分钟时，仍只支持有限工况。当前VISION入口把中文识别结果用于路由，向VLM提交固定英文问题`What do you see? Answer briefly.`，不宣称支持任意中文视觉问题原样推理。Frame Age基于现有主机采集时间戳，不是传感器曝光时间。未实现RGA生产路径或DMA-BUF端到端零拷贝；TTS RTF仍>1、播放与合成仍串行、没有AEC/PTT/语音打断。原稳定版本升级须另经用户审核，当前不执行。

### 最终工程判定

记录工况内工程检查通过，具备提交最终用户审核条件。5.1～5.4保持原验收成果，本节未覆盖稳定主工程。完整机器检查项在validation_summary.json；Word逐页检查和最终归档收据单独核对。未完成单进程60分钟、高占空比任意散热、真实拔插故障或声学仪器测量，不扩大结论。

