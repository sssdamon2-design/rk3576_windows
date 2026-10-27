# 模型、SDK 与外部运行依赖

本包不含模型、SDK、系统库或构建产物。以下路径来自本轮板端只读查询；398项普通依赖文件逐文件大小和SHA在DEPENDENCIES.json。只读引用不会把外部模型纳入RC源码快照身份。

| 环境变量 | 实际配置路径 |
|---|---|
| STAGE5_ASR | `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17` |
| STAGE5_VAD | `/home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx` |
| STAGE5_QWEN | `/home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm` |
| STAGE5_KOKORO | `/home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1` |
| STAGE5_VLM | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm` |
| STAGE5_VISION | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn` |
| STAGE5_SHERPA | `/home/cat/projects/RK3576/rk3576_multimodal/../asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu` |
| STAGE5_RKLLM | `/home/cat/projects/RK3576/rk3576_multimodal/../rkllm_sdk` |
| STAGE5_RKNN_INCLUDE | `/home/cat/projects/RK3576/rk3576_multimodal/../rknn_test/include` |
| STAGE5_RKNN_LIBRARY | `/usr/lib/librknnrt.so` |

Debian GNU/Linux12 bookworm，Linux6.1.99-rk3576 aarch64，CMake3.25.1，GCC12.2，Qt5.15.8。sherpa1.13.8 / ORT1.28.2、RKLLM1.3.1、RKNPU驱动0.9.8来自已验收真实Runtime日志；未在本轮为查询版本重新加载模型。SO文件名不能单独当作Runtime API版本。模型制品以文件SHA为准，文件名不是训练来源证明。

## 关键制品指纹

| 实际文件 | 字节数 | SHA256 |
|---|---|---|
| `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx` | 239233841 | `c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51` |
| `/home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx` | 643854 | `9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6` |
| `/home/cat/projects/RK3576/rk3576_multimodal/../asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu/lib/libonnxruntime.so` | 34606912 | `cfc800d4438f15e8d9017521326776ca7117d8783cb847ccccc2fc61ac4d540f` |
| `/home/cat/projects/RK3576/rk3576_multimodal/../asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu/lib/libsherpa-onnx-c-api.so` | 4613032 | `11378e1aea169aecb59a4d41ca8da6f5ee4f3614c34a4b908dd78de7646a518d` |
| `/home/cat/projects/RK3576/rk3576_multimodal/../rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so` | 7674816 | `f25e9b099db08aaacd0a3ac62b4697d3951d6ae61ae41ea09f6702cfa89eb32c` |
| `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm` | 151406684 | `58afa4e10b5a6cdffb1822264d8e92df989cdcc84b3f93278c2b521cf348ea8e` |
| `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn` | 223089969 | `48b3cf2cbbc19c55e0ceb13afa039ff36f14a0ef93ae8edf52bfd9cf27081eeb` |
| `/home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm` | 1410933676 | `70b4b3c54221892cc403aa877612e0bfdc24abeda5e0011ee3a2e9a3c24e332c` |
| `/home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1/model.onnx` | 325631784 | `acc4adc175b9d9986106cd20060329673ad5a2e12ef3c557d2d3745b694f8b38` |
| `/home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1/voices.bin` | 53790720 | `e64a5a581d8c2a350d848f51c3121657cd83aa07ed6109172177345874a7244c` |
| `/usr/lib/librknnrt.so` | 7259064 | `73993ed4b440460825f21611731564503cc1d5a0c123746477da6cd574f34885` |

## 外部工具和桌面条件

启动器依赖隔离根目录tools/stage5_05_voice_run.py及其stage5_04_run.py、stage5_board_readonly_inventory.py等导入链；采用现有绝对路径，有完整版本副本在历史证据归档。DRM桌面持有者基线位于隔离reports/stage5_05_board/npu_primary_baseline.json；重新登录/重启后应运行既有只读inventory重新核查，不能强行结束桌面进程。现有cat用户X11/xcb与认证、Python3、bash、ALSA开发库、Qt Widgets/Test头文件均为环境依赖。构建与运行不用sudo；已有sudo -n fuser只查询资源持有者，不修改设备权限。

本轮/proc/asound/cards只显示板载es8388、HDMI和DP，无HyperX，真实麦克风与播放未重复测试。先前5.5用户听音确认及GUI截图保留。正式切换前必须接回耳机并执行两条冒烟。
