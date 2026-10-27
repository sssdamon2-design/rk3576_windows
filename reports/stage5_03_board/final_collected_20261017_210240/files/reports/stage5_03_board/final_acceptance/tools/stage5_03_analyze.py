#!/usr/bin/env python3
"""Summarize real Stage 5.3 evidence; never substitute synthetic performance data."""
from pathlib import Path
import argparse,array,csv,hashlib,json,math,re,statistics

ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return [json.loads(s) for s in p.read_text(encoding='utf-8').splitlines() if s]
def stats(xs):
    xs=sorted(xs)
    if not xs:return None
    return dict(n=len(xs),mean=statistics.mean(xs),p50=xs[math.ceil(len(xs)*.50)-1],p95=xs[math.ceil(len(xs)*.95)-1],minimum=xs[0],maximum=xs[-1])
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);args=parser.parse_args()
    base=args.collection/'files/reports/stage5_03_board';out=ROOT/'reports/stage5_03_local';out.mkdir(exist_ok=True)
    allstats={};flat=[];cases={}
    for folder in sorted(base.iterdir()):
        if not folder.is_dir():continue
        case={}
        for name in ['result','camera']:
            if (folder/(name+'.json')).exists():case[name]=load(folder/(name+'.json'))
        if (folder/'resources.jsonl').exists():
            sample=rows(folder/'resources.jsonl')
            case['resource_samples']=len(sample)
            for key in ['VmRSS','VmHWM']:
                values=[int(x[key].split()[0])/1024 for x in sample if key in x]
                if values:case[key+'_sampled_MiB']=stats(values)
        if (folder/'requests.csv').exists():
            req=list(csv.DictReader((folder/'requests.csv').open(encoding='utf-8')))
            case['requests']=len(req);case['successful']=sum(int(x['success']) for x in req)
            case['frame_age_warm9_ms']=stats([float(x['frame_age_ms']) for x in req[3:]])
            case['request_wall_ms']=stats([float(x['vlm_ms']) for x in req])
        if case:cases[folder.name]=case
        p=folder/'image_profile.jsonl'
        if not p.exists():continue
        groups={}
        for x in rows(p):groups.setdefault(x['stage'],[]).append(x)
        allstats[folder.name]={}
        for stage,values in sorted(groups.items()):
            s=stats([x['ms'] for x in values]);s.update(bytes_total=sum(x['bytes'] for x in values),allocations_total=sum(x['allocations'] for x in values))
            allstats[folder.name][stage]=s;flat.append(dict(case=folder.name,stage=stage,**s))
    compare=[];baseline=base/'baseline_fixed_6'
    for name in ['candidate_fixed_6','candidate_fallback_fixed_6','candidate_fixed_final_6']:
        folder=base/name
        if not folder.exists():continue
        for i in range(6):
            entry=dict(case=name,sample=i)
            for extension,size in [('rgb',786432),('f32',147456)]:
                a=(baseline/f'sample_{i}.{extension}').read_bytes();b=(folder/f'sample_{i}.{extension}').read_bytes()
                assert len(a)==len(b)==size
                entry[extension+'_bytes_equal']=a==b
                entry[extension+'_sha256']=hashlib.sha256(b).hexdigest()
                if extension=='rgb':
                    entry['rgb_max_abs_error']=max(abs(x-y) for x,y in zip(a,b));entry['rgb_mean_abs_error']=sum(abs(x-y) for x,y in zip(a,b))/len(a)
                else:
                    aa=array.array('f');aa.frombytes(a);bb=array.array('f');bb.frombytes(b)
                    entry['embedding_max_abs_error']=max(abs(x-y) for x,y in zip(aa,bb))
                    norm=math.sqrt(sum(x*x for x in aa)*sum(x*x for x in bb));entry['embedding_cosine']=sum(x*y for x,y in zip(aa,bb))/norm if norm else None
            def answers(p):return re.findall(r'\[MemoryProbe\] sample=\d+ success=1 frame=\d+ vlm_ms=[^ ]+ answer=(.*?) error=',p.read_text(encoding='utf-8',errors='replace'),re.S)
            aa=answers(baseline/'terminal.log');bb=answers(folder/'terminal.log')
            entry['answer_equal']=len(aa)==len(bb)==6 and aa[i]==bb[i]
            entry['baseline_answer']=aa[i] if len(aa)==6 else None;entry['candidate_answer']=bb[i] if len(bb)==6 else None
            compare.append(entry)
    paired=[]
    for folder in sorted(base.glob('rga_diagnostic*')):
        source=folder/'rga_samples.csv'
        if not source.exists():continue
        groups={}
        for row in csv.DictReader(source.open(encoding='utf-8')):
            groups.setdefault((row['frame'],row['mode']),[]).append(float(row['ms']))
        for (frame,mode),values in groups.items():paired.append(dict(case=folder.name,frame=int(frame),mode=mode,**stats(values)))
    summary=dict(collection=str(args.collection.relative_to(ROOT)) if args.collection.is_absolute() else str(args.collection),quantiles='nearest rank, no interpolation',duration_unit='ms',cases=cases,stages=allstats,fixed_comparisons=compare,paired_cpu_before_failed_rga=paired,limitations=['Fused conversion/resize measured together','Frame age is host DQBUF age, not optical age; warm live comparison excludes first 3 fixture writes','RSS sampled at 0.25s for probes, 1s for voice; not whole-system memory','Allocations are source-visible capacity/control-block events, not all mallocs','SDK internal copies/allocations and model embedded normalization unmeasured'])
    (out/'performance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'performance.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','stage','n','mean','p50','p95','minimum','maximum','bytes_total','allocations_total']);w.writeheader();w.writerows(flat)
    (out/'fixed_frame_comparison.json').write_text(json.dumps(compare,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'paired_cpu.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['case','frame','mode','n','mean','p50','p95','minimum','maximum']);w.writeheader();w.writerows(paired)
    print('ANALYZED',len(cases),'cases',len(flat),'stage statistics',len(compare),'fixed comparisons')
    for name in ['baseline_live_12_retry1','candidate_live_final_12']:
        print(name,json.dumps(cases.get(name),ensure_ascii=False))
        for key in ['capture_owned_copy','preprocess_fused','rknn_inputs_set','rknn_run','embedding_alloc_copy']:
            print(key,allstats.get(name,{}).get(key))
    print('FIXED_ALL_EQUAL',bool(compare) and all(x['rgb_bytes_equal'] and x['f32_bytes_equal'] and x['answer_equal'] for x in compare))
if __name__=='__main__':main()
