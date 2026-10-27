#include "gui/session_window.h"
#include "app/stop_signals.h"
#include <QApplication>
#include <QElapsedTimer>
#include <QTemporaryDir>
#include <QTest>
#include <iostream>

class GuiTests:public QObject {
    Q_OBJECT
private slots:
    void startStopRestartAndClose() {
        QTemporaryDir report;QVERIFY(report.isValid());
        GuiLaunch settings;settings.program=QCoreApplication::applicationDirPath()+"/gui_fake_backend";
        settings.environment=QProcessEnvironment::systemEnvironment();settings.reportRoot=report.path();settings.threadArgument=-1;
        SessionWindow window(settings);window.show();
        auto* start=window.findChild<QPushButton*>("start");auto* stop=window.findChild<QPushButton*>("stop");
        QVERIFY(start && stop);QTest::mouseClick(start,Qt::LeftButton);
        QTRY_VERIFY(window.findChild<QLabel*>("transcript")->text().contains("fake transcript"));
        QVERIFY(window.findChild<QPlainTextEdit*>("answers")->toPlainText().contains("fake answer"));
        QVERIFY(!start->isEnabled());QTest::qWait(120);QVERIFY(window.heartbeatCount()>0);
        QTest::mouseClick(stop,Qt::LeftButton);QTRY_VERIFY(!window.active());QVERIFY(window.verified());
        QCOMPARE(window.completedCycles(),1);QVERIFY(start->isEnabled());
        QTest::mouseClick(start,Qt::LeftButton);QTRY_VERIFY(window.active());
        // Closing a live window must wait for cooperative child exit.
        window.close();QTRY_VERIFY(!window.active());QVERIFY(window.verified());
        QTRY_VERIFY(!window.isVisible());QCOMPARE(window.completedCycles(),2);
    }
    void launchFailureAndRecovery() {
        QTemporaryDir report;BackendSession session;int problems=0;
        connect(&session,&BackendSession::problem,this,[&](const QString&){++problems;});
        QVERIFY(!session.start("/nonexistent/stage5_fake",{},QProcessEnvironment::systemEnvironment(),report.path()+"/failure.log"));
        QVERIFY(problems==1 && !session.active());
        bool finished=false,orderly=false;
        connect(&session,&BackendSession::finished,this,[&](int,bool ok){finished=true;orderly=ok;});
        QFile invalid(report.path()+"/bad_interpreter");QVERIFY(invalid.open(QIODevice::WriteOnly));
        invalid.write("#!/nonexistent/stage5_interpreter\n");invalid.close();
        QVERIFY(invalid.setPermissions(QFileDevice::ReadOwner|QFileDevice::WriteOwner|QFileDevice::ExeOwner));
        QVERIFY(session.start(invalid.fileName(),{},QProcessEnvironment::systemEnvironment(),report.path()+"/exec_error.log"));
        QTRY_VERIFY(finished);QVERIFY(!orderly && !session.active());finished=false;
        QVERIFY(session.start(QCoreApplication::applicationDirPath()+"/gui_fake_backend",{},QProcessEnvironment::systemEnvironment(),report.path()+"/recover.log"));
        QTest::qWait(100);session.requestStop();QTRY_VERIFY(finished);QVERIFY(orderly);
        QVERIFY(!session.start(QCoreApplication::applicationDirPath()+"/gui_fake_backend",{},QProcessEnvironment::systemEnvironment(),report.path()+"/recover.log"));
        QVERIFY(!session.active()); // Existing evidence must never be truncated.
    }
    void automaticCloseDoesNotRestart() {
        QTemporaryDir report;GuiLaunch settings;
        settings.program=QCoreApplication::applicationDirPath()+"/gui_fake_backend";
        settings.environment=QProcessEnvironment::systemEnvironment();settings.reportRoot=report.path();settings.threadArgument=-1;
        settings.automatic=true;settings.cycles=2;
        SessionWindow window(settings);window.show();QTRY_VERIFY(window.active());
        window.close();QTRY_VERIFY(!window.active());QTRY_VERIFY(!window.isVisible());
        QTest::qWait(300);QVERIFY(!window.active());QCOMPARE(window.completedCycles(),1);
        QVERIFY(window.verified());
    }
};
int main(int argc,char** argv) {
    StopSignals stopSignals; // Match production inheritance for a stop during Starting.
    QApplication app(argc,argv);GuiTests tests;
    return QTest::qExec(&tests,argc,argv);
}
#include "gui_session_tests.moc"
