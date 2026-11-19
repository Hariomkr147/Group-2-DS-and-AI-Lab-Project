"""Exercise private/unreviewed boundaries and genuine tokenizer limits."""
import unittest
from copy import deepcopy
from build_content_pack import resolve_group, validate_pack


class ContentBoundaries(unittest.TestCase):
    def setUp(self):
        self.group = dict(source_id="source", page=2, orders=[1], printed_page_label="10")
        self.block = dict(block_id="source:p002:hash:b001", source_id="source",
                          page_number=2, cleaned_text="Heat transfer by radiation requires no medium.", review_status="approved",
                          quarantine_reasons=[], content_role="chapter_content", retrieval_visibility="evidence")

    def test_unreviewed_private_and_missing_never_resolve(self):
        self.assertEqual(resolve_group(self.group, [self.block]), [self.block])
        for field, value in [("review_status", "pending"), ("retrieval_visibility", "private"), ("content_role", "private_answer")]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                resolve_group(self.group, [{**self.block, field: value}])
        with self.assertRaises(ValueError):
            resolve_group({**self.group, "orders": [1, 2]}, [self.block])

    def test_private_scoring_is_separate_and_bank_aligned(self):
        question = dict(question_id="q1", concept_ids=["radiation"], source_block_ids=[self.block["block_id"]])
        answer = dict(question_id="q1")
        validate_pack([{"concept_id": "radiation"}], [], [question], [answer], [self.block])
        bad = deepcopy(question); bad["gold_answer"] = "leak"
        with self.assertRaises(ValueError):
            validate_pack([{"concept_id": "radiation"}], [], [bad], [answer], [self.block])
        with self.assertRaises(ValueError):
            validate_pack([{"concept_id": "radiation"}], [], [question], [], [self.block])


if __name__ == "__main__":
    unittest.main()
