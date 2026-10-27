"""Create the Stage5.5 report directly from the collected raw observations."""
from pathlib import Path
import json,shlex,re,csv
from stage5_05_analyze import stats
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def fmt(s):
 if not s:return '未测量'
 return '/'.join(f'{s[k]:.3f}' for k in ['mean','p50','p95','minimum','maximum'])+f" (n={s['n']})"
def main():
 local=ROOT/'reports/stage5_05_local';perf=load(local/'analysis/performance.json');st=load(local/'analysis/stability.json');cases=perf['cases'];base=Path(perf['collection']).resolve()/'files/reports/stage5_05_board'
 sections=[]
 def add(s):sections.append(s.strip()+'\n\n')
 add('# 5.5 Qt 集成与最终系统工程验收报告')
 add('本报告记录2026年10月17日至18日香港时间在同一台RK3576隔离工程的真实开发与验证。5.1～5.4已经用户验收；本节工程检查结果以validation_summary.json为准，最终用户审核仍待确认。没有将隔离版本覆盖为原稳定工程。有限长测只支持记录工况内结论。')
 add('## 1 继承版本与实际改动')
 add('先以SHA256核对5.4最终v3的96项源码，再冻结171项源码、工具、测试、配置与文档至backups/stage5_05_before。原稳定目录321项、5.1～5.4四个已验收程序和5.4源码分别留存清单。最终生产源码104项位于stage5_05_source_final_v2，构建为build/stage5_05_final_v2。较早stage5_05_source_thermal仅放宽原CLI记录秒数及回放偏移上限，用于同版本2/4线程热对照；不能拿它冒充最后Qt与结构化日志版本。final_v1、qt_v1是未部署的本地中间快照。')
 add('最小改动：CMake增加默认关闭的BUILD_QT_GUI；StopSignals类正文从CLI原样移到共用头文件；CLI监听上限120→3600秒、回放偏移上限120000→3600000ms，默认12秒和20ms信号轮询不变；复用ImageProfile的steady_clock、mutex和JSONL新增完整识别/回答字符串事件。5.3池、图像预处理、RKNN/RKLLM后端、TTS合成与播放算法及5.2队列保持字节不变，未更换模型或生成参数。')
 add('实际语音入口VADAudioWorker→音频段队列→ASRWorker→IntentRouter→额度管理→单消费者InferenceWorker→Qwen或Camera/RKNN/SmolVLM2→TTSWorker/Kokoro/ALSA，没有经过另一个CLI入口的RequestProcessor。Qt通过QProcess复用完整入口，后台原线程运行模型与设备；Qt主线程只处理事件、有限日志和控件，不进行SDK加载、推理或等待音频。')
 add('![最终线程架构](../reports/stage5_05_local/plots/system_architecture.png)')
 add('![Camera Buffer 生命周期](../reports/stage5_05_local/plots/buffer_lifecycle.png)')
 add('![退出与销毁顺序](../reports/stage5_05_local/plots/shutdown_order.png)')
 add('## 2 Qt 运行环境与实际验收')
 add('板端已有Qt5.15.8 Widgets/Test、头文件、平台插件和GNOME/X11 DISPLAY :0；DSI已连接。本节没有安装系统软件、迁移车载工程、修改显示或权限配置。实际运行采用xcb与现有cat认证。QWidget::grab截取本次真实窗口，未生成模拟截图。启动时libGL报告rockchip DRI加载失败，但普通Widgets页面正常显示；这不能视为硬件OpenGL渲染已验证。Kokoro已有未知token/phoneme警告如实保留，不等于本节新引入崩溃。')
 add('GUI显示五模块、识别、TEXT/VISION、完整回答、阶段、队列事件快照、错误、ASR/推理/TTS/首次提交延迟。选项支持2/4线程及排空/取消等待。活动时禁止更改配置，关闭事件先ignore→SIGINT→等待QProcess finished→关闭窗口；90秒未退出报告失败，不把强杀算作成功。信号在QApplication及SDK线程创建前阻塞，由普通sigwait线程接收；没有异步handler调用Qt或锁。QProcess连接带QObject context，正常窗口关闭先等待后台，避免回调触达已销毁对象。重新开始是新进程和新UUID目录，并非宣称闭源SDK实例内重启。')
 for name in ['gui_microphone_final_v2','gui_paired_restart_final_v2','gui_sigterm_vision_final_v2','gui_mixed_1800s_4t_final_v2']:
  if name in cases:
   x=cases[name]['result'];add(f"实际case `{name}`：退出码{x['returncode']}，持续{x['duration_seconds']:.3f}秒，所有会话有序退出={x['all_sessions_orderly']}，强制终止={x['forced_kill']}，设备释放={x['devices_released']}。原始记录：`{(base/name/'result.json').as_posix()}`。")
 if 'gui_mixed_1800s_4t_final_v2' in cases:
  rows=['| 最终进程 | CPU平均/P95 %（80s后） | RSS峰值MiB | VmHWM观测峰值MiB | 线程峰值 | 温度峰值℃ |','|---|---|---|---|---|---|']
  for name,c in cases.items():
   if not name.startswith('gui_mixed_1800s_4t_final_v2'):continue
   res=c.get('resources')
   if not res:continue
   cpu=res.get('cpu_percent_after_80s');temperature=max((x['maximum'] for x in res.get('temperature_C',{}).values()),default=None)
   rows.append('| '+('后台AI' if '/run_' in name else 'Qt父进程')+' | '+(f"{cpu['mean']:.2f}/{cpu['p95']:.2f}" if cpu else '未测量')+f" | {res['rss_MiB']['maximum']:.3f} | {res['VmHWM_observed_MiB']['maximum']:.3f} | {res['threads']['maximum']} | {temperature} |")
  add('\n'.join(rows))
 feedback=base/'gui_microphone_final_v2/user_feedback.json'
 if feedback.exists():
  f=load(feedback);add('本次人工确认原文：“'+f['user_exact_reply']+'”。针对该轮明确问题，已记录两个回答均通过HyperX实际听到、视觉描述大致相符、Qt显示识别文本/路由/回答。不能将程序success=true替代这份确认。自然语音仅TEXT/VISION各1条，不能据此推导大样本音质或识别率。')
 for name,caption in [('gui_listening','本次真实xcb界面进入监听'),('gui_answer_2','本次真实视觉回答和延迟'),('gui_finished','本次有序停止后的真实界面')]:
  if (local/'figures'/f'{name}.png').exists():add(f'![{caption}](../reports/stage5_05_local/figures/{name}.png)')
 add('## 3 ARM64 构建和确定性测试')
 for name in ['build_thermal','build_final_v2']:
  if name not in cases:continue
  x=cases[name]['result'];targets=re.findall(r'Built target (\S+)',(base/name/'build.stdout.log').read_text(encoding='utf-8',errors='replace'));add(f"`{name}`：成功={x['successful']}，去重目标{len(set(targets))}个；各步骤真实记录：`"+json.dumps(x['steps'],ensure_ascii=False)+'`。')
 add('| 注册测试 | 具体验证 | 实际SDK边界 |\n|---|---|---|\n| request_profile_tests | 固定音频输入与请求计时、UTF8/控制字符转义、并发完整文本事件 | 无模型 |\n| image_pipeline_tests | stride、池复用、weak_ptr生命周期、缓存RGB与像素一致 | CPU/Fake帧 |\n| async_pipeline_tests | 连续/交替、满载、取消、过期、停止重启、推理和TTS/播放异常后恢复 | Fake Backend/Service |\n| asr_pipeline_tests | 空队列停止唤醒、ASR异常与回调异常、队列终态 | Fake ASR |\n| audio_preprocessor_tests | 音频转换与边界 | CPU |\n| llm_worker_tests | 生命周期、停止/重启、异常和回调 | Fake LLM |\n| camera_service_tests | 打开失败、超时、异常、停止、重启和帧所有权 | Fake Camera |\n| gui_session_tests | 主线程心跳、显示、无覆盖启动、错误恢复、停止/重启、活跃窗口关闭、关闭优先于自动重启 | offscreen Qt与明确Fake子进程 |')
 add('最终ARM64 CTest的8项通过与Windows portable 9项分别保存；它们是确定性逻辑测试，真实SDK和硬件回归另列。编译残留未使用函数、测试缩进和RGA SDK匿名struct警告保留，不能改写成零警告。')
 add('## 4 热测试条件与安全边界')
 add('同板、同模型/Runtime、相同真实语音段和固定NV12、相同推理参数，2/4线程依次180秒短测、1800秒混合输入长测。所有读到的zone低于55℃才开始，最长冷却600秒；保持ondemand、不改CPU频率、亲和性或风扇。长测每15秒一个输入，TEXT/TEXT/VISION/VISION/TEXT/VISION循环，共121条；生产TTS等待12秒、请求期限45秒，排队满载明确拒绝。固定音频绕过麦克风/VAD，Camera真实持续采集，但Vision读取同一固定帧，因此固定场景Frame Age未测量。')
 add('实际thermal_zone2 little passive为75℃/85℃，critical为115℃。这些是Linux当前配置，不是芯片额定安全温度证明。测试护栏为任一温度≥90℃、温度不可读、MemAvailable<256MiB或磁盘<500MiB立即向确认PID发SIGTERM；有限宽限后若仍卡住，只能强制终止本次确认PID并记失败。实际没有修改thermal/sysfs配置。采样每秒，smaps约每5次；CPU按一核100%，HZ来自本板sysconf。')
 add('| 真实case | 进程秒数 | 输入/完成 | 峰值温度℃ |\n|---|---|---|---|')
 for name in ['mixed_180s_2t','mixed_180s_4t','mixed_1800s_2t','mixed_1800s_4t']:
  if name not in cases:continue
  c=cases[name];res=c['resources'];temp=max(s['maximum'] for s in res['temperature_C'].values());ctr=c['terminal_counters'];cpu=res['cpu_percent_after_80s'];add(f"| {name} | {c['result']['duration_seconds']:.3f} | {ctr['PipelineStats']['dispatched']}/{ctr['QueueStats/tts']['completed']} | {temp:.3f} |")
 rows=['| 同一case资源 | 峰值RSS MiB | CPU均值/P95 %（80s后） | 峰值线程 |','|---|---|---|---|']
 for name in ['mixed_180s_2t','mixed_180s_4t','mixed_1800s_2t','mixed_1800s_4t']:
  c=cases[name];res=c['resources'];cpu=res['cpu_percent_after_80s'];rows.append(f"| {name} | {res['rss_MiB']['maximum']:.3f} | {cpu['mean']:.2f}/{cpu['p95']:.2f} | {res['threads']['maximum']} |")
 add('\n'.join(rows))
 # Consecutive rows must remain one Markdown table.
 add('2/4线程长测TSV的SHA均为`5e9f356f3647cdcdbbb31117e0a312f65bee2f9abe58d43e4bf570dd932585b7`，121行。两轮每条成功完成，失败/超时/拒绝/丢弃均为0，队列峰值1、在途峰值2，Camera均29.997FPS。原始队列计数、资源样本及统计口径在CSV/JSON。2线程最高86.777℃，4线程85.888℃；此节奏混合负载不能据此推论4线程总是更凉。5.4连续独立合成中4线程更热，两类负载占空比与DVFS不同。')
 add('## 5 热对照的暖态延迟分布')
 add('请求暖态边界从首个asr_enqueued起算5分钟，RSS趋势则从进程首次资源采样起算，二者不混用。每轮前5分钟请求单列，以下仅warm_after_5min：TEXT n50、VISION n51。时间单位ms，格式为均值/P50/P95/最小/最大(n)。合成输出长度可能略变，额外按每条实际PCM长度计算RTF；不混合中英文回答直接算模型加速。首次提交是ALSA write调用边界，drain是软件排空，均非直接声学测量。')
 for route in ['TEXT','VISION']:
  add('### '+route+' 同输入路线对照')
  rows=['| 指标 | 2线程 | 4线程 |','|---|---|---|']
  for metric in ['asr_rtf','asr_decode_ms','asr_api_ms','inference_queue_ms','inference_service_ms','tts_queue_ms','tts_generate_api_ms','tts_rtf','synthesis_to_first_submit_ms','asr_enqueue_to_first_submit_ms','asr_enqueue_to_playback_end_ms']:
   vals=[]
   for n in ['mixed_1800s_2t','mixed_1800s_4t']:vals.append(fmt(st['cases'][n]['metrics'].get(route+'/warm_after_5min/success',{}).get(metric)))
   rows.append('| '+metric+' | '+' | '.join(vals)+' |')
  add('\n'.join(rows))
 add('4线程在本次混合工况下ASR没有出现饥饿：TEXT平均ASR RTF约0.446→0.370，VISION约0.465→0.399。模型计算、调度、温度和输入节奏共同作用，不能从这些非随机交叉的整系统数据归因每个子系统必然加速。两边都是每15秒到达，30分钟总体完成数相同，不宣称吞吐提升30%。TTS纯同条件计算收益仍引用5.4固定文本各语言n30的30.42%/29.74%，不篡改比较条件。')
 for name,caption in [('thermal_cpu_memory','实际热与CPU及频率时间序列'),('warm_rtf','暖态请求RTF分布'),('warmed_rss','预热后的RSS分段变化')]:add(f'![{caption}](../reports/stage5_05_local/plots/{name}.png)')
 add('## 6 RSS趋势与Linux降频证据')
 for name in ['mixed_1800s_2t','mixed_1800s_4t']:
  trend=st['cases'][name]['resources'];add(f"`{name}`：5～30分钟RSS斜率{trend['RSS_slope_MiB_per_minute']:.6f} MiB/min，5～10分钟中位数{trend['median_5_to_10min_MiB']:.3f} MiB，25～30分钟中位数{trend['median_25_to_30min_MiB']:.3f} MiB。排除初次模型页驻留与退出下降，不用开始/结束两个点证明无泄漏。")
  rows=['| cooling设备或频率 | 实际读数 |','|---|---|']
  for path,value in trend['cooling'].items():rows.append(f"| {path} | 最大state={value['max_state']}，positive={value['positive_samples']}/{value['samples']} |")
  for path,value in trend['scaling_max_frequency_kHz'].items():
   if '/cpu0/' in path or '/cpu4/' in path:rows.append(f"| {path} | min={value['minimum']:.0f}，max={value['maximum']:.0f} kHz |")
  add('\n'.join(rows))
 add('cooling_device0/1对应cpufreq-cpu0/cpu4，2对应devfreq GPU，3为devfreq-dmc，4为devfreq NPU，以实际inventory type为准。CPU cooling为正并伴随scaling_max_freq收紧，支持发生Linux热管理限频；仅ondemand的scaling_cur_freq变化不能单独证明热降频。GPU cooling为正不能冒充CPU降频。本轮有热管理活动，但未出现90℃护栏、崩溃、明显ASR饥饿或持续RSS增长，默认保留4线程，2线程可回退。这个选择仅适用于现有散热与记录负载，更高占空比应再测。')
 add('4线程较早加载后的RSS增加不直接判为泄漏。中段与末段真实smaps映射比较：DRI RSS 1,369,584kB、heap 903,064kB、匿名映射424,592kB、video11 48,608kB保持一致，小量变化集中于文件映射页；暖态中位数仅约0.516MiB变化，未见该窗口持续堆/匿名增长。4线程比2线程峰值约多64MiB。没有LeakSanitizer/闭源SDK泄漏证明，不能写“系统绝无内存泄漏”。')
 add('## 7 最终源码性能与自然输入复核')
 for name,c in cases.items():
  if '/run_' not in name or not any(k in name for k in ['gui_mixed_1800s_','gui_microphone_']):continue
  add('### '+name)
  ctr=c.get('terminal_counters',{});add('实际最终计数：`'+json.dumps(ctr,ensure_ascii=False)+'`。')
  metrics=c.get('request_metrics',{});rows=['| 指标 | 真实统计 |','|---|---|']
  # request_metrics uses route-prefixed groups; retain exact schema as evidence.
  for group,values in st['cases'].get(name,{}).get('metrics',{}).items():
   for key in ['frame_age_ms','asr_rtf','inference_service_ms','tts_generate_api_ms','tts_rtf','tts_queue_ms','asr_enqueue_to_first_submit_ms','asr_enqueue_to_playback_end_ms']:
    if values.get(key):rows.append(f'| {group} {key} | {fmt(values[key])} |')
  for key,value in c.get('image_stages',{}).items():rows.append(f'| {key} | {fmt(value)} |')
  add('\n'.join(rows))
  if c.get('resources'):add('后台CPU/RSS/线程/温度完整统计记录在analysis/performance.json和stability_resources.csv，GUI父进程另有资源样本，不能只报GUI几十MiB来冒充整机占用。')
 if 'camera_gap_recheck' in cases:
  c=cases['camera_gap_recheck'];rows=list(csv.DictReader((base/'camera_gap_recheck/requests.csv').open(encoding='utf-8')))
  add('### Camera序号缺口复核')
  add('最终Qt长测Camera发布54397帧，29.9952FPS，记录1次driver_sequence_gaps，pool_discarded=0、timeout=0，不能称零丢帧。源码video_capture.cpp在DQBUF成功后比较驱动sequence差值，大于1才计缺口；pool满时的显式discard另外计数，重启时have_sequence重置。现有代码没有记录每次缺口的发生时间，因此无法从总计数定位唯一时刻，更不能编造CPU饥饿或硬件故障根因。')
  add('追加使用最终已有stage5_03_memory_probe，不改生产源码、内核或设备配置，64次真实最新Camera/VLM调用全部成功，持续112.841秒，3337帧29.9528FPS，驱动序号缺口0、pool满丢弃0、timeout0。较早长测1次缺口保留为未确定具体原因的非致命风险，不把未复现写成已修复；功能闭环成功不等于严格零丢帧。')
  lines=['| 64次真实最新帧指标 | 均值/P50/P95/最小/最大(n) ms |','|---|---|']
  for key in ['frame_age_ms','get_latest_wall_ms','vlm_ms']:lines.append('| '+key+' | '+fmt(stats([float(x[key]) for x in rows]))+' |')
  add('\n'.join(lines))
  add('该复核只测真实Camera与VLM，不包含ASR/Qwen/TTS，也没有每帧语义人工标注。内核日志完整保留于camera_gap_recheck与protection_final_after_camera，未发现该窗口新增OOM、segfault、RKNPU失败等匹配项；Camera具体单帧缺口仍未归因。')
 add('ASR打印RTF按ASRService内部创建stream至结果文本复制后的latency_ms除以16kHz语音时长计算，结束点在unique_ptr清理前；asr_begin→asr_end是外层recognize调用墙钟，包含返回前Result/Stream清理，因此两者不应强行相等。纯Decode区间另列asr_decode_ms，不把整个API耗时冒充单个NPU或CPU算子。自然麦克风的VAD语音起/止是主机估计，不是ADC硬件时间戳；完整阶段见requests.csv。固定输入没有VAD事件时保持空。真实声学输出延迟、精确单token TTFT、可信NPU利用率/带宽/功耗仍未测量。RKNN run与整体VLM时长分列，首次文本chunk不能改称精确首token。')
 add('## 8 退出背压异常及设备释放')
 rows=['| 实际case | 退出码 | 信号到退出秒数 | 终态与清理 |','|---|---|---|---|']
 for name,c in cases.items():
  if not name.startswith('final_') or 'returncode' not in c.get('result',{}):continue
  x=c['result'];rows.append(f"| {name} | {x['returncode']} | {x.get('signal_to_exit_seconds')} | devices={x.get('devices_released')} forced={x.get('forced_kill')}；{json.dumps(c.get('terminal_counters',{}).get('PipelineStats',{}),ensure_ascii=False)} |")
 add('\n'.join(rows))
 faults=base/'real_invalid_paths/result.json'
 if faults.exists():
  x=load(faults);rows=['| 真实故障输入 | 真实退出码 | 秒数 | 设备释放与预期失败 |','|---|---|---|---|']
  for c in x['cases']:rows.append(f"| {c['case']} | {c['returncode']} | {c['duration_seconds']:.3f} | {c['devices_released']} / {c['expected_failure_clean']} |")
  add('\n'.join(rows))
 add('真实非法路径只验证打开/初始化失败的清理，不模拟拔掉设备、内核故障或SDK内存破坏。ASR推理异常、Camera超时/异常、TTS失败/抛异常/无效PCM、播放失败和后续恢复通过Fake验证；真实运行期间没有人为破坏设备。取消等待不强行打断已进入SDK的活动请求；排空停止输入后完成已经接收任务。超时和拒绝不算推理成功。生命周期检查结合完整shutdown日志、队列pending/active=0、pool in_use=0、进程消失与fuser/ALSA状态，不能只看exit0。')
 add('## 9 实际问题与修复记录')
 add('真实长测中2线程请求86/104、4线程41/107等stdout诊断插入流式回答；后台完整字符串和合成内容未受影响，但直接用终端解析GUI会错。修复是在既有ImageProfile互斥JSONL中一次写入完整UTF8识别/回答，明确input_text与asr_text，GUI读取该结构化通道；原始stdout保留诊断。控制字符转义、50并发文本和模型真实回答均检查，未改变模型输出。')
 add('最终文档复核还发现一处历史检查脚本的空路径漏洞：5.4的source_invariants列过并不存在的src/ai/inference_worker.cpp，前后都不存在时旧sha辅助函数都返回null，误显示unchanged。真实InferenceWorker是include/ai/llm_worker.h中LLMWorker的using别名，实现在llm_worker.cpp；5.5已改为校验这两个真实文件并强制两侧存在。历史JSON保留原样，并未借此否定另有96项真实SHA匹配的5.4验收；本节记录这个检查自身的局限并修正。')
 add('长测中段真实fd快照还显示RKNN/RKLLM打开/dev/dri/card1，GUI自身没有Camera/ALSA/NPU句柄；早期fuser仅查对应renderD129，NPU占用检查范围不足。保留旧工具，5.5统一补查同rknpu驱动的card和render节点。新增primary检查先拒绝了systemd/logind/Xorg既有桌面句柄，AI程序尚未启动；保留这次工具保护中止。随后只读核实PID1/932/1619，固定PID、启动标识、UID及命令行，Xorg真实UID为1000而fuser显示其有效root身份。Camera/ALSA/render必须为空，primary只允许这组精确基线，未知进程仍拒绝；不结束系统服务。最终CLI故障/生命周期与保护检查使用这一严格前后对照，资源释放指本次AI句柄消失并恢复桌面基线，不能说所有primary句柄都关闭。较早退出进程已消失、销毁日志仍有效，但不能声称当时已经查询过card1。GUI与后台主线程实际SigBlk均0x4002，即SIGINT与SIGTERM被阻塞，由普通sigwait线程处理。')
 add('首轮GUI监控使用/proc/PID/task/PID/children，但本内核没有该文件，首轮mic及首轮paired无后台资源采样；不填造这些数据。修复监控工具为PPid查询并核实exe/start-token，原工具保存在gui_sampler_original.py，最终长测包含GUI和后台分开采样。这个工具修复没有更改已构建生产源码。')
 add('主机绘图旧matplotlib不支持tick_labels，改labels后重跑；Git全局docx textconv曾使差异变成文本抽取，字节回放失败，保留失败JSON后禁用--no-textconv/--no-ext-diff，二进制补丁回放成功；Word沙箱COM失败，使用已授权原生Word导出；初次Word对象HWND为空改用Document.ActiveWindow.Hwnd。打包renderer缺少LibreOffice，保留错误并用现有Word生成PDF后复用同一renderer光栅化。没有安装软件，不终止用户原Word进程。所有失败实验保留，不能作为成功运行计数。')
 add('## 10 保护复现与交付结论')
 add('最终保护核对原稳定321项SHA/大小/mtime、四个历史可执行文件、冻结5.4和本节源码、设备、内存/磁盘及内核错误窗口。最新保护结果以protection_final_after_camera/result.json为准，较早protection_final保留。Camera/ALSA/render无持有者，primary恢复精确桌面基线；原稳定321项及四个历史程序均一致。测试结束磁盘剩余1,740,128,256字节，归档后的空间另见final_delivery_receipt.json。所有写入仅隔离目录；SDK/模型按原有路径读取，没有删除、覆盖模型或修改系统配置。')
 add('运行说明见README_STAGE5_FINAL.md和tools/stage5_05_launch_gui.sh；重要命令逐项说明见stage5_05_commands.md；完整前后源码见stage5_05_source_appendix.md；关键语句与寿命见stage5_05_statement_notes.md；12道完整问答见stage5_05_interview.md。最终Word和Markdown手册共同源自RK3576_STAGE5_ENGINEERING_MANUAL.md，包含5.1～5.5及可复核性能成果、真实局限和简历表述。Git格式patch通过全新临时树apply和逐字节SHA回放，不虚构Git提交。')
 add('考虑到已出现Linux热限频，本轮不继续扩大为单进程60分钟负载。没有单进程60分钟验收；本节完成记录中的2/4线程各约30分钟对照和最终GUI约30分钟时，仍只支持有限工况。当前VISION入口把中文识别结果用于路由，向VLM提交固定英文问题`What do you see? Answer briefly.`，不宣称支持任意中文视觉问题原样推理。Frame Age基于现有主机采集时间戳，不是传感器曝光时间。未实现RGA生产路径或DMA-BUF端到端零拷贝；TTS RTF仍>1、播放与合成仍串行、没有AEC/PTT/语音打断。原稳定版本升级须另经用户审核，当前不执行。')
 validation=local/'validation_summary.json'
 if validation.exists():
  v=load(validation)
  add('### 最终工程判定')
  add(('记录工况内工程检查通过，具备提交最终用户审核条件。' if v['all_checks_passed'] else '尚未满足工程检查，不能宣告最终通过。')+'5.1～5.4保持原验收成果，本节未覆盖稳定主工程。完整机器检查项在validation_summary.json；Word逐页检查和最终归档收据单独核对。未完成单进程60分钟、高占空比任意散热、真实拔插故障或声学仪器测量，不扩大结论。')
 # add() separates paragraphs; remove blank rows only inside consecutive tables.
 text=''.join(sections);text=re.sub(r'(?m)^(\|[^\n]*\|)\n\n(?=\|)',r'\1\n',text)
 (ROOT/'docs/stage5_05_final_acceptance.md').write_text(text,encoding='utf-8')
 commands=['# 5.5 重要命令及真实输出解析\n\n以下命令来自保存的argv，复现应选不存在的新case和build目录。模型/SDK仅引用现有路径。SSH传输码和测试子进程退出码分别保存，故意非法路径必须非零且完成清理。\n\n']
 selected=[]
 for folder in [base/'build_final_v2',base/'thermal_matrix',base/'gui_microphone_final_v2',base/'gui_paired_restart_final_v2',base/'gui_sigterm_vision_final_v2',base/'gui_mixed_1800s_4t_final_v2',base/'final_matrix',base/'final_matrix_retry1',base/'real_invalid_paths',base/'final_camera_followup',base/'camera_gap_recheck']:
  if folder.exists():selected.extend(sorted(folder.glob('*command.json')))
 selected.extend(sorted((base/'real_invalid_paths').glob('*/command.json')))
 for file in selected:
  command=load(file)
  if not isinstance(command,list):continue
  label=file.stem.replace('.command','');folder=file.parent;outcome_path=folder/(label+'.result.json');outcome=load(outcome_path) if outcome_path.exists() else (load(folder/'result.json') if (folder/'result.json').exists() else None)
  if folder.name in {'final_matrix','final_matrix_retry1'} and (base/file.name.replace('_command.json','')/'result.json').exists():outcome=load(base/file.name.replace('_command.json','')/'result.json')
  if folder.name=='thermal_matrix':outcome=next((x for x in outcome.get('cases',[]) if x['case'] in file.name),{}) if outcome else None
  commands.append('## '+folder.name+' '+label+'\n\n目的：'+('用现有ARM64 SDK配置、全量构建或运行确定性测试。' if folder.name=='build_final_v2' else '在记录输入与有限时限内验证GUI、模型链路、负载或错误清理。')+'\n\n```bash\n'+shlex.join(command)+'\n```\n\n')
  descriptions={'--output':'全新且位于隔离reports下的NPU桌面身份基线JSON，不覆盖旧记录','--name':'独占case目录，存在则拒绝覆盖','--build':'指定冻结ARM64构建','--build-name':'指定冻结ARM64构建','--mode':'区分microphone真实输入、paired_restart重启、sigterm_vision推理中退出或stability长测','--seconds':'有限输入监听秒数','--threads':'Kokoro线程数','--tts-threads':'Kokoro线程数','--timeout':'运行截止秒数，超时必须记失败','--grace':'信号后协作清理宽限秒数，超出强制终止只算失败','--audio-replay-file':'预分段真实语音TSV，执行真实ASR但跳过麦克风/VAD','--fixed-frame-dir':'固定NV12夹具目录，Camera仍真实采集，Frame Age不可用','--signal':'实际发出的SIGINT或SIGTERM','--trigger':'从真实日志定位发送阶段','--delay':'触发后等待秒数','--stop-mode':'排空或取消等待，活动同步SDK不被强行中断','--tts-queue-ms':'TTS最大等待毫秒数','--request-lifetime-ms':'请求绝对寿命毫秒数','--capture':'当轮动态发现的HyperX采集设备','--playback':'当轮动态发现的HyperX播放设备','--report-root':'已存在的隔离日志根，每次创建UUID子目录','--auto-start':'测试时进入事件循环后点击开始','--stop-after-answers':'测试收到指定成功完成数后停止，0表示不按回答数停止','--cycles':'fresh子进程会话轮数，不是在同SDK句柄内重启'}
  if folder.name=='build_final_v2':
   commands.append('参数逐项：`bash -c`执行保存的脚本，后续占位名为$0，再依次$1/$2/$3/$4；source只加载本次环境。`cmake -S`冻结源码、`-B`独立产物、`-DCMAKE_BUILD_TYPE=Release`优化、`BUILD_TESTING=ON`测试；`BUILD_WITH_RKLLM/BUILD_WITH_VLM/ENABLE_SHERPA_ASR=ON`链接真实SDK，ROOT/INCLUDE/RUNTIME_LIBRARY指定原路径，`BUILD_QT_GUI=ON`启用Qt5 Widgets/Test。`--build --parallel 3`最多3编译任务；`ctest --test-dir`选构建、`--timeout 30`逐项上限、`--output-on-failure`保留错误、`--output-junit`保存XML。\n\n')
  else:
   explanations=[]
   if Path(command[0]).name=='asr_llm_tts_smoke':
    roles=['采集设备','SenseVoice目录','Silero VAD模型','Qwen RKLLM模型','Kokoro目录','播放设备','有限监听秒数','TTS线程数','sid','SmolVLM2语言模型','RKNN Vision模型','Camera节点']
    explanations.append('CLI位置参数1～12依次为'+ '、'.join(roles)+'。本case故意将一个设备或模型路径改为不存在值，预期返回1并清理，不能当成正常模型请求成功。')
   for i,arg in enumerate(command):
    if arg in descriptions:explanations.append('`'+arg+'`'+descriptions[arg]+('，实际值`'+command[i+1]+'`' if i+1<len(command) and not command[i+1].startswith('--') else '')+'。')
   if any(x in command for x in ['-I','-B']):explanations.insert(0,'`python3 -I -B`隔离用户Python环境并禁止字节码写入。')
   commands.append('参数逐项：'+' '.join(explanations)+'\n\n')
  if outcome and 'result' in outcome:outcome=outcome['result']
  if outcome:commands.append('真实退出记录节选：\n\n```json\n'+json.dumps({k:v for k,v in outcome.items() if k not in {'cases','sessions','owned_children'}},ensure_ascii=False,indent=2)+'\n```\n\n')
  logs=[folder/(label+'.stdout.log'),folder/'terminal.log']
  if folder.name in {'thermal_matrix','final_matrix','final_matrix_retry1','final_camera_followup'}:logs=[folder/(label.replace('_command','')+'_runner.log')]
  for log in logs:
   if not log.exists():continue
   lines=log.read_text(encoding='utf-8',errors='replace').splitlines();excerpt=lines[-7:];commands.append('真实输出节选（完整`'+log.relative_to(ROOT).as_posix()+'`）：\n\n```text\n'+'\n'.join(x[:360] for x in excerpt)+'\n```\n\n')
  commands.append('解释与成功判断：编译需返回0且目标生成，CTest需注册项全部通过；Fake不能替代硬件。真实测试需子进程退出符合预期、无超时/强杀、shutdown、设备释放和原工程指纹一致；拒绝/到期/取消须核对预期计数。环境影响仅新隔离源码、构建、日志与本次设备占用，不改系统/模型。该命令的结论以对应result.json及上述原始日志为准，不从SSH退出0推测模型成功。\n\n')
 commands.append('## 主机收集统计与文档生成\n\n```powershell\npython tools/stage5_05_collect.py --complete-only\npython tools/stage5_05_analyze.py --collection '+str(Path(perf['collection']).as_posix())+'\npython tools/stage5_05_stability.py --collection '+str(Path(perf['collection']).as_posix())+'\npython tools/stage5_05_plots.py\npython tools/stage5_05_export.py\npython tools/stage5_05_validate.py --collection '+str(Path(perf['collection']).as_posix())+'\npython tools/stage5_05_manual.py\n```\n\ncollect只读打包本节完成目录，--complete-only跳过活动case，逐个验证普通文件/安全相对路径和总字节上限，保留SHA。analyze按case+request_id关联steady ns，缺失值为null；stability排除前5分钟并计算RSS趋势和逐条RTF；plots只用真实CSV，不生成假数据。export用真实git diff --no-index --binary，core.autocrlf=false避免换行转换，再在临时树apply后逐文件SHA。validate核对全部证据，不把本地测试替代ARM。manual从最终报告和当前源码抽取完整函数。成功输出和结果分别在collection manifest、analysis、patch_roundtrip、validation_summary及manual_source_manifest。\n\n文档创建使用已解析的Codex bundled Python运行stage5_05_build_docx.py，字体为楷体/Times New Roman 12pt、1.5倍行距、两字符缩进，代码等宽。packaged renderer因缺少LibreOffice失败的日志保留；原生Word只打开本次文档、更新目录并导出PDF，然后复用packaged rasterizer生成PNG。仅关闭本任务新建且无其他文档的Word实例，不结束用户Word。每页视觉核对与代码逐行回读在document_build、render结果与document_QA保存，不能只靠XML检查声称排版成功。\n')
 (ROOT/'docs/stage5_05_commands.md').write_text(''.join(commands),encoding='utf-8')
 print('REPORT_GENERATED',len(text.encode()),'bytes; commands',len(selected))
if __name__=='__main__':main()
