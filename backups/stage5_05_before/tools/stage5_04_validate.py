#!/usr/bin/env python3
"""Validate actual case outcomes; expected backpressure is checked separately."""
from pathlib import Path
import argparse,csv,hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collection',type=Path,required=True);args=parser.parse_args()
    base=args.collection/'files/reports/stage5_04_board';local=ROOT/'reports/stage5_04_local'
    load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    data=load(local/'analysis/performance.json');cases=data['cases'];checks={}
    selection=ROOT/'reports/stage5_04_local/voice_selection.json'
    voice_case=json.loads(selection.read_text(encoding='utf-8'))['case'] if selection.exists() else 'candidate_voice_4t_final'
    expected=['raw_tts_baseline_2t','raw_tts_final_4t','baseline_asr_30','candidate_asr_30','baseline_vision_30','candidate_vision_30','baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t','baseline_voice_2t',voice_case,'candidate_burst_audio','candidate_expiry_audio','candidate_sigint_drain','candidate_sigterm_cancel_tts','candidate_sigterm_cancel_waiting','candidate_final_sigterm_drain','candidate_default_queue_audio']
    for name in expected:
        r=cases[name]['result']
        checks[name]=r['returncode']==0 and not r.get('timeout',False) and not r.get('termination_reason') and not r['forced_kill'] and r['devices_released'] and r['process_gone'] and r['original_321_unchanged']
    for name in ['raw_tts_baseline_2t','raw_tts_final_4t']:
        rows=list(csv.DictReader((base/name/'tts_samples.csv').open(encoding='utf-8')))
        checks[name+'_30_per_language']=all(sum(x['phase']=='measured' and x['language']==language for x in rows)==30 for language in ('zh','en'))
        checks[name+'_finite_PCM']=all(int(x['nonfinite'])==0 and int(x['sample_rate'])==24000 and float(x['audio_seconds'])>0 and 0<float(x['peak'])<=1.0 and float(x['rms'])>0 for x in rows)
    initial=ROOT/'reports/stage5_04_board/collected_20261017_213845/files/reports/stage5_04_board/raw_baseline_build/tts_bench'
    current=base/'raw_baseline_build/tts_bench'
    checks['frozen_TTS_benchmark_binary_unchanged']=hashlib.sha256(initial.read_bytes()).digest()==hashlib.sha256(current.read_bytes()).digest()
    checks['same_fixed_TTS_input_bytes']=(base/'raw_tts_baseline_2t/inputs.txt').read_bytes()==(base/'raw_tts_final_4t/inputs.txt').read_bytes()
    for name in ['baseline_tts_ort_detail','candidate_tts_profile_4t','baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        events=cases[name].get('session_events',[])
        checks[name+'_TTS_initialized_once']=sum(x['event']=='tts_initialize_begin' for x in events)==1 and sum(x['event']=='tts_initialize_end' for x in events)==1
    for kind in ['asr','vision']:
        rows=[]
        for prefix in ('baseline','candidate'):
            rows.append(list(csv.DictReader((base/(prefix+'_'+kind+'_30')/(kind+'_samples.csv')).open(encoding='utf-8'))))
        checks[kind+'_30_each']=all(sum(x['phase']=='measured' for x in batch)==30 for batch in rows)
        checks[kind+'_output_texts_equal']=all(a.get('text',a.get('answer'))==b.get('text',b.get('answer')) for a,b in zip(*rows)) and len(rows[0])==len(rows[1])==32
    rgb=[];emb=[]
    for i in range(32):
        for suffix,target in [('rgb',rgb),('f32',emb)]:
            # Backend output suffixes are verified against actual files below.
            leaf=f'sample_{i}.'+suffix
            a=base/'baseline_vision_30'/leaf;b=base/'candidate_vision_30'/leaf
            target.append(a.is_file() and b.is_file() and a.read_bytes()==b.read_bytes())
    checks['RGB_32_pairs_byte_equal']=all(rgb);checks['embeddings_32_pairs_byte_equal']=all(emb)
    for name in ['baseline_pipeline_pairs_2t','candidate_pipeline_pairs_4t']:
        c=cases[name];counter=c['terminal_counters'];pipeline=counter['PipelineStats'];tts=counter['QueueStats/tts']
        checks[name+'_all_six_complete']=pipeline['accepted']==6 and pipeline['dispatched']==6 and pipeline['rejected']==0 and tts['accepted']==tts['completed']==6 and tts['failed']==tts['expired']==tts['cancelled']==0
    for name in expected:
        c=cases[name]
        for key,row in c.get('terminal_counters',{}).items():
            if key.startswith('QueueStats/'):
                checks[name+'_'+key+'_settled']=row['accepted']==row['completed'] and row['pending']==row['active']==row['failed']==row['callback_errors']==0
        if (base/name/'profile.jsonl').exists():checks[name+'_no_profile_errors']=not c.get('terminal_errors',{}).get('profile_error',0)
    checks['burst_exact_backpressure']=cases['candidate_burst_audio']['terminal_counters']['PipelineStats']['rejected']>=1
    checks['expiry_is_observed']=cases['candidate_expiry_audio']['terminal_counters']['QueueStats/tts']['expired']>=1
    checks['cancelled_waiting_TTS_observed']=cases['candidate_sigterm_cancel_tts']['terminal_counters']['QueueStats/tts']['cancelled']>=1
    w=cases['candidate_sigterm_cancel_waiting'];p=w['terminal_counters']['PipelineStats']
    checks['cancel_future_input_did_not_wait_100s']=w['result']['signal_to_exit_seconds']<30 and (p['downstream_cancelled']+p['vision_cancelled']>=1)
    for name in ['candidate_sigint_drain','candidate_final_sigterm_drain']:
        c=cases[name];checks[name+'_drained_active_request']=c['terminal_counters']['QueueStats/tts']['completed']>=1 and c['result']['shutdown_complete_marker'] and c['result']['signal_to_exit_seconds']<60
    for name in ['baseline_voice_2t',voice_case]:
        c=cases[name];feedback=load(base/name/'user_feedback.json') if (base/name/'user_feedback.json').exists() else {}
        checks[name+'_user_actually_heard_both']=feedback.get('both_TEXT_VISION_audible') is True
        checks[name+'_TEXT_VISION_success']=c['result']['text_tts_completed'] and c['result']['vision_tts_completed']
        checks[name+'_zero_XRUN']=c['terminal_counters']['ALSA']['XRUN']==0
        checks[name+'_frame_pool_released']=c['terminal_counters']['FramePool']['in_use']==0
    arm=load(base/'candidate_build_v3/result.json');checks['final_ARM64_config_build_ctest']=arm['successful']
    xml=ET.parse(base/'candidate_build_v3/ctest.xml').getroot();tests=xml.findall('.//testcase');checks['ARM64_CTest_7_passed']=len(tests)==7 and not xml.findall('.//failure') and not xml.findall('.//error')
    portable=load(local/'instrumentation_local_v6/result.json');checks['local_portable_checks']=portable['successful']
    guard=base/('protection_final_after_manual' if (base/'protection_final_after_manual/result.json').exists() else 'protection_final')
    protection=load(guard/'result.json') if (guard/'result.json').exists() else None;checks['protection']=bool(protection and all(protection['checks'].values()) and all(x['all_sha_match'] for x in protection['frozen_stage5_04_sources'].values()))
    patch=load(local/'patch_roundtrip.json');invariants=load(local/'source_invariants.json')
    checks['patch_byte_roundtrip']=patch['exit_code']==0 and patch['all_bytes_match'];checks['source_matches_final_ARM64']=invariants['final_source_matches_ARM64_candidate_v3']
    targets=re.findall(r'Built target (\S+)',(base/'candidate_build_v3/build.stdout.log').read_text())
    summary={'stage':'5.4','engineering_status':'verified within recorded scenarios; user acceptance pending' if all(checks.values()) else 'NOT ACCEPTABLE: checks failed','user_acceptance_pending':True,'next_stage_started':False,'scope':'authorized isolated review directory only','checks':checks,'all_checks_passed':all(checks.values()),'final_ARM64_targets':targets,'final_ARM64_CTest':{'total':len(tests),'passed':sum(not t.findall('failure') and not t.findall('error') for t in tests),'seconds':sum(float(t.attrib.get('time',0)) for t in tests),'type':'Fake/deterministic unit tests; hardware cases separate'},'local_portable':portable,'TTS_warm_measured_each_language':30,'performance_comparison':{language:{'before_mean_ms':cases['raw_tts_baseline_2t']['tts'][language+'/measured']['synthesis_ms']['mean'],'after_mean_ms':cases['raw_tts_final_4t']['tts'][language+'/measured']['synthesis_ms']['mean']} for language in ('zh','en')},'fixed_vision_RGB_pairs':len(rgb),'fixed_vision_embedding_pairs':len(emb),'protection':protection,'source_invariants':invariants,'patch_roundtrip':{'exit_code':patch['exit_code'],'all_bytes_match':patch['all_bytes_match'],'files':len(patch['files'])},'selected_voice_case':voice_case,'retained_failed_voice_trial':cases['candidate_voice_4t_final']['result'] if voice_case!='candidate_voice_4t_final' else None,'collection':str(args.collection),'limitations':['Natural speech and full-pipeline repeats are finite small samples','ALSA submit/drain is not acoustic latency','True token-granular TTFT unmeasured','TTS frontend/phonemization not separately measured','No reliable NPU utilization/bandwidth/power measurement','Higher CPU and temperature with four TTS threads','No long-duration stress, sanitizer proof or full real-SDK failure injection','Full n30 fixed-model and paired regressions use v2; final v3 changes only audio-replay error checks and is separately rebuilt/CTest/live-voice/signal tested']}
    (local/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('VALIDATION',sum(checks.values()),'/',len(checks),'failed',[k for k,v in checks.items() if not v])
    return 0 if all(checks.values()) else 1

if __name__=='__main__':raise SystemExit(main())
