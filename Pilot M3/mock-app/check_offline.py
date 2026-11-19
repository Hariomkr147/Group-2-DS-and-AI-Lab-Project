"""Check real pilot artifacts and controller using ephemeral history; no response-model calls."""
import json
import sqlite3
from unittest.mock import Mock,patch
from server import Engine,HERE


def main():
    real_connect=sqlite3.connect
    with patch('server.sqlite3.connect',side_effect=lambda *a,**k:real_connect(':memory:',check_same_thread=False)):
        engine=Engine()
    engine.llm.ask=Mock(side_effect=AssertionError('Hosted model is intentionally excluded from this check'))
    try:
        assert engine.kt.status.startswith('AKT') and engine.kt.n==123 and engine.kt.mapping=={'fraction_multiplication':42,'fraction_division':38,'percentages':75}
        evidence=[]
        for cid,c in engine.concepts.items():
            hits=engine.evidence(cid,c['summary'])
            assert hits and all(cid in h['concept_ids'] and h['review_status']=='approved' for h in hits)
            evidence.append(dict(concept=cid,chunks=[h['chunk_id'] for h in hits]))
        # Section topics from the automatic release are on-topic; unrelated chat is not.
        assert len(engine.concepts)>6 and all(engine.topic_terms.search(t) for t in ['How does a sea breeze form?','What is compound interest?'])
        assert not engine.topic_terms.search('who won the match')
        sid=engine.create('percentages','Hariom')['session_id']
        result=engine.respond(sid,'Try a question',intent='practice')
        pool={q['id']:q for _,_,q in engine.practice_pool(engine.get(sid))};seen=set()
        while result['session']['active_question']:
            qid=result['session']['active_question']['id'];assert qid not in seen;seen.add(qid)
            assert 'key' not in result['session']['active_question']
            result=engine.respond(sid,pool[qid]['key'],intent='answer')
        assert len(seen)==7 and result['session']['state']=='DONE'
        result=engine.respond(sid,'Try a question',intent='practice')
        assert result['session']['practice_progress']['round']==2 and len(engine.get(sid)['attempts'])==7
        readiness=engine.progress(engine.get(sid))['concept_readiness']
        assert {r['concept_id'] for r in readiness if r['origin']=='akt_prediction'}==set(engine.kt.mapping)
        cases=[('20% of 50','1000','50 * 20 = 1000','22482'),
               ('20% of 50','2.5','50 / 20 = 2.5','26916'),
               ('1/2 + 1/3','2/5','1+1=2\n2+3=5','19849'),
               ('1/2 * 1/3','3/2','1/2 * 3 = 3/2','22666'),
               ('1/2 ÷ 1/3','1/6','1/2 * 1/3 = 1/6','23021'),
               ('Convert the ratio to a percentage: 3 : 4','0.75%','3 / 4 = 0.75','14036')]
        for q,a,w,mid in cases:
            d=engine.diagnose({'prompt':q},a,w)
            assert d['misconception_id']==mid and not d['confirmed'] and not d['persistent']
            assert not d['remote_selector_enabled']
            assert engine.diagnose({'prompt':q},a,'I guessed')['misconception_id'] is None
        engine.llm.ask.assert_not_called()
        report=dict(passed=True,corpus_version=engine.version,rag_chunks=len(engine.chunks),topics=len(engine.concepts),
            kt_status=engine.kt.status,kt_skills=engine.kt.n,kt_mappings=engine.kt.mapping,
            concepts_checked=evidence,source_questions_completed=len(seen),review_round=2,
            corroborated_rule_families=len(cases),unsupported_working_abstentions=len(cases),
            response_model_calls=0,history='ephemeral in-memory SQLite',
            limitation='Program and artifact verification, not learner diagnosis accuracy or live Qwen teaching validation')
        (HERE/'logs/offline_hardening_checks.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(report),flush=True)
    finally:engine.db.close()


if __name__=='__main__':main()
