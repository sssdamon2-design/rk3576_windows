#!/usr/bin/env python3
"""Derive the Stage 5.1 acceptance summary from preserved board/user evidence."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=Path('reports/stage5_01_board/phase3_ssh_20261017_190524_321782')
BASE=ROOT/EVIDENCE/'collected/reports/stage5_01_board'


def read(path):
    return path.read_text(encoding='utf-8')


def load(path):
    return json.loads(read(path))


def counters(text):
    labels=('VAD segments','ASR recognized','Audio queue dropped',
            'LLM accepted/completed/success/failed/rejected',
            'TTS accepted/completed/success/failed/rejected/empty',
            'VISION completed/success/failed')
    result={}
    for label in labels:
        match=re.search('^'+re.escape(label)+r': ([0-9/]+)\s*$',text,re.M)
        assert match, 'Missing counter: '+label
        result[label]=[int(n) for n in match.group(1).split('/')]
    return result


def main():
    cases={}
    for name in ('baseline_sigint','baseline_sigterm','fixed_idle_sigint','fixed_idle_sigterm',
                 'fixed_initializing_sigterm','voice_both_natural_01','voice_text_active_sigterm'):
        folder=BASE/name
        result=load(folder/'result.json')
        terminal=read(folder/'terminal.log')
        capture=re.search(r'\[ALSA\] XRUN=(\d+) Suspends=(\d+) Recoveries=(\d+) RecoveryFailures=(\d+)',terminal)
        result['capture_error_counters']=dict(zip(('xruns','suspends','recoveries','recovery_failures'),map(int,capture.groups()))) if capture else None
        playback=re.search(r'\[Shutdown\] TTS joined; playback_xruns=(\d+)',terminal)
        result['playback_xruns']=int(playback.group(1)) if playback else None
        result['nonfatal_diagnostics']={'kokoro_unknown_token':terminal.count('Unknown token:'),
                                        'rkllm_custom_template_warning':terminal.count('Calling rkllm_set_chat_template will disable')}
        samples=[json.loads(line) for line in read(folder/'resources.jsonl').splitlines()]
        result['sampled_max_rss_kib']=max((int(s['VmRSS'].split()[0]) for s in samples if 'VmRSS' in s),default=0)
        result['sampled_max_threads']=max((int(s['Threads']) for s in samples if 'Threads' in s),default=0)
        result['evidence_directory']=(EVIDENCE/'collected/reports/stage5_01_board'/name).as_posix()
        assert not result['forced_kill'] and not result['timeout']
        assert result['process_gone'] and result['devices_released'] and result['original_321_unchanged']
        if name.startswith('baseline_'):
            assert result['returncode']==(-2 if name.endswith('sigint') else -15)
            result['acceptance']='OBSERVED_DEFECT_BEFORE_FIX'
        else:
            assert result['returncode']==0 and result['shutdown_complete_marker']
            result['acceptance']='PASSED'
            result['counters']=counters(terminal)
            assert result['playback_xruns']==0
            if result['capture_error_counters'] is not None:
                assert all(v==0 for v in result['capture_error_counters'].values())
        if 'timing_scope' not in result:
            result['timing_interpretation']='Legacy interval includes post-exit device/fingerprint queries; conservative upper bound, not precise child exit latency'
        cases[name]=result
    core=cases['voice_both_natural_01']
    assert core['program_PASS'] and core['text_tts_completed'] and core['vision_tts_completed']
    assert core['counters']['LLM accepted/completed/success/failed/rejected']==[1,1,1,0,0]
    assert core['counters']['TTS accepted/completed/success/failed/rejected/empty']==[2,2,2,0,0,0]
    assert core['counters']['VISION completed/success/failed']==[1,1,0]
    assert core['counters']['VAD segments']==core['counters']['ASR recognized']==[2]
    assert core['counters']['Audio queue dropped']==[0]
    active=cases['voice_text_active_sigterm']
    assert active['text_tts_completed'] and active['counters']['TTS accepted/completed/success/failed/rejected/empty']==[1,1,1,0,0,0]
    user=load(ROOT/'reports/stage5_01_board/user_participation.json')
    assert user['audible_confirmation']['run']=='voice_both_natural_01'
    assert user['audible_confirmation']['text_answer_heard'] and user['audible_confirmation']['vision_answer_heard']
    assert user['active_signal_audible_confirmation']['text_answer_heard']
    assert load(BASE/'voice_text_active_sigterm/user_confirmation.json')==user
    suites=[]
    for folder in (BASE/'phase3_precheck_ctest_20261017T105346Z',BASE/'signal_fix_20261017T105740Z'):
        xml=ET.parse(folder/'ctest.xml').getroot()
        assert xml.attrib['tests']=='4' and xml.attrib['failures']=='0'
        tests=[{'name':e.attrib['name'],'time_seconds':float(e.attrib['time']),
                'kind':'pure_algorithm' if e.attrib['name']=='audio_preprocessor_tests' else 'Fake_or_Mock_unit_test'} for e in xml.findall('testcase')]
        output=read(folder/'ctest.stdout.log')
        total=float(re.search(r'Total Test time \(real\) =\s+([0-9.]+)',output).group(1))
        code=load(folder/'result.json')['ctest_exit_code'] if (folder/'result.json').exists() else int(read(folder/'ctest.exit_code.txt'))
        assert code==0
        suites.append({'folder':folder.name,'total':4,'passed':4,'failed':0,'exit_code':code,'ctest_total_seconds':total,'tests':tests})
    build_folder=BASE/'signal_fix_20261017T105740Z'
    rebuilt=set(re.findall(r'Built target (\S+)',read(build_folder/'build.stdout.log')))
    original_targets=set(load(ROOT/'reports/stage5_01_board/phase2_summary.json')['build_targets_passed'])
    assert rebuilt==original_targets and len(rebuilt)==21
    assert load(build_folder/'build.result.json')=={'returncode':0,'stop_reason':None}
    final=load(BASE/'phase3_final_20261017T110519Z/result.json')
    assert final['original_321_unchanged'] and final['devices']['clear'] and not final['live_isolated_voice_pids']
    assert final['local_remote_source_files_match']==77
    baseline=load(ROOT/'reports/stage5_01_board/stable_original_baseline.json')['fingerprints']
    assert load(BASE/'phase3_final_20261017T110519Z/original_fingerprint.json')==baseline
    for name,digest in load(BASE/'phase3_final_20261017T110519Z/source_sha256.json').items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    initial=load(BASE/'baseline_sigint/system_after.json')['dmesg']
    final_kernel=final['dmesg']
    added=[line for line in final_kernel['stdout'].splitlines() if line not in set(initial['stdout'].splitlines())]
    suspicious=[line for line in added if re.search(r'BUG:|Oops:|segfault|Out of memory|Killed process|rknpu.*(?:failed|error|timeout)',line,re.I)]
    assert final_kernel['exit_code']==0 and not suspicious
    summary={'status':'STAGE5_01_ACCEPTED','scope':'Bounded ARM64 unit tests and short real hardware regression; not proof of long-run leak freedom or exhaustive SDK failure behavior',
             'stage5_01_formally_accepted':True,'ready_for_stage5_02':True,'stage5_02_implementation_started':False,
             'host':'cat@192.168.10.27','remote_root':'/home/cat/projects/RK3576/rk3576_multimodal_stage5_review',
             'local_complete_evidence':EVIDENCE.as_posix(),'arm64_build':'21/21 targets built; post-fix rebuild exit 0',
             'post_fix_build_targets':sorted(rebuilt),'post_fix_build_exit_code':0,
             'ctest_runs':suites,'hardware_and_signal_runs':cases,'user_confirmation':user,
             'error_statistics':{'original_signal_defects_observed':2,'post_fix_case_failures':0,
                                 'ctest_failures_before_fix':0,'ctest_failures_after_fix':0,
                                 'timeouts':0,'forced_kills':0,'core_audio_queue_dropped':0,
                                 'core_llm_failures':0,'core_vision_failures':0,'core_tts_failures':0,
                                 'note':'Absent pre-fix/early-stop capture statistics remain null, not fabricated zeros; known nonfatal model diagnostics are counted per case'},
             'final_checks':{'time':final['time']['stdout'].strip(),'original_321_unchanged':True,'source_files_match':77,
                             'target_devices_clear':True,'live_isolated_voice_pids':[],
                             'disk_free_bytes':final['disk_free_bytes'],'memory_command':final['memory'],
                             'existing_3a_service':final['existing_3a_service'],
                             'new_kernel_lines_since_baseline':len(added),'matching_oom_crash_npu_error_lines':suspicious},
             'production_fix_files':['src/audio/asr_llm_tts_smoke.cpp','include/audio/vad_audio_worker.h','src/audio/vad_audio_worker.cpp'],
             'phase3_production_patch':'reports/stage5_01_local/phase3_signal_fix/signal_fix.patch',
             'phase3_raw_git_diff':'reports/stage5_01_local/phase3_signal_fix/signal_fix.git.diff',
             'remaining_risks':['Synchronous SDK initialization/inference and blocking ALSA calls are drained, not forcibly cancelled; hung SDK remains bounded by the external test guard only',
                                'Short separate-process regressions do not prove same-process long-duration leak freedom; no ASan/Valgrind or exhaustive SDK fault injection',
                                'RKNN failed outputs_get ownership and release/destroy error returns remain untested SDK failure cases',
                                'Runtime callback serialization/late-userdata behavior is not exhaustively proven; current real synchronous runs passed',
                                'Completion callback exception can still lose completion accounting; prior documented risk, not observed in these runs',
                                'NPU parallel arbitration/throughput not tested; Stage 5.2 architecture remains unchanged',
                                'Existing Kokoro unknown-token and RKLLM custom-template diagnostics retained; no model modifications',
                                'VLM image semantics and varied Chinese visual questioning not accepted; original fixed English prompt retained']}
    output=ROOT/'reports/stage5_01_board/phase3_summary.json'
    output.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    artifacts=[]
    for p in sorted((ROOT/EVIDENCE).rglob('*')):
        if p.is_file():
            artifacts.append({'file':p.relative_to(ROOT/EVIDENCE).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    (ROOT/'reports/stage5_01_board/phase3_evidence_manifest.json').write_text(json.dumps(artifacts,indent=2)+'\n',encoding='utf-8')
    print('Verified board/user evidence: CTest 4/4 twice, original signal defect twice, five successful fixed hardware/signal cases; original 321 entries unchanged.')
    print('Stage 5.1 accepted within documented scope; Stage 5.2 not started.')


if __name__=='__main__':
    main()
