import unittest
from audit_source_symbols import flags_for_page, sample_pages


class SourceSymbolChecks(unittest.TestCase):
    def test_missing_glyph_and_hour_ocr_are_flagged(self):
        blocks = [{'block_id': 'one', 'cleaned_text': 'Distance in 1 h0ur', 'cleaned_latex': None}]
        flags = flags_for_page('Cost \uf060 600', blocks)
        self.assertEqual({x['reason'] for x in flags}, {'native_private_use_glyph_near_number', 'suspicious_h0ur_ocr'})
        self.assertEqual(flags[1]['block_ids'], ['one'])
        self.assertEqual(flags_for_page('Distance in 1 hour', [{'block_id': 'one', 'cleaned_text': '1 hour', 'cleaned_latex': None}]), [])

    def test_sample_is_reproducible_and_independent_of_record_order(self):
        pages = [dict(source_id=source, page_number=page, content_role='chapter_content')
                 for source in ('a', 'b') for page in range(1, 6)]
        self.assertEqual(sample_pages(pages), sample_pages(list(reversed(pages))))
        self.assertEqual(len(sample_pages(pages)), 2)


if __name__ == '__main__':
    unittest.main()
