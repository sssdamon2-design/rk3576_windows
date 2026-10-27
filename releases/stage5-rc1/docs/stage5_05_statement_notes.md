# 5.5 Qt 适配与稳定性工具逐句说明

本文对应真实`BackendSession`、`SessionWindow`、Qt入口、共用`StopSignals`及测试工具。完整源码将由导出器逐文件保留。Qt代码是否通过真实ARM64构建和运行，以最终验收报告为准；本地SDK关闭的9项测试不能证明GUI可运行。

## BackendSession 的对象与启动语句

`class BackendSession final : public QObject`使适配器进入Qt对象和信号系统，`final`阻止派生类改变其停止契约。`Q_OBJECT`由AUTOMOC生成元对象信息；没有它，自定义信号不能连接。`QProcess process_`、`QFile terminal_`和`QTimer stopDeadline_`是成员值对象，全部由Qt线程持有。本类不持有模型、Frame或SDK借用指针。

构造函数将通道设为`MergedChannels`，让SDK stderr与业务stdout按实际到达顺序进入同一日志。`connect(sender,signal,this,lambda)`中的`this`是接收上下文，Qt在上下文销毁时断开连接。lambda只在上下文寿命内访问成员，不把裸窗口指针交给AI Worker。QProcess和窗口同属Qt线程，因此readyRead/finished在该线程更新控件；跨进程传来的是复制字节，绝不是后台C++对象的悬空引用。

`start()`先判断`active()`，重复启动返回false并产生可见错误。`QFileInfo(executable).isExecutable()`检查外层程序；真正exec失败仍由`errorOccurred(FailedToStart)`处理。日志使用`WriteOnly|NewOnly`，已经存在就拒绝，避免擦掉上轮证据。partial、stopping和shutdownSeen仅在新会话清理，不在旧会话运行时重置。

`process_.setProcessEnvironment(environment)`设置本次子进程环境，不调用全局qputenv与其他线程竞争。`process_.start(executable,arguments,ReadOnly)`异步启动，立即返回；QStringList中的每个参数独立传递，不进行shell插值。模型路径、设备名含空格或特殊字符也不被解释成命令。生产外层是`/usr/bin/stdbuf`，argv顺序为`-oL,-eL,CLI,capture,ASR,VAD,Qwen,Kokoro,playback,seconds,threads,sid,VLM,Vision,Camera`，threads的零基下标是10。

`started`只证明操作系统成功启动外层进程，不代表模型和设备全部就绪。页面必须依据原入口的加载、Camera ready和Listen日志更新状态。停止若发生于Starting，先记`stopping_`，等started再向已得到的子进程PID发送SIGINT；不会对PID 0或进程组发送信号。

## 停止与窗口关闭

`requestStop()`先检查状态，再设协作停止标志。`::kill(processId,SIGINT)`在普通Qt槽中执行，只发给QProcess拥有的子进程。这里没有异步signal handler。90秒单次定时器只报告“停止未通过”，不调用kill或waitForFinished；活跃同步SDK仍需要自然完成。真正永久阻塞的SDK无法由共享flag保证退出，这一限制必须保留。

`closeEvent()`发现后台仍在运行时先设置closing，调用`event->ignore()`保留窗口和回调接收者，再请求停止。收到finished时先排空可读输出、关闭诊断文件、恢复按钮、保存真实退出码和截图，再通过带上下文的singleShot关闭窗口。对象没有在Worker或QProcess回调中自我析构，QProcess析构也不是正常停止手段。

`orderly`同时要求NormalExit、exitCode=0和原入口`[Shutdown] complete`标记；GUI不会只凭窗口消失或kill返回0宣称清理完成。设备释放仍需进程外fuser、ALSA status、进程存在性和原工程指纹复核。90秒GUI提示与守护70/90秒失败清理是不同层次，最终强制终止一律记录失败。

## 输入缓冲与界面内存

