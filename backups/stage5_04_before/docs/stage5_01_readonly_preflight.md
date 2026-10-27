# 5.1 第一阶段只读预检实测与第二阶段申请

本文件保留第一阶段只读结果及当时第二阶段申请命令。**后续三阶段均已获授权并完成，5.1正式验收通过，见 [第三阶段实机验收](stage5_01_board_acceptance.md)。** 下文“未执行/待确认”属于申请时历史状态，不能用于重新执行排他部署。

## 操作 1：真实只读执行结果

最终查询时间：2026-10-17 18:27:18～18:27:20，Asia/Hong_Kong（UTC+08:00）。主机：`cat@192.168.10.27`。

| 用户要求 | 实际结果与证据 | 判定 |
|---|---|---|
| SSH正常 | 系统OpenSSH，非交互认证成功；最终SSH退出0，无连接/查询超时 | 通过 |
| 独立目录不存在 | 每次查询先检查目录/悬空符号链接；最终检查前后均不存在 | 通过；尚未mkdir |
| 足够空间 | `/dev/mmcblk0p3`：29G总量、26G已用、2.1G可用、93%使用率；精确可用2,238,889,984 bytes，1,567,756可用inode | 满足本次2GiB编译/日志预留预算；该预算不是已测新构建大小 |
| 原工程与旧构建不变 | 源码/配置/测试及`build/stage5_full`共321项前后hash、大小、mtime/符号链接目标一致；旧可执行文件存在 | 通过（覆盖范围见原始inventory的original_scope） |
| 复用模型/SDK | 20项模型/词表/目录/头文件/库/旧程序均存在且可读；SDK取自稳定构建缓存；ldd退出0，无not found | 路径及加载器依赖检查通过；未执行新程序或模型 |
| 所需设备无占用 | root只读fuser确认`/dev/video11`、`/dev/snd/pcmC1D0c`、`/dev/snd/pcmC1D0p`、`/dev/dri/renderD129`无用户；stdout/stderr空，fuser退出1表示未找到占用者 | 通过，仅为查询时刻快照；阶段2/3执行前需重查 |

实际系统：`aarch64`、`Linux 6.1.99-rk3576`；CMake 3.25.1；Debian GCC 12.2.0。内存总量3.8GiB，available约3.1GiB，Swap 0。旧稳定程序经`file`识别为ARM aarch64；**这不是本轮修改已经编译为ARM64的证据**。

保留的旧稳定可执行文件：

```text
/home/cat/projects/RK3576/rk3576_multimodal/build/stage5_full/asr_llm_tts_smoke
SHA256 c22de21ef6b82b4aee4cc2d0e4f2e1850960c23c356df2f3fc033b9d1c61fcc4
size 244408 bytes
```

板端CMake、完整语音入口、VLM后端、Router的SHA256也与本地修改前快照及`4.md`指纹一致。模型权重只查存在性/可读性/大小，没有复制或为本次检查读取整个模型计算hash。

### 原有3A服务的实际占用

广泛查询发现PID423、root、`/usr/bin/rkaiq_3A_server`打开`/dev/video0`、`video1`、`video15`、`video16`、`video17`、`video18`。sysfs名称包括CIF输入、raw读入、`rkisp-statistics`及`rkisp-input-params`；本次Camera目标`video11`为`rkisp_mainpath`，没有占用者。现有3A服务保持原状，没有结束、重启或改配置；不能把“目标capture节点空闲”写成“所有ISP节点都无人使用”。3A与新Camera的实际协同仍由第三阶段回归确认。

RKNPU节点根据sysfs驱动确认为`/dev/dri/renderD129 → /sys/bus/platform/drivers/RKNPU`；`renderD128`对应rockchip-drm，不把两者混淆。HyperX Cloud III实际为card1/device0，录放两向的`/proc/asound`状态均为closed。

### 查询中遇到的问题与真实返回

普通用户无法读取部分root进程的/proc fd，所以没有把“可见进程无占用”直接判为空闲。只尝试非交互`sudo -n /usr/bin/fuser -v`查询，没有使用-k或任何发送信号参数。

