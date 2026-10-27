# 5.5 新增关键源码逐行学习索引

本附录按最终真实文件行号定位，每条保留原句并给出语法提示；提示不是C++解析器或独立的完整业务语义证明，具体变量、条件和所有权需与前述人工状态机讲解及完整源码连读。完整文件见source_appendix，设计流程见statement_notes。生成器不会把说明插入生产源码。

## src/gui/backend_session.cpp

职责：Qt主线程中的QProcess适配，不加载模型；QObject context限制回调寿命，停止是向确认子PID发SIGINT。SHA256：`b724f970b6636aef8e9c582fa6dea7691c0035af35bacb6f4a7b72a368857225`。

行1 `#include "gui/backend_session.h"`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行2 `#include <QFileInfo>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <cerrno>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <cstring>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <signal.h>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <sys/types.h>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行7 `#include <cstdio>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行9 `BackendSession::BackendSession(QObject* parent):QObject(parent) {`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行10 `process_.setProcessChannelMode(QProcess::MergedChannels);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行11 `connect(&process_,&QProcess::readyReadStandardOutput,this,&BackendSession::consume);`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行12 `connect(&process_,&QProcess::started,this,[this] {`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行13 `emit running();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行14 `if(stopping_)requestStop(); // Stop pressed during asynchronous startup.`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行15 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行16 `connect(&process_,&QProcess::errorOccurred,this,[this](QProcess::ProcessError error) {`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行17 `emit problem(process_.errorString());`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行18 `if(error==QProcess::FailedToStart) {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行19 `stopDeadline_.stop();terminal_.close();emit finished(-1,false);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行20 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行21 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行22 `connect(&process_,qOverload<int,QProcess::ExitStatus>(&QProcess::finished),this,`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行23 `[this](int code,QProcess::ExitStatus status) {`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行24 `consume();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行25 `if(!partial_.isEmpty()){emit lineReceived(QString::fromUtf8(partial_));partial_.clear();}`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行26 `stopDeadline_.stop();terminal_.close();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行27 `emit finished(code,status==QProcess::NormalExit && code==0 && shutdownSeen_);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行28 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行29 `stopDeadline_.setSingleShot(true);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行30 `connect(&stopDeadline_,&QTimer::timeout,this,[this] {`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行31 `emit problem(QStringLiteral("停止等待超过90秒，退出未通过；仍保留窗口和进程，不以强杀冒充安全退出"));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行32 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行33 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行34 `BackendSession::~BackendSession() {`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行35 `stopDeadline_.stop();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行36 `QObject::disconnect(&process_,nullptr,this,nullptr);`：断开指定QObject信号连接；本调用不注册新连接，防止成员析构阶段回调访问已销毁缓冲。

行37 `// Normal owners wait for finished. If an unrelated emergency destroys an`：该注释说明相邻代码的工程约束，本行不执行。

行38 `// active owner, prevent callbacks into already-destroyed member buffers.`：该注释说明相邻代码的工程约束，本行不执行。

行39 `// QProcess fallback cleanup in that failure path is never counted orderly.`：该注释说明相邻代码的工程约束，本行不执行。

行40 `if(active())std::fprintf(stderr,"[GUI FAILURE] active backend destruction; emergency cleanup is NOT graceful\n");`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行41 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行42 `bool BackendSession::start(const QString& executable,const QStringList& arguments,`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行43 `const QProcessEnvironment& environment,const QString& terminalPath) {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行44 `if(active()){emit problem(QStringLiteral("已有交互进程，拒绝重复启动"));return false;}`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行45 `if(!QFileInfo(executable).isExecutable()){emit problem(QStringLiteral("入口程序不可执行"));return false;}`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行46 `terminal_.setFileName(terminalPath);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行47 `if(!terminal_.open(QIODevice::WriteOnly|QIODevice::NewOnly)) {`：要求文件不存在才创建，防止重复启动覆盖已有终端或验收结果。

行48 `emit problem(QStringLiteral("拒绝覆盖日志或无法创建日志"));return false;`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行49 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行50 `partial_.clear();stopping_=shutdownSeen_=false;`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行51 `process_.setProcessEnvironment(environment);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行52 `// argv is structured; paths/text are never interpolated into a shell.`：该注释说明相邻代码的工程约束，本行不执行。

行53 `process_.start(executable,arguments,QIODevice::ReadOnly);`：用独立程序路径与QStringList异步启动子进程，不拼接shell，不阻塞等待模型加载。

行54 `return true;`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行55 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行56 `void BackendSession::requestStop() {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行57 `if(!active())return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行58 `stopping_=true;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行59 `if(process_.state()!=QProcess::Running)return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行60 `const auto child=process_.processId();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行61 `if(child<=0)return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行62 `if(::kill(static_cast<pid_t>(child),SIGINT)!=0 && errno!=ESRCH)`：请求本对象持有且已确认的后台进程协作退出；调用返回不等于设备已经释放。

