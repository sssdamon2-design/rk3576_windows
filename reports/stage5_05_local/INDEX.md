# 第五阶段最终结果与证据索引

5.1～5.4已由用户验收。5.5提交最终用户审核，隔离版未覆盖主稳定工程。最终手册为docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx与同名.md；报告为docs/stage5_05_final_acceptance.md。

工程机器检查：135/135；all_checks_passed=True。每个check的具体证据见validation_summary.json。

## 文件分类

| 类型 | 真实位置 |
|---|---|
| 完整Git格式差异 | changes.patch，change_manifest.json |
| 精确补丁还原 | patch_check.json，patch_roundtrip.json |
| 源码版本与算法不变量 | source_invariants.json，final_v2_deployment_manifest.json |
| 最终源码全文与解释 | docs/stage5_05_source_appendix.md，statement_notes.md，line_notes.md |
| 请求与统计 | analysis/requests.csv，statistics.csv，performance.json |
| 温度内存与RTF | analysis/stability_requests.csv，stability_resources.csv，stability_statistics.csv，stability.json |
| 科学绘图与架构 | plots/*.png及.svg，figures/gui_*.png |
| Word正文及逐页检查 | document_build.json，document_QA.json，manual_source_manifest.json |
| 原始板端日志 | reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/ |
| 主机SSH命令与原始返回 | reports/stage5_05_board/ssh_*/remote.* |
| 本地Fake测试 | portable_structured_text/，structured_text_validation.json；不等于ARM |

## 实机案例索引

| Case | 退出码 | 时间秒 | 实际范围 |
|---|---|---|---|
| camera_gap_recheck | 0 | 112.84128189699913 | LIVE Camera and real VLM only; no ASR, Qwen or TTS; no pixel/semantic ground truth for every frame；原始result.json及terminal.log |
| final_burst_audio | None | None | NOT_EXECUTED protection refused preexisting seat DRM owners；原始result.json及terminal.log |
| final_burst_audio_retry1 | 0 | 47.81705280100141 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| final_expiry_audio | 0 | 48.21312145699994 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| final_sigint_asr | 0 | 38.448516194999684 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| final_sigint_drain | 0 | 38.95098321399928 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| final_sigterm_cancel_waiting | 0 | 39.597558984998614 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| final_sigterm_initialization | 0 | 23.79481105800005 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| gui_microphone_final_v2 | 0 | 79.4961776759992 | microphone；原始result.json及terminal.log |
| gui_mixed_1800s_4t_final_v2 | 0 | 1837.7822822689996 | stability；原始result.json及terminal.log |
| gui_paired_restart_final_v2 | 0 | 102.26650997400066 | paired_restart；原始result.json及terminal.log |
| gui_sigterm_vision_final_v2 | 0 | 53.1265482710005 | sigterm_vision；原始result.json及terminal.log |
| mixed_1800s_2t | 0 | 1839.8901995140004 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| mixed_1800s_4t | 0 | 1833.323821127 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| mixed_180s_2t | 0 | 221.52749982000023 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |
| mixed_180s_4t | 0 | 218.62452942800155 | fixed_audio_REAL_ASR_no_microphone_VAD；原始result.json及terminal.log |

ARM64注册8项均为Fake/确定性测试，真实SDK运行另列；人工HyperX和GUI反馈保存于gui_microphone_final_v2/user_feedback.json。最终Qt长测的父/子资源分开，首轮mic/paired后台采样缺失不补造。实际无效路径4项期待返回1并清理；其日志位于real_invalid_paths各子目录。

## 历史验收与保留局限

5.1架构/生命周期报告，5.2异步/性能报告，5.3memory_pipeline与失败RGA，5.4performance_profiling与2/4线程n30均在docs/。阶段冻结源位于backups/及板端各stage5_XX_source*；不修改过去的失败记录或用户审核前状态。完整历史原始证据使用交付归档清单列出的canonical collections，模型/SDK继续原路径。

声学输出、精确token TTFT、可靠NPU利用率/功耗未测；未实现零拷贝、RGA生产、AEC/PTT和全真实拔插恢复；没有单进程60分钟保证。4线程默认适用已记录负载，2线程可配，Linux thermal限频确有观测，不能称无热代价。

## 最终归档

RK3576_STAGE5_FINAL_REVIEW.tgz按final_archive_manifest.json逐文件SHA生成，包含全部源码/文档及五阶段canonical证据，排除模型、重复构建和内部QA PNG/PDF。final_archive.json记录外层SHA；final_delivery_receipt.json是归档完成后的外部收据，不能将自身收据递归放入同一个归档。板端仅保存于授权reports/stage5_05_board/final_acceptance，不解压覆盖、不升级稳定版本。
