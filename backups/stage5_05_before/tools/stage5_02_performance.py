#!/usr/bin/env python3
"""Generate finite-sample performance tables from immutable Stage 5.2 evidence."""
from pathlib import Path
import json,re
from stage5_02_summarize import distribution,fields
ROOT=Path(__file__).resolve().parents[1]
def f(value):return '—' if value is None else f'{value:.3f}'
def main():
 data=json.loads((ROOT/'reports/stage5_02_board/metrics.json').read_text(encoding='utf-8'))
 evidence=ROOT/data['collection']/'files/reports/stage5_02_board';cases=data['cases']
 text=(evidence/'baseline_and_npu_probe/probe.stdout.log').read_text()
 npu=[fields(line) for line in text.splitlines() if line.startswith('PROBE_RESULT')]
 stats={}
 for mode in [0,1]:
  rows=[r for r in npu if r['parallel']==mode]
  stats[str(mode)]={key:distribution([r[key] for r in rows]) for key in ['text_ms','vision_ms','pair_ms','sdk_call_overlap_ms']}
 (ROOT/'reports/stage5_02_board/npu_metrics.json').write_text(json.dumps(dict(rounds=npu,stats=stats),indent=2)+'\n')
 out=['# 5.2 实测性能数据\n\n',
      '本表由 `tools/stage5_02_performance.py` 从采集的原始终端/JSON 生成。设备、模型、构建和限制见 [验收报告](stage5_02_board_acceptance.md)。日期 2026-10-17，RK3576 真机；Fake 测试不纳入这些性能数字。\n\n',
      '统计均为毫秒（吞吐表除外），P50/P95 使用 nearest-rank，n=2 的 P50 为较小值，n≤4 的 P95 常等于最大值。每个 case 仅运行一次、请求数很小，没有置信区间或生产尾延迟结论；频率、温度、图像和生成长度未严格固定。\n\n',
      '## 操作 1：NPU 实际 SDK 调用对照\n\n',
      '| 调用方式（每类 n=3） | 指标 | 平均 ms | P50 ms | P95 ms |\n|---|---|---:|---:|---:|\n']
 for mode,name in [('0','顺序'),('1','重叠')]:
  for key,label in [('text_ms','Qwen 调用'),('vision_ms','RKNN+SmolVLM2 调用'),('pair_ms','一对任务完成'),('sdk_call_overlap_ms','SDK 调用区间交集')]:
   d=stats[mode][key];out.append(f'| {name} | {label} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\n6/6 对成功。重叠未观察到崩溃，但 Qwen 调用变慢；区间交集不是 NPU 硬件利用率。统一消费者是响应可预测性的选择，不是“并行已经被证明不安全”的结论。\n\n',
       '## 操作 2：ASR 业务回调/受控提交阻塞\n\n',
       '| case | n | 平均 ms | P50 ms | P95 ms |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  d=c['dispatch_ms'];out.append(f'| {c["case"]} | {d["n"]} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\nbaseline 的 VISION 耗时落在调用者线程；candidate 的 VISION 工作落在推理 Worker。表中混合 TEXT/VISION；过载 case 的 n 包括被拒绝请求，应同时读接受率。受控文本模式测同一个生产回调，不测 ASR 模型；真实 microphone case 才包含 USB/VAD/SenseVoice。\n\n',
       '## 操作 3：各队列等待\n\n',
       '| case | 推理排队 n / 平均 / P50 / P95 ms | TTS 终态 n / 平均 / P50 / P95 ms |\n|---|---|---|\n']
 for c in cases:
  def ds(d):return f'{d["n"]} / {f(d["mean"])} / {f(d["p50"])} / {f(d["p95"])}'
  out.append(f'| {c["case"]} | {ds(c["inference_queue_ms"])} | {ds(c["tts_queue_ms_all_terminals"])} |\n')
 out+=['\nbaseline 推理队列 n 只包含异步 TEXT，VISION 直接同步执行，没有相应 queue_ms；不能把缺失数据当零后混平均。TTS 统计包括过期/取消的真实驻留；取消回调兼容值 -1 已用 `[TTS cancelled]` 的实际驻留代替。过期出队时检查，实际驻留可超过配置期限。\n\n',
       '## 操作 4：深度、接受/拒绝、成功率和完整交付\n\n',
       '| case | 推理峰值 / TTS 峰值 | 跨阶段峰值 | 推理成功/实际执行 | 播放/输入请求 | Admission 拒绝 | TTS 过期/取消 | 子进程码 |\n|---|---|---|---|---|---:|---|---:|\n']
 for c in cases:
  q=c['queues'];p=c['pipeline'];old=c['baseline_peaks']
  peaks=f'{q["inference"]["peak"]}/{q["tts"]["peak"]}' if q else f'{old["inference_peak"]}/{old["tts_peak"]}'
  credit=str(p['peak']) if p else '无跨阶段限制'
  reject=p['rejected'] if p else '不适用'
  terminal=f'{p["tts_expired"]}/{p["tts_cancelled"]}' if p else '无该策略'
  out.append(f'| {c["case"]} | {peaks} | {credit} | {c["ai_successful"]}/{c["ai_started"]} | {c["delivered"]}/{c["dispatch_count"]} | {reject} | {terminal} | {c["process"]["returncode"]} |\n')
 out+=['\nbaseline_replay_overload 另有 1 次 TTS 队列满拒绝，退出 1；其余子程序返回 0。candidate_cancel_active_vision 下游取消 1，不启动 TTS。不能把推理成功率当请求最终交付率；没有执行的请求不计进模型成功分母。音频队列两轮真实 microphone 均峰值 1、dropped 0。\n\n',
       '## 操作 5：有限批次吞吐和自然排空退出\n\n',
       '| case | ready 至退出 s | 成功推理 / s | 完成播放 / s | 输入关闭至退出 s |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  if c['post_ready_to_exit_seconds'] is None:continue
  out.append(f'| {c["case"]} | {f(c["post_ready_to_exit_seconds"])} | {f(c["inference_per_second_including_shutdown"])} | {f(c["delivered_per_second_including_shutdown"])} | {f(c["process"].get("input_closed_to_exit_seconds"))} |\n')
 out+=['\n吞吐分母包含 drain/退出；真实 microphone case 还包含等待用户和静音窗口，不能称持续最大吞吐。两请求 equal_work_pair 都接受并播放 2/2，TTL 放宽到 60 s 排队/120 s 生命周期以避免策略丢弃。源输入相同，但 VLM 分别生成12 与 17 个英文词，PCM 帧数 80696 与 107578，未保持计算工作量完全相同；candidate 的批次排空实际更慢，不能宣称端到端加速。其主要收益是 VISION 回调不再占用 ASR。\n\n',
       '## 操作 6：停止模式和资源采样\n\n',
       '| case | 信号 | 模式 | 信号至退出 s | 采样峰值 RSS KiB | 采样线程峰值 |\n|---|---|---|---:|---:|---:|\n']
 for c in cases:
  p=c['process'];out.append(f'| {c["case"]} | {p["sent_signal"] or "自然结束"} | {p["stop_mode"]} | {f(p["signal_to_exit_seconds"])} | {c["rss_peak_kib"]} | {c["thread_peak"]} |\n')
 out+=['\n信号延迟从 harness 发送时刻至子进程退出/输出 EOF，排除后续 fuser/指纹查询。Drain 与 CancelPending 完成工作量不同，不是同等计算加速。采样周期约 1 s，可能漏过短峰值；RSS 包含 SDK、模型映射和工作缓冲，不能当 C++ heap 泄漏大小。全部 case 无超时/强制终止且设备释放。长期稳定性留后续独立验收。\n\n',
       '## 操作 7：模型计算时间与局限\n\n',
       '| case | 成功 TTS n | 合成平均 ms | P50 ms | P95 ms |\n|---|---:|---:|---:|---:|\n']
 for c in cases:
  d=c['tts_synthesis_ms'];out.append(f'| {c["case"]} | {d["n"]} | {f(d["mean"])} | {f(d["p50"])} | {f(d["p95"])} |\n')
 out+=['\n回答文本长度、CPU 竞争和 Camera 场景不同，合成数值波动不能归因为异步化提升模型速度。本节未改变 Kokoro 模型或合成算法。5.4 再按固定语料、更多样本和统一时间链路分析计算性能。\n']
 (ROOT/'docs/stage5_02_performance.md').write_text(''.join(out),encoding='utf-8',newline='\n')
 print('Generated performance tables for',len(cases),'cases and',len(npu),'NPU pairs')
if __name__=='__main__':main()
