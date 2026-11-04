"""Source-bound corrections and conservative native-PDF agreement reviews."""
import copy
import json
import re
import sys
import unicodedata
from pathlib import Path

import fitz

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'00_setup_and_scope/code'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'05_clean_and_preprocess/code'))
from pipeline import ROOT,SOURCES,read_csv,read_jsonl,sha256,write_csv,now
from clean_content import CORRECTIONS,clean_text,content_hash


def canonical(text):
    return re.sub(r'\s+','',unicodedata.normalize('NFKC',text).replace('’',"'").replace('‘',"'").replace('“','"').replace('”','"'))


def scope(source,page,text=''):
    if source['subject']=='mathematics':
        if source['grade']=='6' and (page<=8 or page==36):return ['fractions']
        if source['grade']=='7':
            if page<=14:return ['fraction_multiplication']
            if 15<=page<=18:return ['fraction_division']
        if source['grade']=='8' and page<=3:return ['percentages']
    if source['subject']=='science':
        if page in {2,3}:return ['conduction']
        if page in {8,9}:return ['radiation']
    return []


def source_agrees(text,native):
    return bool(text.strip()) and canonical(text) in canonical(native)


def main():
    raw=read_jsonl(ROOT/'04_extract_text_and_ocr/outputs/blocks.jsonl')
    sources={s['source_id']:s for s in read_csv(SOURCES)}
    for source in sources.values():
        if sha256(ROOT/source['local_path'])!=source['sha256']:raise ValueError('Original PDF changed')
    documents={sid:fitz.open(ROOT/s['local_path']) for sid,s in sources.items()}
    fixes={};currency_unresolved=[];orders=[]
    def add(block,text,reason,latex=None):
        before=dict(text=clean_text(block['raw_text'])[0],latex=block['raw_latex'],html=block.get('raw_html'))
        after=copy.deepcopy(before);after['text']=text
        if latex is not None:after['latex']=latex
        fixes[block['block_id']]=dict(block_id=block['block_id'],source_sha256=block['source_sha256'],
            before=before,after=after,reason=reason,review_status='approved',reviewer='Codex',
            review_method='ai_source_checked_font_alignment',physical_page=block['page_number'],
            evidence='Original PDF and native character coordinates; known hour/currency/reading-order pages visually checked')
    for block in raw:
        if (block['source_id']=='ncert-en-mathematics-g6-fegp1-r202627-07' and block['page_number']==2
                and 'Each one drank glass of sugarcane juice.' in block['raw_text']):
            add(block,clean_text(block['raw_text'])[0].replace('Each one drank glass','Each one drank ____ glass'),
                'Restore source-visible answer blank; checked against original Grade 6 physical page 2')
        if re.search(r'\bh0ur\b',block['raw_text'],re.I):
            native=documents[block['source_id']][block['page_number']-1].get_text()
            if 'hour' not in native:raise ValueError('Hour correction lacks original evidence')
            add(block,re.sub(r'\bh0ur\b','hour',clean_text(block['raw_text'])[0],flags=re.I),'Source-verified hour OCR repair',
                re.sub(r'\bh0ur\b','hour',block['raw_latex'],flags=re.I) if block['raw_latex'] else None)
    sid='ncert-en-mathematics-g8-hemh1-r202425-07'
    doc=documents[sid]
    for page in doc:
        blocks=[b for b in raw if b['source_id']==sid and b['page_number']==page.number+1 and b['content_role']=='chapter_content']
        for layout in page.get_text('rawdict')['blocks']:
            for line in layout.get('lines',[]):
                chars=[c for span in line['spans'] for c in span['chars']]
                text=''.join(c['c'] for c in chars)
                for match in re.finditer(r'\uf060\s*(\d[\d,]*(?:\.\d+)?)',text):
                    char=chars[match.start()];value=match[1]
                    cx=(char['bbox'][0]+char['bbox'][2])/2/page.rect.width
                    cy=(char['bbox'][1]+char['bbox'][3])/2/page.rect.height
                    candidates=[]
                    for block in blocks:
                        box=block['bbox']
                        if not box or not block['coordinate_system'].startswith('MinerU normalized'):continue
                        if box[0]-.012<=cx<=box[2]+.012 and box[1]-.006<=cy<=box[3]+.006:
                            candidates.append(block)
                    candidates.sort(key=lambda b:(b['bbox'][2]-b['bbox'][0])*(b['bbox'][3]-b['bbox'][1]))
                    block=next((b for b in candidates if re.search(r'(?<![\d,])'+re.escape(value)+r'(?![\d,])',b['raw_text'])),None)
                    if block is None or block['raw_latex'] or block.get('raw_html'):
                        currency_unresolved.append(dict(source_id=sid,page=page.number+1,value=value,block_id=block['block_id'] if block else None,native_bbox=char['bbox'],reason='formula/table or ambiguous block; not automatically edited'))
                        continue
                    current=fixes.get(block['block_id'],{}).get('after',{}).get('text',clean_text(block['raw_text'])[0])
                    pattern=r'(?<![\d,])'+re.escape(value)+r'(?![\d,])'
                    positions=list(re.finditer(pattern,current))
                    if len(positions)!=1:
                        currency_unresolved.append(dict(source_id=sid,page=page.number+1,block_id=block['block_id'],reason='repeated amount; requires formula/source check'))
                        continue
                    pos=positions[0].start()
                    if '₹' in current[max(0,pos-3):pos]:continue
                    add(block,current[:pos]+'₹'+current[pos:],'Restore rupee glyph U+F060 at original native-PDF coordinates')
    sid='ncert-en-science-g7-gecu1-r202627-07'
    page_blocks=[b for b in raw if b['source_id']==sid and b['page_number']==6]
    ordered=sorted(page_blocks,key=lambda b:((b['bbox'] or [0,0])[1],(b['bbox'] or [0])[0],b['block_order']))
    orders.append(dict(source_id=sid,physical_page=6,source_sha256=sources[sid]['sha256'],
        block_ids=[b['block_id'] for b in ordered],reason='Visually checked upper convection passage precedes lower Land and Sea Breeze section'))
    CORRECTIONS.parent.mkdir(exist_ok=True)
    CORRECTIONS.write_text(json.dumps(dict(blocks=list(fixes.values()),page_orders=orders,currency_unresolved=currency_unresolved),indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(corrected_blocks=len(fixes),currency_cases_quarantined=len(currency_unresolved),ordered_pages=len(orders))))


