#!/usr/bin/env python3
"""Bounded manual hardware benchmark runner; writes only isolated Stage 5.4 reports."""
from pathlib import Path
import argparse,glob,json,os,signal,subprocess,sys,time,shutil
ROOT=Path('/home/cat/projects/RK3576/rk3576_multimodal_stage5_review')
sys.path.insert(0,str(ROOT/'tools'))
from stage5_board_readonly_inventory import fingerprint
from stage5_03_voice_run import discover_audio,devices,query
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def sample(pid,index):
    result={'monotonic':time.monotonic(),'wall_time':time.time(),'pid':pid}
    try:
        result['stat']=Path(f'/proc/{pid}/stat').read_text()
        result['status']=Path(f'/proc/{pid}/status').read_text()
        result['system_stat']=Path('/proc/stat').read_text().splitlines()[0]
        result['loadavg']=Path('/proc/loadavg').read_text().strip()
        result['tasks']={}
        for folder in Path(f'/proc/{pid}/task').iterdir():
            try:result['tasks'][folder.name]={'stat':(folder/'stat').read_text(),'allowed':[x for x in (folder/'status').read_text().splitlines() if x.startswith('Cpus_allowed_list:')]}
            except OSError:pass
        if index%5==0:result['smaps_rollup']=Path(f'/proc/{pid}/smaps_rollup').read_text()
        result['sysfs']={}
        for pattern in ['/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq','/sys/class/thermal/thermal_zone*/temp','/sys/class/devfreq/*npu*/cur_freq','/sys/class/devfreq/*npu*/load']:
            for name in glob.glob(pattern):
                try:result['sysfs'][name]=Path(name).read_text().strip()
                except OSError as e:result['sysfs'][name]={'error':str(e)}
    except OSError as e:result['sample_error']=str(e)
    return result
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--name',required=True);parser.add_argument('--exe',required=True);parser.add_argument('--timeout',type=int,default=1800);parser.add_argument('--affinity');parser.add_argument('--ort-profile',action='store_true');parser.add_argument('--env',action='append',default=[]);parser.add_argument('arguments',nargs=argparse.REMAINDER);args=parser.parse_args()
    assert Path(__file__).resolve().parent==ROOT/'tools' and not ROOT.is_symlink()
    assert args.name and all(x.isalnum() or x in '_-' for x in args.name)
    exe=Path(args.exe).resolve();assert exe.is_relative_to(ROOT) and exe.is_file()
    assert 1<=args.timeout<=3600
    report=ROOT/'reports/stage5_04_board'/args.name;report.mkdir()
    before=fingerprint();save(report/'stable_before.json',before);audio=discover_audio();pre=devices(audio);save(report/'devices_before.json',pre);assert pre['clear']
    envout=subprocess.check_output(['bash','-c','set -a; source "$1/tools/stage5_board_paths.sh"; env -0','stage5_04',str(ROOT)],timeout=15)
    env=dict(x.decode().split('=',1) for x in envout.split(b'\0') if b'=' in x)
    for entry in args.env:
        key,value=entry.split('=',1);assert key.startswith('STAGE5_');env[key]=value.replace('{REPORT}',str(report))
    if args.ort_profile:
        config=report/'ort_session.config'
        config.write_text('ProfilingFilePrefix='+str(report/'ort_profile')+'\n')
        env['STAGE5_TTS_ORT_PROFILE_CONFIG']=str(config)
    argv=args.arguments[1:] if args.arguments[:1]==['--'] else args.arguments
    argv=[x.replace('{REPORT}',str(report)).replace('{KOKORO}',env['STAGE5_KOKORO']) for x in argv]
    command=[str(exe),*argv]
    if args.affinity:command=['taskset','-c',args.affinity,*command]
    save(report/'command.json',command);save(report/'parameters.json',vars(args));save(report/'environment.json',{k:v for k,v in env.items() if k.startswith('STAGE5_') or k=='LD_LIBRARY_PATH'})
    save(report/'system_before.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)]),'clock_ticks':os.sysconf('SC_CLK_TCK')})
    assert shutil.disk_usage(ROOT).free>=500*1024**2
    with (report/'terminal.log').open('wb') as out,(report/'stderr.log').open('wb') as err,(report/'resources.jsonl').open('w') as samples:
        child=subprocess.Popen(command,cwd=ROOT,env=env,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);start=time.monotonic();reason=None;forced=False
        token=Path(f'/proc/{child.pid}/stat').read_text().split()[21];save(report/'pid.json',{'pid':child.pid,'exe':str(exe),'start_token':token})
        index=0
        while child.poll() is None:
            samples.write(json.dumps(sample(child.pid,index))+'\n');samples.flush();index+=1
            if time.monotonic()-start>args.timeout or shutil.disk_usage(ROOT).free<500*1024**2:
                reason='timeout' if time.monotonic()-start>args.timeout else 'disk_below_500MiB'
                assert Path(f'/proc/{child.pid}/exe').resolve()==exe and Path(f'/proc/{child.pid}/stat').read_text().split()[21]==token
                os.kill(child.pid,signal.SIGTERM)
                try:child.wait(timeout=15)
                except subprocess.TimeoutExpired:os.kill(child.pid,signal.SIGKILL);forced=True;child.wait(timeout=10)
                break
            time.sleep(1)
        code=child.wait();seconds=time.monotonic()-start
    post=devices(audio);save(report/'devices_after.json',post);after=fingerprint();save(report/'stable_after.json',after)
    save(report/'system_after.json',{'memory':query(['free','-b']),'disk':query(['df','-B1',str(ROOT)])})
    result={'returncode':code,'seconds':seconds,'termination_reason':reason,'forced_kill':forced,'process_gone':not Path(f'/proc/{child.pid}').exists(),'devices_released':post['clear'],'original_321_unchanged':before==after,'disk_free_bytes':shutil.disk_usage(ROOT).free}
    save(report/'result.json',result);print('RUN_RESULT',args.name,json.dumps(result),flush=True)
    print((report/'terminal.log').read_text(errors='replace')[-10000:],flush=True);print((report/'stderr.log').read_text(errors='replace')[-2000:],flush=True)
    return 0 if code==0 and not reason and post['clear'] and before==after else 1
if __name__=='__main__':raise SystemExit(main())
