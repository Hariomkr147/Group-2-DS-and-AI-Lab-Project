import json
import unittest
from evaluate_diagnostic_improvements import PHASE,metrics,one_per_group
from pipeline import read_jsonl


class DiagnosticProtocolChecks(unittest.TestCase):
    def test_native_and_covered_denominators_are_distinct(self):
        result=metrics([['a'],['b'],['c']],[{'a'},set(),{'z'}])
        self.assertEqual(result['cases'],3);self.assertEqual(result['covered'],2)
        self.assertEqual(result['recall_at_5'],.5)
        self.assertIsNone(metrics([[]],[set()])['recall_at_5'])

    def test_fresh_300_groups_exclude_exposed_test(self):
        p=json.loads((PHASE/'evaluation/diagnostic_improvement_protocol.json').read_text())
        old=json.loads((PHASE/'evaluation/diagnostic_protocol.json').read_text())
        examples={r['example_id']:r for r in read_jsonl(PHASE/'outputs/diagnostic_examples.jsonl')}
        train={examples[x]['problem_group_id'] for x in p['calibration_ids']}
        test={examples[x]['problem_group_id'] for x in p['test_ids']}
        exposed={examples[x]['problem_group_id'] for x in old['selected_example_ids'] if examples[x]['split']=='held_out_by_question'}
        self.assertEqual((len(train),len(test)),(200,300));self.assertFalse(test&(train|exposed))
        self.assertEqual(len(one_per_group([dict(example_id='a',problem_group_id='x'),dict(example_id='b',problem_group_id='x')],2)),1)


if __name__=='__main__':unittest.main()
