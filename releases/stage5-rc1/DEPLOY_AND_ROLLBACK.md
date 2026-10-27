# Stage5 RC1 版本化部署与回滚

本轮仅部署独立 RC、重新构建和确定性测试，不切换任何正式入口。以下“切换”命令均为**尚未执行，必须等待用户单独批准**。原稳定工程及 `build/stage5_full` 保持原路径。RC 不是脱离模型、SDK及当前隔离环境的便携包。

## 1. 固定路径与保护

```bash
isolation=/home/cat/projects/RK3576/rk3576_multimodal_stage5_review
stable=/home/cat/projects/RK3576/rk3576_multimodal
rc="$isolation/releases/stage5-rc1"
test "$(readlink -f -- "$isolation")" = "$isolation" || exit 1
test "$(readlink -f -- "$stable")" = "$stable" || exit 1
test "$rc" = "$isolation/releases/stage5-rc1" || exit 1
test -x "$stable/build/stage5_full/asr_llm_tts_smoke" || exit 1
```

`readlink -f` 拒绝符号链接带来的路径漂移。禁止 `cp -r RC stable`、删除旧 build、修改模型/SDK或系统温控。原版本完整源码、构建产物由既有目录保留；321 项清单及四个历史验收程序指纹位于历史证据归档。本轮再次读取比对，未另外复制大模型。

## 2. 新机器或另一个版本目录的部署步骤

先检查外层 `.tgz.sha256` 和 `SHA256SUMS`。用 `tar -tzf` 查看内容，必须全部位于 `stage5-rc1/`，无绝对路径、`..`、反斜杠、符号链接、设备文件或重复条目。本轮自动校验脚本还逐文件核对 `PACKAGE_MANIFEST.json` 中 SHA256 和大小。

```bash
test ! -e "$rc" && test ! -L "$rc" || exit 1
test "$(df -B1 --output=avail "$isolation" | tail -1)" -gt 734003200 || exit 1
# 将实际 RC 外层归档放在隔离 reports/stage5_rc1_board 中；先核对随附外层 SHA。
sha256sum -c stage5-rc1.tgz.sha256
tar -tzf stage5-rc1.tgz
# 仅在完成路径与成员校验后：独占新目录，不覆盖历史目录。
tar --keep-old-files --no-same-owner --no-same-permissions -xzf stage5-rc1.tgz -C "$isolation/releases"
cd "$rc"
sha256sum -c SHA256SUMS
python3 -I -B tools/build.py
```

上面是重建说明，**不能直接在本轮已经创建的 RC 同名目录重复执行**。`tools/build.py` 要求普通 cat 用户、确切授权路径、新 build 和新日志目录，逐步骤限制 90/600/150 秒并监控磁盘 500 MiB 下限。失败保留所有产物，不清理任何目录。独立移植到其他根路径需要先审查构建/启动脚本中的路径约束；不是修改系统或使用 sudo 编译的理由。

## 3. 切换前少量冒烟

1. 接回 HyperX；确认 `/proc/asound/cards` 可识别；从现有 cat 桌面运行 `bash "$rc/tools/launch.sh" gui 4`。
2. 点击开始，等待监听，问“一加一等于几”，听完再问“前面有什么”；确认耳机、画面描述、识别文本、路由和回答。
3. 点击安全停止，确认有序退出；重新开始一轮后关闭窗口，等待后台退出。
4. 可在独立终端对本次记录的 launcher PID 发 SIGTERM。发信号前用 `/proc/PID/exe` 和命令行确认其确属 RC，不能使用 `pkill` 扫描终止。CLI 可直接 Ctrl+C。

成功标准：实际两条回答听到、正确路由，终端 shutdown complete，退出码0，Camera/ALSA关闭，NPU句柄恢复到已登记桌面基线，没有强杀。固定输入回放或 `TTS success=true` 不能替代人工听音。当前收尾预检未发现 HyperX，故本轮不新增真实声音验收，复用已通过5.5证据；此步留作正式切换前的必要检查。

## 4. 经批准后的入口切换设计（未执行）

