"""Use packaged render_docx rasterization with diagnosed native Word PDF fallback."""
from pathlib import Path
import argparse,importlib.util,json,os,subprocess,sys,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
RUNTIME=Path('C:/Users/53009/.cache/codex-runtimes/codex-primary-runtime')
SKILL=Path('C:/Users/53009/.codex/plugins/cache/openai-primary-runtime/documents/26.1015.12040/skills/documents')

def main():
 p=argparse.ArgumentParser();p.add_argument('--document',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args()
 assert a.label.isidentifier() and a.document.resolve().is_relative_to(ROOT)
 report=ROOT/'reports/stage5_05_local'/('render_'+a.label);report.mkdir()
 env=dict(os.environ);env['PATH']=str(RUNTIME/'dependencies/native/poppler/Library/bin')+os.pathsep+env.get('PATH','')
 command=[sys.executable,str(SKILL/'render_docx.py'),str(a.document.resolve()),'--output_dir',str(report/'packaged_attempt'),'--verbose']
 start=time.monotonic()
 with (report/'packaged.stdout.log').open('wb') as out,(report/'packaged.stderr.log').open('wb') as err:
  process=subprocess.run(command,env=env,stdout=out,stderr=err,timeout=90)
 (report/'packaged.result.json').write_text(json.dumps({'command':command,'returncode':process.returncode,'seconds':time.monotonic()-start},indent=2))
 if process.returncode==0:
  print('PACKAGED_RENDER_SUCCEEDED',report);return 0
 error=(report/'packaged.stderr.log').read_text(encoding='utf-8',errors='replace')
 assert 'soffice' in error and 'not found' in error,'Unexpected renderer failure; diagnose instead of hiding it'
 pdf=report/'word_export.pdf'
 command=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'tools/stage5_05_word_export.ps1'),'-InputDocument',str(a.document.resolve()),'-OutputPdf',str(pdf)]
 start=time.monotonic()
 with (report/'word.stdout.log').open('wb') as out,(report/'word.stderr.log').open('wb') as err:
  process=subprocess.run(command,stdout=out,stderr=err,timeout=300)
 (report/'word.result.json').write_text(json.dumps({'command':command,'returncode':process.returncode,'seconds':time.monotonic()-start},indent=2))
 assert process.returncode==0 and pdf.is_file(),(report/'word.stderr.log').read_text(errors='replace')
 os.environ['PATH']=env['PATH']
 spec=importlib.util.spec_from_file_location('packaged_docx_renderer',SKILL/'render_docx.py')
 renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
 # Keep packaged PDF-to-PNG machinery; replace only its unavailable LO conversion.
 renderer.convert_to_pdf=lambda *args,**kwargs:(str(pdf),'Native Word PDF export, recorded in word.result.json')
 output=report/'pages';renderer.rasterize(str(a.document.resolve()),str(output),120,False,False)
 pages=sorted(output.glob('page-*.png'));assert pages
 from pypdf import PdfReader
 document=PdfReader(str(pdf));assert len(document.pages)==len(pages)
 for page in document.pages:assert (page.extract_text() or '').strip(),'unexpected empty page'
 result={'pages':len(pages),'word_pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'docx_sha256':hashlib.sha256(a.document.read_bytes()).hexdigest(),'renderer':'Word COM to PDF, packaged render_docx.py PDF rasterization','packaged_LO_failure_retained':True,'all_PNG_exist':True,'visual_review_complete':False}
 (report/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print('RENDERED',json.dumps(result),report)
 return 0
if __name__=='__main__':raise SystemExit(main())
