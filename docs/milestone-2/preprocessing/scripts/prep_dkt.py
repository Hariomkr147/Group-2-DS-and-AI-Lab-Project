"""ASSISTments 2009-2010 skill builder -> DKT arrays (script version of the first Colab notebook).

Steps (each prints its row count; the counts are saved to processed/dkt/stats.json):
  1 load 4 columns            2 drop rows with missing values      3 drop duplicates (student, order, skill)
  4 drop students with < 3 answers
  5 number the skills 0..N-1  6 encode each answer as x = skill + N * correct
  7 sort by student and order 8 cut each history into chunks of 200, drop chunks < 3, pad, build mask
  9 split by STUDENT 80/20 (seed 42)
 10 validation = 10% of the train students (seed 42), written as sequence indices

The frozen arrays the team models on (hosted_dataset/assistments_dkt, 82 skills) came from the first Colab
notebook, which started from a 303,260-row file. Run on the Drive file linked in the report (525,534 rows) this
script gives 123 skills, so the numbers differ; `--compare` reports, array by array, whether a run reproduces
the frozen arrays.

Usage: python prep_dkt.py [--input FILE] [--compare ../../hosted_dataset/assistments_dkt]
Input:  raw/assistments_2009/sb.csv   (skill_builder_data.csv)
Output: processed/dkt/dkt_data.npz, dkt_validation.json, skill_map.csv, stats.json
"""
import argparse
import json
import random
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "assistments_2009" / "sb.csv"
OUT = ROOT / "processed" / "dkt"
MAX_LEN, MIN_LEN, SEED, TEST_FRACTION, VAL_FRACTION = 200, 3, 42, 0.2, 0.1


def clean(log: list, path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="ISO-8859-15", usecols=["order_id", "user_id", "skill_id", "correct"])
    log.append(("1 load", len(df)))
    df = df.dropna()
    log.append(("2 drop missing", len(df)))
    df = df.drop_duplicates(["user_id", "order_id", "skill_id"]).astype(int)
    log.append(("3 drop duplicates", len(df)))
    lens = df.groupby("user_id").size()
    df = df[df["user_id"].isin(lens[lens >= MIN_LEN].index)]
    log.append(("4 drop students < 3 answers", len(df)))
    return df


def encode(df: pd.DataFrame):
    skills = sorted(df["skill_id"].unique())
    skill_map = {s: i for i, s in enumerate(skills)}
    n = len(skills)
    df = df.sort_values(["user_id", "order_id"], kind="stable").copy()
    df["sk"] = df["skill_id"].map(skill_map)
    df["x"] = df["sk"] + n * df["correct"]
    return df, skill_map, n


def chunks_of(df: pd.DataFrame, users) -> list:
    groups = {u: d for u, d in df.groupby("user_id")}
    return [(u, groups[u].iloc[s:s + MAX_LEN]) for u in users for s in range(0, len(groups[u]), MAX_LEN)
            if len(groups[u].iloc[s:s + MAX_LEN]) >= MIN_LEN]


def arrays(chunks: list):
    X, S, C, M = (np.zeros((len(chunks), MAX_LEN), dtype=np.int64) for _ in range(4))
    for i, (_, p) in enumerate(chunks):
        k = len(p)
        X[i, :k], S[i, :k], C[i, :k], M[i, :k] = p["x"], p["sk"], p["correct"], 1
    return X, S, C, M


def main(compare: str | None, path: Path):
    log: list = []
    df, skill_map, n = encode(clean(log, path))
    users = np.array(sorted(df["user_id"].unique()))
    np.random.default_rng(SEED).shuffle(users)
    cut = int((1 - TEST_FRACTION) * len(users))
    train_users, test_users = users[:cut], users[cut:]
    tr_chunks, te_chunks = chunks_of(df, train_users), chunks_of(df, test_users)
    X_tr, S_tr, C_tr, M_tr = arrays(tr_chunks)
    X_te, S_te, C_te, M_te = arrays(te_chunks)

    real = M_tr == 1
    assert ((S_tr + n * C_tr)[real] == X_tr[real]).all(), "x formula broken"
    assert not set(train_users) & set(test_users), "a student is in both splits"
    log.append(("8 chunks of 200, kept", int(M_tr.sum() + M_te.sum())))

    # validation: whole students out of the train students
    seq_user = [u for u, _ in tr_chunks]
    val_students = set(random.Random(SEED).sample(sorted(set(seq_user)), round(len(set(seq_user)) * VAL_FRACTION)))
    val_idx = [i for i, u in enumerate(seq_user) if u in val_students]
    val_mask = M_tr[val_idx] == 1
    validation = {"seed": SEED, "fraction": VAL_FRACTION, "unit": "student",
                  "validation_students": len(val_students), "validation_sequences": len(val_idx),
                  "validation_answers": int(val_mask.sum()),
                  "validation_correct_rate": round(float(C_tr[val_idx][val_mask].mean()), 3),
                  "validation_train_sequence_indices": val_idx}

    OUT.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(OUT / "dkt_data.npz", X_tr=X_tr, S_tr=S_tr, C_tr=C_tr, M_tr=M_tr,
                        X_te=X_te, S_te=S_te, C_te=C_te, M_te=M_te, N=n)
    (OUT / "dkt_validation.json").write_text(json.dumps(validation))
    lens = df.groupby("user_id").size()
    stats = {"steps": [{"step": s, "rows": r} for s, r in log], "skills": n,
             "students": int(len(users)), "train_students": len(train_users), "test_students": len(test_users),
             "train_sequences": len(tr_chunks), "test_sequences": len(te_chunks),
             "train_answers": int(M_tr.sum()), "test_answers": int(M_te.sum()),
             "correct_rate_train": round(float(C_tr[real].mean()), 3),
             "correct_rate_test": round(float(C_te[M_te == 1].mean()), 3),
             "history_length": {"median": float(lens.median()), "max": int(lens.max()),
                                "share_over_200": round(float((lens > MAX_LEN).mean()), 3)},
             "validation": {k: v for k, v in validation.items() if not isinstance(v, list)}}
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    pd.DataFrame({"skill_index": list(skill_map.values()), "skill_id_original": list(skill_map)}
                 ).to_csv(OUT / "skill_map.csv", index=False)
    print(json.dumps(stats, indent=2))

    if compare:
        ref = np.load(Path(compare) / "dkt_data.npz")
        mine = np.load(OUT / "dkt_data.npz")
        print("identical to the frozen arrays:", {k: bool(np.array_equal(ref[k], mine[k])) for k in ref.files})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare")
    ap.add_argument("--input", type=Path, default=RAW)
    a = ap.parse_args()
    main(a.compare, a.input)
