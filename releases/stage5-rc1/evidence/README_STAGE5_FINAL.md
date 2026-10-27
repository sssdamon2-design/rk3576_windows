# RK3576 第五阶段最终隔离版本操作说明

本说明对应`stage5_05_source_final_v2`及`build/stage5_05_final_v2`，不把隔离版本覆盖为主工程。最终结果以`docs/stage5_05_final_acceptance.md`、`reports/stage5_05_local/validation_summary.json`和原始板端日志为准。

## 启动已有 Qt 版本

在开发板当前cat用户的桌面终端执行：

```bash
cd /home/cat/projects/RK3576/rk3576_multimodal_stage5_review
bash tools/stage5_05_launch_gui.sh 4
```

参数`4`为Kokoro线程数，可改为`2`；窗口也可在停止后切换。启动前保持Camera、HyperX和NPU无其他测试进程占用。脚本动态按HyperX名称和双工PCM发现设备，不写死数字声卡，引用原模型和SDK。新建专属报告/缓存目录，已有目录不会覆盖。使用现有X11桌面和认证，不能假装SSH终端自带屏幕。

点击开始后，GUI通过QProcess异步启动原语音入口；模型加载期间界面可操作。说“一加一等于几”，或“前面有什么”。等待耳机回答；本系统没有AEC和语音打断。停止方式可选排空或取消等待；正在执行的同步SDK请求仍允许完成。关闭窗口会先请求SIGINT，待后台清理后关闭，不要把外部强杀当安全退出。停止后再点击开始会创建新进程并重新加载模型。

每次`manual_gui_.../run_.../`保存终端、Request ID JSONL、结果和实际窗口截图。识别/回答来自结构化事件，诊断文本可能跨线程交错。界面只展示最近100行回答和400行诊断，完整日志不截断。2/4线程可配置不代表两者在任意散热环境下都有同样性能。

## 桌面DRM基线变化时重新只读预检

NPU实际使用`/dev/dri/card1`，已有systemd、logind和Xorg会持有桌面/seat相关DRM句柄。工具要求Camera/ALSA/render节点无持有者，primary节点只能保留已冻结的精确PID、启动标识、UID和命令行集合；新增模型进程拒绝。不能关闭系统桌面进程来强求所有DRM句柄为空。重启或显示会话更换后旧身份会失效，先运行只读检查生成全新基线并人工查看输出：

```bash
set -a
source tools/stage5_board_paths.sh
set +a
owner_baseline="$STAGE5_REVIEW/reports/stage5_05_board/owners_$(date -u +%Y%m%d_%H%M%S)_$$.json"
python3 -I -B tools/stage5_05_npu_inventory.py --output "$owner_baseline"
export STAGE5_NPU_OWNER_BASELINE="$owner_baseline"
bash tools/stage5_05_launch_gui.sh 4
```

`--output`必须为隔离reports下尚不存在的文件。未知持有者会拒绝；此操作不停止进程、不改设备权限或系统配置，也不把打开DRM句柄等同于可信NPU利用率。常规同一启动会话可继续使用当前已验证默认基线。

## 独立重新构建

`tools/stage5_board_paths.sh`包含已验证SDK和模型路径，不复制模型。用全新构建目录替换下面的示例名；目录已存在时停止，不能清理旧验收构建腾空间。

```bash
set -a
source tools/stage5_board_paths.sh
set +a
new_build="$STAGE5_REVIEW/build/stage5_05_reproduce_USER_LABEL"
test ! -e "$new_build" || exit 1
test "$(df -B1 --output=avail "$STAGE5_REVIEW" | tail -1)" -ge 524288000 || exit 1
cmake -S "$STAGE5_REVIEW/stage5_05_source_final_v2" -B "$new_build" -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=ON -DBUILD_QT_GUI=ON -DBUILD_WITH_RKLLM=ON -DBUILD_WITH_VLM=ON -DENABLE_SHERPA_ASR=ON -DSHERPA_ONNX_ROOT="$STAGE5_SHERPA" -DRKLLM_SDK_ROOT="$STAGE5_RKLLM" -DRKNN_INCLUDE_DIR="$STAGE5_RKNN_INCLUDE" -DRKNN_RUNTIME_LIBRARY="$STAGE5_RKNN_LIBRARY"
cmake --build "$new_build" --parallel 3
ctest --test-dir "$new_build" --output-on-failure --timeout 30
```

以上配置键与真实成功命令一致，环境变量由现有`stage5_board_paths.sh`定义。Qt可用性不足时`BUILD_QT_GUI=OFF`保留CLI。CTest使用Fake验证确定性逻辑，不等同于真实硬件全链路。

## 证据与复现

详见`docs/RK3576_STAGE5_ENGINEERING_MANUAL.md`及同名DOCX，源码逐文件全文见`docs/stage5_05_source_appendix.md`。基线冻结在`backups/stage5_05_before/`；完整Git格式差异、字节回放验证、CSV/JSON和证据索引在`reports/stage5_05_local/`。板端测试日志始终在隔离工程的`reports/stage5_05_board/`，本地`collected_*`保存逐文件SHA一致副本。

运行时不安装软件、不改设备树、驱动、内核、thermal或CPU governor。温度阈值来自本板Linux trip配置；本次90℃是保守测试护栏，不是芯片额定值。更换环境后需重新验证热条件。
