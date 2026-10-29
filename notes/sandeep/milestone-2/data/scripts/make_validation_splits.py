"""Derive validation splits from Hariom Pandey's prepared data, without changing his files.

His DKT arrays have train/test only, and his chat corpus has no split. This script lists a validation
subset of each, as indices into his files, in hosted_dataset/splits/.

  dkt_validation.json   train sequences (row numbers of X_tr etc.) belonging to 10% of the train
                        students, chosen at random (seed 42). Split by student, so no student is in
                        both validation and the rest of train.
  chat_validation.json  line numbers of the MathDial conversations of 10% of the MathDial problems
                        (seed 42). Split by problem, because several dialogues share one problem.
                        SocraTeach dialogues have no problem text in their messages, so they cannot be
                        grouped and stay in train.

Usage: python notes/sandeep/milestone-2/data/scripts/make_validation_splits.py
"""
import json
import random
import re
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
B = HERE.parents[4] / "hariom pandey" / "milestone-2"
OUT = HERE.parents[2] / "hosted_dataset" / "splits"
SEED, FRACTION = 42, 0.10


def dkt():
    d = np.load(B / "dkt_processed" / "dkt_data.npz")
    steps = pd.read_csv(B / "dkt_processed" / "dkt_processed_steps.csv")
    tr = steps[steps.split == "train"]
    seq = tr.groupby("chunk_id").agg(user=("user_id", "first"), n=("step", "size")).sort_index()
    assert len(seq) == d["X_tr"].shape[0], "chunk_id does not match the train rows"
    assert (seq.n.values == d["M_tr"].sum(axis=1)).all(), "sequence lengths differ from the mask"
    students = sorted(seq.user.unique())
    rng = random.Random(SEED)
    val_students = set(rng.sample(students, round(len(students) * FRACTION)))
    val_idx = [int(i) for i, u in seq.user.items() if u in val_students]
    M = d["M_tr"] == 1
    n_val = int(M[val_idx].sum())
    return {"seed": SEED, "fraction": FRACTION, "unit": "student",
            "train_students": len(students), "validation_students": len(val_students),
            "train_sequences_total": int(len(seq)), "validation_sequences": len(val_idx),
            "validation_answers": n_val, "remaining_train_answers": int(M.sum()) - n_val,
            "validation_correct_rate": round(float(d["C_tr"][val_idx][M[val_idx]].mean()), 3),
            "validation_train_sequence_indices": val_idx}


PROBLEM = re.compile(r"following problem:\s*(.*)", re.S)


def chat():
    rows = []
    with open(B / "socratic_tutor_combined.jsonl", encoding="utf8") as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            if r["source"] == "mathdial":
                m = PROBLEM.search(r["messages"][0]["content"])
                assert m, f"line {i}: no problem text in the system message"
                rows.append((i, m.group(1).strip()))
    problems = sorted({p for _, p in rows})
    rng = random.Random(SEED)
    val_problems = set(rng.sample(problems, round(len(problems) * FRACTION)))
    val_lines = [i for i, p in rows if p in val_problems]
    return {"seed": SEED, "fraction": FRACTION, "unit": "problem (MathDial only)",
            "mathdial_conversations": len(rows), "mathdial_problems": len(problems),
            "validation_problems": len(val_problems), "validation_conversations": len(val_lines),
            "validation_line_numbers_0_based": val_lines}


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, result in (("dkt_validation.json", dkt()), ("chat_validation.json", chat())):
        (OUT / name).write_text(json.dumps(result), encoding="utf8")
        print(name, {k: v for k, v in result.items() if not isinstance(v, list)})
