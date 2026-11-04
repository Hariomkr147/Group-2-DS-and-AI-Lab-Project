"""Local-only, group-separated diagnostic retrieval; native and graph namespaces stay distinct."""
import hashlib
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'00_setup_and_scope/code'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'10_embeddings_and_database/code'))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'11_retrieval_and_evaluation/code'))
from pipeline import ROOT,read_csv,read_jsonl,sha256,run_record,write_jsonl
from embed_chunks import QUERY_PREFIX,load_encoder,encode
from retrieve import bm25
from evaluate_diagnostics import normalized_text

PHASE=ROOT/'09_skill_misconception_and_scope_mapping'


def stable(rows):
    return sorted(rows,key=lambda x:hashlib.sha256(x['example_id'].encode()).hexdigest())


def one_per_group(rows,limit):
    chosen=[];seen=set()
    for row in stable(rows):
        if row['problem_group_id'] in seen:continue
        chosen.append(row);seen.add(row['problem_group_id'])
        if len(chosen)==limit:break
    return chosen


def metrics(rankings,targets):
    covered=[(rank,target) for rank,target in zip(rankings,targets) if target]
    ranks=[next((i+1 for i,x in enumerate(rank[:5]) if x in target),None) for rank,target in covered]
    return dict(cases=len(targets),covered=len(covered),coverage=len(covered)/len(targets),
                recall_at_5=sum(x is not None for x in ranks)/len(ranks) if ranks else None,
                mrr_at_5=sum(1/x if x else 0 for x in ranks)/len(ranks) if ranks else None,
                top1_accuracy=sum(x==1 for x in ranks)/len(ranks) if ranks else None)


