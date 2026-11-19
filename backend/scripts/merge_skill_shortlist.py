"""Merge reviewed rows of models/akt/tier_a_review_shortlist.csv into concept_skill_map.json.

Only rows whose `decision` is "keep" are used (blank, "partial" and "reject" are ignored). A row must match
skill_map.csv (skill_index <-> skill_id), and a concept needs exactly one kept skill: several skills per
concept are not allowed until the team agrees a multi-skill policy. Dry run unless --write is given.

    python scripts/merge_skill_shortlist.py [--write]
"""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent / "models" / "akt"


def merge(folder: Path = FOLDER) -> tuple[dict[str, int], list[str]]:
    """Return (new concept -> skill index entries, problems). Problems must be fixed before writing."""
    ids = {int(r["skill_id"]): int(r["mapped_index"]) for r in csv.DictReader((folder / "skill_map.csv").open())}
    kept, problems = defaultdict(set), []
    with (folder / "tier_a_review_shortlist.csv").open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["decision"].strip().lower() != "keep":
                continue
            if ids.get(int(r["skill_id"])) != int(r["skill_index"]):
                problems.append(f"{r['concept_id']}: skill id {r['skill_id']} does not match index {r['skill_index']}")
                continue
            kept[r["concept_id"]].add(int(r["skill_index"]))
    existing = json.loads((folder / "concept_skill_map.json").read_text())["map"]
    new = {}
    for concept, skills in kept.items():
        if len(skills) > 1:
            problems.append(f"{concept}: {len(skills)} kept skills {sorted(skills)}; keep one")
        elif existing.get(concept, next(iter(skills))) != next(iter(skills)):
            problems.append(f"{concept}: already mapped to {existing[concept]}")
        else:
            new[concept] = next(iter(skills))
    return new, problems


if __name__ == "__main__":
    new, problems = merge()
    for p in problems:
        print("PROBLEM", p)
    print(f"{len(new)} concepts ready to add")
    if "--write" in sys.argv and not problems and new:
        path = FOLDER / "concept_skill_map.json"
        data = json.loads(path.read_text())
        data["map"].update(new)
        path.write_text(json.dumps(data, indent=2) + "\n")
        print("written")
    elif "--write" in sys.argv:
        print("nothing written")