行63 `emit problem(QStringLiteral("发送SIGINT失败: ")+QString::fromLocal8Bit(std::strerror(errno)));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行64 `if(!stopDeadline_.isActive())stopDeadline_.start(90000);`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行65 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行66 `void BackendSession::consume() {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行67 `const auto data=process_.readAllStandardOutput();`：读取当前可用数据，保留未完整行片段；这不是对AI设备的阻塞推理调用。

行68 `if(terminal_.isOpen() && !data.isEmpty()) {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行69 `if(terminal_.write(data)!=data.size())emit problem(QStringLiteral("终端日志写入失败"));`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行70 `terminal_.flush();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行71 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行72 `partial_+=data;`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行73 `for(int end;(end=partial_.indexOf('\n'))>=0;) {`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行74 `const auto bytes=partial_.left(end);partial_.remove(0,end+1);`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行75 `const auto line=QString::fromUtf8(bytes);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行76 `shutdownSeen_|=line.contains(QStringLiteral("[Shutdown] complete"));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行77 `emit lineReceived(line);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行78 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行79 `if(partial_.size()>65536) {`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行80 `partial_.clear();emit problem(QStringLiteral("异常超长未换行输出已丢弃，原始内容仍在终端日志"));`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行81 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行82 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

## src/gui/session_window.cpp

职责：Qt窗口只更新控件和读取有界结构化事件；关闭活动窗口先等待后台清理，重新开始创建新进程。SHA256：`30021fd3b2d9c4641a80fa740447bb30f0ae5b023f73a23d03de69f98766bd65`。

行1 `#include "gui/session_window.h"`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行2 `#include <QCloseEvent>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <QDateTime>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <QDir>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <QGridLayout>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <QJsonDocument>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行7 `#include <QJsonObject>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行8 `#include <QRegularExpression>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行9 `#include <QTextStream>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行10 `#include <QThread>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行11 `#include <QApplication>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行12 `#include <QUuid>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行13 `#include <QVariant>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行14 `#include <utility>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行16 `SessionWindow::SessionWindow(GuiLaunch settings,QWidget* parent)`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行17 `:QWidget(parent),settings_(std::move(settings)) {`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行18 `setWindowTitle(QStringLiteral("RK3576 端侧多模态交互系统"));resize(980,700);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行19 `auto* grid=new QGridLayout(this);`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行20 `auto* title=new QLabel(QStringLiteral("RK3576 多模态语音交互"));`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行21 `title->setStyleSheet("font-size:22px;font-weight:bold");grid->addWidget(title,0,0,1,5);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行22 `int column=0;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行23 `for(const auto& name:{"Camera","ASR","LLM","VLM","TTS"}) {`：遍历当前已有事件/控件或有限缓存；耗时模型循环仍在后台进程。

行24 `auto* label=new QLabel(QString::fromLatin1(name)+QStringLiteral("：未启动"));`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行25 `label->setObjectName(QString::fromLatin1(name));modules_[name]=label;grid->addWidget(label,1,column++);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行26 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行27 `start_=new QPushButton(QStringLiteral("开始语音交互"));start_->setObjectName("start");`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行28 `stop_=new QPushButton(QStringLiteral("安全停止"));stop_->setObjectName("stop");stop_->setEnabled(false);`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行29 `threads_=new QComboBox;threads_->addItems({"TTS 2线程","TTS 4线程"});`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行30 `threads_->setCurrentIndex(settings_.threadArgument>=0 && settings_.arguments.value(settings_.threadArgument)=="2"?0:1);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行31 `stopMode_=new QComboBox;stopMode_->addItems({QStringLiteral("排空已接收任务"),QStringLiteral("取消等待任务")});`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行32 `stopMode_->setCurrentIndex(settings_.environment.value("STAGE5_STOP_MODE")=="cancel_pending"?1:0);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行33 `grid->addWidget(start_,2,0);grid->addWidget(stop_,2,1);grid->addWidget(threads_,2,2);grid->addWidget(stopMode_,2,3,1,2);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行34 `status_=new QLabel(QStringLiteral("就绪，点击开始；首次启动需要加载模型"));`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行35 `asr_=new QLabel(QStringLiteral("识别文本：等待"));asr_->setObjectName("transcript");`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行36 `route_=new QLabel(QStringLiteral("路由：等待"));route_->setObjectName("route");`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行37 `status_->setWordWrap(true);asr_->setWordWrap(true);route_->setWordWrap(true);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行38 `metrics_=new QLabel(QStringLiteral("延迟：尚无实测数据"));metrics_->setWordWrap(true);`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行39 `queue_=new QLabel(QStringLiteral("推理等待：0  TTS等待：0（异步事件快照）"));`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行40 `error_=new QLabel;error_->setWordWrap(true);error_->setStyleSheet("color:#a02020");`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行41 `grid->addWidget(status_,3,0,1,5);grid->addWidget(asr_,4,0,1,5);grid->addWidget(route_,5,0,1,5);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行42 `grid->addWidget(metrics_,6,0,1,5);grid->addWidget(queue_,7,0,1,5);grid->addWidget(error_,8,0,1,5);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行43 `answers_=new QPlainTextEdit;answers_->setReadOnly(true);answers_->setObjectName("answers");answers_->setMaximumBlockCount(100);`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行44 `answers_->setPlaceholderText(QStringLiteral("模型回答，显示最近100行，完整内容保留在本轮日志"));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行45 `logs_=new QPlainTextEdit;logs_->setReadOnly(true);logs_->setMaximumBlockCount(400);`：构造QObject/控件或Qt内部值对象；布局接管控件parent，不能让异步回调借用裸临时地址。

行46 `grid->addWidget(answers_,9,0,1,5);grid->addWidget(logs_,10,0,1,5);grid->setRowStretch(9,2);grid->setRowStretch(10,1);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行47 `connect(start_,&QPushButton::clicked,this,&SessionWindow::startSession);`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行48 `connect(stop_,&QPushButton::clicked,this,&SessionWindow::stopSession);`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行49 `connect(&backend_,&BackendSession::lineReceived,this,&SessionWindow::line);`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行50 `connect(&backend_,&BackendSession::problem,this,[this](const QString& message){error_->setText(message);QTextStream(stdout)<<"[GUI error] "<<message<<Qt::endl;});`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行51 `connect(&backend_,&BackendSession::running,this,[this]{status_->setText(QStringLiteral("后台进程已启动，正在加载"));});`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行52 `connect(&backend_,&BackendSession::finished,this,[this](int code,bool orderly){`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行53 `pollProfile();profile_.close();stopping_=false;lastOrderly_=orderly;++completedCycles_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行54 `start_->setEnabled(true);stop_->setEnabled(false);threads_->setEnabled(true);stopMode_->setEnabled(true);`：根据活动状态启用或禁用控制项，防止运行中重复开始或改变当前会话参数。

行55 `status_->setText(QStringLiteral("进程退出码 %1；%2").arg(code).arg(orderly?QStringLiteral("清理完成"):QStringLiteral("未通过安全退出检查")));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行56 `if(!orderly)error_->setText(QStringLiteral("启动或运行失败，请查看保留的原始日志"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行57 `for(auto* label:modules_)label->setText(label->objectName()+QStringLiteral("：进程已退出"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行58 `QTextStream(stdout)<<"[GUI finished] code="<<code<<" orderly="<<orderly<<" cycles="<<completedCycles_<<" heartbeat="<<heartbeats_<<Qt::endl;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行59 `QFile result(runFolder_+"/result.json");`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行60 `if(result.open(QIODevice::WriteOnly|QIODevice::NewOnly)) {`：要求文件不存在才创建，防止重复启动覆盖已有终端或验收结果。

行61 `QJsonObject object{{"returncode",code},{"orderly",orderly},{"heartbeat",heartbeats_},{"answers_completed",completedAnswers_},{"cycles_completed",completedCycles_}};`：按本行字段构造或解析JSON值；请求事件与会话结果具有不同schema，不从交错stdout猜业务文本。

行62 `result.write(QJsonDocument(object).toJson());`：按本行字段构造或解析JSON值；请求事件与会话结果具有不同schema，不从交错stdout猜业务文本。

行63 `} else error_->setText(QStringLiteral("结果写入失败"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行64 `screenshot("finished.png");`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行65 `if(!closing_ && settings_.automatic && completedCycles_<settings_.cycles && orderly)QTimer::singleShot(200,this,&SessionWindow::startSession);`：把动作推迟到事件循环执行，并提供QObject上下文，避免向已销毁窗口调用。

行66 `else if(closing_ || settings_.automatic)QTimer::singleShot(0,this,&QWidget::close);`：把动作推迟到事件循环执行，并提供QObject上下文，避免向已销毁窗口调用。

行67 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行68 `poll_.setInterval(100);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行69 `connect(&poll_,&QTimer::timeout,this,[this]{++heartbeats_;pollProfile();});poll_.start();`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行70 `if(settings_.automatic)QTimer::singleShot(100,start_,&QPushButton::click);`：把动作推迟到事件循环执行，并提供QObject上下文，避免向已销毁窗口调用。

行71 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行72 `void SessionWindow::startSession() {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行73 `if(backend_.active() || closing_)return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行74 `runFolder_=QDir(settings_.reportRoot).filePath("run_"+QDateTime::currentDateTimeUtc().toString("yyyyMMdd_HHmmss_zzz")+"_"+QUuid::createUuid().toString(QUuid::Id128));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行75 `if(!QDir().mkdir(runFolder_)){error_->setText(QStringLiteral("无法创建独占运行目录"));return;}`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行76 `auto env=settings_.environment;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行77 `env.insert("STAGE5_PROFILE",runFolder_+"/profile.jsonl");`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行78 `env.insert("STAGE5_STOP_MODE",stopMode_->currentIndex()==0?"drain":"cancel_pending");`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行79 `auto args=settings_.arguments;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行80 `if(settings_.threadArgument>=0 && settings_.threadArgument<args.size())args[settings_.threadArgument]=threads_->currentIndex()==0?"2":"4";`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行81 `completedAnswers_=0;lastOrderly_=false;stopping_=false;tasks_.clear();profilePartial_.clear();profile_.close();`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行82 `profile_.setFileName(runFolder_+"/profile.jsonl");`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行83 `error_->clear();answers_->clear();logs_->clear();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行84 `asr_->setText(QStringLiteral("识别文本：等待新会话"));route_->setText(QStringLiteral("路由：等待新会话"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行85 `metrics_->setText(QStringLiteral("延迟：等待新会话实测"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行86 `queue_->setText(QStringLiteral("推理等待：0  TTS等待：0（异步事件快照）"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行87 `if(backend_.start(settings_.program,args,env,runFolder_+"/terminal.log")) {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行88 `start_->setEnabled(false);stop_->setEnabled(true);threads_->setEnabled(false);stopMode_->setEnabled(false);`：根据活动状态启用或禁用控制项，防止运行中重复开始或改变当前会话参数。

行89 `status_->setText(QStringLiteral("异步启动中"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行90 `QTextStream(stdout)<<"[GUI run] "<<runFolder_<<Qt::endl;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行91 `} else if(settings_.automatic)QTimer::singleShot(0,this,&QWidget::close);`：把动作推迟到事件循环执行，并提供QObject上下文，避免向已销毁窗口调用。

行92 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行93 `void SessionWindow::stopSession() {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行94 `if(!backend_.active() || stopping_)return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行95 `stopping_=true;stopClock_.start();backend_.requestStop();stop_->setEnabled(false);`：根据活动状态启用或禁用控制项，防止运行中重复开始或改变当前会话参数。

行96 `status_->setText(QStringLiteral("正在协作停止，等待后台线程和资源释放"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行97 `screenshot("stopping.png");`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行98 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行99 `void SessionWindow::closeEvent(QCloseEvent* event) {`：活动后台未退出时阻止窗口销毁，先协作停止；空闲状态才允许接受关闭。

行100 `if(backend_.active()){closing_=true;event->ignore();stopSession();return;}`：活动后台未退出时阻止窗口销毁，先协作停止；空闲状态才允许接受关闭。

行101 `event->accept();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行102 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行103 `void SessionWindow::screenshot(const QString& leaf) {`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行104 `if(!runFolder_.isEmpty() && !grab().save(runFolder_+'/'+leaf))error_->setText(QStringLiteral("界面截图保存失败"));`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行105 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行106 `void SessionWindow::line(const QString& text) {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行107 `Q_ASSERT(QThread::currentThread()==qApp->thread());`：调试断言要求GUI线程上下文；不是跨线程锁，也不替代发布构建的生命周期设计。

行108 `logs_->appendPlainText(text);QTextStream(stdout)<<text<<Qt::endl;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行109 `const auto module=[this](const char* key,const QString& state){modules_[key]->setText(QString::fromLatin1(key)+"："+state);};`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行110 `if(text.contains("Loading RKLLM"))module("LLM",QStringLiteral("加载中"));`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行111 `if(text.contains("Loading SenseVoice")){module("LLM",QStringLiteral("已加载"));module("ASR",QStringLiteral("加载中"));}`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行112 `if(text.contains("Loading Kokoro")){module("ASR",QStringLiteral("已加载"));module("TTS",QStringLiteral("加载中"));}`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行113 `if(text.contains("[ALSA config]"))module("TTS",QStringLiteral("已加载"));`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行114 `if(text.contains("VLM and Camera ready")){module("Camera",QStringLiteral("采集中"));module("VLM",QStringLiteral("已加载"));}`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行115 `if(text.contains("[Listen]") || text.contains("[Replay ready]")){status_->setText(text);screenshot("listening.png");}`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行116 `if(text.contains("success=false") || text.contains("[Fatal]") || (text.contains("[Init]") && text.contains("failed")) || text.contains("rejected #") || text.contains("[TTS expired"))error_->setText(text);`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行117 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行118 `void SessionWindow::pollProfile() {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行119 `if(!backend_.active() && !profile_.isOpen())return; // Do not replay old events while idle.`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行120 `if(!profile_.isOpen() && !profile_.fileName().isEmpty() && QFile::exists(profile_.fileName()))profile_.open(QIODevice::ReadOnly);`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行121 `if(!profile_.isOpen())return;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行122 `profilePartial_+=profile_.read(65536);`：读取当前可用数据，保留未完整行片段；这不是对AI设备的阻塞推理调用。

行123 `for(int end;(end=profilePartial_.indexOf('\n'))>=0;) {`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行124 `const auto bytes=profilePartial_.left(end);profilePartial_.remove(0,end+1);`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行125 `const auto object=QJsonDocument::fromJson(bytes).object();`：按本行字段构造或解析JSON值；请求事件与会话结果具有不同schema，不从交错stdout猜业务文本。

行126 `if(object.value("kind")!="request")continue;`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行127 `const auto id=object.value("request_id").toVariant().toULongLong();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行128 `const auto name=object.value("event").toString();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行129 `const auto at=object.value("at_ns").toVariant().toLongLong();`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行130 `const QStringList timed={"asr_enqueued","asr_begin","asr_end","inference_begin","inference_end","tts_enqueued","tts_dequeued","tts_generate_begin","tts_generate_end","alsa_first_submit_begin","request_complete"};`：使用同Request ID的真实完成事件更新成功回答计数；自动测试只在规定完成数后停止。

行131 `if(timed.contains(name))tasks_[id]["at:"+name].timestamp=at;`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行132 `if(name=="asr_text" || name=="input_text")asr_->setText((name=="asr_text"?QStringLiteral("识别 #%1："):QStringLiteral("文本输入 #%1：")).arg(id)+object.value("text").toString());`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行133 `if(name=="router_end")route_->setText(QStringLiteral("路由 #%1：%2").arg(id).arg(object.value("value").toInt()==1?"VISION":"TEXT"));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行134 `if(name=="answer_text")answers_->appendPlainText(QStringLiteral("回答 #%1：%2").arg(id).arg(object.value("text").toString()));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行135 `if(name=="request_error")error_->setText(object.value("text").toString());`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行136 `if(name=="request_terminal")status_->setText(object.value("text").toString());`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行137 `if(name.contains("rejected") || name.contains("failed") || name.endsWith("_error"))`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行138 `error_->setText(QStringLiteral("请求#%1 阶段状态：%2，详情见本轮日志").arg(id).arg(name));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行139 `if(name.endsWith("_expired") || name.endsWith("_cancelled"))`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行140 `status_->setText(QStringLiteral("请求#%1：%2").arg(id).arg(name));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行141 `for(const auto& stage:{QString("inference"),QString("tts")}) {`：遍历当前已有事件/控件或有限缓存；耗时模型循环仍在后台进程。

行142 `if(name==stage+"_enqueued" || name==stage+"_dequeued") {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行143 `auto& record=tasks_[id][stage];`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行144 `if(at>=record.timestamp){record.timestamp=at;record.pending=name.endsWith("_enqueued");}`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行145 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行146 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行147 `if(name.endsWith("_begin"))status_->setText(QStringLiteral("执行 #%1：%2").arg(id).arg(name));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行148 `if(timed.contains(name)) {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行149 `const auto& task=tasks_[id];`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行150 `const auto duration=[&](const char* begin,const char* end) {`：用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。

行151 `const auto a=task.value("at:"+QString::fromLatin1(begin)).timestamp;`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行152 `const auto b=task.value("at:"+QString::fromLatin1(end)).timestamp;`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行153 `return a>0 && b>=a?QString::number((b-a)/1e6,'f',1)+" ms":QStringLiteral("未测量");`：用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。

行154 `};`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行155 `metrics_->setText(QStringLiteral("请求#%1  ASR %2  推理 %3  TTS %4  TTS排队 %5  ASR入队→首次提交 %6")`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行156 `.arg(id).arg(duration("asr_begin","asr_end"),duration("inference_begin","inference_end"),`：用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。

行157 `duration("tts_generate_begin","tts_generate_end"),duration("tts_enqueued","tts_dequeued"),`：用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。

行158 `duration("asr_enqueued","alsa_first_submit_begin")));`：用同一请求的时钟差换算毫秒；缺少任一端点显示未测量，不补零。

行159 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行160 `if(name=="request_complete") {`：使用同Request ID的真实完成事件更新成功回答计数；自动测试只在规定完成数后停止。

行161 `++completedAnswers_;screenshot("answer_"+QString::number(completedAnswers_)+".png");`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行162 `if(settings_.stopAfterAnswers>0 && completedAnswers_>=settings_.stopAfterAnswers)stopSession();`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行163 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行164 `while(tasks_.size()>64)tasks_.erase(tasks_.begin());`：限制GUI保留的诊断/回答历史，完整业务证据另存文件，不静默删除任务本身。

行165 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行166 `if(profilePartial_.size()>65536){profilePartial_.clear();error_->setText(QStringLiteral("异常超长诊断事件，已记录错误"));}`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行167 `int inference=0,tts=0;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行168 `for(const auto& task:tasks_){inference+=task.value("inference").pending;tts+=task.value("tts").pending;}`：遍历当前已有事件/控件或有限缓存；耗时模型循环仍在后台进程。

行169 `queue_->setText(QStringLiteral("推理等待：%1  TTS等待：%2（异步事件快照）").arg(inference).arg(tts));`：构造并显示带实际数值/状态的Qt字符串，不把显示动作当成后台任务完成证据。

行170 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

## src/gui/main.cpp

职责：在QApplication及子线程之前建立StopSignals，校验隔离路径和参数，再进入Qt事件循环。SHA256：`0ffdb49603f373c5cf4feaebd43abfe1f1773bfd20ccc3eb12f750180b0a3820`。

行1 `#include "app/stop_signals.h"`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行2 `#include "gui/session_window.h"`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <QApplication>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <QCommandLineParser>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <QDir>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <QFileInfo>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行7 `#include <QTextStream>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行8 `#include <QScreen>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行10 `int main(int argc,char** argv) try {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行11 `StopSignals stopSignals; // Must precede QApplication and every descendant thread.`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行12 `QApplication app(argc,argv);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行13 `app.setApplicationName("rk3576_multimodal_gui");`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行14 `QCommandLineParser parser;parser.addHelpOption();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行15 `parser.addOption({"capture","ALSA capture device, rediscover HyperX before launch","device"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行16 `parser.addOption({"playback","ALSA playback device","device"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行17 `parser.addOption({"report-root","Existing isolated report directory; each run creates a new child","path"});`：验证真实路径或隔离报告根边界，限制输出在授权目录；不会修改模型路径。

行18 `parser.addOption({"threads","Kokoro threads (2 or 4)","number","4"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行19 `parser.addOption({"seconds","Finite listening duration, 1..3600","number","120"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行20 `parser.addOption({"auto-start","Automated regression: click start after event loop begins"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行21 `parser.addOption({"stop-after-answers","Automated regression: stop after N successful TTS answers","number","0"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行22 `parser.addOption({"cycles","Automated regression: fresh child sessions, 1..4","number","1"});`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行23 `parser.process(app);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行24 `const auto env=QProcessEnvironment::systemEnvironment();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行25 `const auto review=env.value("STAGE5_REVIEW");`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行26 `const auto reports=QFileInfo(parser.value("report-root")).canonicalFilePath();`：验证真实路径或隔离报告根边界，限制输出在授权目录；不会修改模型路径。

行27 `if(review.isEmpty() || reports.isEmpty() || !reports.startsWith(QDir(review).canonicalPath()+"/reports/stage5_05_board/"))`：验证真实路径或隔离报告根边界，限制输出在授权目录；不会修改模型路径。

行28 `throw std::runtime_error("report-root must be an existing isolated Stage5.5 report directory");`：验证真实路径或隔离报告根边界，限制输出在授权目录；不会修改模型路径。

行29 `const auto number=[&](const char* key,int lo,int hi){bool ok=false;int n=parser.value(key).toInt(&ok);if(!ok || n<lo || n>hi)throw std::runtime_error("invalid numeric GUI argument");return n;};`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行30 `const int threads=number("threads",2,4),seconds=number("seconds",1,3600);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行31 `if(threads!=2 && threads!=4)throw std::runtime_error("threads must be 2 or 4");`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行32 `if(parser.value("capture").isEmpty() || parser.value("playback").isEmpty())throw std::runtime_error("explicit ALSA devices required");`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行33 `for(const auto* key:{"STAGE5_ASR","STAGE5_VAD","STAGE5_QWEN","STAGE5_KOKORO","STAGE5_VLM","STAGE5_VISION"})`：遍历当前已有事件/控件或有限缓存；耗时模型循环仍在后台进程。

行34 `if(env.value(key).isEmpty())throw std::runtime_error("source and export stage5_board_paths.sh first");`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行35 `GuiLaunch launch;launch.program="/usr/bin/stdbuf";launch.environment=env;launch.reportRoot=reports;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行36 `launch.arguments=QStringList{"-oL","-eL",QCoreApplication::applicationDirPath()+"/asr_llm_tts_smoke",parser.value("capture"),env.value("STAGE5_ASR"),env.value("STAGE5_VAD"),env.value("STAGE5_QWEN"),env.value("STAGE5_KOKORO"),parser.value("playback"),QString::number(seconds),QString::number(threads),"17",env.value("STAGE5_VLM"),env.value("STAGE5_VISION"),"/dev/video11"};`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行37 `launch.automatic=parser.isSet("auto-start");launch.stopAfterAnswers=number("stop-after-answers",0,32);launch.cycles=number("cycles",1,4);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行38 `SessionWindow window(std::move(launch));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行39 `if(auto* screen=QGuiApplication::primaryScreen()) {`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行40 `const auto size=screen->availableGeometry().size();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行41 `window.resize(qMin(980,size.width()-40),qMin(700,size.height()-60));`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行42 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行43 `window.show();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行44 `QTimer pollSignals;pollSignals.setInterval(100);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行45 `QObject::connect(&pollSignals,&QTimer::timeout,&window,[&] {`：注册Qt信号到槽或带context的lambda；由事件循环触发，context销毁会断开连接；不在此同步推理。

行46 `if(stopSignals.received() || stopSignals.failed())window.close();`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行47 `});pollSignals.start();`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行48 `const int code=app.exec();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行49 `return code?code:(stopSignals.failed() || !window.verified()?1:0);`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行50 `} catch(const std::exception& error) {`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行51 `QTextStream(stderr)<<"[GUI fatal] "<<error.what()<<Qt::endl;return 1;`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行52 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

## include/app/stop_signals.h

职责：沿用已验收sigwait普通线程，退出前join并恢复owner线程原信号mask。SHA256：`c8fd4e74fc35c910c195ca789aaaa627c1127c77e018d28e983a860ebb69b5bf`。

行1 `#pragma once`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行2 `#include <atomic>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <cerrno>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <stdexcept>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <thread>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <pthread.h>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行7 `#include <signal.h>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行9 `// Construct before SDKs/workers: all descendant threads inherit the blocked set.`：该注释说明相邻代码的工程约束，本行不执行。

行10 `// sigtimedwait runs in an ordinary thread; there is no asynchronous signal handler.`：该注释说明相邻代码的工程约束，本行不执行。

行11 `class StopSignals {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行12 `public:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行13 `StopSignals()`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行14 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行15 `sigemptyset(&signals_);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行16 `sigaddset(&signals_, SIGINT);`：把SIGINT或SIGTERM加入本线程将阻塞和同步等待的信号集合；不向任何进程发送信号。

行17 `sigaddset(&signals_, SIGTERM);`：把SIGINT或SIGTERM加入本线程将阻塞和同步等待的信号集合；不向任何进程发送信号。

行18 `if (pthread_sigmask(SIG_BLOCK, &signals_, &previous_) != 0)`：保存/设置调用线程信号mask，后续新线程继承；析构恢复owner线程原mask。

行19 `throw std::runtime_error("Cannot block stop signals");`：将非法输入或异常转换为明确错误状态/退出码；不是吞掉异常后继续假报成功。

行20 `try`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行21 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行22 `thread_ = std::thread([this] {`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行23 `const timespec interval{0, 100000000};`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行24 `while (!finished_.load())`：通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。

行25 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行26 `const int received = sigtimedwait(&signals_, nullptr, &interval);`：在普通信号接收线程限时等待被阻塞信号；此处不是异步signal handler。

行27 `if (received == SIGINT || received == SIGTERM)`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行28 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行29 `int empty = 0;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行30 `signal_.compare_exchange_strong(empty, received);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行31 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行32 `else if (received < 0 && errno != EAGAIN && errno != EINTR)`：按当前条件分支决定是否执行后续语句；必须结合括号作用域判断，不能仅按缩进推断。

行33 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行34 `wait_failed_.store(true);`：通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。

行35 `break;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行36 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行37 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行38 `});`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行39 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行40 `catch (...)`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行41 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行42 `pthread_sigmask(SIG_SETMASK, &previous_, nullptr);`：保存/设置调用线程信号mask，后续新线程继承；析构恢复owner线程原mask。

行43 `throw;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行44 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行45 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行46 `~StopSignals()`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行47 `{`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行48 `finished_.store(true);`：通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。

行49 `if (thread_.joinable()) thread_.join();`：等待所拥有线程真正结束，必须先发布停止条件；join前不能销毁线程借用对象。

行50 `pthread_sigmask(SIG_SETMASK, &previous_, nullptr);`：保存/设置调用线程信号mask，后续新线程继承；析构恢复owner线程原mask。

行51 `}`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行52 `StopSignals(const StopSignals&) = delete;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行53 `StopSignals& operator=(const StopSignals&) = delete;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行54 `int received() const noexcept { return signal_.load(); }`：通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。

行55 `bool failed() const noexcept { return wait_failed_.load(); }`：通过atomic读写线程间标志，避免普通bool数据竞争；对象寿命仍须由join保证。

行56 `private:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行57 `sigset_t signals_{};`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行58 `sigset_t previous_{};`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行59 `std::atomic<int> signal_{0};`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行60 `std::atomic<bool> finished_{false};`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行61 `std::atomic<bool> wait_failed_{false};`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行62 `std::thread thread_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行63 `};`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

## include/gui/backend_session.h

职责：定义QProcess所有权、停止状态及QObject信号；值成员的析构顺序必须配合显式disconnect。SHA256：`d08247679bfe26454c0d27ffa82fedb68c3910d4a711d42ea2b15e46ca2720fa`。

行1 `#pragma once`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行2 `#include <QObject>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <QProcess>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <QProcessEnvironment>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <QFile>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <QTimer>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行8 `// Owns one CLI child. No SDK or device calls execute on the Qt thread.`：该注释说明相邻代码的工程约束，本行不执行。

行9 `// Owner must defer destruction until finished; stop never calls waitForFinished/kill.`：该注释说明相邻代码的工程约束，本行不执行。

行10 `class BackendSession final : public QObject {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行11 `Q_OBJECT`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行12 `public:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行13 `explicit BackendSession(QObject* parent=nullptr);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行14 `~BackendSession() override;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行15 `bool start(const QString& executable,const QStringList& arguments,`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行16 `const QProcessEnvironment& environment,const QString& terminalPath);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行17 `void requestStop();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行18 `bool active() const { return process_.state()!=QProcess::NotRunning; }`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行19 `qint64 pid() const { return process_.processId(); }`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行20 `signals:`：Qt moc为信号生成元对象代码，signal发射不是后台模型工作线程。

行21 `void lineReceived(QString line);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行22 `void problem(QString message);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行23 `void running();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行24 `void finished(int code,bool orderly);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行25 `private:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行26 `void consume();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行27 `QProcess process_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行28 `QFile terminal_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行29 `QByteArray partial_;`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行30 `QTimer stopDeadline_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行31 `bool stopping_=false,shutdownSeen_=false;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行32 `};`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

## include/gui/session_window.h

职责：窗口拥有适配器及控件，任务诊断缓存有界，不持有AI回调内的借用Buffer。SHA256：`92ba03778b34f2c64d26b7981d998330e1408e9e74d0e00133ec0b0485feff98`。

行1 `#pragma once`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行2 `#include "gui/backend_session.h"`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行3 `#include <QWidget>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行4 `#include <QMap>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行5 `#include <QLabel>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行6 `#include <QPushButton>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行7 `#include <QComboBox>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行8 `#include <QPlainTextEdit>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行9 `#include <QElapsedTimer>`：预处理阶段引入该实际声明；不创建对象、不启动线程。

行11 `struct GuiLaunch {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行12 `QString program;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行13 `QStringList arguments;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行14 `QProcessEnvironment environment;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行15 `QString reportRoot;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行16 `int threadArgument=10; // stdbuf argv: -oL -eL CLI device ... seconds threads sid ...`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行17 `bool automatic=false;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行18 `int stopAfterAnswers=0;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行19 `int cycles=1;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行20 `};`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

行21 `class SessionWindow final:public QWidget {`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行22 `Q_OBJECT`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行23 `public:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行24 `explicit SessionWindow(GuiLaunch settings,QWidget* parent=nullptr);`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行25 `bool active() const {return backend_.active();}`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行26 `bool verified() const {return lastOrderly_;}`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行27 `int heartbeatCount() const {return heartbeats_;}`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行28 `int completedCycles() const {return completedCycles_;}`：返回结果或提前结束本次函数；局部RAII仍正常析构，后台是否已结束由状态机另行保证。

行29 `public slots:`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行30 `void startSession();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行31 `void stopSession();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行32 `protected:`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行33 `void closeEvent(QCloseEvent* event) override;`：活动后台未退出时阻止窗口销毁，先协作停止；空闲状态才允许接受关闭。

行34 `private:`：指定C++成员访问权限或Qt槽声明，影响接口可见性而不创建线程。

行35 `void line(const QString& text);`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行36 `void pollProfile();`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行37 `void screenshot(const QString& leaf);`：截取真实运行的当前QWidget并保存本次case，不合成运行画面。

行38 `GuiLaunch settings_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行39 `BackendSession backend_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行40 `QPushButton *start_,*stop_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行41 `QComboBox *threads_,*stopMode_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行42 `QLabel *status_,*asr_,*route_,*metrics_,*queue_,*error_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行43 `QPlainTextEdit *answers_,*logs_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行44 `QMap<QString,QLabel*> modules_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行45 `struct QueueEvent {qint64 timestamp=0;bool pending=false;};`：保存steady_clock纳秒或按单调时间比较，抵抗并发入队/出队日志写入顺序颠倒。

行46 `QMap<quint64,QMap<QString,QueueEvent>> tasks_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行47 `QFile profile_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行48 `QByteArray profilePartial_;`：维护跨read边界的字节片段，完整行后再解析，另有64KiB异常上限，避免半个UTF8字符被错误解码。

行49 `QString runFolder_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行50 `QTimer poll_;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行51 `QElapsedTimer stopClock_;`：执行本作用域的成员更新、函数参数续行或声明；与相邻语句共同构成上述状态机，不能脱离作用域理解生命周期。

行52 `bool closing_=false,stopping_=false,lastOrderly_=true;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行53 `int completedAnswers_=0,completedCycles_=0,heartbeats_=0;`：声明/定义当前类型、函数或有作用域的值对象；具体所有权与线程角色见本文件职责和相邻语句。

行54 `};`：结束或开始当前作用域/调用；离开拥有局部RAII对象的作用域时自动析构。

