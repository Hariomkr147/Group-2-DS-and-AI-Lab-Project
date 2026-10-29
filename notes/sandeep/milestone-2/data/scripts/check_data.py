"""Sanity checks on the processed data. Run after the prep scripts; exits non-zero on failure.

    python notes/sandeep/milestone-2/data/scripts/check_data.py
"""
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[1] / "processed"
failures = []


def check(ok: bool, msg: str):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


def jsonl(path: Path):
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f]


# ASSISTments
a = {s: jsonl(P / "assistments" / f"{s}.jsonl") for s in ("train", "val", "test")}
n_skills = sum(1 for _ in open(P / "assistments" / "skill_map.csv")) - 1
users = {s: {r["user_id"] for r in rows} for s, rows in a.items()}
check(not (users["train"] & users["val"] or users["train"] & users["test"] or users["val"] & users["test"]),
      "assistments: no student appears in two splits")
check(all(len(r["skills"]) == len(r["correct"]) for rows in a.values() for r in rows),
      "assistments: skills and correct have equal length")
check(all(0 <= k < n_skills for rows in a.values() for r in rows for k in r["skills"]),
      f"assistments: every skill index is in 0..{n_skills - 1}")
check(all(c in (0, 1) for rows in a.values() for r in rows for c in r["correct"]),
      "assistments: correct is 0/1")
check(all(3 <= len(r["skills"]) <= 200 for rows in a.values() for r in rows),
      "assistments: window length is 3..200")

# MathDial
m = {s: jsonl(P / "mathdial" / f"{s}.jsonl") for s in ("train", "val", "test")}
q = {s: {r["qid"] for r in rows} for s, rows in m.items()}
check(not (q["train"] & q["val"]), "mathdial: no problem shared by train and val")
check(all(r["messages"][0]["role"] == "system" and r["target"] for rows in m.values() for r in rows),
      "mathdial: every example has a system prompt and a non-empty target")
check(not any(r["keep"] and (r["act"] == "telling" or r["leaks_answer"]) for rows in m.values() for r in rows),
      "mathdial: kept examples never tell or leak the answer")

# NCERT (only if it has been built)
chunks = P / "ncert" / "chunks.jsonl"
if chunks.exists():
    c = jsonl(chunks)
    check(len({r["id"] for r in c}) == len(c), "ncert: chunk ids are unique")
    check(all(r["text"].strip() for r in c), "ncert: no empty chunks")
    check({r["subject"] for r in c} == {"maths", "science"}, "ncert: both subjects present")

# Course packs and test scenarios (only if built)
S = P.parent / "test_scenarios"
packs = [json.loads(f.read_text(encoding="utf8")) for f in sorted((P / "course_packs").glob("*.json"))]
if packs:
    for pack in packs:
        ids = {c["id"] for c in pack["concepts"]}
        check(all(p in ids for c in pack["concepts"] for p in c["prerequisites"]),
              f"{pack['id']}: every prerequisite exists")
        check(all(c["questions"] and c["materials"] for c in pack["concepts"]),
              f"{pack['id']}: every concept has questions and study material")
        check(all(q["answer"] and q["hint"] for c in pack["concepts"] for q in c["questions"]),
              f"{pack['id']}: every question has an answer and a hint")
if (S / "backtracking.jsonl").exists():
    concepts = {c["id"] for pack in packs for c in pack["concepts"]}
    bt, mc, gr = (jsonl(S / f"{n}.jsonl") for n in ("backtracking", "misconceptions", "guardrails"))
    check(all(r["target_concept"] in concepts for r in bt), "scenarios: backtracking concepts exist in the packs")
    check(all(r["expected_gap"] is None or r["expected_gap"] in r["weak_concepts"] for r in bt),
          "scenarios: every expected gap is one of the weak concepts")
    check(all(len(r["expected_path"]) == {"gap_one_level": 2, "gap_two_levels": 3}.get(r["type"], 0) for r in bt),
          "scenarios: path length matches the gap type")
    check(all(r["correct_answer"] != r["wrong_answer"] for r in mc), "scenarios: misconception answers are wrong")
    check({r["label"] for r in gr} == {"on_topic", "off_topic", "answer_request"}, "scenarios: all three guardrail labels used")
    all_ids = [r["id"] for r in bt + mc + gr]
    check(len(all_ids) == len(set(all_ids)), "scenarios: ids are unique")

sys.exit(1 if failures else 0)