`consume()`保留UTF-8字节到完整换行后才调用fromUtf8，避免一次readyRead正好拆开中文字符。原始字节原样写入独占terminal.log；超长未换行超过64KiB时清理显示缓冲并显式报错，原日志仍保留。窗口日志400块、答案100块、任务历史64条有上限，不把持续交互变为无界容器。

`SessionWindow`的控件由父窗口拥有，BackendSession为值成员；关闭事件保证其析构前子进程已经finished。startSession先创建UTC时间加UUID的独占子目录，旧会话profile关闭、任务表清空，再打开新会话。每次启动是一个新的CLI进程，不冒称已经专项验证真实SDK的进程内Worker restart。

profile定时器最多读取64KiB并按完整JSONL解析，Request ID与队列阶段分开。每条入队/出队都保留steady时间戳，只接受同一请求阶段较新的状态；即使日志写入顺序与实际时间顺序不同，也不会用较旧入队覆盖已观察到的出队。它是异步观测快照，不宣称瞬时硬实时队列长度。退出后不重新打开旧profile，避免把旧begin事件显示成新任务。

`Q_ASSERT(QThread::currentThread()==qApp->thread())`检查控件访问线程。界面只解析文本、诊断小记录并更新控件，没有加载模型、调用NPU、等待ALSA或同步join。自动回归使用真实Qt事件循环和按钮信号；Fake进程的文本在原日志明确标Fake，不计入硬件功能或性能。

## 共用信号类与Qt入口

`StopSignals`的类正文从5.1修复后的入口移至头文件，算法不变。必须在QApplication和SDK线程之前构造，后续线程继承阻塞集；普通sigwait线程接收SIGINT/SIGTERM并写atomic。Qt定时器读取该状态，发起普通closeEvent。没有在signal handler调用Qt、mutex、分配内存或join。

Qt的`signals`是宏，因此对象变量命名为`stopSignals`，不能用单独的`signals`标识符。QApplication先析构，StopSignals最后join接收线程并恢复旧掩码。子CLI也使用同一类；即使继承了阻塞集，仍由其普通sigwait线程处理，停止语义不会退回默认异步终止。

`QFileInfo(reportRoot).canonicalFilePath()`与隔离reports前缀校验限制产物位置；独占创建失败就拒绝启动。6个模型变量从已有路径脚本导出，GUI没有拷贝模型或编辑SDK配置。`BUILD_QT_GUI`默认OFF，只有明确启用才find Qt5；SDK关闭的portable构建不依赖Qt或Linux信号头。

## 故障测试和长测工具

扩展现有Fake异步测试，在worker空闲的同步点才改变测试注入变量。等待空闲所使用的互斥锁/条件变量建立先行关系，不能在合成运行时改普通int。推理标准/未知异常、TTS返回false/抛异常/无效PCM、ALSA返回false分别检查失败计数和错误文本；随后同一Worker执行成功项，验证错误不是被吞成成功，也没有让线程入口异常终止。

QtTest使用没有SDK和设备的独立Fake进程。它验证点击开始、识别/答案显示、100ms心跳、点击停止、新子进程重启、活跃窗口关闭、不可执行/exec失败、恢复和拒绝覆盖日志。测试父进程同样先构造StopSignals再建立QApplication，模拟生产的阻塞掩码继承。Fake的signal handler只写sig_atomic_t；先安装handler再解除继承的阻塞信号，避免测试自身的早到信号竞态。

实机守护每秒读取/proc与sysfs，明确记录温度、CPU频率、cooling state、线程和RSS，保留实际模型及TTS队列事件。90℃是本项目保守测试线而非芯片安全额定值。cooling state为正只能说明对应Linux cooling设备活动；频率下降还可能来自ondemand和当前负载，不能自动归因于热降频。

分析器复用5.4的steady事件定义与nearest-rank统计。TTS时长由`tts_full_audio_ready`的实际样本数除以应用采样率计算；采样率从ALSA日志的buffer_frames/buffer_ms还原，并核对本模型24kHz条件。它不是耳机声学时长。RSS趋势排除前5分钟，并限制到进程第30分钟以前，避免模型加载或退出释放伪造斜率；同时比较5～10与25～30分钟的中位数，不能只凭进程没OOM就证明无泄漏。

