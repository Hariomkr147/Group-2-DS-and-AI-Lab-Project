"""MathDial + SocraTeach -> one chat corpus with hybrid train / validation / test splits.

Replaces the Colab steps that built the first combined file. Two things changed:

1. MathDial is built from the ORIGINAL release (eth-nlped/mathdial), not from the `mathdial-chat` copy on
   Hugging Face. That copy dropped 458 closing ")" (e.g. "(3rd)" became "(3rd") and merged consecutive teacher
   turns, sometimes repeating text, in 544 of 2,262 conversations. Here every character of every turn is kept
   (checked below) and consecutive turns of one speaker are joined with a space.
2. The source tag is spelled `socrateach` (the first file had a misspelt tag).

Steps
  1 MathDial: parse "Teacher: (act)text|EOM|Student: text" into messages, keep the act label of each tutor turn
  2 SocraTeach: parse each dialogue's turns (tutor = assistant, student = user)
  3 Both: add the same system message with the problem, flag tutor turns that contain the final answer
  4 Check: no character lost, no empty message, roles alternate, source tags correct
  5 Split by PROBLEM across both sources (same problem text -> same split), so validation and test are a
    hybrid of MathDial and SocraTeach and no problem is seen in training

Usage: python prep_chat.py        (needs raw/mathdial/{train,test}.jsonl and raw/socrateach/train.parquet; see download.py)
Output: processed/chat/train.jsonl, val.jsonl, test.jsonl, stats.json
"""
import json
import random
import re
from collections import Counter
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "processed" / "chat"
SEED = 42
MIXED_FRACTION = 0.10     # of the problems that MathDial also covers, per held-out split
ONLY_FRACTION = 0.01      # of the SocraTeach-only problems, per held-out split

SYSTEM = "You are a friendly and supportive teacher.\nThe student is trying to solve the following problem: {question}"
TURN = re.compile(r"^([^:]{1,40}):\s*(?:\((\w+)\))?\s*(.*)$", re.S)


def key(question: str) -> str:
    return re.sub(r"\s+", " ", question).strip().lower().rstrip(".?! ")


def leaks(text: str, answer: str) -> bool:
    answer = answer.replace(",", "").strip()
    return bool(answer) and re.search(rf"(?<![\d.]){re.escape(answer)}(?![\d]|\.\d)", text.replace(",", "")) is not None


def final_answer(ground_truth: str) -> str:
    return ground_truth.strip().splitlines()[-1].strip().replace("$", "").replace(",", "")


def join_turns(turns: list) -> tuple[list, int]:
    """[(role, act, text)] -> alternating messages; consecutive turns of one role are joined with a space."""
    msgs, merged = [], 0
    for role, act, text in turns:
        if msgs and msgs[-1]["role"] == role:
            msgs[-1]["content"] += " " + text
            msgs[-1]["acts"].append(act)
            merged += 1
        else:
            msgs.append({"role": role, "content": text, "acts": [act]})
    return msgs, merged


def mathdial_records(stats: Counter) -> list:
    out = []
    for part in ("train", "test"):
        for n, line in enumerate(open(RAW / "mathdial" / f"{part}.jsonl", encoding="utf8")):
            r = json.loads(line)
            turns = []
            for piece in r["conversation"].split("|EOM|"):
                m = TURN.match(piece.strip())
                if not m:  # no "Speaker:" prefix: text that continues the previous turn
                    if turns and piece.strip():
                        role, act, text = turns[-1]
                        turns[-1] = (role, act, text + " " + piece.strip())
                        stats["mathdial_continuation_pieces_joined"] += 1
                    continue
                speaker, act, text = m.groups()
                if not text.strip():
                    stats["mathdial_empty_turns_removed"] += 1
                    continue
                turns.append(("assistant" if speaker == "Teacher" else "user", act or "", text.strip()))
            msgs, merged = join_turns(turns)
            stats["mathdial_turns_merged"] += merged
            # check: every character (ignoring whitespace) of every turn is still there
            kept = Counter("".join("".join(m["content"].split()) for m in msgs))
            orig = Counter("".join("".join(t.split()) for _, _, t in turns))
            assert kept == orig, f"mathdial {part} {n}: characters lost"
            out.append(dict(source="mathdial", id=f"mathdial-{part}-{n}", question=r["question"].strip(),
                            answer=final_answer(r["ground_truth"]), messages=msgs))
    return out


