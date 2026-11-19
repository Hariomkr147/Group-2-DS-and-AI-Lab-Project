import unittest
from review_source_items import validate_pair


class ItemGateChecks(unittest.TestCase):
    def test_source_lineage_private_key_and_exercise_identity(self):
        sid='ncert-en-mathematics-g8-hemh1-r202425-07'
        sources={sid:{'sha256':'book'},'key':{'sha256':'answers'}}
        raw={'q':{'source_id':sid},'a':{'content_role':'private_answer','source_id':'key'}}
        q=dict(source_id=sid,source_sha256='book',source_block_ids=['q'],section='7.1',number=3)
        a=dict(source_id='key',source_sha256='answers',source_block_ids=['a'],exercise_label='7.1',key_number=3)
        validate_pair(q,a,raw,sources)
        for bad in ({**a,'exercise_label':'7.2'},{**a,'key_number':4},{**a,'source_sha256':'changed'}):
            with self.assertRaises(ValueError):validate_pair(q,bad,raw,sources)
        with self.assertRaises(ValueError):validate_pair({**q,'source_block_ids':['missing']},a,raw,sources)
        with self.assertRaises(ValueError):validate_pair(q,a,{**raw,'a':{'content_role':'chapter_content'}},sources)


if __name__=='__main__':unittest.main()
