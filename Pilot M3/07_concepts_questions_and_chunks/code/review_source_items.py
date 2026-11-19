"""Explicit item dispositions; only checked source/key pairs become scoring eligible."""
import hashlib
import json
import re
import unicodedata
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'00_setup_and_scope/code'))
from pipeline import ROOT,SOURCES,read_csv,read_jsonl,sha256,write_jsonl
from extract_ncert_questions import needs_figure,text_sim

PHASE=ROOT/'07_concepts_questions_and_chunks'
CHECKS=PHASE/'config/item_source_checks.json'


def digest(text):return hashlib.sha256(text.encode()).hexdigest()


def validate_pair(question,answer,raw,sources):
    if question['source_sha256']!=sources[question['source_id']]['sha256']:raise ValueError('Question source changed')
    for bid in question['source_block_ids']:
        if bid not in raw or raw[bid]['source_id']!=question['source_id']:raise ValueError('Question lineage failed')
    if answer:
        if answer['source_sha256']!=sources[answer['source_id']]['sha256']:raise ValueError('Answer source changed')
        if not answer['source_block_ids'] or any(b not in raw or raw[b]['content_role']!='private_answer' or raw[b]['source_id']!=answer['source_id'] for b in answer['source_block_ids']):
            raise ValueError('Answer is not bound to private official solution blocks')
        if question['source_id'].endswith('hemh1-r202425-07'):
            if answer['exercise_label']!=question['section'] or answer['key_number']!=question['number']:
                raise ValueError('Exercise/number link mismatch')


GROUPED=re.compile(r"\b(above|previous|preceding|earlier question|as before|in question \d|the same way)\b",re.I)
PRIVATE_USE=re.compile("[-�]")
PART=re.compile(r"(?:^|[\s:])\(?(?:[a-h]|i{1,3}|iv|v|vi)[.)]\s")


def numbers(text):
    t=unicodedata.normalize("NFKC",text or "")
    t=re.sub(r"(?<=\d)\s+(?=\d)","",re.sub(r"\\[a-zA-Z]+|[{}$_^*\\]"," ",t))
    return Counter(re.findall(r"\d+",t))


def multi_part(prompt):
    return len(PART.findall(prompt))>=2


def auto_reasons(q,a):
    """Automatic replacement for per-item visual checks; any hit holds the item back with a stated reason."""
    reasons=[]
    if q.get('requires_diagram'):reasons.append('needs a figure')
    if GROUPED.search(q['prompt']):reasons.append('depends on another question')
    if PRIVATE_USE.search(q['prompt']) or q['prompt'].count('{')!=q['prompt'].count('}'):reasons.append('unreadable symbols or broken maths markup')
    if a and a.get('key_question','').strip():
        missing=numbers(a['key_question'])-numbers(q['prompt'])
        if missing:reasons.append('chapter text is missing numbers the official key shows ('+', '.join(sorted(missing))+')')
    return reasons


