import unittest
from build_graph import prerequisites, validate_graph


class GraphChecks(unittest.TestCase):
    def test_cycles_unknown_and_depth(self):
        edges = [dict(prerequisite_id=a, dependent_id=b, review_status="approved") for a, b in [("g6", "g7"), ("g7", "g8")]]
        validate_graph(edges, {"g6", "g7", "g8"})
        self.assertEqual(prerequisites(edges, "g8", 1), [{"concept_id": "g7", "depth": 1}])
        self.assertEqual(prerequisites(edges, "g8", 2)[-1], {"concept_id": "g6", "depth": 2})
        self.assertEqual(prerequisites(edges, "g8", 0), [])
        with self.assertRaises(ValueError):
            prerequisites(edges, "g8", 11)
        for extra in [dict(prerequisite_id="g8", dependent_id="g6", review_status="approved"),
                      dict(prerequisite_id="missing", dependent_id="g6", review_status="approved"), edges[0]]:
            with self.assertRaises(ValueError):
                validate_graph([*edges, extra], {"g6", "g7", "g8"})


if __name__ == "__main__":
    unittest.main()
