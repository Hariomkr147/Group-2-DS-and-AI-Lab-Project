import json
import unittest
import numpy as np
from audit_embeddings import verify_database_rows


class EmbeddingAuditChecks(unittest.TestCase):
    def test_identity_text_and_vector_mismatches_fail(self):
        ids, texts, vectors = ['a', 'b'], ['first', 'second'], np.array([[1., 0.], [0., 1.]], dtype='float32')
        rows = [('b', 'second', json.dumps([0, 1])), ('a', 'first', json.dumps([1, 0]))]
        verify_database_rows(ids, texts, vectors, rows)
        for bad in [rows[:1], [('a', 'changed', '[1,0]'), rows[0]],
                    [('a', 'first', '[0,1]'), rows[0]], [rows[0], rows[0]]]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                verify_database_rows(ids, texts, vectors, bad)


if __name__ == '__main__':
    unittest.main()
