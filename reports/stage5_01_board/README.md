# 5.1 板端报告目录状态

当前：**5.1三阶段已完成，正式验收通过；5.2尚未开始。** 最新技术记录见 `docs/stage5_01_board_acceptance.md`，结构化结论为 `phase3_summary.json`。下文保留第一、二阶段历史记录，当前状态以本段和第三阶段证据为准。

第三阶段完整回收证据：`phase3_ssh_20261017_190524_321782/collected/reports/stage5_01_board/`。包含两轮ARM64 CTest（各4/4）、原版SIGINT/SIGTERM直接终止（-2/-15）、三个源码文件修复与重编、五次修复后成功运行（两项空闲信号、初始化中SIGTERM、自然双分支语音、推理中SIGTERM），以及真实设备/线程/fd/内存/磁盘/原工程指纹。所有七次硬件运行均无超时或强制kill。

用户明确确认自然语音两次回答和推理中SIGTERM那次回答均实际听到，原文保存在 `user_participation.json` 及板端run的确认文件。没有从TTS success推断本人听音。自然闭环VAD/ASR各2、LLM成功1、VISION成功1、TTS成功2、丢段0、XRUN0、PASS、退出0。原稳定工程321项指纹保持一致，模型和系统配置未改。

`phase3_evidence_manifest.json` 保存完整回收证据文件的SHA256；`phase3_ssh_*` 保存各实际SSH参数、载荷、原始stdout/stderr和返回码。一次本地GBK重打印错误没有影响SSH退出0或原始日志保存，已修正本地显示编码并保留记录。生产文件差异见 `reports/stage5_01_local/phase3_signal_fix/signal_fix.git.diff`，完整累计差异见 `changes.patch`。

完整构建记录见 `docs/stage5_01_phase2_build.md`，汇总为 `phase2_summary.json`。21个目标全部编译成功，17个可执行文件为ARM aarch64；编译、监督器与日志回收退出0。唯一警告是备用unavailable函数未使用，无编译错误。本轮没有源码修复。

本地完整执行目录为 `phase2_20261017_184503_994558/`，包含每一步命令、实际远端载荷、stdout/stderr和退出码；`collected/`保存回收的配置/编译/ldd/空间采样/原工程指纹/退出码文件。板端同名编译和监督日志保留在隔离目录的reports内。

`readonly_*`保存各次真实只读stdout/stderr和退出码，含一次fuser参数错误及修正后的复查；最终完整预检为`readonly_full_20261017_182718_018778/`，汇总为`readonly_preflight_summary.json`。不得把Windows测试日志或合成fixture放入这里冒充实机记录。

第二阶段结束时尚未运行CTest或硬件程序；后续第三阶段授权与执行已完成，见上文。原工程321项指纹与第一阶段基线一致，没有覆盖原`build/stage5_full`、模型或系统配置。只读历史记录中的“隔离目录不存在”是当时事实，第二阶段已排他创建该目录，不能再次执行首次部署命令。

首次源码审查发现完整语音入口缺少协作信号处理；第三阶段已记录真实缺陷、最小修复并完成SIGINT/SIGTERM实机复验。测试通过PID发送SIGINT，物理键盘Ctrl+C未另外操作，不将两者混写。
