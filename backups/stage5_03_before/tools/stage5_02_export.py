#!/usr/bin/env python3
"""Export Stage 5.2 full current source, hashes and Git-format patch; no remote writes."""
from pathlib import Path
import difflib,hashlib,json,subprocess,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

def main():
 before=ROOT/'backups/stage5_02_before';report=ROOT/'reports/stage5_02_local'
 baseline=json.loads((report/'baseline_manifest.json').read_text())
 assert all(sha(before/r['file'])==r['sha256'] for r in baseline),'baseline snapshot drift'
 paths={Path('CMakeLists.txt')}
 for directory in ['include','src','tests','tools','docs','config']:
  paths.update(p.relative_to(ROOT) for p in (ROOT/directory).rglob('*') if p.is_file() and p.suffix in {'.h','.cpp','.hpp','.cmake','.md','.py','.sh','.txt','.tsv','.ps1'})
 changed=sorted(p for p in paths if sha(before/p)!=sha(ROOT/p))
 source=[p for p in changed if p.parts[0]!='docs']
 appendix=['# 5.2 当前修改源码全文\n\n','由 `tools/stage5_02_export.py` 从真实文件生成。逐句语义解释见 [stage5_02_statement_notes.md](stage5_02_statement_notes.md)，架构与实测见 [stage5_02_async_pipeline.md](stage5_02_async_pipeline.md)。本附录不省略入口及测试，不代替板端版本哈希或执行证据。\n\n']
 for i,p in enumerate(source,1):
  lang='cmake' if p.name=='CMakeLists.txt' else {'.py':'python','.sh':'bash','.tsv':'text','.ps1':'powershell'}.get(p.suffix,'cpp')
  content=(ROOT/p).read_text(encoding='utf-8-sig')
  appendix.append(f'## 操作 {i}：{p.as_posix()}\n\nSHA256：`{sha(ROOT/p)}`；{len(content.splitlines())} 行。\n\n```{lang}\n{content.rstrip()}\n```\n\n')
 (ROOT/'docs/stage5_02_source_appendix.md').write_text(''.join(appendix),encoding='utf-8',newline='\n')
 changed=sorted(set(changed+[Path('docs/stage5_02_source_appendix.md')]))
 manifest=[dict(file=p.as_posix(),before_sha256=sha(before/p),after_sha256=sha(ROOT/p),status='modified' if (before/p).exists() else 'added') for p in changed]
 # Use real git diff --no-index, including byte-level line-ending changes.
 scratch=Path(tempfile.mkdtemp(prefix='stage5_02_diff_'));patch=[]
 for p in changed:
  a=scratch/'a'/p;b=scratch/'b'/p;b.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/p,b)
  if (before/p).is_file():a.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before/p,a);old=(Path('a')/p).as_posix()
  else:old='/dev/null'
  command=['git','-c','core.quotepath=false','-c','core.autocrlf=false','diff','--no-index','--binary','--src-prefix=','--dst-prefix=',old,(Path('b')/p).as_posix()]
  result=subprocess.run(command,cwd=scratch,capture_output=True,timeout=30)
  assert result.returncode in (0,1),result.stderr
  content=result.stdout
  lines=content.splitlines(keepends=True)
  lines[0]=('diff --git a/'+p.as_posix()+' b/'+p.as_posix()+'\n').encode()
  content=b''.join(lines)
  patch.append(content)
 (report/'changes.patch').write_bytes(b''.join(patch))
 (report/'change_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # Apply to exact baseline bytes in a new temporary tree, never to the real workspace.
 check=scratch/'apply';shutil.copytree(before,check)
 command=['git','-c','core.autocrlf=false','apply','--check',str(report/'changes.patch')]
 result=subprocess.run(command,cwd=check,capture_output=True,timeout=60)
 (report/'patch_check.json').write_text(json.dumps(dict(command=command,exit_code=result.returncode,stdout=result.stdout.decode(errors='replace'),stderr=result.stderr.decode(errors='replace')),indent=2))
 assert result.returncode==0,result.stderr.decode(errors='replace')
 applied=subprocess.run(['git','-c','core.autocrlf=false','apply',str(report/'changes.patch')],cwd=check,capture_output=True,timeout=60)
 verification={p.as_posix():sha(check/p)==sha(ROOT/p) for p in changed}
 (report/'patch_roundtrip.json').write_text(json.dumps(dict(exit_code=applied.returncode,all_bytes_match=all(verification.values()),files=verification,stderr=applied.stderr.decode(errors='replace')),indent=2))
 assert applied.returncode==0 and all(verification.values()),verification
 invariants=[]
 for name in ['src/ai/rkllm_backend.cpp','src/ai/rk3576_vlm_backend.cpp','src/video/video_capture.cpp','src/video/camera_service.cpp','src/audio/asr_service.cpp','src/audio/vad_audio_worker.cpp']:
  invariants.append(dict(file=name,before=sha(before/name),after=sha(ROOT/name),unchanged=sha(before/name)==sha(ROOT/name)))
 def signal_helper(path):
  text=path.read_text(encoding='utf-8');start=text.index('class StopSignals');return text[start:text.index('\n};',start)+3]
 signal_same=signal_helper(before/'src/audio/asr_llm_tts_smoke.cpp')==signal_helper(ROOT/'src/audio/asr_llm_tts_smoke.cpp')
 (report/'source_invariants.json').write_text(json.dumps(dict(checks=invariants,signal_helper_unchanged=signal_same,scope='Source equality only; not runtime evidence'),indent=2))
 assert signal_same and all(item['unchanged'] for item in invariants)
 print('EXPORTED',len(source),'source files;',len(manifest),'changes; patch check',result.returncode)
if __name__=='__main__':main()
