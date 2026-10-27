"""Extend reused request profiling with raw thermal, cooling and warmed RSS trends."""
from pathlib import Path
import argparse,collections,csv,hashlib,json,math,re,statistics
from stage5_04_analyze import stats,jsonlines,load,procstat
ROOT=Path(__file__).resolve().parents[1]

def slope(points):
    if len(points)<2:return None
    mx=statistics.mean(x for x,y in points);my=statistics.mean(y for x,y in points)
    den=sum((x-mx)**2 for x,y in points)
    return None if den==0 else sum((x-mx)*(y-my) for x,y in points)/den

def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);a=p.parse_args()
 base=a.collection/'files/reports/stage5_05_board';local=ROOT/'reports/stage5_05_local/analysis'
 data=load(local/'performance.json');requests=list(csv.DictReader((local/'requests.csv').open(encoding='utf-8')))
 result={};details=[];resource_rows=[];metrics_rows=[]
 for name,case in data['cases'].items():
  folder=base/name
  if not (folder/'terminal.log').exists():continue
  terminal=(folder/'terminal.log').read_text(encoding='utf-8',errors='replace')
  asr={int(id):{'asr_logged_latency_ms':float(ms),'asr_rtf':float(rtf)} for id,ms,rtf in re.findall(r'\[ASR\] Segment #(\d+): .*? \| latency=([0-9.]+) ms \| RTF=([0-9.]+)',terminal)}
  ages={int(id):float(age) for id,age in re.findall(r'\[VLM done #(\d+)\].*?frame_age_ms=(-?[0-9.]+)',terminal)}
  config=re.search(r'\[ALSA config\] buffer_frames=(\d+).*?buffer_ms=([0-9.]+)',terminal)
  app_rate=None if not config else round(int(config[1])*1000/float(config[2]))
  selected=[r for r in requests if r['case']==name];events=case.get('profile_events',{})
  first=min((e.get('asr_enqueued',{}).get('at_ns',math.inf) for e in events.values()),default=math.inf)
  groups=collections.defaultdict(list)
  for row in selected:
   id=int(row['request_id']);e=events[str(id)];offset=(e.get('asr_enqueued',{}).get('at_ns',first)-first)/1e9
   phase=('initial_5min' if offset<300 else 'warm_after_5min') if '1800s_' in name else 'all_observed'
   extra={'case':name,'request_id':id,'route':row['route'],'status':row['status'],'phase':phase,'offset_from_first_ASR_enqueue_s':offset}
   extra.update(asr.get(id,{}));extra['frame_age_ms']=ages.get(id) if ages.get(id,-1)>=0 else None
   samples=e.get('tts_full_audio_ready',{}).get('value');extra['audio_sample_count']=samples;extra['app_sample_rate_derived_from_config']=app_rate
   seconds=samples/app_rate if samples and app_rate else None
   extra['tts_audio_seconds']=seconds
   extra['tts_rtf']=float(row['tts_generate_api_ms'])/(seconds*1000) if seconds and row['tts_generate_api_ms'] else None
   for key in ['asr_api_ms','asr_decode_ms','asr_queue_ms','inference_queue_ms','inference_service_ms','tts_queue_ms','tts_generate_api_ms','tts_first_audio_callback_ms','synthesis_to_first_submit_ms','asr_enqueue_to_first_submit_ms','asr_enqueue_to_playback_end_ms']:
    extra[key]=float(row[key]) if row[key] else None
   details.append(extra);groups[(row['route'],phase,row['status'])].append(extra)
  summaries={}
  names=['asr_logged_latency_ms','asr_rtf','frame_age_ms','tts_audio_seconds','tts_rtf','asr_api_ms','asr_decode_ms','asr_queue_ms','inference_queue_ms','inference_service_ms','tts_queue_ms','tts_generate_api_ms','tts_first_audio_callback_ms','synthesis_to_first_submit_ms','asr_enqueue_to_first_submit_ms','asr_enqueue_to_playback_end_ms']
  for group,rows in groups.items():
   key='/'.join(group);summaries[key]={metric:stats([x.get(metric) for x in rows]) for metric in names}
   for metric,value in summaries[key].items():
    if value:metrics_rows.append({'case':name,'group':key,'metric':metric,**value})
  resource=folder/'resources.jsonl';trend=None
  if resource.exists():
   rows=jsonlines(resource);origin=rows[0]['monotonic'];rss=[];cooling=collections.defaultdict(list);maxfreq=collections.defaultdict(list);percase=[]
   smaps_series=collections.defaultdict(list)
   excluded_no_RSS=0
   previous=None;hz=load(folder/'system_before.json').get('clock_ticks')
   for row in rows:
    if 'stat' not in row:continue
    offset=row['monotonic']-origin;status=dict(line.split(':',1) for line in row['status'].splitlines() if ':' in line)
    if 'VmRSS' not in status or 'Threads' not in status:
     excluded_no_RSS+=1;continue # Exited/zombie samples have no resident mapping, never fill with zero.
    mem=float(status['VmRSS'].split()[0])/1024;rss.append((offset/60,mem))
    t=procstat(row['stat'])['ticks'];cpu=None
    if previous and hz:cpu=100*(t-previous[1])/(hz*(row['monotonic']-previous[0]))
    previous=(row['monotonic'],t)
    point={'case':name,'process_offset_s':offset,'rss_MiB':mem,'threads':int(status['Threads']),'cpu_percent_one_core':cpu}
    for path,value in row.get('sysfs',{}).items():
     if isinstance(value,str) and path.endswith('/temp'):point['temp_'+Path(path).parent.name+'_C']=int(value)/1000
     elif isinstance(value,str) and path.endswith('scaling_cur_freq'):point['freq_'+path.split('/')[-3]+'_kHz']=int(value)
    for path,value in row.get('cooling_and_maxfreq',{}).items():
     if 'cooling_device' in path:
      cooling[path].append(int(value));point['cooling_'+Path(path).parent.name]=int(value)
     elif path.endswith('scaling_max_freq'):maxfreq[path].append(int(value))
    if isinstance(row.get('smaps_rollup'),str):
     for field in ['Anonymous','Pss_Anon','Pss_File','Private_Dirty','Private_Clean','Rss']:
      match=re.search(r'^'+field+r':\s+(\d+) kB',row['smaps_rollup'],re.M)
      if match and 300<=offset<=1800:smaps_series[field].append((offset/60,int(match[1])/1024))
    percase.append(point);resource_rows.append(point)
   warmed=[(x,y) for x,y in rss if 5<=x<=30]
   start_bin=[y for x,y in warmed if x<10];end_bin=[y for x,y in warmed if x>=25]
   bins=[]
   for minute in range(0,35,5):
    values=[y for x,y in rss if minute<=x<minute+5]
    if values:bins.append({'start_minute':minute,'rss_MiB':stats(values)})
   trend={'RSS_scope':'process offsets 5..30 min; first 5 minutes excluded; no teardown samples after 30min in slope','warmed_RSS_MiB':stats([y for x,y in warmed]),'RSS_slope_MiB_per_minute':slope(warmed),'median_5_to_10min_MiB':statistics.median(start_bin) if start_bin else None,'median_25_to_30min_MiB':statistics.median(end_bin) if end_bin else None,'five_minute_RSS_bins':bins,'cooling':{path:{'max_state':max(v),'positive_samples':sum(x>0 for x in v),'samples':len(v)} for path,v in cooling.items()},'scaling_max_frequency_kHz':{path:stats(v) for path,v in maxfreq.items()},'warmed_smaps':{key:{'MiB':stats([y for x,y in values]),'slope_MiB_per_minute':slope(values),'median_5_to_10min_MiB':stats([y for x,y in values if x<10]),'median_25_to_30min_MiB':stats([y for x,y in values if x>=25])} for key,values in smaps_series.items()},'raw_time_series_samples':len(percase),'excluded_resource_samples_without_RSS':excluded_no_RSS,'interpretation':'Positive cooling state indicates Linux cooling activity; ordinary frequency variation alone is not proof of thermal throttling. Stable RSS in this finite workload is not a proof of no leak.'}
  counts=collections.Counter(r['status'] for r in selected);counter=case.get('terminal_counters',{})
  result[name]={'metrics':summaries,'request_status_counts':dict(counts),'observed_requests':len(selected),'app_sample_rate_from_buffer_frames_and_ms':app_rate,'audio_duration_method':'tts_full_audio_ready sample count divided by the application rate derived from logged ALSA buffer_frames/buffer_ms; not acoustic duration','resources':trend,'terminal_counters':counter,'image_stages':case.get('image_stages',{}),'result':case.get('result')}
 def write(name,rows):
  if not rows:return
  fields=list(dict.fromkeys(k for r in rows for k in r))
  with (local/name).open('w',newline='',encoding='utf-8') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 write('stability_requests.csv',details);write('stability_resources.csv',resource_rows);write('stability_statistics.csv',metrics_rows)
 comparison={}
 for name in ['mixed_1800s_2t','mixed_1800s_4t']:
  inp=base/'thermal_matrix'/(name+'.tsv')
  if inp.exists():comparison[name]={'input_sha256':hashlib.sha256(inp.read_bytes()).hexdigest(),'lines':len(inp.read_text().splitlines())}
 output={'cases':result,'matched_long_test_inputs':comparison,'quantiles':'nearest rank; mean/P50/P95/min/max/n','limits':['Fixed presegmented audio skips microphone and VAD','Fixed image Frame Age unavailable','ALSA submission/drain not acoustic latency','Exact token TTFT and reliable NPU utilization unmeasured','Thermal thresholds are Linux trip points and a conservative test guard, not a chip safety rating','No 60-minute single-process claim unless such a case is explicitly recorded']}
 (local/'stability.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('STABILITY_ANALYZED',len(result),'cases;',len(details),'requests;',len(resource_rows),'resource samples')
if __name__=='__main__':main()
