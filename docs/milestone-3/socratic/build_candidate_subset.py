"""Candidate subset for fast Socratic-model experiments (Milestone 3).

Samples whole conversations from the Milestone 2 splits with a fixed seed, so no problem
crosses splits. Train/val keep a MathDial share well above its natural 6%, because MathDial
is the on-task (student errors) data. Output: candidate/{train,val,test}.jsonl + stats.json.
"""
import json, random, sys
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "milestone-2/data/processed/socratic_chat"
OUT = Path(__file__).resolve().parent / "candidate"
SIZES = {"train": (600, 1400), "val": (60, 90), "test": (100, 100)}  # (mathdial, socrateach)
SEED = 42


def load(split):
    with open(SRC / f"{split}.jsonl", encoding="utf-8") as f:
        return [json.loads(l) for l in f]


def main():
    OUT.mkdir(exist_ok=True)
    rng = random.Random(SEED)
    stats = {"seed": SEED}
    for split, (n_md, n_st) in SIZES.items():
        rows = load(split)
        picked = []
        for source, n in (("mathdial", n_md), ("socrateach", n_st)):
            pool = [r for r in rows if r["source"] == source]
            picked += rng.sample(pool, min(n, len(pool)))
        rng.shuffle(picked)
        with open(OUT / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for r in picked:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        full_t = sum(len(r["messages"]) for r in rows) / len(rows)
        sub_t = sum(len(r["messages"]) for r in picked) / len(picked)
        stats[split] = {
            "conversations": len(picked),
            "by_source": {s: sum(r["source"] == s for r in picked) for s in ("mathdial", "socrateach")},
            "problems": len({r["problem"] for r in picked}),
            "mean_messages": {"full_split": round(full_t, 2), "subset": round(sub_t, 2)},
        }
    tr = {r["problem"] for r in map(json.loads, open(OUT / "train.jsonl", encoding="utf-8"))}
    for s in ("val", "test"):
        assert not tr & {json.loads(l)["problem"] for l in open(OUT / f"{s}.jsonl", encoding="utf-8")}, s
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    sys.exit(main())
