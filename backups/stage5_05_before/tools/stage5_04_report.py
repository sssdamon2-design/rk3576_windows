#!/usr/bin/env python3
"""Render measured Stage5.4 results without inventing missing observations."""
from pathlib import Path
import csv,json,shlex,re
ROOT=Path(__file__).resolve().parents[1]

def stat(value):
    if not value:return '未测量'
    return ' / '.join(f'{value[k]:.3f}' for k in ('mean','p50','p95','minimum','maximum'))+f"（n={value['n']}）"

def main():
    analysis=ROOT/'reports/stage5_04_local/analysis'
    data=json.loads((analysis/'performance.json').read_text(encoding='utf-8'));cases=data['cases']
    collection=Path(data['collection']).resolve();base=collection/'files/reports/stage5_04_board'
    selection=ROOT/'reports/stage5_04_local/voice_selection.json'
    voice_case=json.loads(selection.read_text(encoding='utf-8'))['case'] if selection.exists() else 'candidate_voice_4t_final'
    before=cases['raw_tts_baseline_2t'];after=cases['raw_tts_final_4t']
    report=ROOT/'docs/stage5_04_performance_profiling.md'
    previous=report.read_text(encoding='utf-8').split('<!-- STAGE5_04_MEASURED -->')[0]
    previous=previous.replace('状态：源码审计与测量边界设计完成，正在执行未经优化的 5.3 TTS 基线并实现可关联埋点；未作 5.4 验收，未开始 5.5。','状态：下方实测章节记录最终结果；等待用户验收，未进入 5.5。')
    previous=previous.replace('原始未优化基线 `raw_tts_baseline_2t` 已独占执行完成','初期真实未优化基线 `raw_tts_baseline_2t` 独占运行（以下保留当时进度，最终统计见后文）')
    previous=re.sub(r'^初期真实未优化基线.*$', '【真实执行】原冻结5.3 TTS库的独立基线已经完成；固定中英文各30个有效暖态样本，另列首次使用和预热。自动合成不等于人工听音确认，最终人工回归状态见下文。',previous,flags=re.M)
    sections=['\n<!-- STAGE5_04_MEASURED -->\n## 操作 5：最终实现、版本与交付索引\n\n']
    sections.append('【源码确认】生产优化是 Kokoro 默认线程数 2→4，保留显式 2 线程回退。复用现有 RequestTrace/ImageProfile 埋点和有界 Worker，未增加合成线程、切换模型、改音色/语速、截断答案或重构播放流水线。另修复显式回放的长 sleep 等待信号问题及新音频回放的 ASR 成功条件。\n\n')
    sections.append('5.3 原始149项快照、未优化86项板端源码、4个早期/候选构建均保留；最终使用 stage5_04_source_v3 与 build/stage5_04_board_v3。v2→v3 只修正音频回放的错误检查，正常路径模型参数不变。v2 的大样本模型/固定输入回归与 v3 的全构建/CTest、自然语音和信号复测分别标版本，不能互相冒充。\n\n')
    sections.append('完整修改前/后文件见 [源码附录](stage5_04_source_appendix.md)，关键语句与寿命审查见 [逐句说明](stage5_04_statement_notes.md)，命令详解见 [命令记录](stage5_04_commands.md)，14道完整问答见 [面试题](stage5_04_interview.md)。Git 格式补丁、逐文件SHA、应用验证和字节级roundtrip见 reports/stage5_04_local/changes.patch、change_manifest.json、patch_check.json、patch_roundtrip.json。这里没有 Git 仓库元数据，不虚构 commit。\n\n')
    sections.append('## 操作 6：15个观测点与指标定义\n\n| 点 | 原始事件 | 解释 |\n|---|---|---|\n')
    definitions=[('1','vad_detected_start','喂入VAD后观察到detected上升沿的主机时点；不是声学起点'),('2','vad_endpoint_confirmed','完整segment可取，复制前记录'),('3','asr_enqueued','实际音频段入队；fixture写盘额外耗时单列'),('4','asr_begin','预处理后进入ASRService'),('5','asr_end','已得到文本'),('6','router_end','路由完成，value=0 TEXT/1 VISION'),('7','inference_enqueued','现有共同推理队列入队'),('8','inference_begin','既有Worker开始执行'),('9','first_text_chunk','首个非空SDK文本chunk；精确首token未测量'),('10','decoder_end / inference_end','同步decoder返回 / 完整任务返回'),('11','tts_enqueued','原TTS队列入队'),('12','tts_synthesis_begin','TTSWorker进入合成'),('13','tts_first_audio_callback / tts_full_audio_ready','SDK首批借用音频 / 全段自有PCM；当前只在全段返回后播放'),('14','alsa_first_submit_begin / complete','首次成功writei的调用前及返回；不等于实际声学输出'),('15','alsa_drain_complete','ALSA排空完成；不宣称声学尾音测量')]
    for a,b,c in definitions:sections.append(f'| {a} | `{b}` | {c} |\n')
    sections.append('\nASR API 与 Decode、VAD端点估算、router、各队列、decoder、合成、复制/转换、首次提交与drain均独立。区间可以嵌套，不能简单全部相加。语音起/止估算基于主机read和样本索引，无ADC时间戳；无效估算不计算。音频回放真实运行ASR但绕过麦克风/VAD，单列asr_enqueued→首次提交/播放结束；文本回放更不含ASR。缺少的事件保持null，不补零。\n\n')
    sections.append('## 操作 7：统计条件与公平性\n\n【真实执行】主 TTS 对照：同一台 RK3576、同一个直接链接冻结5.3 TTS库的 benchmark、同模型/Runtime/文本、sid17、speed1、silence_scale0.2；唯一参数差为线程2/4。每种语言各 iteration0 first_use、iteration1 warmup，随后30个暖态样本，不混入主统计。英文first_use已是模型的第二次调用，不称整模型冷启动。模型初始化另列。\n\n固定中文：`一加一等于二。`；固定英文：`A computer monitor displaying a webpage with some text and images.`。中英文分别统计。API可能生成略有不同的PCM长度，记录每次长度并计算RTF；不要求随机生成逐字节一致。peak/RMS/非有限数与实际听音共同检查，无客观MOS/声学仪器。\n\nCPU governor保持ondemand，未改频率/亲和性/系统配置。采样`/proc`每秒一次，smaps每5次一次；CPU单核=100%，CLK_TCK取板端sysconf。CPU“80s后”是统一时间截断的尾段口径，不冒称全部预热样本。不同温度/频率和未完全控制的系统负载仍是限制，不是随机交叉试验。P50/P95为nearest-rank，表格均为平均/P50/P95/最小/最大（样本数），时间单位ms；audio_seconds为秒，RTF/peak/RMS无量纲。\n\n')
    sections.append('## 操作 8：TTS主对照与候选筛查\n\n| 语言/指标 | 2线程基线 | 4线程最终 |\n|---|---|---|\n')
    gains=[]
    for language,label in [('zh','中文'),('en','英文')]:
        a=before['tts'][language+'/measured'];b=after['tts'][language+'/measured']
        for metric in ['synthesis_ms','call_wall_ms','audio_seconds','rtf','peak','rms']:sections.append(f'| {label} {metric} | {stat(a[metric])} | {stat(b[metric])} |\n')
        gain=100*(1-b['synthesis_ms']['mean']/a['synthesis_ms']['mean'])
        gains.append(f'\n{label}暖态平均合成耗时下降 **{gain:.2f}%**；此结论仅适用于这组同条件测试，不代表任意文本或完整语音端到端都按此比例加速。\n\n')
    sections.extend(gains)
    sections.append('| 筛查配置 | 中文均值ms / RTF | 英文均值ms / RTF | 结论 |\n|---|---|---|---|\n')
    for name,label,conclusion in [('raw_tts_screen_1t','1线程','更慢，不采用'),('raw_tts_screen_4t','4线程','进入足量复测'),('raw_tts_screen_6t','6线程','中文更慢、英文小幅收益但CPU更高，不采用')]:
        c=cases[name]['tts'];a=c['zh/measured'];b=c['en/measured'];sections.append(f"| {label} 每语言n=3 | {a['synthesis_ms']['mean']:.3f} / {a['rtf']['mean']:.3f} | {b['synthesis_ms']['mean']:.3f} / {b['rtf']['mean']:.3f} | {conclusion} |\n")
    sections.append('\n筛查只用于选候选，不能替代n=30主比较；1/6线程的慢结果保留原CSV。没有先合成和播放重叠改造，也没有模型重新初始化优化，因为源码和日志已经确认初始化只做一次。\n\n![TTS暖态分布](../reports/stage5_04_local/plots/tts_latency.png)\n\n![RTF分布](../reports/stage5_04_local/plots/tts_rtf_cdf.png)\n\n')
    sections.append('### 模型实例初始化与首次使用（不是清空页缓存后的断电冷启动）\n\n| case | initialize墙钟ms | 中文first_use / warmup ms | 英文first_use / warmup ms |\n|---|---|---|---|\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        terminal=(base/name/'terminal.log').read_text(encoding='utf-8');match=re.search(r'\[TTSInit\] ms=([0-9.]+)',terminal);c=cases[name]['tts']
        sections.append(f"| {name} | {match[1] if match else '未测量'} | {c['zh/first_use']['synthesis_ms']['mean']:.3f} / {c['zh/warmup']['synthesis_ms']['mean']:.3f} | {c['en/first_use']['synthesis_ms']['mean']:.3f} / {c['en/warmup']['synthesis_ms']['mean']:.3f} |\n")
    sections.append('\n两组各64次Generate调用、各60个measured样本，波形有限数/采样率/长度在validation检查。固定ASR和VLM前后各32次调用（含2次初始调用），实际成功输出和固定RGB/Embedding逐字节对比另列，不用这些样本替代真实听音。\n\n')
    sections.append('## 操作 9：TTS内部诊断与无法测量的边界\n\n')
    diag=cases['baseline_tts_ort_detail'];rows=list(csv.DictReader((base/'baseline_tts_ort_detail/tts_samples.csv').open(encoding='utf-8')));runs=diag['ort_profile']['model_run_events']
    assert len(rows)==len(runs)==6
    sections.append('| 语言/阶段 | Generate API ms | ORT model_run ms | 差值ms（非纯音素化） |\n|---|---|---|---|\n')
    total=sum(float(x['synthesis_ms']) for x in rows);model=sum(x['dur']/1000 for x in runs)
    for row,run in zip(rows,runs):
        api=float(row['synthesis_ms']);r=run['dur']/1000;sections.append(f"| {row['language']}/{row['phase']} | {api:.3f} | {r:.3f} | {api-r:.3f} |\n")
    sections.append(f'\n该独立诊断六次model_run合计占API **{100*model/total:.4f}%**，支持主要瓶颈是模型计算。诊断有trace开销，不纳入主加速百分比。Conv等算子累计占用在JSON保留，算子可能并行/嵌套，不能当硬件利用率或直接把所有dur相加当总墙钟。SDK文本前端、音素化、内部波形处理没有独立可靠回调，分别标未单独测量；差值包含这些以及其他运行开销。\n\n')
    for name in ['baseline_tts_ort_detail','candidate_tts_profile_4t']:
        c=cases[name];sections.append(f'### {name}\n\n| 组别 | 首批callback | 完整自有音频ready | 应用PCM复制 |\n|---|---|---|---|\n')
        for key,metrics in c['request_metrics'].items():
            sections.append(f"| {key} | {stat(metrics.get('tts_first_audio_callback_ms'))} | {stat(metrics.get('tts_full_audio_ready_ms'))} | {stat(metrics.get('tts_pcm_copy_ms'))} |\n")
    sections.append('\n“首批callback更早”没有在本轮改成更早播放，当前首音频提交仍需完整合成。额外 float复制和S16转换实测很小，本轮保留安全所有权，不声称零拷贝，也不将其当秒级瓶颈。\n\n')
    sections.append('## 操作 10：同音频、同图像完整请求和排队对照\n\n留存自然基线指定的segment1/2，固定NV12 frame0，SHA与TSV在fixed_inputs/paired_inputs。三组VISION(0/40/80s)→TEXT(+1s)，真实ASR、原路由/队列/模型/TTS/ALSA；没有麦克风/VAD，不计算这些阶段的虚假时间。Camera仍独立采集，固定图像的Frame Age不计。两组max_wait=60000ms、request_lifetime=180000ms，避免用默认旧任务过期制造加速；生产默认期限不变。每路n=3有限样本，首组有首次使用，后两组才是暖态重复，不能外推长期P95。\n\n| case/路由 | ASR入队→首提交 | ASR入队→drain | TTS队列等待 | 模型服务 |\n|---|---|---|---|---|\n')
    for name in ['baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        for key,m in cases[name]['request_metrics'].items():
            if not key.endswith('/success'):continue
            sections.append(f"| {name}/{key} | {stat(m['asr_enqueue_to_first_submit_ms'])} | {stat(m['asr_enqueue_to_playback_end_ms'])} | {stat(m['tts_queue_ms'])} | {stat(m['inference_service_ms'])} |\n")
    sections.append('\n固定输入不代表模型输出一定逐字一致，回答文本在各case answers/terminal.log保留。若答案或生成长度不同，只作为完整场景观测，不把全部变化归因于线程数；严格收益依据仍是固定文本n=30主对照。队列等待会包含前一条的合成和完整播放，当前串行语义没有改。【理论分析】服务时间减少通常有助于缩短等待，但受输入间隔和输出长度影响，不能保证任意负载的固定比例收益。\n\n![请求阶段分解](../reports/stage5_04_local/plots/pipeline_breakdown.png)\n\n')
    sections.append('【真实执行】这组n=3的TEXT推理服务均值从约1149.5ms升至1422.1ms；同时其完整ASR入队→播放完成从约29.63s降至24.33s。VISION完整请求从约19.91s降至16.69s。没有把局部回退隐藏在总延迟收益中：CPU竞争/热状态可能影响Qwen，有限样本不足以单独确定因果。4线程是当前整体等待收益与资源开销的折中，不是所有子阶段都加速。默认12秒TTS等待策略仍保留，本轮公平对照才单独使用60秒；生产连续请求仍可能按原策略过期。\n\n')
    sections.append('## 操作 11：真实语音、ASR/VLM、Camera与并发回归\n\n| case | 原始退出码 | 有效样本/结果摘要 |\n|---|---|---|\n')
    for name in ['baseline_asr_30','candidate_asr_30','baseline_vision_30','candidate_vision_30','baseline_voice_2t',voice_case,'candidate_burst_audio','candidate_expiry_audio']:
        c=cases[name];r=c['result'];counter=c.get('terminal_counters',{});brief=counter.get('PipelineStats',{})
        if not brief:
            kind='asr' if 'asr' in name else 'vision';samples=list(csv.DictReader((base/name/(kind+'_samples.csv')).open(encoding='utf-8')))
            brief={'CSV总行数':len(samples),'measured样本':sum(x['phase']=='measured' for x in samples),'成功非空文本':sum(bool(x.get('text',x.get('answer','')).strip()) for x in samples)}
        sections.append(f"| {name} | {r.get('returncode')} | `{json.dumps(brief,ensure_ascii=False,separators=(',',':'))}` |\n")
    sections.append('\n自然基线120秒有额外说话：7段识别、5接收、2忙碌拒绝，不能把全部TEXT回答混作同一固定文本性能。当前用户确认优化前两个指定回答都实际听到；优化版确认单列user_feedback，不复用5.3反馈。语音起/止估算→首提交及播放结束的全量逐请求数据见requests.csv；麦克风不是自动固定输入试验。Camera FPS/FramePool/XRUN均保留terminal_counters，实际释放用fuser及/proc/asound状态复核。\n\n')
    feedback=json.loads((base/voice_case/'user_feedback.json').read_text(encoding='utf-8')) if (base/voice_case/'user_feedback.json').exists() else None
    sections.append('### 最终优化版人工确认与设备终态\n\n用户反馈原文及确认边界：\n\n```json\n'+json.dumps(feedback,ensure_ascii=False,indent=2)+'\n```\n\n最终优化版Camera、队列和ALSA计数（实际日志解析）：\n\n```json\n'+json.dumps(cases[voice_case]['terminal_counters'],ensure_ascii=False,indent=2)+'\n```\n\n')
    requests=list(csv.DictReader((analysis/'requests.csv').open(encoding='utf-8')))
    columns=[]
    for name in ['baseline_voice_2t',voice_case]:
        for route in ['TEXT','VISION']:
            selected=next((r for r in requests if r['case']==name and r['route']==route and r['status']=='success'),None)
            columns.append((name+'/'+route+('/ID'+selected['request_id'] if selected else '/pending'),selected or {}))
    sections.append('### 自然语音的逐阶段时点差（有限样本，不是公平加速主表）\n\n每列为该轮首个成功的对应路由，单位ms；两轮真实说话不完全相同，基线还留存fixture写盘，不能据此作同条件加速百分比。\n\n| 指标 | '+' | '.join(c[0] for c in columns)+' |\n|---|---|---|---|---|\n')
    for metric in ['vad_endpoint_host_estimate_ms','asr_queue_ms','asr_api_ms','asr_decode_ms','router_ms','inference_queue_ms','inference_service_ms','inference_first_text_chunk_ms','tts_queue_ms','tts_generate_api_ms','tts_first_audio_callback_ms','tts_full_audio_ready_ms','playback_conversion_ms','synthesis_to_first_submit_ms','alsa_submit_to_drain_ms','vad_detected_to_first_submit_ms','speech_start_host_estimate_to_submit_ms','speech_end_host_estimate_to_submit_ms','speech_start_host_estimate_to_playback_end_ms']:
        sections.append('| '+metric+' | '+' | '.join('未测量' if not row.get(metric) else f'{float(row[metric]):.3f}' for _,row in columns)+' |\n')
    sections.append('\n应用只有SDK float→自有vector复制及float→S16转换，没有新增应用重采样。plughw内部可能进行格式/采样率转换，其独立耗时未测量；提交/排空墙钟不等于声学时间。\n\n')
    sections.append('## 操作 12：安全退出、排空、取消与错误统计\n\n| case | 信号/模式 | 退出码 | 信号→退出s | 强杀/超时 | 设备释放 |\n|---|---|---|---|---|---|\n')
    for name in ['candidate_sigint_drain','candidate_sigterm_cancel_tts','candidate_sigterm_cancel_waiting','candidate_final_sigterm_drain',voice_case]:
        c=cases[name];r=c['result'];elapsed=r.get('signal_to_exit_seconds');sections.append(f"| {name} | {r.get('sent_signal')}/{r.get('stop_mode')} | {r['returncode']} | {'未测量' if elapsed is None else f'{elapsed:.3f}'} | {r['forced_kill']}/{r['timeout']} | {r['devices_released']} |\n")
    sections.append('\n排空会播完已接收工作；取消等待保留当前同步SDK调用安全完成、撤销未开始TTS或阻止新增下游。取消不是中断NPU/ORT。长等待case第二个输入安排100秒后，候选20ms检查信号，退出时间必须看实际记录，不能用杀进程冒充。所有Worker accepted/completed及pending/active/inflight、cancelled/expired/callback_errors均在JSON和原始日志，测试守护的退出码与SSH传输码分别保存。\n\n')
    default=cases['candidate_default_queue_audio'];sections.append('### 最终v3的原默认期限回归\n\n`tts_queue_ms=12000`、`request_lifetime_ms=45000`，保留原策略。实际终态：\n\n```json\n'+json.dumps(default['terminal_counters'],ensure_ascii=False,indent=2)+'\n```\n\n到期任务有明确日志、计数与终态；它不属于模型推理失败，也不属于性能主对照的成功样本。没有为了加速擅自截断或静默删除。\n\n')
    sections.append('## 操作 13：CPU、内存、热状态与NPU限制\n\n| standalone TTS | CPU%（80s后，单核100%） | RSS峰值MiB | VmHWM采样最大MiB | 线程数最大 |\n|---|---|---|---|---|\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        r=cases[name]['resources'];sections.append(f"| {name} | {stat(r['cpu_percent_after_80s'])} | {r['rss_MiB']['maximum']:.3f} | {r['VmHWM_observed_MiB']['maximum']:.3f} | {r['threads']['maximum']} |\n")
    sections.append('\n![CPU与内存](../reports/stage5_04_local/plots/tts_resources.png)\n\n【真实执行】增加线程的代价是更多CPU与热负载。温度、各核频率分布和完整进程RSS/线程曲线在performance.json，不隐藏降频或额外资源占用。RSS采样峰值不是全进程分配追踪，也不等于完整多模态进程内存；VmHWM为读取到的进程高水位。NPU原始load在CPU-only时也可固定100，不能直接换算有效利用率；带宽/功耗未测量。\n\n')
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        r=cases[name]['resources'];thermal=max((v['maximum'] for v in r['temperature_C'].values() if v),default=None)
        big=next((v for k,v in r['cpu_frequency_kHz'].items() if '/cpu4/' in k),None)
        sections.append(f"{name}：所读thermal传感器最高值 {thermal}°C，CPU4频率kHz {stat(big)}。传感器与频率原路径保留，不将温度当功耗。\n\n")
    failed=cases['candidate_voice_4t_final']['result']
    if failed['returncode']!=0:
        sections.append('### 原始人工回归未完成的保留记录\n\n第一轮最终版120秒监听没有检测到VAD语音段/ASR文本，程序正常释放资源后返回1。没有超时或强杀，不能算听音通过；重试必须使用新目录，不能覆盖这一轮。实际记录：\n\n```json\n'+json.dumps(failed,ensure_ascii=False,indent=2)+'\n```\n\n')
    sections.append('## 操作 14：失败记录、回退和剩余风险\n\n1. MinGW inline TLS shared_ptr链接失败：改函数局部TLS accessor，保留v1失败日志。\n2. 本地portable CLI因测试快照漏.txt而失败：补快照脚本，未改CLI实现。\n3. 1线程明显慢，6线程资源代价较大：未进入生产默认，原始数据保留。\n4. 新音频回放原本沿用文本回放免ASR检查：最终v3明确检查consumer.ok并输出错误，未更改模型/调度。\n5. 回放sleep_until延迟信号：v2起采用有限等待检查；v3继承。\n6. SDK未知音素警告在前后存在，原stderr保留，未擅改词典或文本。\n\n回退可在最终隔离程序显式传tts_threads=2；旧5.3可执行文件和源码仍在原处，不需要覆盖/删除。【尚未验证】未做多小时压力、全部SDK故障注入、声学延迟/MOS、精确token TTFT、可信NPU利用率/功耗；4线程在更高并发或更热环境下仍需重新评估。有限回归中无明显泄漏/死锁/重复释放证据，不宣称覆盖所有内部故障。\n\n')
    validation_path=ROOT/'reports/stage5_04_local/validation_summary.json'
    validation=json.loads(validation_path.read_text(encoding='utf-8')) if validation_path.exists() else None
    sections.append('## 操作 15：最终验收状态与下一步\n\n')
    sections.append('自动验证汇总：\n\n```json\n'+json.dumps(validation,ensure_ascii=False,indent=2)+'\n```\n\n')
    sections.append('本节提交用户验收后暂停，**没有开始5.5**。最终阶段工程手册会在5.5汇编Word/Markdown；本节完整Markdown、源代码、逐句说明、命令、问答、图表和证据均已留档。具体验收边界以validation_summary及当前用户听音反馈为准。\n')
    complete=bool(validation and validation.get('all_checks_passed'))
    status='状态：全部记录内验证完成，等待用户验收；未进入5.5。' if complete else '状态：自动测试与性能测量已完成，最终人工语音/听音回归尚未完成，不能正式验收；未进入5.5。'
    previous=re.sub(r'^状态：.*$',status,previous,flags=re.M)
    if not complete:sections[-1]='人工回归尚未完成，当前不能宣告5.4通过；保持本节，不进入5.5。完整Word/Markdown工程手册留待5.5汇编，本节源码、数据和技术材料按实际完成状态保存。\n'
    report.write_text(previous+''.join(sections),encoding='utf-8')
    commands=['# 5.4 命令、逐项参数及真实输出\n\n','全部操作仅cat用户和已授权隔离目录；`sudo -n fuser -v`仅查询，不含-k。复现必须选新case名和不存在的源码/构建目录，不覆盖冻结证据。以下argv来自实际command.json，shell形式用shlex.join转义；运行前使用`set -a; source "$REVIEW/tools/stage5_board_paths.sh"`导出原SDK/模型路径，环境快照在对应case/environment.json。source只改变本次shell，不编辑系统文件。\n\n']
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():continue
        for file in sorted(folder.glob('*command.json')):
            command=json.loads(file.read_text(encoding='utf-8'))
            if not isinstance(command,list):continue
            label=file.name.replace('.command.json','').replace('command.json','run')
            result=folder/(label+'.result.json') if label!='run' else folder/'result.json'
            outcome=json.loads(result.read_text()) if result.exists() else cases.get(folder.name,{}).get('result')
            stdout=folder/(label+'.stdout.log') if label!='run' else folder/'terminal.log'
            stderr=folder/(label+'.stderr.log') if label!='run' else folder/'stderr.log'
            commands.append(f'## 操作 {folder.name}/{label}\n\n目的：'+('独立ARM64配置/构建/确定性测试。' if 'build' in folder.name else '在指定固定/真实输入条件下采样或回归；不安装软件、不改模型和设备配置。')+'\n\n```bash\n'+shlex.join(command)+'\n```\n\n')
            commands.append('参数：`cmake -S`指定冻结源码，`-B`指定独立产物；`-DCMAKE_BUILD_TYPE=Release`启用发布优化；`-DBUILD_TESTING=ON`注册测试；RKLLM/VLM/SHERPA开关启用真实SDK，ROOT/INCLUDE/LIBRARY参数指定已核实原路径；`--build --parallel 3`最多三个编译任务。`ctest --test-dir`选择构建，`--output-on-failure`保留失败输出，`--timeout 30`限制每项，`--output-junit`写报告。`bash -c`内脚本完整保留，后续位置参数对应$1/$2/$3。\n\n' if 'build' in folder.name else '参数：程序绝对路径决定具体冻结版本。TTS bench依次为模型目录、独占报告目录、线程数、有效重复次数（另加两轮first-use/warmup）；ASR bench为模型目录、固定WAV、报告目录、重复次数；Vision bench为语言模型、Vision模型、固定NV12目录、报告目录、重复次数。完整语音入口为采集设备、ASR目录、VAD模型、Qwen模型、Kokoro目录、播放设备、监听秒数、TTS线程数、sid17、VLM语言模型、Vision模型、Camera节点。stdbuf -oL/-eL仅调整输出缓冲，便于按真实监听/信号阶段触发。实际采集/回放模式见test_parameters和environment，不从程序名字猜测。\n\n')
            commands.append('真实退出/守护记录：\n\n```json\n'+json.dumps(outcome,ensure_ascii=False,indent=2)+'\n```\n\n')
            for kind,path in [('stdout',stdout),('stderr',stderr)]:
                if path.exists():
                    lines=path.read_text(encoding='utf-8',errors='replace').splitlines();excerpt=lines if len(lines)<=14 else lines[:5]+['[此处省略，完整原始文件见链接]']+lines[-8:]
                    rel=path.relative_to(ROOT).as_posix();commands.append(f'真实{kind}节选（完整[{path.name}](../{rel})）：\n\n```text\n'+'\n'.join(excerpt)+'\n```\n\n')
            commands.append('输出解释与成功判断：编译需退出0且目标生成；CTest需注册测试全部通过，Fake仅验证并发/生命周期；硬件程序需核对本case真实returncode、无timeout/forced_kill、完整shutdown和设备释放。拒绝/到期/取消的故意场景还必须核对对应终态计数，不把SSH成功当模型成功。环境影响：仅隔离源码/构建/日志写入和本次进程的设备使用，原工程/模型/SDK/系统只读。结论以本case原始记录为准，表内空值就是未测量。\n\n')
    commands.append('## 操作 本地分析、绘图、差异与证据收集\n\n```powershell\npython tools/stage5_04_collect.py --complete-only\npython tools/stage5_04_analyze.py --collection '+collection.as_posix()+'\npython tools/stage5_04_plot.py --before raw_tts_baseline_2t --after raw_tts_final_4t --pipeline-case candidate_pipeline_pairs_4t\npython tools/stage5_04_export.py\n```\n\ncollect仅SSH只读打包reports04，--complete-only跳过未完成case，验证普通文件/安全相对路径、文件和总字节上限，SHA清单保留；不收模型。analyze按case+request_id关联steady事件，按原CSV阶段/语言/fixture分组，nearest-rank统计。plot只读真实数据生成PNG/SVG，未生成示意数据。export生成完整前后源码和git diff --no-index；--binary保留换行字节差异，core.autocrlf=false不转换；在新临时树git apply --check、实际apply后逐文件SHA比对，不在真实工作树执行apply。成功输出、SHA及验证在本地报告目录。\n')
    commands.append('\n## 操作 最终材料归档\n\n目的：将本节完整源码、差异、报告和量化结果保存到隔离reports目录，不更新任何运行版本。\n\n```powershell\npython tools/stage5_04_ssh.py --payload reports/stage5_04_local/payloads/30_delivery.py --timeout 120\n```\n\n`--payload`指定已保存在本地的完整远程Python脚本（含归档SHA）；`--timeout 120`限定SSH命令等待。远程先检查目标不存在、普通文件/安全相对路径、SHA与500MiB剩余空间，再用普通cat权限在`reports/stage5_04_board/final_acceptance/`新建归档及材料树；不覆盖已有目录，不启动测试，不写模型或稳定版本。实际退出码、文件数、SHA、空间与保护核验以`reports/stage5_04_local/final_delivery_receipt.json`及SSH原始日志为准。已有完整原始测试帧/ORT trace保留原reports路径，不重复复制模型或大型数据；材料内命令所链接的日志另保留副本。回退只需继续使用未变的旧版本，不需要删除任何文件。\n')
    (ROOT/'docs/stage5_04_commands.md').write_text(''.join(commands),encoding='utf-8')
    print('GENERATED measured report and command explanations')

if __name__=='__main__':main()
