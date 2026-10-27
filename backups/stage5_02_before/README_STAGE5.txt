第五阶段正式工程化开发入口（2026-10-17）
- 任务书：STAGE5_CODEX_TASK.md（正式约束）
- 源码级计划：docs/stage5_plan.md
- 5.1审计、架构/线程/生命周期图、改动原因、测试和板端待验收命令：docs/stage5_01_architecture_audit.md
- 完整修改源码：docs/stage5_01_source_appendix.md
- 本机真实日志/补丁/hash：reports/stage5_01_local/
- 修改前源码快照：backups/stage5_01_before/
当前5.1已正式通过：隔离工程ARM64构建21/21，板端CTest两轮4/4，真实TEXT/VISION语音及用户听音确认通过；SIGINT/SIGTERM已先记录缺陷、最小修复并实机复验。原稳定工程321项指纹保持一致。
正式验收、真实数据、信号修复差异和剩余风险：docs/stage5_01_board_acceptance.md。
5.2尚未开始；5.2～5.5及最终Word/Markdown完整手册按任务书继续推进。

以下为此前功能集成补丁说明，保留历史验证边界：

RK3576 Stage5 集成补丁：ASR + IntentRouter + Qwen LLM / SmolVLM2 VLM + Kokoro TTS

目标：在原先已实机验证的 asr_llm_tts_smoke.cpp 上新增可选 VISION 分支，复用 Stage4 CameraService 和 RK3576VLMBackend。
修改文件：CMakeLists.txt, src/audio/asr_llm_tts_smoke.cpp。
不覆盖 Stage4 VLM、原有 Camera/LLM/TTS 实现。

旧语音参数完全兼容（7-10 argc）。新完整视觉模式：
  asr_llm_tts_smoke <capture> <asr_dir> <vad> <qwen.rkllm> <kokoro_dir> <playback> <seconds> <tts_threads> <sid> <smolvlm.rkllm> <vision.rknn> <camera_device>
示例：plugwh:3,0 实际应写 plughw:3,0；推荐测试录音 15 秒，一次只问一个问题。

配置：
  cmake -S . -B build/multimodal_full -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON
  cmake --build build/multimodal_full -j3 --target asr_llm_tts_smoke

本次 Stage5 的 VISION 路由暂采用英文固定提示 What do you see? Answer briefly.，以复用已验证成功的 RK3576 VLM；ASR 中文负责触发意图。
视觉分支在 ASR 回调线程里同步执行，约 1.8 s，会暂停处理下一句 ASR，作为功能验收版本；后续工程化优化可迁移至统一调度队列。

本地验证范围：修改后的 audio smoke C++ 语法检查（使用临时占位外部头文件），工程默认配置编译、CTEST 4/4。真实 AArch64 音频 SDK + RKNN + RKLLM 编译、模型共存内存、音频合成播放尚未板端验证。

注意：初次运行务必一问一答，观察 free -h / dmesg 是否 OOM。若同时加载 Qwen + SmolVLM2 + SenseVoice + Kokoro 导致内存不足，后续考虑按需加载 VLM。
