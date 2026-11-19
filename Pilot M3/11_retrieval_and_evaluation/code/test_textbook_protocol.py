import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock,patch
from retrieve import Retriever
from evaluate_textbook_queries import concept_measures,freeze_protocol,route_score


class TextbookChecks(unittest.TestCase):
    def test_frozen_groups_and_challenge_retention(self):
        _,p=freeze_protocol()
        self.assertEqual(len(p['cases']),83)
        groups=[{q['group'] for q in p['cases'] if q['split']==s} for s in ('calibration','held_out')]
        self.assertFalse(groups[0]&groups[1])
        self.assertTrue(any(q['relevance']=='needs_visual' for q in p['cases']))
        self.assertTrue(any(q['relevance']=='extraction_or_boundary_challenge' for q in p['cases']))

    def test_metrics_and_routing_penalize_false_acceptance(self):
        chunks={'a':dict(concept_ids=['fractions']),'b':dict(concept_ids=['conduction'])}
        self.assertEqual(concept_measures([('b',.9),('a',.8)],['fractions'],chunks)['concept_mrr_at_5'],.5)
        rows=[dict(relevance='outside_objectives',relevant_concept_ids=[],rankings={'BGE_cosine':[('b',.9),('a',.6)]})]
        self.assertEqual(route_score(rows,chunks,.7,.02),-2)
        self.assertEqual(route_score(rows,chunks,.95,.02),1)

    def test_failed_router_requires_topic_and_explicit_filter_still_works(self):
        e=Retriever.__new__(Retriever);e.version='v';e.chunks={'a':dict(concept_ids=['fractions'])}
        e.query_vector=Mock(return_value=[]);e.rank=Mock(return_value={'BGE_cosine':[('a',.5)],'RRF_BM25_BGE':[('a',.01)]})
        with tempfile.TemporaryDirectory() as tmp,patch('retrieve.ROOT',Path(tmp)):
            p=Path(tmp)/'11_retrieval_and_evaluation/outputs/resolution_policy.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps(dict(corpus_version='v',automatic_routing_enabled=False)))
            self.assertEqual(e.search('question')['resolution']['status'],'choose_topic');e.query_vector.assert_not_called()
            result=e.search('question',concept_ids=['fractions'])
            self.assertEqual(result['resolution']['selection'],'explicit_user_topic')
            self.assertEqual(len(result['hits']),1)


if __name__=='__main__':unittest.main()
