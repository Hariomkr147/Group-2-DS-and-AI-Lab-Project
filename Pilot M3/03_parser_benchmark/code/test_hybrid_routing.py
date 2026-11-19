import unittest
import pymupdf
from hybrid_route_test import native_features, subject_route


class RoutingChecks(unittest.TestCase):
    def test_precedence_and_science_signals(self):
        self.assertEqual(subject_route("ncert-mathematics-g6", {}), "mineru")
        self.assertEqual(subject_route("ncert-science-g7", {}, "private_answer"), "mineru")
        self.assertEqual(subject_route("ncert-mathematics-g6", {"notation": 1}, "edition_metadata"), "pymupdf")
        self.assertEqual(subject_route("ncert-science-g7", {}), "pymupdf")
        for signal in [{"tables": 1}, {"table_caption": 1}, {"num_lines": 4}, {"notation": 1}]:
            self.assertEqual(subject_route("ncert-science-g9", signal), "mineru")

    def test_real_pdf_equation_and_missed_table_caption(self):
        with pymupdf.open() as doc:
            page = doc.new_page()
            page.insert_text((50, 70), "Energy = 25 J")
            text, features = native_features(page)
            self.assertTrue(features["notation"])
            self.assertEqual(subject_route("ncert-science-g9", features), "mineru")
            page = doc.new_page()
            page.insert_text((50, 70), "Table 8.5: Properties of atoms")
            _, features = native_features(page)
            self.assertEqual(features["tables"], 0)
            self.assertTrue(features["table_caption"])
            self.assertEqual(subject_route("ncert-science-g9", features), "mineru")


if __name__ == "__main__":
    unittest.main()
