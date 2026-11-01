"""Sanity checks on the processed data. Run after the prep scripts; exits non-zero on failure.

    python docs/milestone-2/data/scripts/checks/check_data.py
"""
import json
import sys
from pathlib import Path

P = Path(__file__).resolve().parents[3] / "data" / "processed"
failures = []


def check(ok: bool, msg: str):
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        failures.append(msg)


def jsonl(path: Path):
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f]


# DKT arrays (the frozen set the team models on)
import re
from collections import Counter

import numpy as np

FROZEN = P / "assistments" / "frozen"
d = np.load(FROZEN / "dkt_data.npz")
n = int(d["N"])
real = d["M_tr"] == 1
check(((d["S_tr"] + n * d["C_tr"])[real] == d["X_tr"][real]).all(), "dkt: x = skill + N * correct for every real step")
check(d["X_tr"].shape[1] == 200 and d["X_te"].shape[1] == 200, "dkt: sequences are padded to 200")
check(int(d["X_tr"].max()) < 2 * n and int(d["X_te"].max()) < 2 * n, "dkt: every input id is below 2N")
check(bool((d["M_tr"].sum(1) >= 3).all() and (d["M_te"].sum(1) >= 3).all()), "dkt: every sequence has at least 3 steps")
v = json.loads((FROZEN / "dkt_validation.json").read_text())
check(max(v["validation_train_sequence_indices"]) < d["X_tr"].shape[0], "dkt: validation rows exist in the train arrays")

# Chat corpus (prep_chat.py)
c = {s: jsonl(P / "socratic_chat" / f"{s}.jsonl") for s in ("train", "val", "test")}
prob = {s: {r["problem"] for r in rows} for s, rows in c.items()}
check(not (prob["train"] & prob["val"] or prob["train"] & prob["test"] or prob["val"] & prob["test"]),
      "chat: no problem appears in two splits (across both sources)")
check(all({r["source"] for r in c[s]} == {"mathdial", "socrateach"} for s in ("val", "test")),
      "chat: validation and test each mix MathDial and SocraTeach")
check({r["source"] for rows in c.values() for r in rows} == {"mathdial", "socrateach"},
      "chat: source tags are exactly mathdial and socrateach")
check(all(m["content"].strip() for rows in c.values() for r in rows for m in r["messages"]), "chat: no empty message")
check(all(r["messages"][0]["role"] == "system" for rows in c.values() for r in rows), "chat: every record starts with the system message")
check(len({r["id"] for rows in c.values() for r in rows}) == sum(len(rows) for rows in c.values()), "chat: ids are unique")
SYMBOLS = "()/$%=+*-<>^&:;[]\\"
prefix = re.compile(r"^[^:]{1,40}:\s*(?:\(\w+\))?\s*")
raw_count, kept_count = Counter(), Counter()
for part in ("train", "test"):
    for line in open(P.parents[1] / "data" / "raw" / "socratic_chat" / "mathdial" / f"{part}.jsonl", encoding="utf8"):
        for piece in json.loads(line)["conversation"].split("|EOM|"):
            raw_count.update(x for x in prefix.sub("", piece.strip(), count=1) if x in SYMBOLS)
for rows in c.values():
    for r in rows:
        if r["source"] == "mathdial":
            kept_count.update(x for m in r["messages"][1:] for x in m["content"] if x in SYMBOLS)
check(raw_count == kept_count, "chat: every symbol in the original MathDial turns is still there "
      f"('(' {kept_count['(']}, ')' {kept_count[')']}, '/' {kept_count['/']})")

# NCERT (only if it has been built)
chunks = P / "ncert" / "chunks.jsonl"
if chunks.exists():
    c = jsonl(chunks)
    check(len({r["id"] for r in c}) == len(c), "ncert: chunk ids are unique")
    check(all(r["text"].strip() for r in c), "ncert: no empty chunks")
    check({r["subject"] for r in c} == {"maths", "science"}, "ncert: both subjects present")

# Course packs and test scenarios (only if built)
S = Path(__file__).resolve().parents[3] / "data" / "generated" / "test_scenarios"
packs = [json.loads(f.read_text(encoding="utf8")) for f in sorted((Path(__file__).resolve().parents[3] / "presentation" / "course_packs").glob("*.json"))]
if packs:
    for pack in packs:
        ids = {c["id"] for c in pack["concepts"]}
        check(all(p in ids for c in pack["concepts"] for p in c["prerequisites"]),
              f"{pack['id']}: every prerequisite exists")
        check(all(c["questions"] and c["materials"] for c in pack["concepts"]),
              f"{pack['id']}: every concept has questions and study material")
        check(all(q["answer"] and q["hint"] for c in pack["concepts"] for q in c["questions"]),
              f"{pack['id']}: every question has an answer and a hint")
        check(not [q["id"] for c in pack["concepts"] for q in c["questions"]
                   if len(q["answer"]) > 2 and q["answer"].lower() in q["hint"].lower()],
              f"{pack['id']}: no hint contains the answer")
if (S / "backtracking.jsonl").exists():
    concepts = {c["id"] for pack in packs for c in pack["concepts"]}
    bt, mc, gr = (jsonl(S / f"{n}.jsonl") for n in ("backtracking", "misconceptions", "guardrails"))
    check(all(r["target_concept"] in concepts for r in bt), "scenarios: backtracking concepts exist in the packs")
    check(all(r["expected_gap"] is None or r["expected_gap"] in r["weak_concepts"] for r in bt),
          "scenarios: every expected gap is one of the weak concepts")
    check(all(len(r["expected_path"]) == {"gap_one_level": 2, "gap_two_levels": 3}.get(r["type"], 0) for r in bt),
          "scenarios: path length matches the gap type")
    seen = {}
    for r in bt:
        key = (r["target_concept"], r["learner_answer"] == r["correct_answer"], tuple(r["weak_concepts"]),
               json.dumps(r["mastery"], sort_keys=True))
        seen.setdefault(key, set()).add(r["expected_first_action"])
    check(all(len(v) == 1 for v in seen.values()),
          "scenarios: items with the same inputs never have different labels")
    check(all(r["correct_answer"] != r["wrong_answer"] for r in mc), "scenarios: misconception answers are wrong")
    check({r["label"] for r in gr} == {"on_topic", "off_topic", "answer_request"}, "scenarios: all three guardrail labels used")
    all_ids = [r["id"] for r in bt + mc + gr]
    check(len(all_ids) == len(set(all_ids)), "scenarios: ids are unique")

sys.exit(1 if failures else 0)