优先保留两个显式命令：RC 的 `tools/launch.sh` 与原稳定 CLI，而不覆盖原工程。如果确需一个入口，可在隔离范围建立 `releases/current.env` 选择文件；它没有任何 systemd/autostart 效果，调用者必须主动读取。先创建指向已验收5.5入口的回滚记录：

```bash
# 以下命令仅在用户明确批准后执行。
cd "$isolation/releases"
test ! -e current.env && test ! -L current.env || exit 1
stamp=$(date -u +%Y%m%d_%H%M%S)_$$
backup="current.before_rc1.$stamp.env"
test ! -e "$backup" || exit 1
(set -o noclobber; printf 'STAGE5_ENTRY=%s\n' "$isolation/tools/stage5_05_launch_gui.sh" > "$backup")
next="current.next.$stamp.env"
(set -o noclobber; printf 'STAGE5_ENTRY=%s\n' "$rc/tools/launch.sh" > "$next")
test -f "$next" && test ! -L "$next" || exit 1
mv -T -- "$next" current.env
```

选择文件只存可信绝对路径，调用前必须白名单校验；历史 GUI 入口参数是 `4`，RC 入口参数是 `gui 4`，二者**不能不分版本地直接复用相同参数**。不 `source` 任意下载文件。正式部署时应先停完旧会话再启动另一个版本，防止Camera/ALSA/NPU竞争。

## 5. 回滚（未执行）

先用 RC 窗口安全停止/关闭或对已核实的本次 PID 发信号，等待清理；不要强制删除运行目录。随后直接启动原已验收 GUI：

```bash
cd "$isolation"
bash tools/stage5_05_launch_gui.sh 4
```

该路径重新使用5.5既有二进制，适合撤销本次 RC 包装/启动脚本问题。若要退回最初主稳定 CLI，则普通 cat 用户执行：

```bash
set -a
source "$isolation/tools/stage5_board_paths.sh"
set +a
# 先动态确定 HyperX 的实际 CARD ID，不能写死历史数字声卡。
audio=$(python3 -I -B -c 'import sys;sys.path.insert(0,sys.argv[1]+"/tools");from stage5_05_voice_run import discover_audio,devices;a=discover_audio();assert devices(a)["clear"];print(a["alsa_device"])' "$isolation")
"$stable/build/stage5_full/asr_llm_tts_smoke" "$audio" "$STAGE5_ASR" "$STAGE5_VAD" "$STAGE5_QWEN" "$STAGE5_KOKORO" "$audio" 120 2 17 "$STAGE5_VLM" "$STAGE5_VISION" /dev/video11
```

原稳定版本的信号行为以其历史实现为准，不能把5.1后的协作退出结论套给旧程序。旧程序需要正常结束有限监听，并让已接收回答播放结束。回滚成功标准：所运行 `/proc/PID/exe` 是选定旧路径，原文件 SHA 未变，TEXT/VISION及播放正常，旧会话资源已释放。

如已经建立选择文件，以下命令仍需单独批准，并把 `backup` 换为上次保存的确切文件名：

```bash
cd "$isolation/releases"
backup=current.before_rc1_实际已记录文件名.env  # 换为保存的实际 basename
case "$backup" in current.before_rc1.*.env) ;; *) exit 1;; esac
test -f "$backup" && test ! -L "$backup" || exit 1
test "$(cat -- "$backup")" = "STAGE5_ENTRY=$isolation/tools/stage5_05_launch_gui.sh" || exit 1
test -f current.env && test ! -L current.env || exit 1
test "$(cat current.env)" = "STAGE5_ENTRY=$rc/tools/launch.sh" || exit 1
restore="current.restore.$(date -u +%Y%m%d_%H%M%S)_$$.env"
(set -o noclobber; cat -- "$backup" > "$restore")
mv -T -- "$restore" current.env
test "$(cat current.env)" = "STAGE5_ENTRY=$isolation/tools/stage5_05_launch_gui.sh" || exit 1
```

示例占位值本身不会通过case白名单，避免未经选择就执行回滚。所有旧源码、模型、build、日志、RC 都保留，回滚不依赖删除目录或覆盖二进制。
