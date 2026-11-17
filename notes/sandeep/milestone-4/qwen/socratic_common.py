"""Shared helpers for the Milestone 4 Qwen scripts: data loading, chat formatting, encoding, metrics.

Logic is taken from the M3 Qwen notebook (notes/hariom kumar/milestone-3/model_finetune/qwen-finetuning.ipynb)
so M3 and M4 numbers are comparable: same system prompt, same leak definition, same metrics.
"""
import glob
import gzip
import json
import random
import re
from pathlib import Path

SYSTEM = ("You are a Socratic maths tutor. Guide the student one step at a time with questions and hints. "
          "Never state the final answer.\n\nProblem: {question}\n"
          "Correct final answer (for checking only, never reveal it): {answer}")

NUM = re.compile(r"(?<![\d./])-?\d[\d,]*(?:\.\d+)?(?!\d|\.\d|/)")
RUNAWAY = re.compile(r"\n\s*(?:user|assistant|model|system)\s*\n", re.I)


# ---------------------------------------------------------------- data files
def find_file(name, extra_dirs=()):
    """Find <name>.jsonl(.gz) on Kaggle, Colab or next to the repo's processed folder."""
    pats = [f"/kaggle/input/**/{name}.jsonl*", f"/content/{name}.jsonl*", f"/content/drive/MyDrive/**/{name}.jsonl*",
            f"../../hariom kumar/milestone-3/socratic_data_prep/processed/{name}.jsonl*", f"processed/{name}.jsonl*"]
    pats += [f"{d}/{name}.jsonl*" for d in extra_dirs]
    for p in pats:
        hits = sorted(glob.glob(p, recursive=True))
        if hits:
            return Path(hits[0])
    raise FileNotFoundError(f"{name}.jsonl(.gz) not found; attach the processed dataset (see README step 1)")


def read_jsonl(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def split_data(cfg):
    """Return (train_rows, tune_val_rows, report_val_rows, test_rows).

    train        : subset of train.jsonl.gz (all MathDial train + a SocraTeach sample)
    tune_val     : val dialogues used for validation loss / early stopping / sweep objective
    report_val   : DIFFERENT val dialogues, used only to report SocraTeach generation metrics
    test         : MathDial test split, untouched until final evaluation
    All splits are problem-level (done in M3), so no problem appears in two of them.
    """
    rng = random.Random(cfg["seed"])
    train_all, val_all, test = (read_jsonl(find_file(n)) for n in ("train", "val", "test"))
    md = [r for r in train_all if r["source"] == "mathdial"]
    st = [r for r in train_all if r["source"] == "socrateach"]
    n_st = max(0, cfg["n_train"] - len(md))
    train = md + rng.sample(st, min(n_st, len(st)))
    rng.shuffle(train)
    ids = sorted(r["dialogue_id"] for r in val_all)
    rng.shuffle(ids)
    tune_ids = set(ids[:cfg["val_dialogues"]])
    tune = [r for r in val_all if r["dialogue_id"] in tune_ids]
    report = [r for r in val_all if r["dialogue_id"] not in tune_ids and r["source"] == "socrateach"]
    report = rng.sample(report, min(cfg["report_socrateach"], len(report)))
    problems = lambda rows: {r["problem_id"] for r in rows}
    for a, b in ((train, tune), (train, report), (train, test), (tune, report)):
        assert not (problems(a) & problems(b)), "a problem appears in two splits"
    return train, tune, report, test


# ---------------------------------------------------------------- tokenizer / chat format
class Prep:
    def __init__(self, tok, max_len):
        self.tok, self.max_len = tok, max_len
        probe = self.template([{"role": "user", "content": "U"}, {"role": "assistant", "content": "QQQ"}])
        self.end_of_turn = probe[probe.index("QQQ") + 3:].split("\n")[0]       # "<|im_end|>" for Qwen
        ids = tok.encode(self.end_of_turn, add_special_tokens=False)
        self.stop_ids = sorted({tok.eos_token_id, *(ids if len(ids) == 1 else [])} - {None})

    def template(self, msgs, generation_prompt=False):
        return self.tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=generation_prompt,
                                            enable_thinking=False)

    @staticmethod
    def chat_messages(rec, upto=None):
        sys_msg = SYSTEM.format(question=rec["question"], answer=rec["reference_answer"])
        if rec.get("student_attempt"):
            sys_msg += "\n\nStudent's first attempt:\n" + rec["student_attempt"]
        msgs = rec["messages"] if upto is None else rec["messages"][:upto]
        return [{"role": "system", "content": sys_msg}] + [
            {"role": "assistant" if m["role"] == "tutor" else "user", "content": m["content"]} for m in msgs]

    def render(self, rec, n):
        msgs = self.chat_messages(rec, n)
        if not any(m["role"] == "user" for m in msgs):
            return None, None
        text, spans, pos = self.template(msgs), [], 0
        for i, m in enumerate(msgs):
            if m["role"] != "assistant":
                continue
            start = text.find(m["content"] + self.end_of_turn, pos)
            if start < 0:
                return None, None
            end = start + len(m["content"]) + len(self.end_of_turn)
            src = rec["messages"][i - 1]
            # tutor turns flagged as telling or leaking the answer stay as context but are never targets
            spans.append((start, end, src.get("move") != "telling" and not src.get("leaks_answer", False)))
            pos = end
        return text, spans

    def encode(self, rec):
        n = len(rec["messages"])
        while n > 0:   # cut back to the last tutor turn that fits in max_len
            if rec["messages"][n - 1]["role"] == "tutor":
                text, spans = self.render(rec, n)
                if text is None:
                    return None
                enc = self.tok(text, return_offsets_mapping=True, add_special_tokens=False)
                if len(enc["input_ids"]) <= self.max_len:
                    break
            n -= 1
        if n == 0:
            return None
        labels = [-100] * len(enc["input_ids"])
        for k, (a, b) in enumerate(enc["offset_mapping"]):
            if any(ok and a >= s and b <= e for s, e, ok in spans):
                labels[k] = enc["input_ids"][k]
        if all(l == -100 for l in labels):
            return None
        return dict(dialogue_id=rec["dialogue_id"], source=rec["source"], input_ids=enc["input_ids"],
                    labels=labels, cut=n < len(rec["messages"]))


