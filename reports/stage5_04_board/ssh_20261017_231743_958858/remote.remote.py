from pathlib import Path
import json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
p=r/'reports/stage5_04_board/candidate_voice_4t_final_retry1'
result=json.loads((p/'result.json').read_text())
assert result['returncode']==0 and result['text_tts_completed'] and result['vision_tts_completed'] and result['devices_released'] and result['original_321_unchanged']
feedback={'case': 'candidate_voice_4t_final_retry1', 'recorded_at': '2026-10-17T23:17:42.838533+08:00', 'initial_reply': '两个都回答了', 'clarification_question': '这两个回答是否都通过 HyperX 耳机实际听到了？若有明显杂音、缺字或视觉描述不符，也请说明。', 'clarification_reply': '两个都通过耳机实际听到了', 'both_TEXT_VISION_audible': True, 'visual_match_confirmed': None, 'no_audio_quality_defect_confirmed': None, 'note': '用户明确确认耳机实际听到两条回答；没有额外明确确认视觉匹配或无杂音，不推断。'}
with (p/'user_feedback.json').open('x',encoding='utf-8') as f:json.dump(feedback,f,ensure_ascii=False,indent=2)
print('USER_FEEDBACK_RECORDED',json.dumps(feedback,ensure_ascii=False))