首次fuser使用独立`--`参数时，板端工具返回“未指定进程/用法”，该轮整体预检SSH退出22，判据未通过；已保留失败原文。随后去掉不兼容参数，再查得3A服务的其他ISP节点占用；最后对确切的测试目标节点查询，并重新完整预检，最终8个检查均为true、SSH退出0。没有伪造、覆盖或删除前述失败记录。

### 原始日志

```text
reports/stage5_01_board/readonly_guard_20261017_181540_720060/
reports/stage5_01_board/readonly_full_20261017_182201_324598/  # 首次fuser参数错误，SSH退出22
reports/stage5_01_board/readonly_full_20261017_182311_779187/  # 广泛节点占用查询
reports/stage5_01_board/readonly_full_20261017_182408_344229/  # 目标节点复查
reports/stage5_01_board/readonly_full_20261017_182718_018778/  # 最终完整预检，SSH退出0
```

每次保留`command.json`、未改写的`stdout.log`/`stderr.log`、`execution.json`；完整查询另存实际通过SSH stdin执行的脚本、脚本hash及从原始JSON解析的`inventory.json`。汇总见`readonly_preflight_summary.json`。命令总超时：guard本地30秒，完整远端120秒、本地150秒；各辅助只读查询20秒。

日志目前只写本地，因为第一阶段必须让远端独立目录继续不存在。获准创建隔离目录后，才可把本阶段日志归档到该目录的reports中。没有向原工程、模型、驱动或系统配置写入，没有上传文件或启动AI测试。

## 操作 2：已核实的复用路径

| 用途 | 板端真实路径 |
|---|---|
| ASR目录 | `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17` |
| VAD | `/home/cat/projects/RK3576/asr_runtime/vad/silero_vad.onnx` |
| Qwen | `/home/cat/projects/RK3576/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm` |
| Kokoro目录 | `/home/cat/projects/RK3576/tts_runtime/models/kokoro-multi-lang-v1_1` |
| VLM | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm` |
| Vision | `/home/cat/projects/RK3576/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn` |
| sherpa SDK/库 | `/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu` |
| RKLLM SDK | `/home/cat/projects/RK3576/rkllm_sdk` |
| RKNN头文件 | `/home/cat/projects/RK3576/rknn_test/include` |
| RKNN库 | `/usr/lib/librknnrt.so` |

缓存中的部分路径含`rk3576_multimodal/..`，上述表格使用其规范化实际路径。动态链接器已能找到RKLLM、RKNN、sherpa、ONNX Runtime、ALSA等库；没有据此宣称SDK接口兼容性或本轮推理已通过。

## 操作 3：第二阶段待确认的具体操作

**下列命令仅展示，尚未执行。授权申请只包含隔离上传、解压校验、ARM64编译和动态依赖检查；CTest、模型运行、音频播放、信号测试和SIGINT修复留在第三阶段另行确认。**

### 源码包与目录

本地候选包：`reports/stage5_01_local/board_package/stage5_01_review_preflight_v2.tgz`。精确文件列表和SHA256保存在对应`.manifest.json`及`.sha256`；旧候选包保持保留。本次只加入预检工具、阶段2仅编译脚本和最新报告，没有改生产C++/模型/Prompt。

唯一远端写入根：`/home/cat/projects/RK3576/rk3576_multimodal_stage5_review`，内含源码、`build/stage5_01_board`、`reports/stage5_01_board`。模型和SDK从上表原路径只读使用，不包含在包内。

### 上传、解压和校验（Windows PowerShell，逐条检查退出码）

```powershell
$ssh = 'C:\Windows\System32\OpenSSH\ssh.exe'
$scp = 'C:\Windows\System32\OpenSSH\scp.exe'
$pkg = 'reports/stage5_01_local/board_package/stage5_01_review_preflight_v2.tgz'
$opts = @('-o','BatchMode=yes','-o','ConnectTimeout=5','-o','StrictHostKeyChecking=yes','-o','UpdateHostKeys=no')

