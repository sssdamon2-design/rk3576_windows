#!/usr/bin/env python3
"""Capture an explicitly authorized phase-3 SSH payload without rewriting output."""
import argparse
from datetime import datetime
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
import stage5_phase2_deploy as transport


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload', type=Path)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    assert bool(args.payload) != args.collect
    root = transport.ROOT
    report = root/'reports/stage5_01_board'/('phase3_ssh_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
    report.mkdir()
    if args.collect:
        source = transport.payloads()['05_collect']
    else:
        path = args.payload.resolve()
        assert path.is_relative_to(root)
        source = path.read_text(encoding='utf-8')
    compile(source, '<remote>', 'exec')
    code = transport.run_step(report, 'remote', transport.remote_command(), source.encode('utf-8'), args.timeout, binary=args.collect)
    if args.collect and code == 0:
        destination=report/'collected'
        destination.mkdir()
        with tarfile.open(report/'remote.tgz','r:gz') as archive:
            for m in archive.getmembers():
                p=PurePosixPath(m.name)
                assert m.isfile() and not p.is_absolute() and '..' not in p.parts
                target=destination/Path(*p.parts)
                target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as stream:
                    stream.write(archive.extractfile(m).read())
    print('REPORT_DIRECTORY',report.relative_to(root),flush=True)
    if not args.collect:
        print((report/'remote.stdout.log').read_text(encoding='utf-8',errors='replace')[-18000:],flush=True)
        print((report/'remote.stderr.log').read_text(encoding='utf-8',errors='replace')[-4000:],flush=True)
    return code


if __name__=='__main__':
    raise SystemExit(main())
