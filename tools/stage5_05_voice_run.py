#!/usr/bin/env python3
"""Stage 5.5 hardware/replay comparisons; explicit input mode and PID-safe timeout guards."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import re
import resource
import signal
import subprocess
import sys
import threading
import time

ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_04_run import sample as profile_sample


def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def query(command):
    r=subprocess.run(command,capture_output=True,timeout=15)
    return {'command':command,'exit_code':r.returncode,'stdout':r.stdout.decode(errors='replace'),'stderr':r.stderr.decode(errors='replace')}


def discover_audio():
    cards=Path('/proc/asound/cards').read_text()
    matches=re.findall(r'^\s*(\d+)\s+\[([^\]]+)\]\s*:\s*USB-Audio - HyperX Cloud III\s*$',cards,re.M)
    assert len(matches)==1,'expected exactly one HyperX Cloud III'
    card,card_id=matches[0]; card_id=card_id.strip()
    capture={re.search(r'pcm(\d+)c$',p.name).group(1) for p in Path('/proc/asound',f'card{card}').glob('pcm*c')}
    playback={re.search(r'pcm(\d+)p$',p.name).group(1) for p in Path('/proc/asound',f'card{card}').glob('pcm*p')}
    common=capture & playback
    assert len(common)==1, 'expected unique duplex PCM device'
    device=common.pop()
    return {'cards':cards,'capture_listing':query(['arecord','-l']),'playback_listing':query(['aplay','-l']),
            'card_number':int(card),'card_id':card_id,'pcm_device':int(device),
            'alsa_device':f'plughw:CARD={card_id},DEV={device}',
            'nodes':[f'/dev/snd/pcmC{card}D{device}c',f'/dev/snd/pcmC{card}D{device}p']}


def owner_identity(pid):
    proc=Path('/proc')/str(pid);status=(proc/'status').read_text()
    uid=int(re.search(r'^Uid:\s+(\d+)',status,re.M)[1])
    stat=(proc/'stat').read_text();fields=stat[stat.rfind(')')+2:].split()
    return {'pid':int(pid),'start_token':fields[19],'uid':uid,'comm':(proc/'comm').read_text().strip(),'cmdline':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace').strip()}


def devices(audio):
    npu=[]
    for p in Path('/sys/class/drm').iterdir():
        if not re.fullmatch(r'(?:card|renderD)\d+',p.name):continue
        driver=p/'device/driver'
        if driver.exists() and 'rknpu' in str(driver.resolve()).lower():npu.append('/dev/dri/'+p.name)
    assert npu,'RKNPU DRM node required'
    nodes=['/dev/video11',*audio['nodes'],*sorted(npu)]
    strict=['/dev/video11',*audio['nodes'],*[p for p in npu if Path(p).name.startswith('renderD')]]
    strict_query=query(['sudo','-n','--','/usr/bin/fuser','-v',*strict])
    strict_clear=strict_query['exit_code']==1 and not strict_query['stdout'].strip() and not strict_query['stderr'].strip()
    baseline_path=Path(os.environ.get('STAGE5_NPU_OWNER_BASELINE',str(ROOT/'reports/stage5_05_board/npu_primary_baseline.json')))
    assert baseline_path.resolve().is_relative_to(ROOT),'baseline must be inside isolated project'
    baseline=json.loads(baseline_path.read_text());primary={};matched=True
    for node in npu:
        if not Path(node).name.startswith('card'):continue
        q=query(['sudo','-n','--','/usr/bin/fuser','-v',node])
        identities=[owner_identity(int(x)) for x in q['stdout'].split() if x.isdigit()]
        expected=baseline['primary_nodes'].get(node,{}).get('identities')
        unchanged=q['exit_code'] in (0,1) and expected is not None and identities==expected
        primary[node]={'query':q,'identities':identities,'matches_frozen_desktop_owners':unchanged};matched &= unchanged
    return {'nodes':nodes,'NPU_nodes':sorted(npu),'query':strict_query,'primary_owner_queries':primary,'desktop_owner_baseline':str(baseline_path),'clear':strict_clear and matched,
            'scope':'Camera/ALSA/render empty; NPU primary may retain EXACT frozen root systemd/logind/Xorg owners; unknown owners reject',
            'alsa_status':{str(p):p.read_text() for p in Path('/proc/asound',f"card{audio['card_number']}").glob('pcm*/sub*/status')}}


def sample(pid):
    result={'time':time.time(),'pid':pid}
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            k=line.split(':',1)[0]
            if k in {'State','Threads','VmRSS','VmHWM','VmSize'}:
                result[k]=line.split(':',1)[1].strip()
        result['fds']={p.name:os.readlink(p) for p in Path(f'/proc/{pid}/fd').iterdir()}
        result['tasks']=sorted(p.name for p in Path(f'/proc/{pid}/task').iterdir())
    except OSError as e:
        result['sample_error']=str(e)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name',required=True)
    parser.add_argument('--build-name',default='stage5_05_thermal')
    parser.add_argument('--tts-threads',type=int,default=2)
    parser.add_argument('--variant',choices=('baseline','candidate'),default='candidate')
    parser.add_argument('--revision',choices=('v1','v2','v3'),default='v3')
    parser.add_argument('--capture-fixtures',action='store_true')
    parser.add_argument('--audio-replay-file')
    parser.add_argument('--fixed-frame-dir')
    parser.add_argument('--replay',action='store_true')
    parser.add_argument('--replay-source',choices=('four','pair'),default='four')
    parser.add_argument('--stop-mode',choices=('drain','cancel_pending'),default='drain')
    parser.add_argument('--tts-queue-ms',type=int,default=12000)
    parser.add_argument('--request-lifetime-ms',type=int,default=45000)
    parser.add_argument('--signal',choices=('SIGINT','SIGTERM'))
    parser.add_argument('--trigger',choices=('init','ready','llm','vision','tts','both_done'),default='ready')
    parser.add_argument('--delay',type=float,default=2)
    parser.add_argument('--seconds',type=int,default=120)
    parser.add_argument('--timeout',type=int,default=240)
    parser.add_argument('--grace',type=int,default=40)
    args=parser.parse_args()
    assert Path(__file__).resolve().parents[1]==ROOT and not ROOT.is_symlink()
    assert re.fullmatch(r'[A-Za-z0-9_-]+',args.name)
    assert 1<=args.seconds<=3600 and 1<=args.timeout<=4200 and 1<=args.grace<=90 and args.delay>=0
    report=ROOT/'reports/stage5_05_board'/args.name
    report.mkdir()
    before=fingerprint(); save(report/'stable_before.json',before)
    audio=discover_audio(); save(report/'audio_detection.json',audio)
    pre=devices(audio);save(report/'devices_before.json',pre)
    assert pre['clear'],'target device occupied'
    assert os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize>=500*1024**2
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'clock_ticks':os.sysconf('SC_CLK_TCK')})
    envout=subprocess.check_output(['bash','-c','source "$1/tools/stage5_board_paths.sh"; env -0','phase3',str(ROOT)],timeout=15)
    env=dict(part.decode().split('=',1) for part in envout.split(b'\0') if b'=' in part)
    assert 1<=args.tts_threads<=8
    assert 1<=args.tts_queue_ms<=60000 and 1<=args.request_lifetime_ms<=300000
    env.pop('STAGE5_IMAGE_PROFILE',None)
    env['STAGE5_PROFILE']=str(report/'profile.jsonl')
    env['STAGE5_STOP_MODE']=args.stop_mode
    env['STAGE5_TTS_QUEUE_MS']=str(args.tts_queue_ms)
    env['STAGE5_REQUEST_LIFETIME_MS']=str(args.request_lifetime_ms)
    for key in ('STAGE5_CAPTURE_AUDIO_FIXTURES','STAGE5_REPLAY_AUDIO_FILE','STAGE5_REPLAY_FRAME_DIR'):env.pop(key,None)
    assert not (args.replay and args.audio_replay_file)
    if args.capture_fixtures:
        assert not args.replay and not args.audio_replay_file
        (report/'audio_fixtures').mkdir();env['STAGE5_CAPTURE_AUDIO_FIXTURES']=str(report/'audio_fixtures')
    if args.fixed_frame_dir:
        fixed=Path(args.fixed_frame_dir);assert fixed.resolve().is_relative_to(ROOT) and (args.replay or args.audio_replay_file)
        env['STAGE5_REPLAY_FRAME_DIR']=str(fixed)
    if args.audio_replay_file:
        replay=Path(args.audio_replay_file);assert replay.resolve().is_relative_to(ROOT)
        env['STAGE5_REPLAY_AUDIO_FILE']=str(replay)
        save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'text':replay.read_text()})
    if args.replay:
        replay=ROOT/('tests/stage5_02_replay.tsv' if args.replay_source=='four' else 'tests/stage5_02_replay_pair.tsv')
        env['STAGE5_REPLAY_FILE']=str(replay)
        save(report/'replay_input.json',{'path':str(replay),'sha256':hashlib.sha256(replay.read_bytes()).hexdigest(),'text':replay.read_text()})
    else: env.pop('STAGE5_REPLAY_FILE',None)
    base='/home/cat/projects/RK3576'
    suffix='' if args.revision=='v1' else '_'+args.revision
    assert re.fullmatch(r'stage5_05_[A-Za-z0-9_]+',args.build_name)
    exe=ROOT/'build'/args.build_name/'asr_llm_tts_smoke'
    command=['stdbuf','-oL','-eL',str(exe),audio['alsa_device'],
             base+'/asr_runtime/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17',
             base+'/asr_runtime/vad/silero_vad.onnx',base+'/rkllm_sdk/models/Qwen2.5-1.5B-Instruct_RK3576_w4a16.rkllm',
             base+'/tts_runtime/models/kokoro-multi-lang-v1_1',audio['alsa_device'],str(args.seconds),str(args.tts_threads),'17',
             base+'/rk3576_multimodal/models/vlm/smolvlm2_256m_w4a16_rk3576.rkllm',
             base+'/rk3576_multimodal/models/vlm/smolvlm_vision_scatterfix_rk3576.rknn','/dev/video11']
    save(report/'command.json',command)
    save(report/'test_parameters.json',vars(args))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    events=queue.Queue()
    def reader():
        for line in iter(child.stdout.readline,b''):
            events.put(line)
        events.put(None)
    thread=threading.Thread(target=reader,daemon=True);thread.start()
    start=time.monotonic(); trigger_at=None; sent_at=None; eof=False; forced=False; timed_out=False; signaled=None
    input_closed_at=None; safety_reason=None
    sample_number=0; pid_token=None; text_done=False; vision_done=False; lines=[]; next_sample=start
    save(report/'pid.json',{'pid':child.pid,'exe':str(exe),'started':time.time()})
    def checked_signal(value):
        nonlocal pid_token
        assert child.poll() is None
        assert Path(f'/proc/{child.pid}/exe').resolve()==exe.resolve(),'PID/executable mismatch; refuse signal'
        current=Path(f'/proc/{child.pid}/stat').read_text().split()[21]
        if pid_token is None: pid_token=current
        assert current==pid_token,'PID start token mismatch'
        os.kill(child.pid,value) # exactly the child PID, no shared process group
    with (report/'terminal.log').open('wb') as terminal,(report/'resources.jsonl').open('w') as samples,(report/'events.jsonl').open('w') as eventlog:
        while child.poll() is None or not eof:
            try:
                line=events.get(timeout=0.1)
                if line is None: eof=True
                else:
                    terminal.write(line);terminal.flush();sys.stdout.buffer.write(line);sys.stdout.buffer.flush()
                    s=line.decode(errors='replace');lines.append(s)
                    milestone=('[Shutdown] replay input closed' in s or '[Shutdown] capture/VAD and ASR joined' in s)
                    if milestone and input_closed_at is None:
                        input_closed_at=time.monotonic()
                        eventlog.write(json.dumps({'event':'input_closed','elapsed':input_closed_at-start})+'\n');eventlog.flush()

                    text_done |= bool(re.search(r'(?<!VISION )\[TTS done .*success=true',s))
                    vision_done |= '[VISION TTS done ' in s and 'success=true' in s
                    found=(args.trigger=='init' and '[Init] Loading RKLLM' in s or args.trigger=='ready' and ('[Listen]' in s or '[Replay ready]' in s) or args.trigger=='llm' and '[ASR->LLM #' in s or args.trigger=='vision' and '[ASR->VISION #' in s or args.trigger=='tts' and '[ALSA write]' in s or args.trigger=='both_done' and text_done and vision_done)
                    if trigger_at is None and found:
                        trigger_at=time.monotonic()
                        eventlog.write(json.dumps({'event':'trigger','elapsed':trigger_at-start,'trigger':args.trigger})+'\n');eventlog.flush()
            except queue.Empty: pass
            now=time.monotonic()
            if child.poll() is None and now>=next_sample:
                reading=profile_sample(child.pid,sample_number)
                extra={str(p):p.read_text().strip() for pattern in ['/sys/class/thermal/cooling_device*/cur_state','/sys/devices/system/cpu/cpu*/cpufreq/scaling_max_freq'] for p in Path('/').glob(pattern.lstrip('/'))}
                reading['cooling_and_maxfreq']=extra
                samples.write(json.dumps(reading)+'\n');samples.flush();next_sample=now+1;sample_number+=1
                temps=[int(v)/1000 for k,v in reading.get('sysfs',{}).items() if k.endswith('/temp') and isinstance(v,str)]
                if not temps: safety_reason='temperature_unreadable'
                elif max(temps)>=90: safety_reason='temperature_at_or_above_conservative_90C_guard'
                if os.statvfs(ROOT).f_bavail*os.statvfs(ROOT).f_frsize<500*1024**2:safety_reason='disk_below_500MiB'
                available=next(int(x.split()[1]) for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))
                if available<256*1024:safety_reason='MemAvailable_below_256MiB'
            if child.poll() is None and sent_at is None:
                requested=args.signal and trigger_at is not None and now-trigger_at>=args.delay
                timed_out=now-start>args.timeout
                if requested or timed_out or safety_reason:
                    signaled='SIGTERM' if timed_out or safety_reason else args.signal
                    checked_signal(getattr(signal,signaled));sent_at=now
                    eventlog.write(json.dumps({'event':'signal','signal':signaled,'elapsed':now-start,'pid':child.pid,'pid_start_token':pid_token,'timeout':timed_out,'safety_reason':safety_reason})+'\n');eventlog.flush()
            if child.poll() is None and sent_at is not None and now-sent_at>args.grace:
                checked_signal(signal.SIGKILL);forced=True
                eventlog.write(json.dumps({'event':'FORCED_KILL_EXIT_FAILURE','pid':child.pid,'elapsed':now-start})+'\n');eventlog.flush()
                child.wait(timeout=10)
            if child.poll() is not None and not eof and now-start>args.timeout+args.grace+10:
                raise RuntimeError('child ended but output did not close')
    code=child.wait(); ended=time.monotonic(); thread.join(timeout=5)
    terminal=''.join(lines)
    post=devices(audio);save(report/'devices_after.json',post)
    after=fingerprint();save(report/'stable_after.json',after)
    summary={'pid':child.pid,'returncode':code,'termination_reason':safety_reason,'sent_signal':signaled,'trigger_observed':trigger_at is not None,'forced_kill':forced,'timeout':timed_out,
             'duration_seconds':ended-start,'input_closed_to_exit_seconds':None if input_closed_at is None else ended-input_closed_at,'signal_to_exit_seconds':None if sent_at is None else ended-sent_at,
             'timing_scope':'child exit/output EOF, excludes subsequent device/fingerprint queries',
             'process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':before==after,
             'image_profile_errors':'[ImageProfile ERROR]' in terminal,'shutdown_complete_marker':'[Shutdown] complete' in terminal,'program_PASS':bool(re.search(r'^PASS\s*$',terminal,re.M)),
             'text_tts_completed':text_done,'vision_tts_completed':vision_done,'user_audible_confirmation':None,'variant':args.variant,'input_mode':'fixed_audio_REAL_ASR_no_microphone_VAD' if args.audio_replay_file else ('controlled_text_no_microphone_ASR' if args.replay else 'real_microphone_ASR'),'stop_mode':args.stop_mode}
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'dmesg':query(['dmesg','--ctime'])})
    save(report/'result.json',summary)
    print('STAGE5_05_RUN_RESULT',json.dumps(summary),flush=True)
    print('REMOTE_REPORT',report,flush=True)
    return 0 # transport succeeded; child return code remains explicitly recorded above


if __name__=='__main__':
    raise SystemExit(main())
