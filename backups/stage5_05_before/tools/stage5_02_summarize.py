#!/usr/bin/env python3
"""Derive Stage 5.2 finite-sample metrics from preserved terminal/result evidence."""
import argparse,csv,json,math,re,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def distribution(values):
 if not values:return dict(n=0,mean=None,p50=None,p95=None,max=None)
 ordered=sorted(values)
 return dict(n=len(values),mean=statistics.mean(values),p50=ordered[max(0,math.ceil(.50*len(values))-1)],p95=ordered[max(0,math.ceil(.95*len(values))-1)],max=max(values),method='nearest-rank; finite sample only')
def fields(text):
 return {k:float(v) if '.' in v or 'e' in v.lower() else int(v) for k,v in re.findall(r'(\w+)=(-?[\d.]+(?:e[+-]?\d+)?)',text,re.I)}
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--collection',type=Path);args=parser.parse_args()
 folder=args.collection or sorted((ROOT/'reports/stage5_02_board').glob('collected_*'))[-1]
 evidence=folder/'files/reports/stage5_02_board';cases=[]
 confirmations=load(ROOT/'reports/stage5_02_board/user_confirmations.json')
 for result in sorted(evidence.glob('*/result.json')):
  case=result.parent;log=case/'terminal.log'
  if not log.is_file():continue
  text=log.read_text(encoding='utf-8',errors='replace');summary=load(result)
  def values(pattern):return [float(x) for x in re.findall(pattern,text)]
  # completed lines only; cancelled/expired callback rows stay included in wait distribution.
  infer_lines=re.findall(r'\[(?:LLM|VLM) done #\d+\][^\n]*',text)
  tts_lines=re.findall(r'\[(?:VISION )?TTS done #\d+\][^\n]*',text)
  ready=None
  events=case/'events.jsonl'
  if events.is_file():
   for line in events.read_text().splitlines():
    event=json.loads(line)
    if event.get('event')=='trigger' and event.get('trigger')=='ready':ready=event['elapsed']
  cancelled_waits={int(i):float(v) for i,v in re.findall(r'\[TTS cancelled #(\d+)\] queue_ms=([\d.e+-]+)',text)}
  measured_tts_waits=[]
  for line in tts_lines:
   if 'queue_ms=' not in line:continue
   wait=fields(line)['queue_ms']
   if wait<0:
    request=int(re.search(r'done #(\d+)',line).group(1))
    wait=cancelled_waits.get(request)
   if wait is not None:measured_tts_waits.append(wait)
  delivered=sum('success=true' in line for line in tts_lines)
  successful=sum('success=true' in line for line in infer_lines)
  started=len(infer_lines)
  rows={}
  for line in re.findall(r'\[QueueStats\][^\n]*',text):
   stage=re.search(r'stage=(\w+)',line).group(1);rows[stage]=fields(line)
  if 'inference' in rows:started=rows['inference']['started']
  pipe=re.search(r'\[PipelineStats\]([^\n]*)',text)
  if pipe:pipe=fields(pipe.group(1))
  scope=summary['duration_seconds']-ready if ready is not None else None
  samples=[json.loads(x) for x in (case/'resources.jsonl').read_text().splitlines()]
  rss=[int(x['VmRSS'].split()[0]) for x in samples if 'VmRSS' in x]
  entry=dict(case=case.name,evidence=str(case.relative_to(ROOT)),process=summary,
             dispatch_ms=distribution(values(r'\[Dispatch\] id=\d+ callback_ms=([\d.e+-]+)')),
             inference_queue_ms=distribution([fields(x)['queue_ms'] for x in infer_lines if 'queue_ms=' in x]),
             tts_queue_ms_all_terminals=distribution(measured_tts_waits),
             tts_cancel_callback_sentinel='Cancelled callback retains legacy -1; actual wait read from [TTS cancelled] marker or QueueStats',
             tts_synthesis_ms=distribution([fields(x)['synth_ms'] for x in tts_lines if 'success=true' in x]),
             ai_started=started,ai_successful=successful,inference_success_fraction=None if not started else successful/started,
             delivered=delivered,dispatch_count=len(re.findall(r'\[Dispatch\]',text)),pipeline=pipe,queues=rows,
             baseline_peaks=fields(re.search(r'\[BaselineQueues\]([^\n]*)',text).group(1)) if '[BaselineQueues]' in text else None,
             post_ready_to_exit_seconds=scope,inference_per_second_including_shutdown=None if not scope else successful/scope,
             delivered_per_second_including_shutdown=None if not scope else delivered/scope,
             throughput_warning='Includes shutdown/drain, and quiet microphone window. Not steady-state NPU throughput.',
             rss_peak_kib=max(rss) if rss else None,thread_peak=max(int(x.get('Threads',0)) for x in samples),
             playback_xruns=values(r'playback_xruns=(\d+)'),audio_capture_xruns=values(r'\[ALSA\] XRUN=(\d+)'),
             runtime_error_markers=re.findall(r'^.*\[(?:Fatal|LLM error|VLM Error|TTS error|Inference callback error|TTS callback error)\].*$',text,re.M),
             user_confirmation=[r for r in confirmations if r['case']==case.name])
  cases.append(entry)
 report=ROOT/'reports/stage5_02_board'
 (report/'metrics.json').write_text(json.dumps(dict(collection=str(folder.relative_to(ROOT)),percentile_method='nearest-rank',cases=cases),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 with (report/'metrics.csv').open('w',encoding='utf-8-sig',newline='') as out:
  writer=csv.writer(out);writer.writerow(['case','returncode','dispatch_n','dispatch_mean_ms','dispatch_p50_ms','dispatch_p95_ms','ai_started','ai_successful','delivered','tts_wait_mean_ms','tts_wait_max_ms','rss_peak_kib','signal_to_exit_seconds'])
  for c in cases:writer.writerow([c['case'],c['process']['returncode'],c['dispatch_ms']['n'],c['dispatch_ms']['mean'],c['dispatch_ms']['p50'],c['dispatch_ms']['p95'],c['ai_started'],c['ai_successful'],c['delivered'],c['tts_queue_ms_all_terminals']['mean'],c['tts_queue_ms_all_terminals']['max'],c['rss_peak_kib'],c['process']['signal_to_exit_seconds']])
 print(json.dumps([dict(case=c['case'],code=c['process']['returncode'],dispatch=c['dispatch_ms'],ai=c['ai_successful'],delivered=c['delivered'],pipe=c['pipeline']) for c in cases],indent=2))
if __name__=='__main__':main()
