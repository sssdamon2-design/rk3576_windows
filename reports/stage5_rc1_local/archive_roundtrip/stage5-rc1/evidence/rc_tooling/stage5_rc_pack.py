"""Create final RC delivery and a real safe-archive roundtrip; no Git identity invented."""
from pathlib import Path,PurePosixPath
import hashlib,json,re,shutil,tarfile,subprocess,sys,difflib,ast
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[1]
RC=ROOT/'releases/stage5-rc1';REPORT=ROOT/'reports/stage5_rc1_local'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 assert not (RC/'PACKAGE_MANIFEST.json').exists(),'RC already packaged; never silently repack'
 version=json.loads((RC/'VERSION.json').read_text());source=json.loads((RC/'SOURCE_MANIFEST.json').read_text())
 assert all(sha(ROOT/x['file'])==x['sha256']==sha(RC/'source'/x['file']) for x in source)
 qa=json.loads((REPORT/'document_QA.json').read_text(encoding='utf-8'));assert qa['all_pages_inspected'] and qa['pages']==238
 build=json.loads((REPORT/'board_build/result.json').read_text());assert build['successful']
 tests=ET.parse(REPORT/'board_build/ctest.xml').getroot();assert tests.get('tests')=='8' and tests.get('failures')=='0'
 dest=RC/'evidence/rc_tooling';dest.mkdir()
 for p in sorted((ROOT/'tools').glob('stage5_rc_*.py')):
  ast.parse(p.read_text(encoding='utf-8'));shutil.copyfile(p,dest/p.name)
 for name in ['STAGE5_CODEX_TASK.md','README_STAGE5_FINAL.md']:
  shutil.copyfile(ROOT/name,RC/'evidence'/name)
 # Preserve raw failures and successful preflight/upload commands independently of the old evidence.
 for p in REPORT.iterdir():
  if p.is_dir() and (p.name.startswith('ssh_') or p.name=='source_deploy'):
   shutil.copytree(p,RC/'reports'/p.name)
 text=f'''# Stage 5 RC1 最终发布候选验收报告

本轮完成版本冻结与交付准备，核心推理代码零修改。适用于RK3576端侧多模态工程实践、面试和有限演示；不扩大为7×24商业系统验收。正式入口尚未切换。

## 版本与可追溯性

- 版本：stage5-rc1。
- 当前目录不是Git仓库，5条Git查询均真实退出128；分支、HEAD、未提交/未跟踪分类和Git Tag均不可取得。因此没有创建Commit或Git Tag，git_commit为null，未伪造提交。
- 可验证源码快照：`{version['source_snapshot_id']}`。
- 104项CMake/C++/头文件/测试与5.5已验收final_v2逐字节一致；逐项SHA见SOURCE_MANIFEST.json。上述标识由该清单规范JSON字节计算，算法见VERSION.json。
- 板端独立RC：`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/releases/stage5-rc1`。
- 历史五节完整Git格式Diff分别在evidence/stage5_01～05/changes.patch；原日志、CSV/JSON、历史源码和原252页手册完整保存在内层历史归档，4835成员已经逐项核验。新包装文本Diff见evidence/rc_changes.patch，二进制变化以SHA清单追溯。

## 本轮真实执行

| 项目 | 结果与口径 |
|---|---|
| ARM64 CMake配置 | rc=0，{build['steps'][0]['seconds']:.3f}秒，真实RKLLM/RKNN/sherpa与Qt5开启 |
| ARM64全量构建 | rc=0，{build['steps'][1]['seconds']:.3f}秒，最大并行3；未改模型、SDK或系统 |
| ARM64 CTest | 8/8、失败0，CTest自身real=6.12秒；外层含启动采样6.511秒；每项上限30秒 |
| 磁盘 | 构建后{build['disk_free_bytes']:,}字节，构建最低采样1,571,704,832字节，始终高于500MiB |
| 原工程保护 | 构建前后321项SHA/大小/mtime一致，4个历史已验收程序不变 |
| 依赖清单 | 实机只读记录398项模型、SDK、Runtime及音素资源的实际路径/大小/SHA |
| 手册 | 原生Word实际打开/更新目录/导出；A4共238页已逐页检查，26处完整代码抽取、4449行代码一致，14处图像/11个去重媒体文件未改变且可解码 |

8项CTest分别为：
'''
 purposes={'request_profile_tests':'请求ID、帧ID区分、steady事件及JSONL文本。','image_pipeline_tests':'CPU像素/stride/通道及有界Frame lease；Fake Camera。','async_pipeline_tests':'连续ASR推进、TEXT/VISION交替、满载、取消/过期、重启与回调异常；Fake服务。','asr_pipeline_tests':'音频队列关闭唤醒、排空、析构及服务/回调异常；Fake ASR。','audio_preprocessor_tests':'音频预处理纯逻辑。','llm_worker_tests':'Worker生命周期、任务执行与错误路径；Fake推理。','camera_service_tests':'Camera工作线程与停止/重启；Fake采集。','gui_session_tests':'真实Qt offscreen事件循环、开始/停止/重启/关闭及错误恢复；Fake子进程。'}
 for test in tests.findall('testcase'):text+=f"\n- `{test.get('name')}`：{purposes[test.get('name')]} 实测{test.get('time')}秒。"
 text+='''

上述测试没有调用真实模型或占用Camera/ALSA/NPU。原始配置、构建、CTest stdout/stderr、完整argv、真实退出码及XML在reports/rc_build/。

本轮只读预检发现HyperX不在/proc/asound/cards，首轮预检因此退出失败，保留原始Traceback；修正收集脚本后明确记录缺失而不绕过硬件检查。未运行RC真实语音/Qt窗口/耳机冒烟，不把CTest当作耳机验证。现有5.5实际麦克风、耳机、视觉描述、Qt及约30分钟121/121闭环成果完整继承，源码同一性已核验。正式切换前需接回HyperX，动态发现声卡，完成两条语音、界面和安全停止的短冒烟；无需重复长测。

## 手册一致性与修正

仅RC Word副本将历史Letter纸张修正为任务书A4；更新TOC造成252→238页重排。正文、表格、源码和嵌入图像保持一致，Markdown未改字节。原252页文件未修改。楷体/Times New Roman小四、1.5倍行距、两字符首行缩进、加粗标题及等宽代码已查；真实Qt截图沿用验收记录。61道面试问答按各节10/10/15/14/12保留，与相应阶段及最终源码讲解对应。历史章节中的“后续进入下一节”“user_acceptance_pending=true”是当时交付快照，本次用户已验收5.1～5.5，RC推广仍待批准。历史命令保留原路径，RC日常入口以本包README为准。

文档检查器首轮误把14处图片插入当14个ZIP媒体文件，实际Word去重为11个；修正检查器分别核验14处与11项SHA。5.4问答标题实际为“操作 N”，检查器改为匹配真实标题。没有为通过检查改写手册正文或历史结果。Markdown缺少的5.4引用图已按原SHA复制补齐。详细机器检查在reports/document_QA.json与visual_review.json。

## 性能与剩余风险

沿用原条件：5.3融合CPU预处理n12平均下降24.67%；5.4固定中文/英文暖态各n30合成均值下降30.42%/29.74%，CPU接近翻倍，RTF仍>1。5.2提交耗时下降是调度改善，不是NPU同比加速。原Qt约1837.782秒121/121固定输入混合请求完成，Camera29.9952FPS、XRUN0，不能据此宣称任意工况稳定或整体端到端加速30%。

默认Kokoro4线程，保留2线程回退。历史Linux热限制活动原样保留，本轮未做额外热专项/降频研究/长测，也未改温控。一次Camera driver sequence gap根因未明，后续64次视觉复测未复现；LatestFrameBuffer主动替换旧帧不等于驱动采集丢帧或消费者帧ID间隙，后续定位建议见README。

RGA未启用、未实现全链路Zero-copy；部分真实拔插、闭源SDK内部故障和更长持续运行未验证。无可信NPU利用率、功耗或真实声学时间戳；首次ALSA提交不是人耳听到时刻，首文本chunk不是精确Token TTFT。同步SDK永久阻塞仍是协作退出的边界，无AEC/PTT/语音打断。运行依赖现有板端模型/SDK、Qt桌面及隔离工具，不是脱离环境的独立运行包。

## 交付及升级判断

建议将stage5-rc1作为实践与演示用途的最终发布候选交付；不建议现在直接覆盖或切换主工程。接回HyperX完成短冒烟并获用户明确批准后，可按DEPLOY_AND_ROLLBACK.md进行版本入口选择；异常时恢复原5.5GUI或原稳定CLI，原目录与程序始终保留。

本包不含正式构建二进制/大型模型/SDK；板端RC/build为本轮独立编译产物，两个主入口SHA在reports/rc_build/result.json。历史证据内的旧源码和实验程序仅用于查阅，不进入RC正式构建/启动路径。SHA256SUMS与PACKAGE_MANIFEST.json区分源码/文档/证据；外层归档及其自身SHA、板端最后落盘和保护检查位于外部reports/stage5_rc1_local/archive_result.json及final_delivery_receipt.json，避免自身归档哈希的循环引用。打包前本报告不预填未来上传成功。

下一步仅为用户审核。未切换入口、未覆盖主工程、未公开推送、未安装软件或修改系统配置；停止后续开发。
'''
 (RC/'RC_ACCEPTANCE.md').write_text(text,encoding='utf-8')
 # Link checks cover current release entry documents; historical source appendices include literal examples.
 checked=[]
 for p in [ROOT/'README.md',*[RC/n for n in ['README.md','EVIDENCE_INDEX.md','DEPENDENCIES.md','DEPLOY_AND_ROLLBACK.md']]]:
  for n in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
   if n.startswith(('http:','https:','#')):continue
   target=(p.parent/n.split('#')[0]).resolve();assert target.exists(),(p,n);checked.append(str(target.relative_to(ROOT)))
 for p in (RC/'docs').glob('*.md'):
  fence=False
  for line in p.read_text(encoding='utf-8').splitlines():
   if line.startswith('```'):fence=not fence
   if not fence:
    for n in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',line):assert (p.parent/n).is_file(),(p,n)
 save(RC/'reports/release_consistency.json',{'at_UTC':datetime.now(timezone.utc).isoformat(),'source104_identical':True,'entry_document_links_checked':len(checked),'markdown_images_outside_code_exist':True,'core_changes':0,'no_git_commit_or_tag':True})
 # Git-compatible full added-text diff, not a fabricated Git commit or binary-evidence duplication.
 patch=[]
 selected=[ROOT/'README.md',*sorted((ROOT/'tools').glob('stage5_rc_*.py')),*[RC/n for n in ['README.md','DEPENDENCIES.md','DEPLOY_AND_ROLLBACK.md','EVIDENCE_INDEX.md','RC_ACCEPTANCE.md']]]
 selected.extend(sorted((RC/'tools').glob('*')))
 for p in selected:
  if p.suffix not in {'.py','.sh','.md'}:continue
  name=p.relative_to(ROOT).as_posix();lines=p.read_text(encoding='utf-8').splitlines(keepends=True)
  patch+=['diff --git a/'+name+' b/'+name+'\n','new file mode 100644\n']
  patch+=list(difflib.unified_diff([],lines,fromfile='/dev/null',tofile='b/'+name))
 (RC/'evidence/rc_changes.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
 save(RC/'evidence/rc_changes_manifest.json',{'core_changes':[],'text_added_as_packaging':[p.relative_to(ROOT).as_posix() for p in selected],'docx_change':'RC copy only: Letter to A4 and Word TOC page cache. Original unchanged. See document_QA hashes.','large_evidence_and_copied_source':'Exact files identified by SOURCE_MANIFEST and PACKAGE_MANIFEST; not embedded as duplicated binary patch blobs.'})
 rows=[{'file':p.relative_to(RC).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(RC.rglob('*')) if p.is_file()]
 assert not any('/__pycache__/' in x['file'] or x['file'].startswith('build/') for x in rows)
 save(RC/'PACKAGE_MANIFEST.json',rows)
 checks=rows+[{'file':'PACKAGE_MANIFEST.json','sha256':sha(RC/'PACKAGE_MANIFEST.json')}]
 (RC/'SHA256SUMS').write_text(''.join(x['sha256']+'  '+x['file']+'\n' for x in checks),encoding='utf-8',newline='\n')
 result=subprocess.run([sys.executable,'-I','-B',str(RC/'tools/verify.py')],capture_output=True,timeout=90)
 (REPORT/'verify_local.stdout.log').write_bytes(result.stdout);(REPORT/'verify_local.stderr.log').write_bytes(result.stderr);assert result.returncode==0
 archive=REPORT/'stage5-rc1.tgz';assert not archive.exists()
 files=sorted(p for p in RC.rglob('*') if p.is_file())
 with tarfile.open(archive,'x:gz',compresslevel=6) as bundle:
  for p in files:
   assert not p.is_symlink();bundle.add(p,arcname='stage5-rc1/'+p.relative_to(RC).as_posix(),recursive=False)
 unpack=REPORT/'archive_roundtrip';unpack.mkdir()
 with tarfile.open(archive,'r:gz') as bundle:
  members=bundle.getmembers();assert len(members)==len(files) and len({m.name for m in members})==len(members)
  for m in members:
   p=PurePosixPath(m.name);assert m.isfile() and not p.is_absolute() and '..' not in p.parts and '\\' not in m.name and ':' not in m.name and p.parts[0]=='stage5-rc1'
   target=unpack/m.name;assert target.resolve().is_relative_to(unpack);target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:shutil.copyfileobj(bundle.extractfile(m),f)
   assert sha(target)==sha(RC/p.relative_to('stage5-rc1'))
 result=subprocess.run([sys.executable,'-I','-B',str(unpack/'stage5-rc1/tools/verify.py')],capture_output=True,timeout=90)
 (REPORT/'verify_roundtrip.stdout.log').write_bytes(result.stdout);(REPORT/'verify_roundtrip.stderr.log').write_bytes(result.stderr);assert result.returncode==0
 info={'version':'stage5-rc1','archive':archive.relative_to(ROOT).as_posix(),'bytes':archive.stat().st_size,'sha256':sha(archive),'files':len(files),'uncompressed_bytes':sum(p.stat().st_size for p in files),'local_verify_exit_code':0,'safe_archive_roundtrip_verified':True,'roundtrip_verify_exit_code':0,'models_SDK_build_binaries_included':False,'historical_evidence_archive_preserved':True,'source_snapshot_id':version['source_snapshot_id']}
 save(REPORT/'archive_result.json',info);archive.with_suffix('.tgz.sha256').write_text(info['sha256']+'  '+archive.name+'\n',encoding='utf-8')
 print(json.dumps(info,indent=2))
if __name__=='__main__':main()
