import unittest
from retrieve import bm25, reciprocal_rank_fusion, resolve


class RetrievalChecks(unittest.TestCase):
    def test_real_bm25_and_rrf(self):
        scores = bm25("radiation", ["radiation needs no medium", "a metal conducts heat", "radiation radiation"])
        self.assertGreater(scores[2], scores[0]); self.assertEqual(scores[1], 0)
        self.assertEqual(bm25("heat", []), [])
        fused = reciprocal_rank_fusion([[('a', 5), ('b', 2)], [('b', 7)]])
        self.assertEqual(fused[0][0], 'b')

    def test_abstention_and_concept_dedup(self):
        chunks = {'a': {'concept_ids': ['fractions']}, 'b': {'concept_ids': ['fractions']}, 'c': {'concept_ids': ['radiation']}}
        dense = [('a', .8), ('b', .79), ('c', .6)]
        self.assertEqual(resolve(dense, chunks, .7, .1)['concept_id'], 'fractions')
        self.assertEqual(resolve(dense, chunks, .9, .1)['status'], 'unsupported')
        self.assertEqual(resolve(dense, chunks, .7, .3)['status'], 'clarify')
        self.assertEqual(resolve([], chunks, .7, .1)['status'], 'no_evidence')


if __name__ == '__main__':
    unittest.main()