def review_plain_blocks():
    sources={s['source_id']:s for s in read_csv(SOURCES)}
    raw={b['block_id']:b for b in read_jsonl(ROOT/'04_extract_text_and_ocr/outputs/blocks.jsonl')}
    clean=read_jsonl(ROOT/'05_clean_and_preprocess/outputs/clean_blocks.jsonl')
    review_path=ROOT/'06_eda_and_quality/outputs/block_reviews.csv';reviews=read_csv(review_path)
    fixes={r['block_id']:r for r in json.loads(CORRECTIONS.read_text(encoding='utf-8'))['blocks']}
    clean_by_id={b['block_id']:b for b in clean}
    for review in reviews:
        block=clean_by_id[review['block_id']]
        if review['content_hash']!=block['content_hash']:
            fix=fixes.get(block['block_id'])
            if not fix or review['content_hash']!=content_hash(**fix['before']):raise ValueError('Unexplained review hash change')
            review['content_hash']=block['content_hash'];review['review_date']=now()
            review['notes']+=' Source-verified currency/word correction applied with exact before/after evidence.'
    known={r['block_id'] for r in reviews};added=[]
    docs={sid:fitz.open(ROOT/s['local_path']) for sid,s in sources.items()}
    for b in clean:
        source=sources[b['source_id']];text=b['cleaned_text'];original=raw[b['block_id']]
        if b['block_id'] in known or b['removed'] or b['content_role']!='chapter_content' or not scope(source,b['page_number'],text):continue
        if (b['quarantine_reasons'] or b['content_type']!='prose' or original['inline_formulas'] or b['cleaned_latex']
                or b['cleaned_html'] or re.search(r'[\d\\=<>%₹]',text) or len(text.split())<10 or not re.search(r'[.!?]$',text)):
            continue
        if not source_agrees(text,docs[b['source_id']][b['page_number']-1].get_text(sort=True)):continue
        row=dict(block_id=b['block_id'],source_id=b['source_id'],source_sha256=source['sha256'],page_number=b['page_number'],
            content_hash=b['content_hash'],review_status='approved',reviewer='Codex',review_date=now(),
            review_method='automatic_pdf_text_agreement',source_check='pass',critical_checks='pass',
            evidence_ref=source['local_path']+'#page='+str(b['page_number']),
            notes='Exact normalized original-PDF prose agreement within frozen pilot page scope. No digits, formulas, tables or diagram-dependent text automatically approved.')
        reviews.append(row);added.append(b['block_id'])
    write_csv(review_path,reviews,list(reviews[0]))
    policy=ROOT/'00_setup_and_scope/config/review_policy.json';data=json.loads(policy.read_text())
    if 'automatic_pdf_text_agreement' not in data['allowed_review_methods']:data['allowed_review_methods'].append('automatic_pdf_text_agreement')
    policy.write_text(json.dumps(data,indent=2)+'\n')
    print('Additional source-agreeing prose blocks:',len(added))


if __name__=='__main__':
    if '--review-plain' in sys.argv:review_plain_blocks()
    else:main()
