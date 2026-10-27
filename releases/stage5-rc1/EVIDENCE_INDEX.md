# 五阶段证据与RC结果索引

历史完整归档：evidence/RK3576_STAGE5_FINAL_REVIEW.tgz，外层SHA及逐文件清单见evidence/final_archive.json和final_archive_manifest.json。本轮已逐文件验证其中4835成员，未重写历史失败。只解到新证据目录，不把归档中的历史源码或路径当正式入口。

| 小节 | 报告 | 独立Diff/机器结果 |
|---|---|---|
| 5.1 | [报告](docs/stage5_01_architecture_audit.md) | [Git格式Diff](evidence/stage5_01/changes.patch)、[验证结果](evidence/stage5_01/validation_summary.json) |
| 5.2 | [报告](docs/stage5_02_board_acceptance.md) | [Git格式Diff](evidence/stage5_02/changes.patch)、[验证结果](evidence/stage5_02/validation_summary.json) |
| 5.3 | [报告](docs/stage5_03_memory_pipeline.md) | [Git格式Diff](evidence/stage5_03/changes.patch)、[验证结果](evidence/stage5_03/validation_summary.json) |
| 5.4 | [报告](docs/stage5_04_performance_profiling.md) | [Git格式Diff](evidence/stage5_04/changes.patch)、[验证结果](evidence/stage5_04/validation_summary.json) |
| 5.5 | [报告](docs/stage5_05_final_acceptance.md) | [Git格式Diff](evidence/stage5_05/changes.patch)、[验证结果](evidence/stage5_05/validation_summary.json) |

历史内层归档保留的最新规范采集目录：5.2 collected_20261017_195843；5.3 collected_20261017_205548；5.4 collected_20261017_231748；5.5 collected_20261018_014600。5.1为原始phase2/phase3目录。

5.5原始terminal、profile.jsonl、CSV/JSON在reports/stage5_05_board/collected_20261018_014600/files/reports/stage5_05_board/；本地analysis在reports/stage5_05_local/analysis/。自然麦克风用户反馈为gui_microphone_final_v2/user_feedback.json，真实截图已放在reports/stage5_05_local/figures/并嵌入手册。

RC本轮重建日志直接提供reports/rc_build/的stdout/stderr、steps.json、ctest.xml、result.json；确切二进制SHA也在result.json。没有把重建8项Fake测试说成新的硬件闭环。历史全部Git Diff分别保留，RC核心104项变化数为0，新增内容是包装、文档及校验。
