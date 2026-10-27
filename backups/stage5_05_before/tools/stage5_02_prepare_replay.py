#!/usr/bin/env python3
"""Add the same explicit replay/timer instrumentation to candidate and copied 5.1 entry.

Runs locally only. Baseline model algorithms, capacities and stop semantics are retained.
"""
from pathlib import Path
import difflib

ROOT=Path(__file__).resolve().parents[1]


def replay(s, candidate):
    s=s.replace('#include <chrono>','#include <chrono>\n#include <fstream>\n#include <sstream>\n#include <cstdlib>')
    begin=s.index('    try\n    {\n        // ASR',s.index('    const auto on_text ='))
    end=s.index('    asr.shutdown();',begin)
    normal=s[begin:end]
    s=s[:begin]+'''    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");
    const bool replay_mode=replay_path!=nullptr;
    if (replay_mode)
    {
        std::ifstream input(replay_path);
        if (!input) throw std::runtime_error("Cannot open replay input");
        std::cout << "[InputMode] replay_only NO_MICROPHONE_ASR_OR_VAD_INFERENCE\\n" << std::flush;
        const auto replay_start=std::chrono::steady_clock::now();
        std::string line;
        while (std::getline(input,line))
        {
            if (line.empty()) continue;
            const auto tab=line.find('\\t');
            if (tab==std::string::npos) throw std::runtime_error("Invalid replay line");
            std::size_t used=0;
            const long delay=std::stol(line.substr(0,tab),&used);
            if (used!=tab || delay<0 || delay>120000) throw std::runtime_error("Invalid replay offset");
            std::this_thread::sleep_until(replay_start+std::chrono::milliseconds(delay));
            if (stop_signals.received()!=0) break;
            std::cout << "[Replay] scheduled_ms=" << delay << " source=controlled_text\\n" << std::flush;
            on_text(line.substr(tab+1));
        }
        audio_queue.close();
    }
    else
    {
'''+normal+'''    }
'''+s[end:]
    # Unlike real microphone runs, replay must not claim the non-started VAD/ASR workers succeeded.
    s=s.replace('if (!producer.ok())','if (!replay_mode && !producer.ok())')
    s=s.replace('if (!consumer.ok())','if (!replay_mode && !consumer.ok())')
    if candidate:
        s=s.replace('producer.ok() && consumer.ok() && audio_queue.droppedCount()==0 &&','(replay_mode || (producer.ok() && consumer.ok())) && audio_queue.droppedCount()==0 &&')
    else:
        s=s.replace('''        producer.ok() &&
        consumer.ok() &&''','''        (replay_mode || (producer.ok() && consumer.ok())) &&''')
    # Honest mode labels: replay does not start/join capture/VAD/ASR workers.
    declarations='    const char* replay_path=std::getenv("STAGE5_REPLAY_FILE");\n    const bool replay_mode=replay_path!=nullptr;\n'
    s=s.replace(declarations,'',1)
    listen=s.index('    std::cout\n        << "[Listen] "')
    listen_end=s.index('        << std::flush;',listen)+len('        << std::flush;')
    s=s[:listen]+declarations+'    if (!replay_mode)\n    {\n'+s[listen:listen_end]+'\n    }\n    else std::cout << "[Replay ready] controlled text; microphone/VAD/ASR not run\\n" << std::flush;'+s[listen_end:]
    s=s.replace('std::cout << "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\\n" << std::flush;', 'std::cout << (replay_mode ? "[Shutdown] replay input closed; recognizer destroyed\\n" : "[Shutdown] capture/VAD and ASR joined; recognizer destroyed\\n") << std::flush;')
    return s


def main():
    entry=ROOT/'src/audio/asr_llm_tts_smoke.cpp'
    s=entry.read_text(encoding='utf-8')
    if '[InputMode] replay_only' in s:raise SystemExit('Replay already prepared; refuse duplicate instrumentation')
    entry.write_text(replay(s,True),encoding='utf-8')
    baseline=ROOT/'backups/stage5_02_before'
    out=ROOT/'reports/stage5_02_local/instrumented_baseline'
    out.mkdir()
    changes=[]
    def save(name,modified):
        p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(modified,encoding='utf-8')
        old=(baseline/name).read_text(encoding='utf-8') if (baseline/name).exists() else ''
        changes.extend(difflib.unified_diff(old.splitlines(keepends=True),modified.splitlines(keepends=True),fromfile='a/'+name,tofile='b/'+name))
    s=(baseline/'src/audio/asr_llm_tts_smoke.cpp').read_text(encoding='utf-8')
    s=s.replace('#include <chrono>','#include <chrono>\n#include "app/pipeline_metrics.h"')
    s=s.replace('    IntentRouter router;','    IntentRouter router;\n    std::size_t dispatch_calls=0;')
    anchor='    {\n        // --------------------------------------------------\n        // 12.1'
    start=s.index(anchor,s.index('    const auto on_text ='))
    s=s[:start]+s[start:].replace('    {\n','    {\n        DispatchTimer dispatch_timer{print_mutex, ++dispatch_calls};\n',1)
    s=replay(s,False)
    start=s.index('    const bool passed =')
    s=s[:start]+'''    std::cout << "[BaselineQueues] inference_peak=" << llm_worker.peakCount()
              << " tts_peak=" << tts_worker.peakCount() << " audio_peak=" << audio_queue.peakCount() << '\\n';
'''+s[start:]
    save('src/audio/asr_llm_tts_smoke.cpp',s)
    for name,container,field in [('ai/llm_worker','pending_','rejected_'),('audio/tts_worker','pending_','rejected_'),('audio/asr_pipeline','items_','dropped_')]:
        hname='include/'+name+'.h';cname='src/'+name+'.cpp'
        h=(baseline/hname).read_text(encoding='utf-8')
        h=h.replace('    std::size_t '+field+' = 0;','    std::size_t '+field+' = 0;\n    std::size_t measured_peak_ = 0;',1)
        h=h.replace('    std::size_t '+('rejectedCount' if field=='rejected_' else 'droppedCount')+'() const;',
                    '    std::size_t '+('rejectedCount' if field=='rejected_' else 'droppedCount')+'() const;\n    std::size_t peakCount() const {std::lock_guard<std::mutex> lock(mutex_);return measured_peak_;}',1)
        c=(baseline/cname).read_text(encoding='utf-8')
        c='#include <algorithm>\n'+c
        push='        '+container+'.push_back(std::move('+('task' if container=='pending_' else 'segment')+'));'
        assert push in c
        c=c.replace(push,push+'\n        measured_peak_=std::max(measured_peak_,'+container+'.size());',1)
        save(hname,h);save(cname,c)
    for name in ('include/app/pipeline_metrics.h','include/common/work_control.h'):
        save(name,(ROOT/name).read_text(encoding='utf-8'))
    (ROOT/'reports/stage5_02_local/baseline_instrumentation.patch').write_text(''.join(changes),encoding='utf-8')
    print('Prepared matching explicit replay/timer instrumentation; baseline queue algorithms and limits unchanged.')


if __name__=='__main__':main()
