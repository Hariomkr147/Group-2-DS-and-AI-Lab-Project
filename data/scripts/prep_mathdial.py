"""Turn MathDial tutoring dialogues into training examples for the Socratic model.

Each dialogue is cut into one example per teacher turn: given the problem and the
conversation so far, the target is the next teacher reply.

Every teacher reply keeps MathDial's own label (probing / focus / generic / telling).
`keep` is true only for replies we want the model to imitate: not "telling" and not
containing the final answer. Replies that tell or leak are still saved (for analysis
and for the answer-leakage baseline) but are not used as training targets.

Splits: MathDial's own test set is kept as our test set. Validation is carved out of
train BY PROBLEM (qid), because the same problem is solved in several dialogues and
splitting by dialogue would leak it into training.

Output (data/processed/mathdial/): train/val/test.jsonl, stats.json
"""
import json
import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw" / "mathdial"
OUT = ROOT / "processed" / "mathdial"
SEED, VAL_FRACTION = 42, 0.1

SYSTEM = ("You are a patient maths tutor. Guide the student to the answer with short probing "
          "questions, one at a time. Never state the final answer.\n\n"
          "Problem: {question}\nReference solution (hidden from the student): {solution}")
TURN = re.compile(r"^(Teacher|[^:]{1,40}): ?(?:\((\w+)\))? ?(.*)$", re.S)


def final_answer(ground_truth: str) -> str:
    return ground_truth.strip().splitlines()[-1].strip().replace(",", "")


def leaks(text: str, answer: str) -> bool:
    return bool(answer) and re.search(rf"(?<![\d.]){re.escape(answer)}(?![\d]|\.\d)", text.replace(",", "")) is not None


def parse(conversation: str):
    for raw in conversation.split("|EOM|"):
        m = TURN.match(raw.strip())
        if m:
            speaker, act, text = m.groups()
            yield ("tutor" if speaker == "Teacher" else "student"), (act or "unknown"), text.strip()


def examples(row: dict):
    answer = final_answer(row["ground_truth"])
    solution = row["ground_truth"].strip().replace("\n", " ")
    turns = list(parse(row["conversation"]))
    for i, (role, act, text) in enumerate(turns):
        if role != "tutor" or not text:
            continue
        messages = [{"role": "system", "content": SYSTEM.format(question=row["question"], solution=solution)}]
        # the student's first message is their (wrong) solution, which the tutor reacts to
        messages.append({"role": "user", "content": row["student_incorrect_solution"].strip()})
        messages += [{"role": "assistant" if r == "tutor" else "user", "content": t}
                     for r, _, t in turns[:i] if t]
        leak = leaks(text, answer)
        yield {"qid": row["qid"], "turn": i, "messages": messages, "target": text,
               "act": act, "leaks_answer": leak, "keep": act != "telling" and not leak,
               "dialogue_outcome": row["self-correctness"]}


def read(name: str) -> list[dict]:
    with open(RAW / f"{name}.jsonl", encoding="utf8") as f:
        return [json.loads(line) for line in f]


def write(name: str, rows: list[dict]) -> dict:
    with open(OUT / f"{name}.jsonl", "w", encoding="utf8") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    acts = Counter(r["act"] for r in rows)
    return {"examples": len(rows), "kept": sum(r["keep"] for r in rows),
            "leaks_answer": sum(r["leaks_answer"] for r in rows), "acts": dict(acts)}


def main():
    train_rows, test_rows = read("train"), read("test")
    qids = sorted({r["qid"] for r in train_rows})
    random.Random(SEED).shuffle(qids)
    val_qids = set(qids[:int(len(qids) * VAL_FRACTION)])
    split = {"train": [r for r in train_rows if r["qid"] not in val_qids],
             "val": [r for r in train_rows if r["qid"] in val_qids], "test": test_rows}

    OUT.mkdir(parents=True, exist_ok=True)
    stats = {}
    for name, rows in split.items():
        stats[name] = {"dialogues": len(rows), "problems": len({r["qid"] for r in rows}),
                       **write(name, [e for r in rows for e in examples(r)])}
    train_q = {r["qid"] for r in split["train"]}
    stats["test"]["problems_also_in_train"] = len({r["qid"] for r in test_rows} & train_q)
    (OUT / "stats.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
