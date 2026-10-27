#pragma once
#include "gui/backend_session.h"
#include <QWidget>
#include <QMap>
#include <QLabel>
#include <QPushButton>
#include <QComboBox>
#include <QPlainTextEdit>
#include <QElapsedTimer>

struct GuiLaunch {
    QString program;
    QStringList arguments;
    QProcessEnvironment environment;
    QString reportRoot;
    int threadArgument=10; // stdbuf argv: -oL -eL CLI device ... seconds threads sid ...
    bool automatic=false;
    int stopAfterAnswers=0;
    int cycles=1;
};
class SessionWindow final:public QWidget {
    Q_OBJECT
public:
    explicit SessionWindow(GuiLaunch settings,QWidget* parent=nullptr);
    bool active() const {return backend_.active();}
    bool verified() const {return lastOrderly_;}
    int heartbeatCount() const {return heartbeats_;}
    int completedCycles() const {return completedCycles_;}
public slots:
    void startSession();
    void stopSession();
protected:
    void closeEvent(QCloseEvent* event) override;
private:
    void line(const QString& text);
    void pollProfile();
    void screenshot(const QString& leaf);
    GuiLaunch settings_;
    BackendSession backend_;
    QPushButton *start_,*stop_;
    QComboBox *threads_,*stopMode_;
    QLabel *status_,*asr_,*route_,*metrics_,*queue_,*error_;
    QPlainTextEdit *answers_,*logs_;
    QMap<QString,QLabel*> modules_;
    struct QueueEvent {qint64 timestamp=0;bool pending=false;};
    QMap<quint64,QMap<QString,QueueEvent>> tasks_;
    QFile profile_;
    QByteArray profilePartial_;
    QString runFolder_;
    QTimer poll_;
    QElapsedTimer stopClock_;
    bool closing_=false,stopping_=false,lastOrderly_=true;
    int completedAnswers_=0,completedCycles_=0,heartbeats_=0;
};
