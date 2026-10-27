"""Plot only recorded time series and requests; no fabricated comparison samples."""
from pathlib import Path
import csv,json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from statistics import median
ROOT=Path(__file__).resolve().parents[1]

def main():
 local=ROOT/'reports/stage5_05_local';data=json.loads((local/'analysis/stability.json').read_text(encoding='utf-8'))
 raw=list(csv.DictReader((local/'analysis/stability_resources.csv').open(encoding='utf-8')))
 requests=list(csv.DictReader((local/'analysis/stability_requests.csv').open(encoding='utf-8')))
 out=local/'plots';out.mkdir(exist_ok=True)
 names=[x for x in ['mixed_1800s_2t','mixed_1800s_4t'] if x in data['cases']]
 if not names:names=[x for x in ['mixed_180s_2t','mixed_180s_4t'] if x in data['cases']]
 fig,axes=plt.subplots(4,1,figsize=(11,10),sharex=True,layout='constrained')
 for name in names:
  rows=[r for r in raw if r['case']==name];x=[float(r['process_offset_s'])/60 for r in rows];label=name.rsplit('_',1)[1]
  temperature=[max(float(v) for k,v in r.items() if k.startswith('temp_') and v) for r in rows]
  cpu=[float(r['cpu_percent_one_core']) if r['cpu_percent_one_core'] else float('nan') for r in rows]
  # Medians are display smoothing only. Raw CSV remains unchanged.
  smoothed=[median(cpu[max(1,i-15):min(len(cpu),i+15)]) if i>0 else float('nan') for i in range(len(cpu))]
  axes[0].plot(x,temperature,label=label);axes[1].plot(x,smoothed,label=label)
  axes[2].plot(x,[float(r['rss_MiB']) for r in rows],label=label)
  axes[3].plot(x,[float(r['freq_cpu4_kHz'])/1e6 if r.get('freq_cpu4_kHz') else float('nan') for r in rows],label=label)
 axes[0].axhline(90,color='r',ls='--',label='90 C test stop guard')
 axes[0].axhline(85,color='gray',ls=':',label='85 C little-core passive trip')
 for ax,label in zip(axes,['Highest observed temperature (C)','Process CPU % (one core = 100%)','Observed process RSS (MiB)','CPU4 current frequency (GHz)']):
  ax.set_ylabel(label);ax.grid(alpha=.25);ax.legend(loc='upper right')
 axes[3].set_xlabel('Minutes from process launch (includes initialization)')
 fig.suptitle('RK3576 matched fixed-audio / fixed-frame mixed workload')
 fig.savefig(out/'thermal_cpu_memory.png',dpi=150);fig.savefig(out/'thermal_cpu_memory.svg');plt.close(fig)
 fig,axes=plt.subplots(1,2,figsize=(11,4.5),layout='constrained')
 for axis,metric,title in [(axes[0],'tts_rtf','TTS RTF (TEXT and VISION separated)'),(axes[1],'asr_rtf','ASR RTF (same two input segments)')]:
  labels=[];values=[]
  for name in names:
   for route in ['TEXT','VISION']:
    rows=[r for r in requests if r['case']==name and r['route']==route and r['status']=='success' and (r['phase']=='warm_after_5min' if '1800s' in name else True) and r.get(metric)]
    if rows:labels.append(name.rsplit('_',1)[1]+' '+route+'\nn='+str(len(rows)));values.append([float(r[metric]) for r in rows])
  if values:axis.boxplot(values,labels=labels,showmeans=True)
  axis.set_title(title);axis.set_ylabel(metric+' = model time / audio duration');axis.grid(axis='y',alpha=.25)
 fig.savefig(out/'warm_rtf.png',dpi=150);fig.savefig(out/'warm_rtf.svg');plt.close(fig)
 fig,ax=plt.subplots(figsize=(10,4),layout='constrained')
 for name in names:
  trend=data['cases'][name].get('resources')
  if trend:
   bins=[v for v in trend['five_minute_RSS_bins'] if 5<=v['start_minute']<30]
   ax.plot([b['start_minute']+2.5 for b in bins],[b['rss_MiB']['p50'] for b in bins],marker='o',label=name.rsplit('_',1)[1])
 ax.set_xlabel('Process-offset five-minute bin midpoint (minutes)');ax.set_ylabel('RSS median per bin (MiB)')
 ax.set_title('Warmed RSS trend; finite workload evidence, not a proof of no leaks');ax.grid(alpha=.25);ax.legend()
 fig.savefig(out/'warmed_rss.png',dpi=150);fig.savefig(out/'warmed_rss.svg');plt.close(fig)
 print('STABILITY_PLOTS',out)
if __name__=='__main__':main()
