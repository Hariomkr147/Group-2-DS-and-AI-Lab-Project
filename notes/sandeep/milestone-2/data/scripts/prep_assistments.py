"""Clean ASSISTments 2009-2010 (corrected) and split it for knowledge tracing.

Steps (same recipe as the pyKT benchmark, so results can be compared with it):
  1. keep the columns we need; sort each student's answers by order_id (time order)
  2. drop rows with no skill (they cannot be used to track a concept)
  3. drop students with fewer than 3 answers
  4. map skill_id to a contiguous concept index 0..K-1
  5. cut each student's history into windows of at most 200 answers
  6. split BY STUDENT into train / validation / test, so no student is in two sets

Output (notes/sandeep/milestone-2/data/processed/assistments/):
  interactions.csv   clean row-per-answer table
  train/val/test.jsonl   one window per line: {user_id, skills, correct}
  skill_map.csv      concept index <-> skill_id <-> skill_name
  stats.json         counts for the report
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "assistments" / "skill_builder_data_corrected.csv"
OUT = ROOT / "processed" / "assistments"
SEED, MAX_LEN, MIN_LEN = 42, 200, 3
SPLIT = {"train": 0.8, "val": 0.1, "test": 0.1}


def clean(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw[["order_id", "user_id", "problem_id", "skill_id", "skill_name",
              "correct", "hint_count", "attempt_count", "original"]].copy()
    df = df.drop_duplicates(subset="order_id")
    df = df.dropna(subset=["skill_id"])
    df = df[df["correct"].isin([0, 1])]
    df["skill_id"] = df["skill_id"].astype(int)
    df["correct"] = df["correct"].astype(int)
    df = df.sort_values(["user_id", "order_id"], kind="stable")
    df = df[df.groupby("user_id")["order_id"].transform("size") >= MIN_LEN]
    return df.reset_index(drop=True)


def split_users(users: np.ndarray) -> dict[str, np.ndarray]:
    users = np.random.default_rng(SEED).permutation(users)
    n_train, n_val = int(len(users) * SPLIT["train"]), int(len(users) * SPLIT["val"])
    return {"train": users[:n_train], "val": users[n_train:n_train + n_val],
            "test": users[n_train + n_val:]}


def windows(df: pd.DataFrame, users: np.ndarray, skill_index: dict[int, int]):
    for uid, g in df[df["user_id"].isin(set(users))].groupby("user_id", sort=True):
        skills = [skill_index[s] for s in g["skill_id"]]
        correct = g["correct"].tolist()
        for i in range(0, len(skills), MAX_LEN):
            if len(skills[i:i + MAX_LEN]) >= MIN_LEN:
                yield {"user_id": int(uid), "skills": skills[i:i + MAX_LEN],
                       "correct": correct[i:i + MAX_LEN]}


def main():
    raw = pd.read_csv(RAW, encoding="latin-1", low_memory=False)
    df = clean(raw)

    ids = sorted(df["skill_id"].unique())
    skill_index = {s: i for i, s in enumerate(ids)}
    df["skill"] = df["skill_id"].map(skill_index)
    names = df.groupby("skill_id")["skill_name"].agg(lambda s: s.dropna().iloc[0] if s.notna().any() else "")
    skill_map = pd.DataFrame({"skill": range(len(ids)), "skill_id": ids,
                              "skill_name": [names[s] for s in ids]})

    OUT.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT / "interactions.csv", index=False)
    skill_map.to_csv(OUT / "skill_map.csv", index=False)

    stats = {"raw_rows": len(raw), "raw_students": int(raw["user_id"].nunique()),
             "rows_without_skill": int(raw["skill_id"].isna().sum()),
             "clean_rows": len(df), "clean_students": int(df["user_id"].nunique()),
             "skills": len(ids), "problems": int(df["problem_id"].nunique()),
             "correct_rate": round(float(df["correct"].mean()), 4), "splits": {}}
    for name, users in split_users(df["user_id"].unique()).items():
        rows = list(windows(df, users, skill_index))
        with open(OUT / f"{name}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
        answers = sum(len(r["skills"]) for r in rows)
        pos = sum(sum(r["correct"]) for r in rows)
        stats["splits"][name] = {"students": len(users), "windows": len(rows),
                                 "answers": answers, "correct_rate": round(pos / answers, 4)}
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
