#!/usr/bin/env python3
"""Make shareable plots from measured CSV/JSON; no illustrative/synthetic samples."""
from pathlib import Path
import argparse,csv,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--before',required=True);parser.add_argument('--after',required=True);parser.add_argument('--pipeline-case');args=parser.parse_args()
    folder=ROOT/'reports/stage5_04_local/analysis';out=ROOT/'reports/stage5_04_local/plots';out.mkdir(exist_ok=True)
    raw=list(csv.DictReader((folder/'tts_raw.csv').open(encoding='utf-8')))
    fig,axes=plt.subplots(1,2,figsize=(10,4.5),layout='constrained')
    for ax,language in zip(axes,['zh','en']):
        a=[float(r['synthesis_ms'])/1000 for r in raw if r['case']==args.before and r['language']==language and r['phase']=='measured']
        b=[float(r['synthesis_ms'])/1000 for r in raw if r['case']==args.after and r['language']==language and r['phase']=='measured']
        if not a or not b:raise ValueError('missing measured input groups')
        ax.boxplot([a,b],labels=[f'Before n={len(a)}',f'After n={len(b)}'],showmeans=True)
        for i,values in enumerate([a,b],1):ax.scatter(np.full(len(values),i),values,s=9,alpha=.45)
        ax.set_title('Chinese fixed text' if language=='zh' else 'English fixed text');ax.set_ylabel('Generate API latency (s)');ax.grid(axis='y',alpha=.25)
    fig.suptitle('Same RK3576 / model / speaker 17 / speed 1 / text; warm measurements')
    fig.savefig(out/'tts_latency.png',dpi=160);fig.savefig(out/'tts_latency.svg');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
    for ax,language in zip(axes,['zh','en']):
        for case,label in [(args.before,'Before'),(args.after,'After')]:
            values=sorted(float(r['rtf']) for r in raw if r['case']==case and r['language']==language and r['phase']=='measured')
            ax.step(values,np.arange(1,len(values)+1)/len(values),where='post',label=f'{label} n={len(values)}')
        ax.set_title('Chinese' if language=='zh' else 'English');ax.set_xlabel('RTF = synthesis / generated duration');ax.set_ylabel('Empirical CDF');ax.grid(alpha=.25);ax.legend()
    fig.savefig(out/'tts_rtf_cdf.png',dpi=160);fig.savefig(out/'tts_rtf_cdf.svg');plt.close(fig)
    data=json.loads((folder/'performance.json').read_text(encoding='utf-8'))
    fig,axes=plt.subplots(2,1,figsize=(10,6),layout='constrained')
    for case,label in [(args.before,'Before'),(args.after,'After')]:
        samples=data['cases'][case]['resources']['cpu_samples']
        if samples:
            start=samples[0]['monotonic'];axes[0].plot([x['monotonic']-start for x in samples],[x['percent_one_core'] for x in samples],label=label)
        axes[1].bar(label,data['cases'][case]['resources']['rss_MiB']['maximum'])
    axes[0].set_ylabel('Process CPU % (one core = 100%)');axes[0].set_xlabel('Seconds since first process sample');axes[0].legend();axes[0].grid(alpha=.25)
    axes[1].set_ylabel('Sampled peak RSS (MiB)');axes[1].set_title('Same standalone TTS workload; not full multimodal process memory')
    fig.savefig(out/'tts_resources.png',dpi=160);fig.savefig(out/'tts_resources.svg');plt.close(fig)
    if args.pipeline_case:
        case=data['cases'][args.pipeline_case];rows=case['profile_events'];fig,ax=plt.subplots(figsize=(11,4.5),layout='constrained');labels=[]
        spans=[('ASR','asr_begin','asr_end'),('Inference queue','inference_enqueued','inference_dequeued'),('Inference','inference_begin','inference_end'),('TTS queue','tts_enqueued','tts_dequeued'),('TTS generate','tts_generate_begin','tts_generate_end'),('Playback call','playback_convert_begin','alsa_drain_complete')]
        colors=plt.get_cmap('tab10')
        for y,(id,events) in enumerate(rows.items()):
            origin=min(v['at_ns'] for v in events.values());labels.append('Request '+id)
            for j,(label,a,b) in enumerate(spans):
                if a in events and b in events:ax.barh(y,(events[b]['at_ns']-events[a]['at_ns'])/1e9,left=(events[a]['at_ns']-origin)/1e9,color=colors(j),label=label if y==0 else None)
        ax.set_yticks(range(len(labels)),labels);ax.set_xlabel('Seconds relative to each request first recorded timestamp');ax.set_title(args.pipeline_case+' (submission timing is not acoustic output)');ax.legend(loc='upper left',bbox_to_anchor=(1,1));ax.grid(axis='x',alpha=.25)
        fig.savefig(out/'pipeline_breakdown.png',dpi=160);fig.savefig(out/'pipeline_breakdown.svg');plt.close(fig)
    print('PLOTS',out)
if __name__=='__main__':main()
