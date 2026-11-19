"""Select source-checked pilot checkpoints; keep keys outside the served frontend."""
import csv
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'Ncert work'

# Method scaffolds for the seven source-checked checkpoints; no final results.
HINTS = {
 'ncert-q-c3a756d6b7fec30f': ['Equal sharing divides the total mass into equal parts.', 'Use the total mass and the number of equally sized guavas.', 'Divide the total mass by the number of guavas, then express one share in kilograms.'],
 'ncert-q-28b12a0710579884': ['Each equal packet contains the same share of the total rice.', 'Identify the total mass and the number of equal packets.', 'Divide the total mass by the number of packets and write one packet’s mass as a fraction.'],
 'ncert-q-f4ee9c70712ab0aa': ['Share the total juice equally among the friends.', 'The total amount is three glasses, rather than one glass.', 'Divide the total number of glasses by the number of friends; keep the unit as glasses per friend.'],
 'ncert-q-8aeecb0f03d30df2': ['For the same-sized rotis, flour scales with the number of rotis.', 'Set up (1/4) × (6/12) kg: original flour times the fraction of the original number of rotis.', 'Simplify the scale factor before multiplying the fractions; check that fewer rotis use less flour.'],
 'ncert-q-0fe00fb37afbe158': ['Distance equals distance per litre multiplied by litres used.', 'Set up 16 × (2 + 3/4) km, keeping the whole and fractional parts of the fuel.', 'Convert the mixed number to an improper fraction, or multiply each part by the rate and add the two distances.'],
 'ncert-q-380e8280f8e39c00': ['The friends share only the cake that remains.', 'First set up the remainder as 1 − 4/5; only then share it among three friends.', 'Divide the remainder by three, equivalently multiply it by 1/3; simplify after multiplying.'],
 'ncert-q-cf4f13b6d844b94c': ['A ratio a:b compares a with b, so its fraction is a/b; a percentage expresses that same comparison out of 100.', 'Set up (3/4) × 100%. Keep four as the denominator; adding the ratio terms would describe a different comparison.', 'Divide the first ratio term by the second, then multiply by 100 and attach the percent sign. Check by expressing the same fraction with denominator 100.']
}


def readable(text):
    text = re.sub(r'\\frac\s*\{([^{}]+)\}\s*\{([^{}]+)\}',
                  lambda m: '(' + m[1].replace(' ', '') + ')/(' + m[2].replace(' ', '') + ')', text)
    for old, new in [('\\times', '×'), ('\\div', '÷'), ('\\%', '%'), ('\\operatorname { i s }', 'is')]:
        text = text.replace(old, new)
    return text


def prepare():
    folder=ROOT/'07_concepts_questions_and_chunks/outputs'
    read=lambda name:[json.loads(x) for x in (folder/name).read_text(encoding='utf-8').splitlines()]
    bank=json.loads((folder/'ncert_bank_manifest.json').read_text())
    for name in ['ncert_questions.jsonl','ncert_answers_private.jsonl']:
        if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=bank['artifact_hashes']['07_concepts_questions_and_chunks/outputs/'+name]:
            raise ValueError('Question bank changed; source checks must be repeated')
    questions={x['question_id']:x for x in read('ncert_questions.jsonl')}
    answers={x['question_id']:x for x in read('ncert_answers_private.jsonl') if x['question_id'] and x['answer']}
    sources={x['source_id']:x for x in csv.DictReader((ROOT/'01_download_pdfs/manifests/sources.csv').open(encoding='utf-8'))}
    choices={'fractions':['ncert-q-c3a756d6b7fec30f','ncert-q-28b12a0710579884','ncert-q-f4ee9c70712ab0aa'],
             'fraction_multiplication':['ncert-q-8aeecb0f03d30df2','ncert-q-0fe00fb37afbe158'],
             'fraction_division':['ncert-q-380e8280f8e39c00'],
             'percentages':['ncert-q-cf4f13b6d844b94c']}
    result={}
    for cid,ids in choices.items():
        result[cid]=[]
        for qid in ids:
            q,a=questions[qid],answers[qid];s=sources[q['source_id']]
            if not all(x.get('review_status')=='approved' and x.get('scoring_eligible') is True for x in (q,a)):
                raise ValueError('Checkpoint did not pass the source/key scoring gate')
            if hashlib.sha256((ROOT/s['local_path']).read_bytes()).hexdigest()!=s['sha256']:
                raise ValueError('Source PDF changed')
            values=re.findall(r'\d+/\d+|\d+(?:\.\d+)?',readable(a['answer']))
            if not values:raise ValueError('Official numeric key missing')
            prompt=readable(q['prompt'])
            if cid=='percentages':
                prompt='Convert the following ratio to a percentage: (a) 3 : 4';qid+=':a'
            result[cid].append(dict(id=qid,prompt=prompt,key=values[0],official_answer_text=a['answer'],hint_steps=HINTS[q['question_id']],
                source_id=q['source_id'],source_sha256=s['sha256'],source_block_ids=q['source_block_ids'],
                answer_source_id=a['source_id'],answer_page=a['page_start'],
                citation=dict(url=s['source_url']+'#page='+str(q['page_start']),label=s['book_title']+' PDF p'+str(q['page_start'])),
                review='Codex visual source check 4 November 2026; isolated pilot; percentage subpart a only'))
    (HERE/'data').mkdir(exist_ok=True);(HERE/'logs').mkdir(exist_ok=True)
    (HERE/'data/private_questions.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':prepare()
