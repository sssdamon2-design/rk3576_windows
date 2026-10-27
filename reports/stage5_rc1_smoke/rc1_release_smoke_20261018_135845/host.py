from pathlib import Path
import sys,json
sys.path.insert(0,str(Path.cwd()/'tools'));import stage5_phase2_deploy as t
out=Path(__file__).resolve().parent
name=sys.argv[1];payload=(out/(name+'.py')).read_bytes();compile(payload,str(out/(name+'.py')),'exec')
raise SystemExit(t.run_step(out,name,t.remote_command(),payload,430 if name=='run' else 120))