& $ssh -T @opts cat@192.168.10.27 'set -eu; p=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review; if test -e "$p" || test -L "$p"; then echo DESTINATION_EXISTS_STOP; exit 20; fi; umask 077; mkdir "$p"'
# 退出0才执行下一条；失败保留现场并停止。
& $scp -S $ssh @opts $pkg "$pkg.sha256" cat@192.168.10.27:/home/cat/projects/RK3576/rk3576_multimodal_stage5_review/
& $ssh -T @opts cat@192.168.10.27 'set -eu; cd /home/cat/projects/RK3576/rk3576_multimodal_stage5_review; sha256sum -c stage5_01_review_preflight_v2.tgz.sha256; tar --keep-old-files -xzf stage5_01_review_preflight_v2.tgz; sha256sum -c SOURCE_SHA256SUMS'
```

SSH不会自动接受新host key，SCP明确使用系统SSH；凭既有cat账户完成，不上传私钥或密码。`mkdir`前重新拒绝目录或符号链接已存在的情况；umask077只作用于新目录权限。归档在本地核验无绝对路径、父目录跳转、符号链接或模型/旧build成员；`--keep-old-files`防止解压覆盖已存在文件。每条命令的stdout/stderr及真实退出码将保存到本地`reports/stage5_01_board/phase2_*`，失败不继续。

### ARM64仅编译

```powershell
& $ssh -T @opts cat@192.168.10.27 'timeout --signal=TERM --kill-after=15s 840s bash /home/cat/projects/RK3576/rk3576_multimodal_stage5_review/tools/stage5_board_compile_only.sh'
```

该脚本实际配置命令如下：

```bash
ROOT=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
cmake -S "$ROOT" -B "$ROOT/build/stage5_01_board" \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON \
  -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON \
  -DSHERPA_ONNX_ROOT=/home/cat/projects/RK3576/asr_runtime/sherpa-onnx-v1.13.8-linux-aarch64-shared-cpu \
  -DRKLLM_SDK_ROOT=/home/cat/projects/RK3576/rkllm_sdk \
  -DRKNN_INCLUDE_DIR=/home/cat/projects/RK3576/rknn_test/include \
  -DRKNN_RUNTIME_LIBRARY=/usr/lib/librknnrt.so
cmake --build "$ROOT/build/stage5_01_board" --parallel 3
```

实际脚本优先读取已核实的稳定缓存路径，其指向与上述规范化路径一致；配置超时180秒、编译600秒、ldd15秒，超时保留真实错误码。不使用旧`stage5_board_build.sh`的“构建后立即CTest”流程，避免越过分阶段授权。BUILD_TESTING=ON只构建测试可执行文件，不自动运行CTest。CMake自身编译器探测属于构建流程，不访问音视频或NPU模型。

脚本拒绝已有新构建目录，校验包内文件、ARM64平台、输出父目录符号链接及至少2GiB剩余预算。日志写新目录`reports/stage5_01_board/compile_only_<UTC时间>/`，包括configure/build/ldd/session、真实退出码、阶段范围标记和原源码/稳定程序前后指纹。普通cat权限即可，不安装依赖、不sudo编译、不改ldconfig或系统环境文件。

### 日志回收和回退

阶段2获准后才会在新目录创建reports，并把本地只读预检记录同步到该目录的独立子目录。编译日志从新目录下载回本地，逐轮保留原文件，不混写原报告。

回退不需要覆盖原文件：结束本次编译任务，保留隔离目录及失败日志，继续保留原`build/stage5_full`程序。不会自动删除隔离目录、模型或系统文件；后续如需清理，应再明确范围。任何路径不符、目标已存在、依赖/空间变化、指纹改变或超时都会停止，不继续CTest/硬件程序。

## 操作 4：当前验收边界

现在只有只读预检通过。当前修改的ARM64编译、CTest、ASR/Qwen/VLM/TTS、实听、XRUN、模型/Worker退出及SIGINT/SIGTERM均未执行。已知信号缺陷将在第三阶段先记录真实行为，再在隔离工程最小修复并重编重验；外部强制清理不能作为优雅退出成功证据。

第二阶段需要用户明确确认以上上传、解压、编译范围；当前没有执行这些命令。