def main():
    examples_path=PHASE/'outputs/diagnostic_examples.jsonl'
    old_protocol=PHASE/'evaluation/diagnostic_protocol.json'
    manifest_path=PHASE/'outputs/competition_dataset_manifest.json'
    with run_record('09_skill_misconception_and_scope_mapping',[examples_path,old_protocol,manifest_path]) as run:
        examples=read_jsonl(examples_path)
        old_ids=set(json.loads(old_protocol.read_text())['selected_example_ids'])
        exposed={r['problem_group_id'] for r in examples if r['example_id'] in old_ids and r['split']=='held_out_by_question'}
        eedi=[r for r in examples if r['source_dataset'].startswith('eedi-')]
        train=one_per_group([r for r in eedi if r['split']=='calibration'],200)
        test=one_per_group([r for r in eedi if r['split']=='held_out_by_question' and r['problem_group_id'] not in exposed],300)
        assert len(test)==300 and not {r['problem_group_id'] for r in train}&{r['problem_group_id'] for r in test}
        datasets=json.loads(manifest_path.read_text())['datasets'];dataset=next(d for d in datasets if d['competition'].startswith('eedi-'))
        mapping=read_csv(ROOT/dataset['files']['misconception_mapping.csv']['path'])
        original={r['QuestionId']:r for r in read_csv(ROOT/dataset['files']['train.csv']['path'])}
        ids=[r['MisconceptionId'] for r in mapping];labels=[r['MisconceptionName'] for r in mapping]
        graph=read_jsonl(PHASE/'outputs/misconceptions.jsonl');graph_ids=[r['misconception_id'] for r in graph]
        graph_by_text=defaultdict(set)
        for r in graph:graph_by_text[normalized_text(r['text'])].add(r['misconception_id'])
        protocol=dict(source_sha256=sha256(examples_path),native_labels_sha256=sha256(ROOT/dataset['files']['misconception_mapping.csv']['path']),
            calibration_ids=[r['example_id'] for r in train],test_ids=[r['example_id'] for r in test],
            group_overlap=0,previously_exposed_test_groups_excluded=len(exposed),
            native_namespace='Original Kaggle Eedi misconception IDs; 2587 labels',graph_namespace='Eedi graph original IDs; exact label-text bridge only',
            model='Pinned BGE-small CLS/L2; no generative model',
            query='Original question + wrong answer; alternative adds publisher construct and correct answer contrast',
            tuning='Calibration only, leave each calibration question group out of its own prototype index',
            grid=dict(prototype_boost=[0,.1,.25,.5,1],bm25_boost=[0,.05,.1,.2]),
            restricted_data='Local only; no competition records sent to a hosted API',frozen_before_scoring=True)
        protocol_path=PHASE/'evaluation/diagnostic_improvement_protocol.json'
        if protocol_path.exists() and json.loads(protocol_path.read_text())!=protocol:raise ValueError('Frozen protocol changed')
        protocol_path.write_text(json.dumps(protocol,indent=2)+'\n')
        tokenizer,model=load_encoder()
        cases=train+test
        plain=[];contrast=[];eligible=[]
        for case in cases:
            row=original[case['source_question_id']]
            a=QUERY_PREFIX+'Question: '+case['question']+'\nStudent answer: '+case['student_answer']
            b=QUERY_PREFIX+row['ConstructName']+'. Correct answer: '+row['Answer'+row['CorrectAnswer']+'Text']+'. Incorrect answer: '+case['student_answer']+'. Question: '+case['question']
            if max(len(tokenizer.encode(x,truncation=False)) for x in (a,b))>512:continue
            plain.append(a);contrast.append(b);eligible.append(case)
        print('Encoding native catalogue and',len(eligible),'original cases',flush=True)
        vlabels=encode(labels,tokenizer,model)
        vplain=encode(plain,tokenizer,model);vcontrast=encode(contrast,tokenizer,model)
        ntrain=sum(c['split']=='calibration' for c in eligible)
        assert eligible[:ntrain]==train[:ntrain] or all(c['split']=='calibration' for c in eligible[:ntrain])
        label_index={x:i for i,x in enumerate(ids)}
        proto_labels=[label_index[c['gold_original_misconception_id']] for c in eligible[:ntrain]]
        sparse=[]
        for i,c in enumerate(eligible):
            scores=np.array(bm25(original[c['source_question_id']]['ConstructName']+' '+c['question']+' '+c['student_answer'],labels),dtype='float32')
            sparse.append(scores/max(float(scores.max()),1e-6))
        sparse=np.array(sparse)
        targets=[{c['gold_original_misconception_id']} for c in eligible]
        options=[]
        for view,v in [('plain',vplain),('contrast',vcontrast)]:
            dense=v@vlabels.T;similarities=v@v[:ntrain].T
            prototypes=np.zeros_like(dense)
            for i,c in enumerate(eligible):
                order=np.argsort(-similarities[i])
                for j in order[:40]:
                    if eligible[j]['problem_group_id']==c['problem_group_id']:continue
                    k=proto_labels[j]
                    prototypes[i,k]=max(prototypes[i,k],max(0,float(similarities[i,j])-.6))
            for beta in protocol['grid']['prototype_boost']:
                for gamma in protocol['grid']['bm25_boost']:
                    scores=dense+beta*prototypes+gamma*sparse
                    rankings=[[ids[j] for j in np.argsort(-s,kind='stable')[:5]] for s in scores[:ntrain]]
                    m=metrics(rankings,targets[:ntrain]);options.append((m['recall_at_5'],m['mrr_at_5'],view,beta,gamma,scores))
        best=max(options,key=lambda x:(x[0],x[1],-x[3],-x[4]))
        baseline=vplain@vlabels.T
        rankings=lambda matrix:[[ids[j] for j in np.argsort(-s,kind='stable')[:5]] for s in matrix]
        baseline_rank=rankings(baseline);improved_rank=rankings(best[-1])
        gm=json.loads((PHASE/'outputs/eedi_catalogue_manifest.json').read_text())
        gvec=np.load(ROOT/gm['vector_path'],allow_pickle=False)
        graph_rank=[[graph_ids[j] for j in np.argsort(-s,kind='stable')[:5]] for s in vplain@gvec.T]
        graph_targets=[graph_by_text.get(normalized_text(c['gold_misconception_text']),set()) for c in eligible]
        results=[]
        for i,c in enumerate(eligible):
            results.append(dict(example_id=c['example_id'],problem_group_id=c['problem_group_id'],split=c['split'],
                                native_gold=sorted(targets[i]),native_baseline_top5=baseline_rank[i],native_improved_top5=improved_rank[i],
                                graph_gold=sorted(graph_targets[i]),graph_baseline_top5=graph_rank[i]))
        write_jsonl(PHASE/'outputs/diagnostic_improvement_rows.jsonl',results)
        report=dict(run_id=run['run_id'],protocol_sha256=sha256(protocol_path),calibration_cases=ntrain,test_cases=len(eligible)-ntrain,
            selected=dict(query_view=best[2],prototype_boost=best[3],bm25_boost=best[4]),
            calibration_native=metrics(improved_rank[:ntrain],targets[:ntrain]),
            held_out_native_baseline=metrics(baseline_rank[ntrain:],targets[ntrain:]),
            held_out_native_improved=metrics(improved_rank[ntrain:],targets[ntrain:]),
            held_out_graph_baseline=metrics(graph_rank[ntrain:],graph_targets[ntrain:]),
            oversize_excluded=len(cases)-len(eligible),remote_calls=0,confident_diagnoses_enabled=False,
            limitations=['Native label and graph ID metrics are separate and cannot be presented as the same task',
                        'Prototype training uses calibration groups only; fresh test groups exclude the old exposed benchmark',
                        'Eedi distractors are not observed student working; no Qwen classification accuracy is inferred',
                        'Candidate retrieval is not diagnosis; automatic confident labels remain disabled'])
        (PHASE/'outputs/diagnostic_improvement_metrics.json').write_text(json.dumps(report,indent=2)+'\n')
        run['outputs'].extend([protocol_path,PHASE/'outputs/diagnostic_improvement_rows.jsonl',PHASE/'outputs/diagnostic_improvement_metrics.json']);run['counts']=report
        print(json.dumps(report),flush=True)


if __name__=='__main__':main()
