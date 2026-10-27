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