完整命令、失败修复、实机数据与未验证条件以最终报告为准。文档辅助工具使用打包python-docx/Poppler，原生Word导出仅操作本工程DOCX；没有捏造GUI截图、热曲线或运行日志。

## 真实stdout交错与结构化文本修复

2线程长测的原始日志中，Qwen回答的流式片段被ALSA write日志插入；完整result.text仍正确，模型未失败。原来的print_mutex只管理业务打印，无法约束ALSA和SDK的独立stdout。GUI不能把混杂行当作答案协议，原始证据继续保留。

ImageProfile::text复用既有mutex与steady时钟，写kind=request的完整文本事件。逐字节保留UTF-8，双引号、反斜杠、换行、回车、tab和0x20以下控制字节做JSON转义；循环不把用户内容当事件名或格式串。写入和flush都在同一把锁内，错误显式报告；没有另一套计时器或无界请求表。RequestTrace::text只携带原有不可变ID。

on_text在移动supplied_trace前记录是否来自ASR，分别写asr_text或input_text；不会把直接文本回放假装语音识别。LLM/VLM完成回调把成功的完整result.text写answer_text，失败和取消分别写request_error/request_terminal。原Prompt、推理参数、流式CLI、TTS提交与生命周期不变。

GUI从JSONL读取识别、路由和完整答案，延迟由同一请求已有steady事件相减，缺少点显示未测量。自动停止依据request_complete而非stdout中的success字样，防止交错输出漏计；真实耳机仍必须用户确认。测试用两线程并发50条文本事件，加引号、中文、换行及控制字节样本，实际56行逐条JSON解析和文本回环检查通过；ARM结果必须另列。

Qt5.15进程创建路径的源码参考为[官方Qt仓库](https://raw.githubusercontent.com/qt/qtbase/5.15/src/corelib/io/qprocess_unix.cpp)。它不能替代当前Debian Qt5.15.8的实际信号测试；最终会核对GUI和CLI的SigBlk及真实退出结果。


## 本轮实际验证补充

最终final_v2已在ARM64完成全量构建和8项CTest，真实Qt xcb页面及两轮新进程重启均正常。用户在gui_microphone_final_v2确认两个回答实际通过HyperX听到、视觉描述大致相符、窗口显示识别/路由/回答。GUI外层SIGTERM触发普通事件循环关闭，后台通过既有SIGINT协作式清理；不把两种信号混称同时由同一进程接收。

当前内核不提供/proc/PID/task/PID/children，首轮监控遗漏后台RSS；修复工具按PPid找直接子进程，并核实exe与start token。原版工具保留，首轮缺失数据不补造。最终长测分别采样Qt和AI进程，不把GUI约90MiB等同全系统内存。

全局Git docx textconv可能把二进制文档转换成可读文本差异，git apply返回0仍不能证明字节相同。本节确实捕获了DOCX字节检查失败，随后显式禁用textconv和外部diff，再以SHA验证补丁实际还原；失败结果保留在patch_roundtrip_before_binaryfix.json。


ASR统计特别说明：ASRService::recognize的latency_ms结束点在返回前Result/Stream unique_ptr析构之前，打印RTF沿用这个内部区间；外层ASRWorker的asr_begin/asr_end包含recognize返回所需清理。asr_decode_begin/asr_decode_end只包含DecodeOfflineStream。三种口径分别保留，不把差额认定为纯音素化、模型计算或错误计时。

InferenceWorker实际是include/ai/llm_worker.h末尾的`using InferenceWorker = LLMWorker`。它没有独立inference_worker.cpp，也没有第二个队列实现。本节检查器明确要求被比较路径在前后两个版本都存在，避免None==None造成“未修改”假阳性；早期检查记录保留并注明这个漏洞。
