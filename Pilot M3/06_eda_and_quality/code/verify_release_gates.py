"""Fail closed on unresolved source hazards in the active evidence/scoring release."""
import json
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'00_setup_and_scope/code'))
from pipeline import ROOT,read_jsonl,sha256


def main():
    clean=read_jsonl(ROOT/'05_clean_and_preprocess/outputs/clean_blocks.jsonl')
    chunks=read_jsonl(ROOT/'07_concepts_questions_and_chunks/outputs/accepted_chunks.jsonl')
    roles={r['block_id']:r['role'] for r in read_jsonl(ROOT/'07_concepts_questions_and_chunks/outputs/block_roles.jsonl')}
    corrections=json.loads((ROOT/'05_clean_and_preprocess/config/source_corrections.json').read_text(encoding='utf-8'))
    assert not any('h0ur' in (b['cleaned_text'] or '') or 'h0ur' in (b['cleaned_latex'] or '') for b in clean)
    assert all(roles[bid]=='content' for c in chunks for bid in c['block_ids'])
    assert all(c['review_status']=='approved' and c['retrieval_visibility']=='evidence' and c['token_count']<=400 for c in chunks)
    unresolved={r.get('block_id') for r in corrections['currency_unresolved'] if r.get('block_id')}
    assert not unresolved&{bid for c in chunks for bid in c['block_ids']}
    science=sorted([b for b in clean if b['source_id']=='ncert-en-science-g7-gecu1-r202627-07' and b['page_number']==6],key=lambda b:b['reading_order'])
    texts=[b['cleaned_text'] for b in science]
    assert next(i for i,t in enumerate(texts) if 'process of convection' in t)<next(i for i,t in enumerate(texts) if '7.2.1 Land and Sea Breeze' in t)
    qpath=ROOT/'07_concepts_questions_and_chunks/outputs/ncert_questions.jsonl';apath=ROOT/'07_concepts_questions_and_chunks/outputs/ncert_answers_private.jsonl'
    questions=read_jsonl(qpath);answers=read_jsonl(apath);by_id={a['question_id']:a for a in answers if a['question_id']}
    assert len(questions)==len(read_jsonl(ROOT/'07_concepts_questions_and_chunks/outputs/question_item_reviews.jsonl'))
    assert all(q['review_status']!='pending' for q in questions) and all(a['review_status']!='pending' for a in answers)
    assert any('₹5' in q['prompt'] for q in questions) and any('₹600' in q['prompt'] for q in questions)
    for q in questions:
        if q['scoring_eligible']:
            assert q['review_status']=='approved' and by_id[q['question_id']]['review_status']=='approved'
            assert by_id[q['question_id']]['scoring_eligible'] and not by_id[q['question_id']]['link_needs_review']
    conflict=next(a for a in answers if (a['question_id'] or '').endswith('c9d7d888'))
    assert conflict['review_status']=='quarantined' and not conflict['scoring_eligible']
    report=dict(status='passed',accepted_chunks=len(chunks),questions_dispositioned=len(questions),answers_dispositioned=len(answers),
        scoring_pairs=sum(q['scoring_eligible'] for q in questions),corrected_blocks=len(corrections['blocks']),
        unresolved_currency_positions_excluded=len(corrections['currency_unresolved']),
        source_corrections_sha256=sha256(ROOT/'05_clean_and_preprocess/config/source_corrections.json'),
        question_bank_sha256=sha256(qpath),answer_bank_sha256=sha256(apath),
        limitation='Gate checks integrity and the resolved source boundaries; quarantine is not an approval or a corpus error-rate estimate.')
    (ROOT/'06_eda_and_quality/outputs/release_gate_checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
