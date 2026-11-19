import unittest
from load_eedi_catalogue import catalogue


class CatalogueChecks(unittest.TestCase):
    def test_original_ids_text_weights_and_foreign_keys(self):
        constructs = [{"ConstructId": "1"}, {"ConstructId": "2"}]
        first = dict(MisconceptionId="13708", ConstructId="1", MisconceptionName="When asked for the value of a digit, just gives the digit", PercentageMisconceptionExistsInThisConstruct="60")
        second = {**first, "ConstructId": "2", "PercentageMisconceptionExistsInThisConstruct": "40"}
        rows = catalogue(constructs, [first, second])
        self.assertEqual(rows[0]["misconception_id"], "13708")
        self.assertEqual(rows[0]["text"], first["MisconceptionName"])
        for bad in [{**second, "ConstructId": "missing"}, {**second, "MisconceptionName": "changed"}, {**second, "PercentageMisconceptionExistsInThisConstruct": "-4"}]:
            with self.assertRaises(ValueError):
                catalogue(constructs, [first, bad])
        with self.assertRaises(ValueError):
            catalogue(constructs, [first])


if __name__ == "__main__":
    unittest.main()