def socrateach_records(stats: Counter) -> list:
    df = pd.read_parquet(RAW / "socrateach" / "train.parquet")
    out = []
    for _, row in df.iterrows():
        for d in row["dialogues"]:
            turns = []
            for t in d["turns"]:
                t = json.loads(t) if isinstance(t, str) else t
                tutor, student = (t.get("system") or "").strip(), (t.get("user") or "").strip()
                if tutor:
                    turns.append(("assistant", "", tutor))
                else:
                    stats["socrateach_missing_tutor_text"] += 1
                if student:
                    turns.append(("user", "", student))
            msgs, merged = join_turns(turns)
            stats["socrateach_turns_merged"] += merged
            if {m["role"] for m in msgs} != {"assistant", "user"}:
                stats["socrateach_dialogues_skipped"] += 1
                continue
            out.append(dict(source="socrateach", id=d["dialogue_id"], question=row["question"].strip(),
                            answer=str(row["answer"]).replace(",", "").strip(), messages=msgs))
    return out


def finish(rec: dict) -> dict:
    """Add the system message and the labels; drop the working fields."""
    msgs = [{"role": "system", "content": SYSTEM.format(question=rec["question"])}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in rec["messages"]]
    tutor = [m for m in rec["messages"] if m["role"] == "assistant"]
    acts = [m["acts"][0] for m in tutor]  # act label of each tutor message (first piece if merged)
    return {"source": rec["source"], "id": rec["id"], "problem": key(rec["question"]),
            "messages": msgs,
            "tutor_acts": acts if rec["source"] == "mathdial" else None,
            "tutor_leaks_answer": [leaks(m["content"], rec["answer"]) for m in tutor]}


def check(rows: list):
    for r in rows:
        assert r["source"] in {"mathdial", "socrateach"}, r["source"]
        roles = [m["role"] for m in r["messages"]]
        assert roles[0] == "system" and all(a != b for a, b in zip(roles[1:], roles[2:])), r["id"]
        assert all(m["content"].strip() for m in r["messages"]), r["id"]
        json.dumps(r, ensure_ascii=False)
    assert len({r["id"] for r in rows}) == len(rows), "duplicate ids"


def split(rows: list) -> dict:
    by_problem: dict = {}
    for r in rows:
        by_problem.setdefault(r["problem"], []).append(r)
    mixed = sorted(p for p, rs in by_problem.items() if any(r["source"] == "mathdial" for r in rs))
    only = sorted(p for p in by_problem if p not in set(mixed))
    rng = random.Random(SEED)
    rng.shuffle(mixed), rng.shuffle(only)
    n_m, n_o = round(len(mixed) * MIXED_FRACTION), round(len(only) * ONLY_FRACTION)
    assign = {}
    for name, a, b in (("test", 0, 1), ("val", 1, 2)):
        for p in mixed[a * n_m:b * n_m] + only[a * n_o:b * n_o]:
            assign[p] = name
    out = {"train": [], "val": [], "test": []}
    for r in rows:
        out[assign.get(r["problem"], "train")].append(r)
    return out


def main():
    stats: Counter = Counter()
    rows = [finish(r) for r in mathdial_records(stats) + socrateach_records(stats)]
    check(rows)
    parts = split(rows)
    seen = [{r["problem"] for r in parts[s]} for s in ("train", "val", "test")]
    assert not (seen[0] & seen[1] or seen[0] & seen[2] or seen[1] & seen[2]), "problem in two splits"

    OUT.mkdir(parents=True, exist_ok=True)
    summary = {"seed": SEED, "cleaning": dict(stats), "splits": {}}
    for name, rs in parts.items():
        with open(OUT / f"{name}.jsonl", "w", encoding="utf8") as f:
            f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rs)
        tutor = [m for r in rs for m in r["messages"] if m["role"] == "assistant"]
        summary["splits"][name] = {
            "conversations": len(rs), "problems": len({r["problem"] for r in rs}),
            "by_source": dict(Counter(r["source"] for r in rs)),
            "tutor_messages": len(tutor),
            "tutor_messages_leaking_answer": sum(sum(r["tutor_leaks_answer"]) for r in rs),
            "mathdial_acts": dict(Counter(a for r in rs if r["tutor_acts"] for a in r["tutor_acts"]))}
    (OUT / "stats.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
