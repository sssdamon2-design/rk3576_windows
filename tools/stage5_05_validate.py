"""Verify Stage5.5 using exact outcomes; a transport success is not hardware success."""
from pathlib import Path
import argparse,hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);p.add_argument('--require-document',action='store_true');a=p.parse_args()
 base=a.collection/'files/reports/stage5_05_board';local=ROOT/'reports/stage5_05_local';data=load(local/'analysis/performance.json');cases=data['cases'];st=load(local/'analysis/stability.json');checks={}
 for name in ['mixed_180s_2t','mixed_180s_4t','mixed_1800s_2t','mixed_1800s_4t','gui_microphone_final_v2','gui_paired_restart_final_v2','gui_sigterm_vision_final_v2','gui_mixed_1800s_4t_final_v2','final_burst_audio_retry1','final_expiry_audio','final_sigint_drain','final_sigterm_cancel_waiting','final_sigterm_initialization','final_sigint_asr']:
  r=cases[name]['result'];checks[name+'_clean']=r['returncode']==0 and not r.get('timeout') and not r.get('termination_reason') and not r['forced_kill'] and r['devices_released'] and r['process_gone'] and r['original_321_unchanged']
  if name.startswith('gui_'):checks[name+'_sessions']=r['all_sessions_orderly']
 for name in ['mixed_1800s_2t','mixed_1800s_4t']:
  c=cases[name];q=c['terminal_counters'];checks[name+'_121_full_answers']=q['PipelineStats']['dispatched']==121 and q['PipelineStats']['accepted']==121 and q['PipelineStats']['rejected']==0 and q['QueueStats/tts']['completed']==121 and q['QueueStats/tts']['failed']==q['QueueStats/tts']['expired']==q['QueueStats/tts']['cancelled']==0
  checks[name+'_no_audio_drop']=q['AudioQueueStats']['dropped']==0
  resource=st['cases'][name]['resources'];checks[name+'_RSS_observed_plateau']=abs(resource['RSS_slope_MiB_per_minute'])<1 and abs(resource['median_25_to_30min_MiB']-resource['median_5_to_10min_MiB'])<16
 inputs=st['matched_long_test_inputs'];checks['matched_thermal_inputs']=inputs['mixed_1800s_2t']['input_sha256']==inputs['mixed_1800s_4t']['input_sha256'] and all(x['lines']==121 for x in inputs.values())
 gui=[(n,c) for n,c in cases.items() if n.startswith('gui_mixed_1800s_4t_final_v2/run_')];checks['one_final_GUI_long_session']=len(gui)==1
 if gui:
  n,c=gui[0];q=c['terminal_counters'];checks['final_GUI_long_121_answers']=q['PipelineStats']['dispatched']==q['QueueStats/tts']['completed']==121 and q['PipelineStats']['rejected']==0 and q['QueueStats/tts']['failed']==q['QueueStats/tts']['expired']==0
  checks['final_GUI_long_backend_samples']=c['resources']['samples']>=1500
  res=st['cases'][n]['resources'];checks['final_GUI_RSS_observed_plateau']=abs(res['RSS_slope_MiB_per_minute'])<1 and abs(res['median_25_to_30min_MiB']-res['median_5_to_10min_MiB'])<16
 for n,c in cases.items():
  if 'terminal.log' not in [p.name for p in (base/n).glob('terminal.log')]:continue
  if n.startswith(('mixed_','final_')) or '/run_' in n:
   ctr=c.get('terminal_counters',{});checks[n+'_no_active_or_pending']=all(q.get('pending',0)==0 and q.get('active',0)==0 for k,q in ctr.items() if k.startswith('QueueStats/'))
   checks[n+'_frame_pool_released']=ctr.get('FramePool',{}).get('in_use')==0
   text=(base/n/'terminal.log').read_text(encoding='utf-8',errors='replace');checks[n+'_no_XRUN']='xruns=1' not in text and not re.search(r'\[ALSA\] XRUN=[1-9]',text)
  res=c.get('resources')
  if res and res.get('temperature_C'):checks[n+'_below_test_guard']=max(v['maximum'] for v in res['temperature_C'].values())<90
 checks['final_burst_backpressure_observed']=cases['final_burst_audio_retry1']['terminal_counters']['PipelineStats']['rejected']>=1
 checks['final_expiry_observed']=cases['final_expiry_audio']['terminal_counters']['QueueStats/tts']['expired']>=1
 checks['final_cancel_waiting_observed']=cases['final_sigterm_cancel_waiting']['terminal_counters']['QueueStats/tts']['cancelled']>=1
 for name,expected in [('final_sigint_drain','SIGINT'),('final_sigterm_cancel_waiting','SIGTERM'),('final_sigterm_initialization','SIGTERM'),('final_sigint_asr','SIGINT')]:
  x=cases[name]['result'];checks[name+'_signal']=x['sent_signal']==expected and x['trigger_observed'] and x['shutdown_complete_marker'] and x['signal_to_exit_seconds']<90
 checks['gui_SIGTERM_active_vision']=cases['gui_sigterm_vision_final_v2']['result']['sent_signal']=='SIGTERM' and cases['gui_sigterm_vision_final_v2']['result']['signal_to_exit_seconds']<90
 f=load(base/'gui_microphone_final_v2/user_feedback.json');checks['user_heard_TEXT_and_VISION']=f['both_TEXT_VISION_audible'] is True;checks['user_saw_GUI_and_matching_scene']=f['vision_roughly_matches'] is True and f['GUI_recognition_route_answer_visible'] is True
 fault=load(base/'real_invalid_paths/result.json');checks['real_invalid_paths_expected_clean']=fault['complete'] and len(fault['cases'])==4 and all(x['expected_failure_clean'] and x['returncode']==1 for x in fault['cases']) and fault['devices_released'] and fault['original_321_unchanged']
 build=load(base/'build_final_v2/result.json');checks['ARM64_config_build_CTest']=build['successful'] and all(x['returncode']==0 and not x['reason'] for x in build['steps'])
 xml=ET.parse(base/'build_final_v2/ctest.xml').getroot();tests=xml.findall('.//testcase');checks['ARM64_8_CTest']=len(tests)==8 and not xml.findall('.//failure') and not xml.findall('.//error')
 portable=load(local/'portable_structured_text/result.json');checks['portable_9_tests']=portable['successful'];checks['structured_text_roundtrip']=(lambda t:t['all_lines_parse'] and t['UTF8_quote_backslash_newline_CR_tab_control_roundtrip'] and t['concurrent_text_events']==50)(load(local/'structured_text_validation.json'))
 for n,c in cases.items():
  path=base/n/'profile.jsonl'
  if not path.exists():continue
  events=[json.loads(s) for s in path.read_text(encoding='utf-8').splitlines() if s.strip()]
  checks[n+'_valid_JSONL']=all(isinstance(e,dict) for e in events)
  if n.startswith('gui_') and '/run_' in n:
   answers=[x for x in events if x.get('event')=='answer_text'];checks[n+'_structured_answers']=len(answers)>=c['result']['answers_completed'] and all(isinstance(x.get('text'),str) and x['text'].strip() for x in answers)
 protection=load(base/'protection_final_after_camera/result.json');checks['original_and_frozen_protection']=all(protection['checks'].values())
 camera=cases['camera_gap_recheck'];r=camera['result'];checks['live_camera_VLM_64_recheck']=r['returncode']==0 and r['all_VLM_success'] and r['samples']==64 and r['devices_released'] and r['original_321_unchanged'] and not r['termination_reason'] and not r['forced_kill']
 checks['camera_recheck_no_sequence_gap']=camera['terminal_counters']['CameraCounters']['driver_sequence_gaps']==0
 primary=load(base/'protection_final_after_camera/devices.json');checks['NPU_primary_owners_restored_exactly']=all(x['matches_frozen_desktop_owners'] for x in primary['primary_owner_queries'].values()) and primary['query']['exit_code']==1
 patch=load(local/'patch_roundtrip.json');invariants=load(local/'source_invariants.json');checks['patch_roundtrip']=patch['exit_code']==0 and patch['all_bytes_match'];checks['exact_ARM64_source']=invariants['final_source_matches_ARM64_final_v2'];checks['inherited_algorithms_and_signals']=invariants['StopSignals_class_body_unchanged'] and all(x['unchanged'] for x in invariants['checks'])
 if a.require_document:
  qa=load(local/'document_QA.json');checks['all_Word_pages_visually_checked']=qa['all_pages_inspected'] and qa['clean'] and qa['pages']==len(qa['inspected_pages'])
  checks['document_hash_matches_QA']=hashlib.sha256((ROOT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx').read_bytes()).hexdigest()==qa['docx_sha256']
 targets=sorted(set(re.findall(r'Built target (\S+)',(base/'build_final_v2/build.stdout.log').read_text(encoding='utf-8',errors='replace'))))
 result=dict(stage='5.5',all_checks_passed=all(checks.values()),checks=checks,engineering_status='verified in recorded finite scenarios; final user review pending' if all(checks.values()) else 'NOT PASSED',user_acceptance_pending=True,stable_promoted=False,next_stage_started=False,collection=str(a.collection),final_source='stage5_05_source_final_v2',ARM64_targets=targets,ARM64_CTest=dict(total=len(tests),passed=sum(not t.findall('failure') and not t.findall('error') for t in tests),seconds=sum(float(t.attrib.get('time',0)) for t in tests),type='Fake/deterministic; real hardware separate'),document_gate_required=a.require_document,limitations=st['limits']+['Final GUI long test had one driver sequence gap; targeted 64-call live recheck did not reproduce; exact cause unresolved','No proof all closed SDK allocations are leak free','No physical unplug or SDK internal corruption injection','Qt Widgets succeeded despite existing DRI warnings','No stable version replacement'])
 (local/'validation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('VALIDATION',sum(checks.values()),'/',len(checks),'FAILED',[k for k,v in checks.items() if not v]);return 0 if result['all_checks_passed'] else 1
if __name__=='__main__':raise SystemExit(main())