def audit_bank():
    out=PHASE/'outputs';questions=read_jsonl(out/'ncert_questions.jsonl');answers=read_jsonl(out/'ncert_answers_private.jsonl')
    checks={r['question_id']:r for r in json.loads(CHECKS.read_text(encoding='utf-8'))}
    sources={s['source_id']:s for s in read_csv(SOURCES)}
    for s in sources.values():
        if sha256(ROOT/s['local_path'])!=s['sha256']:raise ValueError('Original PDF changed')
    raw={b['block_id']:b for b in read_jsonl(ROOT/'04_extract_text_and_ocr/outputs/blocks.jsonl')}
    linked={a['question_id']:a for a in answers if a['question_id'] and a['answer']}
    decisions=[]
    for q in questions:
        a=linked.get(q['question_id']);validate_pair(q,a,raw,sources)
        row=checks.get(q['question_id']);q['scoring_eligible']=False
        if row:
            if row['question_sha256']!=digest(q['prompt']) or row['source_sha256']!=q['source_sha256']:
                raise ValueError('Question decision belongs to changed text')
            if not a or row['answer_sha256']!=digest(a['answer']) or row['answer_source_sha256']!=a['source_sha256']:
                raise ValueError('Answer decision belongs to changed text')
            q.update(review_status='approved',reviewer='Codex',review_method='ai_visual_source_check',
                     source_check='pass',review_evidence=row['evidence'])
            a.update(review_status=row['answer_status'],link_needs_review=False,reviewer='Codex',
                     review_method='ai_visual_source_check',review_evidence=row['evidence'],source_check='pass')
            if 'answer_after' in row:
                a['transcription_before']=a['answer'];a['answer']=row['answer_after']
                a['transcription_correction_reason']=row['answer_correction_reason']
            a['review_reason']=row.get('reason','Source question and complete official key checked against rendered originals')
            q['scoring_mode']=row.get('scoring_mode','source_key_rubric')
            q['scoring_eligible']=a['review_status']=='approved' and q['scoring_mode']!='clock_time_rubric'
            a['scoring_eligible']=q['scoring_eligible']
        else:
            reasons=auto_reasons(q,a)
            if reasons and all(r.startswith('chapter text is missing numbers') for r in reasons) and text_sim(q['prompt'],a['key_question'])<0.75:
                # Different wording and different numbers: the key belongs to another question. Unlink it, keep the question.
                a.update(question_id=None,match_method='rejected_number_mismatch');a=None
                q.update(answer_available=False,answer_source=None)
                reasons=auto_reasons(q,a)
            if reasons and all(r.startswith('chapter text is missing numbers') for r in reasons):
                # Same question, but extraction lost digits in the chapter copy; NCERT's own restatement is complete.
                restated=a['key_question'].strip()
                if not auto_reasons({**q,'prompt':restated,'requires_diagram':needs_figure(restated)},a):
                    q.update(prompt_from_chapter=q['prompt'],prompt=restated,text_source='official_key_restatement',
                             text_repair_reason=reasons[0])
                    reasons=[]
            if reasons:
                q.update(review_status='quarantined',source_check='not_passed',review_reason='; '.join(reasons))
                if a:
                    a.update(review_status='quarantined',link_needs_review=True,scoring_eligible=False,
                             review_reason='Linked question held back: '+'; '.join(reasons))
            else:
                q.update(review_status='approved',reviewer='pipeline',review_method='automatic_rule_gate',source_check='pass',
                         review_reason='Chapter lineage, transcription and key-agreement rules passed'+('; question text from official key restatement' if q.get('text_source') else ''))
                parts=multi_part(q['prompt'])
                usable_key=bool(a and a['answer'] and not a['answer_has_image'])
                q['scoring_mode']='source_key_rubric'
                q['scoring_eligible']=usable_key and not parts
                if a:
                    a.update(review_status='approved' if a['answer'] and not a['answer_has_image'] else 'quarantined',
                             reviewer='pipeline',review_method='automatic_rule_gate',link_needs_review=False,
                             scoring_eligible=q['scoring_eligible'],
                             review_reason='Key linked by '+str(a.get('match_method'))+('; multi-part, graded per part later' if parts else '')
                             if a['answer'] and not a['answer_has_image'] else 'Image-only or empty key; cannot be graded automatically')
                if not usable_key:q['review_reason']+='; practice prompt (no gradable NCERT key)'
                elif parts:q['review_reason']+='; multi-part, not auto-graded yet'
        decisions.append(dict(question_id=q['question_id'],review_status=q['review_status'],
            scoring_eligible=q['scoring_eligible'],answer_link_status=a['review_status'] if a else 'no_official_answer',
            source_id=q['source_id'],physical_pages=[q['page_start'],q['page_end']],
            reason=q.get('review_reason',a.get('review_reason','Source checked') if a else 'Source checked'),
            source_sha256=q['source_sha256'],question_text_sha256=digest(q['prompt'])))
    for a in answers:
        if not a['question_id'] and a['source_id'].endswith('-an'):
            a.update(review_status='outside_pilot',scoring_eligible=False,link_needs_review=False,
                     review_reason='Key belongs to a chapter outside this release')
        elif not a['question_id']:
            a.update(review_status='unmatched_key',scoring_eligible=False,link_needs_review=False,
                     review_reason='Key could not be matched to chapter text (merged sub-items or skipped figure question); not turned into a question')
        elif not a['answer']:
            a.update(review_status='quarantined',scoring_eligible=False,review_reason='Missing text key; image/empty answer cannot be automatically scored')
    write_jsonl(out/'ncert_questions.jsonl',questions);write_jsonl(out/'ncert_answers_private.jsonl',answers)
    write_jsonl(out/'question_item_reviews.jsonl',decisions)
    report=dict(questions_checked=len(questions),answer_items_checked=len(answers),
        question_statuses=dict(Counter(q['review_status'] for q in questions)),
        answer_statuses=dict(Counter(a['review_status'] for a in answers)),
        scoring_pairs=sum(q['scoring_eligible'] for q in questions),pending_items=0,
        decisions_sha256=sha256(CHECKS),invented_gold_answers=0,
        source_key_conflicts=[q['question_id'] for q in questions if q['question_id'] in checks and not q['scoring_eligible']],
        approved_practice_only=sum(q['review_status']=='approved' and not q['scoring_eligible'] for q in questions),
        quarantine_reasons=dict(Counter(q['review_reason'].split(' (')[0] for q in questions if q['review_status']=='quarantined')),
        review_methods=dict(Counter(q.get('review_method','none') for q in questions)),
        limitation='Every item has a disposition. Automatic rules (lineage, figure, grouped-question, markup and key-number agreement) replace per-item visual checks for new items; earlier visually checked items keep their decisions. Quarantine means a rule failed, with the reason stated.')
    (out/'item_review_summary.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':print(json.dumps(audit_bank(),indent=2))
