#include "gui/session_window.h"
#include <QCloseEvent>
#include <QDateTime>
#include <QDir>
#include <QGridLayout>
#include <QJsonDocument>
#include <QJsonObject>
#include <QRegularExpression>
#include <QTextStream>
#include <QThread>
#include <QApplication>
#include <QUuid>
#include <QVariant>
#include <utility>

SessionWindow::SessionWindow(GuiLaunch settings,QWidget* parent)
    :QWidget(parent),settings_(std::move(settings)) {
    setWindowTitle(QStringLiteral("RK3576 端侧多模态交互系统"));resize(980,700);
    auto* grid=new QGridLayout(this);
    auto* title=new QLabel(QStringLiteral("RK3576 多模态语音交互"));
    title->setStyleSheet("font-size:22px;font-weight:bold");grid->addWidget(title,0,0,1,5);
    int column=0;
    for(const auto& name:{"Camera","ASR","LLM","VLM","TTS"}) {
        auto* label=new QLabel(QString::fromLatin1(name)+QStringLiteral("：未启动"));
        label->setObjectName(QString::fromLatin1(name));modules_[name]=label;grid->addWidget(label,1,column++);
    }
    start_=new QPushButton(QStringLiteral("开始语音交互"));start_->setObjectName("start");
    stop_=new QPushButton(QStringLiteral("安全停止"));stop_->setObjectName("stop");stop_->setEnabled(false);
    threads_=new QComboBox;threads_->addItems({"TTS 2线程","TTS 4线程"});
    threads_->setCurrentIndex(settings_.threadArgument>=0 && settings_.arguments.value(settings_.threadArgument)=="2"?0:1);
    stopMode_=new QComboBox;stopMode_->addItems({QStringLiteral("排空已接收任务"),QStringLiteral("取消等待任务")});
    stopMode_->setCurrentIndex(settings_.environment.value("STAGE5_STOP_MODE")=="cancel_pending"?1:0);
    grid->addWidget(start_,2,0);grid->addWidget(stop_,2,1);grid->addWidget(threads_,2,2);grid->addWidget(stopMode_,2,3,1,2);
    status_=new QLabel(QStringLiteral("就绪，点击开始；首次启动需要加载模型"));
    asr_=new QLabel(QStringLiteral("识别文本：等待"));asr_->setObjectName("transcript");
    route_=new QLabel(QStringLiteral("路由：等待"));route_->setObjectName("route");
    status_->setWordWrap(true);asr_->setWordWrap(true);route_->setWordWrap(true);
    metrics_=new QLabel(QStringLiteral("延迟：尚无实测数据"));metrics_->setWordWrap(true);
    queue_=new QLabel(QStringLiteral("推理等待：0  TTS等待：0（异步事件快照）"));
    error_=new QLabel;error_->setWordWrap(true);error_->setStyleSheet("color:#a02020");
    grid->addWidget(status_,3,0,1,5);grid->addWidget(asr_,4,0,1,5);grid->addWidget(route_,5,0,1,5);
    grid->addWidget(metrics_,6,0,1,5);grid->addWidget(queue_,7,0,1,5);grid->addWidget(error_,8,0,1,5);
    answers_=new QPlainTextEdit;answers_->setReadOnly(true);answers_->setObjectName("answers");answers_->setMaximumBlockCount(100);
    logs_=new QPlainTextEdit;logs_->setReadOnly(true);logs_->setMaximumBlockCount(400);
    grid->addWidget(answers_,9,0,1,5);grid->addWidget(logs_,10,0,1,5);grid->setRowStretch(9,2);grid->setRowStretch(10,1);
    connect(start_,&QPushButton::clicked,this,&SessionWindow::startSession);
    connect(stop_,&QPushButton::clicked,this,&SessionWindow::stopSession);
    connect(&backend_,&BackendSession::lineReceived,this,&SessionWindow::line);
    connect(&backend_,&BackendSession::problem,this,[this](const QString& message){error_->setText(message);QTextStream(stdout)<<"[GUI error] "<<message<<Qt::endl;});
    connect(&backend_,&BackendSession::running,this,[this]{status_->setText(QStringLiteral("后台进程已启动，正在加载"));});
    connect(&backend_,&BackendSession::finished,this,[this](int code,bool orderly){
        pollProfile();profile_.close();stopping_=false;lastOrderly_=orderly;++completedCycles_;
        start_->setEnabled(true);stop_->setEnabled(false);threads_->setEnabled(true);stopMode_->setEnabled(true);
        status_->setText(QStringLiteral("进程退出码 %1；%2").arg(code).arg(orderly?QStringLiteral("清理完成"):QStringLiteral("未通过安全退出检查")));
        if(!orderly)error_->setText(QStringLiteral("启动或运行失败，请查看保留的原始日志"));
        for(auto* label:modules_)label->setText(label->objectName()+QStringLiteral("：进程已退出"));
        QTextStream(stdout)<<"[GUI finished] code="<<code<<" orderly="<<orderly<<" cycles="<<completedCycles_<<" heartbeat="<<heartbeats_<<Qt::endl;
        QFile result(runFolder_+"/result.json");
        if(result.open(QIODevice::WriteOnly|QIODevice::NewOnly)) {
            QJsonObject object{{"returncode",code},{"orderly",orderly},{"heartbeat",heartbeats_},{"answers_completed",completedAnswers_},{"cycles_completed",completedCycles_}};
            result.write(QJsonDocument(object).toJson());
        } else error_->setText(QStringLiteral("结果写入失败"));
        screenshot("finished.png");
        if(!closing_ && settings_.automatic && completedCycles_<settings_.cycles && orderly)QTimer::singleShot(200,this,&SessionWindow::startSession);
        else if(closing_ || settings_.automatic)QTimer::singleShot(0,this,&QWidget::close);
    });
    poll_.setInterval(100);
    connect(&poll_,&QTimer::timeout,this,[this]{++heartbeats_;pollProfile();});poll_.start();
    if(settings_.automatic)QTimer::singleShot(100,start_,&QPushButton::click);
}
void SessionWindow::startSession() {
    if(backend_.active() || closing_)return;
    runFolder_=QDir(settings_.reportRoot).filePath("run_"+QDateTime::currentDateTimeUtc().toString("yyyyMMdd_HHmmss_zzz")+"_"+QUuid::createUuid().toString(QUuid::Id128));
    if(!QDir().mkdir(runFolder_)){error_->setText(QStringLiteral("无法创建独占运行目录"));return;}
    auto env=settings_.environment;
    env.insert("STAGE5_PROFILE",runFolder_+"/profile.jsonl");
    env.insert("STAGE5_STOP_MODE",stopMode_->currentIndex()==0?"drain":"cancel_pending");
    auto args=settings_.arguments;
    if(settings_.threadArgument>=0 && settings_.threadArgument<args.size())args[settings_.threadArgument]=threads_->currentIndex()==0?"2":"4";
    completedAnswers_=0;lastOrderly_=false;stopping_=false;tasks_.clear();profilePartial_.clear();profile_.close();
    profile_.setFileName(runFolder_+"/profile.jsonl");
    error_->clear();answers_->clear();logs_->clear();
    asr_->setText(QStringLiteral("识别文本：等待新会话"));route_->setText(QStringLiteral("路由：等待新会话"));
    metrics_->setText(QStringLiteral("延迟：等待新会话实测"));
    queue_->setText(QStringLiteral("推理等待：0  TTS等待：0（异步事件快照）"));
    if(backend_.start(settings_.program,args,env,runFolder_+"/terminal.log")) {
        start_->setEnabled(false);stop_->setEnabled(true);threads_->setEnabled(false);stopMode_->setEnabled(false);
        status_->setText(QStringLiteral("异步启动中"));
        QTextStream(stdout)<<"[GUI run] "<<runFolder_<<Qt::endl;
    } else if(settings_.automatic)QTimer::singleShot(0,this,&QWidget::close);
}
void SessionWindow::stopSession() {
    if(!backend_.active() || stopping_)return;
    stopping_=true;stopClock_.start();backend_.requestStop();stop_->setEnabled(false);
    status_->setText(QStringLiteral("正在协作停止，等待后台线程和资源释放"));
    screenshot("stopping.png");
}
void SessionWindow::closeEvent(QCloseEvent* event) {
    if(backend_.active()){closing_=true;event->ignore();stopSession();return;}
    event->accept();
}
void SessionWindow::screenshot(const QString& leaf) {
    if(!runFolder_.isEmpty() && !grab().save(runFolder_+'/'+leaf))error_->setText(QStringLiteral("界面截图保存失败"));
}
void SessionWindow::line(const QString& text) {
    Q_ASSERT(QThread::currentThread()==qApp->thread());
    logs_->appendPlainText(text);QTextStream(stdout)<<text<<Qt::endl;
    const auto module=[this](const char* key,const QString& state){modules_[key]->setText(QString::fromLatin1(key)+"："+state);};
    if(text.contains("Loading RKLLM"))module("LLM",QStringLiteral("加载中"));
    if(text.contains("Loading SenseVoice")){module("LLM",QStringLiteral("已加载"));module("ASR",QStringLiteral("加载中"));}
    if(text.contains("Loading Kokoro")){module("ASR",QStringLiteral("已加载"));module("TTS",QStringLiteral("加载中"));}
    if(text.contains("[ALSA config]"))module("TTS",QStringLiteral("已加载"));
    if(text.contains("VLM and Camera ready")){module("Camera",QStringLiteral("采集中"));module("VLM",QStringLiteral("已加载"));}
    if(text.contains("[Listen]") || text.contains("[Replay ready]")){status_->setText(text);screenshot("listening.png");}
    if(text.contains("success=false") || text.contains("[Fatal]") || (text.contains("[Init]") && text.contains("failed")) || text.contains("rejected #") || text.contains("[TTS expired"))error_->setText(text);
}
void SessionWindow::pollProfile() {
    if(!backend_.active() && !profile_.isOpen())return; // Do not replay old events while idle.
    if(!profile_.isOpen() && !profile_.fileName().isEmpty() && QFile::exists(profile_.fileName()))profile_.open(QIODevice::ReadOnly);
    if(!profile_.isOpen())return;
    profilePartial_+=profile_.read(65536);
    for(int end;(end=profilePartial_.indexOf('\n'))>=0;) {
        const auto bytes=profilePartial_.left(end);profilePartial_.remove(0,end+1);
        const auto object=QJsonDocument::fromJson(bytes).object();
        if(object.value("kind")!="request")continue;
        const auto id=object.value("request_id").toVariant().toULongLong();
        const auto name=object.value("event").toString();
        const auto at=object.value("at_ns").toVariant().toLongLong();
        const QStringList timed={"asr_enqueued","asr_begin","asr_end","inference_begin","inference_end","tts_enqueued","tts_dequeued","tts_generate_begin","tts_generate_end","alsa_first_submit_begin","request_complete"};
        if(timed.contains(name))tasks_[id]["at:"+name].timestamp=at;
        if(name=="asr_text" || name=="input_text")asr_->setText((name=="asr_text"?QStringLiteral("识别 #%1："):QStringLiteral("文本输入 #%1：")).arg(id)+object.value("text").toString());
        if(name=="router_end")route_->setText(QStringLiteral("路由 #%1：%2").arg(id).arg(object.value("value").toInt()==1?"VISION":"TEXT"));
        if(name=="answer_text")answers_->appendPlainText(QStringLiteral("回答 #%1：%2").arg(id).arg(object.value("text").toString()));
        if(name=="request_error")error_->setText(object.value("text").toString());
        if(name=="request_terminal")status_->setText(object.value("text").toString());
        for(const auto& stage:{QString("inference"),QString("tts")}) {
            if(name==stage+"_enqueued" || name==stage+"_dequeued") {
                auto& record=tasks_[id][stage];
                if(at>=record.timestamp){record.timestamp=at;record.pending=name.endsWith("_enqueued");}
            }
        }
        if(name.endsWith("_begin"))status_->setText(QStringLiteral("执行 #%1：%2").arg(id).arg(name));
        if(timed.contains(name)) {
            const auto& task=tasks_[id];
            const auto duration=[&](const char* begin,const char* end) {
                const auto a=task.value("at:"+QString::fromLatin1(begin)).timestamp;
                const auto b=task.value("at:"+QString::fromLatin1(end)).timestamp;
                return a>0 && b>=a?QString::number((b-a)/1e6,'f',1)+" ms":QStringLiteral("未测量");
            };
            metrics_->setText(QStringLiteral("请求#%1  ASR %2  推理 %3  TTS %4  TTS排队 %5  ASR入队→首次提交 %6")
                .arg(id).arg(duration("asr_begin","asr_end"),duration("inference_begin","inference_end"),
                    duration("tts_generate_begin","tts_generate_end"),duration("tts_enqueued","tts_dequeued"),
                    duration("asr_enqueued","alsa_first_submit_begin")));
        }
        if(name=="request_complete") {
            ++completedAnswers_;screenshot("answer_"+QString::number(completedAnswers_)+".png");
            if(settings_.stopAfterAnswers>0 && completedAnswers_>=settings_.stopAfterAnswers)stopSession();
        }
        while(tasks_.size()>64)tasks_.erase(tasks_.begin());
    }
    if(profilePartial_.size()>65536){profilePartial_.clear();error_->setText(QStringLiteral("异常超长诊断事件，已记录错误"));}
    int inference=0,tts=0;
    for(const auto& task:tasks_){inference+=task.value("inference").pending;tts+=task.value("tts").pending;}
    queue_->setText(QStringLiteral("推理等待：%1  TTS等待：%2（异步事件快照）").arg(inference).arg(tts));
}