# ---------------------------------------------------------------- evaluation points and metrics
def numbers(text):
    return {n.replace(",", "").rstrip("0").rstrip(".") if "." in n else n.replace(",", "") for n in NUM.findall(text)}


def answer_key(rec):
    found = numbers(rec["reference_answer"])
    key = found.pop() if len(found) == 1 else None
    return None if key in numbers(rec["question"]) else key


def eval_points(rows, seed):
    """One random tutor turn per dialogue. Stored as plain chat messages so any model or API can use them."""
    rng, pts = random.Random(seed), []
    for rec in rows:
        idx = [i for i, m in enumerate(rec["messages"]) if m["role"] == "tutor" and i > 0
               and rec["messages"][i - 1]["role"] == "student"]
        if not idx:
            continue
        i = rng.choice(idx)
        key = answer_key(rec)
        said = key is not None and any(key in numbers(m["content"]) for m in rec["messages"][:i] if m["role"] == "student")
        pts.append(dict(dialogue_id=rec["dialogue_id"], turn=i, source=rec["source"], key=key, student_said=said,
                        messages=Prep.chat_messages(rec, i), reference=rec["messages"][i]["content"]))
    return pts


def score(replies, pts):
    """Leak rate, question rate, words, ROUGE-L, BLEU: overall and per source (same definitions as M3)."""
    import numpy as np
    import sacrebleu
    from rouge_score import rouge_scorer
    sc = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    rows = [dict(source=p["source"], leak=p["key"] is not None and not p["student_said"] and p["key"] in numbers(r),
                 question="?" in r, words=len(r.split()), rougeL=sc.score(p["reference"], r)["rougeL"].fmeasure)
            for r, p in zip(replies, pts)]

    def summary(mask):
        sel = [d for d, m in zip(rows, mask) if m]
        rs = [r for r, m in zip(replies, mask) if m]
        refs = [p["reference"] for p, m in zip(pts, mask) if m]
        if not sel:
            return {}
        return dict(n=len(sel), leak_rate=round(float(np.mean([d["leak"] for d in sel])), 4),
                    question_rate=round(float(np.mean([d["question"] for d in sel])), 4),
                    words=round(float(np.mean([d["words"] for d in sel])), 2),
                    rougeL=round(float(np.mean([d["rougeL"] for d in sel])), 4),
                    bleu=round(sacrebleu.corpus_bleu(rs, [refs]).score / 100, 4))

    out = summary([True] * len(rows))
    out["by_source"] = {s: summary([d["source"] == s for d in rows]) for s in ("socrateach", "mathdial")}
    return out
