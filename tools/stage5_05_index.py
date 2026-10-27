"""Generate a final evidence index, separating unit, hardware and human evidence."""
from pathlib import Path
import argparse,json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--collection',type=Path,required=True);a=p.parse_args();local=ROOT/'reports/stage5_05_local'
 load=lambda p:json.loads(p.read_text(encoding='utf-8'));v=load(local/'validation_summary.json');data=load(local/'analysis/performance.json');base=a.collection/'files/reports/stage5_05_board'
 lines=['# 第五阶段最终结果与证据索引\n\n','5.1～5.4已由用户验收。5.5提交最终用户审核，隔离版未覆盖主稳定工程。最终手册为docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx与同名.md；报告为docs/stage5_05_final_acceptance.md。\n\n',f"工程机器检查：{sum(v['checks'].values())}/{len(v['checks'])}；all_checks_passed={v['all_checks_passed']}。每个check的具体证据见validation_summary.json。\n\n",'## 文件分类\n\n| 类型 | 真实位置 |\n|---|---|\n| 完整Git格式差异 | changes.patch，change_manifest.json |\n| 精确补丁还原 | patch_check.json，patch_roundtrip.json |\n| 源码版本与算法不变量 | source_invariants.json，final_v2_deployment_manifest.json |\n| 最终源码全文与解释 | docs/stage5_05_source_appendix.md，statement_notes.md，line_notes.md |\n| 请求与统计 | analysis/requests.csv，statistics.csv，performance.json |\n| 温度内存与RTF | analysis/stability_requests.csv，stability_resources.csv，stability_statistics.csv，stability.json |\n| 科学绘图与架构 | plots/*.png及.svg，figures/gui_*.png |\n| Word正文及逐页检查 | document_build.json，document_QA.json，manual_source_manifest.json |\n| 原始板端日志 | '+a.collection.as_posix()+'/files/reports/stage5_05_board/ |\n| 主机SSH命令与原始返回 | reports/stage5_05_board/ssh_*/remote.* |\n| 本地Fake测试 | portable_structured_text/，structured_text_validation.json；不等于ARM |\n\n','## 实机案例索引\n\n| Case | 退出码 | 时间秒 | 实际范围 |\n|---|---|---|---|\n']
 for name,c in data['cases'].items():
  result=c.get('result',{})
  if '/run_' in name:continue
  if 'returncode' in result:lines.append(f"| {name} | {result['returncode']} | {result.get('duration_seconds')} | {result.get('input_mode','见参数/环境')}；原始result.json及terminal.log |\n")
 lines+=['\nARM64注册8项均为Fake/确定性测试，真实SDK运行另列；人工HyperX和GUI反馈保存于gui_microphone_final_v2/user_feedback.json。最终Qt长测的父/子资源分开，首轮mic/paired后台采样缺失不补造。实际无效路径4项期待返回1并清理；其日志位于real_invalid_paths各子目录。\n\n','## 历史验收与保留局限\n\n5.1架构/生命周期报告，5.2异步/性能报告，5.3memory_pipeline与失败RGA，5.4performance_profiling与2/4线程n30均在docs/。阶段冻结源位于backups/及板端各stage5_XX_source*；不修改过去的失败记录或用户审核前状态。完整历史原始证据使用交付归档清单列出的canonical collections，模型/SDK继续原路径。\n\n','声学输出、精确token TTFT、可靠NPU利用率/功耗未测；未实现零拷贝、RGA生产、AEC/PTT和全真实拔插恢复；没有单进程60分钟保证。4线程默认适用已记录负载，2线程可配，Linux thermal限频确有观测，不能称无热代价。\n\n','## 最终归档\n\nRK3576_STAGE5_FINAL_REVIEW.tgz按final_archive_manifest.json逐文件SHA生成，包含全部源码/文档及五阶段canonical证据，排除模型、重复构建和内部QA PNG/PDF。final_archive.json记录外层SHA；final_delivery_receipt.json是归档完成后的外部收据，不能将自身收据递归放入同一个归档。板端仅保存于授权reports/stage5_05_board/final_acceptance，不解压覆盖、不升级稳定版本。\n']
 (local/'INDEX.md').write_text(''.join(lines),encoding='utf-8');print('INDEX_WRITTEN',len(data['cases']),'cases')
if __name__=='__main__':main()
