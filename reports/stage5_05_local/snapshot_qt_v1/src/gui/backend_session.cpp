#include "gui/backend_session.h"
#include <QFileInfo>
#include <cerrno>
#include <cstring>
#include <signal.h>

BackendSession::BackendSession(QObject* parent):QObject(parent) {
    process_.setProcessChannelMode(QProcess::MergedChannels);
    connect(&process_,&QProcess::readyReadStandardOutput,this,&BackendSession::consume);
    connect(&process_,&QProcess::started,this,[this] {
        emit running();
        if(stopping_)requestStop(); // Stop pressed during asynchronous startup.
    });
    connect(&process_,&QProcess::errorOccurred,this,[this](QProcess::ProcessError error) {
        emit problem(process_.errorString());
        if(error==QProcess::FailedToStart) {
            stopDeadline_.stop();terminal_.close();emit finished(-1,false);
        }
    });
    connect(&process_,qOverload<int,QProcess::ExitStatus>(&QProcess::finished),this,
            [this](int code,QProcess::ExitStatus status) {
        consume();
        if(!partial_.isEmpty()){emit lineReceived(QString::fromUtf8(partial_));partial_.clear();}
        stopDeadline_.stop();terminal_.close();
        emit finished(code,status==QProcess::NormalExit && code==0 && shutdownSeen_);
    });
    stopDeadline_.setSingleShot(true);
    connect(&stopDeadline_,&QTimer::timeout,this,[this] {
        emit problem(QStringLiteral("停止等待超过90秒，退出未通过；仍保留窗口和进程，不以强杀冒充安全退出"));
    });
}
bool BackendSession::start(const QString& executable,const QStringList& arguments,
                           const QProcessEnvironment& environment,const QString& terminalPath) {
    if(active()){emit problem(QStringLiteral("已有交互进程，拒绝重复启动"));return false;}
    if(!QFileInfo(executable).isExecutable()){emit problem(QStringLiteral("入口程序不可执行"));return false;}
    terminal_.setFileName(terminalPath);
    if(!terminal_.open(QIODevice::WriteOnly|QIODevice::NewOnly)) {
        emit problem(QStringLiteral("拒绝覆盖日志或无法创建日志"));return false;
    }
    partial_.clear();stopping_=shutdownSeen_=false;
    process_.setProcessEnvironment(environment);
    // argv is structured; paths/text are never interpolated into a shell.
    process_.start(executable,arguments,QIODevice::ReadOnly);
    return true;
}
void BackendSession::requestStop() {
    if(!active())return;
    stopping_=true;
    if(process_.state()!=QProcess::Running)return;
    const auto child=process_.processId();
    if(child<=0)return;
    if(::kill(static_cast<pid_t>(child),SIGINT)!=0 && errno!=ESRCH)
        emit problem(QStringLiteral("发送SIGINT失败: ")+QString::fromLocal8Bit(std::strerror(errno)));
    if(!stopDeadline_.isActive())stopDeadline_.start(90000);
}
void BackendSession::consume() {
    const auto data=process_.readAllStandardOutput();
    if(terminal_.isOpen() && !data.isEmpty()) {
        if(terminal_.write(data)!=data.size())emit problem(QStringLiteral("终端日志写入失败"));
        terminal_.flush();
    }
    partial_+=data;
    for(int end;(end=partial_.indexOf('\n'))>=0;) {
        const auto bytes=partial_.left(end);partial_.remove(0,end+1);
        const auto line=QString::fromUtf8(bytes);
        shutdownSeen_|=line.contains(QStringLiteral("[Shutdown] complete"));
        emit lineReceived(line);
    }
    if(partial_.size()>65536) {
        partial_.clear();emit problem(QStringLiteral("异常超长未换行输出已丢弃，原始内容仍在终端日志"));
    }
}
