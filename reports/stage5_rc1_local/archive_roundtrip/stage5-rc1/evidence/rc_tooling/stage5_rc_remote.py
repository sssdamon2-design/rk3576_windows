"""Run RC-only SSH payloads with complete command/output/exit records."""
from pathlib import Path
from datetime import datetime
import argparse,sys
import stage5_phase2_deploy as t
def main():
 p=argparse.ArgumentParser();p.add_argument('payload',type=Path);p.add_argument('--timeout',type=int,default=180);a=p.parse_args()
 source=a.payload.read_bytes();compile(source,str(a.payload),'exec')
 report=t.ROOT/'reports/stage5_rc1_local'/('ssh_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'));report.mkdir()
 rc=t.run_step(report,'remote',t.remote_command(),source,a.timeout)
 print('LOG',report.relative_to(t.ROOT))
 for leaf in ['remote.stdout.log','remote.stderr.log']:print((report/leaf).read_text(encoding='utf-8',errors='replace')[-5000:])
 return rc
if __name__=='__main__':raise SystemExit(main())
