#!/usr/bin/env python3
"""Bind Stage 5.3 acceptance statements to actual local/board evidence."""
from pathlib import Path
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def main():
 report=ROOT/'reports/stage5_03_local';p=load(report/'performance.json');board=ROOT/p['collection']/'files/reports/stage5_03_board'
 final=max((ROOT/'reports/stage5_03_board').glob('final_collected_*'),key=lambda x:x.stat().st_mtime)/'files/reports/stage5_03_board/final_state'
 arm_xml=board/'candidate_config_review/ctest.xml';tree=ET.parse(arm_xml);tests=tree.findall('.//testcase');failures=tree.findall('.//failure');errors=tree.findall('.//error')
 ctest=dict(platform='ARM64 native',tests=len(tests),passed=len(tests)-len(failures)-len(errors),failures=len(failures),errors=len(errors),time_seconds=sum(float(x.attrib.get('time',0)) for x in tests),returncode=load(board/'candidate_config_review/ctest.result.json')['returncode'],names=[x.attrib['name'] for x in tests],hardware_inference=False,evidence=str(arm_xml.relative_to(ROOT)))
 cases={n:p['cases'][n]['result'] for n in ['candidate_live_final_12','candidate_fixed_final_6','candidate_fallback_live_3','candidate_fallback_fixed_6','voice_natural_retry1','sigint_idle_final','sigterm_vision_cancel_final','sigterm_tts_drain_final']}
 assert ctest['tests']==ctest['passed']==6 and ctest['returncode']==0
 assert all(x['returncode']==0 and x['devices_released'] and x['process_gone'] and x['original_321_unchanged'] and not x['forced_kill'] for x in cases.values())
 confirmation=load(ROOT/'reports/stage5_03_board/user_confirmations.json');assert confirmation['text_audio_confirmed'] and confirmation['vision_audio_confirmed']
 assert len(p['fixed_comparisons'])==18 and all(x['rgb_bytes_equal'] and x['f32_bytes_equal'] and x['answer_equal'] for x in p['fixed_comparisons'])
 local_log=(report/'final_config_ctest.stdout.log').read_text(encoding='utf-8');assert '100% tests passed, 0 tests failed out of 8' in local_log
 a=p['stages']['baseline_live_12_retry1']['preprocess_fused']['mean'];b=p['stages']['candidate_live_final_12']['preprocess_fused']['mean']
 local=dict(platform='Windows portable SDK off',tests=8,passed=8,failures=0,returncode=0,time_seconds=1.74,evidence='reports/stage5_03_local/final_config_ctest.stdout.log',hardware_verification=False)
 unchanged=load(final/'result.json');assert all(v for k,v in unchanged.items() if isinstance(v,bool))
 patch=load(report/'patch_roundtrip.json');assert patch['exit_code']==0 and patch['all_bytes_match']
 rga={n:load(board/n/'result.json') for n in ['rga_diagnostic','rga_diagnostic_dma','rga_diagnostic_split']};assert all(x['returncode']==1 for x in rga.values())
 targets=re.findall(r'Built target (\S+)',(board/'candidate_build/build.stdout.log').read_text(encoding='utf-8'));targets=sorted(set(targets));assert len(targets)==26
 summary=dict(stage='5.3',date='2026-10-17',engineering_status='CPU path verified; RGA diagnostics failed and not enabled',user_acceptance_pending=True,next_stage_started=False,next_stage='5.4 only after user acceptance',scope='/home/cat/projects/RK3576/rk3576_multimodal_stage5_review',arm64_configure_and_build=load(board/'candidate_build/result.json'),arm64_targets=targets,arm64_final_ctest=ctest,local_portable_ctest=local,hardware_cases=cases,user_confirmation=confirmation,fixed_comparison_count=18,fixed_rgb_embeddings_answers_all_equal=True,preprocessing=dict(baseline_mean_ms=a,candidate_mean_ms=b,reduction_percent=(1-b/a)*100,samples_each=12),source_visible_warm_allocations_per_frame=dict(before=5,after=1,scope='Not global malloc totals; excludes cold pool initialization'),copy_reduction=False,zero_copy=False,rga_enabled_in_production=False,rga_failed_diagnostics=rga,retained_failed_voice=load(board/'voice_natural_final/result.json'),protection=unchanged,final_state_collection=str(final.relative_to(ROOT)),source_invariants=load(report/'source_invariants.json'),patch_check=load(report/'patch_check.json'),patch_roundtrip=dict(exit_code=patch['exit_code'],all_bytes_match=patch['all_bytes_match'],files=len(patch['files'])),limitations=p['limitations']+['RGA hardware timeout root cause unresolved','Existing device full-range metadata versus preserved limited-range conversion needs independent calibration','No ASan/TSan or long duration leak/stress verification','Small sample, frequency and scene not locked; local preprocessing gain is not an end-to-end gain'])
 (report/'validation_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('VALIDATED',len(targets),'ARM targets; CTest',ctest['passed'],'; fixed groups',18,'; user acceptance pending')
if __name__=='__main__':main()
