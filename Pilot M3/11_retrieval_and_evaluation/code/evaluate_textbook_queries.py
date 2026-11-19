"""Frozen publisher-question challenge; concept relevance, not independent learner gold."""
import hashlib
import json
import statistics
from collections import Counter
from retrieve import ROOT, Retriever, resolve
from pipeline import read_jsonl, run_record, sha256, write_jsonl

PHASE=ROOT/'11_retrieval_and_evaluation'
BANK=ROOT/'07_concepts_questions_and_chunks/outputs/ncert_questions.jsonl'


def freeze_protocol():
    path=PHASE/'evaluation/textbook_protocol_v2.json'
    if path.exists():
        # Frozen: the 83 publisher questions, labels and splits are fixed text, independent of later bank or corpus rebuilds.
        return path,json.loads(path.read_text(encoding='utf-8'))
    questions=[q for q in read_jsonl(BANK) if q['provenance']=='ncert_extracted']
    assert len(questions)==83
    supported={**{i:['fractions'] for i in (0,1,2)},
        **{i:['fraction_multiplication'] for i in (33,34,35,36,41,42,46,49)},
        45:['fraction_division'],51:['fraction_division'],
        **{i:['percentages'] for i in range(57,63)},79:['conduction']}
    partial={4:['fractions'],5:['fractions'],16:['fractions'],17:['fractions'],18:['fractions'],
        37:['fraction_multiplication'],38:['fraction_multiplication'],39:['fraction_multiplication'],
        40:['fraction_multiplication'],43:['fraction_multiplication'],47:['fraction_division'],
        48:['fraction_multiplication'],52:['fraction_multiplication'],55:['fraction_multiplication'],
        65:['percentages'],66:['percentages'],77:['conduction'],78:['conduction','radiation']}
    damaged={6,7,11,12,15,27,28,29,44,56,76,82}
    cases=[]
    for i,q in enumerate(questions):
        concepts=supported.get(i,partial.get(i,[]))
        status='supported' if i in supported else 'partial' if i in partial else 'outside_objectives'
        if q['requires_diagram']:status='needs_visual'
        if i in damaged:status='extraction_or_boundary_challenge'
        group=q['source_id']+'|'+q['section']+'|p'+str(q['page_start'])
        split='calibration' if int(hashlib.sha256(group.encode()).hexdigest()[:8],16)%3==0 else 'held_out'
        cases.append(dict(question_id=q['question_id'],text=q['instruction']+'\n'+q['prompt'],
            source_id=q['source_id'],source_sha256=q['source_sha256'],page=q['page_start'],group=group,
            split=split,relevance=status,relevant_concept_ids=concepts))
    protocol=dict(bank_sha256=sha256(BANK),chunks_sha256=sha256(ROOT/'07_concepts_questions_and_chunks/outputs/accepted_chunks.jsonl'),
        annotation='Codex objective-based judgment before rankings; original publisher wording, no synthetic paraphrases',
        corpus_amendment='Standalone passage checks after initial 52-chunk run; original labels/splits unchanged; held-out questions reused',
        split='source + section + physical page groups; all same-page subparts kept together',
        primary='Fully supported text questions only; all other cases test abstention',
        thresholds=[.60,.65,.70,.75,.80,.85,.90],margins=[0,.02,.05,.08,.10],
        criterion='+1 correct supported acceptance or challenge abstention; -2 wrong acceptance; zero positive abstention',
        cases=cases)
    if path.exists():
        if json.loads(path.read_text(encoding='utf-8'))!=protocol:raise ValueError('Frozen textbook protocol changed')
    else:path.write_text(json.dumps(protocol,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return path,protocol


def concept_measures(ranking,relevant,chunks):
    found=[bool(set(chunks[c]['concept_ids'])&set(relevant)) for c,_ in ranking[:5]]
    return dict(concept_hit_at_1=int(bool(found and found[0])),concept_hit_at_5=int(any(found)),
        concept_mrr_at_5=next((1/(i+1) for i,x in enumerate(found) if x),0))


def route_score(rows,chunks,threshold,margin):
    value=0
    for row in rows:
        d=resolve(row['rankings']['BGE_cosine'],chunks,threshold,margin)
        accepted=d['status']=='resolved'
        correct=row['relevance']=='supported' and d['concept_id'] in row['relevant_concept_ids']
        value+=1 if correct or not accepted and row['relevance']!='supported' else -2 if accepted else 0
    return value


def main():
    path,protocol=freeze_protocol() # Freeze all annotations before loading/ranking.
    with run_record('11_retrieval_and_evaluation',[path,BANK,ROOT/'10_embeddings_and_database/outputs/embedding_manifest.json']) as run:
        engine=Retriever()
        try:
            groups=[{q['group'] for q in protocol['cases'] if q['split']==s} for s in ('calibration','held_out')]
            assert not groups[0]&groups[1]
            rows=[]
            for case in protocol['cases']:
                try:
                    ranking=engine.rank(case['text'],engine.query_vector(case['text']))
                    rejected=False
                except ValueError as error:
                    if 'oversize input' not in str(error):raise
                    ranking={m:[] for m in ('BM25','BGE_cosine','RRF_BM25_BGE')}
                    rejected=True
                rows.append({**case,'rankings':ranking,'oversize_rejected_without_truncation':rejected})
            calibration=[r for r in rows if r['split']=='calibration']
            selected=max(((route_score(calibration,engine.chunks,t,m),t,m)
                          for t in protocol['thresholds'] for m in protocol['margins']))
            _,threshold,margin=selected
            metrics=[]
            for split in ('calibration','held_out'):
                subset=[r for r in rows if r['split']==split]
                positive=[r for r in subset if r['relevance']=='supported']
                for method in ('BM25','BGE_cosine','RRF_BM25_BGE'):
                    values=[concept_measures(r['rankings'][method],r['relevant_concept_ids'],engine.chunks) for r in positive]
                    metrics.append(dict(split=split,method=method,fully_supported_cases=len(positive),
                        **{k:statistics.mean(v[k] for v in values) for k in values[0]}))
                for row in subset:row['resolution']=resolve(row['rankings']['BGE_cosine'],engine.chunks,threshold,margin)
            routing=[]
            for split in ('calibration','held_out'):
                subset=[r for r in rows if r['split']==split]
                positives=[r for r in subset if r['relevance']=='supported']
                challenges=[r for r in subset if r['relevance']!='supported']
                routing.append(dict(split=split,cases=len(subset),supported=len(positives),challenges=len(challenges),
                    correct_supported_acceptances=sum(r['resolution']['concept_id'] in r['relevant_concept_ids'] for r in positives),
                    supported_abstentions=sum(r['resolution']['status']!='resolved' for r in positives),
                    challenge_false_acceptances=sum(r['resolution']['status']=='resolved' for r in challenges)))
            policy=dict(corpus_version=engine.version,threshold=threshold,margin=margin,
                automatic_routing_enabled=False,required_mode='User-selected single concept; free-form routing failed positive coverage',
                calibration_split='textbook protocol calibration groups only',protocol_sha256=sha256(path),
                criterion=protocol['criterion'],tie_rule='higher threshold then higher margin',
                confidence='Heuristic abstention; not a probability or proof of scope',run_id=run['run_id'])
            result=dict(run_id=run['run_id'],corpus_version=engine.version,chunks=len(engine.chunks),queries=len(rows),
                protocol_sha256=sha256(path),relevance_counts=dict(Counter(r['relevance'] for r in rows)),
                oversize_inputs=sum(r['oversize_rejected_without_truncation'] for r in rows),
                metrics=metrics,routing=routing,policy=policy,
                limitations=['Publisher questions are authentic but are not independent learner queries',
                    'Codex assigned concept relevance; no independent gold and only six objectives',
                    'Concept Hit@5 is not document Recall@5; redundant passages can make it easy',
                    'Partial/visual/boundary cases require abstention, even when a related concept is found',
                    'Corpus pruned after initial 52-chunk run; held-out questions reused, not a fresh independent test'])
            out=PHASE/'outputs'
            write_jsonl(out/'textbook_retrieval_rows.jsonl',rows)
            for name,value in [('textbook_retrieval_metrics.json',result),('resolution_policy.json',policy)]:
                (out/name).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');run['outputs'].append(out/name)
            run['outputs'].append(out/'textbook_retrieval_rows.jsonl');run['counts']=dict(queries=len(rows),chunks=len(engine.chunks),routing=routing)
            print(json.dumps(result),flush=True)
        finally:engine.close()


if __name__=='__main__':main()
