#pragma once
#include <QObject>
#include <QProcess>
#include <QProcessEnvironment>
#include <QFile>
#include <QTimer>

// Owns one CLI child. No SDK or device calls execute on the Qt thread.
// Owner must defer destruction until finished; stop never calls waitForFinished/kill.
class BackendSession final : public QObject {
    Q_OBJECT
public:
    explicit BackendSession(QObject* parent=nullptr);
    bool start(const QString& executable,const QStringList& arguments,
               const QProcessEnvironment& environment,const QString& terminalPath);
    void requestStop();
    bool active() const { return process_.state()!=QProcess::NotRunning; }
    qint64 pid() const { return process_.processId(); }
signals:
    void lineReceived(QString line);
    void problem(QString message);
    void running();
    void finished(int code,bool orderly);
private:
    void consume();
    QProcess process_;
    QFile terminal_;
    QByteArray partial_;
    QTimer stopDeadline_;
    bool stopping_=false,shutdownSeen_=false;
};
