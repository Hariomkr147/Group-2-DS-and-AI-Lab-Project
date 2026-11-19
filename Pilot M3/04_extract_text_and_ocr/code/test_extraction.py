"""Canonical-adapter checks against real parser output and unsafe input boundaries."""
import copy
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from extract_content import ROOT, POLICY, normalize_page, safe_member
from pipeline import SOURCES, read_csv, sha256
from validate_extraction import validate_extraction


class ExtractionChecks(unittest.TestCase):
    def setUp(self):
        self.source = next(s for s in read_csv(SOURCES) if "g6-" in s["source_id"] and not s["source_id"].endswith("ps"))
        self.policy = json.loads(POLICY.read_text(encoding="utf-8"))

    def test_real_mineru_page_preserves_math_and_asset_lineage(self):
        archive = next((ROOT / "03_parser_benchmark/evidence/parser_outputs").rglob("*g6*-mineru.zip"))
        with zipfile.ZipFile(archive) as bundle:
            raw = next(p for p in json.loads(bundle.read("middle_json.json"))["pages"] if p["page_idx"] == 14)
        args = (self.source, 15, raw, "MinerU", archive.relative_to(ROOT).as_posix(), sha256(archive), {"proposed_content_role": "chapter_content"}, self.policy, "test")
        page, blocks = normalize_page(*args, ocr_observed_in_batch=True, parse_mode="txt")
        page2, blocks2 = normalize_page(*args, ocr_observed_in_batch=True, parse_mode="txt")
        self.assertEqual([b["block_id"] for b in blocks], [b["block_id"] for b in blocks2])
        self.assertTrue(any(b["inline_formulas"] for b in blocks))
        self.assertTrue(any(b["raw_html"] for b in blocks))
        self.assertTrue(any(b["asset_ids"] for b in blocks))
        self.assertIsNone(page["ocr_used"])
        self.assertTrue(page["ocr_observed_in_batch"])
        self.assertEqual(page["parser_parse_mode"], "txt")
        self.assertIsNone(page["printed_page_label"])
        self.assertTrue(all(b["retrieval_visibility"] == "not_accepted" for b in blocks))

    def test_native_fallback_is_quarantined_and_private_answers_stay_private(self):
        raw = {"blocks": [{"type": 0, "bbox": [0, 0, 100, 20], "lines": [{"spans": [{"text": "1/2 + 1/3 = 5/6"}]}]}]}
        for role in ("chapter_content", "private_answer"):
            page, blocks = normalize_page(self.source, 1, raw, "PyMuPDF", "native.jsonl", "a" * 64, {"proposed_content_role": role}, self.policy, "test")
            self.assertEqual(blocks[0]["raw_text"], "1/2 + 1/3 = 5/6")
            if role == "chapter_content": self.assertEqual(page["status"], "quarantined")
            else:
                self.assertEqual(blocks[0]["content_type"], "answer")
                self.assertEqual(blocks[0]["retrieval_visibility"], "private")

    def test_zip_paths_cannot_escape_asset_folder(self):
        safe_member("images/page_0_image_1.jpg")
        for name in ("../outside", "/images/a.jpg", "images/../../a", "images\\a.jpg", "C:/a", "other/a.jpg"):
            with self.subTest(name=name), self.assertRaises(ValueError): safe_member(name)

    def test_validation_rejects_omitted_page_open_answer_and_changed_native(self):
        with tempfile.TemporaryDirectory() as directory:
            rawfile = Path(directory) / "native.jsonl"
            rawfile.write_text("fixture", encoding="utf-8")
            source = {**self.source, "pdf_pages": "1"}
            page, blocks = normalize_page(source, 1, {"blocks": [{"type": 0, "bbox": [0, 0, 10, 10], "lines": [{"spans": [{"text": "42"}]}]}]}, "PyMuPDF", "fixture", sha256(rawfile), {"proposed_content_role": "private_answer"}, self.policy, "test")
            with patch("validate_extraction.local_path", return_value=rawfile):
                validate_extraction([source], [page], blocks, [])
                with self.assertRaisesRegex(ValueError, "Physical pages"):
                    validate_extraction([source], [], blocks, [])
                changed = copy.deepcopy(blocks); changed[0]["retrieval_visibility"] = "public"
                with self.assertRaises(ValueError): validate_extraction([source], [page], changed, [])
                rawfile.write_text("tampered", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Changed native"):
                    validate_extraction([source], [page], blocks, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
