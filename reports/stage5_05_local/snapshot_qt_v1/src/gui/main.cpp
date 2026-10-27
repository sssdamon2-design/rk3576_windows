#include "app/stop_signals.h"
#include "gui/session_window.h"
#include <QApplication>
#include <QCommandLineParser>
#include <QDir>
#include <QFileInfo>
#include <QTextStream>

int main(int argc,char** argv) try {
    StopSignals stopSignals; // Must precede QApplication and every descendant thread.
    QApplication app(argc,argv);
    app.setApplicationName("rk3576_multimodal_gui");
    QCommandLineParser parser;parser.addHelpOption();
    parser.addOption({"capture","ALSA capture device, rediscover HyperX before launch","device"});
    parser.addOption({"playback","ALSA playback device","device"});
    parser.addOption({"report-root","Existing isolated report directory; each run creates a new child","path"});
    parser.addOption({"threads","Kokoro threads (2 or 4)","number","4"});
    parser.addOption({"seconds","Finite listening duration, 1..3600","number","120"});
    parser.addOption({"auto-start","Automated regression: click start after event loop begins"});
    parser.addOption({"stop-after-answers","Automated regression: stop after N successful TTS answers","number","0"});
    parser.addOption({"cycles","Automated regression: fresh child sessions, 1..4","number","1"});
    parser.process(app);
    const auto env=QProcessEnvironment::systemEnvironment();
    const auto review=env.value("STAGE5_REVIEW");
    const auto reports=QFileInfo(parser.value("report-root")).canonicalFilePath();
    if(review.isEmpty() || reports.isEmpty() || !reports.startsWith(QDir(review).canonicalPath()+"/reports/stage5_05_board/"))
        throw std::runtime_error("report-root must be an existing isolated Stage5.5 report directory");
    const auto number=[&](const char* key,int lo,int hi){bool ok=false;int n=parser.value(key).toInt(&ok);if(!ok || n<lo || n>hi)throw std::runtime_error("invalid numeric GUI argument");return n;};
    const int threads=number("threads",2,4),seconds=number("seconds",1,3600);
    if(threads!=2 && threads!=4)throw std::runtime_error("threads must be 2 or 4");
    if(parser.value("capture").isEmpty() || parser.value("playback").isEmpty())throw std::runtime_error("explicit ALSA devices required");
    for(const auto* key:{"STAGE5_ASR","STAGE5_VAD","STAGE5_QWEN","STAGE5_KOKORO","STAGE5_VLM","STAGE5_VISION"})
        if(env.value(key).isEmpty())throw std::runtime_error("source and export stage5_board_paths.sh first");
    GuiLaunch launch;launch.program="/usr/bin/stdbuf";launch.environment=env;launch.reportRoot=reports;
    launch.arguments={"-oL","-eL",QCoreApplication::applicationDirPath()+"/asr_llm_tts_smoke",parser.value("capture"),env.value("STAGE5_ASR"),env.value("STAGE5_VAD"),env.value("STAGE5_QWEN"),env.value("STAGE5_KOKORO"),parser.value("playback"),QString::number(seconds),QString::number(threads),"17",env.value("STAGE5_VLM"),env.value("STAGE5_VISION"),"/dev/video11"};
    launch.automatic=parser.isSet("auto-start");launch.stopAfterAnswers=number("stop-after-answers",0,32);launch.cycles=number("cycles",1,4);
    SessionWindow window(std::move(launch));window.show();
    QTimer pollSignals;pollSignals.setInterval(100);
    QObject::connect(&pollSignals,&QTimer::timeout,&window,[&] {
        if(stopSignals.received() || stopSignals.failed())window.close();
    });pollSignals.start();
    const int code=app.exec();
    return code?code:(stopSignals.failed() || !window.verified()?1:0);
} catch(const std::exception& error) {
    QTextStream(stderr)<<"[GUI fatal] "<<error.what()<<Qt::endl;return 1;
}
