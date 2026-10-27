# 配置入口

> 本页列举的是文本 CLI 的 AppConfig。完整语音入口 asr_llm_tts_smoke 使用位置参数，见根目录 README_STAGE5.txt 及 docs/stage5_01_architecture_audit.md；当前尚无统一 JSON/YAML 总配置。旧文档中的“SDK/模型不在仓库”不代替板端实际路径核查。

当前只使用 CLI 参数，未引入 JSON/YAML 解析依赖。

- --device：默认 /dev/video11。
- --no-camera：禁用 Camera。
- --llm-model：文本模型路径。
- --vlm-model：视觉语言模型路径。
- --vision-model：独立视觉编码器路径（如真实 SDK 需要）。

Camera 请求格式在 main 的组装配置中固定为 3840×2160 NV12，实际采用驱动协商值。
SDK/模型不在仓库中。路径存在并不意味着当前可以推理。
未来统一配置文件可在 AppConfig/BackendConfig 边界接入，无需更改 Router 或采集线程。
