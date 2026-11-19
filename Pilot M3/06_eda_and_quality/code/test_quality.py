"""Release-boundary checks: no silent mathematical edits or fabricated approvals."""
import copy
import unittest

from build_quality_report import accepted_blocks, validate_cleaning
from clean_content import content_hash


class QualityChecks(unittest.TestCase):
    def fixture(self):
        raw = {"block_id": "b", "raw_text": "1/2 + 1/3 = 5/6", "raw_latex": None, "raw_html": None,
               "retrieval_visibility": "not_accepted", "content_role": "chapter_content"}
        clean = {"block_id": "b", "raw_block_id": "b", "source_id": "s", "page_number": 1,
                 "cleaned_text": raw["raw_text"], "cleaned_latex": None, "cleaned_html": None,
                 "content_hash": content_hash(raw["raw_text"], None, None), "retrieval_visibility": "not_accepted",
                 "content_role": "chapter_content", "removed": False, "applied_rule_ids": [], "quarantine_reasons": [], "content_type": "prose"}
        return raw, clean

    def test_slash_loss_and_unlogged_changes_fail_even_with_updated_hash(self):
        raw, clean = self.fixture()
        self.assertEqual(validate_cleaning([raw], [clean], []), 0)
        altered = copy.deepcopy(clean)
        altered["cleaned_text"] = "12 + 13 = 56"
        altered["content_hash"] = content_hash(altered["cleaned_text"], None, None)
        with self.assertRaisesRegex(ValueError, "non-whitespace"):
            validate_cleaning([raw], [altered], [])
        altered = copy.deepcopy(clean)
        altered["cleaned_text"] += " "
        altered["content_hash"] = content_hash(altered["cleaned_text"], None, None)
        with self.assertRaisesRegex(ValueError, "transformation evidence"):
            validate_cleaning([raw], [altered], [])

    def test_missing_reviews_policy_and_private_answers_cannot_be_released(self):
        _, clean = self.fixture()
        policy = {"accepted_default_parser": "MinerU", "accepted_ocr_policy": "reviewed conditional"}
        pending = {"source_id": "s", "page_number": 1, "review_status": "pending"}
        self.assertEqual(accepted_blocks([clean], [pending], policy), [])
        approval = {**pending, "review_status": "approved"}
        with self.assertRaisesRegex(ValueError, "authorized"):
            accepted_blocks([clean], [approval], policy)
        approval.update(reviewer="Codex fixture", review_date="2026-11-02", evidence_ref="fixture-only", review_method="ai_visual_source_check", source_check="pass", critical_checks="pass")
        authorization = {"allowed_review_methods": ["ai_visual_source_check"]}
        self.assertEqual(accepted_blocks([clean], [approval], {}, authorization), [])
        self.assertEqual(len(accepted_blocks([clean], [approval], policy, authorization)), 1)
        self.assertEqual(accepted_blocks([{**clean, "run_id": "first"}], [approval], policy, authorization), accepted_blocks([{**clean, "run_id": "rerun"}], [approval], policy, authorization))
        private = {**clean, "retrieval_visibility": "private", "content_role": "private_answer"}
        self.assertEqual(accepted_blocks([private], [approval], policy, authorization), [])
        corrupted = {**clean, "quarantine_reasons": ["unresolved_unicode_glyphs"]}
        self.assertEqual(accepted_blocks([corrupted], [approval], policy, authorization), [])

    def test_ai_authorization_is_explicit_and_approves_only_matching_blocks(self):
        _, clean = self.fixture()
        policy = {"accepted_default_parser": "MinerU", "accepted_ocr_policy": "conditional"}
        review = {"block_id": "b", "source_id": "s", "page_number": "1", "content_hash": clean["content_hash"], "review_status": "approved",
                  "reviewer": "Codex fixture", "review_date": "2026-11-02", "evidence_ref": "fixture-source", "review_method": "ai_visual_source_check", "source_check": "pass", "critical_checks": "pass"}
        with self.assertRaisesRegex(ValueError, "authorized"):
            accepted_blocks([clean], [], policy, block_reviews=[review])
        authorization = {"allowed_review_methods": ["ai_visual_source_check"]}
        unreviewed = {**clean, "block_id": "other", "raw_block_id": "other"}
        result = accepted_blocks([clean, unreviewed], [], policy, authorization, [review])
        self.assertEqual([b["block_id"] for b in result], ["b"])
        self.assertEqual(result[0]["review_method"], "ai_visual_source_check")
        with self.assertRaisesRegex(ValueError, "changed"):
            accepted_blocks([clean], [], policy, authorization, [{**review, "content_hash": "stale"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
