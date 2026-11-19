"""Regression checks for the mathematical data-loss risks in the previous pipeline."""
import unittest

from clean_content import clean_records, clean_text


def block(identifier, text, number=1, bbox=None, **values):
    return {"block_id": identifier, "source_id": "source", "page_number": number,
            "raw_text": text, "raw_latex": None, "raw_html": None, "inline_formulas": [],
            "bbox": bbox or [0.1, 0.2, 0.8, 0.4], "coordinate_system": "MinerU normalized 0..1",
            "content_role": "chapter_content", "content_type": "prose", "retrieval_visibility": "not_accepted",
            "parent_raw_ref": "native.zip", **values}


class CleaningChecks(unittest.TestCase):
    def test_preserves_notation_numeric_lines_and_ambiguous_hyphen(self):
        for text in ("1/2 + 1/3 = 5/6", "20% of 50 = 10", "42\n1\n10", "8 -\n3 = 5", "word-\nwrap",
                     "−3 × 2 ÷ 4 < 0; 1.5 m/s; H₂O; x² ≥ 2", "a  b\t1/10"):
            with self.subTest(text=text):
                self.assertEqual(clean_text(text), (text, []))

    def test_controls_cannot_silently_join_numbers(self):
        after, rules = clean_text("1\x002\r\n42  ")
        self.assertEqual(after, "1 2\n42")
        self.assertEqual(set(rules), {"CRLF_TO_LF", "CONTROL_TO_SPACE", "TRIM_LINE_ENDS"})

    def test_margin_removal_requires_repetition_and_never_removes_a_numeric_value(self):
        sources = [{"source_id": "source", "edition": "Reprint 2026-27", "book_title": "Ganita Prakash", "chapter_title": "Fractions", "grade": "6"}]
        pages = [{"source_id": "source", "page_number": n, "source_sha256": "a" * 64, "raw_output_ref": "native.zip", "status": "extracted", "content_role": "chapter_content", "retrieval_visibility": "not_accepted"} for n in range(1, 4)]
        blocks = [block(f"footer-{n}", "Reprint 2026-27", n, [0.3, 0.96, 0.7, 0.98]) for n in range(1, 4)]
        blocks += [block("number", "42", 1, [0.3, 0.96, 0.7, 0.98]), block("body-footer-wording", "Reprint 2026-27", 1)]
        cleaned, transforms, quarantine, _, _ = clean_records(pages, blocks, sources, {}, "test")
        self.assertEqual(sum(b["removed"] for b in cleaned), 3)
        self.assertEqual(cleaned[-2]["cleaned_text"], "42")
        self.assertEqual(cleaned[-1]["cleaned_text"], "Reprint 2026-27")
        self.assertEqual(len(transforms), 3)
        self.assertEqual(transforms[0]["before"]["text"], "Reprint 2026-27")
        one_page = clean_records(pages[:1], blocks[:1], sources, {}, "test")[0]
        self.assertFalse(one_page[0]["removed"])

    def test_raw_latex_html_private_status_and_quarantine_are_preserved(self):
        sources = [{"source_id": "source", "edition": "Reprint 2026-27", "book_title": "Book", "chapter_title": "Chapter", "grade": "6"}]
        pages = [{"source_id": "source", "page_number": 1, "source_sha256": "a" * 64, "raw_output_ref": "native.zip", "status": "extracted", "content_role": "private_answer", "retrieval_visibility": "private"}]
        raw = block("critical", "1\x002", raw_latex=r"\frac{1}{10}", raw_html="<table><tr><td>1/10</td></tr></table>", content_role="private_answer", content_type="answer", retrieval_visibility="private")
        cleaned, transforms, quarantine, _, _ = clean_records(pages, [raw], sources, {}, "test")
        self.assertEqual(cleaned[0]["cleaned_latex"], raw["raw_latex"])
        self.assertEqual(cleaned[0]["cleaned_html"], raw["raw_html"])
        self.assertEqual(cleaned[0]["retrieval_visibility"], "private")
        self.assertEqual(cleaned[0]["review_status"], "quarantined")
        self.assertEqual(len(quarantine), 1)
        self.assertEqual(transforms[0]["before"]["text"], "1\x002")


if __name__ == "__main__":
    unittest.main(verbosity=2)
