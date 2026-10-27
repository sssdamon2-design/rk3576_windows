# Stage 5 RC1 最终发布候选验收报告

本轮完成版本冻结与交付准备，核心推理代码零修改。适用于RK3576端侧多模态工程实践、面试和有限演示；不扩大为7×24商业系统验收。正式入口尚未切换。

## 版本与可追溯性

- 版本：stage5-rc1。
- 当前目录不是Git仓库，5条Git查询均真实退出128；分支、HEAD、未提交/未跟踪分类和Git Tag均不可取得。因此没有创建Commit或Git Tag，git_commit为null，未伪造提交。
- 可验证源码快照：`sha256:2b19cd571f87e083b506da586aa1f1a772cd76ed253b1fe848337ff524fe6f87`。
- 104项CMake/C++/头文件/测试与5.5已验收final_v2逐字节一致；逐项SHA见SOURCE_MANIFEST.json。上述标识由该清单规范JSON字节计算，算法见VERSION.json。
- 板端独立RC：`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/releases/stage5-rc1`。
- 历史五节完整Git格式Diff分别在evidence/stage5_01～05/changes.patch；原日志、CSV/JSON、历史源码和原252页手册完整保存在内层历史归档，4835成员已经逐项核验。新包装文本Diff见evidence/rc_changes.patch，二进制变化以SHA清单追溯。

## 本轮真实执行

| 项目 | 结果与口径 |
|---|---|
| ARM64 CMake配置 | rc=0，2.003秒，真实RKLLM/RKNN/sherpa与Qt5开启 |
| ARM64全量构建 | rc=0，155.584秒，最大并行3；未改模型、SDK或系统 |
| ARM64 CTest | 8/8、失败0，CTest自身real=6.12秒；外层含启动采样6.511秒；每项上限30秒 |
| 磁盘 | 构建后1,571,917,824字节，构建最低采样1,571,704,832字节，始终高于500MiB |
| 原工程保护 | 构建前后321项SHA/大小/mtime一致，4个历史已验收程序不变 |
| 依赖清单 | 实机只读记录398项模型、SDK、Runtime及音素资源的实际路径/大小/SHA |
| 手册 | 原生Word实际打开/更新目录/导出；A4共238页已逐页检查，26处完整代码抽取、4449行代码一致，14处图像/11个去重媒体文件未改变且可解码 |

8项CTest分别为：

- `request_profile_tests`：请求ID、帧ID区分、steady事件及JSONL文本。 实测0.0263333秒。
- `image_pipeline_tests`：CPU像素/stride/通道及有界Frame lease；Fake Camera。 实测0.596988秒。
- `async_pipeline_tests`：连续ASR推进、TEXT/VISION交替、满载、取消/过期、重启与回调异常；Fake服务。 实测0.0368343秒。
- `asr_pipeline_tests`：音频队列关闭唤醒、排空、析构及服务/回调异常；Fake ASR。 实测0.0147641秒。
- `audio_preprocessor_tests`：音频预处理纯逻辑。 实测0.00943169秒。
- `llm_worker_tests`：Worker生命周期、任务执行与错误路径；Fake推理。 实测0.0102219秒。
- `camera_service_tests`：Camera工作线程与停止/重启；Fake采集。 实测0.225106秒。
- `gui_session_tests`：真实Qt offscreen事件循环、开始/停止/重启/关闭及错误恢复；Fake子进程。 实测5.18841秒。

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
