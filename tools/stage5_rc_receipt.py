"""Write a post-delivery report without changing the frozen archive or RC files."""
from pathlib import Path
import json,hashlib,base64,difflib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/stage5_rc1_local';RC=ROOT/'releases/stage5-rc1'
def main():
 a=json.loads((OUT/'archive_result.json').read_text());r=json.loads((OUT/'final_delivery_receipt.json').read_text());v=json.loads((RC/'VERSION.json').read_text());assert a['sha256']==r['archive_sha256']
 assert all(r[k] for k in ['original_321_unchanged','four_historical_binaries_unchanged','accepted_final_v2_104_unchanged','RC_binaries_unchanged_after_packaging'])
 text=f'''# Stage 5 最终 RC 发布收尾报告

日期：2026-10-18。最终候选版本 **stage5-rc1**，工程交付检查通过，停止开发并等待用户审核；尚未切换主工程或演示默认入口。

## 版本冻结

当前目录不是Git仓库，真实Git查询退出128；没有可报告的分支/HEAD/Commit，也未创建Git Tag。采用独立源码快照，标识为：

`{v['source_snapshot_id']}`

104项源码/头文件/测试/CMake与5.5已验收final_v2完全一致。本轮核心源码变化0。SOURCE_MANIFEST.json记录逐文件大小/SHA，VERSION.json记录快照计算方法。未初始化虚构历史，未强制覆盖任何标记。

## 本轮检查与真实结果

| 检查 | 实际结果 |
|---|---|
| ARM64配置及全量构建 | rc0；2.003秒/155.584秒；日志36条不同Built target，含2项AUTOMOC辅助目标 |
| ARM64 CTest | 8/8、失败0、跳过0；CTest real 6.12秒，外层6.511秒，每项30秒上限；Fake/纯逻辑/真实Qt offscreen+Fake子进程，不是新的硬件闭环 |
| 本地归档校验 | 260个安全普通文件，逐项SHA、路径安全检查、全新目录解压回放和verify.py均通过 |
| 板端补齐与校验 | 新增150项；110项原有且SHA相同，跳过写入；verify.py rc0、sha256sum rc0、bash -n rc0、非法启动模式按预期rc2，未启动模型 |
| 稳定工程保护 | 原稳定321项SHA/大小/mtime、4个历史程序、5.5冻结104项以及RC新编译主入口均核对通过 |
| 板端最终剩余空间 | {r['disk_free_after_bytes']:,}字节，约{r['disk_free_after_bytes']/1024**3:.3f}GiB，超过500MiB护栏 |
| 文档一致性 | A4手册238页逐页检查，26个源码片段、4449行代码、14处图像插入/11个去重媒体；正文及表格未变，61题保留 |

本轮预检未识别HyperX，保留首次预检失败日志；未重复真实麦克风/耳机/Qt窗口和长测。此前5.5用户确认的两类回答、视觉与Qt正常，及约1837.782秒121/121混合负载成果，均保留原始证据且与冻结源码对应。不能将本次CTest冒充新的硬件验收。

## 交付文件

| 内容 | 本地相对本报告的路径 |
|---|---|
| 完整RC归档 | [stage5-rc1.tgz](stage5-rc1.tgz) |
| 外层SHA | [stage5-rc1.tgz.sha256](stage5-rc1.tgz.sha256) |
| 精确文件校验清单 | [SHA256SUMS](../../releases/stage5-rc1/SHA256SUMS)、[PACKAGE_MANIFEST](../../releases/stage5-rc1/PACKAGE_MANIFEST.json) |
| 最终README及编译/CLI/Qt操作 | [项目README](../../README.md)、[包内README](../../releases/stage5-rc1/README.md) |
| Word手册 | [A4 DOCX](../../releases/stage5-rc1/docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx) |
| Markdown手册 | [完整手册](../../releases/stage5-rc1/docs/RK3576_STAGE5_ENGINEERING_MANUAL.md) |
| 模型/SDK/Runtime真实路径与398项指纹 | [依赖说明](../../releases/stage5-rc1/DEPENDENCIES.md)、[机器清单](../../releases/stage5-rc1/DEPENDENCIES.json) |
| 五阶段日志/CSV/JSON/Diff索引 | [证据索引](../../releases/stage5-rc1/EVIDENCE_INDEX.md) |
| RC完整文本包装Diff | [rc_full_text_changes.patch](rc_full_text_changes.patch)，含包内包装Diff及包外末次报告生成工具；核心零修改；Word排版变化SHA见document_QA |
| 逐节完整Git格式Diff | ../../releases/stage5-rc1/evidence/stage5_01～05/changes.patch |
| 历史完整证据 | ../../releases/stage5-rc1/evidence/RK3576_STAGE5_FINAL_REVIEW.tgz，4835成员、原日志/旧版本/失败实验均保留 |
| 安全升级/回滚及路径保护命令 | [操作方案](../../releases/stage5-rc1/DEPLOY_AND_ROLLBACK.md) |
| 本轮原始构建与CTest | board_build/、source_deploy/，包内reports/rc_build/ |
| 本轮上传/板端校验及真实退出码 | final_deploy/、board_final/、[末次回执](final_delivery_receipt.json) |

归档大小 **{a['bytes']:,}字节**，SHA256：

`{a['sha256']}`

板端RC位于 `{r['RC_directory']}`；归档位于 `{r['archive']}`。以普通cat权限创建，仅在既有隔离目录新增文件，没有覆盖旧源码、旧build、模型、SDK或配置。正式构建只从RC/source读取，运行仅选RC/build内GUI/CLI。历史实验源代码仅位于证据中；归档不复制大型模型/SDK/正式构建二进制，依赖现有绝对路径、Qt桌面及隔离工具，不能称为脱离环境的独立程序包。

SHA256SUMS覆盖258项内容和PACKAGE_MANIFEST自身；外层压缩包及末次回执放在包外避免循环引用。原252页Letter手册未改；RC副本纠正A4后重排238页并更新目录，Markdown字节保持原样。章节中的历史待验收状态是当时快照，用户已确认5.1～5.5，当前待审批的是RC升级。

## 保留风险与升级结论

4线程作为演示默认、2线程可回退。固定中文/英文暖态各n30 TTS平均下降30.42%/29.74%，CPU消耗明显增加，RTF仍>1。5.3仅CPU预处理下降24.67%；5.2改善提交阻塞，不是NPU推理同比加速。历史热限制活动和一次Camera序号间隙（后续64次未复现、根因未明）如实保留，本轮没有额外热专项或更长压力测试。

RGA未启用、未全链路Zero-copy、部分硬件/闭源SDK异常及更长运行未经验证；没有可信NPU利用率和声学时间戳，不把ALSA提交当人耳声学输出。同步SDK永久阻塞、无AEC/PTT/打断等局限继续保留。完整风险和后续定位方法见README及验收报告。

**建议：作为有限演示/工程实践的最终RC交付。暂不直接切换主工程。** 正式切换前接回HyperX，动态确认声卡，执行两问、Qt展示、停止/重新开始与资源释放的少量冒烟，并取得用户明确批准；无需重复30分钟长测。升级与回滚命令已经准备但未执行，原稳定版本始终保留，可回到原5.5 GUI或原稳定CLI。

本轮没有公开推送、安装系统软件、改温控/驱动/内核/设备树或切换入口。工作到此结束，等待用户审核。
'''
 (OUT/'FINAL_RELEASE_REPORT.md').write_text(text,encoding='utf-8')
 result={'release_candidate':'stage5-rc1','git_commit':None,'source_snapshot_id':v['source_snapshot_id'],'core_changes':0,'source_files':104,'ARM64_build_passed':True,'CTest':{'registered':8,'passed':8,'failed':0,'skipped':0,'real_seconds':6.12,'hardware_models_used':False},'safe_archive_roundtrip':True,'board_package_hashes_match':True,'word_A4_pages':238,'new_hardware_smoke_this_round':False,'HyperX_missing':True,'historical_5_5_hardware_acceptance_preserved':True,'original_stable_unchanged':True,'entry_switched':False,'public_push':False,'recommendation':'RC delivery ready; reconnect HyperX and perform brief smoke plus explicit user approval before entry switch','archive':a,'board_receipt':r}
 (OUT/'validation_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Add only the final report and checksums outside the immutable RC tree/archive.
 patch=(RC/'evidence/rc_changes.patch').read_text(encoding='utf-8')
 for p in [Path(__file__),OUT/'FINAL_RELEASE_REPORT.md']:
  name=p.resolve().relative_to(ROOT).as_posix();lines=p.read_text(encoding='utf-8').splitlines(keepends=True)
  patch+='diff --git a/'+name+' b/'+name+'\nnew file mode 100644\n'
  patch+=''.join(difflib.unified_diff([],lines,fromfile='/dev/null',tofile='b/'+name))
 (OUT/'rc_full_text_changes.patch').write_text(patch,encoding='utf-8',newline='\n')
 files={n:base64.b64encode((OUT/n).read_bytes()).decode() for n in ['FINAL_RELEASE_REPORT.md','validation_summary.json','stage5-rc1.tgz.sha256','rc_full_text_changes.patch']}
 payload='''from pathlib import Path
import base64,hashlib,json
r=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/reports/stage5_rc1_board')
assert r.resolve()==r
files='''+repr(files)+'''
assert all(not (r/n).exists() and not (r/n).is_symlink() for n in files)
for n,b in files.items():
 assert Path(n).name==n
 with (r/n).open('xb') as f:f.write(base64.b64decode(b))
print(json.dumps({'final_report_files':list(files),'all_written_new':True,'entry_switched':False}))
'''
 (OUT/'final_summary_payload.py').write_text(payload,encoding='utf-8')
 print('FINAL_RELEASE_REPORT_READY',a['sha256'])
if __name__=='__main__':main()
