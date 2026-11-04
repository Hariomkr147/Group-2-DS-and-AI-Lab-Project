import unittest
import numpy as np
from embed_chunks import validate_vectors


class EmbeddingChecks(unittest.TestCase):
    def test_alignment_dimension_finite_and_norm(self):
        good = np.zeros((2, 384), dtype="float32"); good[:, 0] = 1
        validate_vectors(good, ["a", "b"])
        for matrix, ids in [(good, ["a", "a"]), (good, ["a"]), (good[:, :383], ["a", "b"]),
                            (np.zeros_like(good), ["a", "b"]), (good * np.nan, ["a", "b"])]:
            with self.assertRaises(ValueError):
                validate_vectors(matrix, ids)


if __name__ == "__main__":
    unittest.main()
