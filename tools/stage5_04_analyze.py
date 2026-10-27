#!/usr/bin/env python3
"""Analyze raw Stage 5.4 CSV/JSONL; missing observations remain null, never zero."""
from pathlib import Path
import argparse,csv,json,math,re,statistics,collections
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def jsonlines(p):return [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
def stats(values):
    xs=sorted(x for x in values if x is not None and math.isfinite(x))
    if not xs:return None
    return dict(n=len(xs),mean=statistics.mean(xs),p50=xs[math.ceil(len(xs)*.5)-1],p95=xs[math.ceil(len(xs)*.95)-1],minimum=xs[0],maximum=xs[-1])
PAIRS={
 'vad_endpoint_host_estimate_ms':('audio_end_estimated','vad_endpoint_confirmed'),
 'asr_enqueue_to_first_submit_ms':('asr_enqueued','alsa_first_submit_begin'),
 'asr_enqueue_to_playback_end_ms':('asr_enqueued','alsa_drain_complete'),
 'asr_queue_ms':('asr_enqueued','asr_dequeued'),
 'asr_preprocess_ms':('asr_dequeued','asr_begin'),
 'asr_api_ms':('asr_begin','asr_end'),
 'asr_decode_ms':('asr_decode_begin','asr_decode_end'),
 'router_ms':('router_begin','router_end'),
 'inference_queue_ms':('inference_enqueued','inference_dequeued'),
 'inference_service_ms':('inference_begin','inference_end'),
 'decoder_ms':('decoder_begin','decoder_end'),
 'decoder_first_text_chunk_ms':('decoder_begin','first_text_chunk'),
 'inference_first_text_chunk_ms':('inference_begin','first_text_chunk'),
 'tts_queue_ms':('tts_enqueued','tts_dequeued'),
 'tts_generate_api_ms':('tts_generate_begin','tts_generate_end'),
 'tts_first_audio_callback_ms':('tts_generate_begin','tts_first_audio_callback'),
 'tts_pcm_copy_ms':('tts_pcm_copy_begin','tts_pcm_copy_end'),
 'tts_full_audio_ready_ms':('tts_synthesis_begin','tts_full_audio_ready'),
 'tts_api_return_ms':('tts_synthesis_begin','tts_api_return'),
 'playback_conversion_ms':('playback_convert_begin','playback_convert_end'),
 'first_submit_call_duration_ms':('alsa_first_submit_begin','alsa_first_submit_complete'),
 'synthesis_to_first_submit_ms':('tts_synthesis_begin','alsa_first_submit_begin'),
 'tts_enqueue_to_first_submit_ms':('tts_enqueued','alsa_first_submit_begin'),
 'playback_call_ms':('playback_convert_begin','alsa_drain_complete'),
 'alsa_submit_to_drain_ms':('alsa_first_submit_begin','alsa_drain_complete'),
 'alsa_drain_wait_ms':('alsa_drain_begin','alsa_drain_complete'),
 'business_to_first_submit_ms':('business_dispatch_begin','alsa_first_submit_begin'),
 'business_to_playback_end_ms':('business_dispatch_begin','alsa_drain_complete'),
 'vad_detected_to_first_submit_ms':('vad_detected_start','alsa_first_submit_begin'),
 'speech_start_host_estimate_to_submit_ms':('audio_start_estimated','alsa_first_submit_begin'),
 'speech_end_host_estimate_to_submit_ms':('audio_end_estimated','alsa_first_submit_begin'),
 'speech_start_host_estimate_to_playback_end_ms':('audio_start_estimated','alsa_drain_complete'),
 'speech_end_host_estimate_to_playback_end_ms':('audio_end_estimated','alsa_drain_complete')}
def procstat(text):
    x=text[text.rfind(')')+2:].split()
    return dict(ticks=int(x[11])+int(x[12]),cpu=int(x[36]))
def resources(path):
    if not path.exists():return None
    rows=jsonlines(path);cpu=[];rss=[];hwm=[];threads=[];frequencies=collections.defaultdict(list);temps=collections.defaultdict(list);npu=collections.defaultdict(list);affinity=collections.Counter()
    previous=None
    for row in rows:
        if 'stat' not in row:continue
        current=procstat(row['stat']);now=row['monotonic']
        if previous:
            dt=now-previous[0]
            if dt>0:cpu.append(dict(monotonic=now,percent_one_core=100*(current['ticks']-previous[1])/(100*dt)))
        previous=(now,current['ticks'])
        for line in row['status'].splitlines():
            key,value=line.split(':',1)
            if key in {'VmRSS','VmHWM'}:(rss if key=='VmRSS' else hwm).append(int(value.split()[0])/1024)
            if key=='Threads':threads.append(int(value))
        for task in row.get('tasks',{}).values():
            for allowed in task.get('allowed',[]):affinity[allowed.split(':',1)[-1].strip()]+=1
        for name,value in row.get('sysfs',{}).items():
            if not isinstance(value,str):continue
            if 'scaling_cur_freq' in name:frequencies[name].append(int(value))
            elif '/thermal/' in name and name.endswith('/temp'):temps[name].append(int(value)/1000)
            elif 'npu' in name:npu[name].append(value)
    # The board reports CLK_TCK in system_before.json. Do not assume host HZ.
    hz=load(path.parent/'system_before.json').get('clock_ticks') if (path.parent/'system_before.json').exists() else None
    if hz:
        for row in cpu:row['percent_one_core']*=100/hz
    else:cpu=[]
    start=next((x['monotonic'] for x in rows if 'monotonic' in x),0)
    warm=[x['percent_one_core'] for x in cpu if x['monotonic']>=start+80]
    return dict(samples=len(rows),cpu_percent_one_core=stats([x['percent_one_core'] for x in cpu]),cpu_percent_after_80s=stats(warm),rss_MiB=stats(rss),VmHWM_observed_MiB=stats(hwm),threads=stats(threads),affinity_sample_counts=dict(affinity),cpu_frequency_kHz={k:stats(v) for k,v in frequencies.items()},temperature_C={k:stats(v) for k,v in temps.items()},npu_raw_unique={k:sorted(set(v)) for k,v in npu.items()},npu_utilization_percent=None,cpu_samples=cpu)
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);args=parser.parse_args()
    base=args.collection/'files/reports/stage5_04_board';out=ROOT/'reports/stage5_04_local/analysis';out.mkdir(exist_ok=True)
    cases={};requests=[];table=[];tts_raw=[];asr_raw=[];vision_raw=[]
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():continue
        case={};name=folder.name;phases={}
        if (folder/'result.json').exists():case['result']=load(folder/'result.json')
        if (folder/'resources.jsonl').exists():case['resources']=resources(folder/'resources.jsonl')
        if (folder/'terminal.log').exists():
            terminal=(folder/'terminal.log').read_text(encoding='utf-8',errors='replace')
            if (folder/'stderr.log').exists():terminal+='\n'+(folder/'stderr.log').read_text(encoding='utf-8',errors='replace')
            counters={}
            for line in terminal.splitlines():
                marker=re.match(r'^\[(QueueStats|AudioQueueStats|PipelineStats|CameraCounters|FramePool|ALSA)\] (.*)',line)
                if not marker:continue
                values={k:(float(v) if '.' in v else int(v)) if re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?',v) else v for k,v in re.findall(r'(\w+)=([^ ]+)',marker[2])}
                key=marker[1]+('/'+values['stage'] if 'stage' in values else '');counters[key]=values
            case['terminal_counters']=counters
            case['terminal_errors']={'profile_error':terminal.count('[ImageProfile ERROR]'),'asr_error':terminal.count('[ASR ERROR]'),'timeouts':terminal.count('[Timeout]'),'warnings_existing_unknown_phonemes':terminal.count('Skip unknown phonemes')}
            case['answers']={kind:{key:text for key,text in re.findall(pattern,terminal)} for kind,pattern in [('VISION',r'\[VLM Answer #(\d+)\] ([^\n]*)'),('TEXT',r'\[LLM #(\d+)\] ([^\n]*)')]}
            case['downstream_cancelled_ids']=re.findall(r'\[Pipeline downstream cancelled #(\d+)\]',terminal)
        if (folder/'user_feedback.json').exists():case['user_feedback']=load(folder/'user_feedback.json')
        for kind,filename,metrics,raw in [('tts','tts_samples.csv',['synthesis_ms','call_wall_ms','audio_seconds','rtf','peak','rms'],tts_raw),('asr','asr_samples.csv',['api_ms','wall_ms','audio_seconds','rtf'],asr_raw),('vision','vision_samples.csv',['latency_ms','decoder_first_text_ms'],vision_raw)]:
            p=folder/filename
            if not p.exists():continue
            values=list(csv.DictReader(p.open(encoding='utf-8')))
            for row in values:
                raw.append(dict(case=name,**row))
                key=int(row['iteration'])*2+(2 if row.get('language')=='en' else 1) if kind=='tts' else int(row['iteration'])+1
                phases[key]=(row['phase'],row.get('language','vision' if kind=='vision' else 'asr'))
            groups={}
            for row in values:groups.setdefault((row.get('language','fixture_'+row['fixture'] if kind=='vision' else 'zh'),row['phase']),[]).append(row)
            case[kind]={}
            for (language,phase),rows in groups.items():
                key=language+'/'+phase;case[kind][key]={metric:stats([float(r[metric]) for r in rows]) for metric in metrics}
                for metric,s in case[kind][key].items():
                    if s:table.append(dict(case=name,group=kind+'/'+key,metric=metric,**s))
        profile=folder/'profile.jsonl'
        if profile.exists():
            grouped=collections.defaultdict(dict);other=collections.defaultdict(list);counts=collections.Counter();session=[]
            for row in jsonlines(profile):
                if row.get('kind')=='request' and row['request_id']!=0:
                    key=row['request_id'];event=row['event']
                    if event in grouped[key]:raise ValueError(f'duplicate event {name}/{key}/{event}')
                    grouped[key][event]=row
                    if any(x in event for x in ['rejected','cancelled','expired','failed','dropped']):counts[event]+=1
                elif row.get('kind')=='request':session.append(row)
                elif 'stage' in row:other[row['stage']].append(row['ms'])
            case['session_events']=session;case['profile_counts']=dict(counts);case['profile_requests']=len(grouped);case['profile_events']={str(k):v for k,v in grouped.items()}
            case['request_metrics']={};byroute=collections.defaultdict(list)
            for key,events in grouped.items():
                row={'case':name,'request_id':key,'route':'VISION' if events.get('router_end',{}).get('value')==1 else 'TEXT' if 'router_end' in events else 'NOT_ROUTED','phase':phases.get(key,('interactive_or_replay',''))[0]}
                if name in ('baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t'):row['phase']='first_pair' if key<=2 else 'warm_pair'
                row['status']='success' if 'request_complete' in events else 'cancelled' if any('cancelled' in x for x in events) else 'expired' if any('expired' in x for x in events) else 'rejected' if any('rejected' in x for x in events) else 'failed' if any('failed' in x for x in events) else 'cancelled_downstream' if str(key) in case.get('downstream_cancelled_ids',[]) else 'stage_only_or_incomplete'
                for metric,(first,last) in PAIRS.items():
                    row[metric]=(events[last]['at_ns']-events[first]['at_ns'])/1e6 if first in events and last in events else None
                    if row[metric] is not None and row[metric]<0:raise ValueError(f'negative duration {name}/{key}/{metric}')
                requests.append(row);group=row['route']+'/'+row['phase']+'/'+row['status']+('/'+phases[key][1] if key in phases else '');byroute[group].append(row)
            for route,rows in byroute.items():
                case['request_metrics'][route]={metric:stats([r[metric] for r in rows]) for metric in PAIRS}
                for metric,s in case['request_metrics'][route].items():
                    if s:table.append(dict(case=name,group=route,metric=metric,**s))
            case['image_stages']={k:stats(v) for k,v in other.items()}
            for stage,value in case['image_stages'].items():
                if value:table.append(dict(case=name,group='image/all_observed_including_first_use',metric=stage,**value))
        for p in folder.glob('ort_profile*.json'):
            data=load(p);runs=[x for x in data if x.get('name')=='model_run'];nodes=[x for x in data if x.get('cat')=='Node' and x.get('ph')=='X']
            op=collections.defaultdict(list)
            for node in nodes:op[node.get('args',{}).get('op_name','unknown')].append(node.get('dur',0)/1000)
            case['ort_profile']={'file':str(p.relative_to(base)),'model_run_ms':stats([x['dur']/1000 for x in runs]),'model_run_events':runs,'operator_sum_ms':{k:sum(v) for k,v in sorted(op.items(),key=lambda x:-sum(x[1]))},'note':'ORT tracing is a separate diagnostic, not the fair speed comparison; operator sums can overlap threads'}
        if case.get('resources'):
            resource=case['resources']
            for metric in ['cpu_percent_one_core','cpu_percent_after_80s','rss_MiB','VmHWM_observed_MiB','threads']:
                if resource.get(metric):table.append(dict(case=name,group='resources/observed',metric=metric,**resource[metric]))
            for category in ['cpu_frequency_kHz','temperature_C']:
                for sensor,value in resource[category].items():
                    if value:table.append(dict(case=name,group='resources/'+category,metric=sensor,**value))
        if case:cases[name]=case
    def write_csv(name,rows):
        if not rows:return
        fields=list(dict.fromkeys(k for row in rows for k in row))
        with (out/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    write_csv('statistics.csv',table);write_csv('requests.csv',requests);write_csv('tts_raw.csv',tts_raw);write_csv('asr_raw.csv',asr_raw);write_csv('vision_raw.csv',vision_raw)
    result={'collection':str(args.collection),'quantiles':'nearest-rank','clock':'C++ steady_clock; recorded raw monotonic ns','cases':cases,'notes':['Request IDs reset per process; pair ID with case name','First text chunk is observable; true token-granular TTFT unmeasured','ALSA submission/drain is not acoustic timing','Estimated speech clocks depend on capture sample mapping; not ADC timestamps','NPU load sysfs raw values retained, utilization unvalidated','Missing values remain null; no synthetic samples']}
    (out/'performance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ANALYZED',len(cases),'cases;',len(requests),'requests;',len(tts_raw),'TTS rows;',len(asr_raw),'ASR rows;',len(vision_raw),'vision rows')
if __name__=='__main__':main()
