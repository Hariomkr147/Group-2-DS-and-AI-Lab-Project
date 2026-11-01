"""Derive a validation split for the frozen DKT arrays, without changing them.

The frozen arrays (processed/assistments/frozen) have train/test only. This script lists a validation
subset as row numbers of the train arrays, in processed/assistments/frozen/dkt_validation.json: the train sequences
of 10% of the train students, chosen at random (seed 42). Split by student, so no student is in both
validation and the rest of train. (The chat corpus makes its own splits in prep_chat.py.)

Usage: python docs/milestone-2/data/scripts/assistments/make_validation_splits.py
"""
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve()
FROZEN = HERE.parents[3] / "data" / "processed" / "assistments" / "frozen"
OUT = FROZEN
SEED, FRACTION = 42, 0.10


def dkt():
    d = np.load(FROZEN / "dkt_data.npz")
    steps = pd.read_csv(FROZEN / "dkt_processed_steps.csv")
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


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, result in (("dkt_validation.json", dkt()),):
        (OUT / name).write_text(json.dumps(result), encoding="utf8")
        print(name, {k: v for k, v in result.items() if not isinstance(v, list)})
