# RK3576 第三阶段 · ASR \+ RKLLM \+ Kokoro \+ ALSA 源码级工程技术手册

# RK3576 第三阶段 · ASR \+ RKLLM \+ Kokoro \+ ALSA 源码级工程技术手册

**完整语音交互 PASS 基线 \| Stage 3\.1—3\.5 \| 2026\-10\-16**

**适用：Linux、嵌入式系统、C\+\+17、端侧 AI、NPU Runtime、AI Infra 实习与校招面试。** 本手册的主要材料来自用户实际上传 `rk3576_multimodal_stage3_pass_20261016_1124.tar(1).gz` 的全部相关真实代码，以及对话中留存的 RK3576 终端日志。**不重构、不替换原代码作为历史证据**。若历史命令或日志缺失，将明确标识建议复现，而不会把现在推导的命令冒充当时执行过的命令。

## 阅读地图与证据标记

- **【实际执行 / 实测】**：对话中用户贴出的原始终端命令或返回；原始数值、型号、时间保留。长日志若节选则说明节选。

- **【源码可确认】**：来自用户上传的最终 PASS 压缩包。先前草稿没有保留时，不声称是早期原始实现。

- **【历史测试摘要】**：早期3\.2/3\.3/3\.4验收的关键数值能从本项目连续对话获取，但部分完整命令/日志未保留；不可混作同一轮精确可配对样本。

- **【建议复现操作】**：依据归档源码中的 argv 参数与 CMake 目标写出的命令；语法可从源码验证，但不宣称当时逐字执行过。

- **【典型输出示例，非当时实测】**：正常或异常情况下的教学示例，不能算实绩。

- **【尚未验证】**：缺乏压测或硬件证据的可能改进。不能写为“已实现”。

**全文组织**：第一篇目标与架构；第二篇按实际工程学习先后逐操作、逐命令讲解；第三篇 C\+\+/SDK/驱动底层机制；第四篇性能与指标口径；第五篇故障诊断；第六篇26道高频面试题；第七篇简历与后续任务；第八篇重现实验；第九篇最终真实源码原文 \+ 物理行号精读。阅读 Word 时用导航窗格与自动目录；Markdown 可通过 VSCode 的 Outline 按层级检索。

## 项目目标及可证最终验收标准

**前提**：RK3576 LubanCat\-3 Debian 12 已实现 USB 麦克风 PCM 采集、Silero VAD、SenseVoice INT8 ASR、`LLMEngine + RKLLMBackend + LLMWorker` Qwen2\.5\-1\.5B W4A16 RKNPU 推理。第三阶段核心并不是重做基础 ASR，而是把“中文文本→本地声波”形成 C\+\+ 模块并接通原链路。

**终态：**真实人声 → ALSA Capture → VAD → `AudioBufferQueue` → `ASRWorker`/SenseVoice → `IntentRouter` → `LLMWorker`/RKLLM → `result.text` → `TTSWorker`/Kokoro → float32 PCM → `AlsaPlaybackService` → S16\_LE ALSA Playback → USB 耳机。必须同时满足模型确实推理、音频队列无丢弃、LLM/TTS任务计数闭合、ALSA无XRUN、Worker安全退出，**终端PASS \+ 用户实听完整播报**。一次 PASS 不等于已经达到量产级低延迟或长时间可靠性。

## 重要历史真实性边界

当前压缩包排除了 `build/`、`.git/`、`*.onnx`、`*.rkllm`、`*.wav`、`*.pcm`。它证明当前 C\+\+、CMake 和头文件内容，但**没有包含实际模型权重、共享库、早期草稿和每次历史运行全部日志**。若记录了 `nano` 编辑，仅表示过程中的文件创建/保存历史可追溯；不能虚构 nano 的屏幕回显。**第三阶段 3\.5 的真正 PASS 程序长1077行**，不可用早期发出的不同长度草稿冒充最终归档源码。`asr_llm_smoke.cpp` 长403行，属于先前阶段复用代码。

## 源码取证清单：SHA\-256 与真实行数

|归档最终版本|行数|SHA\-256 前16位|
|---|---|---|
|include/audio/tts\_service\.h|63|f4a149ddf6f90567|
|src/audio/tts\_service\.cpp|313|b43677e31f8b53dd|
|src/audio/tts\_smoke\.cpp|182|63561803c786cd36|
|include/audio/alsa\_playback\_service\.h|60|d51e6deb7a316fc0|
|src/audio/alsa\_playback\_service\.cpp|399|777ca61cc29489ec|
|src/audio/tts\_playback\_smoke\.cpp|192|55553c6370de604b|
|include/audio/tts\_worker\.h|130|5a78c0fbfe888b19|
|src/audio/tts\_worker\.cpp|301|590e9676d023d228|
|src/audio/tts\_worker\_smoke\.cpp|231|b0a6c515ad88cd7d|
|src/audio/tts\_worker\_queue\_smoke\.cpp|245|9bfd8faba054eb20|
|src/audio/asr\_llm\_smoke\.cpp|403|7f1dd9be3dd88142|
|src/audio/asr\_llm\_tts\_smoke\.cpp|1077|63d4ffc5fbd52aa0|
|CMakeLists\.txt|309|693a117f29b226cb|
|include/ai/llm\_worker\.h|82|10a03767c8c3c3bf|
|src/ai/llm\_worker\.cpp|204|685fe657c9ac1a6b|
|include/audio/asr\_pipeline\.h|163|4e40ad4170c560cd|
|include/audio/asr\_service\.h|53|53cd22464e052cf9|
|include/audio/vad\_audio\_worker\.h|55|08ce86b0d0197bb0|
|include/router/intent\_router\.h|15|4bd47b86d95d2da9|
|src/router/intent\_router\.cpp|74|791099a42b0086cf|

**来源说明**：上述 SHA\-256 直接依据用户上传的 stage3\_pass 压缩包解压后的文件计算。源文件不重新生成、不修改，不包含模型权重/SDK 库。文中任何「建议复现」命令与历史实测原日志单独标注，不把不同测试时刻的输出强行归到同一命令。

# 第一篇 · 整体架构、运行环境、数据流与职责

## 1\. RK3576 硬件和软件分层

|层级|本阶段真实组件|职责与边界|
|---|---|---|
|硬件|RK3576 CPU / NPU、USB HyperX Cloud III 耳机麦克风、eMMC|CPU执行 ASR/TTS，RKNPU执行 Qwen；USB耳机负责真实声学出入|
|Linux内核|6\.1\.99\-rk3576，ALSA snd\-pcm / USB音频驱动、RKNPU内核驱动|提供设备访问、DMA和内核资源；当前不是自研这些内核驱动|
|用户态设备库|ALSA 1\.2\.8 / libasound|`snd_pcm_open/set_params/writei/drain/close` 管理 PCM|
|模型运行库|sherpa\-onnx v1\.13\.8 aarch64 CPU|Silero VAD、SenseVoice、Kokoro 的推理 C API 和解码器前端|
|NPU用户态 Runtime|librkllmrt\.so v1\.3\.1 / RKNPU driver 0\.9\.8|装载 RKLLM 文件、Qwen W4A16 文本推理、Tokens回调|
|模块封装层|`ASRService`, `LLMEngine`, `TTSService`, `AlsaPlaybackService`|资源所有权、错误处理、接口抽象|
|调度层|`VadAudioWorker`, `ASRWorker`, `LLMWorker`, `TTSWorker`|线程、队列、异步任务、背压、完成通知|
|业务入口|`asr_llm_tts_smoke.cpp`|编排模型加载、意图路由、整体统计、验收PASS/FAIL|

**实测环境**：LubanCat\-3；Debian GNU/Linux 12 \(bookworm\) / aarch64；内核 Linux 6\.1\.99\-rk3576 \#8；CPU RAM `3.8GiB`；无Swap；根分区 `/dev/mmcblk0p3` 29G、已用27G、可用1\.1G。ALSA卡号曾是 `card3 device0`，最终实机 PASS 用 `plughw:1,0`，卡号不可硬编码为永久恒定身份。USB 耳机品牌为 HyperX Cloud III。

## 2\. CPU/NPU/音频的数据链与运行线程

```Plaintext
flowchart TD
  USB[HyperX USB麦克风] --> ALSAC[libasound: Capture PCM]
  ALSAC --> VAD[VadAudioWorker / Silero VAD CPU]
  VAD --> Q[AudioBufferQueue: 有界缓冲]
  Q --> ASR[ASRWorker / SenseVoice INT8 CPU]
  ASR --> ROUTER[IntentRouter: RequestType::Text]
  ROUTER --> LLQ[LLMWorker: 有界FIFO]
  LLQ --> ENGINE[LLMEngine / RKLLMBackend]
  ENGINE --> RK[RKLLM Runtime / RKNPU驱动 / NPU]
  RK --> DONE[LLM Done / result.text]
  DONE --> TTQ[TTSWorker: 有界FIFO]
  TTQ --> KOKORO[TTSService / Kokoro v1.1 CPU]
  KOKORO --> FPCM[TTSAudio vector float32 24kHz mono]
  FPCM --> CONV[AlsaPlaybackService: float32转S16_LE]
  CONV --> PLAY[libasound: PCM writei / drain]
  PLAY --> H[HyperX耳机完整播报]
```

主线程创建模型服务、两个Worker并开启VAD/ASR两个音频线程。VAD线程产生完整语音片段；ASR线程消费音频队列，文本回调送入 LLMWorker；LLMWorker自己的线程执行 NPU 推理，Done 回调提交 TTSWorker；TTSWorker线程先完整合成PCM，再阻塞播放，最后调用Done回调。**回调实际运行在相关Worker线程，而非神秘“自动切回主线程”。** 统计通过 `state_mutex`、完成等待通过 `condition_variable`，打印经 `print_mutex` 同步。

## 3\. 字符串、PCM缓冲和所有权（实际拷贝次数）

- ASR返回 `std::string` UTF\-8 文本；LLM请求通过 `std::move` 进入 `Task`（移动表达式不保证绝对零拷贝）。

- `InferenceResult.text` 在 LLM 回调中被交给 `TTSWorker::submit`，线程池队列保存任务和回调。

- `SherpaOnnxOfflineTtsGenerateWithConfig` 返回 SDK拥有的 `SherpaOnnxGeneratedAudio`；`TTSService` 用带自定义删除器的 `unique_ptr` 包装，在 `output.samples.assign(...)` 拷贝后销毁 SDK 音频。

- `TTSAudio.samples` 是 `vector<float>`；`AlsaPlaybackService` 再分配 `vector<int16_t>`，逐样本进行 finite 检查、\[\-1,1\] 限幅、整数舍入，然后 `snd_pcm_writei()` 发送。**本次音频链路不是DMA\-BUF零拷贝。**

- `TTSWorker` 持有 `TTSService&` 和 `AlsaPlaybackService&` 非拥有引用，所以必须先建立两个Service，再建Worker；回收时反过来，先停止/join Worker，再close/shutdown Service。

## 4\. 模型、SDK和声学参数

|模块|实际值|原理与影响|
|---|---|---|
|SenseVoice|zh/en/ja/ko/yue INT8；输入16kHz mono|CPU离线识别；ASR RTF≈0\.469|
|RKLLM|Qwen2\.5\-1\.5B\-Instruct RK3576 W4A16|RKLLM 1\.3\.1、NPU 2核；上下文上限日志4096|
|Kokoro|kokoro\-multi\-lang\-v1\_1；模型311MB、voices约52MB|CPU ONNX；内部多语言词典、espeak前端|
|中文音色|`sid=17`，历史测试 zf\_024|103 speakers，索引从0开始，选17|
|TTS音频|24000 samples/s、单声道 float32|TTS生成自然数秒声音；转换为S16\_LE向ALSA写入|
|ALSA PCM|`plughw:1,0`，S16\_LE、interleaved、1声道|libasound可按配置协商软转换；不是设备树固定编号|
|Buffer/period|12000/3000帧，start\_threshold=6000帧|24kHz下对应500ms/125ms；先积累两period再自动启动|

**用户态到内核态调用边界**：`AlsaPlaybackService::open/play/close()`调用 **libasound**，后者与 Linux内核 ALSA PCM 驱动交互；不需要在本阶段自己调用 open/read/write 直接操作PCM字符设备。`RKLLMBackend`调用 `librkllmrt.so`，Runtime再与NPU内核驱动通信。**不能把SDK集成写成“开发了RKNPU驱动/UMD”。**

## 5\. 结束时序与线程安全因果链

```Plaintext
sequenceDiagram
 participant MAIN as 主线程
 participant VA as VAD录音线程
 participant ASR as ASRWorker
 participant LW as LLMWorker
 participant TW as TTSWorker
 participant ALSA as ALSA设备
 MAIN->>LW: start()
 MAIN->>TW: start()
 MAIN->>ASR: start()
 MAIN->>VA: start()
 VA->>ASR: AudioBufferQueue语音片段
 ASR->>LW: submit(request_id,prompt)
 LW->>TW: on_done: submit(request_id,result.text)
 TW->>TW: Kokoro.synthesize()
 TW->>ALSA: writei() + drain()
 ALSA-->>TW: XRUN=0
 TW-->>MAIN: on_done,completed++,notify_all()
 MAIN->>VA: join()
 MAIN->>ASR: join()
 MAIN->>LW: wait LLM Done; requestStop(); join()
 MAIN->>TW: wait TTS Done; requestStop(); join()
 MAIN->>ALSA: close(); tts.shutdown()
```

**不能颠倒**：ASRWorker全部退出才不会有新的LLM提交；LLM Done的回调必须**先提交TTS任务、后更新 LLM完成计数**；只有所有LLM Done完成并join之后，主线程才能确信TTS提交数不再增加，进而等待全部TTS完成。Worker工作线程join之后，再关闭其引用的Service。反过来可能有悬垂捕获、队列取消、双重释放或USB声音截断。

# 第二篇 · 逐项操作及命令级复现

## 操作 1：识别第三阶段最终1077行源码与文件边界

### 1\. 为什么执行：上一步问题、假设与本步目标

为了避免把早期草稿当成最终验收程序，先验证文件真实存在、前后完整和行数。这一步处于复盘取证，不证明运行成功。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
wc -l src/audio/asr_llm_tts_smoke.cpp
head -n 10 src/audio/asr_llm_tts_smoke.cpp
tail -n 15 src/audio/asr_llm_tts_smoke.cpp
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：Shell 内建命令，切换当前目录。

- **`$HOME`**：展开当前用户主目录 /home/cat；双引号防止路径被分词。

- **`wc -l`**：按换行符统计文件物理行数，而非语句数。

- **`head -n 10`**：读取开头10行，核对头文件引用；\-n指定行数。

- **`tail -n 15`**：读取末尾15行，核对 PASS/FAIL 和 main 收尾。

- **`src/audio/asr_llm_tts_smoke.cpp`**：相对工程根目录的第三阶段联调源文件。

### 4\. 终端实际返回/未保存事实

**【真实输出节选】**

```Plaintext
1077 src/audio/asr_llm_tts_smoke.cpp
#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"
#include "audio/tts_worker.h
...（中间内容未在这一段 head/tail 展示）
        tts_failed == 0 &&
        tts_rejected == 0 &&
        tts_empty == 0;
    std::cout << (passed ? "PASS\n" : "FAIL\n");
    return passed ? 0 : 1;
}
```

### 5\. 输出内容逐行/逐字段解释

- 1077 表示最后通过验收的完整文件长度，不是早期434行版本。

- 头文件将 ASR、LLM、TTS、ALSA接口接到同一入口。

- passed ? 0 : 1 是三元运算符；零退出码表成功、非零表失败。

### 6\. 成功与失败判断、退出状态

文件存在并首尾完整、wc为1077。通常命令退出码为0；缺文件则报 No such file or directory，不能仅用文件长度判断程序正确。

### 7\. 环境影响、权限、风险及后续衔接

只读；cd只影响当前Shell；不修改驱动或生成文件。下一步检查模型构建开关。

### 8\. 最终工程结论

明确第三阶段最终代码是真实1077行、并非由手册重新编写。

### 本操作面试问题与回答

**问：编译、链接、实机PASS三者如何区分？**

答：编译验证语法和静态类型；链接验证外部符号/库；实机PASS才证明模型与声卡真实执行。三者不能替代。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 2：确认 CMake 的 ENABLE\_SHERPA\_ASR 和 BUILD\_WITH\_RKLLM

### 1\. 为什么执行：上一步问题、假设与本步目标

