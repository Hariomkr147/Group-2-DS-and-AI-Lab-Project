import copy
import json
import unittest
from repair_pilot_sources import source_agrees,scope,ROOT,SOURCES,read_csv,read_jsonl
from clean_content import clean_records


class SourceReviewChecks(unittest.TestCase):
    def test_native_agreement_preserves_words_and_numbers(self):
        self.assertTrue(source_agrees('Heat moves from hot to cold.','Header\nHeat moves from\nhot to cold.\nFooter'))
        self.assertFalse(source_agrees('Distance in 1 h0ur','Distance in 1 hour'))
        self.assertFalse(source_agrees('The amount is 600.','The amount is 60.'))

    def test_scope_does_not_promote_interest_or_convection(self):
        self.assertEqual(scope(dict(subject='mathematics',grade='8'),3),['percentages'])
        self.assertEqual(scope(dict(subject='mathematics',grade='8'),10),[])
        self.assertEqual(scope(dict(subject='science',grade='7'),6),[])
        self.assertEqual(scope(dict(subject='mathematics',grade='7'),14),['fraction_multiplication'])

    def test_real_source_fix_is_exact_and_stale_input_fails_closed(self):
        raw=read_jsonl(ROOT/'04_extract_text_and_ocr/outputs/blocks.jsonl')
        block=next(b for b in raw if 'h0ur' in b['raw_text'])
        sources=read_csv(SOURCES)
        pages=[p for p in read_jsonl(ROOT/'04_extract_text_and_ocr/outputs/pages.jsonl') if p['source_id']==block['source_id'] and p['page_number']==block['page_number']]
        clean,transforms,*_=clean_records(pages,[block],sources,{},'test')
        self.assertNotIn('h0ur',clean[0]['cleaned_text'])
        self.assertIn('SOURCE_CHECKED_FIX',transforms[0]['rule_ids'])
        bad=copy.deepcopy(block);bad['raw_text']+=' changed'
        with self.assertRaisesRegex(ValueError,'original block bytes'):clean_records(pages,[bad],sources,{},'test')


if __name__=='__main__':unittest.main()
