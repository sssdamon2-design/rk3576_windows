"""Post-Word roundtrip and formatting validation; visual ledger is a separate input."""
from pathlib import Path
import argparse,hashlib,json,re
from docx import Document
from docx.oxml.ns import qn
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--render',type=Path,required=True);p.add_argument('--ledger',type=Path,required=True);a=p.parse_args()
 docx=ROOT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.docx';md=ROOT/'docs/RK3576_STAGE5_ENGINEERING_MANUAL.md';doc=Document(docx)
 expected=[];fence=False
 for line in md.read_text(encoding='utf-8').splitlines():
  if line.startswith('```'):fence=not fence
  elif fence:expected.append(line)
 actual=[p.text for p in doc.paragraphs if p.style.name=='Source Code'];assert expected==actual,'Word Save changed source code text'
 normal=doc.styles['Normal'];family=normal.element.get_or_add_rPr().find(qn('w:rFonts'));ind=normal.element.get_or_add_pPr().find(qn('w:ind'))
 assert family.get(qn('w:ascii'))=='Times New Roman' and family.get(qn('w:eastAsia')) in {'楷体','KaiTi'}
 assert normal.font.size.pt==12 and normal.paragraph_format.line_spacing==1.5 and ind.get(qn('w:firstLineChars'))=='200'
 def inherited(style,getter):
  while style is not None:
   value=getter(style)
   if value is not None:return value
   style=style.base_style
  return None
 def font_value(style,key):
  family=style.element.get_or_add_rPr().find(qn('w:rFonts'))
  return family.get(qn('w:'+key)) if family is not None else None
 for name in ['Title' ,'Heading 1','Heading 2','Heading 3','Heading 4','Heading 5','Heading 6']:
  style=doc.styles[name];assert inherited(style,lambda x:x.font.bold) and inherited(style,lambda x:x.font.size).pt==12
  family=style.element.get_or_add_rPr().find(qn('w:rFonts'));assert inherited(style,lambda x:font_value(x,'ascii'))=='Times New Roman' and inherited(style,lambda x:font_value(x,'eastAsia')) in {'楷体','KaiTi'}
  assert family is None or not any('Theme' in key for key in family.attrib)
  color=style.element.get_or_add_rPr().find(qn('w:color'));assert color is None or color.get(qn('w:val'))=='000000'
 render=json.loads((a.render/'result.json').read_text());ledger=json.loads(a.ledger.read_text());pages=render['pages'];ids=sorted(set(ledger['inspected_pages']));assert ids==list(range(1,pages+1)),'not all pages have been visually inspected'
 assert ledger['clean'] and ledger['render_folder']==str(a.render.as_posix())
 assert all(ledger['page_sha256'].get(str(i))==hashlib.sha256((a.render/'pages'/f'page-{i}.png').read_bytes()).hexdigest() for i in ids),'visual ledger PNG hash mismatch'
 digest=hashlib.sha256(docx.read_bytes()).hexdigest();assert digest==render['docx_sha256'],'render does not match current DOCX'
 manifest=json.loads((ROOT/'reports/stage5_05_local/manual_source_manifest.json').read_text(encoding='utf-8'));assert all(hashlib.sha256((ROOT/r['file']).read_bytes()).hexdigest()==r['file_sha256'] for r in manifest)
 result={'all_pages_inspected':True,'clean':True,'pages':pages,'inspected_pages':ids,'docx_sha256':digest,'markdown_sha256':hashlib.sha256(md.read_bytes()).hexdigest(),'all_source_code_lines_preserved_after_Word_Save':True,'source_code_lines':len(actual),'body_Chinese':'楷体12pt','body_Latin':'Times New Roman12pt','line_spacing':1.5,'first_line_chars':2,'headings_bold_black':True,'render':str(a.render.as_posix()),'limitations':'PNG visual review plus OOXML checks; does not validate hardware outcomes'}
 (ROOT/'reports/stage5_05_local/document_QA.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('DOCUMENT_QA_PASSED',pages,'pages;',len(actual),'source lines')
if __name__=='__main__':main()
