"""Extract and print basic information from dkt_data.npz.

Usage: python test_dkt_data.py [path/to/dkt_data.npz]
"""
import sys
from pathlib import Path

import numpy as np

path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("dkt_data.npz")
d = np.load(path)

print("Arrays:")
for k in d.files:
    print(f"  {k:5s} shape={d[k].shape} dtype={d[k].dtype}")

n_skills = int(d["N"])
print(f"\nNumber of skills (N): {n_skills}")

for split in ("tr", "te"):
    X, S, C, M = (d[f"{a}_{split}"] for a in "XSCM")
    mask = M == 1
    lengths = M.sum(axis=1)
    print(f"\n[{split}] sequences={X.shape[0]}, max_len={X.shape[1]}")
    print(f"  total interactions : {mask.sum()}")
    print(f"  seq length min/mean/max: {lengths.min()} / {lengths.mean():.1f} / {lengths.max()}")
    print(f"  overall correct rate  : {C[mask].mean():.3f}")
    print(f"  distinct skills used  : {len(np.unique(S[mask]))}")
    print(f"  X == S + N*C on valid steps: {bool((X[mask] == S[mask] + n_skills * C[mask]).all())}")

# Per-skill stats on the training split
S, C, M = d["S_tr"], d["C_tr"], d["M_tr"] == 1
counts = np.bincount(S[M], minlength=n_skills)
correct = np.bincount(S[M], weights=C[M], minlength=n_skills)
print("\nTop 5 most attempted skills (train): skill_index, attempts, correct rate")
for s in np.argsort(counts)[::-1][:5]:
    print(f"  {s:3d}  {counts[s]:6d}  {correct[s] / counts[s]:.3f}")

# First sequence preview
L = int(d["M_tr"][0].sum())
print(f"\nFirst train sequence (length {L}), first 10 steps:")
print("  skill  :", d["S_tr"][0][:10].tolist())
print("  correct:", d["C_tr"][0][:10].tolist())
print("  x      :", d["X_tr"][0][:10].tolist())
