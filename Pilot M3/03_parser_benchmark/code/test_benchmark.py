"""Check that parser comparisons cannot silently score different physical pages."""
import unittest

from benchmark_parsers import page_groups, verify_page_set


class BenchmarkChecks(unittest.TestCase):
    def test_bad_or_duplicate_source_pages_fail(self):
        sources = [{"source_id": "s", "pdf_pages": "3"}]
        good = [{"source_id": "s", "page_number": "3"}, {"source_id": "s", "page_number": "1"}]
        self.assertEqual(page_groups(good, sources), {"s": [1, 3]})
        for bad in ([good[0], good[0]], [{"source_id": "other", "page_number": "1"}],
                    [{"source_id": "s", "page_number": "0"}], [{"source_id": "s", "page_number": "4"}], []):
            with self.subTest(selection=bad), self.assertRaises(ValueError):
                page_groups(bad, sources)

    def test_parser_must_return_original_physical_page_indices(self):
        verify_page_set({"pages": [{"page_idx": 0}, {"page_idx": 14}]}, [1, 15])
        for pages in ([{"page_idx": 0}, {"page_idx": 1}], [{"page_idx": 0}],
                      [{"page_idx": 0}, {"page_idx": 0}]):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                verify_page_set({"pages": pages}, [1, 15])


if __name__ == "__main__":
    unittest.main(verbosity=2)
