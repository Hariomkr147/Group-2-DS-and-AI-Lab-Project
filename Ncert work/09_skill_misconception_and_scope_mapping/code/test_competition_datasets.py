import tempfile
import unittest
import zipfile
from pathlib import Path
from load_competition_datasets import validate_archive


class CompetitionArchiveChecks(unittest.TestCase):
    def test_path_and_column_alignment_boundaries(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "original.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("train.csv", "QuestionId,Category\n1,True_Correct\n")
            self.assertEqual(len(validate_archive(path, {"train.csv"})["train.csv"]["rows"]), 1)
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("../train.csv", "id\n1\n")
            with self.assertRaises(ValueError):
                validate_archive(path, {"train.csv"})
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("train.csv", "id,Category\n1,True_Correct,extra\n")
            with self.assertRaises(ValueError):
                validate_archive(path, {"train.csv"})


if __name__ == "__main__":
    unittest.main()
