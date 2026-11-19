import csv
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import merge_skill_shortlist as m  # noqa: E402


def _copy(tmp_path, decisions):
    for name in ("skill_map.csv", "concept_skill_map.json", "tier_a_review_shortlist.csv"):
        shutil.copy(m.FOLDER / name, tmp_path / name)
    path = tmp_path / "tier_a_review_shortlist.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    for i, d in decisions.items():
        rows[i]["decision"] = d
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    return rows


def test_shortlist_matches_skill_map():
    # every kept row agrees with the checkpoint's skill map, has one skill per concept, and is already merged
    new, problems = m.merge()
    assert problems == []
    mapping = json.loads((m.FOLDER / "concept_skill_map.json").read_text())["map"]
    assert all(mapping[c] == i for c, i in new.items())


def test_keep_rows_are_merged_and_conflicts_reported(tmp_path):
    rows = _copy(tmp_path, {7: "keep", 11: "keep", 13: "keep", 14: "keep"})
    new, problems = m.merge(tmp_path)
    assert new[rows[7]["concept_id"]] == int(rows[7]["skill_index"])
    assert new[rows[11]["concept_id"]] == int(rows[11]["skill_index"])
    assert any(rows[13]["concept_id"] in p for p in problems)  # two different skills kept for one concept
    json.loads((tmp_path / "concept_skill_map.json").read_text())


def test_mismatched_skill_is_a_problem(tmp_path):
    rows = _copy(tmp_path, {0: "keep"})
    p = tmp_path / "tier_a_review_shortlist.csv"
    p.write_text(p.read_text(encoding="utf-8").replace(f",{rows[0]['skill_index']},{rows[0]['skill_id']},", ",999,"+rows[0]["skill_id"]+",", 1), encoding="utf-8")
    assert m.merge(tmp_path)[1]