真实第一次构建提示目标不存在；需要区分构建选项未启用还是遗漏 add\_executable。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
grep -n "add_executable(asr_llm_tts_smoke" CMakeLists.txt
grep -E '^(ENABLE_SHERPA_ASR|BUILD_WITH_RKLLM):BOOL=' build/asr_llm/CMakeCache.txt
```

### 3\. 命令本体和参数逐项解析

- **`grep`**：按模式搜索文本。

- **`-n`**：输出匹配的物理行号。

- **`add_executable(asr_llm_tts_smoke`**：在 CMake 文件中搜索确切目标。

- **`-E`**：扩展正则支持 \| 交替。

- **`^`**：匹配行首。

- **`(X|Y)`**：分组二选一搜索两项配置，单引号避免Shell误解释竖线。

- **`CMakeCache.txt`**：保存当前build目录实际缓存的BOOL开关，不能仅看CMake默认值。

### 4\. 终端实际返回/未保存事实

**【真实输出：第一条没有输出，第二条有两行】**

```Plaintext
BUILD_WITH_RKLLM:BOOL=ON
ENABLE_SHERPA_ASR:BOOL=ON
```

### 5\. 输出内容逐行/逐字段解释

- 第一条无输出：当时新目标尚未加入CMakeLists。

- 两个 BOOL=ON 表明 RKLLM 和音频构建条件均已启用。

- 第一条 grep 无匹配可能返回退出码1，这是搜索未找到，不是Shell崩溃。

### 6\. 成功与失败判断、退出状态

CMakeCache两个开关ON且grep目标缺失，定位目标定义遗漏；grep的空输出不能认定文件不存在。

### 7\. 环境影响、权限、风险及后续衔接

只读，不修改CMake。后续需要备份并追加add\_executable，非root。

### 8\. 最终工程结论

构建失败是目标遗漏，不是C\+\+源码编译失败。

### 本操作面试问题与回答

**问：新建 cpp 后为何CMake不自动出现目标？**

答：CMake必须通过add\_executable或add\_library明确加入构建图，源文件存在本身不会自动产生同名可执行目标。

## 操作 3：3\.1 模型选择：Kokoro与MeloTTS差别及音色文件

### 1\. 为什么执行：上一步问题、假设与本步目标

历史上比较过MeloTTS zh\_en与Kokoro，用户认为Kokoro zf\_024更合适；须确认模型文件和英文/中文前端资源存在。原始模型下载和比较命令未完整保存。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作，非原始逐字历史命令】**

```Bash
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
ls -lh "$KOKORO_MODEL/model.onnx" "$KOKORO_MODEL/voices.bin" "$KOKORO_MODEL/tokens.txt"
ls -ld "$KOKORO_MODEL/espeak-ng-data"
```

### 3\. 命令本体和参数逐项解析

- **`KOKORO_MODEL=`**：定义本Shell变量；=旁不可加空格。

- **`$HOME`**：/home/cat用户家目录；引号保护路径完整。

- **`ls`**：列出文件或目录。

- **`-l`**：长列表含权限、大小、修改时间。

- **`-h`**：把字节数以便于阅读的KiB/MiB展示。

- **`-d`**：打印目录本身而非递归展开。

- **`model.onnx`**：Kokoro ONNX模型。

- **`voices.bin`**：音色相关二进制数据。

- **`tokens.txt`**：模型符号/标记表。

- **`espeak-ng-data`**：Kokoro依赖的语言前端数据目录。

### 4\. 终端实际返回/未保存事实

**【历史确认参数；本条 ls 原始返回未保留】**

```Plaintext
历史验收：Kokoro多语言v1.1，model.onnx约311 MB、voices.bin约52 MB；103个speaker，zf_024对应sid=17。
本条ls的精确行级权限、大小、时间戳未保存。
```

### 5\. 输出内容逐行/逐字段解释

- 文件存在仅是CreateOfflineTts的前置条件，不能证明推理成功。

- 103 speakers意味着有效索引0—102，17属于合法范围。

- 后端CPU合成耗时长，最终选择是用户音色质量与实机约束的取舍。

### 6\. 成功与失败判断、退出状态

文件及目录可读，再通过后续TTSService初始化与合成验证。ls路径不存在通常报 cannot access，退出码非0。

### 7\. 环境影响、权限、风险及后续衔接

只读，无模型加载、不占音频设备；不需要root。

### 8\. 最终工程结论

最终选Kokoro v1\.1中文女声sid17；MeloTTS为保留兼容分支，不是最终播报后端。

### 本操作面试问题与回答

**问：为什么speaker不能简单设置成103？**

答：合法speaker ID按0开始，NumSpeakers返回103意味着范围0\.\.102；源代码对ID越界进行Destroy并报告失败。

## 操作 4：3\.2 使用 nano 创建 TTSService 头文件与RAII接口

### 1\. 为什么执行：上一步问题、假设与本步目标

必须为SDK TTS裸指针建立类型安全、确定销毁的C\+\+封装，同时把生成float32 PCM放入具有所有权的vector。真实文件保留，初次编辑器具体按键过程未保存。

### 2\. 完整命令（原始 / 建议复现标注）

**【历史操作可确认；原始 nano 回显未记录】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano include/audio/tts_service.h
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：切换到工程根目录，定位include相对路径。

- **`nano`**：终端文本编辑器；Ctrl\+O回车保存、Ctrl\+X退出。

- **`include/audio/tts_service.h`**：公共头文件，对外暴露TTSAudio/TTSService接口。

- **`#pragma once`**：头文件内的一次包含保护，不是Shell命令。

### 4\. 终端实际返回/未保存事实

**【源码确认；无历史编辑器标准输出】**

```Plaintext
归档确认：include/audio/tts_service.h 存在；含 TTSAudio.samples(vector<float>)、sample_rate、synthesis_ms、initialize、synthesize、shutdown。
```

### 5\. 输出内容逐行/逐字段解释

- vector拥有单声道合成采样，避免引用SDK销毁后的内存。

- TTSService禁止复制/移动以规避SDK句柄被复制导致double free。

- 析构调用shutdown，属于RAII生命周期管理。

### 6\. 成功与失败判断、退出状态

成功保存后文件存在并在最终CMake中编译通过；单独进入nano不等于已正确编码。典型错误是头文件路径/Sherpa SDK include错误。

### 7\. 环境影响、权限、风险及后续衔接

编辑将改写工程文件，可能覆盖旧内容，建议先Git或备份；不改驱动、不需root。

### 8\. 最终工程结论

业务层使用稳定C\+\+接口，SDK所有权收敛于TTSService。

### 本操作面试问题与回答

**问：为什么SDK指针不能被两个TTSService直接共享？**

答：如果两对象析构时各自调用同一个Destroy将重复释放；需显式设计共享所有权或像当前这样禁止拷贝。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `include/audio/tts_service.h`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 5：3\.2 TTSService实现：Sherpa C API合成与资源自动释放

### 1\. 为什么执行：上一步问题、假设与本步目标

实现Kokoro与先前MeloTTS两条配置分支，并对输出PCM进行独立复制，确保后续Worker异步播音期间采样数据仍然有效。

### 2\. 完整命令（原始 / 建议复现标注）

**【源码可确认；编辑器原始回显未保存】**

```Bash
nano src/audio/tts_service.cpp
```

### 3\. 命令本体和参数逐项解析

- **`nano`**：编辑C\+\+源码，保存后需要重新构建。

- **`src/audio/tts_service.cpp`**：SDK Create/Generate/Destroy实现，位于工程src/audio。

- **`num_threads`**：初始化参数允许1至8，最终实测2。

- **`speaker_id`**：Kokoro使用17，生成配置gen\.sid保存此值。

### 4\. 终端实际返回/未保存事实

**【归档源码事实】**

```Plaintext
初始化：SherpaOnnxCreateOfflineTts(&cfg)；声音列表：SherpaOnnxOfflineTtsNumSpeakers；合成：SherpaOnnxOfflineTtsGenerateWithConfig；释放：SherpaOnnxDestroyOfflineTtsGeneratedAudio、SherpaOnnxDestroyOfflineTts。
```

### 5\. 输出内容逐行/逐字段解释

- 创建模型前必须保证cfg内c\_str\(\)的字符串存活至Create返回。

- unique\_ptr\<const GeneratedAudio, AudioDeleter\>把SDK特定Destroy封装为自定义删除器。

- output\.samples\.assign复制SDK内部PCM到自有vector，产生一次真实的CPU内存拷贝。

- provider=cpu说明Kokoro并未走RKLLM/RKNPU。

### 6\. 成功与失败判断、退出状态

后续tts\_smoke真正产生非空PCM、正确采样率与PASS，而不仅是Create返回非空。缺模型文件/音色非法会返回false和error。

### 7\. 环境影响、权限、风险及后续衔接

修改源码，不直接访问硬件；编译和运行会额外占CPU/内存，非root。

### 8\. 最终工程结论

TTSService管理SDK生命周期、返回自有PCM，使音频播报与模型SDK接口解耦。

### 本操作面试问题与回答

**问：C API指针配unique\_ptr有什么特殊之处？**

答：不能调用delete释放SDK对象，必须把SDK规定的Destroy函数作为unique\_ptr第二个模板参数中的删除器，作用域退出自动调用。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_service.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 6：3\.2：编写独立 TTS 合成验证程序 tts\_smoke

### 1\. 为什么执行：上一步问题、假设与本步目标

不能因为 SDK 头文件和模型文件存在就认为 TTS 可用；先不接声卡，只验证文本→float样本→WAV持久化的最小闭环。目标是分离合成错误与音频播放问题。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作；历史命令仅按资料还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano src/audio/tts_smoke.cpp
cmake -S . -B build/asr_llm
cmake --build build/asr_llm --target tts_smoke --parallel 2
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：切换当前Shell工作目录，不修改硬盘文件。

- **`$HOME`**：展开/home/cat；双引号避免路径空格分词。

- **`nano`**：交互式文本编辑器，创建或覆盖已有文件的内容，必须手工Ctrl\+O、Enter、Ctrl\+X保存退出。

- **`src/audio/tts_smoke.cpp`**：第三阶段独立合成测试入口，归档完整182行，见源码附录。

- **`cmake -S .`**：源码根目录当前路径；\-S指定source tree。

- **`-B build/asr_llm`**：指定现有的CMake二进制构建目录。

- **`--build`**：构建选定目录，使用生成器调用make。

- **`--target tts_smoke`**：仅构建tts\_smoke及依赖，不把所有测试一起编译。

- **`--parallel 2`**：并发最多两个编译任务，控制RK3576内存峰值。

### 4\. 终端实际返回/未保存事实

**【典型输出示例，非当时实测】**

```Plaintext
[100%] Built target tts_smoke（此行是结构性示例，未保存本操作原始编译日志）
```

### 5\. 输出内容逐行/逐字段解释

- Built target仅证明编译/链接成功，不表示Kokoro已经在板上合成。

- 若缺Sherpa头/库，通常编译或链接失败；应先确认SHERPA\_ONNX\_ROOT。

### 6\. 成功与失败判断、退出状态

成功标准为构建返回码0且build/asr\_llm/tts\_smoke生成；gcc/gmake非0时查第一处error。即使100%也需要下一步真实合成。

### 7\. 环境影响、权限、风险及后续衔接

编辑源文件会写磁盘；CMake写构建目录；内存/CPU短时占用；无需root，不改内核/设备树。

### 8\. 最终工程结论

完成TTS合成专用的可执行测试入口，为独立验收合成RTF建立基线。

### 本操作面试问题与回答

**问：为什么要先单测TTS再接ALSA？**

答：推理与PCM播放位于不同接口层；单测把模型/词典/采样率问题与设备枚举、PCM缓冲/XRUN隔离，减少故障空间。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 7：3\.2：运行Kokoro独立合成并核实声线、RTF

### 1\. 为什么执行：上一步问题、假设与本步目标

为了比较候选模型与音色，利用TTSService读取Kokoro multi\-lang v1\.1，采用线程数2和speaker 17生成中文PCM/WAV，量化合成耗时，听感由用户验证。此前MeloTTS也已探索但最终选Kokoro。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作；历史命令仅按资料还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
RUNTIME="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
LD_LIBRARY_PATH="$RUNTIME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./build/asr_llm/tts_smoke "$KOKORO_MODEL" /tmp/stage3_kokoro.wav "你好，我是你的车载语音助手。" 2 17
```

### 3\. 命令本体和参数逐项解析

- **`RUNTIME`**：已使用的aarch64 sherpa\-onnx v1\.13\.8 CPU共享运行时路径。

- **`KOKORO_MODEL`**：已使用的Kokoro模型目录，含model\.onnx及voices\.bin。

- **`LD_LIBRARY_PATH`**：ELF动态链接器的\.so搜索路径；覆盖前把旧值通过$\{变量:\+:旧值\}条件追加。

- **`./build/asr_llm/tts_smoke`**：独立合成/WAV测试程序。

- **`模型目录`**：传给TTSService::initialize的第一个实参，不是单个onnx路径。

- **`/tmp/stage3_kokoro.wav`**：UTF\-8文本，最终输出语音。

- **`中文句子`**：本次推荐的临时WAV输出路径；非历史原始文件名。

- **`2`**：num\_threads=2，CPU ONNX推理并发线程。

- **`17`**：speaker\_id=17，对应用户选中的Kokoro女声zf\_024。

### 4\. 终端实际返回/未保存事实

**【历史真实实机日志节选；对应建议命令非当时记录的原始执行命令】**

```Plaintext
[Init] ... sample_rate=24000 speakers=103 sid=17
[TTS] synth_ms=19254.025 audio_sec=3.752 RTF=5.132
PASS
```

### 5\. 输出内容逐行/逐字段解释

- 【历史单测实测片段】sample\_rate=24000表示每秒24000样本；speakers=103是模型暴露的音色数。

- sid=17固定选zf\_024；不能误读为设备号。

- synth\_ms=19254\.025是推理约19\.254秒。

- audio\_sec=3\.752是生成声波长度，不是录制用时。

- RTF=19\.254025/3\.752≈5\.132；RTF\>1表示合成慢于实时。

- 此历史日志的完整命令行未保留；上面提供的是基于最终源码重建的【建议复现】，并非当时实际输入。

### 6\. 成功与失败判断、退出状态

历史单测PASS且真实合成数据存在；推荐命令是否可运行仍需对应最终源码的argc解析验证（源码附录可核对），不能将例子当作已执行。失败定位模型路径/词典/SDK动态库/音色编号。

### 7\. 环境影响、权限、风险及后续衔接

读取模型，CPU计算消耗内存；在/tmp生成WAV可能占磁盘；不涉及ALSA、无需root，不可据此证明有声音输出。

### 8\. 最终工程结论

Kokoro支持中文和sid17，质量满足功能需要；RTF≈5确定TTS是后续主要优化对象。

### 本操作面试问题与回答

**问：如何计算TTS的RTF，怎样解读5\.132？**

答：RTF=合成墙钟时间/生成音频时长。本次19\.254/3\.752≈5\.132，代表合成3\.75秒语音花约19\.25秒；CPU上远慢于实时。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `src/audio/tts_service.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 8：3\.3：创建 ALSA 播放服务头文件和实现

### 1\. 为什么执行：上一步问题、假设与本步目标

TTSService的输出是float PCM采样，并非可直接驱动USB耳机的ALSA PCM流；需要统一封装设备打开、S16\_LE转换、短写/EAGAIN/XRUN处理、drain与关闭。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作；历史命令仅按资料还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano include/audio/alsa_playback_service.h
nano src/audio/alsa_playback_service.cpp
wc -l include/audio/alsa_playback_service.h src/audio/alsa_playback_service.cpp
```

### 3\. 命令本体和参数逐项解析

- **`nano`**：CUI编辑器，输入归档中真实声明/定义；每次Ctrl\+O保存。

- **`include/audio/alsa_playback_service.h`**：面向调用方的类接口和成员，最终60行。

- **`src/audio/alsa_playback_service.cpp`**：实现ALSA打开、写入、格式转换、恢复、关闭，最终399行。

- **`wc`**：word count工具。

- **`-l`**：按换行计数，不代表可执行语句数。

- **`两个相对路径`**：都以工程根为基准。

### 4\. 终端实际返回/未保存事实

**【根据上传源码计算的事实；非历史终端截图】**

```Plaintext
60 include/audio/alsa_playback_service.h
399 src/audio/alsa_playback_service.cpp
```

### 5\. 输出内容逐行/逐字段解释

- 【源码归档验证】最终头文件60行，实现399行；这是对上传包的确定事实。

- 编写操作时没有保存当时nano交互界面及wc命令原始输出，展示的是归档可复算的计数结果，不能误称历史原始输出。

### 6\. 成功与失败判断、退出状态

成功为文件真实存在、声明和实现符号匹配、后续编译通过；ALSA打开/播放仍需真实外设验证。

### 7\. 环境影响、权限、风险及后续衔接

编辑/创建文件；不需要root；更改C\+\+不会立刻改变系统设备，必须重新编译链接。

### 8\. 最终工程结论

实现了可复用的AlsaPlaybackService；资源通过RAII和明确close生命周期管理。

### 本操作面试问题与回答

**问：为什么浮点PCM要转S16\_LE？**

答：目前ALSA设备参数用SND\_PCM\_FORMAT\_S16\_LE，而Kokoro输出float \[\-1,1\]；必须裁剪并乘量程量化成小端16位有符号整数，传给snd\_pcm\_writei按帧写。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `include/audio/alsa_playback_service.h`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `src/audio/alsa_playback_service.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 9：3\.3：编写并构建 TTS→ALSA 实机播放入口

### 1\. 为什么执行：上一步问题、假设与本步目标

为把推理与播放结合起来，同时避免污染异步Worker，先用单线程 smoke 测试完成初始化→合成→PCM write→drain，记录ALSA buffer/period/xrun和Wall Time。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作；历史命令仅按资料还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano src/audio/tts_playback_smoke.cpp
cmake -S . -B build/asr_llm
cmake --build build/asr_llm --target tts_playback_smoke --parallel 2
```

### 3\. 命令本体和参数逐项解析

- **`nano`**：编辑最终192行实机测试入口，主程序CLI位置详见附录。

- **`cmake`**：跨平台构建系统配置工具。

- **`-S .`**：指向当前源码根目录。

- **`-B build/asr_llm`**：复用Stage2/3的构建缓存和输出目录。

- **`--build`**：编译而非配置。

- **`--target tts_playback_smoke`**：精确编译tts\_playback\_smoke可执行文件。

- **`--parallel 2`**：限制嵌入式板上的构建并发，以免峰值内存太高。

### 4\. 终端实际返回/未保存事实

**【典型输出示例，非当时实测】**

```Plaintext
[100%] Built target tts_playback_smoke（编译输出历史未保留；结构性示例）
```

### 5\. 输出内容逐行/逐字段解释

- 该目标在归档CMake中单独直接包含tts\_service\.cpp和alsa\_playback\_service\.cpp。

- 仅能证明函数/动态库链接，不能断定PCM运行时硬件打开成功。

### 6\. 成功与失败判断、退出状态

编译退出0与可执行文件存在为构建合格；链接失败看undefined reference、找不到libasound\.so等错误。

### 7\. 环境影响、权限、风险及后续衔接

写源代码和build目录；CPU/RAM编译占用，无需root，不修改声卡驱动配置。

### 8\. 最终工程结论

得到最小真实音频播放验收入口；下一步验证ALSA参数并试听。

### 本操作面试问题与回答

**问：snd\_pcm\_writei返回的是字节数还是帧数？**

答：返回本次成功提交的PCM帧数。mono且S16时一帧2字节；多声道时一帧包含所有通道。因此不能把返回值当字节数，否则会导致偏移错误或音频截断。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_playback_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 10：3\.3：修复ALSA XRUN并以真实声卡播放通过

### 1\. 为什么执行：上一步问题、假设与本步目标

早期播放出现EPIPE/XRUN欠载风险；提高缓冲窗口并设置软件start\_threshold让硬件等至少2个period准备就绪，再交叉核实written frames、流状态和XRUN计数。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现操作；历史命令仅按资料还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
RUNTIME="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
LD_LIBRARY_PATH="$RUNTIME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./build/asr_llm/tts_playback_smoke "$KOKORO_MODEL" "plughw:1,0" "你好，我是你的车载语音助手。" 2 17
```

### 3\. 命令本体和参数逐项解析

- **`LD_LIBRARY_PATH`**：sherpa C API共享库搜索路径，先为此进程生效，不持久化写系统配置。

- **`tts_playback_smoke`**：同步串联合成与ALSA的测试二进制。

- **`KOKORO_MODEL`**：模型根目录。

- **`中文文本`**：需要合成的UTF\-8文本。

- **`plughw:1,0`**：ALSA PCM plug插件自动做格式适配，card=1、device=0；以当时HyperX识别结果为准，热插拔可能改变card编号。

- **`2`**：合成CPU线程数。

- **`17`**：Kokoro speaker\_id。

- **`内部buffer_time=500000`**：ALSAlib设置的建议buffer time单位微秒，即500ms；库会返回实际协商frames。

- **`内部start_threshold=6000`**：应用端约定最初准备两period再启动，降低小首包触发的欠载。

### 4\. 终端实际返回/未保存事实

**【历史真实实机日志节选；参数化复现命令为建议版本】**

```Plaintext
[Init] ... sample_rate=24000 speakers=103 sid=17
[TTS] synth_ms=19254.025 audio_sec=3.752 RTF=5.132
[ALSA config] buffer_frames=12000 period_frames=3000 start_threshold=6000 buffer_ms=500.000
[ALSA write] submitted_frames=90037 state=RUNNING
[ALSA] playback_ms=3860.631 xrun_count=0
PASS
```

### 5\. 输出内容逐行/逐字段解释

- 【历史实机日志节选】buffer\_frames=12000除以24000采样/秒=0\.5秒缓冲。

- period\_frames=3000对应125ms。

- start\_threshold=6000对应250ms预填；采用双period启动。

- submitted\_frames=90037对应约3\.752秒音频，说明全部样本已提交。

- state=RUNNING是查询时ALSA流状态，不能单凭此保证耳机听到声音；用户随后验证。

- playback\_ms=3860\.631约3\.86秒，包括drain及其他开销；xrun\_count=0本次没有计到EPIPE。

- 完整的原始命令行未保存，此处是根据最终CLI签名整理的复现版本；数字是真实的历史日志。

### 6\. 成功与失败判断、退出状态

PASS \+用户真实听到完整声音 \+XRUN=0表明这一段单次播放达标；设备忙可能报EBUSY，EPIPE为欠载可recover但验收仍应记录XRUN。

### 7\. 环境影响、权限、风险及后续衔接

打开并占用USB耳机的Playback PCM，播放音频；无root、无驱动/设备树修改；临时内存存储float\+int16复制。

### 8\. 最终工程结论

500ms buffer和双period门槛消除该次可观察到的XRUN；并非证明所有播放场景永不欠载。

### 本操作面试问题与回答

**问：为什么buffer=500ms、period=125ms能缓解XRUN？**

答：ALSA DMA以period为节拍消费环形缓冲，生产端若供给不足会under\-run产生\-EPIPE。较大buffer提供调度抖动余量，start\_threshold=2period延迟启动形成初始积累；代价是首播延迟和更高瞬态缓冲。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/alsa_playback_service.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `src/audio/tts_playback_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 11：3\.4：创建 TTSWorker 有界异步队列头文件

### 1\. 为什么执行：上一步问题、假设与本步目标

同步tts\.synthesize\+play串行执行可阻塞业务调度线程20–30秒；需要把慢TTS放入独立工作线程，通过状态机、回调和有界FIFO隔离。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现；根据最终源码接口还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano include/audio/tts_worker.h
wc -l include/audio/tts_worker.h
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：$HOME是cat主目录；进入工程根。

- **`nano`**：交互创建头文件，在编辑器保存退出；更改同名文件会覆盖之前内容。

- **`include/audio/tts_worker.h`**：最终130行定义TTSWorker/TTSSubmitStatus/TTSWorkerResult/Done回调。

- **`wc -l`**：统计文件换行数，不是函数执行计数。

### 4\. 终端实际返回/未保存事实

**【由实际源码可复算的行数，非历史回显】**

```Plaintext
130 include/audio/tts_worker.h
```

### 5\. 输出内容逐行/逐字段解释

- 【源码可确认】归档该文件130行；历史终端wc回显未留存。

- TTSWorkerResult包含success、synthesis\_ms、playback\_ms、audio\_seconds、sample\_rate、xrun\_count。

- TTSSubmitStatus至少有Accepted、NotRunning、QueueFull；队列背压在提交时而非播放时发生。

### 6\. 成功与失败判断、退出状态

头文件语法及接口要通过依赖目标编译才能确认；wc=130仅确认文件长度，无法排除运行时竞态。

### 7\. 环境影响、权限、风险及后续衔接

修改用户代码，文件持久化；无需root、不触碰ALSA设备或NPU。

### 8\. 最终工程结论

TTSWorker头文件将排队状态和回调边界固定下来；服务引用不转移所有权。

### 本操作面试问题与回答

**问：有界队列capacity限制的是什么？**

答：TTSWorker中通常限制等待队列大小，不是正在运行任务数；因此capacity=1时可以一条正在执行、一条待执行，再提交第三条报QueueFull，不能误读为最多总共一条。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `include/audio/tts_worker.h`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 12：3\.4：实现 TTSWorker 后台线程与安全停止逻辑

### 1\. 为什么执行：上一步问题、假设与本步目标

解决主线程被TTS推理阻塞、多个请求堆积、进程关闭时回调引用失效、取消队列任务丢通知等工程问题。实现线程启动、submit、runLoop、requestStop与join。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现；根据最终源码接口还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano src/audio/tts_worker.cpp
wc -l src/audio/tts_worker.cpp
```

### 3\. 命令本体和参数逐项解析

- **`nano`**：将归档实现写入该\.cpp，必须明确保存。

- **`src/audio/tts_worker.cpp`**：301行，职责是TTSWorker的任务FIFO/condition\_variable和回调。

- **`wc -l`**：只验证物理行数，不能测试线程互斥与停止竞态。

- **`命令无sudo`**：工程用户cat拥有源码目录写权限。

### 4\. 终端实际返回/未保存事实

**【由实际源码可复算的行数，非历史回显】**

```Plaintext
301 src/audio/tts_worker.cpp
```

### 5\. 输出内容逐行/逐字段解释

- 【源码可确认】最终cpp为301行。

- std::mutex保护queue\_/running\_/stop\_requested\_共享字段；cv\_\.wait\(predicate\)避免忙轮询/假唤醒。

- requestStop取消等待任务但可让已执行任务结束；所有Accepted任务仍应回调，包括取消者。

### 6\. 成功与失败判断、退出状态

后续构建并通过队列测试，才支持“线程功能正确”的结论；本步编辑成功并非并发正确性证明。

### 7\. 环境影响、权限、风险及后续衔接

更改源码，在编译前不影响既有可执行文件；无root或驱动操作。

### 8\. 最终工程结论

创建具有明确背压与终止语义的异步TTS生产消费模块，支持后续LLMWorker回调提交。

### 本操作面试问题与回答

**问：为什么回调不能持有队列mutex调用？**

答：用户回调可能获取print\_mutex/state\_mutex、调用submit/requestStop等，如果仍持queue\_mutex则容易锁顺序反转、自锁或阻塞工作线程；应先取出任务或任务结果、释放内部锁，再调用回调。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_worker.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 13：3\.4：使用 multimodal\_tts 静态库统一构建

### 1\. 为什么执行：上一步问题、假设与本步目标

避免多个测试入口重复编译TTSService/Playback/Worker导致职责分散；统一发布多模块可复用静态库并通过PUBLIC依赖传递sherpa/ALSA头文件与链接库。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现；根据最终源码接口还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano CMakeLists.txt
cmake -S . -B build/asr_llm
cmake --build build/asr_llm --target multimodal_tts --parallel 2
```

### 3\. 命令本体和参数逐项解析

- **`CMakeLists.txt`**：工程构建描述文件，归档Stage3\.4段用add\_library\(multimodal\_tts STATIC \.\.\.\)。

- **`add_library(... STATIC)`**：产出\.a归档链接库，供smoke与后续系统引用。

- **`target_link_libraries(... PUBLIC multimodal_audio)`**：PUBLIC使链接依赖对下游可见，可传递头路径/使用要求。

- **`cmake -S .`**：从当前工程源生成规则。

- **`-B build/asr_llm`**：复用既有build缓存。

- **`--target multimodal_tts`**：构建此静态库及依赖；不会执行任何ASR/TTS模型。

- **`--parallel 2`**：限制并行编译进程，减轻RAM。

### 4\. 终端实际返回/未保存事实

**【后续3\.5编译真实输出节选，非本操作最初编译日志】**

```Plaintext
[ 90%] Built target multimodal_tts
```

### 5\. 输出内容逐行/逐字段解释

- 【3\.5最终编译真实片段】这是最终整合编译时目标成功行，不代表3\.4最初执行时的确切输出。

- 静态库编译成功，不保证运行时动态库的搜寻路径设置正确。

### 6\. 成功与失败判断、退出状态

CMake配置返回0且静态库目标可构建为成功；若出现multiple definition要核查源文件是否同时被多目标重复直接链接。

### 7\. 环境影响、权限、风险及后续衔接

重写CMakeLists\.txt\+构建输出，修改编译图和\.a文件；无root、不触碰模型硬件。

### 8\. 最终工程结论

形成可复用 multimodal\_tts 组件，并进入Worker smoke实测。

### 本操作面试问题与回答

**问：为何静态库仍需LD\_LIBRARY\_PATH？**

答：multimodal\_tts是自身\.a静态归档，但其引用的sherpa C API等依然通过动态共享库加载，动态装载器需找到libsherpa\-onnx\-c\-api\.so。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 14：3\.4：TTSWorker单任务异步处理与主线程响应性实测

### 1\. 为什么执行：上一步问题、假设与本步目标

验证submit立即返回Accepted而主线程无需等待Kokoro完成；在worker执行synthesize\+ALSA play后Done回调记录queue/synth/audio/playback；验证无XRUN。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现；根据最终源码接口还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
RUNTIME="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
LD_LIBRARY_PATH="$RUNTIME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./build/asr_llm/tts_worker_smoke "$KOKORO_MODEL" "plughw:1,0" "你好，我是你的车载语音助手。" 2 17
```

### 3\. 命令本体和参数逐项解析

- **`LD_LIBRARY_PATH`**：使进程优先搜索sh­erpa\-onnx CPU动态库文件。

- **`tts_worker_smoke`**：异步单请求可执行测试程序；argc=6，含程序名。

- **`KOKORO_MODEL`**：第一个参数，模型目录。

- **`plughw:1,0`**：第二个参数，USB播放ALSA PCM，编号受插拔影响。

- **`中文句子`**：第三个参数，合成数据输入。

- **`2`**：第四个参数，TTS num\_threads。

- **`17`**：第五个参数，Kokoro sid。

### 4\. 终端实际返回/未保存事实

**【历史真实实机日志节选；完整历史命令未保存】**

```Plaintext
[Init] OK init_ms=6215.36
[ALSA config] buffer_frames=12000 period_frames=3000 start_threshold=6000 buffer_ms=500
[Main] submit accepted; main thread remains responsive
[ALSA write] submitted_frames=92095 state=RUNNING
[Done] success=true queue_ms=0.088 synth_ms=18771.862 audio_sec=3.837 playback_ms=3861.562 xrun_count=0
PASS
```

### 5\. 输出内容逐行/逐字段解释

- 【历史真实实机日志节选】init\_ms=6215\.36是模型加载耗时，独立于合成延迟。

- Main submit accepted说明异步任务被接纳；不是合成已完成。

- queue\_ms=0\.088为等待队列耗时；并发负载下会变化。

- synth\_ms=18\.77秒，audio\_sec=3\.837，RTF≈4\.89；仍为慢TTS。

- playback\_ms≈3\.86秒略长于音频长度，因为drain/调度。

- xrun\_count=0仅代表本轮无记录的underrun。

### 6\. 成功与失败判断、退出状态

本轮必须同时有Accepted、Done success=true、xrun\_count=0、PASS及实听（如有）才称通过；如果模型加载卡住不等于线程失效。

### 7\. 环境影响、权限、风险及后续衔接

CPU模型推理\+独占耳机播放，硬件真实发声；没有源码/内核配置修改，可因声卡设备繁忙失败。

### 8\. 最终工程结论

证实TTSWorker解耦了主线程与慢合成，功能达到3\.4单任务验收。

### 本操作面试问题与回答

**问：为什么异步后延迟还是19秒？**

答：异步改变调用方线程阻塞和任务调度方式，不改变Kokoro单次ONNX推理的计算量；真实RTF仍约5，低延迟必须换/量化/优化模型或流式合成。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_worker_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `src/audio/tts_worker.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 15：3\.4：QueueFull、NotRunning及取消任务回调验证

### 1\. 为什么执行：上一步问题、假设与本步目标

单任务PASS不能证明背压和安全停止；故意设置有限待执行队列，并快速提交三个任务，验证前两任务接收、第三任务QueueFull、停止后的第四任务NotRunning、第二任务收到取消回调。

### 2\. 完整命令（原始 / 建议复现标注）

**【建议复现；根据最终源码接口还原】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
RUNTIME="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
LD_LIBRARY_PATH="$RUNTIME/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./build/asr_llm/tts_worker_queue_smoke "$KOKORO_MODEL" "plughw:1,0" 2 17
```

### 3\. 命令本体和参数逐项解析

- **`tts_worker_queue_smoke`**：专用排队/关闭边界测试，argc=5。

- **`KOKORO_MODEL`**：第一个CLI参数。

- **`plughw:1,0`**：第二个CLI参数，用户USB Playback PCM。

- **`2`**：第三个参数，线程数。

- **`17`**：第四个参数，speaker ID。

- **`LD_LIBRARY_PATH`**：仅为该进程注入SDK动态库路径。

### 4\. 终端实际返回/未保存事实

**【历史真实实机日志节选；完整历史命令未保存】**

```Plaintext
[Queue] task101=Accepted task102=Accepted task103=QueueFull pending=1
[Stop] task104=NotRunning
[ALSA write] submitted_frames=90079 state=RUNNING
[Result] callbacks=true first_success=true second_cancelled=true rejected_count=1
PASS
```

### 5\. 输出内容逐行/逐字段解释

- 【历史真实实机日志节选】101正在运行、102等待FIFO，103被拒绝，pending=1描述等待队列而非总任务数。

- task104=NotRunning表明停止之后拒绝新任务。

- callbacks=true说明所有已接纳任务都获得结束通知，防止主线程永久等待。

- first\_success=true表示在途任务可完成；second\_cancelled=true表示等待任务停止时被取消且回调执行。

- rejected\_count=1对应103这一条队列溢出。

- submitted\_frames=90079说明正在运行的第一个任务仍正常播放音频。

### 6\. 成功与失败判断、退出状态

PASS\+取消者回调\+拒绝计数吻合构成单次边界验收；仍需TSAN/压力测试覆盖时序竞态。

### 7\. 环境影响、权限、风险及后续衔接

真实访问ALSA和CPU推理；stop只停止工作对象不影响OS服务；无需root。

### 8\. 最终工程结论

可明确向面试官证明处理了Backpressure、Graceful Shutdown与Callback Completion语义。

### 本操作面试问题与回答

**问：队列已满为什么不能无限缓存？**

答：TTS生成常需近20秒，如果LLM持续提交而无上限队列，等待任务会无限增长、文本内存与响应延迟失控；有界队列将资源压力显式反馈给业务层。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/tts_worker_queue_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `include/audio/tts_worker.h`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 16：3\.5：从已验证的 ASR→LLM 入口核对清理和回调顺序

### 1\. 为什么执行：上一步问题、假设与本步目标

为避免重写先前已通过验收的 ASR\+LLM 模块，先检查原403行asr\_llm\_smoke尾部，确认producer\.join→consumer\.join→completed==accepted→llm\_worker\.join→llm\.shutdown的实际顺序。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
sed -n '301,430p' src/audio/asr_llm_smoke.cpp
tail -n 100 CMakeLists.txt
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：切入工程根目录，$HOME对应/home/cat。

- **`sed`**：流式文本编辑/打印工具，本次仅输出指定范围而不写文件。

- **`-n`**：关闭默认整文件打印，只显示p选择区间。

- **`'301,430p'`**：单引号保持sed脚本字面量；从301到430物理行打印，尽管文件实际403行。

- **`src/audio/asr_llm_smoke.cpp`**：上一阶段已验证的ASR→LLM基准入口。

- **`tail -n 100`**：读取末尾100行；\-n指定数量。

- **`CMakeLists.txt`**：查看第三阶段模块已有库/可执行目标，防止重复add\_executable。

### 4\. 终端实际返回/未保存事实

**【历史实际查询后保留的关键代码结构；完整原文见附录】**

```Plaintext
producer.join();
consumer.join();
while (completed < accepted) { completed_cv.wait_for(...); }
llm_worker.requestStop();
llm_worker.join();
llm.shutdown();
...
if(ENABLE_SHERPA_ASR)
    add_executable(tts_worker_queue_smoke ... )
endif()
```

### 5\. 输出内容逐行/逐字段解释

- 【真实提供的源码节选，排版抽象过渡】原日志里存在完整的try/catch、condition\_variable等待和summary，这里用省略号代表未逐字复刻；最终原403行原文在第九篇。

- producer\.join先等录音结束；consumer\.join再等识别工作队列排空。

- while\+wait\_for直到全部已接受LLM请求完成，才关闭LLMWorker/Runtime。

- CMake原尾部有3\.4 queue smoke，没有3\.5可执行目标。

### 6\. 成功与失败判断、退出状态

能从文件看到合理退出流程，但无法仅凭查看代码证明无竞态；最终必须编译/执行完整联调。

### 7\. 环境影响、权限、风险及后续衔接

只读，不更改模型、源码或声卡；下一步创建隔离的新测试入口。

### 8\. 最终工程结论

沿用旧可靠链路，新增LLM Done→TTS submit和第二重TTS drained等待，不破坏Stage2 smoke。

### 本操作面试问题与回答

**问：为什么必须先consumer\.join再判断LLM accepted总数？**

答：只要ASRWorker尚在运行，它就可能继续往LLMWorker提交新任务，accepted计数仍在增长。只有停止生产者并等待消费者退出，后续任务总数才稳定。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `include/audio/asr_pipeline.h`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 17：3\.5：nano写入1077行真正的最终联调程序

### 1\. 为什么执行：上一步问题、假设与本步目标

第三阶段要保留上一阶段基线，独立新建asr\_llm\_tts\_smoke\.cpp；把成功LLM答复通过TTSWorker异步播出，同时加入两个Worker统计、等待、关闭和错误路径。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
nano src/audio/asr_llm_tts_smoke.cpp
wc -l src/audio/asr_llm_tts_smoke.cpp
head -n 10 src/audio/asr_llm_tts_smoke.cpp
tail -n 15 src/audio/asr_llm_tts_smoke.cpp
```

### 3\. 命令本体和参数逐项解析

- **`nano`**：交互源码编辑；在开发板直接粘贴并Ctrl\+O\+回车\+Ctrl\+X保存。

- **`src/audio/asr_llm_tts_smoke.cpp`**：独立Stage3\.5入口，原路径未覆盖asr\_llm\_smoke\.cpp。

- **`wc -l`**：统计文件实际行数。

- **`head -n 10`**：查看开头十行，确认ASR/TTS/LLM头文件。

- **`tail -n 15`**：检查末尾PASS和return。

- **`各命令换行`**：同一Shell依次执行，正常读操作仅标准输出、不更新文件。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
1077 src/audio/asr_llm_tts_smoke.cpp

#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"
#include "audio/tts_worker.h"
...（head与tail之间未展示）
        tts_failed == 0 &&
        tts_rejected == 0 &&
        tts_empty == 0;

    std::cout
        << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
```

### 5\. 输出内容逐行/逐字段解释

- 1077是用户当场wc返回的真实物理行数；归档副本同为1077行。

- 头文件接口跨audio/asr、audio/tts、ai/llm三个组件。

- 最终验收是多个bool和计数共同成立，不是看到模型加载就通过。

- 末尾return passed ? 0:1是三元条件运算符，0正常完成、1失败。

### 6\. 成功与失败判断、退出状态

文件首尾已复查；还必须通过下游CMake编译证明完整代码语法与链接成功，并实机判断所有回调。

### 7\. 环境影响、权限、风险及后续衔接

编辑源文件；读操作不改文件；未改旧入口、内核与设备树。

### 8\. 最终工程结论

实际1077行联调源码存在且完备；下步必须注册CMake目标。

### 本操作面试问题与回答

**问：LLM完成回调里提交TTS有什么生命周期风险？**

答：该回调捕获TTSWorker与state\_mutex等引用；如果主线程在LLMWorker退出前销毁这些对象会出现悬空引用。因此先等待LLM回调结束、join LLMWorker，再等TTS完成、join TTSWorker。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 18：3\.5：首次构建失败—CMake没有add\_executable目标

### 1\. 为什么执行：上一步问题、假设与本步目标

源文件写好后直接指定\-\-target构建，CMake配置成功但gmake提示没有规则。需要确认是不是条件为OFF或者根本未注册目标，而不是无意义地修改C\+\+源码。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
cmake -S . -B build/asr_llm
cmake --build build/asr_llm --target asr_llm_tts_smoke --parallel 2
grep -n "add_executable(asr_llm_tts_smoke" CMakeLists.txt
grep -E '^(ENABLE_SHERPA_ASR|BUILD_WITH_RKLLM):BOOL=' build/asr_llm/CMakeCache.txt
```

### 3\. 命令本体和参数逐项解析

- **`cmake -S . -B build/asr_llm`**：配置CMake，成功不代表该特定目标存在。

- **`--target asr_llm_tts_smoke`**：要求构建系统查找精确可执行目标名。

- **`--parallel 2`**：最多2个编译并行任务；找不到目标时尚未编译。

- **`grep -n`**：查找关键字并附带行号；匹配不到退出码通常是1且无标准输出。

- **`add_executable(...`**：CMake注册可执行文件目标的声明。

- **`grep -E`**：启用扩展正则。

- **`'^(ENABLE_SHERPA_ASR|BUILD_WITH_RKLLM):BOOL='`**：Shell单引号保留正则；^锚定开头，\(\.\.\.\)\|\(\.\.\.\)两种变量名，:BOOL=限定缓存变量类型。

- **`CMakeCache.txt`**：特定build树上次配置后的变量状态，不应与其它构建目录混用。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
-- Real RKLLM backend enabled
-- Configuring done
-- Generating done
gmake: *** 没有规则可制作目标“asr_llm_tts_smoke”。 停止。
（grep -n 第一条没有输出）
BUILD_WITH_RKLLM:BOOL=ON
ENABLE_SHERPA_ASR:BOOL=ON
```

### 5\. 输出内容逐行/逐字段解释

- CMake打印Configuring done与Generating done说明配置生成成功，但与target存在性无必然关系。

- gmake没有规则表示构建图里没有asr\_llm\_tts\_smoke这一目标；尚未涉及C\+\+语法。

- grep \-n无输出表明CMakeLists里找不到目标声明；对grep而言退出状态为1。

- 两项BOOL均ON，排除了条件OFF导致跳过注册的可能。

### 6\. 成功与失败判断、退出状态

本步骤期望是准确找出异常原因而非要求编译成功。诊断成功：缺少add\_executable；应追加CMake目标。

### 7\. 环境影响、权限、风险及后续衔接

cmake配置更新build树，grep只读；此步没有运行模型、也不修改C\+\+。

### 8\. 最终工程结论

首次构建失败根因是漏加CMake target，不是SDK或编译器故障。

### 本操作面试问题与回答

**问：CMake配置成功为何仍不能build某个target？**

答：CMake解析CMakeLists合法并生成已定义目标即可成功；尚未添加add\_executable的目标不属于构建图。要用\-\-target help或grep准确核查。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 19：3\.5：备份CMake、增加目标并确认生成规则

### 1\. 为什么执行：上一步问题、假设与本步目标

明确两个开关ON且缺目标后，只追加Stage3\.5 target与三个已存在的lib依赖，不重复写cpp文件；备份CMake以便回滚。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
cp -a CMakeLists.txt CMakeLists.txt.before_stage35.bak
nano CMakeLists.txt
cmake -S . -B build/asr_llm
cmake --build build/asr_llm --target help | grep asr_llm_tts_smoke
```

### 3\. 命令本体和参数逐项解析

- **`cp`**：复制文件。

- **`-a`**：保留权限、时间戳等归档属性；输出同名\.bak供回退。

- **`nano CMakeLists.txt`**：手工追加if\(ENABLE\_SHERPA\_ASR AND BUILD\_WITH\_RKLLM\)、add\_executable与target\_link\_libraries，不删除旧target。

- **`if(... AND ...)`**：仅开启ASR与RKLLM两个后端时生成该目标。

- **`target_link_libraries(... PRIVATE ...)`**：链接multimodal\_audio、multimodal\_core、multimodal\_tts，PRIVATE不对其它消费者传播依赖。

- **`cmake -S . -B ...`**：重新生成构建规则。

- **`--target help`**：列出可构建target而非实际构建。

- **`|`**：Shell管道，将前一个命令标准输出输入grep。

- **`grep asr_llm_tts_smoke`**：过滤确认目标存在，若无匹配返回1。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
-- Real RKLLM backend enabled
-- RKLLM include: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/include
-- RKLLM library: /home/cat/projects/RK3576/rkllm_sdk/rkllm-runtime/Linux/librkllm_api/aarch64/librkllmrt.so
-- Configuring done
-- Generating done
... asr_llm_tts_smoke
... src/audio/asr_llm_tts_smoke.o
... src/audio/asr_llm_tts_smoke.i
... src/audio/asr_llm_tts_smoke.s
```

### 5\. 输出内容逐行/逐字段解释

- include/lib路径是CMake定位的真实RKLLM头目录和librkllmrt\.so，不是TTS音频设备。

- `... asr_llm_tts_smoke`存在证明make生成了目标。

- \.o是目标文件、\.i通常为预处理输出、\.s为汇编文件，make help额外生成这些规则是正常现象。

- 备份文件以before\_stage35命名，用来区别修改前版本。

### 6\. 成功与失败判断、退出状态

成功判据help列出目标，cmake配置无错误；目标存在仍不意味着源码已编译或有能力加载模型。

### 7\. 环境影响、权限、风险及后续衔接

产生\.bak（占一点磁盘），修改CMakeLists，重新写build Makefile；无需root。

### 8\. 最终工程结论

构建目标注册完毕，下一步才可以验证1077行源码真正编译链接。

### 本操作面试问题与回答

**问：PRIVATE与PUBLIC对CMake依赖有什么区别？**

答：PRIVATE表示本目标编译/链接需用，但不把使用要求传播到依赖此目标的后继目标；PUBLIC既自己用也向下游传播。工程multimodal\_tts PUBLIC链接multimodal\_audio以传递ALSA和Sherpa依赖。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 20：3\.5：最终完整源文件编译与链接通过

### 1\. 为什么执行：上一步问题、假设与本步目标

目标存在后，用低并发构建验证1077行代码与ASR/LLM/TTS真实库链接，只有这一关通过才有资格上板联合运行。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
cmake --build build/asr_llm --target asr_llm_tts_smoke --parallel 2
```

### 3\. 命令本体和参数逐项解析

- **`cmake --build`**：调用该构建目录已经选择的生成器。

- **`build/asr_llm`**：之前配置成功的构建树路径。

- **`--target asr_llm_tts_smoke`**：构建唯一Stage3\.5联调目标及其依赖。

- **`--parallel 2`**：两并发，符合4GiB级RK3576构建内存预算。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
[ 42%] Built target multimodal_core
[ 71%] Built target multimodal_audio
[ 90%] Built target multimodal_tts
[ 95%] Building CXX object CMakeFiles/asr_llm_tts_smoke.dir/src/audio/asr_llm_tts_smoke.cpp.o
[100%] Linking CXX executable asr_llm_tts_smoke
[100%] Built target asr_llm_tts_smoke
```

### 5\. 输出内容逐行/逐字段解释

- 42/71/90%是构建进度不是运行成功率。

- multimodal\_core、multimodal\_audio、multimodal\_tts三库目标已构建。

- CXX object表示正在把src/audio/asr\_llm\_tts\_smoke\.cpp编译成对象文件。

- Linking CXX executable表示解析依赖符号、生成ELF可执行文件。

- 100% Built target为构建系统确认完成，不保证所有模型能同时驻留内存。

### 6\. 成功与失败判断、退出状态

构建退出码0，最后一行Built target且生成可执行文件；SDK环境缺失可能出现undefined reference或运行时cannot open shared object，与这里的成功不同。

### 7\. 环境影响、权限、风险及后续衔接

创建/覆盖build目录内\.o和ELF，不运行ALSA/NPU；无root、不改内核。

### 8\. 最终工程结论

3\.5新程序编译\+链接通过，但下一步必须实机加载全部模型才能判定完整功能。

### 本操作面试问题与回答

**问：为什么“编译通过”还会在真实设备被OOM杀死？**

答：编译只检查语义/链接；运行时加载2GB级NPU内存、CPU ONNX、ALSA等形成动态内存峰值，由Linux MM和OOM Killer决定能否完成。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

- `CMakeLists.txt`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 21：3\.5：检查联合运行前RAM、Swap和eMMC剩余空间

### 1\. 为什么执行：上一步问题、假设与本步目标

三模型比单模块占用更多物理内存；需检查可用内存与磁盘，预判OOM/Swap风险。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
free -h
df -h /
```

### 3\. 命令本体和参数逐项解析

- **`free`**：报告总内存、使用量、缓存和可用量；非杀进程操作。

- **`-h`**：human\-readable，自动选择GiB/MiB单位。

- **`df`**：报告已挂载文件系统容量。

- **`-h`**：对df同样按可读单位显示。

- **`/`**：根目录挂载点，只查询根分区。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
total        used        free      shared  buff/cache   available
内存：         3.8Gi       2.2Gi       568Mi        17Mi       1.1Gi       1.6Gi
交换：            0B          0B          0B
文件系统        大小  已用  可用 已用% 挂载点
/dev/mmcblk0p3   29G   27G  1.1G   97% /
```

### 5\. 输出内容逐行/逐字段解释

- total=3\.8Gi：Linux可用内存规模，不等于标称板载4GiB全部可分配。

- used=2\.2Gi，free=568Mi，buff/cache=1\.1Gi；used/free受页缓存影响。

- available=1\.6Gi为综合可回收缓存预测，适合比free判断启动模型余量。

- 交换0B表明无Swap；内存不足时可进入global OOM。

- /dev/mmcblk0p3是eMMC根分区；29G总、27G已用、可用1\.1G、97%使用率。

### 6\. 成功与失败判断、退出状态

两条成功返回0且数字可读取，但不能保证大型模型能够同时初始化；失败可能是proc未挂载或挂载点不可用。

### 7\. 环境影响、权限、风险及后续衔接

只读，不需要root，无文件变更。

### 8\. 最终工程结论

仅1\.6GiB available且无Swap，启动前风险显著；应记录基线。

### 本操作面试问题与回答

**问：available与free有什么区别？**

答：free表示当前直接未分配物理页；available结合可回收cache估算应用可使用内存，更适合观察模型加载前余量。

## 操作 22：3\.5：设置模型SDK路径与动态库环境变量

### 1\. 为什么执行：上一步问题、假设与本步目标

验证全部模型路径来源，避免错误目录被误判为模型缺失；使用变量让后续命令可复现。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
cd "$HOME/projects/RK3576/rk3576_multimodal"
SDK="$HOME/projects/RK3576/rkllm_sdk"
RUNTIME="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
ASR_MODEL="$HOME/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17"
VAD="$HOME/projects/RK3576/asr_runtime/vad/silero_vad.onnx"
MODEL="$SDK/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm"
KOKORO_MODEL="$HOME/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1"
RKLLM_LIB="$SDK/rkllm-runtime/Linux/librkllm_api/aarch64"
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：改变当前Shell工作目录。

- **`$HOME`**：cat用户家目录展开。

- **`双引号`**：保留路径为单个词并允许$变量展开。

- **`SDK`**：RKLLM SDK基目录，不是模型文件。

- **`RUNTIME`**：sherpa\-onnx CPU共享库根目录。

- **`ASR_MODEL`**：SenseVoice模型与tokens目录。

- **`VAD`**：Silero VAD onnx模型文件。

- **`MODEL`**：Qwen2\.5的RKLLM W4A16权重文件。

- **`KOKORO_MODEL`**：Kokoro v1\.1模型及词典、voices目录。

- **`RKLLM_LIB`**：含librkllmrt\.so的aarch64目录。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
【原始终端仅返回Shell提示符；变量赋值成功时无标准输出】
```

### 5\. 输出内容逐行/逐字段解释

- Shell assignment创建本会话局部变量，无print；cd成功后提示符路径改变。

- $SDK在MODEL右值中被展开，原始模型位于rkllm\_sdk/models目录。

- 路径保存在当前SSH会话，另开SSH后不自动继承。

### 6\. 成功与失败判断、退出状态

赋值命令通常退出0；真正检验文件需下一步test \-r。

### 7\. 环境影响、权限、风险及后续衔接

仅当前Shell会话；不修改系统配置，未执行模型、不占硬件。

### 8\. 最终工程结论

把模型版本与路径固定为一次验收条件。

### 本操作面试问题与回答

**问：为什么使用引号？**

答：路径中如有空格，无引号的参数展开会发生word splitting；双引号保持一个实参，同时允许变量替换。

## 操作 23：3\.5：检查全部六个模型资源可读性

### 1\. 为什么执行：上一步问题、假设与本步目标

在加载高内存模型前，先使用POSIX文件可读性检查排除路径错误。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
for f in \
  "$ASR_MODEL/model.int8.onnx" \
  "$ASR_MODEL/tokens.txt" \
  "$VAD" \
  "$MODEL" \
  "$KOKORO_MODEL/model.onnx" \
  "$KOKORO_MODEL/voices.bin"
do
    if [ -r "$f" ]; then
        echo "[OK] $f"
    else
        echo "[MISSING] $f"
    fi
done
```

### 3\. 命令本体和参数逐项解析

- **`for f in`**：Shell循环将六个资源路径逐个赋予f。

- **`\`**：行末续行，使命令可分多行粘贴。

- **`-r`**：test内建的文件可读条件，不是ls选项。

- **`[ ... ]`**：POSIX test条件表达式，方括号左右需要空格。

- **`then/else/fi`**：条件分支语法。

- **`echo`**：将检测状态和路径打印到标准输出。

- **`$ASR_MODEL/model.int8.onnx`**：ASR INT8图权重。

- **`$ASR_MODEL/tokens.txt`**：ASR识别词表。

- **`$VAD`**：Silero VAD ONNX模型。

- **`$MODEL`**：RKLLM模型文件。

- **`$KOKORO_MODEL/model.onnx`**：Kokoro图权重。

- **`$KOKORO_MODEL/voices.bin`**：TTS声线文件。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
[OK] /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/model.int8.onnx
[OK] /home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17/tokens.txt
[OK] /home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx
[OK] /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
[OK] /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1/model.onnx
[OK] /home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1/voices.bin
```

### 5\. 输出内容逐行/逐字段解释

- 每一行OK对应且只对应一个模型所需资源可读性。

- 没有任何MISSING表示六个指定路径均可读；不验证模型格式或RAM容量。

### 6\. 成功与失败判断、退出状态

六项OK是可读检查成功；但脚本末项echo会令循环整体退出0，即使之前有MISSING，不可只凭$?判断全通过。

### 7\. 环境影响、权限、风险及后续衔接

纯只读，无硬件占用；无需root。

### 8\. 最终工程结论

模型路径并非导致首次终止的原因，继续联合加载验证。

### 本操作面试问题与回答

**问：文件可读为什么不代表模型可用？**

答：文件可能损坏、权重与词表不配、运行库版本不兼容；只有SDK成功初始化且真实推理成功才能验证。

## 操作 24：3\.5：第一次联合启动在SenseVoice初始化期间被Kill

### 1\. 为什么执行：上一步问题、假设与本步目标

首次已经编译通过，必须运行RKLLM\+ASR\+Kokoro联调以判断物理内存峰值能否满足。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
LD_LIBRARY_PATH="$RUNTIME/lib:$RKLLM_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
RKLLM_LOG_LEVEL=1 \
./build/asr_llm/asr_llm_tts_smoke \
  "plughw:1,0" "$ASR_MODEL" "$VAD" "$MODEL" \
  "$KOKORO_MODEL" "plughw:1,0" 12 2 17
```

### 3\. 命令本体和参数逐项解析

- **`LD_LIBRARY_PATH`**：为此进程指定CPU sherpa和RKLLM \.so动态库搜索路径；原值非空时追加。

- **`${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}`**：Shell条件展开，变量非空时才追加冒号加原路径。

- **`RKLLM_LOG_LEVEL=1`**：设置RKLLM运行日志级别，仅对这条命令生效。

- **`./build/asr_llm/asr_llm_tts_smoke`**：当前目录下已编译的ELF联调可执行文件。

- **`plughw:1,0`**：第一项ALSA capture，第二项ALSA playback；卡号1设备号0可随硬件枚举变化。

- **`$ASR_MODEL`**：SenseVoice模型目录，程序拼接model\.int8\.onnx和tokens\.txt。

- **`$VAD`**：Silero VAD模型文件。

- **`$MODEL`**：RKLLM量化权重文件。

- **`$KOKORO_MODEL`**：TTS资源目录。

- **`12`**：录音时长秒；2：TTS CPU线程数；17：Kokoro说话人ID。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
I rkllm: Enabled cpus num: 4
[Init] Loading SenseVoice...
已杀死
```

### 5\. 输出内容逐行/逐字段解释

- rkllm Runtime版本1\.3\.1；NPU内核驱动0\.9\.8；设备RK3576。

- ToolKit1\.2\.3、4096上下文上限、2个NPU核心、W4A16量化格式为模型元信息。

- Enabled cpus 4\~7是Runtime可用CPU集合，与TTS 2线程不同。

- 程序进入SenseVoice装载后收到SIGKILL；尚未进入Kokoro、VAD和播放。

- 仅靠已杀死无法独立证明OOM，须通过下一步dmesg确认。

### 6\. 成功与失败判断、退出状态

输出“已杀死”不成功；常见Shell状态128\+9=137（本次未保留echo $?，不能伪造具体退出码）。

### 7\. 环境影响、权限、风险及后续衔接

占用CPU/NPU及RAM，可能触发OOM；不更改磁盘配置。

### 8\. 最终工程结论

多模型常驻环境首次失败；应优先查看内核OOM日志而不是改C\+\+源码。

### 本操作面试问题与回答

**问：SIGKILL和SIGSEGV有什么不同？**

答：SIGKILL由内核/外部发出且不可捕获；SIGSEGV是非法地址访问。这里必须依赖OOM日志进一步归因。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 25：3\.5：内核日志确认global OOM真正杀死联调进程

### 1\. 为什么执行：上一步问题、假设与本步目标

从Killed表面症状定位内核OOM，检查触发者和最终victim，避免误把cpptools认为被杀者。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
sudo dmesg -T | grep -Ei -C 4 \
  'out of memory|oom-kill|oom_reaper|killed process|memory cgroup' \
  | tail -n 100
```

### 3\. 命令本体和参数逐项解析

- **`sudo`**：以管理员权限读取限制访问的内核日志。

- **`dmesg`**：打印内核环形日志。

- **`-T`**：将内核启动以来的时间戳转换为可读本地时间。

- **`|`**：把上游标准输出交给下游标准输入。

- **`grep`**：按模式过滤日志。

- **`-E`**：扩展正则表达式，使\|代表任选匹配。

- **`-i`**：大小写不敏感。

- **`-C 4`**：命中行前后都保留4行辅助归因。

- **`单引号`**：保护管道符在grep内部作为正则或而非Shell管道。

- **`tail -n 100`**：只打印最后100行结果。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
[五 10月 16 11:12:37 2026] cpptools invoked oom-killer: gfp_mask=0x140cca(GFP_HIGHUSER_MOVABLE|__GFP_COMP), order=0, oom_score_adj=0
[五 10月 16 11:12:37 2026] CPU: 2 PID: 4639 Comm: cpptools Tainted: G           O       6.1.99-rk3576 #8
[五 10月 16 11:12:37 2026] [  11069]  1000 11069   825763   405548  3395584        0             0 asr_llm_tts_smo
[五 10月 16 11:12:37 2026] oom-kill:constraint=CONSTRAINT_NONE,nodemask=(null),cpuset=/,mems_allowed=0,global_oom,task_memcg=/user.slice/user-1000.slice/session-c3.scope,task=asr_llm_tts_smo,pid=11069,uid=1000
[五 10月 16 11:12:37 2026] Out of memory: Killed process 11069 (asr_llm_tts_smo) total-vm:3303052kB, anon-rss:628820kB, file-rss:712kB, shmem-rss:992660kB, UID:1000 pgtables:3316kB oom_score_adj:0
```

### 5\. 输出内容逐行/逐字段解释

- cpptools invoked表示触发内存分配失败并进入OOM路径的进程，不代表受害者。

- global\_oom与CONSTRAINT\_NONE表明系统范围内内存耗尽，非某容器独立限额。

- task=asr\_llm\_tts\_smo、pid=11069确定目标进程被选中。

- total\-vm=3303052kB是虚拟地址空间大小，不等于物理RSS。

- anon\-rss=628820kB匿名常驻内存；shmem\-rss=992660kB共享内存常驻页；file\-rss=712kB文件映射常驻。

- oom\_score\_adj=0代表未人为提高/降低该进程OOM优先级。

- 这是一段原始日志关键节选，更多Mali OOM notifier行并不等于GPU本身出错。

### 6\. 成功与失败判断、退出状态

grep有匹配时通常退出0；内核日志与Killed过程同时间可确认OOM因果。

### 7\. 环境影响、权限、风险及后续衔接

只读取内核日志；sudo不变更设备、驱动和配置。

### 8\. 最终工程结论

故障根因由推测升级为【实测确认】Linux global OOM。

### 本操作面试问题与回答

**问：为什么cpptools触发OOM却杀AI程序？**

答：OOM选择victim基于OOM score、进程内存规模和oom\_score\_adj等，不要求杀死触发分配失败的当前进程。

## 操作 26：3\.5：RSS排序确定VSCode Remote扩展宿主超大内存占用

### 1\. 为什么执行：上一步问题、假设与本步目标

找到非模型工作负载中最值得释放的内存，避免盲目改算法。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
ps -eo pid,ppid,stat,rss,%mem,comm,args \
  --sort=-rss | head -n 20
```

### 3\. 命令本体和参数逐项解析

- **`ps`**：查询当前进程快照。

- **`-e`**：选择全部进程。

- **`-o`**：按逗号列表自定义显示字段。

- **`pid`**：进程ID；ppid：父进程ID。

- **`stat`**：调度状态；Sl含可中断睡眠和多线程。

- **`rss`**：常驻物理内存，以KiB显示。

- **`%mem`**：RSS在物理RAM中的百分比。

- **`comm`**：进程短名；args：完整启动命令行。

- **`--sort=-rss`**：按RSS从大到小倒序排列。

- **`| head -n 20`**：只显示最多20行，限制终端输出。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
PID    PPID STAT   RSS %MEM COMMAND         COMMAND
4282   4231 Sl   1135096 28.4 MainThread    /home/cat/.vscode-server/.../server/out/bootstrap-fork --type=extensionHost ...
1765   1640 Sl+   131304  3.2 gnome-shell    /usr/bin/gnome-shell
4347   4259 Sl    100632  2.5 MainThread    /home/cat/.vscode-server/.../server/out/bootstrap-fork --type=agentHost ...
4231   4227 Sl     85424  2.1 MainThread    /home/cat/.vscode-server/.../server/out/server-main.js ...
4458   4282 Sl     65556  1.6 cpptools       /home/cat/.vscode-server/extensions/ms-vscode.cpptools-1.34.4-linux-arm64/bin/cpptools
```

### 5\. 输出内容逐行/逐字段解释

- 【真实实机输出节选】第一行extensionHost RSS=1,135,096KiB≈1\.08GiB，占总内存28\.4%。

- gnome\-shell=131,304KiB明显小于extensionHost。

- agentHost与server\-main\.js是另一批VSCode服务进程；不应仅按comm MainThread误识为普通线程。

- VSCode C\+\+扩展cpptools自己也驻留数十MiB。

### 6\. 成功与失败判断、退出状态

返回0和有效表头表示查询成功；RSS不能等同关闭后available一定增加同样多，因共享页和缓存。

### 7\. 环境影响、权限、风险及后续衔接

纯只读，无root。

### 8\. 最终工程结论

首选先关闭VSCode远程扩展宿主，而不是修改C\+\+模型大小。

### 本操作面试问题与回答

**问：RSS和VSZ如何区分？**

答：RSS是物理常驻页计数；VSZ是虚拟地址空间，可含未映射或共享映射。排查RAM用RSS、PSS与available综合判断。

## 操作 27：3\.5：Windows独立SSH连接避免关闭VSCode导致终端断线

### 1\. 为什么执行：上一步问题、假设与本步目标

关闭VSCode Server会中断其集成终端，因此先从Windows自带命令提示符建立与VSCode无关的SSH会话。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```PowerShell
ssh cat@192.168.10.27
```

### 3\. 命令本体和参数逐项解析

- **`ssh`**：Windows OpenSSH客户端，经TCP连接远端sshd。

- **`cat`**：RK3576 Debian登录用户名。

- **`@`**：分隔登录用户与目标主机地址。

- **`192.168.10.27`**：开发板eth0当时的IPv4地址；与本地网络有关，不是永久固定设备名。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
C:\Users\53009>ssh cat@192.168.10.27
Welcome to Debian GNU/Linux 12 (bookworm) (GNU/Linux 6.1.99-rk3576 aarch64)
Board Name:     LubanCat-3
System load:   0.09 0.23 0.16   Up time:       2:45 hours
Memory usage:  57 % of 3895MB   IP:            192.168.10.27
cat@lubancat:~$
```

### 5\. 输出内容逐行/逐字段解释

- 【真实输出节选】说明网络、ssh身份认证和远程登录成功。

- Windows上曾先错误输入ssh cat@ssh cat@192\.168\.10\.27并收到Could not resolve hostname ssh；修正后登录成功。

- Linux 6\.1\.99\-rk3576 aarch64表明目标系统架构；不能从登录成功推出音频或NPU功能正常。

### 6\. 成功与失败判断、退出状态

成功出现cat@lubancat Shell即SSH连接完成；失败可能timeout、Permission denied、Could not resolve hostname。

### 7\. 环境影响、权限、风险及后续衔接

在Windows建立一个SSH客户端连接，不影响板上已有模型或配置；不需要板上root。

### 8\. 最终工程结论

具备安全终止VSCode Server的独立操控通道。

### 本操作面试问题与回答

**问：为何先SSH再停VSCode？**

答：Integrated Terminal的PTY由VSCode Server持有，杀服务会使终端断开；独立ssh不依赖它。

## 操作 28：3\.5：关闭高占用远程服务后重新测量available

### 1\. 为什么执行：上一步问题、假设与本步目标

在Windows VSCode执行Remote\-SSH: Kill VS Code Server on Host后，对比实际RAM收益；注意此UI操作不是Linux命令。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
free -h
ps -eo pid,rss,%mem,comm,args --sort=-rss | head -n 12
```

### 3\. 命令本体和参数逐项解析

- **`free -h`**：human readable显示内存free、buff/cache、available和Swap。

- **`ps -eo`**：查看全部进程并指定字段。

- **`pid,rss,%mem,comm,args`**：对应ID、KiB RSS、RAM占比、短名、完整启动参数。

- **`--sort=-rss`**：按物理常驻内存降序。

- **`| head -n 12`**：截取表头和前11条进程。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
total        used        free      shared  buff/cache   available
内存：         3.8Gi       1.0Gi       2.5Gi        16Mi       328Mi       2.8Gi
交换：            0B          0B          0B
PID RSS %MEM COMMAND COMMAND
1765 133504 3.3 gnome-shell /usr/bin/gnome-shell
4347 119216 2.9 MainThread /home/cat/.vscode-server/... --type=agentHost ...
4231 118712 2.9 MainThread /home/cat/.vscode-server/... --type=extensionHost? [原始列表实际为server-main.js，非extensionHost]
2312 64948 1.6 gnome-software /usr/bin/gnome-software --gapplication-service
```

### 5\. 输出内容逐行/逐字段解释

- available由1\.6GiB上升至2\.8GiB，增加约1\.2GiB；used由2\.2GiB降为1\.0GiB。

- 曾占1\.08GiB的extensionHost已不在前列，但agentHost/server\-main等部分VSCode服务仍在。

- Swap仍为0；这不是创建Swap得到的收益。

- 【取自真实输出并节选】第三个进程真实args是server\-main\.js，不要据片段内问号把它改写为extensionHost。

### 6\. 成功与失败判断、退出状态

内存查询本身成功；收益应看available增量而非把原RSS作为绝对释放值。

### 7\. 环境影响、权限、风险及后续衔接

只读测试，远程VSCode会话此前通过用户UI停止；不改模型、内核与设备树。

### 8\. 最终工程结论

无需改动核心代码就创造了新的并发加载余量，应重新跑完全一致的测试。

### 本操作面试问题与回答

**问：为什么关闭IDE扩展比先换模型更合理？**

答：先消除非业务负载，以相同模型/代码复测，可实现单因素因果定位，避免同时改变算法与环境。

## 操作 29：3\.5：重新执行三模型联合推理并取得首次完整PASS

### 1\. 为什么执行：上一步问题、假设与本步目标

可用内存增加至2\.8GiB；保持完全相同模型与参数，以验证OOM是否由开发环境内存压力导致。

### 2\. 完整命令（原始 / 建议复现标注）

**【实际执行 / 实测】**

```Bash
LD_LIBRARY_PATH="$RUNTIME/lib:$RKLLM_LIB${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" \
RKLLM_LOG_LEVEL=1 \
./build/asr_llm/asr_llm_tts_smoke \
  "plughw:1,0" \
  "$ASR_MODEL" \
  "$VAD" \
  "$MODEL" \
  "$KOKORO_MODEL" \
  "plughw:1,0" \
  12 \
  2 \
  17
```

### 3\. 命令本体和参数逐项解析

- **`LD_LIBRARY_PATH`**：把RUNTIME/lib与RKLLM\_LIB置于动态链接器优先搜索路径。

- **`${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}`**：原变量存在且非空时追加旧值，否则不引入尾随路径。

- **`RKLLM_LOG_LEVEL=1`**：RKLLM运行日志等级。

- **`./build/asr_llm/asr_llm_tts_smoke`**：Stage3\.5集成入口可执行文件。

- **`plughw:1,0（首）`**：ALSA USB音频Capture PCM。

- **`$ASR_MODEL`**：SenseVoice INT8模型和tokens目录。

- **`$VAD`**：Silero模型路径。

- **`$MODEL`**：Qwen2\.5 RKLLM W4A16模型。

- **`$KOKORO_MODEL`**：Kokoro v1\.1多语言TTS目录。

- **`plughw:1,0（末）`**：ALSA USB播放PCM。

- **`12`**：录音窗口秒，必须在Listen后讲话。

- **`2`**：Kokoro的CPU推理线程数。

- **`17`**：speaker\_id，对应测试选中的zf\_024。

### 4\. 终端实际返回/未保存事实

**【真实实机输出】**

```Plaintext
[Init] Loading RKLLM...
I rkllm: rkllm-runtime version: 1.3.1, rknpu driver version: 0.9.8, platform: RK3576
I rkllm: loading rkllm model from /home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm
I rkllm: rkllm-toolkit version: 1.2.3, max_context_limit: 4096, npu_core_num: 2, target_platform: RK3576, model_dtype: W4A16
I rkllm: Enabled cpus: [4, 5, 6, 7]
I rkllm: Enabled cpus num: 4
[Init] Loading SenseVoice...
[Init] Loading Kokoro...
/k2-fsa/sherpa-onnx/sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93 Unknown token: ❓
[ALSA config] buffer_frames=12000 period_frames=3000 start_threshold=6000 buffer_ms=500
[Listen] 12 seconds. Ask ONE short text question and pause.
[VAD] Speech #1 duration=0.97 s
[ASR] Segment #1: 你是谁 | latency=454.935 ms | RTF=0.469005
[Timing] Segment #1 endpoint_est_ms=607.622 vad_to_queue_ms=0.000333 queue_wait_ms=0.246216 preprocess_ms=0.000906 asr_wall_ms=454.979 total_est_ms=1062.85

[ASR->LLM #1] 你是谁

[LLM #1] 我是Qwen，阿里云的超大规模语言模型。I rkllm: --------------------------------------------------------------------------------------
I rkllm:  Model init time (ms)  5220.23
I rkllm:  Stage         Total Time (ms)  Tokens    Time per Token (ms)      Tokens per Second
I rkllm:  Prefill       427.33           44        9.71                     102.97
I rkllm:  Generate      1312.83          12        109.40                   9.14
I rkllm:  Peak Memory Usage (MB)
I rkllm:  2052.37

[LLM done #1] success=true queue_ms=0.132614 first_text_ms=451.464 latency_ms=1764.46
[ALSA] XRUN=0 Suspends=0 Recoveries=0 RecoveryFailures=0
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[Main] waiting for 1 TTS task(s)...
[ALSA write] submitted_frames=124695 state=RUNNING
[TTS done #1] success=true queue_ms=0.18683 synth_ms=25701.4 audio_sec=5.19562 playback_ms=5236.56 xruns=0 asr_text_to_end_ms=32703.1

=== ASR -> LLM -> TTS summary ===
VAD segments: 1
ASR recognized: 1
Audio queue dropped: 0
LLM accepted/completed/success/failed/rejected: 1/1/1/0/0
TTS accepted/completed/success/failed/rejected/empty: 1/1/1/0/0/0
Skipped VISION: 0
PASS
```

### 5\. 输出内容逐行/逐字段解释

- RKLLM和SenseVoice、Kokoro进入初始化，Kokoro词典未知emoji是非致命警告；后来整体PASS。

- ALSA buffer=12000帧、period=3000帧、阈值6000帧，24kHz时分别500、125、250ms。

- VAD语音片段0\.97秒；ASR墙钟454\.935ms，RTF=0\.469005=推理/音频时长。

- Timing total\_est\_ms≈1062\.85包含语音终点估计及ASR排队、预处理等，不是“从开始说话到耳机出声”。

- LLM首文本451\.464ms、总推理1764\.46ms；Prefill 44 token/427\.33ms，Generate12 token/1312\.83ms，9\.14token/s。

- RKLLM报告Peak Memory Usage=2052\.37MB，非整个系统RSS，也非全部模型之和。

- TTS synthesized 25,701\.4ms，输出124695帧/24000≈5\.1956秒，实际音频播放5236\.56ms。

- TTS RTF=25\.7014/5\.19562≈4\.95；是性能主瓶颈。

- asr\_text\_to\_end\_ms=32703\.1ms从ASR文本回调到音频播放完毕，不包括录音与ASR。

- 11次waiting约每2s打印一次，并不表示卡死；TTS尚在CPU合成。

- XRUN=0且audio queue dropped=0，LLM/TTS任务accepted/completed/success均1，失败为0。

- PASS是本轮软件验收成功；用户后续确认耳机完整播放，没有断句。

### 6\. 成功与失败判断、退出状态

退出码来自PASS成功路径为0；编译成功仅是前提，实际要看所有模型推理及耳机音频是否完整。

### 7\. 环境影响、权限、风险及后续衔接

真实占用NPU、CPU、ALSA USB capture/playback、数GiB RAM；不创建模型文件或更改DTS。

### 8\. 最终工程结论

第3阶段功能闭环真实通过，性能瓶颈Kokoro RTF≈4\.95；一次短时PASS不证明长期可靠或低延迟。

### 本操作面试问题与回答

**问：为什么总耗时32\.7秒不能直接当端到端响应时间？**

答：这个计时从ASR文本回调开始，不含录音、VAD检测、ASR本身。且终点是整段音频播放完，不是首次出声，两种延迟需要分别打点。

**问：TTS能不能靠Worker异步直接加速？**

答：Worker将耗时操作移出ASR/LLM回调，改善并发与主线程响应性，但单条TTS ONNX实际合成仍耗25\.7秒，异步不等于推理加速。

### 本操作对应的完整源码与逐句解读

下方第九篇逐字收录以下源文件并附独立行级解读，避免将同一完整源码重复印刷造成文档臃肿；使用标题中的真实文件路径定位源代码。

- `src/audio/asr_llm_tts_smoke.cpp`（【源码可确认】最终压缩包版本，正文第九篇源码附录可完整检索）

## 操作 30：3\.5：实听与端到端闭环验收结果记录

### 1\. 为什么执行：上一步问题、假设与本步目标

终端PASS只是软件事件，必须补上用户实际听感来确认耳机完整播放，而不是仅提交了PCM。

### 2\. 完整命令（原始 / 建议复现标注）

**【用户实听验收；命令为建议记录，未实际执行】**

```Bash
printf "%s\n" "听感验收由实机用户现场观察，不是Shell自动测量"
```

### 3\. 命令本体和参数逐项解析

- **`printf`**：打印指定格式字符串的Shell命令，示例仅用于记录方式，不是历史执行命令。

- **`%s`**：字符串格式占位符。

- **`\n`**：换行转义序列。

- **`双引号`**：让空格/中文作为一个完整参数。

### 4\. 终端实际返回/未保存事实

**【真实用户反馈 \+ 命令未执行标识】**

```Plaintext
【用户真实口头验收】“完整的说出了，就是等待的时间比较长”。
【建议记录方式的命令，未实际执行；无历史命令输出】
```

### 5\. 输出内容逐行/逐字段解释

- 用户听到完整句“我是Qwen，阿里云的超大规模语言模型”，无截断报告。

- 未保存录音、波形或声音文件，不可假定存在波形客观质量评测。

### 6\. 成功与失败判断、退出状态

实听完整 \+ TTS done success=true \+ XRUN=0 \+ PASS为单轮功能验收；printf自身与音频功能无关。

### 7\. 环境影响、权限、风险及后续衔接

建议记录命令仅写终端，不需root、不改配置。

### 8\. 最终工程结论

音频输出已由人耳验证完整，但听感等待长；后续优先TTS推理优化。

### 本操作面试问题与回答

**问：为什么需要人工听感验收？**

答：驱动正常返回和snd\_pcm\_drain只说明数据提交/耗尽，错误路由、静音或音量异常可能使人耳无可用声音；人工验收提供功能层证据。

## 操作 31：3\.5：创建Stage3 PASS源码压缩备份

### 1\. 为什么执行：上一步问题、假设与本步目标

阶段三PASS后，备份最终源码供恢复和源码取证；板载剩余1\.1GB，不应纳入模型权重和构建缓存。

### 2\. 完整命令（原始 / 建议复现标注）

**【上传压缩包实物可证；命令为历史建议且缺少原终端输出】**

```Bash
cd "$HOME/projects/RK3576"
BACKUP="$HOME/projects/RK3576/rk3576_multimodal_stage3_pass_$(date +%Y%m%d_%H%M).tar.gz"
tar -czf "$BACKUP" \
  --exclude='rk3576_multimodal/build' \
  --exclude='rk3576_multimodal/.git' \
  --exclude='*.onnx' \
  --exclude='*.rkllm' \
  --exclude='*.wav' \
  --exclude='*.pcm' \
  --exclude='*.bak' \
  rk3576_multimodal
ls -lh "$BACKUP"
```

### 3\. 命令本体和参数逐项解析

- **`cd`**：切换到父目录，使tar归档路径有稳定的rk3576\_multimodal/前缀。

- **`BACKUP=`**：Shell变量保存输出归档全路径。

- **`$(date +%Y%m%d_%H%M)`**：命令替换插入年月日\_时分时间戳，防止覆盖。

- **`tar`**：归档工具。

- **`-c`**：新建归档。

- **`-z`**：使用gzip压缩。

- **`-f`**：紧跟输出文件名。

- **`--exclude`**：排除匹配路径或通配符文件。

- **`build`**：缓存和编译产物；\.git：Git对象历史；onnx/rkllm：模型权重。

- **`*.wav/*.pcm`**：音频测试产物；\*\.bak：备份临时文件。

- **`ls -lh`**：列出生成文件及可读大小。

### 4\. 终端实际返回/未保存事实

**【归档实物检查结论；非原命令实测输出】**

```Plaintext
【当前聊天未保存tar命令真实终端回显】
【归档实体已上传并实际检查】rk3576_multimodal_stage3_pass_20261016_1124.tar(1).gz，文件约148KiB，包含 src/audio/asr_llm_tts_smoke.cpp 等源码、CMakeLists.txt 与部分reports。
```

### 5\. 输出内容逐行/逐字段解释

- 压缩包真实存在并能被tar读取；文件名时间戳1124不证明每条建议命令逐字执行。

- 归档大小小因为排除模型权重和编译缓存。

- 包含reports不等于每个历史终端命令日志都完整保存。

### 6\. 成功与失败判断、退出状态

归档能列出目录树并取出源码是实际可用标准；gzip CRC另可使用gzip \-t检查。

### 7\. 环境影响、权限、风险及后续衔接

会生成tar\.gz文件消耗eMMC空间，不删除原目录；不需root；备份仍位于同盘，建议拷贝到Windows。

### 8\. 最终工程结论

得到真实PASS版本源码基线，但恢复后须重新配置模型权重/库和CMake build。

### 本操作面试问题与回答

**问：为什么不把build一起打包？**

答：产物受编译器、动态库、路径和ABI影响，复现性重点是源码\+CMake\+依赖版本\+模型路径；build重建更可靠。

# 第三篇 · 系统级与源码级底层技术机制

## 1\. ALSA PCM与USB音频驱动的调用链

本阶段的`AlsaPlaybackService::open()`并不直接发出原生Linux `open('/dev/snd/...')`；它调用`libasound` 的`snd_pcm_open()`，再通过`set_params`协商`SND_PCM_FORMAT_S16_LE`、交错帧、24kHz单声道。ALSA用户空间库负责设备名解析（`plughw:1,0`）、格式插件与参数处理；内核ALSA PCM/USB Audio驱动负责实际USB等时流与DMA/URB调度。`snd_pcm_writei` 的返回成功帧数不等于“用户听到了声音”，所以要用`drain()`配合实听。

`float` PCM一般表示归一化音频幅值，播放端通过`std::isfinite`过滤NaN和Inf，对\[\-1,1\]饱和截幅，然后舍入至16位有符号整数。S16\_LE中的S代表signed，16为每样本16bit，LE为little endian；一个声道且采样率24kHz时，每秒音频约48,000字节裸数据。`snd_pcm_writei`按**帧数**返回，单声道一帧=1个采样，两声道一帧=2个采样；不可把字节数错传为帧数。

**缓冲推导**：实测`buffer_frames=12000`、`period_frames=3000`、`start_threshold=6000`，采样率24kHz，分别是500ms、125ms、250ms。缓冲增加可以降低XRUN风险，但同时可能增加启动延迟。`EPIPE`表示PCM发生underrun/overrun，`snd_pcm_recover()`仅尝试恢复状态，不意味着没有发生XRUN。项目曾因缓冲设置发生播放欠载，修复后独立播放与联合验收均`xrun_count=0`。

## 2\. Sherpa\-ONNX的C ABI、RAII封装与生命周期

`TTSService`通过Sherpa C API构建Kokoro离线合成器；C API以指针、整数、C字符串表示状态，C\+\+封装负责把返回值转成`TTSAudio { vector<float> samples; sample_rate; synthesis_ms; }`。RAII把资源回收绑定对象生存期：成功初始化持有SDK句柄，错误路径不残留未销毁指针；每次生成SDK缓冲后复制到C\+\+ vector，再释放SDK自身持有的GeneratedAudio。必须确保先释放所有引用生成器的TTS工作线程，后释放生成器本身。

Kokoro模型目录中有`model.onnx`、`voices.bin`以及词典等配套资源。日志中`Unknown token: ❓`是词典预处理的非致命告警，本轮后续成功合成，不能把所有Unknown token都视为永远无影响。模型录入的`speaker_id=17`与特定`zf_024`声线的对应来自当次测试；不同模型版本说话人索引可能变化。

## 3\. 有界FIFO、背压与停止语义

`LLMWorker`和`TTSWorker`各自维护工作线程、有界FIFO队列、互斥锁和条件变量。队列容量2意味着**等待中的**任务最多2个；正在执行的任务通常单独计数，不等于系统总任务最大2。`submit()`成功返回Accepted，满时QueueFull，停止后NotRunning，这是明确的背压，而不是无限申请内存。异步架构使ASR/LLM回调很快返回，但**无法自动降低模型单次推理Wall time**。

`requestStop()`负责设置退出意向，`join()`负责等待工作线程完全退出；前者不等于同步关闭完成。停止时未执行任务可能带取消结果回调；成功提交后的回调原则上应 exactly\-once。队列容器和状态需同一mutex保护，先入队后notify，否则消费者可能错过状态变化。条件变量等待使用带谓词的`wait()`或`wait_for()`抵抗虚假唤醒，避免忙轮询。

## 4\. 回调链与计数竞态：为什么先提交TTS后标记LLM完成

`ASRWorker`把文本交给`LLMWorker::submit(id,prompt,chunk,done)`。LLM推理完成后，done回调先检查`InferenceResult.success && !text.empty()`，再`TTSWorker::submit`，最后更新`llm_completed`。主线程等待`llm_completed == llm_accepted`后关闭LLMWorker，此时才知道不会再有新的TTS请求。随后等待`tts_completed == tts_accepted`，再join并关闭播放、合成资源。

`accepted`可能在异步工作线程回调前后增减，如果一个非常快的任务在`submit()`返回前结束，最终计数仍会正确，前提是所有计数受同一个`state_mutex`保护并且主线程只在ASRWorker退出后判断稳定总数。日志采用另一把`print_mutex`，应避免同一线程同时以相反顺序获取state/print两把锁。`std::shared_ptr<bool>`让流式文本前缀标志随异步回调安全存活，但共享所有权≠自动线程同步；本项目只有LLM worker串行操作其标志。

**注意最终源码实际超时策略**：`wait_for_jobs()`设置180秒LLM和600秒TTS的完成等待上限；超时调用`requestStop`后`join()`仍可能被正在运行的SDK长调用阻塞。这个上限并非强制中断NPU/ONNX的实时超时，不能夸大为硬实时保证。

## 5\. 内核OOM Killer与观测指标

`free -h`中available比free更适合估算模型加载可用余量；`ps RSS`是进程常驻页不保证唯一占有；`total-vm`包含虚拟映射，不能当物理消耗；RKLLM所报`Peak Memory Usage=2052.37 MB`属SDK统计口径，不能简单等于整个Linux进程PSS。内核输出`global_oom`、`task=asr_llm_tts_smo`、`Killed process ...`形成OOM确认链条。`cpptools invoked oom-killer`表示申请失败者是cpptools，受害者则是内核根据打分选出的AI进程。停止VSCode高占用extensionHost后available由1\.6Gi到2\.8Gi，在其他条件不变情况下完整PASS；说明非业务内存压力是此次失败的重要可操作因素。

## 6\. 真正的测量边界与优化优先级

实时因子RTF=计算墙钟时间/音频时长。ASR 0\.469意味着处理0\.97秒语音仅需约0\.455秒；Kokoro 4\.95意味着合成5\.2秒音频用了25\.7秒，尚不能实时。LLM首次文本451\.464ms，完整推理1764\.46ms；Prefill吞吐102\.97 tokens/s、Generate 9\.14 tokens/s是不同计算阶段，不能混为一个吞吐。`asr_text_to_end_ms=32703.1`只涵盖ASR输出后到播放结束；不是完整“开口→首声”延迟。目标优化应先实现真实TTFA（time\-to\-first\-audio）埋点与Kokoro线程、量化/轻量模型、分句推理对比；不能把异步队列已实现夸为合成性能已优化。

## 7\. 常用 C\+\+ 语法解剖

- `std`为C\+\+标准库命名空间，`::`为作用域解析符；`std::mutex`声明互斥量类型。

- `std::lock_guard<std::mutex> lock(state_mutex);`：`lock_guard`是类模板，`<std::mutex>`是模板实参类型，`lock`是该模板实例的局部变量，括号内`state_mutex`引用现有mutex，构造时锁定，当前作用域结束析构释放。比手写lock/unlock更能抵抗return与异常。

- `std::unique_lock<std::mutex> lock(state_mutex);`：同样拥有互斥锁，但支持临时`unlock()`，使等待进度日志在不持有state\_mutex的情况下写入。

- `std::unique_ptr<T>`表示独占所有权，通常不能复制但能移动；`std::make_unique<RKLLMBackend>()`创建派生类，并传给持有接口的`LLMEngine`实现多态策略注入。

- `std::shared_ptr<T>`使用共享引用计数延长对象生命周期；它不是线程安全的业务数据容器。`std::make_shared<bool>(false)`为每条LLM流的输出前缀创建计数标志。

- `std::move(x)`只是将表达式强制转换为右值引用，实际是否转移缓冲需看目标类型移动构造/移动赋值；已移动对象仍然有效但内容可能未指定。

- `[&, prefix_printed, question_at] (...) { ... }`为捕获lambda：`&`让其他被使用的外围对象按引用捕获，两个显式列出的对象按值复制；若异步回调晚于外围变量析构就可能悬空，因此停止/join顺序必不可少。

- `const std::string& text`不复制字符串且不允许通过该引用修改内容，生命周期由调用方管理。`std::string text`按值接收可以在函数中移动所有权。

- `std::condition_variable::wait_for(lock, duration, predicate)`在等待阶段释放mutex，苏醒后重新上锁、重新检查谓词；只有notify并不代表任务成功。

- `std::chrono::steady_clock`提供单调时间基准，适合延迟/吞吐测量；不要用墙钟时间戳做执行耗时差值。

- `std::uint64_t`为明确64位的无符号整数，多线程共享时依旧需要mutex或atomic；`atomic`对单字段适合但不能代替多个计数一致性的临界区。

# 第四篇 · 真实性能测试与统计边界

## 1\. PASS轮测量条件与结果

**【实际执行 / 实测】** 2026\-10\-16独立SSH，RK3576、Qwen2\.5\-1\.5B W4A16、SenseVoice INT8、Kokoro v1\.1 sid=17、TTS CPU线程2、HyperX `plughw:1,0`，录音窗口12秒，实际识别有效中文语音段1个，LLM请求1条，TTS请求1条，成功播放一次；音频时长5\.19562秒。**这不是持续运行负载测试，也不是P50/P95统计。**

|环节|指标与单位|数据|测量起止、局限|
|---|---|---|---|
|VAD|语音片段时长|0\.97 s|一段语音，不代表采集窗口总长|
|ASR|识别wall latency|454\.935 ms|SenseVoice单片段计时|
|ASR|RTF|0\.469005|语音识别walltime / 0\.97s；不是整体端到端RTF|
|VAD/ASR|total\_est\_ms|1062\.85 ms|含endpoint\_est\_ms=607\.622及任务队列等估计项|
|LLM|first\_text\_ms|451\.464 ms|首个文本输出，非耳机首次声音|
|LLM|latency\_ms|1764\.46 ms|完整LLM回答walltime|
|LLM|Prefill|427\.33ms / 44 tokens / 102\.97 tokens/s|Prefill与Decode吞吐口径不同|
|LLM|Generate|1312\.83ms / 12 tokens / 9\.14 tokens/s|单条问题，不能推出稳定峰值吞吐|
|RKLLM|Runtime所报Peak Memory|2052\.37 MB|由SDK输出；不是系统RSS/PSS|
|TTS|synthesis\_ms|25701\.4 ms|Kokoro完整离线合成一次|
|TTS|生成音频长度|5\.19562 s|124695 frames / 24000Hz|
|TTS|RTF（推导）|≈4\.946|25\.7014s/5\.19562s，明显慢于实时|
|ALSA|playback\_ms|5236\.56 ms|含设备播放耗时，不代表必须额外等待5秒才开始合成|
|用户可感知|asr\_text\_to\_end\_ms|32703\.1 ms|ASR文本结果产生→播完，不含录音/ASR；未单独测首次出声|
|可靠性|xrun\_count|0|本次无ALSA播放欠载；不代表长期为0|
|可靠性|Audio queue dropped|0|本次队列无丢弃；不能保证高并发为0|
|任务结果|LLM 1/1/1/0/0；TTS 1/1/1/0/0|PASS|Accepted/Completed/Success/Failed/Rejected，TTS另Empty=0|

## 2\. 计算口径逐项审查

- **ASR RTF**：0\.454935s/0\.97s≈0\.469；音频长度取日志小数近似，精度有限。

- **TTS RTF**：25\.7014s/5\.19562s≈4\.946，代表合成慢于实时约5倍，但并非整个APP总时延倍数。

- **音频时长**：124695帧/24000帧每秒≈5\.196秒，单声道才与sample count直接相同。

- **统计窗口**：32703\.1ms涵盖LLM 1764\.46ms、TTS合成25701\.4ms、播放5236\.56ms及小幅排队/回调开销，不能简单认定零额外开销，也不包括麦克风起声→ASR结果。

- **占比**：25\.7014/32\.7031≈78\.6%；因此先优化TTS比先优化454\.9ms ASR更有效。

- **样本局限**：一条短文本、一次播放、一个sid、TTS 2线程；没有置信区间、P95、持续功耗与热态/冷态多轮对照。

## 3\. 以后验证优化是否真的有效

**【建议复现实验，尚未执行】** 每组固定相同文本、音色、线程绑定、室温/负载条件，独立测试至少30次，分别记录模型冷启动、热态TTFT、首个PCM样本产生、ALSAPCM首帧write完成、听感首声、整句播放结束、RSS/PSS/内存峰值、CPU占用、NPU负载、XRUN、队列满率。记录P50、P95、最大、标准差并保存原始CSV；若换INT8模型须同时验证声线自然度与识别/合成正确性，避免以音质严重下降换取虚假加速。

# 第五篇 · 已遇到的错误、根因分析与可复现排障

## 故障1：CMake 找不到目标 `asr_llm_tts_smoke`

**实际现象**：源码1077行已用nano写入；`cmake -S . -B build/asr_llm`配置成功；`cmake --build ... --target asr_llm_tts_smoke --parallel 2`输出`gmake: *** 没有规则可制作目标“asr_llm_tts_smoke”。 停止。`。**原因**是当时`CMakeLists.txt`没有注册`add_executable(asr_llm_tts_smoke ...)`；`grep`无匹配，两个开关`BUILD_WITH_RKLLM=ON`及`ENABLE_SHERPA_ASR=ON`。按第二篇操作18、19追加目标并用`--target help`确认，之后链接成功。源码存在不意味着构建目标自动存在，CMake配置成功也不意味着所有期望目标都被定义。

## 故障2：第一次联合加载SenseVoice阶段出现“已杀死”

**实际现象**：RKLLM打印Runtime1\.3\.1、Driver0\.9\.8、W4A16、2 NPU Core；接着`[Init] Loading SenseVoice...`，Shell输出`已杀死`，还没执行Kokoro初始化。**明确根因**：`dmesg`显示`cpptools invoked oom-killer`及`global_oom`，最终`Killed process 11069 (asr_llm_tts_smo)`；匿名RSS628820kB、共享内存RSS992660kB。不能错误宣称cpptools是被杀者。分步骤使用`free -h`、`ps --sort=-rss`发现VSCode extensionHost RSS1135096KiB（约1\.08GiB），从独立Windows SSH终端停掉高占用远程VSCode服务，使available由1\.6GiB升到2\.8GiB。保持完全相同模型/CLI再次运行成功，说明内存压力是已验证关键因素。源码并未因此重写。

## 故障3：早期ALSA Playback XRUN（修复后正常）

**历史测试摘要**：独立TTS Playback初期发生欠载/`EPIPE`；修正libasound的PCM缓冲和start threshold后，实测`buffer_frames=12000 period_frames=3000 start_threshold=6000 buffer_ms=500`，后续有`[ALSA write] ... state=RUNNING`、`xrun_count=0`与用户实听。早期XRUN最原始的完整终端日志没有在当前归档中逐字保留，因此本段不会虚构具体早期错误行或错误次数。详细代码见真实`src/audio/alsa_playback_service.cpp`。

## 故障4：Kokoro词表告警 `Unknown token: ❓`

**实际现象**：加载时由`sherpa-onnx/csrc/lexicon.cc:ConvertTokensToIds:93`打印未知token。**验证结果**：其后仍产生124695帧PCM、TTS Done success=true、最终PASS、用户完整听到句子，因此**在此版本/这次输入中非致命**。但并不保证更复杂文本、emoji不会造成发音退化，后续应整理前端文本归一化与token coverage测试。

## 故障5：音频回应等待过久

**实际现象**：耳机确实完整播出回答，但主线程每2秒打印`waiting for 1 TTS task(s)...`多次。**根本原因是性能而非死锁**：`TTSWorker`仍在CPU运行离线Kokoro合成，实测`25701.4ms`生成`5.19562s`声音，RTF≈4\.95，随后正常播放约5\.24秒。异步队列只改善其他线程响应，不直接加速ONNX计算；后续通过模型更换、量化、分段/流式、线程profiling优化，不应为了赶进度声称实时交互已实现。

## 当前风险（尚未发生，不应伪装为历史故障）

短窗口内LLM或TTS队列连续QueueFull、热插拔声卡导致编号从1变化、长期运行内存碎片/缓慢泄露、回调与关闭交织造成死锁、过长文本导致极慢合成，这些是**潜在风险**。应设计独立测试复现，禁止当作本轮真实出错经验。当前C\+\+联调默认`plughw:1,0`运行成功，不代表所有重启后USB卡号固定。

# 第六篇 · 大厂高频面试题（26题，完整参考答案）

## 1\. 整体系统、推理与软件分层

### Q1：请从一次讲话开始解释整个RK3576语音助手的数据链。

**答**：HyperX USB麦克风通过内核USB Audio/ALSA驱动与用户态libasound提供16kHz单声道样本；VAD线程利用Silero对实时帧判断端点，把完整语音段写入`AudioBufferQueue`。ASRWorker在CPU运行SenseVoice，得到“你是谁”；IntentRouter判断为Text请求；LLMWorker提交Qwen2\.5 W4A16给RKLLM Runtime与NPU驱动，完成回调得到`result.text`；TTSWorker将文本交给CPU Kokoro，得到24kHz float32 PCM；ALSA Playback转换为S16\_LE，通过PCM缓冲写入USB耳机，并等待drain。每个Worker的生命周期由主线程管理，日志中的最终PASS说明任务计数闭合，用户现场听到了完整回答。**追问**：内核与用户态分界是`libasound`和`librkllmrt.so`之下，本项目没有重写驱动。

### Q2：本项目到底哪些模块是自己写的，哪些来自SDK？

**答**：工程自建ASR/LLM/TTS服务封装、ASR/VAD/LLM/TTS Worker调度、界限队列、状态计数、生命周期、ALSA Playback PCM转换与日志/测试入口。底层SenseVoice、Kokoro推理算子来自sherpa\-onnx/ONNX Runtime，Qwen NPU算子由RKLLM Runtime执行，声卡是内核ALSA驱动。可以陈述“实现了跨CPU/NPU的异步流水线集成与故障定位”，不能自称开发了RKNPU内核驱动。

### Q3：LLM使用NPU、ASR/TTS使用CPU的理由？

**答**：本次SenseVoice和Kokoro选择sherpa\-onnx aarch64 CPU运行库，Qwen使用Rockchip打包的RKLLM W4A16模型；NPU Runtime负责大模型算子在NPU计算，ASR/TTS使用CPU可快速复用已验证的ONNX模型。实际收益在于跨设备分工，但模型权重都占板上共享物理RAM，资源压力不会因跑在NPU就自动消失。

### Q4：W4A16与INT8如何理解？

**答**：W4A16表示权重4bit、激活16bit的特定模型量化配置，减少模型权重存储/带宽；SenseVoice INT8通常表示部分量化张量为8bit。量化细节取决于算子和runtime，并非所有数据都恰好4/8bit，亦不能简单按位宽直接宣称速度提高4倍。实际格式来自RKLLM日志model\_dtype: W4A16。

### Q5：你如何证明不是写了一个假Demo？

**答**：真实证据包括SenseVoice将0\.97秒人声识别为“你是谁”、LLM推理产生非固定答案、真实NPU Runtime提供token阶段时延、Kokoro生成124695帧音频、ALSA设备state=RUNNING并XRUN=0、最终LLM和TTS统计1/1/1/0/0及用户完整听到回答。这比仅模型load成功更有说服力，但只有一次测试，稳定性不能夸大。

## 2\. C\+\+与并发机制

### Q6：为什么使用`std::lock_guard<std::mutex>`？

**答**：`std`是标准库命名空间；`lock_guard`是RAII类模板；`<std::mutex>`明确互斥锁类型；局部变量`lock(state_mutex)`在构造时调用mutex\.lock，在其作用域结束时析构解锁。可以避免多return或异常导致忘记unlock。`lock`只是对象名称，括号参数是被操作的mutex对象而不是业务数据。

### Q7：`unique_lock`与`lock_guard`如何选择？

**答**：简单短临界区用lock\_guard，开销小、表达清楚。需要临时unlock、relock或condition\_variable等待用unique\_lock。项目`wait_for_jobs()`在等待统计期间使用unique\_lock，向控制台打印等待信息之前先unlock，降低锁交叉依赖风险。

### Q8：为什么条件变量必须带谓词？

**答**：condition\_variable可以虚假唤醒，notify只是重新检查时机，并不保证任务已经完成。谓词`completed >= accepted`位于state\_mutex保护下反复判断，wait期间自动释放锁让工作线程更新计数，苏醒时重新获取锁，防止忙等待和遗漏竞争状态。

### Q9：什么时候`std::shared_ptr<bool>`仍然不安全？

**答**：shared\_ptr保证共享控制块引用计数生存期；不能保证被指向的bool并发读写是原子的。如果多个工作线程同时写`*prefix_printed`需要额外同步。这里LLMWorker流式回调被串行处理，打印时还持有print\_mutex，避免不同请求文本交错。

### Q10：Lambda `[&,prefix_printed,question_at]`的风险？

**答**：`&`默认按引用捕获其余外部变量，两个显式名字按值捕获。异步回调持有外部`state_mutex`、计数和服务对象的引用，如果主函数先退出导致悬空引用就是use\-after\-free。程序先等待计数、requestStop并join所有Worker，最后才销毁服务和状态对象，这是引用安全的核心。

### Q11：`requestStop()`为什么不能代替`join()`？

**答**：requestStop只设停止意向并唤醒等待者，正在调用ONNX/RKLLM的线程未必马上结束。join阻塞调用方直到线程结束，从而建立退出同步点；如先销毁TTSService/ALSA，Worker仍访问它会触发use\-after\-free或设备访问失败。

### Q12：有界FIFO为什么重要？

**答**：语音请求可能快于生成/播放速度，Kokoro RTF约4\.95意味着积压会加重。如果使用无限任务队列，内存可持续增长并触发OOM。capacity=2的等待队列通过QueueFull显式反馈背压，同时保持异步提交不无限阻塞。并不代表系统总任务永远最多两条，因为运行中的任务另计。

### Q13：先标记LLM completed再提交TTS有什么竞态？

**答**：主线程可能看到全部LLM完成并停止TTSWorker，而仍在运行的LLM done回调尚未来得及提交文本，导致NotRunning或丢回答。应在LLM done中先调用`tts_worker.submit`并记下状态，再受锁保护增加llm\_completed；主线程仅在ASRWorker退出且所有LLM完成后进入TTS耗尽阶段。

### Q14：RAII是什么，在哪些地方体现？

**答**：RAII将资源获取绑定对象初始化，将释放绑定析构，常用于mutex guard、vector、unique\_ptr和工作线程拥有者。TTSService封装Sherpa C API的句柄及GeneratedAudio销毁流程；ALSA PlaybackService封装snd\_pcm\_open/close。析构顺序依赖声明反序，但显式stop/join/close可把安全关系写得更清楚。

## 3\. ALSA、数据与性能

### Q15：S16\_LE、24kHz、mono、interleaved什么意思？

**答**：S代表有符号PCM样本，16表示16比特即每样本2字节，LE表示低有效字节先存储，24kHz是一秒24000个采样点，mono为单声道。interleaved对多声道表示LRLR交错；单声道等价于连续样本。一秒单声道S16\_LE音频48kB不计容器头。模型实际输出float32，必须转换后才能按协商格式提交。

### Q16：ALSA buffer与period有什么区别？

**答**：buffer是驱动/用户态交互PCM环形缓冲能容纳的总帧数，period是驱动通知或处理进度的典型批量单位。本次12000/3000帧，在24kHz下分别500ms/125ms。`start_threshold=6000`对应积累250ms数据才启动，有助于减少播放开头欠载但可能带来额外延迟。

### Q17：EPIPE与XRUN怎么排查？

**答**：当ALSA播放硬件消费速度超过应用送入速度，会发生underrun，常见返回`-EPIPE`并进入XRUN状态。读取ALSA状态、使用`snd_pcm_recover`恢复，并记录次数；通过增大buffer、设置合适start\_threshold、避免在播放循环中执行重CPU任务改善。项目改成12000帧buffer、3000 period、6000阈值后独立及联合日志均无XRUN。

### Q18：为什么音频播放前必须处理float NaN和幅值？

**答**：生成模型音频是float数组，理论范围常\[\-1,1\]。NaN/Inf参与取整会出现不可移植或异常行为，超过范围时直接缩放可能溢出、失真。先isfinite，再clamp并乘以int16幅值、lround舍入，再snd\_pcm\_writei按帧数写入。

### Q19：RTF怎样算，为何TTS是主要瓶颈？

**答**：RTF=推理耗时/生成音频播放时长。SenseVoice约454\.935ms/0\.97s=0\.469，快于音频实时播放；Kokoro 25\.7014s/5\.19562s≈4\.95，相当于生成5秒声音要等约26秒。单次例子里LLM只1\.764s，因此优先改TTS。

### Q20：P50/P95延迟现在能报吗？

**答**：不能。本轮完整闭环只有1条成功语音请求，没有足够样本构成稳定分位分布。应设计至少几十次多长度输入，统一起止时间戳，报告median、P95、最大值及内存峰值。不能把单次32\.703s包装成P95或均值。

### Q21：TTFT和首次出声延迟是不是一样？

**答**：不是。TTFT通常指模型生成第一个文本Token/片段的时延，本次first\_text\_ms=451\.464ms；首次出声还要等TTS接收文本、合成首段音频、PCM达到启动阈值并真正由耳机出声。当前程序先整句合成再写ALSA，TTFA尚无打点，因此不能准确报告。

### Q22：异步Worker为什么没有明显减少用户等待？

**答**：异步把耗时工作放到独立线程，防止录音、ASR和主线程阻塞，但Kokoro仍是整句合成、完整播放，25\.7秒CPU推理不因线程封装而缩短。改善首次响应需要支持分句/流式合成、模型量化或更快backend，同时控制内存和音质。

## 4\. Linux OOM、Runtime和工程实战

### Q23：OOM日志中`cpptools invoked oom-killer`究竟代表什么？

**答**：它是触发分配失败并调用OOM逻辑的当前进程，并非最终被杀对象。真正的victim在`task=asr_llm_tts_smo,pid=11069`及`Killed process`行；`global_oom`说明系统全局内存不足。OOM Killer依据任务内存消耗及OOM打分选择受害者，触发者和受害者可不同。

### Q24：RSS、available、RKLLM peak memory为何不同？

**答**：RSS是进程已驻留物理页，可能包含共享映射；available是系统级估计的可供应用分配页量；RKLLM自己的Peak Memory Usage是SDK特定口径，可能含其管理的NPU/模型内存，不能无依据当作进程RSS。排查使用free、ps和OOM日志三者交叉印证。

### Q25：一次OOM你怎样进行工程定位？

**答**：首先停止重复启动，以免内存反复抖动；使用dmesg确认global OOM与被杀PID；free判断available和Swap；ps按RSS找出非业务峰值，发现VSCode extensionHost约1\.08GiB。通过独立ssh安全关闭VSCode服务，available由1\.6升到2\.8GiB，保持同一源码、模型、参数再次运行得PASS。这条“记录→假设→单因素改变→复测”是可解释的工程排障过程。

### Q26：如果面试官说“底层SDK都不是你写的”，怎样回答？

**答**：明确区分能力层次：“模型推理核与设备驱动确实由Rockchip和sherpa\-onnx实现，我主要工作是C\+\+服务封装、CPU/NPU跨Runtime协同、线程队列和生命周期安全、PCM格式处理、工程构建/调试以及真实性能Profiling；我排查过实际Linux global OOM并通过释放远程开发进程内存实现相同模型联合PASS。”不声称自己实现了RKNN算子、改写内核ALSA或优化了未量化的TTS速度。能进一步讲解每一个Worker、submit/Done回调、线程退出和缓冲区所有权。

# 第七篇 · 项目总结、履历用语与后续未完成事项

## 1\. 已实现且有真实证据的成果

- 嵌入式Linux Debian 12 / RK3576 / 4GiB级内存，真实USB耳麦端到端问答；ASR、LLM、Kokoro、ALSA在单C\+\+进程协同运转并输出PASS。

- `TTSService`封装sherpa\-onnx Kokoro模型，`AlsaPlaybackService`实现浮点PCM→S16\_LE转换及硬件播放、缓冲/XRUN处理；`TTSWorker`实现有界异步FIFO、拒绝/取消语义与安全join。

- 性能实测ASR 454\.935ms、LLM 1764\.46ms、TTS synth 25701\.4ms、音频播放5236\.56ms、从ASR文本到回答播放完32703\.1ms；XRUN=0、Dropped=0、LLM/TTS任务计数闭合。

- Linux全局OOM定位：dmesg确认victim PID11069；ps发现VSCode extensionHost RSS≈1\.08GiB；释放非模型工作负载使available由1\.6升至2\.8GiB，完全相同联调可复现一次PASS。

## 2\. 简历可使用的精确描述

> **RK3576 端侧多模态智能终端｜本地语音交互子系统（C\+\+17 / Linux / RKNPU / ALSA / Sherpa\-ONNX）**：集成Silero VAD、SenseVoice INT8 ASR、Qwen2\.5\-1\.5B RKLLM W4A16与Kokoro中文TTS，基于C\+\+有界队列、异步Worker及RAII实现语音识别→NPU语言推理→CPU语音合成→USB耳机播放的端到端闭环；真实设备实现单轮PASS、无音频XRUN/队列丢弃。通过内核OOM日志和RSS分析定位远程IDE内存压力，释放系统可用内存并恢复模型联合运行；建立ASR/LLM/TTS分段Profiling，为后续低延迟优化定位Kokoro RTF≈4\.95瓶颈。

请避免写“实现了自己的RKNPU驱动”“已达到实时语音对话”“成功完成长期稳定性测试”等目前没有证据的说法。

## 3\. 尚未验证或未完成的工作

- **TTFA**与真正“用户开口→首次播放”的全链路采样：当前没有实测，不得推断。

- 多轮持续运行、P50/P95、长期RSS/PSS及OOM回归压测：当前只有一次真实集成PASS。

- Kokoro优化：2/4线程、INT8或轻量后端性能/音质对照、分句合成与增量播放、speaker变化、一句长文本分段处理。

- 真实USB音频热拔插、设备编号变化、AudioCapture失败重启、自恢复、前后台播放争用。

- 多轮并发、背压统计、Worker超时后不可抢占ONNX调用等边界验证。

- 第四阶段Camera LatestFrameBuffer \+ VLM \+意图路由至语音回答，尚不能写为第三阶段完成。

# 第八篇 · 常用命令速查、术语表与完整复现路线

## 1\. 命令速查（这里只做索引；每条命令八要素解释请回看第二篇对应操作）

|场景|命令索引|来源/注意|
|---|---|---|
|检查内存|`free -h`|操作21，真实执行|
|检查根文件系统|`df -h /`|操作21，真实执行|
|模型路径设置|`SDK=...`、`RUNTIME=...`等|操作22，真实执行；新会话重设|
|模型资源可读|`for f ...; [ -r "$f" ]; ...; done`|操作23，真实执行|
|联合运行|`LD_LIBRARY_PATH=... ./build/asr_llm/asr_llm_tts_smoke ...`|操作24与操作30，真实执行|
|OOM诊断|\`sudo dmesg \-T|grep \-Ei \.\.\.\`|
|RSS排序|\`ps \-eo \.\.\. \-\-sort=\-rss|head \-n 20\`|
|Windows独立连接|`ssh cat@192.168.10.27`|操作27，真实执行；IP可能变化|
|源码归档|`tar -czf ... --exclude=...`|操作32，归档实物已证；原命令回显未保存|

**速查索引中的Shell省略号仅指向前面完整原命令，绝不可当作直接可执行命令。** 复现实验时使用第二篇完整命令代码块。

## 2\. 术语表

|缩写/术语|完整含义及本项目对应|
|---|---|
|ALSA|Advanced Linux Sound Architecture；USB PCM录制/播放驱动与libasound|
|PCM|Pulse\-Code Modulation；原始音频采样，float32或S16\_LE|
|VAD|Voice Activity Detection；Silero判断有声片段|
|ASR|Automatic Speech Recognition；SenseVoice转中文文字|
|LLM|Large Language Model；Qwen2\.5文本生成|
|TTS|Text\-To\-Speech；Kokoro生成音频|
|RKNPU|Rockchip Neural Processing Unit；RKLLM加速器硬件|
|UMD|User Mode Driver；本项目使用现有SDK/Runtime，不声称自研|
|KMD|Kernel Mode Driver；板载NPU驱动和ALSA驱动|
|Runtime|模型执行库与调度实现；librkllmrt\.so / sherpa\-onnx|
|RAII|Resource Acquisition Is Initialization；对象生命周期管理句柄/锁|
|FIFO|First In First Out；按提交顺序取任务|
|Backpressure|背压；通过QueueFull限制未处理任务积压|
|XRUN|PCM underrun/overrun导致音频断续，实测0|
|RSS|Resident Set Size；进程常驻内存页数|
|OOM|Out of Memory；Linux global OOM Killer实际杀过进程|
|RTF|Real\-Time Factor=计算耗时/音频时长；ASR0\.469，TTS4\.95|
|TTFT|Time To First Token/Text；LLM首次文本451\.464ms|
|TTFA|Time To First Audio；尚未测量|
|P95|95%样本延迟不超过该值；单次测试不能计算可靠P95|

## 3\. 零基础重建路径

先确认RK3576 Debian系统、USB耳机、网络与SDK及模型目录都在；从用户原始tar\.gz解压出`rk3576_multimodal`工程而非文档中的代码块；核对CMake开关和三个静态库目标；运行TTS单模块合成，再验证ALSA硬件播放和TTSWorker FIFO边界；随后在独立SSH环境下检查available、路径可读性，确保没有占用超过1GiB的远程IDE扩展宿主；运行Stage3\.5入口提出一次简短纯文本问题，留存VAD/ASR/LLM/TTS/ALSA日志、内核OOM记录、RSS以及最终PASS和人耳确认。**如果最终环境未安装模型与SDK，本源码归档本身无法直接执行；不要以文件缺失推断源码错误。**

## 4\. 源文件阅读路径

第一轮先读`include/audio/tts_service.h`和`src/audio/tts_service.cpp`，了解C API和RAII；第二轮读`include/audio/alsa_playback_service.h`、`src/audio/alsa_playback_service.cpp`，掌握PCM转换和缓冲；第三轮读`include/audio/tts_worker.h`、`src/audio/tts_worker.cpp`，掌握异步与背压；第四轮读`src/audio/asr_llm_tts_smoke.cpp`，从main、on\_text、LLM Done、TTS Done顺序逐句讲述整体链路。全部文件的原始版本及行级索引都收在第九篇。

# 第九篇 · 源码级附录（从用户上传 PASS 包原样抽取）

此附录全文嵌入用户真实源码，无任何伪造的“重写版本”。以下源码每一文件均包括绝对归档路径、职责、完整内容、语法精讲与可定位的行级索引；第三阶段文件与第一、二阶段复用接口分别标识。

## 真实源文件：`include/audio/tts_service.h`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/tts_service.h`。归档长度 **63 行**，SHA\-256 完整值 `f4a149ddf6f905670f04bb3dcb592e8802bd745028288d994cc2b763b7903c38`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "sherpa-onnx/c-api/c-api.h"

struct TTSAudio
{
    std::vector<float> samples;
    std::int32_t sample_rate = 0;
    double synthesis_ms = 0.0;
};

class TTSService
{
public:
    TTSService() = default;
    ~TTSService();

    TTSService(const TTSService&) = delete;
    TTSService& operator=(const TTSService&) = delete;
    TTSService(TTSService&&) = delete;
    TTSService& operator=(TTSService&&) = delete;

    // 新增 speaker_id，默认 0，保持旧调用兼容。
    bool initialize(
        const std::string& model_dir,
        std::string& error,
        std::int32_t num_threads = 2,
        std::int32_t speaker_id = 0
    );

    bool synthesize(
        const std::string& text,
        TTSAudio& output,
        std::string& error
    );

    void shutdown() noexcept;

    bool ready() const noexcept
    {
        return tts_ != nullptr;
    }

    std::int32_t sampleRate() const noexcept;
    std::int32_t numSpeakers() const noexcept;

    std::int32_t speakerId() const noexcept
    {
        return speaker_id_;
    }

private:
    // 当前实例所使用的 sherpa-onnx TTS 对象。
    const SherpaOnnxOfflineTts* tts_ = nullptr;

    // 本次初始化选中的音色编号。
    std::int32_t speaker_id_ = 0;
};
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#pragma once`：头文件防重复包含，避免类和结构在同一编译单元中重定义。

- **L4** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <vector>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include "sherpa-onnx/c-api/c-api.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `struct TTSAudio`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L12** `std::vector<float> samples;`：连续动态数组，拥有PCM样本缓冲，分配/析构随vector生命周期。

- **L13** `std::int32_t sample_rate = 0;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L14** `double synthesis_ms = 0.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L17** `class TTSService`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L19** `public:`：访问控制域标签，决定成员能否从类外直接访问。

- **L20** `TTSService() = default;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L21** `~TTSService();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L23** `TTSService(const TTSService&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L24** `TTSService& operator=(const TTSService&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L25** `TTSService(TTSService&&) = delete;`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L26** `TTSService& operator=(TTSService&&) = delete;`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L29** `bool initialize(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L30** `const std::string& model_dir,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L31** `std::string& error,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L32** `std::int32_t num_threads = 2,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L33** `std::int32_t speaker_id = 0`：固定宽度32位整数，常用于采样率、SDK字段。

- **L36** `bool synthesize(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L37** `const std::string& text,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L38** `TTSAudio& output,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L39** `std::string& error`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L42** `void shutdown() noexcept;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L44** `bool ready() const noexcept`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L46** `return tts_ != nullptr;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L49** `std::int32_t sampleRate() const noexcept;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L50** `std::int32_t numSpeakers() const noexcept;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L52** `std::int32_t speakerId() const noexcept`：固定宽度32位整数，常用于采样率、SDK字段。

- **L54** `return speaker_id_;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L57** `private:`：访问控制域标签，决定成员能否从类外直接访问。

- **L59** `const SherpaOnnxOfflineTts* tts_ = nullptr;`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L62** `std::int32_t speaker_id_ = 0;`：固定宽度32位整数，常用于采样率、SDK字段。

## 真实源文件：`src/audio/tts_service.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_service.cpp`。归档长度 **313 行**，SHA\-256 完整值 `b43677e31f8b53ddf7fed2bbf341bf0b35c405dcba86bd8dc972a663d35ea28e`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_service.h"

#include <chrono>
#include <exception>
#include <memory>
#include <string>
#include <vector>

#include <unistd.h>

TTSService::~TTSService()
{
    shutdown();
}

bool TTSService::initialize(
    const std::string& model_dir,
    std::string& error,
    std::int32_t num_threads,
    std::int32_t speaker_id)
{
    shutdown();
    error.clear();

    if (num_threads < 1 || num_threads > 8)
    {
        error = "num_threads must be in [1, 8]";
        return false;
    }

    if (speaker_id < 0)
    {
        error = "speaker_id must be non-negative";
        return false;
    }

    // 根据模型目录名称区分当前两类模型。
    // 后续系统集成时可替换为显式配置枚举。
    const bool is_kokoro =
        model_dir.find("kokoro") != std::string::npos;

    const std::string model =
        model_dir + "/model.onnx";

    const std::string tokens =
        model_dir + "/tokens.txt";

    std::vector<std::string> required{
        model, tokens
    };

    // 这些字符串必须活到 CreateOfflineTts 返回。
    std::string voices;
    std::string data_dir;
    std::string lexicons;

    std::string vits_lexicon;
    std::string rule_fsts;

    SherpaOnnxOfflineTtsConfig cfg{};

    cfg.model.num_threads = num_threads;
    cfg.model.provider = "cpu";
    cfg.model.debug = 0;
    cfg.max_num_sentences = 1;
    cfg.silence_scale = 0.2f;

    if (is_kokoro)
    {
        // Kokoro v1.1 模型文件。
        voices = model_dir + "/voices.bin";

        data_dir =
            model_dir + "/espeak-ng-data";

        const std::string lexicon_en =
            model_dir + "/lexicon-us-en.txt";

        const std::string lexicon_zh =
            model_dir + "/lexicon-zh.txt";

        required.push_back(voices);
        required.push_back(lexicon_en);
        required.push_back(lexicon_zh);

        // 词典之间使用英文逗号分隔。
        lexicons = lexicon_en + "," + lexicon_zh;

        cfg.model.kokoro.model = model.c_str();
        cfg.model.kokoro.voices = voices.c_str();
        cfg.model.kokoro.tokens = tokens.c_str();

        cfg.model.kokoro.data_dir =
            data_dir.c_str();

        cfg.model.kokoro.lexicon =
            lexicons.c_str();
    }
    else
    {
        // 保留先前已经测试成功的 MeloTTS 配置。
        vits_lexicon =
            model_dir + "/lexicon.txt";

        const std::string phone =
            model_dir + "/phone.fst";

        const std::string date =
            model_dir + "/date.fst";

        const std::string number =
            model_dir + "/number.fst";

        const std::string heteronym =
            model_dir + "/new_heteronym.fst";

        required.push_back(vits_lexicon);
        required.push_back(phone);
        required.push_back(date);
        required.push_back(number);
        required.push_back(heteronym);

        rule_fsts =
            phone + "," +
            date + "," +
            number + "," +
            heteronym;

        cfg.model.vits.model = model.c_str();

        cfg.model.vits.lexicon =
            vits_lexicon.c_str();

        cfg.model.vits.tokens = tokens.c_str();

        cfg.model.vits.noise_scale = 0.667f;
        cfg.model.vits.noise_scale_w = 0.8f;
        cfg.model.vits.length_scale = 1.0f;

        cfg.rule_fsts = rule_fsts.c_str();
    }

    // 检查所有需要的文件。
    for (const auto& path : required)
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            error = "Cannot read TTS file: " + path;
            return false;
        }
    }

    // Kokoro 英文前端数据目录必须存在。
    if (is_kokoro &&
        ::access(data_dir.c_str(), F_OK) != 0)
    {
        error =
            "Cannot find espeak data directory: " +
            data_dir;

        return false;
    }

    const SherpaOnnxOfflineTts* new_tts =
        SherpaOnnxCreateOfflineTts(&cfg);

    if (new_tts == nullptr)
    {
        error =
            "SherpaOnnxCreateOfflineTts returned null";
        return false;
    }

    // 加载成功后，检查说话人编号是否合法。
    const std::int32_t speakers =
        SherpaOnnxOfflineTtsNumSpeakers(new_tts);

    if (speaker_id >= speakers)
    {
        error =
            "Invalid speaker_id=" +
            std::to_string(speaker_id) +
            ", speakers=" +
            std::to_string(speakers);

        SherpaOnnxDestroyOfflineTts(new_tts);
        return false;
    }

    tts_ = new_tts;
    speaker_id_ = speaker_id;

    return true;
}

bool TTSService::synthesize(
    const std::string& text,
    TTSAudio& output,
    std::string& error)
{
    output = TTSAudio{};
    error.clear();

    if (tts_ == nullptr)
    {
        error = "TTSService is not initialized";
        return false;
    }

    if (text.empty())
    {
        error = "Input text is empty";
        return false;
    }

    SherpaOnnxGenerationConfig gen{};

    // 关键：使用初始化时选定的说话人。
    gen.sid = speaker_id_;

    gen.speed = 1.0f;
    gen.silence_scale = 0.2f;

    using AudioDeleter = decltype(
        &SherpaOnnxDestroyOfflineTtsGeneratedAudio
    );

    using AudioOwner = std::unique_ptr<
        const SherpaOnnxGeneratedAudio,
        AudioDeleter
    >;

    const auto start =
        std::chrono::steady_clock::now();

    // 真正执行 ONNX TTS 推理。
    AudioOwner audio(
        SherpaOnnxOfflineTtsGenerateWithConfig(
            tts_,
            text.c_str(),
            &gen,
            nullptr,
            nullptr
        ),
        &SherpaOnnxDestroyOfflineTtsGeneratedAudio
    );

    const auto finish =
        std::chrono::steady_clock::now();

    if (!audio ||
        !audio->samples ||
        audio->n <= 0 ||
        audio->sample_rate <= 0)
    {
        error =
            "TTS generation returned invalid audio";
        return false;
    }

    try
    {
        // 复制 SDK PCM 到 C++ 自有缓冲区。
        output.samples.assign(
            audio->samples,
            audio->samples + audio->n
        );
    }
    catch (const std::exception& e)
    {
        error =
            std::string("PCM copy failed: ") +
            e.what();

        return false;
    }

    output.sample_rate = audio->sample_rate;

    output.synthesis_ms =
        std::chrono::duration<double, std::milli>(
            finish - start
        ).count();

    // audio 离开作用域时自动调用 SDK 删除器。
    return true;
}

void TTSService::shutdown() noexcept
{
    if (tts_ != nullptr)
    {
        SherpaOnnxDestroyOfflineTts(tts_);
        tts_ = nullptr;
    }

    speaker_id_ = 0;
}

std::int32_t TTSService::sampleRate() const noexcept
{
    return tts_
        ? SherpaOnnxOfflineTtsSampleRate(tts_)
        : 0;
}

std::int32_t TTSService::numSpeakers() const noexcept
{
    return tts_
        ? SherpaOnnxOfflineTtsNumSpeakers(tts_)
        : 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <memory>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <vector>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <unistd.h>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `TTSService::~TTSService()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L14** `shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L17** `bool TTSService::initialize(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L18** `const std::string& model_dir,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L19** `std::string& error,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L20** `std::int32_t num_threads,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L21** `std::int32_t speaker_id)`：固定宽度32位整数，常用于采样率、SDK字段。

- **L23** `shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L24** `error.clear();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L26** `if (num_threads < 1 || num_threads > 8)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L28** `error = "num_threads must be in [1, 8]";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L29** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L32** `if (speaker_id < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L34** `error = "speaker_id must be non-negative";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L35** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L40** `const bool is_kokoro =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L41** `model_dir.find("kokoro") != std::string::npos;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L43** `const std::string model =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L44** `model_dir + "/model.onnx";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L46** `const std::string tokens =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L47** `model_dir + "/tokens.txt";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L49** `std::vector<std::string> required{`：连续动态数组，拥有PCM样本缓冲，分配/析构随vector生命周期。

- **L50** `model, tokens`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L54** `std::string voices;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L55** `std::string data_dir;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L56** `std::string lexicons;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L58** `std::string vits_lexicon;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L59** `std::string rule_fsts;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L61** `SherpaOnnxOfflineTtsConfig cfg{};`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L63** `cfg.model.num_threads = num_threads;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L64** `cfg.model.provider = "cpu";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L65** `cfg.model.debug = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L66** `cfg.max_num_sentences = 1;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L67** `cfg.silence_scale = 0.2f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L69** `if (is_kokoro)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L72** `voices = model_dir + "/voices.bin";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L74** `data_dir =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L75** `model_dir + "/espeak-ng-data";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L77** `const std::string lexicon_en =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L78** `model_dir + "/lexicon-us-en.txt";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L80** `const std::string lexicon_zh =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L81** `model_dir + "/lexicon-zh.txt";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L83** `required.push_back(voices);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L84** `required.push_back(lexicon_en);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L85** `required.push_back(lexicon_zh);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L88** `lexicons = lexicon_en + "," + lexicon_zh;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L90** `cfg.model.kokoro.model = model.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L91** `cfg.model.kokoro.voices = voices.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L92** `cfg.model.kokoro.tokens = tokens.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L94** `cfg.model.kokoro.data_dir =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L95** `data_dir.c_str();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L97** `cfg.model.kokoro.lexicon =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L98** `lexicons.c_str();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L100** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L103** `vits_lexicon =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L104** `model_dir + "/lexicon.txt";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L106** `const std::string phone =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L107** `model_dir + "/phone.fst";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L109** `const std::string date =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L110** `model_dir + "/date.fst";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L112** `const std::string number =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L113** `model_dir + "/number.fst";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L115** `const std::string heteronym =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L116** `model_dir + "/new_heteronym.fst";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L118** `required.push_back(vits_lexicon);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L119** `required.push_back(phone);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L120** `required.push_back(date);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L121** `required.push_back(number);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L122** `required.push_back(heteronym);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L124** `rule_fsts =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L125** `phone + "," +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L126** `date + "," +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L127** `number + "," +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L128** `heteronym;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L130** `cfg.model.vits.model = model.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L132** `cfg.model.vits.lexicon =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L133** `vits_lexicon.c_str();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L135** `cfg.model.vits.tokens = tokens.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L137** `cfg.model.vits.noise_scale = 0.667f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L138** `cfg.model.vits.noise_scale_w = 0.8f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L139** `cfg.model.vits.length_scale = 1.0f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L141** `cfg.rule_fsts = rule_fsts.c_str();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L145** `for (const auto& path : required)`：循环控制语句，注意终止条件和迭代后状态更新。

- **L147** `if (::access(path.c_str(), R_OK) != 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L149** `error = "Cannot read TTS file: " + path;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L150** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L155** `if (is_kokoro &&`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L156** `::access(data_dir.c_str(), F_OK) != 0)`：POSIX文件读/存在性检查，只说明路径可访问，不证明模型加载成功。

- **L158** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L159** `"Cannot find espeak data directory: " +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L160** `data_dir;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L162** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L165** `const SherpaOnnxOfflineTts* new_tts =`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L166** `SherpaOnnxCreateOfflineTts(&cfg);`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L168** `if (new_tts == nullptr)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L170** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L171** `"SherpaOnnxCreateOfflineTts returned null";`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L172** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L176** `const std::int32_t speakers =`：固定宽度32位整数，常用于采样率、SDK字段。

- **L177** `SherpaOnnxOfflineTtsNumSpeakers(new_tts);`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L179** `if (speaker_id >= speakers)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L181** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L182** `"Invalid speaker_id=" +`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L183** `std::to_string(speaker_id) +`：标准库类型/成员/函数参与线程管理、容器或数据处理；`::`用于命名空间/类作用域限定。

- **L184** `", speakers=" +`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L185** `std::to_string(speakers);`：标准库类型/成员/函数参与线程管理、容器或数据处理；`::`用于命名空间/类作用域限定。

- **L187** `SherpaOnnxDestroyOfflineTts(new_tts);`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L188** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L191** `tts_ = new_tts;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L192** `speaker_id_ = speaker_id;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L194** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L197** `bool TTSService::synthesize(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L198** `const std::string& text,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L199** `TTSAudio& output,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L200** `std::string& error)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L202** `output = TTSAudio{};`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L203** `error.clear();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L205** `if (tts_ == nullptr)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L207** `error = "TTSService is not initialized";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L208** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L211** `if (text.empty())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L213** `error = "Input text is empty";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L214** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L217** `SherpaOnnxGenerationConfig gen{};`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L220** `gen.sid = speaker_id_;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L222** `gen.speed = 1.0f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L223** `gen.silence_scale = 0.2f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L225** `using AudioDeleter = decltype(`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L226** `&SherpaOnnxDestroyOfflineTtsGeneratedAudio`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L229** `using AudioOwner = std::unique_ptr<`：独占所有权RAII指针，结合C API自定义删除器自动释放SDK资源。

- **L230** `const SherpaOnnxGeneratedAudio,`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L231** `AudioDeleter`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L232** `>;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L234** `const auto start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L235** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L238** `AudioOwner audio(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L239** `SherpaOnnxOfflineTtsGenerateWithConfig(`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L240** `tts_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L241** `text.c_str(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L242** `&gen,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L243** `nullptr,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L244** `nullptr`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L245** `),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L246** `&SherpaOnnxDestroyOfflineTtsGeneratedAudio`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L249** `const auto finish =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L250** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L252** `if (!audio ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L253** `!audio->samples ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L254** `audio->n <= 0 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L255** `audio->sample_rate <= 0)`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L257** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L258** `"TTS generation returned invalid audio";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L259** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L262** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L265** `output.samples.assign(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L266** `audio->samples,`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L267** `audio->samples + audio->n`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L270** `catch (const std::exception& e)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L272** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L273** `std::string("PCM copy failed: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L274** `e.what();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L276** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L279** `output.sample_rate = audio->sample_rate;`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L281** `output.synthesis_ms =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L282** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L283** `finish - start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L284** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L287** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L290** `void TTSService::shutdown() noexcept`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L292** `if (tts_ != nullptr)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L294** `SherpaOnnxDestroyOfflineTts(tts_);`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L295** `tts_ = nullptr;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L298** `speaker_id_ = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L301** `std::int32_t TTSService::sampleRate() const noexcept`：固定宽度32位整数，常用于采样率、SDK字段。

- **L303** `return tts_`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L304** `? SherpaOnnxOfflineTtsSampleRate(tts_)`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L305** `: 0;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L308** `std::int32_t TTSService::numSpeakers() const noexcept`：固定宽度32位整数，常用于采样率、SDK字段。

- **L310** `return tts_`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L311** `? SherpaOnnxOfflineTtsNumSpeakers(tts_)`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L312** `: 0;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

## 真实源文件：`src/audio/tts_smoke.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_smoke.cpp`。归档长度 **182 行**，SHA\-256 完整值 `63561803c786cd366740cf391b275935c592be234336e19f023e770c35b122ca`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_service.h"

#include <chrono>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>

static bool parseInteger(
    const char* raw,
    std::int32_t minimum,
    std::int32_t maximum,
    std::int32_t& result)
{
    try
    {
        const std::string value(raw);
        std::size_t used = 0;

        const long parsed = std::stol(value, &used);

        if (used != value.size() ||
            parsed < minimum ||
            parsed > maximum)
        {
            return false;
        }

        result = static_cast<std::int32_t>(parsed);
        return true;
    }
    catch (const std::exception&)
    {
        return false;
    }
}

int main(int argc, char** argv)
{
    if (argc < 4 || argc > 6)
    {
        std::cerr
            << "Usage: tts_smoke "
            << "<model_dir> <output.wav> <text> "
            << "[threads=2] [speaker_id=0]\n";

        return 2;
    }

    const std::string model_dir(argv[1]);
    const std::string wav_path(argv[2]);
    const std::string text(argv[3]);

    std::int32_t threads = 2;
    std::int32_t speaker_id = 0;

    if (argc >= 5 &&
        !parseInteger(argv[4], 1, 8, threads))
    {
        std::cerr << "Invalid threads\n";
        return 2;
    }

    if (argc >= 6 &&
        !parseInteger(argv[5], 0, 10000, speaker_id))
    {
        std::cerr << "Invalid speaker_id\n";
        return 2;
    }

    TTSService tts;
    std::string error;

    std::cout
        << "[Init] Loading TTS model...\n"
        << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            speaker_id))
    {
        std::cerr
            << "[Init] FAIL: " << error << '\n';

        return 1;
    }

    const auto init_end =
        std::chrono::steady_clock::now();

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            init_end - init_start
        ).count();

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Init] OK"
        << " time_ms=" << init_ms
        << " sample_rate=" << tts.sampleRate()
        << " speakers=" << tts.numSpeakers()
        << " sid=" << tts.speakerId()
        << '\n';

    TTSAudio audio;

    std::cout
        << "[TTS] text=" << text << '\n'
        << std::flush;

    if (!tts.synthesize(text, audio, error))
    {
        std::cerr
            << "[TTS] FAIL: " << error << '\n';

        return 1;
    }

    if (audio.sample_rate <= 0 ||
        audio.samples.empty())
    {
        std::cerr << "[TTS] Invalid PCM data\n";
        return 1;
    }

    const double audio_seconds =
        static_cast<double>(audio.samples.size()) /
        audio.sample_rate;

    const double rtf =
        (audio.synthesis_ms / 1000.0) /
        audio_seconds;

    std::cout
        << "[TTS] sample_count="
        << audio.samples.size()
        << " sample_rate=" << audio.sample_rate
        << " audio_sec=" << audio_seconds
        << " synth_ms=" << audio.synthesis_ms
        << " RTF=" << rtf
        << '\n';

    if (audio.samples.size() >
        static_cast<std::size_t>(
            std::numeric_limits<std::int32_t>::max()))
    {
        std::cerr << "[WAV] Too many samples\n";
        return 1;
    }

    const int ok = SherpaOnnxWriteWave(
        audio.samples.data(),
        static_cast<std::int32_t>(
            audio.samples.size()
        ),
        audio.sample_rate,
        wav_path.c_str()
    );

    if (ok != 1)
    {
        std::cerr
            << "[WAV] FAIL: " << wav_path << '\n';

        return 1;
    }

    std::cout
        << "[WAV] " << wav_path << '\n'
        << "PASS\n";

    return 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <iomanip>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <limits>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `static bool parseInteger(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L13** `const char* raw,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L14** `std::int32_t minimum,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L15** `std::int32_t maximum,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L16** `std::int32_t& result)`：固定宽度32位整数，常用于采样率、SDK字段。

- **L18** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L20** `const std::string value(raw);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L21** `std::size_t used = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L23** `const long parsed = std::stol(value, &used);`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L25** `if (used != value.size() ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L26** `parsed < minimum ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L27** `parsed > maximum)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L29** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L32** `result = static_cast<std::int32_t>(parsed);`：固定宽度32位整数，常用于采样率、SDK字段。

- **L33** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L35** `catch (const std::exception&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L37** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L41** `int main(int argc, char** argv)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L43** `if (argc < 4 || argc > 6)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L45** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L46** `<< "Usage: tts_smoke "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L47** `<< "<model_dir> <output.wav> <text> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L48** `<< "[threads=2] [speaker_id=0]\n";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L50** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L53** `const std::string model_dir(argv[1]);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L54** `const std::string wav_path(argv[2]);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L55** `const std::string text(argv[3]);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L57** `std::int32_t threads = 2;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L58** `std::int32_t speaker_id = 0;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L60** `if (argc >= 5 &&`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L61** `!parseInteger(argv[4], 1, 8, threads))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L63** `std::cerr << "Invalid threads\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L64** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L67** `if (argc >= 6 &&`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L68** `!parseInteger(argv[5], 0, 10000, speaker_id))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L70** `std::cerr << "Invalid speaker_id\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L71** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L74** `TTSService tts;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L75** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L77** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L78** `<< "[Init] Loading TTS model...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L79** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L81** `const auto init_start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L82** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L84** `if (!tts.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L85** `model_dir,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L86** `error,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L87** `threads,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L88** `speaker_id))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L90** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L91** `<< "[Init] FAIL: " << error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L93** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L96** `const auto init_end =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L97** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L99** `const double init_ms =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L100** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L101** `init_end - init_start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L102** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L104** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L105** `<< std::fixed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L106** `<< std::setprecision(3)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L107** `<< "[Init] OK"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L108** `<< " time_ms=" << init_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L109** `<< " sample_rate=" << tts.sampleRate()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L110** `<< " speakers=" << tts.numSpeakers()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L111** `<< " sid=" << tts.speakerId()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L112** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L114** `TTSAudio audio;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L116** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L117** `<< "[TTS] text=" << text << '\n'`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L118** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L120** `if (!tts.synthesize(text, audio, error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L122** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L123** `<< "[TTS] FAIL: " << error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L125** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L128** `if (audio.sample_rate <= 0 ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L129** `audio.samples.empty())`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L131** `std::cerr << "[TTS] Invalid PCM data\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L132** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L135** `const double audio_seconds =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L136** `static_cast<double>(audio.samples.size()) /`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L137** `audio.sample_rate;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L139** `const double rtf =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L140** `(audio.synthesis_ms / 1000.0) /`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L141** `audio_seconds;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L143** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L144** `<< "[TTS] sample_count="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L145** `<< audio.samples.size()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L146** `<< " sample_rate=" << audio.sample_rate`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L147** `<< " audio_sec=" << audio_seconds`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L148** `<< " synth_ms=" << audio.synthesis_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L149** `<< " RTF=" << rtf`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L150** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L152** `if (audio.samples.size() >`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L153** `static_cast<std::size_t>(`：与容器大小/样本数量相配套的无符号整数类型。

- **L154** `std::numeric_limits<std::int32_t>::max()))`：固定宽度32位整数，常用于采样率、SDK字段。

- **L156** `std::cerr << "[WAV] Too many samples\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L157** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L160** `const int ok = SherpaOnnxWriteWave(`：调用sherpa\-onnx C ABI，检查空指针/返回值，必须使用对应SDK Destroy释放。

- **L161** `audio.samples.data(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L162** `static_cast<std::int32_t>(`：固定宽度32位整数，常用于采样率、SDK字段。

- **L163** `audio.samples.size()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L164** `),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L165** `audio.sample_rate,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L166** `wav_path.c_str()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L169** `if (ok != 1)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L171** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L172** `<< "[WAV] FAIL: " << wav_path << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L174** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L177** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L178** `<< "[WAV] " << wav_path << '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L179** `<< "PASS\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L181** `return 0;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

## 真实源文件：`include/audio/alsa_playback_service.h`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/alsa_playback_service.h`。归档长度 **60 行**，SHA\-256 完整值 `d51e6deb7a316fc024cfdbb01a4f64d8e76d71f0e065ba24d5ed29fa545dba3d`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include <alsa/asoundlib.h>

#include <cstddef>
#include <cstdint>
#include <string>

// 阻塞式 ALSA 音频播放服务。
// 输入 float PCM，内部转换成 S16_LE。
// 3.3 阶段仅在一个线程中使用，不支持并发调用。
class AlsaPlaybackService
{
public:
    AlsaPlaybackService() = default;
    ~AlsaPlaybackService();

    // ALSA PCM 句柄不可复制。
    AlsaPlaybackService(const AlsaPlaybackService&) = delete;
    AlsaPlaybackService& operator=(const AlsaPlaybackService&) = delete;

    // 初始化声卡和 PCM 播放参数。
    bool open(
        const std::string& device,
        std::int32_t sample_rate,
        std::string& error
    );

    // 播放单声道 float PCM。
    // 本函数阻塞，直到音频播放完成或出错。
    bool play(
        const float* samples,
        std::size_t sample_count,
        std::string& error
    );

    // 关闭设备并释放资源。
    void close() noexcept;

    bool ready() const noexcept
    {
        return pcm_ != nullptr;
    }

    std::uint64_t xrunCount() const noexcept
    {
        return xrun_count_;
    }

private:
    // ALSA PCM 设备句柄。
    snd_pcm_t* pcm_ = nullptr;

    // 当前配置的采样率。
    std::int32_t sample_rate_ = 0;

    // Playback 发生缓冲区欠载的次数。
    std::uint64_t xrun_count_ = 0;
};
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#pragma once`：头文件防重复包含，避免类和结构在同一编译单元中重定义。

- **L4** `#include <alsa/asoundlib.h>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <cstddef>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L13** `class AlsaPlaybackService`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L15** `public:`：访问控制域标签，决定成员能否从类外直接访问。

- **L16** `AlsaPlaybackService() = default;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L17** `~AlsaPlaybackService();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L20** `AlsaPlaybackService(const AlsaPlaybackService&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L21** `AlsaPlaybackService& operator=(const AlsaPlaybackService&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L24** `bool open(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L25** `const std::string& device,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L26** `std::int32_t sample_rate,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L27** `std::string& error`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L32** `bool play(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L33** `const float* samples,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L34** `std::size_t sample_count,`：与容器大小/样本数量相配套的无符号整数类型。

- **L35** `std::string& error`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L39** `void close() noexcept;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L41** `bool ready() const noexcept`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L43** `return pcm_ != nullptr;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L46** `std::uint64_t xrunCount() const noexcept`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L48** `return xrun_count_;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L51** `private:`：访问控制域标签，决定成员能否从类外直接访问。

- **L53** `snd_pcm_t* pcm_ = nullptr;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L56** `std::int32_t sample_rate_ = 0;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L59** `std::uint64_t xrun_count_ = 0;`：64位无符号请求ID/计数，跨线程读写仍须同步。

## 真实源文件：`src/audio/alsa_playback_service.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/alsa_playback_service.cpp`。归档长度 **399 行**，SHA\-256 完整值 `777ca61cc29489ecdf0c47c7a49d49bc1ae4c3f8ff2de15b33b30cc9e63b7e89`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/alsa_playback_service.h"

#include <algorithm>
#include <cerrno>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <new>
#include <string>
#include <vector>

AlsaPlaybackService::~AlsaPlaybackService()
{
    close();
}

bool AlsaPlaybackService::open(
    const std::string& device,
    std::int32_t sample_rate,
    std::string& error)
{
    close();
    error.clear();

    if (device.empty() || sample_rate <= 0)
    {
        error = "Invalid ALSA device or sample rate";
        return false;
    }

    // 1. 打开阻塞式 ALSA Playback PCM。
    int rc = snd_pcm_open(
        &pcm_,
        device.c_str(),
        SND_PCM_STREAM_PLAYBACK,
        0
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_open: ") +
                snd_strerror(rc);
        pcm_ = nullptr;
        return false;
    }

    // 2. 统一配置硬件和软件参数。
    // soft_resample=1 允许 ALSA 插件进行采样率转换。
    // latency=500000 us，即 500 ms 的目标缓冲延迟。
    rc = snd_pcm_set_params(
        pcm_,
        SND_PCM_FORMAT_S16_LE,
        SND_PCM_ACCESS_RW_INTERLEAVED,
        1,
        static_cast<unsigned int>(sample_rate),
        1,
        500000
    );

    if (rc < 0)
    {
        error = std::string("snd_pcm_set_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 3. 查询真正协商出来的 buffer 和 period。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 ||
        buffer_frames < 2 ||
        period_frames == 0)
    {
        error = "Cannot obtain valid ALSA buffer parameters";
        close();
        return false;
    }

    // 4. 设置软件参数。
    snd_pcm_sw_params_t* sw = nullptr;
    snd_pcm_sw_params_alloca(&sw);

    rc = snd_pcm_sw_params_current(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("sw_params_current: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    // 至少积累一部分音频再启动播放。
    // 阈值不超过缓冲区大小减 1。
    const snd_pcm_uframes_t start_threshold =
        std::min(
            buffer_frames - 1,
            period_frames * 2
        );

    rc = snd_pcm_sw_params_set_start_threshold(
        pcm_,
        sw,
        start_threshold
    );

    if (rc < 0)
    {
        error = std::string("set_start_threshold: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params_set_avail_min(
        pcm_,
        sw,
        period_frames
    );

    if (rc < 0)
    {
        error = std::string("set_avail_min: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    rc = snd_pcm_sw_params(pcm_, sw);

    if (rc < 0)
    {
        error = std::string("snd_pcm_sw_params: ") +
                snd_strerror(rc);
        close();
        return false;
    }

    sample_rate_ = sample_rate;
    xrun_count_ = 0;

    std::cout
        << "[ALSA config]"
        << " buffer_frames=" << buffer_frames
        << " period_frames=" << period_frames
        << " start_threshold=" << start_threshold
        << " buffer_ms="
        << (1000.0 * buffer_frames / sample_rate)
        << '\n';

    return true;
}

bool AlsaPlaybackService::play(
    const float* samples,
    std::size_t sample_count,
    std::string& error)
{
    error.clear();

    if (pcm_ == nullptr)
    {
        error = "ALSA device is not initialized";
        return false;
    }

    if (samples == nullptr || sample_count == 0)
    {
        error = "Invalid audio samples";
        return false;
    }

    // 1. 先在内存中完成全部格式转换，
    // 避免播放期间进行耗时的逐样本转换。
    std::vector<std::int16_t> pcm_data;

    try
    {
        pcm_data.resize(sample_count);
    }
    catch (const std::bad_alloc&)
    {
        error = "Cannot allocate playback PCM buffer";
        return false;
    }

    for (std::size_t i = 0; i < sample_count; ++i)
    {
        float value = samples[i];

        if (!std::isfinite(value))
        {
            value = 0.0f;
        }

        value = std::max(
            -1.0f,
            std::min(1.0f, value)
        );

        const float scale =
            value < 0.0f ? 32768.0f : 32767.0f;

        pcm_data[i] = static_cast<std::int16_t>(
            std::lround(value * scale)
        );
    }

    // 2. 准备播放设备。
    int rc = snd_pcm_prepare(pcm_);

    if (rc < 0)
    {
        error = std::string("snd_pcm_prepare: ") +
                snd_strerror(rc);
        return false;
    }

    // 查询 period，以便按照设备缓冲节奏提交数据。
    snd_pcm_uframes_t buffer_frames = 0;
    snd_pcm_uframes_t period_frames = 0;

    rc = snd_pcm_get_params(
        pcm_,
        &buffer_frames,
        &period_frames
    );

    if (rc < 0 || period_frames == 0)
    {
        error = "Cannot query playback period size";
        return false;
    }

    std::size_t offset = 0;
    int consecutive_recoveries = 0;
    int wait_timeouts = 0;

    // 3. 持续将音频送入 ALSA。
    while (offset < pcm_data.size())
    {
        const std::size_t remaining =
            pcm_data.size() - offset;

        const snd_pcm_uframes_t frames =
            static_cast<snd_pcm_uframes_t>(
                std::min(
                    remaining,
                    static_cast<std::size_t>(
                        period_frames
                    )
                )
            );

        const snd_pcm_sframes_t written =
            snd_pcm_writei(
                pcm_,
                pcm_data.data() + offset,
                frames
            );

        if (written > 0)
        {
            offset += static_cast<std::size_t>(written);

            consecutive_recoveries = 0;
            wait_timeouts = 0;
            continue;
        }

        if (written == -EAGAIN || written == 0)
        {
            const int wait_rc =
                snd_pcm_wait(pcm_, 1000);

            if (wait_rc < 0)
            {
                error = std::string("snd_pcm_wait: ") +
                        snd_strerror(wait_rc);
                return false;
            }

            if (wait_rc == 0)
            {
                if (++wait_timeouts > 5)
                {
                    error = "ALSA wait timeout";
                    return false;
                }
            }

            continue;
        }

        // EPIPE 表示播放缓冲区欠载。
        if (written == -EPIPE)
        {
            ++xrun_count_;

            std::cerr
                << "[ALSA XRUN] write offset="
                << offset
                << " total=" << pcm_data.size()
                << '\n';
        }

        const int recover_rc = snd_pcm_recover(
            pcm_,
            static_cast<int>(written),
            1
        );

        if (recover_rc < 0)
        {
            error = std::string("snd_pcm_recover: ") +
                    snd_strerror(recover_rc);
            return false;
        }

        if (++consecutive_recoveries > 5)
        {
            error = "Too many ALSA recoveries";
            return false;
        }
    }

    // 4. 记录全部数据写入后的 PCM 状态。
    snd_pcm_state_t state = snd_pcm_state(pcm_);

    std::cout
        << "[ALSA write]"
        << " submitted_frames=" << offset
        << " state=" << snd_pcm_state_name(state)
        << '\n';

    // 对短音频：如果还未达到自动启动阈值，
    // 显式启动播放，再进行 drain。
    if (state == SND_PCM_STATE_PREPARED)
    {
        rc = snd_pcm_start(pcm_);

        if (rc < 0)
        {
            error = std::string("snd_pcm_start: ") +
                    snd_strerror(rc);
            return false;
        }
    }

    // 5. 等待 ALSA 将缓冲区中的音频播放完。
    rc = snd_pcm_drain(pcm_);

    if (rc < 0)
    {
        if (rc == -EPIPE)
        {
            ++xrun_count_;
        }

        state = snd_pcm_state(pcm_);

        error = std::string("snd_pcm_drain: ") +
                snd_strerror(rc) +
                " state=" +
                snd_pcm_state_name(state);

        return false;
    }

    // XRUN 即使恢复成功，也说明本次播放可能存在断续。
    if (xrun_count_ != 0)
    {
        error = "Playback completed with detected XRUN";
        return false;
    }

    return true;
}

void AlsaPlaybackService::close() noexcept
{
    if (pcm_ != nullptr)
    {
        snd_pcm_close(pcm_);
        pcm_ = nullptr;
    }

    sample_rate_ = 0;
    xrun_count_ = 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/alsa_playback_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <algorithm>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <cerrno>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <cmath>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <new>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L11** `#include <vector>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L13** `AlsaPlaybackService::~AlsaPlaybackService()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L15** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L18** `bool AlsaPlaybackService::open(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L19** `const std::string& device,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L20** `std::int32_t sample_rate,`：固定宽度32位整数，常用于采样率、SDK字段。

- **L21** `std::string& error)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L23** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L24** `error.clear();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L26** `if (device.empty() || sample_rate <= 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L28** `error = "Invalid ALSA device or sample rate";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L29** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L33** `int rc = snd_pcm_open(`：ALSA Playback打开；负错误码经snd\_strerror转换可读信息。

- **L34** `&pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L35** `device.c_str(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L36** `SND_PCM_STREAM_PLAYBACK,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L37** `0`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L40** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L42** `error = std::string("snd_pcm_open: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L43** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L44** `pcm_ = nullptr;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L45** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L51** `rc = snd_pcm_set_params(`：协商PCM格式、单声道、采样率、重采样及缓冲延迟，随后应查询实际参数。

- **L52** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L53** `SND_PCM_FORMAT_S16_LE,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L54** `SND_PCM_ACCESS_RW_INTERLEAVED,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L55** `1,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L56** `static_cast<unsigned int>(sample_rate),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L57** `1,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L58** `500000`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L61** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L63** `error = std::string("snd_pcm_set_params: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L64** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L65** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L66** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L70** `snd_pcm_uframes_t buffer_frames = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L71** `snd_pcm_uframes_t period_frames = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L73** `rc = snd_pcm_get_params(`：读取ALSA真实协商出的buffer和period帧数。

- **L74** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L75** `&buffer_frames,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L76** `&period_frames`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L79** `if (rc < 0 ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L80** `buffer_frames < 2 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L81** `period_frames == 0)`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L83** `error = "Cannot obtain valid ALSA buffer parameters";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L84** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L85** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L89** `snd_pcm_sw_params_t* sw = nullptr;`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L90** `snd_pcm_sw_params_alloca(&sw);`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L92** `rc = snd_pcm_sw_params_current(pcm_, sw);`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L94** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L96** `error = std::string("sw_params_current: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L97** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L98** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L99** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L104** `const snd_pcm_uframes_t start_threshold =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L105** `std::min(`：求两个边界最小值，防止period/buffer边界越界。

- **L106** `buffer_frames - 1,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L107** `period_frames * 2`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L110** `rc = snd_pcm_sw_params_set_start_threshold(`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L111** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L112** `sw,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L113** `start_threshold`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L116** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L118** `error = std::string("set_start_threshold: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L119** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L120** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L121** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L124** `rc = snd_pcm_sw_params_set_avail_min(`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L125** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L126** `sw,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L127** `period_frames`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L130** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L132** `error = std::string("set_avail_min: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L133** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L134** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L135** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L138** `rc = snd_pcm_sw_params(pcm_, sw);`：设置/应用ALSA start\_threshold、avail\_min等软件缓冲控制。

- **L140** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L142** `error = std::string("snd_pcm_sw_params: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L143** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L144** `close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L145** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L148** `sample_rate_ = sample_rate;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L149** `xrun_count_ = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L151** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L152** `<< "[ALSA config]"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L153** `<< " buffer_frames=" << buffer_frames`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L154** `<< " period_frames=" << period_frames`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L155** `<< " start_threshold=" << start_threshold`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L156** `<< " buffer_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L157** `<< (1000.0 * buffer_frames / sample_rate)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L158** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L160** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L163** `bool AlsaPlaybackService::play(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L164** `const float* samples,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L165** `std::size_t sample_count,`：与容器大小/样本数量相配套的无符号整数类型。

- **L166** `std::string& error)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L168** `error.clear();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L170** `if (pcm_ == nullptr)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L172** `error = "ALSA device is not initialized";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L173** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L176** `if (samples == nullptr || sample_count == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L178** `error = "Invalid audio samples";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L179** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L184** `std::vector<std::int16_t> pcm_data;`：连续动态数组，拥有PCM样本缓冲，分配/析构随vector生命周期。

- **L186** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L188** `pcm_data.resize(sample_count);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L190** `catch (const std::bad_alloc&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L192** `error = "Cannot allocate playback PCM buffer";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L193** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L196** `for (std::size_t i = 0; i < sample_count; ++i)`：循环控制语句，注意终止条件和迭代后状态更新。

- **L198** `float value = samples[i];`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L200** `if (!std::isfinite(value))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L202** `value = 0.0f;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L205** `value = std::max(`：求边界最大值，保证float裁剪在\[\-1,1\]。

- **L206** `-1.0f,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L207** `std::min(1.0f, value)`：求两个边界最小值，防止period/buffer边界越界。

- **L210** `const float scale =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L211** `value < 0.0f ? 32768.0f : 32767.0f;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L213** `pcm_data[i] = static_cast<std::int16_t>(`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L214** `std::lround(value * scale)`：将经过截幅缩放的float PCM舍入为16位整数。

- **L219** `int rc = snd_pcm_prepare(pcm_);`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L221** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L223** `error = std::string("snd_pcm_prepare: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L224** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L225** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L229** `snd_pcm_uframes_t buffer_frames = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L230** `snd_pcm_uframes_t period_frames = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L232** `rc = snd_pcm_get_params(`：读取ALSA真实协商出的buffer和period帧数。

- **L233** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L234** `&buffer_frames,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L235** `&period_frames`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L238** `if (rc < 0 || period_frames == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L240** `error = "Cannot query playback period size";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L241** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L244** `std::size_t offset = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L245** `int consecutive_recoveries = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L246** `int wait_timeouts = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L249** `while (offset < pcm_data.size())`：循环控制语句，注意终止条件和迭代后状态更新。

- **L251** `const std::size_t remaining =`：与容器大小/样本数量相配套的无符号整数类型。

- **L252** `pcm_data.size() - offset;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L254** `const snd_pcm_uframes_t frames =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L255** `static_cast<snd_pcm_uframes_t>(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L256** `std::min(`：求两个边界最小值，防止period/buffer边界越界。

- **L257** `remaining,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L258** `static_cast<std::size_t>(`：与容器大小/样本数量相配套的无符号整数类型。

- **L259** `period_frames`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L264** `const snd_pcm_sframes_t written =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L265** `snd_pcm_writei(`：交错PCM写入，返回已提交帧数而非字节数，必须处理短写和负错误码。

- **L266** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L267** `pcm_data.data() + offset,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L268** `frames`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L271** `if (written > 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L273** `offset += static_cast<std::size_t>(written);`：与容器大小/样本数量相配套的无符号整数类型。

- **L275** `consecutive_recoveries = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L276** `wait_timeouts = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L277** `continue;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L280** `if (written == -EAGAIN || written == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L282** `const int wait_rc =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L283** `snd_pcm_wait(pcm_, 1000);`：等待PCM可写/超时，避免对EAGAIN的无意义忙轮询。

- **L285** `if (wait_rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L287** `error = std::string("snd_pcm_wait: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L288** `snd_strerror(wait_rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L289** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L292** `if (wait_rc == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L294** `if (++wait_timeouts > 5)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L296** `error = "ALSA wait timeout";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L297** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L301** `continue;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L305** `if (written == -EPIPE)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L307** `++xrun_count_;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L309** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L310** `<< "[ALSA XRUN] write offset="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L311** `<< offset`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L312** `<< " total=" << pcm_data.size()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L313** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L316** `const int recover_rc = snd_pcm_recover(`：尝试从ALSA流错误恢复，已经发生的XRUN仍需记录。

- **L317** `pcm_,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L318** `static_cast<int>(written),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L319** `1`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L322** `if (recover_rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L324** `error = std::string("snd_pcm_recover: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L325** `snd_strerror(recover_rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L326** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L329** `if (++consecutive_recoveries > 5)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L331** `error = "Too many ALSA recoveries";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L332** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L337** `snd_pcm_state_t state = snd_pcm_state(pcm_);`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L339** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L340** `<< "[ALSA write]"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L341** `<< " submitted_frames=" << offset`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L342** `<< " state=" << snd_pcm_state_name(state)`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L343** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L347** `if (state == SND_PCM_STATE_PREPARED)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L349** `rc = snd_pcm_start(pcm_);`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L351** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L353** `error = std::string("snd_pcm_start: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L354** `snd_strerror(rc);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L355** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L360** `rc = snd_pcm_drain(pcm_);`：等待ALSA把提交的播放队列实际耗尽，以免函数提前返回。

- **L362** `if (rc < 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L364** `if (rc == -EPIPE)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L366** `++xrun_count_;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L369** `state = snd_pcm_state(pcm_);`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L371** `error = std::string("snd_pcm_drain: ") +`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L372** `snd_strerror(rc) +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L373** `" state=" +`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L374** `snd_pcm_state_name(state);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L376** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L380** `if (xrun_count_ != 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L382** `error = "Playback completed with detected XRUN";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L383** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L386** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L389** `void AlsaPlaybackService::close() noexcept`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L391** `if (pcm_ != nullptr)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L393** `snd_pcm_close(pcm_);`：回收ALSA PCM句柄，遵守Worker先join再关闭服务顺序。

- **L394** `pcm_ = nullptr;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L397** `sample_rate_ = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L398** `xrun_count_ = 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

## 真实源文件：`src/audio/tts_playback_smoke.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_playback_smoke.cpp`。归档长度 **192 行**，SHA\-256 完整值 `55553c6370de604b1deeb7d4b4d3dffd6c78dbb44742f36982891de98e13c7c1`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"

#include <chrono>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 6)
    {
        std::cerr
            << "Usage:\n"
            << "tts_playback_smoke "
            << "<model_dir> <device> <text> "
            << "<threads> <speaker_id>\n";

        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];
    const std::string text = argv[3];

    std::int32_t threads = 2;
    std::int32_t speaker_id = 17;

    try
    {
        std::size_t used_threads = 0;
        std::size_t used_speaker = 0;

        const std::string threads_arg = argv[4];
        const std::string speaker_arg = argv[5];

        threads = std::stoi(
            threads_arg, &used_threads
        );

        speaker_id = std::stoi(
            speaker_arg, &used_speaker
        );

        if (used_threads != threads_arg.size() ||
            used_speaker != speaker_arg.size() ||
            threads < 1 || threads > 8 ||
            speaker_id < 0)
        {
            throw std::invalid_argument("Invalid arguments");
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "Invalid threads or speaker_id\n";

        return 2;
    }

    std::string error;
    TTSService tts;
    TTSAudio audio;

    // 1. 初始化 TTS 模型。
    std::cout << "[Init] Loading TTS...\n"
              << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            speaker_id))
    {
        std::cerr
            << "[Init] FAIL: " << error << '\n';

        return 1;
    }

    const auto init_end =
        std::chrono::steady_clock::now();

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            init_end - init_start
        ).count();

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Init] OK"
        << " init_ms=" << init_ms
        << " sample_rate=" << tts.sampleRate()
        << " speakers=" << tts.numSpeakers()
        << " sid=" << tts.speakerId()
        << '\n';

    // 2. 进行 TTS 推理。
    std::cout
        << "[TTS] text=" << text << '\n'
        << std::flush;

    if (!tts.synthesize(text, audio, error))
    {
        std::cerr
            << "[TTS] FAIL: " << error << '\n';

        return 1;
    }

    if (audio.sample_rate <= 0 ||
        audio.samples.empty())
    {
        std::cerr
            << "[TTS] Invalid output audio\n";

        return 1;
    }

    const double audio_sec =
        static_cast<double>(audio.samples.size()) /
        audio.sample_rate;

    const double rtf =
        (audio.synthesis_ms / 1000.0) / audio_sec;

    std::cout
        << "[TTS] synth_ms=" << audio.synthesis_ms
        << " audio_sec=" << audio_sec
        << " RTF=" << rtf
        << '\n';

    // 3. 打开 ALSA Playback。
    AlsaPlaybackService playback;

    if (!playback.open(
            device,
            audio.sample_rate,
            error))
    {
        std::cerr
            << "[ALSA] Open FAIL: " << error << '\n';

        return 1;
    }

    std::cout
        << "[ALSA] Device=" << device
        << " sample_rate=" << audio.sample_rate
        << '\n'
        << "[ALSA] Starting playback...\n"
        << std::flush;

    // 4. 直接播放内存中的 float PCM。
    const auto play_start =
        std::chrono::steady_clock::now();

    if (!playback.play(
            audio.samples.data(),
            audio.samples.size(),
            error))
    {
        std::cerr
            << "[ALSA] Playback FAIL: "
            << error << '\n';

        return 1;
    }

    const auto play_end =
        std::chrono::steady_clock::now();

    const double play_ms =
        std::chrono::duration<double, std::milli>(
            play_end - play_start
        ).count();

    std::cout
        << "[ALSA] playback_ms=" << play_ms
        << " xrun_count=" << playback.xrunCount()
        << '\n'
        << "PASS\n";

    return 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L3** `#include "audio/alsa_playback_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <iomanip>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `int main(int argc, char** argv)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L14** `if (argc != 6)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L16** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L17** `<< "Usage:\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L18** `<< "tts_playback_smoke "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L19** `<< "<model_dir> <device> <text> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L20** `<< "<threads> <speaker_id>\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L22** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L25** `const std::string model_dir = argv[1];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L26** `const std::string device = argv[2];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L27** `const std::string text = argv[3];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L29** `std::int32_t threads = 2;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L30** `std::int32_t speaker_id = 17;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L32** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L34** `std::size_t used_threads = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L35** `std::size_t used_speaker = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L37** `const std::string threads_arg = argv[4];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L38** `const std::string speaker_arg = argv[5];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L40** `threads = std::stoi(`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L41** `threads_arg, &used_threads`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L44** `speaker_id = std::stoi(`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L45** `speaker_arg, &used_speaker`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L48** `if (used_threads != threads_arg.size() ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L49** `used_speaker != speaker_arg.size() ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L50** `threads < 1 || threads > 8 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L51** `speaker_id < 0)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L53** `throw std::invalid_argument("Invalid arguments");`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L56** `catch (const std::exception&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L58** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L59** `<< "Invalid threads or speaker_id\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L61** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L64** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L65** `TTSService tts;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L66** `TTSAudio audio;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L69** `std::cout << "[Init] Loading TTS...\n"`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L70** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L72** `const auto init_start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L73** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L75** `if (!tts.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L76** `model_dir,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L77** `error,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L78** `threads,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L79** `speaker_id))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L81** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L82** `<< "[Init] FAIL: " << error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L84** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L87** `const auto init_end =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L88** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L90** `const double init_ms =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L91** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L92** `init_end - init_start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L93** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L95** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L96** `<< std::fixed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L97** `<< std::setprecision(3)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L98** `<< "[Init] OK"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L99** `<< " init_ms=" << init_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L100** `<< " sample_rate=" << tts.sampleRate()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L101** `<< " speakers=" << tts.numSpeakers()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L102** `<< " sid=" << tts.speakerId()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L103** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L106** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L107** `<< "[TTS] text=" << text << '\n'`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L108** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L110** `if (!tts.synthesize(text, audio, error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L112** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L113** `<< "[TTS] FAIL: " << error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L115** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L118** `if (audio.sample_rate <= 0 ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L119** `audio.samples.empty())`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L121** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L122** `<< "[TTS] Invalid output audio\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L124** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L127** `const double audio_sec =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L128** `static_cast<double>(audio.samples.size()) /`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L129** `audio.sample_rate;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L131** `const double rtf =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L132** `(audio.synthesis_ms / 1000.0) / audio_sec;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L134** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L135** `<< "[TTS] synth_ms=" << audio.synthesis_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L136** `<< " audio_sec=" << audio_sec`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L137** `<< " RTF=" << rtf`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L138** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L141** `AlsaPlaybackService playback;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L143** `if (!playback.open(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L144** `device,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L145** `audio.sample_rate,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L146** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L148** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L149** `<< "[ALSA] Open FAIL: " << error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L151** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L154** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L155** `<< "[ALSA] Device=" << device`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L156** `<< " sample_rate=" << audio.sample_rate`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L157** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L158** `<< "[ALSA] Starting playback...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L159** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L162** `const auto play_start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L163** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L165** `if (!playback.play(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L166** `audio.samples.data(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L167** `audio.samples.size(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L168** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L170** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L171** `<< "[ALSA] Playback FAIL: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L172** `<< error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L174** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L177** `const auto play_end =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L178** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L180** `const double play_ms =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L181** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L182** `play_end - play_start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L183** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L185** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L186** `<< "[ALSA] playback_ms=" << play_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L187** `<< " xrun_count=" << playback.xrunCount()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L188** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L189** `<< "PASS\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L191** `return 0;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

## 真实源文件：`include/audio/tts_worker.h`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/tts_worker.h`。归档长度 **130 行**，SHA\-256 完整值 `5a78c0fbfe888b1920d4be37971d4de31eca1658474d544f144c0379f3597925`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include "audio/alsa_playback_service.h"
#include "audio/tts_service.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

// 任务提交状态。
// 与现有 LLMSubmitStatus 保持一致。
enum class TTSSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

// 一次 TTS 合成和播放的执行结果。
struct TTSWorkerResult
{
    bool success = false;

    std::string error_message;

    // TTS 模型合成耗时。
    double synthesis_ms = 0.0;

    // ALSA 播放调用耗时，包含 drain。
    double playback_ms = 0.0;

    // 生成的音频时长。
    double audio_seconds = 0.0;

    std::int32_t sample_rate = 0;

    // 本次播放检测到的 XRUN 数量。
    std::uint64_t xrun_count = 0;
};

// 完成回调参数：
// request_id、结果、等待队列耗时（ms）。
// 取消的任务使用 queue_wait_ms=-1。
using TTSWorkerDone = std::function<void(
    std::uint64_t,
    const TTSWorkerResult&,
    double
)>;

// 单消费者 + 有界 FIFO。
// 不拥有 TTSService / AlsaPlaybackService。
//
// 必须先初始化两个 Service，再启动 Worker。
// 回调在 Worker 线程执行；回调中不得销毁
// 或 join 当前 Worker。
class TTSWorker final
{
public:
    explicit TTSWorker(
        TTSService& tts,
        AlsaPlaybackService& playback,
        std::size_t capacity = 2
    );

    ~TTSWorker();

    TTSWorker(const TTSWorker&) = delete;
    TTSWorker& operator=(const TTSWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 非阻塞提交任务。
    TTSSubmitStatus submit(
        std::uint64_t id,
        std::string text,
        TTSWorkerDone on_done = {}
    );

    // 不再接收新任务。
    // 等待队列中的任务报告取消；
    // 正在执行的任务允许自然完成。
    void requestStop() noexcept;

    // 必须从非 Worker 线程调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;

private:
    struct Task
    {
        std::uint64_t id = 0;

        std::string text;

        TTSWorkerDone on_done;

        std::chrono::steady_clock::time_point
            enqueued_at{};
    };

    void run();

    // 外部对象引用，不负责销毁。
    TTSService& tts_;
    AlsaPlaybackService& playback_;

    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;

    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;

    std::size_t rejected_ = 0;
};
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#pragma once`：头文件防重复包含，避免类和结构在同一编译单元中重定义。

- **L4** `#include "audio/alsa_playback_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include "audio/tts_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <condition_variable>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <cstddef>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L11** `#include <deque>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `#include <functional>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L13** `#include <mutex>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L14** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L15** `#include <thread>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L19** `enum class TTSSubmitStatus`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L21** `Accepted,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L22** `NotRunning,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L23** `QueueFull`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L27** `struct TTSWorkerResult`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L29** `bool success = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L31** `std::string error_message;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L34** `double synthesis_ms = 0.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L37** `double playback_ms = 0.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L40** `double audio_seconds = 0.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L42** `std::int32_t sample_rate = 0;`：固定宽度32位整数，常用于采样率、SDK字段。

- **L45** `std::uint64_t xrun_count = 0;`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L51** `using TTSWorkerDone = std::function<void(`：回调类型擦除包装器，可持有捕获Lambda。

- **L52** `std::uint64_t,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L53** `const TTSWorkerResult&,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L54** `double`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L55** `)>;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L63** `class TTSWorker final`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L65** `public:`：访问控制域标签，决定成员能否从类外直接访问。

- **L66** `explicit TTSWorker(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L67** `TTSService& tts,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L68** `AlsaPlaybackService& playback,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L69** `std::size_t capacity = 2`：与容器大小/样本数量相配套的无符号整数类型。

- **L72** `~TTSWorker();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L74** `TTSWorker(const TTSWorker&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L75** `TTSWorker& operator=(const TTSWorker&) = delete;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L78** `bool start(std::string& error);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L81** `TTSSubmitStatus submit(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L82** `std::uint64_t id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L83** `std::string text,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L84** `TTSWorkerDone on_done = {}`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L90** `void requestStop() noexcept;`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L93** `void join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L95** `std::size_t pendingCount() const;`：与容器大小/样本数量相配套的无符号整数类型。

- **L96** `std::size_t rejectedCount() const;`：与容器大小/样本数量相配套的无符号整数类型。

- **L98** `private:`：访问控制域标签，决定成员能否从类外直接访问。

- **L99** `struct Task`：定义类/结构/强类型枚举，约束对象生命周期与 API/状态。

- **L101** `std::uint64_t id = 0;`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L103** `std::string text;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L105** `TTSWorkerDone on_done;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L107** `std::chrono::steady_clock::time_point`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L108** `enqueued_at{};`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L111** `void run();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L114** `TTSService& tts_;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L115** `AlsaPlaybackService& playback_;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L117** `const std::size_t capacity_;`：与容器大小/样本数量相配套的无符号整数类型。

- **L119** `mutable std::mutex mutex_;`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L120** `std::condition_variable cv_;`：多线程事件通知机制；实际条件由mutex保护的共享计数或队列状态决定。

- **L122** `std::deque<Task> pending_;`：可高效从首端取出任务的FIFO队列，capacity限制等待中的任务。

- **L124** `std::thread thread_;`：启动/管理C\+\+真实工作线程；线程必须被join或显式detach，项目用join保证安全退出。

- **L126** `bool started_ = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L127** `bool stop_requested_ = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L129** `std::size_t rejected_ = 0;`：与容器大小/样本数量相配套的无符号整数类型。

## 真实源文件：`src/audio/tts_worker.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_worker.cpp`。归档长度 **301 行**，SHA\-256 完整值 `590e9676d023d228c0aaf39e1106538f171f7d1577c17981137e2598f4a22b54`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_worker.h"

#include <exception>
#include <stdexcept>
#include <utility>

TTSWorker::TTSWorker(
    TTSService& tts,
    AlsaPlaybackService& playback,
    std::size_t capacity)
    : tts_(tts),
      playback_(playback),
      capacity_(capacity)
{
    if (capacity_ == 0)
    {
        throw std::invalid_argument(
            "TTSWorker capacity must be > 0"
        );
    }
}

TTSWorker::~TTSWorker()
{
    requestStop();
    join();
}

bool TTSWorker::start(std::string& error)
{
    std::lock_guard<std::mutex> lock(mutex_);
    error.clear();

    if (started_ || stop_requested_)
    {
        error =
            "TTSWorker can only be started once";
        return false;
    }

    // 两个 Service 必须事先初始化。
    if (!tts_.ready() || !playback_.ready())
    {
        error =
            "Initialize TTSService and ALSA Playback "
            "before starting TTSWorker";
        return false;
    }

    try
    {
        // 启动 TTSWorker::run() 工作线程。
        thread_ = std::thread(
            &TTSWorker::run,
            this
        );

        started_ = true;
    }
    catch (const std::exception& e)
    {
        error =
            std::string(
                "TTSWorker thread creation failed: "
            ) + e.what();

        return false;
    }

    return true;
}

TTSSubmitStatus TTSWorker::submit(
    std::uint64_t id,
    std::string text,
    TTSWorkerDone on_done)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
        {
            return TTSSubmitStatus::NotRunning;
        }

        if (pending_.size() >= capacity_)
        {
            ++rejected_;
            return TTSSubmitStatus::QueueFull;
        }

        Task task;
        task.id = id;
        task.text = std::move(text);
        task.on_done = std::move(on_done);

        task.enqueued_at =
            std::chrono::steady_clock::now();

        pending_.push_back(std::move(task));
    }

    // 通知一个等待中的消费者线程。
    cv_.notify_one();

    return TTSSubmitStatus::Accepted;
}

void TTSWorker::requestStop() noexcept
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        stop_requested_ = true;
    }

    // 唤醒线程，让它处理停止请求。
    cv_.notify_all();
}

void TTSWorker::join()
{
    if (thread_.joinable())
    {
        thread_.join();
    }
}

std::size_t TTSWorker::pendingCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return pending_.size();
}

std::size_t TTSWorker::rejectedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);

    return rejected_;
}

void TTSWorker::run()
{
    for (;;)
    {
        Task task;
        bool cancelled = false;

        {
            std::unique_lock<std::mutex> lock(mutex_);

            // 没有任务时休眠，不进行忙轮询。
            cv_.wait(lock, [this] {
                return stop_requested_ ||
                       !pending_.empty();
            });

            // 队列清空且要求停止时，退出线程。
            if (pending_.empty() && stop_requested_)
            {
                return;
            }

            // FIFO：取出队首任务。
            task = std::move(pending_.front());
            pending_.pop_front();

            // 停止请求到来后，
            // 尚未开始的排队任务转为取消结果。
            cancelled = stop_requested_;
        }

        TTSWorkerResult result;

        double queue_wait_ms = -1.0;

        if (cancelled)
        {
            result.error_message =
                "TTS task cancelled: worker stopping";
        }
        else
        {
            // 等待队列的耗时。
            queue_wait_ms =
                std::chrono::duration<double, std::milli>(
                    std::chrono::steady_clock::now() -
                    task.enqueued_at
                ).count();

            try
            {
                TTSAudio audio;
                std::string error;

                // 1. 在工作线程中执行 TTS。
                if (!tts_.synthesize(
                        task.text, audio, error))
                {
                    result.error_message =
                        "TTS synthesize: " + error;
                }
                else if (
                    audio.sample_rate <= 0 ||
                    audio.samples.empty())
                {
                    result.error_message =
                        "TTS returned invalid PCM";
                }
                else
                {
                    result.synthesis_ms =
                        audio.synthesis_ms;

                    result.sample_rate =
                        audio.sample_rate;

                    result.audio_seconds =
                        static_cast<double>(
                            audio.samples.size()
                        ) / audio.sample_rate;

                    // 记录本次播放前的 XRUN 总数。
                    const std::uint64_t xruns_before =
                        playback_.xrunCount();

                    const auto play_start =
                        std::chrono::steady_clock::now();

                    // 2. 在同一工作线程中播放 PCM。
                    const bool played = playback_.play(
                        audio.samples.data(),
                        audio.samples.size(),
                        error
                    );

                    const auto play_end =
                        std::chrono::steady_clock::now();

                    result.playback_ms =
                        std::chrono::duration<
                            double, std::milli
                        >(
                            play_end - play_start
                        ).count();

                    result.xrun_count =
                        playback_.xrunCount() -
                        xruns_before;

                    if (!played)
                    {
                        result.error_message =
                            "ALSA playback: " + error;
                    }
                    else if (result.xrun_count != 0)
                    {
                        result.error_message =
                            "ALSA detected XRUN";
                    }
                    else
                    {
                        result.success = true;
                    }
                }
            }
            catch (const std::exception& e)
            {
                result.error_message =
                    std::string(
                        "TTSWorker exception: "
                    ) + e.what();
            }
            catch (...)
            {
                result.error_message =
                    "TTSWorker: unknown exception";
            }
        }

        // 3. 处理完成或取消后，通知业务层。
        // 不持有 mutex_ 执行用户回调。
        if (task.on_done)
        {
            try
            {
                task.on_done(
                    task.id,
                    result,
                    queue_wait_ms
                );
            }
            catch (...)
            {
                // 回调异常不能杀死工作线程。
            }
        }
    }
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <stdexcept>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <utility>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `TTSWorker::TTSWorker(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L9** `TTSService& tts,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L10** `AlsaPlaybackService& playback,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L11** `std::size_t capacity)`：与容器大小/样本数量相配套的无符号整数类型。

- **L12** `: tts_(tts),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L13** `playback_(playback),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L14** `capacity_(capacity)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L16** `if (capacity_ == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L18** `throw std::invalid_argument(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L19** `"TTSWorker capacity must be > 0"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L24** `TTSWorker::~TTSWorker()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L26** `requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L27** `join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L30** `bool TTSWorker::start(std::string& error)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L32** `std::lock_guard<std::mutex> lock(mutex_);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L33** `error.clear();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L35** `if (started_ || stop_requested_)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L37** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L38** `"TTSWorker can only be started once";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L39** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L43** `if (!tts_.ready() || !playback_.ready())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L45** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L46** `"Initialize TTSService and ALSA Playback "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L47** `"before starting TTSWorker";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L48** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L51** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L54** `thread_ = std::thread(`：启动/管理C\+\+真实工作线程；线程必须被join或显式detach，项目用join保证安全退出。

- **L55** `&TTSWorker::run,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L56** `this`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L59** `started_ = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L61** `catch (const std::exception& e)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L63** `error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L64** `std::string(`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L65** `"TTSWorker thread creation failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L66** `) + e.what();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L68** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L71** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L74** `TTSSubmitStatus TTSWorker::submit(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L75** `std::uint64_t id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L76** `std::string text,`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L77** `TTSWorkerDone on_done)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L80** `std::lock_guard<std::mutex> lock(mutex_);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L82** `if (!started_ || stop_requested_)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L84** `return TTSSubmitStatus::NotRunning;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L87** `if (pending_.size() >= capacity_)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L89** `++rejected_;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L90** `return TTSSubmitStatus::QueueFull;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L93** `Task task;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L94** `task.id = id;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L95** `task.text = std::move(text);`：`std::move` 是右值转换，允许字符串或任务移动资源，不能无条件宣称零拷贝。

- **L96** `task.on_done = std::move(on_done);`：`std::move` 是右值转换，允许字符串或任务移动资源，不能无条件宣称零拷贝。

- **L98** `task.enqueued_at =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L99** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L101** `pending_.push_back(std::move(task));`：`std::move` 是右值转换，允许字符串或任务移动资源，不能无条件宣称零拷贝。

- **L105** `cv_.notify_one();`：通知一个等待线程从FIFO消费任务，必须和锁内任务入队顺序一致。

- **L107** `return TTSSubmitStatus::Accepted;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L110** `void TTSWorker::requestStop() noexcept`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L113** `std::lock_guard<std::mutex> lock(mutex_);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L115** `stop_requested_ = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L119** `cv_.notify_all();`：通知所有等待线程重新检查条件，并不代表任务必然成功。

- **L122** `void TTSWorker::join()`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L124** `if (thread_.joinable())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L126** `thread_.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L130** `std::size_t TTSWorker::pendingCount() const`：与容器大小/样本数量相配套的无符号整数类型。

- **L132** `std::lock_guard<std::mutex> lock(mutex_);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L134** `return pending_.size();`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L137** `std::size_t TTSWorker::rejectedCount() const`：与容器大小/样本数量相配套的无符号整数类型。

- **L139** `std::lock_guard<std::mutex> lock(mutex_);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L141** `return rejected_;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L144** `void TTSWorker::run()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L146** `for (;;)`：循环控制语句，注意终止条件和迭代后状态更新。

- **L148** `Task task;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L149** `bool cancelled = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L152** `std::unique_lock<std::mutex> lock(mutex_);`：`std::unique_lock<std::mutex>` 是可解锁/重锁的互斥锁拥有者，适配条件变量的等待。

- **L155** `cv_.wait(lock, [this] {`：条件变量阻塞消费线程直到队列非空或停止，避免CPU空转与丢通知。

- **L156** `return stop_requested_ ||`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L157** `!pending_.empty();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L158** `});`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L161** `if (pending_.empty() && stop_requested_)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L163** `return;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L167** `task = std::move(pending_.front());`：`std::move` 是右值转换，允许字符串或任务移动资源，不能无条件宣称零拷贝。

- **L168** `pending_.pop_front();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L172** `cancelled = stop_requested_;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L175** `TTSWorkerResult result;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L177** `double queue_wait_ms = -1.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L179** `if (cancelled)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L181** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L182** `"TTS task cancelled: worker stopping";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L184** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L187** `queue_wait_ms =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L188** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L189** `std::chrono::steady_clock::now() -`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L190** `task.enqueued_at`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L191** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L193** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L195** `TTSAudio audio;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L196** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L199** `if (!tts_.synthesize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L200** `task.text, audio, error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L202** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L203** `"TTS synthesize: " + error;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L205** `else if (`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L206** `audio.sample_rate <= 0 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L207** `audio.samples.empty())`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L209** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L210** `"TTS returned invalid PCM";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L212** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L214** `result.synthesis_ms =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L215** `audio.synthesis_ms;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L217** `result.sample_rate =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L218** `audio.sample_rate;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L220** `result.audio_seconds =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L221** `static_cast<double>(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L222** `audio.samples.size()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L223** `) / audio.sample_rate;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L226** `const std::uint64_t xruns_before =`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L227** `playback_.xrunCount();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L229** `const auto play_start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L230** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L233** `const bool played = playback_.play(`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L234** `audio.samples.data(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L235** `audio.samples.size(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L236** `error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L239** `const auto play_end =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L240** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L242** `result.playback_ms =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L243** `std::chrono::duration<`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L244** `double, std::milli`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L245** `>(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L246** `play_end - play_start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L247** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L249** `result.xrun_count =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L250** `playback_.xrunCount() -`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L251** `xruns_before;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L253** `if (!played)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L255** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L256** `"ALSA playback: " + error;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L258** `else if (result.xrun_count != 0)`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L260** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L261** `"ALSA detected XRUN";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L263** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L265** `result.success = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L269** `catch (const std::exception& e)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L271** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L272** `std::string(`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L273** `"TTSWorker exception: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L274** `) + e.what();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L276** `catch (...)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L278** `result.error_message =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L279** `"TTSWorker: unknown exception";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L285** `if (task.on_done)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L287** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L289** `task.on_done(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L290** `task.id,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L291** `result,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L292** `queue_wait_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L295** `catch (...)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

## 真实源文件：`src/audio/tts_worker_smoke.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_worker_smoke.cpp`。归档长度 **231 行**，SHA\-256 完整值 `b0a6c515ad88cd7d110f662e28bafcef1c65dc787161b5104c5e222f38b3ac5a`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_worker.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>

int main(int argc, char** argv)
{
    if (argc != 6)
    {
        std::cerr
            << "Usage: tts_worker_smoke "
            << "<model_dir> <device> <text> "
            << "<threads> <speaker_id>\n";

        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];
    const std::string text = argv[3];

    int threads = 2;
    int sid = 17;

    try
    {
        const std::string threads_arg = argv[4];
        const std::string sid_arg = argv[5];

        std::size_t n1 = 0;
        std::size_t n2 = 0;

        threads = std::stoi(threads_arg, &n1);
        sid = std::stoi(sid_arg, &n2);

        if (n1 != threads_arg.size() ||
            n2 != sid_arg.size() ||
            threads < 1 ||
            threads > 8 ||
            sid < 0)
        {
            throw std::invalid_argument(
                "Invalid threads or sid"
            );
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "Invalid threads or speaker_id\n";

        return 2;
    }

    std::string error;

    // 先创建并初始化两个 Service。
    TTSService tts;
    AlsaPlaybackService playback;

    std::cout
        << "[Init] Loading TTS model...\n"
        << std::flush;

    const auto init_start =
        std::chrono::steady_clock::now();

    if (!tts.initialize(
            model_dir,
            error,
            threads,
            sid))
    {
        std::cerr
            << "[Init] FAIL: "
            << error << '\n';

        return 1;
    }

    const double init_ms =
        std::chrono::duration<double, std::milli>(
            std::chrono::steady_clock::now() -
            init_start
        ).count();

    std::cout
        << "[Init] OK init_ms="
        << init_ms << '\n';

    // ALSA 使用 TTS 模型的实际采样率。
    if (!playback.open(
            device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[ALSA] Open FAIL: "
            << error << '\n';

        return 1;
    }

    // Worker 最后构造，确保它最先析构。
    TTSWorker worker(tts, playback, 2);

    if (!worker.start(error))
    {
        std::cerr
            << "[Worker] Start FAIL: "
            << error << '\n';

        return 1;
    }

    // 主线程用于接收完成回调的同步变量。
    std::mutex done_mutex;
    std::condition_variable done_cv;

    bool finished = false;

    TTSWorkerResult final_result;
    double queue_wait_ms = -1.0;

    // 提交一个真实 TTS 播放任务。
    const auto status = worker.submit(
        1,
        text,
        [&](std::uint64_t id,
            const TTSWorkerResult& result,
            double queue_ms)
        {
            if (id != 1)
            {
                return;
            }

            {
                std::lock_guard<std::mutex>
                    lock(done_mutex);

                final_result = result;
                queue_wait_ms = queue_ms;
                finished = true;
            }

            done_cv.notify_one();
        }
    );

    if (status != TTSSubmitStatus::Accepted)
    {
        std::cerr
            << "[Main] submit rejected\n";

        worker.requestStop();
        worker.join();

        return 1;
    }

    // 这条日志应在 TTS 合成完成前出现。
    std::cout
        << "[Main] submit accepted; "
        << "main thread remains responsive\n"
        << std::flush;

    // 主线程阻塞等待“完成通知”，
    // 但不负责执行 TTS 推理或音频播放。
    bool completed = false;

    {
        std::unique_lock<std::mutex>
            lock(done_mutex);

        completed = done_cv.wait_for(
            lock,
            std::chrono::seconds(180),
            [&] {
                return finished;
            }
        );
    }

    // 退出前执行安全停止。
    worker.requestStop();
    worker.join();

    if (!completed)
    {
        std::cerr
            << "[Worker] FAIL: completion timeout\n";

        return 1;
    }

    std::cout
        << std::fixed
        << std::setprecision(3)
        << "[Done] success="
        << std::boolalpha
        << final_result.success
        << " queue_ms=" << queue_wait_ms
        << " synth_ms=" << final_result.synthesis_ms
        << " audio_sec=" << final_result.audio_seconds
        << " playback_ms=" << final_result.playback_ms
        << " xrun_count=" << final_result.xrun_count
        << '\n';

    if (!final_result.success)
    {
        std::cerr
            << "[Done] error="
            << final_result.error_message
            << '\n';

        return 1;
    }

    std::cout << "PASS\n";

    return 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <condition_variable>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <iomanip>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <mutex>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L11** `#include <stdexcept>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L14** `int main(int argc, char** argv)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L16** `if (argc != 6)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L18** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L19** `<< "Usage: tts_worker_smoke "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L20** `<< "<model_dir> <device> <text> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L21** `<< "<threads> <speaker_id>\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L23** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L26** `const std::string model_dir = argv[1];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L27** `const std::string device = argv[2];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L28** `const std::string text = argv[3];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L30** `int threads = 2;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L31** `int sid = 17;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L33** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L35** `const std::string threads_arg = argv[4];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L36** `const std::string sid_arg = argv[5];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L38** `std::size_t n1 = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L39** `std::size_t n2 = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L41** `threads = std::stoi(threads_arg, &n1);`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L42** `sid = std::stoi(sid_arg, &n2);`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L44** `if (n1 != threads_arg.size() ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L45** `n2 != sid_arg.size() ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L46** `threads < 1 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L47** `threads > 8 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L48** `sid < 0)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L50** `throw std::invalid_argument(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L51** `"Invalid threads or sid"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L55** `catch (const std::exception&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L57** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L58** `<< "Invalid threads or speaker_id\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L60** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L63** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L66** `TTSService tts;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L67** `AlsaPlaybackService playback;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L69** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L70** `<< "[Init] Loading TTS model...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L71** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L73** `const auto init_start =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L74** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L76** `if (!tts.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L77** `model_dir,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L78** `error,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L79** `threads,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L80** `sid))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L82** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L83** `<< "[Init] FAIL: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L84** `<< error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L86** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L89** `const double init_ms =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L90** `std::chrono::duration<double, std::milli>(`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L91** `std::chrono::steady_clock::now() -`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L92** `init_start`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L93** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L95** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L96** `<< "[Init] OK init_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L97** `<< init_ms << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L100** `if (!playback.open(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L101** `device,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L102** `tts.sampleRate(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L103** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L105** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L106** `<< "[ALSA] Open FAIL: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L107** `<< error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L109** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L113** `TTSWorker worker(tts, playback, 2);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L115** `if (!worker.start(error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L117** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L118** `<< "[Worker] Start FAIL: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L119** `<< error << '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L121** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L125** `std::mutex done_mutex;`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L126** `std::condition_variable done_cv;`：多线程事件通知机制；实际条件由mutex保护的共享计数或队列状态决定。

- **L128** `bool finished = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L130** `TTSWorkerResult final_result;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L131** `double queue_wait_ms = -1.0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L134** `const auto status = worker.submit(`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L135** `1,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L136** `text,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L137** `[&](std::uint64_t id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L138** `const TTSWorkerResult& result,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L139** `double queue_ms)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L141** `if (id != 1)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L143** `return;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L147** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L148** `lock(done_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L150** `final_result = result;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L151** `queue_wait_ms = queue_ms;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L152** `finished = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L155** `done_cv.notify_one();`：通知一个等待线程从FIFO消费任务，必须和锁内任务入队顺序一致。

- **L159** `if (status != TTSSubmitStatus::Accepted)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L161** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L162** `<< "[Main] submit rejected\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L164** `worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L165** `worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L167** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L171** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L172** `<< "[Main] submit accepted; "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L173** `<< "main thread remains responsive\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L174** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L178** `bool completed = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L181** `std::unique_lock<std::mutex>`：`std::unique_lock<std::mutex>` 是可解锁/重锁的互斥锁拥有者，适配条件变量的等待。

- **L182** `lock(done_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L184** `completed = done_cv.wait_for(`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L185** `lock,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L186** `std::chrono::seconds(180),`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L187** `[&] {`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L188** `return finished;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L194** `worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L195** `worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L197** `if (!completed)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L199** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L200** `<< "[Worker] FAIL: completion timeout\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L202** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L205** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L206** `<< std::fixed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L207** `<< std::setprecision(3)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L208** `<< "[Done] success="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L209** `<< std::boolalpha`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L210** `<< final_result.success`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L211** `<< " queue_ms=" << queue_wait_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L212** `<< " synth_ms=" << final_result.synthesis_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L213** `<< " audio_sec=" << final_result.audio_seconds`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L214** `<< " playback_ms=" << final_result.playback_ms`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L215** `<< " xrun_count=" << final_result.xrun_count`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L216** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L218** `if (!final_result.success)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L220** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L221** `<< "[Done] error="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L222** `<< final_result.error_message`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L223** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L225** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L228** `std::cout << "PASS\n";`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L230** `return 0;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

## 真实源文件：`src/audio/tts_worker_queue_smoke.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/tts_worker_queue_smoke.cpp`。归档长度 **245 行**，SHA\-256 完整值 `9bfd8faba054eb20662a21c063fb3436fb1dd4fdbb5d37854fac70f6f1a638a1`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/tts_worker.h"

#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <exception>
#include <iostream>
#include <mutex>
#include <stdexcept>
#include <string>
#include <thread>

int main(int argc, char** argv)
{
    if (argc != 5)
    {
        std::cerr
            << "Usage: tts_worker_queue_smoke "
            << "<model_dir> <device> <threads> <sid>\n";
        return 2;
    }

    const std::string model_dir = argv[1];
    const std::string device = argv[2];

    int threads = 2;
    int sid = 17;

    try
    {
        std::size_t n1 = 0;
        std::size_t n2 = 0;

        const std::string arg_threads = argv[3];
        const std::string arg_sid = argv[4];

        threads = std::stoi(arg_threads, &n1);
        sid = std::stoi(arg_sid, &n2);

        if (n1 != arg_threads.size() ||
            n2 != arg_sid.size() ||
            threads < 1 || threads > 8 ||
            sid < 0)
        {
            throw std::invalid_argument("invalid argument");
        }
    }
    catch (const std::exception&)
    {
        std::cerr << "[Args] Invalid threads or sid\n";
        return 2;
    }

    TTSService tts;
    AlsaPlaybackService playback;
    std::string error;

    std::cout << "[Init] Loading Kokoro...\n"
              << std::flush;

    if (!tts.initialize(model_dir, error, threads, sid))
    {
        std::cerr << "[Init] FAIL: " << error << '\n';
        return 1;
    }

    if (!playback.open(device, tts.sampleRate(), error))
    {
        std::cerr << "[ALSA] FAIL: " << error << '\n';
        return 1;
    }

    std::mutex done_mutex;
    std::condition_variable done_cv;

    bool first_done = false;
    bool second_done = false;

    TTSWorkerResult first_result;
    TTSWorkerResult second_result;

    // 只允许一个等待任务。
    TTSWorker worker(tts, playback, 1);

    if (!worker.start(error))
    {
        std::cerr << "[Worker] FAIL: " << error << '\n';
        return 1;
    }

    // 第一个任务：应当正常执行并播放。
    const auto s1 = worker.submit(
        101,
        "你好，我是你的智能语音助手。",
        [&](std::uint64_t,
            const TTSWorkerResult& result,
            double)
        {
            {
                std::lock_guard<std::mutex> lock(done_mutex);
                first_result = result;
                first_done = true;
            }
            done_cv.notify_all();
        }
    );

    if (s1 != TTSSubmitStatus::Accepted)
    {
        std::cerr << "[Task 101] Not accepted\n";
        worker.requestStop();
        worker.join();
        return 1;
    }

    // 等待 Task 101 从 FIFO 取出。
    // 此时它正在执行或即将执行，等待队列为空。
    bool dequeued = false;

    for (int i = 0; i < 200; ++i)
    {
        if (worker.pendingCount() == 0)
        {
            dequeued = true;
            break;
        }

        std::this_thread::sleep_for(
            std::chrono::milliseconds(10)
        );
    }

    if (!dequeued)
    {
        std::cerr << "[Test] Task 101 not dequeued\n";
        worker.requestStop();
        worker.join();
        return 1;
    }

    // 第二个任务：应该进入唯一的等待位置。
    const auto s2 = worker.submit(
        102,
        "这个排队任务应该被取消。",
        [&](std::uint64_t,
            const TTSWorkerResult& result,
            double)
        {
            {
                std::lock_guard<std::mutex> lock(done_mutex);
                second_result = result;
                second_done = true;
            }
            done_cv.notify_all();
        }
    );

    // 第三个任务：队列已满，应该被拒绝。
    const auto s3 = worker.submit(
        103,
        "这条任务不应该进入队列。"
    );

    std::cout
        << "[Queue] task101=Accepted"
        << " task102="
        << (s2 == TTSSubmitStatus::Accepted
                ? "Accepted" : "Unexpected")
        << " task103="
        << (s3 == TTSSubmitStatus::QueueFull
                ? "QueueFull" : "Unexpected")
        << " pending=" << worker.pendingCount()
        << '\n'
        << std::flush;

    // 请求停止：Task 101 自然完成，
    // Task 102 应报告取消。
    worker.requestStop();

    // 停止后的新任务必须被拒绝。
    const auto s4 = worker.submit(
        104,
        "停止后不能接受这条任务。"
    );

    std::cout
        << "[Stop] task104="
        << (s4 == TTSSubmitStatus::NotRunning
                ? "NotRunning" : "Unexpected")
        << '\n'
        << std::flush;

    // 等待两个被接受任务的完成/取消回调。
    bool callbacks_received = false;

    {
        std::unique_lock<std::mutex> lock(done_mutex);

        callbacks_received = done_cv.wait_for(
            lock,
            std::chrono::seconds(120),
            [&] {
                return first_done && second_done;
            }
        );
    }

    worker.join();

    const bool first_ok =
        first_done && first_result.success;

    const bool cancelled_ok =
        second_done &&
        !second_result.success &&
        second_result.error_message.find("cancelled") !=
            std::string::npos;

    const bool queue_ok =
        s2 == TTSSubmitStatus::Accepted &&
        s3 == TTSSubmitStatus::QueueFull &&
        s4 == TTSSubmitStatus::NotRunning &&
        worker.rejectedCount() == 1;

    std::cout
        << std::boolalpha
        << "[Result] callbacks=" << callbacks_received
        << " first_success=" << first_ok
        << " second_cancelled=" << cancelled_ok
        << " rejected_count=" << worker.rejectedCount()
        << '\n';

    if (!callbacks_received ||
        !first_ok ||
        !cancelled_ok ||
        !queue_ok)
    {
        std::cerr << "FAIL\n";
        return 1;
    }

    std::cout << "PASS\n";
    return 0;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/tts_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include <condition_variable>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L8** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include <mutex>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include <stdexcept>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L11** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L12** `#include <thread>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L14** `int main(int argc, char** argv)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L16** `if (argc != 5)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L18** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L19** `<< "Usage: tts_worker_queue_smoke "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L20** `<< "<model_dir> <device> <threads> <sid>\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L21** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L24** `const std::string model_dir = argv[1];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L25** `const std::string device = argv[2];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L27** `int threads = 2;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L28** `int sid = 17;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L30** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L32** `std::size_t n1 = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L33** `std::size_t n2 = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L35** `const std::string arg_threads = argv[3];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L36** `const std::string arg_sid = argv[4];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L38** `threads = std::stoi(arg_threads, &n1);`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L39** `sid = std::stoi(arg_sid, &n2);`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L41** `if (n1 != arg_threads.size() ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L42** `n2 != arg_sid.size() ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L43** `threads < 1 || threads > 8 ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L44** `sid < 0)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L46** `throw std::invalid_argument("invalid argument");`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L49** `catch (const std::exception&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L51** `std::cerr << "[Args] Invalid threads or sid\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L52** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L55** `TTSService tts;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L56** `AlsaPlaybackService playback;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L57** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L59** `std::cout << "[Init] Loading Kokoro...\n"`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L60** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L62** `if (!tts.initialize(model_dir, error, threads, sid))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L64** `std::cerr << "[Init] FAIL: " << error << '\n';`：把失败诊断写stderr，便于区别正常标准日志。

- **L65** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L68** `if (!playback.open(device, tts.sampleRate(), error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L70** `std::cerr << "[ALSA] FAIL: " << error << '\n';`：把失败诊断写stderr，便于区别正常标准日志。

- **L71** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L74** `std::mutex done_mutex;`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L75** `std::condition_variable done_cv;`：多线程事件通知机制；实际条件由mutex保护的共享计数或队列状态决定。

- **L77** `bool first_done = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L78** `bool second_done = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L80** `TTSWorkerResult first_result;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L81** `TTSWorkerResult second_result;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L84** `TTSWorker worker(tts, playback, 1);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L86** `if (!worker.start(error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L88** `std::cerr << "[Worker] FAIL: " << error << '\n';`：把失败诊断写stderr，便于区别正常标准日志。

- **L89** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L93** `const auto s1 = worker.submit(`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L94** `101,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L95** `"你好，我是你的智能语音助手。",`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L96** `[&](std::uint64_t,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L97** `const TTSWorkerResult& result,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L98** `double)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L101** `std::lock_guard<std::mutex> lock(done_mutex);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L102** `first_result = result;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L103** `first_done = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L105** `done_cv.notify_all();`：通知所有等待线程重新检查条件，并不代表任务必然成功。

- **L109** `if (s1 != TTSSubmitStatus::Accepted)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L111** `std::cerr << "[Task 101] Not accepted\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L112** `worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L113** `worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L114** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L119** `bool dequeued = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L121** `for (int i = 0; i < 200; ++i)`：循环控制语句，注意终止条件和迭代后状态更新。

- **L123** `if (worker.pendingCount() == 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L125** `dequeued = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L126** `break;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L129** `std::this_thread::sleep_for(`：标准库类型/成员/函数参与线程管理、容器或数据处理；`::`用于命名空间/类作用域限定。

- **L130** `std::chrono::milliseconds(10)`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L134** `if (!dequeued)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L136** `std::cerr << "[Test] Task 101 not dequeued\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L137** `worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L138** `worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L139** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L143** `const auto s2 = worker.submit(`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L144** `102,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L145** `"这个排队任务应该被取消。",`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L146** `[&](std::uint64_t,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L147** `const TTSWorkerResult& result,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L148** `double)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L151** `std::lock_guard<std::mutex> lock(done_mutex);`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L152** `second_result = result;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L153** `second_done = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L155** `done_cv.notify_all();`：通知所有等待线程重新检查条件，并不代表任务必然成功。

- **L160** `const auto s3 = worker.submit(`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L161** `103,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L162** `"这条任务不应该进入队列。"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L165** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L166** `<< "[Queue] task101=Accepted"`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L167** `<< " task102="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L168** `<< (s2 == TTSSubmitStatus::Accepted`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L169** `? "Accepted" : "Unexpected")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L170** `<< " task103="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L171** `<< (s3 == TTSSubmitStatus::QueueFull`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L172** `? "QueueFull" : "Unexpected")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L173** `<< " pending=" << worker.pendingCount()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L174** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L175** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L179** `worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L182** `const auto s4 = worker.submit(`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L183** `104,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L184** `"停止后不能接受这条任务。"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L187** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L188** `<< "[Stop] task104="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L189** `<< (s4 == TTSSubmitStatus::NotRunning`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L190** `? "NotRunning" : "Unexpected")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L191** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L192** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L195** `bool callbacks_received = false;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L198** `std::unique_lock<std::mutex> lock(done_mutex);`：`std::unique_lock<std::mutex>` 是可解锁/重锁的互斥锁拥有者，适配条件变量的等待。

- **L200** `callbacks_received = done_cv.wait_for(`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L201** `lock,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L202** `std::chrono::seconds(120),`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L203** `[&] {`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L204** `return first_done && second_done;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L209** `worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L211** `const bool first_ok =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L212** `first_done && first_result.success;`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L214** `const bool cancelled_ok =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L215** `second_done &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L216** `!second_result.success &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L217** `second_result.error_message.find("cancelled") !=`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L218** `std::string::npos;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L220** `const bool queue_ok =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L221** `s2 == TTSSubmitStatus::Accepted &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L222** `s3 == TTSSubmitStatus::QueueFull &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L223** `s4 == TTSSubmitStatus::NotRunning &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L224** `worker.rejectedCount() == 1;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L226** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L227** `<< std::boolalpha`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L228** `<< "[Result] callbacks=" << callbacks_received`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L229** `<< " first_success=" << first_ok`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L230** `<< " second_cancelled=" << cancelled_ok`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L231** `<< " rejected_count=" << worker.rejectedCount()`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L232** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L234** `if (!callbacks_received ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L235** `!first_ok ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L236** `!cancelled_ok ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L237** `!queue_ok)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L239** `std::cerr << "FAIL\n";`：把失败诊断写stderr，便于区别正常标准日志。

- **L240** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L243** `std::cout << "PASS\n";`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L244** `return 0;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

## 真实源文件：`src/audio/asr_llm_smoke.cpp`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/asr_llm_smoke.cpp`。归档长度 **403 行**，SHA\-256 完整值 `7f1dd9be3dd8814228876681bca7294a0cdfc0f5de0ed76fe35466b1d5247d40`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>
#include <unistd.h>

// Operation 2.9: ALSA -> Silero VAD -> SenseVoice -> LLMWorker -> RKLLM.
// This smoke test intentionally handles only TEXT questions.
int main(int argc, char** argv)
{
    if (argc != 5 && argc != 6)
    {
        std::cerr << "Usage: asr_llm_smoke <ALSA device> <ASR model dir> "
                  << "<VAD model> <RKLLM model> [record seconds: 20]\n";
        return 2;
    }

    const std::string audio_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    std::size_t record_seconds = 20;

    if (argc == 6)
    {
        try
        {
            const std::string value = argv[5];
            std::size_t parsed = 0;
            const unsigned long seconds = std::stoul(value, &parsed);

            if (parsed != value.size() || seconds < 1 || seconds > 120)
                throw std::invalid_argument("out of range");

            record_seconds = static_cast<std::size_t>(seconds);
        }
        catch (const std::exception&)
        {
            std::cerr << "Record seconds must be an integer from 1 to 120\n";
            return 2;
        }
    }

    const std::string asr_model = asr_dir + "/model.int8.onnx";
    const std::string asr_tokens = asr_dir + "/tokens.txt";

    for (const auto& path : {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr << "Cannot read model file: " << path << '\n';
            return 1;
        }
    }

    std::string error;

    LLMEngine llm(std::make_unique<RKLLMBackend>());

    std::cout << "[Init] RKLLM loading...\n" << std::flush;

    if (!llm.initialize(BackendConfig{llm_model, {}}, error))
    {
        std::cerr << "[Init] RKLLM failed: " << error << '\n';
        return 1;
    }

    ASRService asr;

    std::cout << "[Init] SenseVoice loading...\n" << std::flush;

    if (!asr.initialize(asr_model, asr_tokens, error))
    {
        std::cerr << "[Init] ASR failed: " << error << '\n';
        return 1;
    }

    // LLMWorker 内部使用独立线程执行 RKLLM 推理。
    // 队列容量为 2，用于限制等待推理的任务数量。
    LLMWorker llm_worker(llm, 2);

    if (!llm_worker.start(error))
    {
        std::cerr << "[Init] LLMWorker failed: " << error << '\n';
        return 1;
    }

    // 音频队列用于连接 VAD 与 ASRWorker。
    AudioBufferQueue audio_queue(4);

    // 保护多线程终端输出，避免日志严重交错。
    std::mutex print_mutex;

    // 保护 LLM 请求完成情况。
    std::mutex state_mutex;
    std::condition_variable completed_cv;

    IntentRouter router;

    std::uint64_t next_id = 1;

    std::size_t accepted = 0;
    std::size_t completed = 0;
    std::size_t successful = 0;
    std::size_t failed = 0;
    std::size_t rejected = 0;
    std::size_t skipped_vision = 0;

    // ASRWorker 识别出文字后执行此回调。
    // 注意：本回调运行在 ASRWorker 的工作线程中。
    const auto on_text = [&](const std::string& recognized)
    {
        // 先通过 IntentRouter 判断请求类型。
        const RouteDecision route = router.route(recognized);

        // 当前操作 2.9 仅支持 TEXT。
        if (route.type != RequestType::Text)
        {
            ++skipped_vision;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[Route] VISION not supported in operation 2.9: "
                << recognized << '\n';

            return;
        }

        // 为每个请求分配唯一 ID。
        const std::uint64_t id = next_id++;

        // 用于控制流式输出前缀只打印一次。
        auto prefix_printed = std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "\n[ASR->LLM] request #" << id
                << ": " << recognized
                << '\n'
                << std::flush;
        }

        // =====================================================
        // 操作 2.9 优化：构造简短回答 Prompt
        //
        // recognized：SenseVoice 输出的原始识别文字。
        // prompt：提交给 Qwen 的完整问题。
        //
        // 只约束 LLM 回答，不修改 ASR 原始识别内容。
        // =====================================================

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过50个汉字。";

        // =====================================================
        // 非阻塞提交 LLMWorker
        //
        // submit() 仅负责提交任务。
        // 真正耗时的 rkllm_run() 在 Worker 线程执行。
        // =====================================================

        const auto status = llm_worker.submit(
            id,
            prompt,

            // 流式输出回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const std::string& chunk)
            {
                if (chunk.empty())
                    return;

                std::lock_guard<std::mutex> lock(print_mutex);

                if (!*prefix_printed)
                {
                    std::cout
                        << "\n[LLM #" << request_id << "] ";

                    *prefix_printed = true;
                }

                std::cout << chunk << std::flush;
            },

            // LLM 推理完成回调。
            [&, prefix_printed](
                std::uint64_t request_id,
                const InferenceResult& result,
                double wait_ms)
            {
                {
                    std::lock_guard<std::mutex> lock(print_mutex);

                    if (*prefix_printed)
                        std::cout << '\n';

                    std::cout
                        << "[LLM done #" << request_id << "] success="
                        << (result.success ? "true" : "false")
                        << " queue_wait_ms=" << wait_ms
                        << " first_text_ms=" << result.first_text_ms
                        << " request_latency_ms=" << result.latency_ms
                        << '\n';

                    if (!result.success)
                    {
                        std::cout
                            << "[LLM error] "
                            << result.error_message
                            << '\n';
                    }
                }

                {
                    std::lock_guard<std::mutex> lock(state_mutex);

                    ++completed;

                    if (result.success)
                        ++successful;
                    else
                        ++failed;
                }

                // 通知主线程：某个 LLM 请求已完成。
                completed_cv.notify_one();
            }
        );

        // 判断任务是否成功加入队列。
        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex> lock(state_mutex);
            ++accepted;
        }
        else
        {
            ++rejected;

            std::lock_guard<std::mutex> lock(print_mutex);

            std::cout
                << "[LLM rejected #" << id << "] "
                << (status == LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "worker not running")
                << '\n';
        }
    };

    // ASRWorker 从音频队列取出语音片段，执行 SenseVoice。
    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        on_text
    );

    // VadAudioWorker 负责 ALSA 录音和 Silero VAD 分段。
    VadAudioWorker producer(
        audio_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    std::cout
        << "[Listen] "
        << record_seconds
        << " seconds. Speak one short TEXT question, then pause.\n"
        << std::flush;

    try
    {
        // 启动 ASR 消费线程。
        consumer.start();

        // 启动 ALSA + VAD 生产线程。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Thread creation failed: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        return 1;
    }

    // 等待录音/VAD 线程结束。
    producer.join();

    // 等待 ASR 处理完剩余语音片段。
    consumer.join();

    // ASRWorker 退出后，不会再产生新的 LLM 请求。
    // 先等待所有已接受请求完成，再停止 LLMWorker。
    {
        std::unique_lock<std::mutex> lock(state_mutex);

        while (completed < accepted)
        {
            if (!completed_cv.wait_for(
                    lock,
                    std::chrono::seconds(2),
                    [&] { return completed == accepted; }))
            {
                const auto remaining = accepted - completed;

                lock.unlock();

                {
                    std::lock_guard<std::mutex> out(print_mutex);

                    std::cout
                        << "\n[Main] waiting for "
                        << remaining
                        << " LLM request(s)...\n"
                        << std::flush;
                }

                lock.lock();
            }
        }
    }

    // 正确的资源释放顺序：
    // 1. 停止 Worker。
    // 2. 等待 Worker 线程退出。
    // 3. 关闭 RKLLM Runtime。
    llm_worker.requestStop();
    llm_worker.join();
    llm.shutdown();

    // 输出整个语音问答链路的统计信息。
    {
        std::lock_guard<std::mutex> out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM summary ===\n"
            << "VAD segments: " << producer.producedCount() << '\n'
            << "ASR recognized: " << consumer.processedCount() << '\n'
            << "Audio queue dropped: " << audio_queue.droppedCount() << '\n'
            << "LLM accepted: " << accepted << '\n'
            << "LLM completed: " << completed << '\n'
            << "LLM successful: " << successful << '\n'
            << "LLM failed: " << failed << '\n'
            << "LLM rejected: " << rejected << '\n'
            << "Skipped VISION: " << skipped_vision << '\n';

        if (!producer.ok())
            std::cerr << "[VAD] " << producer.error() << '\n';

        if (!consumer.ok())
            std::cerr << "[ASR] " << consumer.error() << '\n';
    }

    // 最终验收条件。
    const bool passed =
        producer.ok() &&
        consumer.ok() &&
        accepted > 0 &&
        accepted == completed &&
        successful > 0 &&
        failed == 0 &&
        rejected == 0 &&
        audio_queue.droppedCount() == 0;

    std::cout << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
```

## 真实源文件：`src/audio/asr_llm_tts_smoke.cpp`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/audio/asr_llm_tts_smoke.cpp`。归档长度 **1077 行**，SHA\-256 完整值 `63d4ffc5fbd52aa029c75afd7cf094423fbe0e7109a06a9baa8fbd29e1a18ee8`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "audio/asr_pipeline.h"
#include "audio/asr_service.h"
#include "audio/vad_audio_worker.h"
#include "audio/tts_service.h"
#include "audio/alsa_playback_service.h"
#include "audio/tts_worker.h"

#include "ai/llm_worker.h"
#include "ai/rk_backends.h"
#include "router/intent_router.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <exception>
#include <iostream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <utility>

#include <unistd.h>

// ==========================================================
// Stage 3.5
//
// ALSA Capture
//     ↓
// Silero VAD
//     ↓
// SenseVoice ASR
//     ↓
// IntentRouter
//     ↓
// LLMWorker -> RKLLM / Qwen2.5
//     ↓
// TTSWorker -> Kokoro
//     ↓
// AlsaPlaybackService
//     ↓
// USB Headset
//
// 当前只处理 TEXT 类型的问题。
// ==========================================================

int main(int argc, char** argv)
{
    // ------------------------------------------------------
    // 1. 命令行参数检查
    // ------------------------------------------------------

    if (argc < 7 || argc > 10)
    {
        std::cerr
            << "Usage: asr_llm_tts_smoke "
            << "<capture_device> "
            << "<asr_model_dir> "
            << "<vad_model> "
            << "<rkllm_model> "
            << "<kokoro_dir> "
            << "<playback_device> "
            << "[record_seconds=12] "
            << "[tts_threads=2] "
            << "[sid=17]\n";

        return 2;
    }

    const std::string capture_device = argv[1];
    const std::string asr_dir = argv[2];
    const std::string vad_model = argv[3];
    const std::string llm_model = argv[4];
    const std::string kokoro_dir = argv[5];
    const std::string playback_device = argv[6];

    unsigned int record_seconds = 12;

    int tts_threads = 2;
    int sid = 17;

    // ------------------------------------------------------
    // 2. 解析可选参数
    // ------------------------------------------------------

    try
    {
        const auto parse = [](
            const char* arg,
            int lo,
            int hi
        ) -> int
        {
            const std::string value(arg);

            std::size_t used = 0;

            const int result =
                std::stoi(value, &used);

            if (used != value.size() ||
                result < lo ||
                result > hi)
            {
                throw std::invalid_argument(
                    "out of range"
                );
            }

            return result;
        };

        if (argc >= 8)
        {
            record_seconds =
                static_cast<unsigned int>(
                    parse(argv[7], 1, 120)
                );
        }

        if (argc >= 9)
        {
            tts_threads =
                parse(argv[8], 1, 8);
        }

        if (argc >= 10)
        {
            sid =
                parse(argv[9], 0, 10000);
        }
    }
    catch (const std::exception&)
    {
        std::cerr
            << "[Args] Invalid record_seconds / "
            << "threads / sid\n";

        return 2;
    }

    // ------------------------------------------------------
    // 3. 检查 ASR / VAD / LLM 模型文件
    // ------------------------------------------------------

    const std::string asr_model =
        asr_dir + "/model.int8.onnx";

    const std::string asr_tokens =
        asr_dir + "/tokens.txt";

    for (const auto& path :
         {asr_model, asr_tokens, vad_model, llm_model})
    {
        if (::access(path.c_str(), R_OK) != 0)
        {
            std::cerr
                << "[Init] Cannot read model file: "
                << path
                << '\n';

            return 1;
        }
    }

    std::string error;

    // ------------------------------------------------------
    // 4. 初始化 RKLLM
    // ------------------------------------------------------

    LLMEngine llm(
        std::make_unique<RKLLMBackend>()
    );

    std::cout
        << "[Init] Loading RKLLM...\n"
        << std::flush;

    if (!llm.initialize(
            BackendConfig{llm_model, {}},
            error))
    {
        std::cerr
            << "[Init] RKLLM failed: "
            << error
            << '\n';

        return 1;
    }

    // ------------------------------------------------------
    // 5. 初始化 SenseVoice
    // ------------------------------------------------------

    ASRService asr;

    std::cout
        << "[Init] Loading SenseVoice...\n"
        << std::flush;

    if (!asr.initialize(
            asr_model,
            asr_tokens,
            error))
    {
        std::cerr
            << "[Init] ASR failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 6. 初始化 Kokoro TTS
    // ------------------------------------------------------

    TTSService tts;

    std::cout
        << "[Init] Loading Kokoro...\n"
        << std::flush;

    if (!tts.initialize(
            kokoro_dir,
            error,
            tts_threads,
            sid))
    {
        std::cerr
            << "[Init] Kokoro failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 7. 初始化 ALSA Playback
    // ------------------------------------------------------

    AlsaPlaybackService playback;

    if (!playback.open(
            playback_device,
            tts.sampleRate(),
            error))
    {
        std::cerr
            << "[Init] ALSA playback failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 8. 创建并启动 TTSWorker
    // ------------------------------------------------------
    //
    // TTSWorker 不拥有 TTSService 和 PlaybackService。
    // 两个 Service 必须比 Worker 活得更久。
    //
    // capacity=2 表示最多允许两个等待任务。
    // ------------------------------------------------------

    TTSWorker tts_worker(
        tts,
        playback,
        2
    );

    if (!tts_worker.start(error))
    {
        std::cerr
            << "[Init] TTSWorker failed: "
            << error
            << '\n';

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 9. 创建并启动 LLMWorker
    // ------------------------------------------------------

    LLMWorker llm_worker(
        llm,
        2
    );

    if (!llm_worker.start(error))
    {
        std::cerr
            << "[Init] LLMWorker failed: "
            << error
            << '\n';

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 10. 创建 ASR 音频队列和线程同步对象
    // ------------------------------------------------------

    AudioBufferQueue audio_queue(4);

    // 保护不同线程的日志输出。
    std::mutex print_mutex;

    // 保护 LLM/TTS 任务完成计数。
    std::mutex state_mutex;

    // 通知主线程有任务完成。
    std::condition_variable completed_cv;

    IntentRouter router;

    // 由单个 ASRWorker 回调生成请求 ID。
    std::uint64_t next_id = 1;

    // ------------------------------------------------------
    // 11. LLM 和 TTS 统计
    // ------------------------------------------------------

    std::size_t llm_accepted = 0;
    std::size_t llm_completed = 0;
    std::size_t llm_successful = 0;
    std::size_t llm_failed = 0;
    std::size_t llm_rejected = 0;

    std::size_t skipped_vision = 0;

    std::size_t tts_accepted = 0;
    std::size_t tts_completed = 0;
    std::size_t tts_successful = 0;
    std::size_t tts_failed = 0;
    std::size_t tts_rejected = 0;
    std::size_t tts_empty = 0;

    // ------------------------------------------------------
    // 12. ASR 识别完成回调
    // ------------------------------------------------------
    //
    // 此回调在 ASRWorker 线程执行。
    //
    // recognized 是 SenseVoice 的识别结果。
    // ------------------------------------------------------

    const auto on_text =
        [&](const std::string& recognized)
    {
        // --------------------------------------------------
        // 12.1 意图判断
        // --------------------------------------------------

        const RouteDecision route =
            router.route(recognized);

        if (route.type != RequestType::Text)
        {
            ++skipped_vision;

            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "\n[Route] Skipped non-TEXT request: "
                << recognized
                << '\n';

            return;
        }

        // --------------------------------------------------
        // 12.2 分配请求 ID
        // --------------------------------------------------

        const std::uint64_t id =
            next_id++;

        // 记录 ASR 输出文本的时刻。
        const auto question_at =
            std::chrono::steady_clock::now();

        // 记录 LLM 是否已经输出前缀。
        auto prefix_printed =
            std::make_shared<bool>(false);

        {
            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "\n[ASR->LLM #" << id << "] "
                << recognized
                << '\n';
        }

        // --------------------------------------------------
        // 12.3 构造 LLM Prompt
        // --------------------------------------------------
        //
        // 限制回答长度，降低当前 Kokoro 的合成等待。
        // 不改变 ASR 原始文本。
        // --------------------------------------------------

        const std::string prompt =
            recognized +
            "\n请直接用一句话回答，不超过25个汉字。";

        // --------------------------------------------------
        // 12.4 非阻塞提交 LLMWorker
        // --------------------------------------------------

        const auto status =
            llm_worker.submit(
                id,
                prompt,

                // ------------------------------------------
                // LLM 流式文本回调
                // ------------------------------------------

                [&, prefix_printed](
                    std::uint64_t request_id,
                    const std::string& chunk)
                {
                    if (chunk.empty())
                    {
                        return;
                    }

                    std::lock_guard<std::mutex>
                        out(print_mutex);

                    if (!*prefix_printed)
                    {
                        std::cout
                            << "\n[LLM #"
                            << request_id
                            << "] ";

                        *prefix_printed = true;
                    }

                    std::cout
                        << chunk
                        << std::flush;
                },

                // ------------------------------------------
                // LLM 推理完成回调
                // ------------------------------------------
                //
                // 关键：这里把 LLM 答案交给 TTSWorker。
                // ------------------------------------------

                [&, prefix_printed, question_at](
                    std::uint64_t request_id,
                    const InferenceResult& result,
                    double llm_queue_ms)
                {
                    {
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        if (*prefix_printed)
                        {
                            std::cout << '\n';
                        }

                        std::cout
                            << "[LLM done #"
                            << request_id
                            << "] success="
                            << (result.success
                                ? "true"
                                : "false")
                            << " queue_ms="
                            << llm_queue_ms
                            << " first_text_ms="
                            << result.first_text_ms
                            << " latency_ms="
                            << result.latency_ms
                            << '\n';

                        if (!result.success)
                        {
                            std::cout
                                << "[LLM error] "
                                << result.error_message
                                << '\n';
                        }
                    }

                    // --------------------------------------
                    // 12.5 判断 LLM 是否产生有效文本
                    // --------------------------------------

                    TTSSubmitStatus tts_status =
                        TTSSubmitStatus::NotRunning;

                    std::string tts_submit_error;

                    const bool has_answer =
                        result.success &&
                        !result.text.empty();

                    if (has_answer)
                    {
                        try
                        {
                            // ------------------------------
                            // 12.6 向 TTSWorker 提交答案
                            // ------------------------------

                            tts_status =
                                tts_worker.submit(
                                    request_id,
                                    result.text,

                                    // ----------------------
                                    // TTS 完成回调
                                    // ----------------------

                                    [&, question_at](
                                        std::uint64_t tts_id,
                                        const TTSWorkerResult& tts_result,
                                        double tts_queue_ms)
                                    {
                                        // 从 ASR 输出文本到
                                        // 播放任务结束的耗时。
                                        const double e2e_ms =
                                            std::chrono::duration<
                                                double,
                                                std::milli
                                            >(
                                                std::chrono::
                                                    steady_clock::now()
                                                - question_at
                                            ).count();

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > out(print_mutex);

                                            std::cout
                                                << "[TTS done #"
                                                << tts_id
                                                << "] success="
                                                << (tts_result.success
                                                    ? "true"
                                                    : "false")
                                                << " queue_ms="
                                                << tts_queue_ms
                                                << " synth_ms="
                                                << tts_result.synthesis_ms
                                                << " audio_sec="
                                                << tts_result.audio_seconds
                                                << " playback_ms="
                                                << tts_result.playback_ms
                                                << " xruns="
                                                << tts_result.xrun_count
                                                << " asr_text_to_end_ms="
                                                << e2e_ms
                                                << '\n';

                                            if (!tts_result.success)
                                            {
                                                std::cout
                                                    << "[TTS error] "
                                                    << tts_result.error_message
                                                    << '\n';
                                            }
                                        }

                                        // ------------------
                                        // 更新 TTS 任务统计
                                        // ------------------

                                        {
                                            std::lock_guard<
                                                std::mutex
                                            > lock(state_mutex);

                                            ++tts_completed;

                                            if (tts_result.success)
                                            {
                                                ++tts_successful;
                                            }
                                            else
                                            {
                                                ++tts_failed;
                                            }
                                        }

                                        // 唤醒等待中的主线程。
                                        completed_cv.notify_all();
                                    }
                                );
                        }
                        catch (const std::exception& e)
                        {
                            tts_submit_error = e.what();
                        }
                        catch (...)
                        {
                            tts_submit_error =
                                "unknown exception";
                        }

                        // ----------------------------------
                        // 12.7 处理 TTS 提交失败
                        // ----------------------------------

                        if (tts_status !=
                            TTSSubmitStatus::Accepted)
                        {
                            std::lock_guard<std::mutex>
                                out(print_mutex);

                            std::cout
                                << "[TTS rejected #"
                                << request_id
                                << "] ";

                            if (!tts_submit_error.empty())
                            {
                                std::cout
                                    << tts_submit_error;
                            }
                            else if (
                                tts_status ==
                                TTSSubmitStatus::QueueFull)
                            {
                                std::cout
                                    << "queue full";
                            }
                            else
                            {
                                std::cout
                                    << "not running";
                            }

                            std::cout << '\n';
                        }
                    }
                    else if (result.success)
                    {
                        // LLM 成功但回答为空，
                        // 不能向 TTS 提交空文本。
                        std::lock_guard<std::mutex>
                            out(print_mutex);

                        std::cout
                            << "[TTS skipped #"
                            << request_id
                            << "] LLM returned empty answer\n";
                    }

                    // --------------------------------------
                    // 12.8 更新任务计数
                    // --------------------------------------
                    //
                    // 重要：
                    // 先提交 TTS，再标记 LLM completed。
                    //
                    // 这样主线程等完所有 LLM 后，
                    // 就能确认不再产生新的 TTS 请求。
                    // --------------------------------------

                    {
                        std::lock_guard<std::mutex>
                            lock(state_mutex);

                        ++llm_completed;

                        if (result.success)
                        {
                            ++llm_successful;
                        }
                        else
                        {
                            ++llm_failed;
                        }

                        if (result.success &&
                            result.text.empty())
                        {
                            ++tts_empty;
                        }

                        if (has_answer)
                        {
                            if (tts_status ==
                                TTSSubmitStatus::Accepted)
                            {
                                ++tts_accepted;
                            }
                            else
                            {
                                ++tts_rejected;
                            }
                        }
                    }

                    completed_cv.notify_all();
                }
            );

        // --------------------------------------------------
        // 12.9 处理 LLM 任务提交结果
        // --------------------------------------------------

        if (status == LLMSubmitStatus::Accepted)
        {
            std::lock_guard<std::mutex>
                lock(state_mutex);

            ++llm_accepted;
        }
        else
        {
            // 只有 ASRWorker 修改该计数。
            ++llm_rejected;

            std::lock_guard<std::mutex>
                out(print_mutex);

            std::cout
                << "[LLM rejected #"
                << id
                << "] "
                << (status ==
                    LLMSubmitStatus::QueueFull
                    ? "queue full"
                    : "not running")
                << '\n';
        }
    };

    // ------------------------------------------------------
    // 13. 创建 ASRWorker 和 VadAudioWorker
    // ------------------------------------------------------

    ASRWorker consumer(
        audio_queue,
        asr,
        print_mutex,
        on_text
    );

    VadAudioWorker producer(
        capture_device,
        vad_model,
        audio_queue,
        print_mutex,
        record_seconds
    );

    std::cout
        << "[Listen] "
        << record_seconds
        << " seconds. "
        << "Ask ONE short text question and pause.\n"
        << std::flush;

    // ------------------------------------------------------
    // 14. 启动录音/VAD 和 ASR 工作线程
    // ------------------------------------------------------

    try
    {
        // ASR 消费者先启动。
        consumer.start();

        // VAD 录音生产者后启动。
        producer.start();
    }
    catch (const std::exception& e)
    {
        std::cerr
            << "[Start] Cannot start capture/ASR thread: "
            << e.what()
            << '\n';

        producer.requestStop();
        audio_queue.close();

        producer.join();
        consumer.join();

        llm_worker.requestStop();
        llm_worker.join();

        tts_worker.requestStop();
        tts_worker.join();

        llm.shutdown();

        return 1;
    }

    // ------------------------------------------------------
    // 15. 等待录音/VAD 和 ASR 完成
    // ------------------------------------------------------

    producer.join();

    consumer.join();

    // 此时 ASRWorker 已经退出，
    // 不会继续向 LLMWorker 提交新请求。

    // ------------------------------------------------------
    // 16. 通用 Worker 完成等待函数
    // ------------------------------------------------------
    //
    // 在等待期间，主线程每 2 秒输出一次进度。
    //
    // accepted / completed 都必须由 state_mutex 保护。
    // ------------------------------------------------------

    const auto wait_for_jobs =
        [&](const char* stage,
            const std::size_t& accepted,
            const std::size_t& completed,
            int deadline_seconds) -> bool
    {
        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::seconds(deadline_seconds);

        std::unique_lock<std::mutex>
            lock(state_mutex);

        while (completed < accepted)
        {
            const bool all_done =
                completed_cv.wait_for(
                    lock,
                    std::chrono::seconds(2),
                    [&]()
                    {
                        return completed >= accepted;
                    }
                );

            if (all_done)
            {
                break;
            }

            const std::size_t remaining =
                accepted - completed;

            // 输出日志前释放状态锁。
            lock.unlock();

            {
                std::lock_guard<std::mutex>
                    out(print_mutex);

                std::cout
                    << "[Main] waiting for "
                    << remaining
                    << " "
                    << stage
                    << " task(s)...\n"
                    << std::flush;
            }

            lock.lock();

            if (std::chrono::steady_clock::now() >=
                deadline)
            {
                return false;
            }
        }

        return true;
    };

    // ------------------------------------------------------
    // 17. 等待全部 LLM 任务完成
    // ------------------------------------------------------

    const bool llm_drained =
        wait_for_jobs(
            "LLM",
            llm_accepted,
            llm_completed,
            180
        );

    if (!llm_drained)
    {
        std::cerr
            << "[Timeout] LLM tasks "
            << "did not finish in 180s\n";
    }

    // ------------------------------------------------------
    // 18. 停止 LLMWorker
    // ------------------------------------------------------
    //
    // 必须等 LLMWorker 完全停止，
    // 才能确认不会再向 TTSWorker 提交任务。
    // ------------------------------------------------------

    llm_worker.requestStop();
    llm_worker.join();

    // LLM 不再被工作线程访问后，
    // 才允许释放 RKLLM Runtime。
    llm.shutdown();

    // ------------------------------------------------------
    // 19. 等待全部 TTS 任务完成
    // ------------------------------------------------------
    //
    // 必须先等待 accepted == completed，
    // 然后再 requestStop。
    //
    // 否则会把队列中等待的 TTS 任务取消。
    // ------------------------------------------------------

    const bool tts_drained =
        wait_for_jobs(
            "TTS",
            tts_accepted,
            tts_completed,
            600
        );

    if (!tts_drained)
    {
        std::cerr
            << "[Timeout] TTS tasks "
            << "did not finish in 600s\n";
    }

    // ------------------------------------------------------
    // 20. 停止 TTSWorker
    // ------------------------------------------------------

    tts_worker.requestStop();
    tts_worker.join();

    // 只有 Worker 退出以后，
    // 才能安全关闭 ALSA 和 TTSService。
    playback.close();
    tts.shutdown();

    // ------------------------------------------------------
    // 21. 输出整个语音交互链路的统计
    // ------------------------------------------------------

    {
        std::lock_guard<std::mutex>
            out(print_mutex);

        std::cout
            << "\n=== ASR -> LLM -> TTS summary ===\n"

            << "VAD segments: "
            << producer.producedCount()
            << '\n'

            << "ASR recognized: "
            << consumer.processedCount()
            << '\n'

            << "Audio queue dropped: "
            << audio_queue.droppedCount()
            << '\n'

            << "LLM accepted/completed/"
            << "success/failed/rejected: "
            << llm_accepted
            << '/'
            << llm_completed
            << '/'
            << llm_successful
            << '/'
            << llm_failed
            << '/'
            << llm_rejected
            << '\n'

            << "TTS accepted/completed/"
            << "success/failed/rejected/empty: "
            << tts_accepted
            << '/'
            << tts_completed
            << '/'
            << tts_successful
            << '/'
            << tts_failed
            << '/'
            << tts_rejected
            << '/'
            << tts_empty
            << '\n'

            << "Skipped VISION: "
            << skipped_vision
            << '\n';

        if (!producer.ok())
        {
            std::cerr
                << "[VAD] "
                << producer.error()
                << '\n';
        }

        if (!consumer.ok())
        {
            std::cerr
                << "[ASR] "
                << consumer.error()
                << '\n';
        }
    }

    // ------------------------------------------------------
    // 22. 最终验收条件
    // ------------------------------------------------------

    const bool passed =
        producer.ok() &&
        consumer.ok() &&

        audio_queue.droppedCount() == 0 &&

        llm_drained &&
        tts_drained &&

        llm_accepted > 0 &&
        llm_accepted == llm_completed &&
        llm_successful == llm_accepted &&
        llm_failed == 0 &&
        llm_rejected == 0 &&

        tts_accepted == llm_successful &&
        tts_completed == tts_accepted &&
        tts_successful == tts_accepted &&
        tts_failed == 0 &&
        tts_rejected == 0 &&
        tts_empty == 0;

    std::cout
        << (passed ? "PASS\n" : "FAIL\n");

    return passed ? 0 : 1;
}
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

### 逐句定位：源文件物理行号与执行意义

**阅读规则**：以源码的实际物理行号定位。空行仅分隔逻辑；注释不产生运行时指令；孤立 `{ }` 只界定作用域并决定 RAII 对象析构时间。对于拆成多行的一个函数调用，形参、实参、闭括号应结合相邻行理解。

- **L2** `#include "audio/asr_pipeline.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L3** `#include "audio/asr_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L4** `#include "audio/vad_audio_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L5** `#include "audio/tts_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L6** `#include "audio/alsa_playback_service.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L7** `#include "audio/tts_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L9** `#include "ai/llm_worker.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L10** `#include "ai/rk_backends.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L11** `#include "router/intent_router.h"`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L13** `#include <chrono>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L14** `#include <condition_variable>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L15** `#include <cstddef>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L16** `#include <cstdint>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L17** `#include <exception>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L18** `#include <iostream>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L19** `#include <memory>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L20** `#include <mutex>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L21** `#include <stdexcept>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L22** `#include <string>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L23** `#include <utility>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L25** `#include <unistd.h>`：预处理包含头文件声明；引号引用项目头，尖括号引用SDK/标准库头；不产生运行时函数调用。

- **L49** `int main(int argc, char** argv)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L55** `if (argc < 7 || argc > 10)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L57** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L58** `<< "Usage: asr_llm_tts_smoke "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L59** `<< "<capture_device> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L60** `<< "<asr_model_dir> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L61** `<< "<vad_model> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L62** `<< "<rkllm_model> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L63** `<< "<kokoro_dir> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L64** `<< "<playback_device> "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L65** `<< "[record_seconds=12] "`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L66** `<< "[tts_threads=2] "`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L67** `<< "[sid=17]\n";`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L69** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L72** `const std::string capture_device = argv[1];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L73** `const std::string asr_dir = argv[2];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L74** `const std::string vad_model = argv[3];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L75** `const std::string llm_model = argv[4];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L76** `const std::string kokoro_dir = argv[5];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L77** `const std::string playback_device = argv[6];`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L79** `unsigned int record_seconds = 12;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L81** `int tts_threads = 2;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L82** `int sid = 17;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L88** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L90** `const auto parse = [](`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L91** `const char* arg,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L92** `int lo,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L93** `int hi`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L94** `) -> int`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L96** `const std::string value(arg);`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L98** `std::size_t used = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L100** `const int result =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L101** `std::stoi(value, &used);`：解析命令行数字，配合长度/上下限验证，防止非法参数进入SDK。

- **L103** `if (used != value.size() ||`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L104** `result < lo ||`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L105** `result > hi)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L107** `throw std::invalid_argument(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L108** `"out of range"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L112** `return result;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L115** `if (argc >= 8)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L117** `record_seconds =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L118** `static_cast<unsigned int>(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L119** `parse(argv[7], 1, 120)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L123** `if (argc >= 9)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L125** `tts_threads =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L126** `parse(argv[8], 1, 8);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L129** `if (argc >= 10)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L131** `sid =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L132** `parse(argv[9], 0, 10000);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L135** `catch (const std::exception&)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L137** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L138** `<< "[Args] Invalid record_seconds / "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L139** `<< "threads / sid\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L141** `return 2;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L148** `const std::string asr_model =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L149** `asr_dir + "/model.int8.onnx";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L151** `const std::string asr_tokens =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L152** `asr_dir + "/tokens.txt";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L154** `for (const auto& path :`：循环控制语句，注意终止条件和迭代后状态更新。

- **L155** `{asr_model, asr_tokens, vad_model, llm_model})`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L157** `if (::access(path.c_str(), R_OK) != 0)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L159** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L160** `<< "[Init] Cannot read model file: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L161** `<< path`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L162** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L164** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L168** `std::string error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L174** `LLMEngine llm(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L175** `std::make_unique<RKLLMBackend>()`：在堆上构造独占backend，通过多态接口注入LLMEngine。

- **L178** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L179** `<< "[Init] Loading RKLLM...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L180** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L182** `if (!llm.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L183** `BackendConfig{llm_model, {}},`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L184** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L186** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L187** `<< "[Init] RKLLM failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L188** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L189** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L191** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L198** `ASRService asr;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L200** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L201** `<< "[Init] Loading SenseVoice...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L202** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L204** `if (!asr.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L205** `asr_model,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L206** `asr_tokens,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L207** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L209** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L210** `<< "[Init] ASR failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L211** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L212** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L214** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L216** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L223** `TTSService tts;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L225** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L226** `<< "[Init] Loading Kokoro...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L227** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L229** `if (!tts.initialize(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L230** `kokoro_dir,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L231** `error,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L232** `tts_threads,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L233** `sid))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L235** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L236** `<< "[Init] Kokoro failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L237** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L238** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L240** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L242** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L249** `AlsaPlaybackService playback;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L251** `if (!playback.open(`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L252** `playback_device,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L253** `tts.sampleRate(),`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L254** `error))`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L256** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L257** `<< "[Init] ALSA playback failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L258** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L259** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L261** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L263** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L276** `TTSWorker tts_worker(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L277** `tts,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L278** `playback,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L279** `2`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L282** `if (!tts_worker.start(error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L284** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L285** `<< "[Init] TTSWorker failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L286** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L287** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L289** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L291** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L298** `LLMWorker llm_worker(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L299** `llm,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L300** `2`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L303** `if (!llm_worker.start(error))`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L305** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L306** `<< "[Init] LLMWorker failed: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L307** `<< error`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L308** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L310** `tts_worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L311** `tts_worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L313** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L315** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L322** `AudioBufferQueue audio_queue(4);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L325** `std::mutex print_mutex;`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L328** `std::mutex state_mutex;`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L331** `std::condition_variable completed_cv;`：多线程事件通知机制；实际条件由mutex保护的共享计数或队列状态决定。

- **L333** `IntentRouter router;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L336** `std::uint64_t next_id = 1;`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L342** `std::size_t llm_accepted = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L343** `std::size_t llm_completed = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L344** `std::size_t llm_successful = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L345** `std::size_t llm_failed = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L346** `std::size_t llm_rejected = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L348** `std::size_t skipped_vision = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L350** `std::size_t tts_accepted = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L351** `std::size_t tts_completed = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L352** `std::size_t tts_successful = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L353** `std::size_t tts_failed = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L354** `std::size_t tts_rejected = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L355** `std::size_t tts_empty = 0;`：与容器大小/样本数量相配套的无符号整数类型。

- **L366** `const auto on_text =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L367** `[&](const std::string& recognized)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L373** `const RouteDecision route =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L374** `router.route(recognized);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L376** `if (route.type != RequestType::Text)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L378** `++skipped_vision;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L380** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L381** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L383** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L384** `<< "\n[Route] Skipped non-TEXT request: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L385** `<< recognized`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L386** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L388** `return;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L395** `const std::uint64_t id =`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L396** `next_id++;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L399** `const auto question_at =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L400** `std::chrono::steady_clock::now();`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L403** `auto prefix_printed =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L404** `std::make_shared<bool>(false);`：在堆创建共享所有权对象，使异步Lambda捕获对象保持存活。

- **L407** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L408** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L410** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L411** `<< "\n[ASR->LLM #" << id << "] "`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L412** `<< recognized`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L413** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L424** `const std::string prompt =`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L425** `recognized +`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L426** `"\n请直接用一句话回答，不超过25个汉字。";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L432** `const auto status =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L433** `llm_worker.submit(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L434** `id,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L435** `prompt,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L441** `[&, prefix_printed](`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L442** `std::uint64_t request_id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L443** `const std::string& chunk)`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L445** `if (chunk.empty())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L447** `return;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L450** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L451** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L453** `if (!*prefix_printed)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L455** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L456** `<< "\n[LLM #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L457** `<< request_id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L458** `<< "] ";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L460** `*prefix_printed = true;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L463** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L464** `<< chunk`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L465** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L475** `[&, prefix_printed, question_at](`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L476** `std::uint64_t request_id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L477** `const InferenceResult& result,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L478** `double llm_queue_ms)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L481** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L482** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L484** `if (*prefix_printed)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L486** `std::cout << '\n';`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L489** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L490** `<< "[LLM done #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L491** `<< request_id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L492** `<< "] success="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L493** `<< (result.success`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L494** `? "true"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L495** `: "false")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L496** `<< " queue_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L497** `<< llm_queue_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L498** `<< " first_text_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L499** `<< result.first_text_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L500** `<< " latency_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L501** `<< result.latency_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L502** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L504** `if (!result.success)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L506** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L507** `<< "[LLM error] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L508** `<< result.error_message`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L509** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L517** `TTSSubmitStatus tts_status =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L518** `TTSSubmitStatus::NotRunning;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L520** `std::string tts_submit_error;`：拥有UTF\-8字节字符串；传给C API需要c\_str且应关注字符串生命周期。

- **L522** `const bool has_answer =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L523** `result.success &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L524** `!result.text.empty();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L526** `if (has_answer)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L528** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L534** `tts_status =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L535** `tts_worker.submit(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L536** `request_id,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L537** `result.text,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L543** `[&, question_at](`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L544** `std::uint64_t tts_id,`：64位无符号请求ID/计数，跨线程读写仍须同步。

- **L545** `const TTSWorkerResult& tts_result,`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L546** `double tts_queue_ms)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L550** `const double e2e_ms =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L551** `std::chrono::duration<`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L552** `double,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L553** `std::milli`：标准库类型/成员/函数参与线程管理、容器或数据处理；`::`用于命名空间/类作用域限定。

- **L554** `>(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L555** `std::chrono::`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L556** `steady_clock::now()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L557** `- question_at`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L558** `).count();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L561** `std::lock_guard<`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L562** `std::mutex`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L563** `> out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L565** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L566** `<< "[TTS done #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L567** `<< tts_id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L568** `<< "] success="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L569** `<< (tts_result.success`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L570** `? "true"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L571** `: "false")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L572** `<< " queue_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L573** `<< tts_queue_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L574** `<< " synth_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L575** `<< tts_result.synthesis_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L576** `<< " audio_sec="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L577** `<< tts_result.audio_seconds`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L578** `<< " playback_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L579** `<< tts_result.playback_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L580** `<< " xruns="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L581** `<< tts_result.xrun_count`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L582** `<< " asr_text_to_end_ms="`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L583** `<< e2e_ms`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L584** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L586** `if (!tts_result.success)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L588** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L589** `<< "[TTS error] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L590** `<< tts_result.error_message`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L591** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L600** `std::lock_guard<`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L601** `std::mutex`：互斥锁成员，保护FIFO/打印/统计的共享访问。

- **L602** `> lock(state_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L604** `++tts_completed;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L606** `if (tts_result.success)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L608** `++tts_successful;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L610** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L612** `++tts_failed;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L617** `completed_cv.notify_all();`：通知所有等待线程重新检查条件，并不代表任务必然成功。

- **L621** `catch (const std::exception& e)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L623** `tts_submit_error = e.what();`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L625** `catch (...)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L627** `tts_submit_error =`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L628** `"unknown exception";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L635** `if (tts_status !=`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L636** `TTSSubmitStatus::Accepted)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L638** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L639** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L641** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L642** `<< "[TTS rejected #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L643** `<< request_id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L644** `<< "] ";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L646** `if (!tts_submit_error.empty())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L648** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L649** `<< tts_submit_error;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L651** `else if (`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L652** `tts_status ==`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L653** `TTSSubmitStatus::QueueFull)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L655** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L656** `<< "queue full";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L658** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L660** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L661** `<< "not running";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L664** `std::cout << '\n';`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L667** `else if (result.success)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L671** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L672** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L674** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L675** `<< "[TTS skipped #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L676** `<< request_id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L677** `<< "] LLM returned empty answer\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L692** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L693** `lock(state_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L695** `++llm_completed;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L697** `if (result.success)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L699** `++llm_successful;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L701** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L703** `++llm_failed;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L706** `if (result.success &&`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L707** `result.text.empty())`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L709** `++tts_empty;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L712** `if (has_answer)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L714** `if (tts_status ==`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L715** `TTSSubmitStatus::Accepted)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L717** `++tts_accepted;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L719** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L721** `++tts_rejected;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L726** `completed_cv.notify_all();`：通知所有等待线程重新检查条件，并不代表任务必然成功。

- **L734** `if (status == LLMSubmitStatus::Accepted)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L736** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L737** `lock(state_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L739** `++llm_accepted;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L741** `else`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L744** `++llm_rejected;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L746** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L747** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L749** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L750** `<< "[LLM rejected #"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L751** `<< id`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L752** `<< "] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L753** `<< (status ==`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L754** `LLMSubmitStatus::QueueFull`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L755** `? "queue full"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L756** `: "not running")`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L757** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L765** `ASRWorker consumer(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L766** `audio_queue,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L767** `asr,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L768** `print_mutex,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L769** `on_text`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L772** `VadAudioWorker producer(`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L773** `capture_device,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L774** `vad_model,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L775** `audio_queue,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L776** `print_mutex,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L777** `record_seconds`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L780** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L781** `<< "[Listen] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L782** `<< record_seconds`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L783** `<< " seconds. "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L784** `<< "Ask ONE short text question and pause.\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L785** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L791** `try`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L794** `consumer.start();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L797** `producer.start();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L799** `catch (const std::exception& e)`：异常保护边界：把潜在SDK/分配异常转换成错误结果，避免逃逸线程入口。

- **L801** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L802** `<< "[Start] Cannot start capture/ASR thread: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L803** `<< e.what()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L804** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L806** `producer.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L807** `audio_queue.close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L809** `producer.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L810** `consumer.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L812** `llm_worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L813** `llm_worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L815** `tts_worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L816** `tts_worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L818** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L820** `return 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L827** `producer.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L829** `consumer.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L843** `const auto wait_for_jobs =`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L844** `[&](const char* stage,`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L845** `const std::size_t& accepted,`：与容器大小/样本数量相配套的无符号整数类型。

- **L846** `const std::size_t& completed,`：与容器大小/样本数量相配套的无符号整数类型。

- **L847** `int deadline_seconds) -> bool`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L849** `const auto deadline =`：`auto`从初始化表达式推导编译期类型；需要通过右侧和调用者上下文理解实际值。

- **L850** `std::chrono::steady_clock::now() +`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L851** `std::chrono::seconds(deadline_seconds);`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L853** `std::unique_lock<std::mutex>`：`std::unique_lock<std::mutex>` 是可解锁/重锁的互斥锁拥有者，适配条件变量的等待。

- **L854** `lock(state_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L856** `while (completed < accepted)`：循环控制语句，注意终止条件和迭代后状态更新。

- **L858** `const bool all_done =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L859** `completed_cv.wait_for(`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L860** `lock,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L861** `std::chrono::seconds(2),`：使用单调时钟和duration，测量queue/synth/playback延迟。

- **L862** `[&]()`：Lambda表达式：`&`捕获引用，必须保证引用对象晚于异步回调销毁；值捕获保存副本。

- **L864** `return completed >= accepted;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L868** `if (all_done)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L870** `break;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L873** `const std::size_t remaining =`：与容器大小/样本数量相配套的无符号整数类型。

- **L874** `accepted - completed;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L877** `lock.unlock();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L880** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L881** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L883** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L884** `<< "[Main] waiting for "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L885** `<< remaining`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L886** `<< " "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L887** `<< stage`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L888** `<< " task(s)...\n"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L889** `<< std::flush;`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L892** `lock.lock();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L894** `if (std::chrono::steady_clock::now() >=`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L895** `deadline)`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L897** `return false;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L901** `return true;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

- **L908** `const bool llm_drained =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L909** `wait_for_jobs(`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L910** `"LLM",`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L911** `llm_accepted,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L912** `llm_completed,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L913** `180`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L916** `if (!llm_drained)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L918** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L919** `<< "[Timeout] LLM tasks "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L920** `<< "did not finish in 180s\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L931** `llm_worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L932** `llm_worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L936** `llm.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L948** `const bool tts_drained =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L949** `wait_for_jobs(`：带超时和谓词的condition\_variable等待，释放mutex睡眠、唤醒后重查条件。

- **L950** `"TTS",`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L951** `tts_accepted,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L952** `tts_completed,`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L953** `600`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L956** `if (!tts_drained)`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L958** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L959** `<< "[Timeout] TTS tasks "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L960** `<< "did not finish in 600s\n";`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L967** `tts_worker.requestStop();`：合作式请求停止，区别于join等待；不会强制打断正运行的ONNX推理。

- **L968** `tts_worker.join();`：等待工作线程完全退出，确保之后不再访问被引用的模型/ALSA资源。

- **L972** `playback.close();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L973** `tts.shutdown();`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L980** `std::lock_guard<std::mutex>`：`std::lock_guard<std::mutex>` 是 RAII 模板锁，构造对象立即上锁，当前花括号结束自动解锁，异常退出也安全。

- **L981** `out(print_mutex);`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L983** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L984** `<< "\n=== ASR -> LLM -> TTS summary ===\n"`：`->`通过有效指针访问对象成员；需检查指针非空和生命周期。

- **L986** `<< "VAD segments: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L987** `<< producer.producedCount()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L988** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L990** `<< "ASR recognized: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L991** `<< consumer.processedCount()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L992** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L994** `<< "Audio queue dropped: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L995** `<< audio_queue.droppedCount()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L996** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L998** `<< "LLM accepted/completed/"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L999** `<< "success/failed/rejected: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1000** `<< llm_accepted`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1001** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1002** `<< llm_completed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1003** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1004** `<< llm_successful`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1005** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1006** `<< llm_failed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1007** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1008** `<< llm_rejected`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1009** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1011** `<< "TTS accepted/completed/"`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1012** `<< "success/failed/rejected/empty: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1013** `<< tts_accepted`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1014** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1015** `<< tts_completed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1016** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1017** `<< tts_successful`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1018** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1019** `<< tts_failed`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1020** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1021** `<< tts_rejected`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1022** `<< '/'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1023** `<< tts_empty`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1024** `<< '\n'`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1026** `<< "Skipped VISION: "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1027** `<< skipped_vision`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1028** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1030** `if (!producer.ok())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L1032** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L1033** `<< "[VAD] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1034** `<< producer.error()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1035** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1038** `if (!consumer.ok())`：条件分支开始，内部布尔谓词决定进入哪条初始化/错误/正常执行路径。

- **L1040** `std::cerr`：把失败诊断写stderr，便于区别正常标准日志。

- **L1041** `<< "[ASR] "`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1042** `<< consumer.error()`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1043** `<< '\n';`：本行参与上一条声明、参数列表或语句；括号、逗号、分号决定实参分组与作用域。

- **L1051** `const bool passed =`：`const`防止通过当前名字修改对象；引用/指针语法还要区分是否拥有资源。

- **L1052** `producer.ok() &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1053** `consumer.ok() &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1055** `audio_queue.droppedCount() == 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1057** `llm_drained &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1058** `tts_drained &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1060** `llm_accepted > 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1061** `llm_accepted == llm_completed &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1062** `llm_successful == llm_accepted &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1063** `llm_failed == 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1064** `llm_rejected == 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1066** `tts_accepted == llm_successful &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1067** `tts_completed == tts_accepted &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1068** `tts_successful == tts_accepted &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1069** `tts_failed == 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1070** `tts_rejected == 0 &&`：布尔逻辑短路组合，决定任务是否有效、是否拒绝或整体PASS。

- **L1071** `tts_empty == 0;`：初始化或赋值语句，更新局部/成员/任务状态；C\+\+对象拷贝或移动由表达式类型决定。

- **L1073** `std::cout`：输出日志及计数，注意并行回调需要print\_mutex防止交织。

- **L1074** `<< (passed ? "PASS\n" : "FAIL\n");`：结束前面的函数调用/参数列表并执行相应动作，检查返回码/错误信息。

- **L1076** `return passed ? 0 : 1;`：函数返回：以真实类型/状态表示成功失败；非0主函数退出码可供Shell判断。

## 真实源文件：`CMakeLists.txt`

【源码可确认】第三阶段新增或修改的核心文件。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/CMakeLists.txt`。归档长度 **309 行**，SHA\-256 完整值 `693a117f29b226cba7ac00f81d2f903f64759ad3a0e4f2bf41f93dee956bd6bf`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```Plaintext
cmake_minimum_required(VERSION 3.16)
project(rk3576_multimodal LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
find_package(Threads REQUIRED)

option(BUILD_WITH_RKLLM "Build the real Rockchip RKLLM backend" OFF)
option(BUILD_WITH_VLM "Require a real VLM SDK adapter (not included yet)" OFF)
option(ENABLE_SHERPA_ASR "Build ALSA + sherpa-onnx audio pipeline" OFF)
set(SHERPA_ONNX_ROOT
    "${CMAKE_CURRENT_SOURCE_DIR}/../asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu"
    CACHE PATH "Root of sherpa-onnx aarch64 shared CPU runtime")

if(BUILD_WITH_VLM)
    message(FATAL_ERROR "VLM Runtime/SDK adapter is not implemented yet.")
endif()

set(RKLLM_SDK_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../rkllm_sdk"
    CACHE PATH "Root directory of the RKLLM SDK")

if(BUILD_WITH_RKLLM)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
        message(FATAL_ERROR "The real RKLLM backend currently requires Linux.")
    endif()

    if(NOT CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
        message(FATAL_ERROR "The current RKLLM library requires Linux AArch64.")
    endif()

    set(RKLLM_API_DIR "${RKLLM_SDK_ROOT}/rkllm-runtime/Linux/librkllm_api")
    set(RKLLM_INCLUDE_DIR "${RKLLM_API_DIR}/include")
    set(RKLLM_RUNTIME_LIBRARY "${RKLLM_API_DIR}/aarch64/librkllmrt.so")

    if(NOT EXISTS "${RKLLM_INCLUDE_DIR}/rkllm.h")
        message(FATAL_ERROR "RKLLM header not found: ${RKLLM_INCLUDE_DIR}/rkllm.h")
    endif()

    if(NOT EXISTS "${RKLLM_RUNTIME_LIBRARY}")
        message(FATAL_ERROR "RKLLM runtime library not found: ${RKLLM_RUNTIME_LIBRARY}")
    endif()

    message(STATUS "Real RKLLM backend enabled")
    message(STATUS "RKLLM include: ${RKLLM_INCLUDE_DIR}")
    message(STATUS "RKLLM library: ${RKLLM_RUNTIME_LIBRARY}")
endif()

function(project_warnings target)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4 /utf-8)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endfunction()

add_library(multimodal_core
    src/video/latest_frame_buffer.cpp
    src/ai/llm_engine.cpp
    src/ai/llm_worker.cpp
    src/ai/vlm_engine.cpp
    src/ai/rk_backends_unavailable.cpp
    src/router/intent_router.cpp
    src/app/request_processor.cpp
)

target_include_directories(multimodal_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(multimodal_core PUBLIC Threads::Threads)

if(BUILD_WITH_RKLLM)
    target_sources(multimodal_core PRIVATE src/ai/rkllm_backend.cpp)
    target_include_directories(multimodal_core PRIVATE "${RKLLM_INCLUDE_DIR}")
    target_link_libraries(multimodal_core PUBLIC "${RKLLM_RUNTIME_LIBRARY}")
    target_compile_definitions(multimodal_core PRIVATE RK3576_WITH_RKLLM=1)
endif()

project_warnings(multimodal_core)

if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    set(CAMERA_CAPTURE_SOURCE src/video/video_capture.cpp)
else()
    set(CAMERA_CAPTURE_SOURCE src/video/video_capture_unavailable.cpp)
    message(STATUS "V4L2 unavailable: building portable core/CLI with explicit camera error")
endif()

add_library(multimodal_camera
    src/video/camera_service.cpp
    ${CAMERA_CAPTURE_SOURCE}
)

target_link_libraries(multimodal_camera PUBLIC multimodal_core)
project_warnings(multimodal_camera)

add_executable(rk3576_multimodal
    src/main.cpp
    src/app/cli.cpp
)

target_link_libraries(rk3576_multimodal PRIVATE multimodal_camera)
project_warnings(rk3576_multimodal)

# 操作 2.8：真实 RKLLMWorker 实机验证。
if(BUILD_WITH_RKLLM)
    add_executable(
        rkllm_worker_smoke
        src/ai/llm_worker_smoke.cpp
    )

    target_link_libraries(
        rkllm_worker_smoke
        PRIVATE multimodal_core
    )

    project_warnings(rkllm_worker_smoke)
endif()


# Optional audio pipeline. Disabled in the original portable/RKLLM-only builds.
if(ENABLE_SHERPA_ASR)
    if(NOT CMAKE_SYSTEM_NAME STREQUAL "Linux")
        message(FATAL_ERROR "ALSA audio pipeline currently requires Linux")
    endif()

    find_package(ALSA REQUIRED)
    set(SHERPA_INCLUDE_DIR "${SHERPA_ONNX_ROOT}/include")
    set(SHERPA_LIBRARY "${SHERPA_ONNX_ROOT}/lib/libsherpa-onnx-c-api.so")
    if(NOT EXISTS "${SHERPA_INCLUDE_DIR}/sherpa-onnx/c-api/c-api.h")
        message(FATAL_ERROR "sherpa-onnx C API header missing: ${SHERPA_INCLUDE_DIR}")
    endif()
    if(NOT EXISTS "${SHERPA_LIBRARY}")
        message(FATAL_ERROR "sherpa-onnx C API library missing: ${SHERPA_LIBRARY}")
    endif()

    add_library(multimodal_audio
        src/audio/audio_capture.cpp
        src/audio/audio_preprocessor.cpp
        src/audio/asr_service.cpp
        src/audio/asr_pipeline.cpp
        src/audio/vad_audio_worker.cpp
    )
    target_include_directories(multimodal_audio PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        "${SHERPA_INCLUDE_DIR}")
    target_link_libraries(multimodal_audio PUBLIC
        Threads::Threads ALSA::ALSA "${SHERPA_LIBRARY}")
    project_warnings(multimodal_audio)

    # Restore previously used ASR verification targets.
    foreach(smoke IN ITEMS audio_capture_smoke asr_live_smoke
                           asr_pipeline_smoke asr_vad_smoke)
        add_executable(${smoke} "src/audio/${smoke}.cpp")
        target_link_libraries(${smoke} PRIVATE multimodal_audio)
        project_warnings(${smoke})
    endforeach()

    add_executable(asr_route_smoke src/audio/asr_route_smoke.cpp)
    target_link_libraries(asr_route_smoke PRIVATE multimodal_audio multimodal_camera)
    project_warnings(asr_route_smoke)

    # Operation 2.9: actual mic -> VAD -> ASR -> asynchronous RKLLM.
    if(BUILD_WITH_RKLLM)
        add_executable(asr_llm_smoke src/audio/asr_llm_smoke.cpp)
        target_link_libraries(asr_llm_smoke PRIVATE multimodal_audio multimodal_core)
        project_warnings(asr_llm_smoke)
    endif()
endif()


include(CTest)

if(BUILD_TESTING)

    # Mock Backend 测试，不加载模型、不使用 NPU。
    add_executable(llm_worker_tests tests/llm_worker_tests.cpp)
    target_link_libraries(llm_worker_tests PRIVATE multimodal_core)
    project_warnings(llm_worker_tests)
    add_test(NAME llm_worker_tests COMMAND llm_worker_tests)
    set_tests_properties(llm_worker_tests PROPERTIES TIMEOUT 15)

    if(NOT BUILD_WITH_RKLLM)
        add_executable(core_tests tests/core_tests.cpp)
        target_link_libraries(core_tests PRIVATE multimodal_core)
        project_warnings(core_tests)
        add_test(NAME core_tests COMMAND core_tests)

        add_test(NAME cli_smoke COMMAND ${CMAKE_COMMAND}
            -DAPP=$<TARGET_FILE:rk3576_multimodal>
            -DTEST_DATA=${CMAKE_CURRENT_SOURCE_DIR}/tests
            -P ${CMAKE_CURRENT_SOURCE_DIR}/tests/cli_smoke.cmake)

        set_tests_properties(core_tests cli_smoke PROPERTIES TIMEOUT 20)
    endif()

    add_executable(camera_service_tests
        tests/camera_service_tests.cpp
        tests/camera_test_capture.cpp
        src/video/camera_service.cpp)

    target_include_directories(camera_service_tests PRIVATE tests)
    target_link_libraries(camera_service_tests PRIVATE multimodal_core)
    project_warnings(camera_service_tests)
    add_test(NAME camera_service_tests COMMAND camera_service_tests)
    set_tests_properties(camera_service_tests PROPERTIES TIMEOUT 20)

endif()
# ==========================================================
# Stage 3.2: Offline TTSService + WAV smoke test
# ==========================================================

if(ENABLE_SHERPA_ASR)
    add_executable(tts_smoke
        src/audio/tts_service.cpp
        src/audio/tts_smoke.cpp
    )

    target_link_libraries(tts_smoke
        PRIVATE multimodal_audio
    )

    project_warnings(tts_smoke)
endif()


# ==========================================================
# Stage 3.3: TTS -> ALSA Playback smoke test
# ==========================================================

if(ENABLE_SHERPA_ASR)
    add_executable(tts_playback_smoke
        src/audio/tts_service.cpp
        src/audio/alsa_playback_service.cpp
        src/audio/tts_playback_smoke.cpp
    )

    target_link_libraries(tts_playback_smoke
        PRIVATE multimodal_audio
    )

    project_warnings(tts_playback_smoke)
endif()


# ==========================================================
# Stage 3.4: Reusable TTS library + asynchronous worker
# ==========================================================

if(ENABLE_SHERPA_ASR)

    add_library(multimodal_tts STATIC
        src/audio/tts_service.cpp
        src/audio/alsa_playback_service.cpp
        src/audio/tts_worker.cpp
    )

    target_include_directories(multimodal_tts PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
    )

    target_link_libraries(multimodal_tts PUBLIC
        multimodal_audio
    )

    project_warnings(multimodal_tts)

    add_executable(tts_worker_smoke
        src/audio/tts_worker_smoke.cpp
    )

    target_link_libraries(tts_worker_smoke PRIVATE
        multimodal_tts
    )

    project_warnings(tts_worker_smoke)

endif()
# Stage 3.4: TTSWorker queue and shutdown verification
if(ENABLE_SHERPA_ASR)
    add_executable(tts_worker_queue_smoke
        src/audio/tts_worker_queue_smoke.cpp
    )

    target_link_libraries(tts_worker_queue_smoke
        PRIVATE multimodal_tts
    )

    project_warnings(tts_worker_queue_smoke)
endif()
# ==========================================================
# Stage 3.5: ASR -> LLM -> TTS -> ALSA
# ==========================================================

if(ENABLE_SHERPA_ASR AND BUILD_WITH_RKLLM)

    add_executable(asr_llm_tts_smoke
        src/audio/asr_llm_tts_smoke.cpp
    )

    target_link_libraries(asr_llm_tts_smoke PRIVATE
        multimodal_audio
        multimodal_core
        multimodal_tts
    )

    project_warnings(asr_llm_tts_smoke)

endif()
```

### 核心语法与运行时机制精讲

**入口与职责**：请从本文件的完整原始源码逐行定位函数/类。声明文件定义外部接口，cpp实现业务动作，Smoke验证行为，CMake控制构建与链接。

**运行时资源与线程**：结合代码中的start/join/requestStop、initialize/shutdown及mutex作用域，区分主线程/后台线程和非拥有引用。

**参数和返回约定**：bool\+error消息表示初始化成功/失败；队列提交状态有Accepted/QueueFull/NotRunning三态；音频数据包含sample\_rate、samples、synthesis\_ms。

**安全边界**：要逐行检查所有SDK返回指针与错误路径，防止异常引起资源泄露以及回调捕获引用悬空。

## 真实源文件：`include/ai/llm_worker.h`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/ai/llm_worker.h`。归档长度 **82 行**，SHA\-256 完整值 `10a03767c8c3c3bf200ea2e857070a7b801d73828404e69d7b52b06aee1c127e`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++
#pragma once

#include "ai/llm_engine.h"

#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>

enum class LLMSubmitStatus
{
    Accepted,
    NotRunning,
    QueueFull
};

using LLMWorkerChunk =
    std::function<void(std::uint64_t, const std::string&)>;

using LLMWorkerDone =
    std::function<void(std::uint64_t, const InferenceResult&, double)>;

// 单消费者、有界排队；不拥有 LLMEngine。
// Engine 必须比 Worker 活得更久。
// 回调中不得销毁 Worker，也不能 join Worker 自己的线程。
class LLMWorker final
{
public:
    explicit LLMWorker(LLMEngine& engine, std::size_t capacity = 2);
    ~LLMWorker();

    LLMWorker(const LLMWorker&) = delete;
    LLMWorker& operator=(const LLMWorker&) = delete;

    // 只允许启动一次。
    bool start(std::string& error);

    // 正在执行的任务不占用等待队列容量。
    LLMSubmitStatus submit(std::uint64_t id,
                           std::string question,
                           LLMWorkerChunk on_chunk = {},
                           LLMWorkerDone on_done = {});

    // 停止接收新请求，排队任务取消。
    void requestStop() noexcept;

    // 需要先 requestStop，且不能从 Worker 线程内部调用。
    void join();

    std::size_t pendingCount() const;
    std::size_t rejectedCount() const;

private:
    struct Task
    {
        std::uint64_t id = 0;
        std::string question;
        LLMWorkerChunk on_chunk;
        LLMWorkerDone on_done;
        std::chrono::steady_clock::time_point enqueued_at{};
    };

    void run();

    LLMEngine& engine_;
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<Task> pending_;

    std::thread thread_;

    bool started_ = false;
    bool stop_requested_ = false;
    std::size_t rejected_ = 0;
};
```

## 真实源文件：`src/ai/llm_worker.cpp`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/ai/llm_worker.cpp`。归档长度 **204 行**，SHA\-256 完整值 `685fe657c9ac1a6b5443fa77a6a1f15c7cd305a2902f977b61b5b06eaa1a96e9`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++
#include "ai/llm_worker.h"

#include <atomic>
#include <exception>
#include <stdexcept>
#include <utility>

LLMWorker::LLMWorker(LLMEngine& engine, std::size_t capacity)
    : engine_(engine), capacity_(capacity)
{
    if (capacity_ == 0)
        throw std::invalid_argument(
            "LLMWorker capacity must be greater than zero");
}

LLMWorker::~LLMWorker()
{
    requestStop();
    join();
}

bool LLMWorker::start(std::string& error)
{
    std::lock_guard<std::mutex> lock(mutex_);
    error.clear();

    if (started_ || stop_requested_)
    {
        error = "LLMWorker can only be started once";
        return false;
    }

    try
    {
        thread_ = std::thread(&LLMWorker::run, this);
        started_ = true;
    }
    catch (const std::exception& e)
    {
        error = std::string("LLMWorker thread creation failed: ")
              + e.what();
        return false;
    }

    return true;
}

LLMSubmitStatus LLMWorker::submit(
    std::uint64_t id,
    std::string question,
    LLMWorkerChunk on_chunk,
    LLMWorkerDone on_done)
{
    {
        std::lock_guard<std::mutex> lock(mutex_);

        if (!started_ || stop_requested_)
            return LLMSubmitStatus::NotRunning;

        if (pending_.size() >= capacity_)
        {
            ++rejected_;
            return LLMSubmitStatus::QueueFull;
        }

        Task task;
        task.id = id;
        task.question = std::move(question);
        task.on_chunk = std::move(on_chunk);
        task.on_done = std::move(on_done);
        task.enqueued_at = std::chrono::steady_clock::now();

        pending_.push_back(std::move(task));
    }

    cv_.notify_one();
    return LLMSubmitStatus::Accepted;
}

void LLMWorker::requestStop() noexcept
{
    {
        std::lock_guard<std::mutex> lock(mutex_);
        stop_requested_ = true;
    }

    cv_.notify_all();
}

void LLMWorker::join()
{
    if (thread_.joinable())
        thread_.join();
}

std::size_t LLMWorker::pendingCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return pending_.size();
}

std::size_t LLMWorker::rejectedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return rejected_;
}

void LLMWorker::run()
{
    for (;;)
    {
        Task task;
        bool cancelled = false;

        {
            std::unique_lock<std::mutex> lock(mutex_);

            cv_.wait(lock, [this] {
                return stop_requested_ || !pending_.empty();
            });

            if (pending_.empty() && stop_requested_)
                return;

            task = std::move(pending_.front());
            pending_.pop_front();
            cancelled = stop_requested_;
        }

        InferenceResult result;
        double queue_wait_ms = -1.0;

        if (cancelled)
        {
            result.error_message =
                "LLM request cancelled: worker stopping";
        }
        else
        {
            const auto now = std::chrono::steady_clock::now();

            queue_wait_ms =
                std::chrono::duration<double, std::milli>(
                    now - task.enqueued_at).count();

            std::atomic<bool> chunk_callback_failed{false};

            try
            {
                result = engine_.inferStreaming(
                    task.question,
                    [&](const std::string& chunk)
                    {
                        if (!task.on_chunk)
                            return;

                        try
                        {
                            task.on_chunk(task.id, chunk);
                        }
                        catch (...)
                        {
                            chunk_callback_failed.store(true);
                        }
                    });
            }
            catch (const std::exception& e)
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    std::string("LLMWorker inference exception: ")
                    + e.what();
            }
            catch (...)
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    "LLMWorker inference: unknown exception";
            }

            if (chunk_callback_failed.load())
            {
                result.success = false;
                result.text.clear();
                result.error_message =
                    "LLMWorker chunk callback threw an exception";
            }
        }

        if (task.on_done)
        {
            try
            {
                task.on_done(task.id, result, queue_wait_ms);
            }
            catch (...)
            {
                // 上层回调异常不能终止整个 Worker。
            }
        }
    }
}
```

## 真实源文件：`include/audio/asr_pipeline.h`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/asr_pipeline.h`。归档长度 **163 行**，SHA\-256 完整值 `4e40ad4170c560cd4151d55b99cc25b5572578a57b359c41813b524c0fd6e3ba`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

class ASRService;

// 一个完整的待识别音频段。
struct AudioSegment {
    std::uint64_t sequence = 0;

    // 操作 7 使用：S16_LE PCM。
    std::vector<std::int16_t> pcm;

    // 操作 8 使用：VAD 输出的 Float32。
    std::vector<float> samples;

    // 操作 10：阶段时间戳。
    // audio_end_estimated_at 为主机读取时钟推算的
    // VAD 音频段末尾时间，而非精确发声结束时间。
    bool timing_valid = false;

    std::chrono::steady_clock::time_point
        audio_end_estimated_at{};

    std::chrono::steady_clock::time_point
        vad_ready_at{};

    std::chrono::steady_clock::time_point
        enqueued_at{};
};

// 有界音频段队列。
class AudioBufferQueue {
public:
    explicit AudioBufferQueue(std::size_t capacity);

    bool push(AudioSegment segment);
    bool pop(AudioSegment& segment);

    void close();

    std::size_t droppedCount() const;

private:
    const std::size_t capacity_;

    mutable std::mutex mutex_;
    std::condition_variable cv_;
    std::deque<AudioSegment> items_;

    bool closed_ = false;
    std::size_t dropped_ = 0;
};

// 操作 7 的音频生产者。
class AudioWorker {
public:
    AudioWorker(
        std::string device,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t segment_count
    );

    ~AudioWorker();

    AudioWorker(const AudioWorker&) = delete;
    AudioWorker& operator=(const AudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();

    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();

    std::string device_;
    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t segment_count_;

    std::atomic<bool> stop_requested_{false};
    std::thread thread_;

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};

// ASR 消费者。
// 支持操作 9 的可选识别文本回调。
class ASRWorker {
public:
    using TextCallback =
        std::function<void(const std::string&)>;

    ASRWorker(
        AudioBufferQueue& queue,
        ASRService& asr,
        std::mutex& print_mutex,
        TextCallback on_text = {}
    );

    ~ASRWorker();

    ASRWorker(const ASRWorker&) = delete;
    ASRWorker& operator=(const ASRWorker&) = delete;

    void start();
    void join();

    bool ok() const {
        return ok_;
    }

    const std::string& error() const {
        return error_;
    }

    std::size_t processedCount() const {
        return processed_;
    }

private:
    void run();

    AudioBufferQueue& queue_;
    ASRService& asr_;
    std::mutex& print_mutex_;

    TextCallback on_text_;

    std::thread thread_;

    bool ok_ = false;
    std::string error_;
    std::size_t processed_ = 0;
};
```

## 真实源文件：`include/audio/asr_service.h`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/asr_service.h`。归档长度 **53 行**，SHA\-256 完整值 `53cd22464e052cf94892f124ed680e78b73b95c3c7a7ae284a8421cda13d467f`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include <string>
#include <vector>

// sherpa-onnx C API 的模型句柄前向声明。
// 具体定义由官方 c-api.h 提供。
struct SherpaOnnxOfflineRecognizer;

// ASRService：封装离线语音识别模型。
// 一个对象持有一个常驻的 Recognizer。
class ASRService
{
public:
    ASRService() = default;

    // 析构函数：自动释放模型资源。
    ~ASRService();

    // 禁止复制，防止两个对象重复释放模型句柄。
    ASRService(const ASRService&) = delete;
    ASRService& operator=(const ASRService&) = delete;

    // 加载模型和词表。
    bool initialize(
        const std::string& model_path,
        const std::string& tokens_path,
        std::string& error
    );

    // 输入：
    // samples：16 kHz、Mono、归一化 Float32 PCM。
    //
    // 输出：
    // text：识别出的中文文本。
    // latency_ms：本次识别接口耗时，单位毫秒。
    // error：失败原因。
    bool recognize(
        const std::vector<float>& samples,
        std::string& text,
        double& latency_ms,
        std::string& error
    );

    // 释放模型资源。
    // 可以重复调用。
    void shutdown() noexcept;

private:
    // sherpa-onnx 离线模型实例句柄。
    const SherpaOnnxOfflineRecognizer* recognizer_ = nullptr;
};
```

## 真实源文件：`include/audio/vad_audio_worker.h`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/audio/vad_audio_worker.h`。归档长度 **55 行**，SHA\-256 完整值 `08ce86b0d0197bb0709ad5005fecd9e8b1308af3a8b7124d9ba42a070cad9842`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#pragma once

#include "audio/asr_pipeline.h"

#include <atomic>
#include <cstddef>
#include <mutex>
#include <string>
#include <thread>

class VadAudioWorker {
public:
    VadAudioWorker(
        std::string device,
        std::string vad_model,
        AudioBufferQueue& queue,
        std::mutex& print_mutex,
        std::size_t record_seconds
    );

    ~VadAudioWorker();

    VadAudioWorker(const VadAudioWorker&) = delete;
    VadAudioWorker& operator=(const VadAudioWorker&) = delete;

    void start();
    void requestStop() noexcept;
    void join();

    // 仅在 join() 之后读取以下状态。
    bool ok() const { return ok_; }
    const std::string& error() const { return error_; }
    std::size_t producedCount() const {
        return produced_;
    }

private:
    void run();

    std::string device_;
    std::string vad_model_;

    AudioBufferQueue& queue_;
    std::mutex& print_mutex_;

    std::size_t record_seconds_;

    std::atomic<bool> stop_requested_{false};
    std::thread thread_;

    bool ok_ = false;
    std::string error_;
    std::size_t produced_ = 0;
};
```

## 真实源文件：`include/router/intent_router.h`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/include/router/intent_router.h`。归档长度 **15 行**，SHA\-256 完整值 `4bd47b86d95d2da94b824d9ff9d75000c9980b1d7b5b407b086b98f1651d64aa`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++
#pragma once
#include <string>

enum class RequestType { Text, Vision };
struct RouteDecision
{
    RequestType type = RequestType::Text;
    std::string reason;
};
class IntentRouter
{
public:
    RouteDecision route(const std::string& question) const;
};
const char* requestTypeName(RequestType type);
```

## 真实源文件：`src/router/intent_router.cpp`

【源码可确认】此前阶段已实现、第三阶段复用的真实源码。源码路径：`/home/cat/projects/RK3576/rk3576_multimodal/src/router/intent_router.cpp`。归档长度 **74 行**，SHA\-256 完整值 `791099a42b0086cf1af55f33769c14c172edb3c65ffaee895cda0f79569f0c6e`。此文件以下全文是归档原文，不是改写的示例。

### 完整源码（最终 PASS 归档，不省略）

```C++

#include "router/intent_router.h"

#include <algorithm>

// UTF-8 子串匹配的最小路由器：
// 只将询问当前相机画面的句子识别为 VISION；
// “摄像头驱动原理是什么”等知识问题仍为 TEXT。
RouteDecision IntentRouter::route(
    const std::string& question) const
{
    std::string normalized = question;

    // ASCII 英文字母转小写；
    // 中文 UTF-8 字节保持不变。
    std::transform(
        normalized.begin(),
        normalized.end(),
        normalized.begin(),
        [](unsigned char c) {
            return c >= 'A' && c <= 'Z'
                ? static_cast<char>(c + 32)
                : static_cast<char>(c);
        }
    );

    const char* vision_phrases[] = {
        u8"前面有什么",
        u8"摄像头里",
        u8"面前是什么",
        u8"看看前方",
        u8"当前画面",
        u8"现在的画面",
        u8"摄像头看到",
        u8"你看到了什么",
        u8"眼前有什么",
        u8"看看这个",
        u8"描述画面",
        u8"前方道路上有什么",
        u8"前方道路有什么",
        u8"前方有什么",
        u8"前面道路有什么",
        "what do you see",
        "what is in front",
        "what's in front",
        "camera view",
        "describe the scene",
        "current image"
    };

    for (const auto* phrase : vision_phrases)
    {
        if (normalized.find(phrase) !=
            std::string::npos)
        {
            return {
                RequestType::Vision,
                std::string("matched: ") + phrase
            };
        }
    }

    return {
        RequestType::Text,
        "default text rule"
    };
}

const char* requestTypeName(RequestType type)
{
    return type == RequestType::Vision
        ? "VISION"
        : "TEXT";
}
```

---

**源文件与正文核对完毕**：完整源码已直接嵌入 Word 和 Markdown；若需还原为可编译目录结构，应从原始 tar\.gz 提取各文件，而不是把 Markdown 的代码围栏粘成一个\.cpp。

