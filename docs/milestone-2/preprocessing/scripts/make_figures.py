"""Figures for the Milestone 2 report (docs/milestone-2/figures/).

Reads the frozen DKT arrays (hosted_dataset/assistments_dkt), the rebuilt chat corpus (processed/chat/), the
test scenarios and the detector score. Run after prep_chat.py and eval_misconception.py.
"""
import json
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT.parent
FIG = DOCS / "figures"
DKT = np.load(DOCS / "hosted_dataset" / "assistments_dkt" / "dkt_data.npz")
P = ROOT / "processed"
# Symbol counts in the 2,262 MathDial training conversations of the first chat file (built from the Hugging Face
# `mathdial-chat` copy), measured once; the rebuilt corpus is counted below.
FIRST_FILE = {"(": 3498, ")": 3052, "/": 4099}
NAVY, BLUE, GREY, RED, GREEN = "#1f3a5f", "#3b7dd8", "#8a94a6", "#c0504d", "#4f9d69"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=170)
    plt.close(fig)
    print("wrote", name)


def jsonl(path):
    with open(path, encoding="utf8") as f:
        return [json.loads(line) for line in f]


def dkt_figures():
    real = DKT["M_tr"] == 1
    skills = np.concatenate([DKT["S_tr"][real], DKT["S_te"][DKT["M_te"] == 1]])
    correct = np.concatenate([DKT["C_tr"][real], DKT["C_te"][DKT["M_te"] == 1]])
    n = int(DKT["N"])
    counts = np.bincount(skills, minlength=n)
    rate = np.array([correct[skills == k].mean() if counts[k] else np.nan for k in range(n)])

    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    ax[0].bar(range(n), np.sort(counts)[::-1], color=BLUE, width=1.0)
    ax[0].axhline(100, color=RED, lw=1, ls="--")
    ax[0].set(title=f"Answers per skill ({n} skills)", xlabel="Skills, most to least answers", ylabel="Answers")
    ax[0].text(n * 0.5, counts.max() * 0.6, f"{(counts < 100).sum()} skills have\nunder 100 answers\n(red line)", color=RED)

    lengths = np.concatenate([DKT["M_tr"].sum(1), DKT["M_te"].sum(1)])
    ax[1].hist(lengths, bins=40, color=BLUE)
    ax[1].set(title="Steps per sequence (model input)", xlabel="Steps (200 = cut-off)", ylabel="Sequences")
    ax[1].text(120, ax[1].get_ylim()[1] * 0.8, f"{(lengths == 200).mean():.0%} reach 200", color=RED)

    ax[2].hist(rate[~np.isnan(rate)], bins=20, color=BLUE)
    ax[2].axvline(correct.mean(), color=RED, lw=1.5)
    ax[2].set(title="Label balance: correct rate per skill", xlabel="Share answered correctly", ylabel="Skills")
    ax[2].text(0.02, ax[2].get_ylim()[1] * 0.85, f"overall {correct.mean():.1%}", color=RED)
    save(fig, "dkt_inputs_labels.png")


def chat_figures():
    parts = {s: jsonl(P / "chat" / f"{s}.jsonl") for s in ("train", "val", "test")}
    sources = ("socrateach", "mathdial")

    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    bottom = np.zeros(3)
    for src, col in zip(sources, (GREY, BLUE)):
        v = np.array([sum(r["source"] == src for r in parts[s]) for s in parts])
        ax[0].bar(list(parts), v, bottom=bottom, color=col, label=src)
        bottom += v
    ax[0].set(title="Conversations per split and source", ylabel="Conversations")
    ax[0].legend(frameon=False)
    share = [np.mean([r["source"] == "mathdial" for r in parts[s]]) for s in parts]
    bars = ax[1].bar(list(parts), share, color=BLUE)
    ax[1].bar_label(bars, labels=[f"{x:.0%}" for x in share])
    ax[1].set(title="MathDial share of each split", ylim=(0, 0.5), ylabel="Share of conversations")
    save(fig, "chat_hybrid_split.png")

    allrows = [r for rows in parts.values() for r in rows]
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for src, col in zip(sources, (GREY, BLUE)):
        rs = [r for r in allrows if r["source"] == src]
        ax[0].hist([len(r["messages"]) - 1 for r in rs], bins=range(0, 41, 2), alpha=.7, color=col, label=src, density=True)
        ax[1].hist([len(m["content"].split()) for r in rs for m in r["messages"] if m["role"] == "assistant"],
                   bins=range(0, 120, 4), alpha=.7, color=col, label=src, density=True)
        ax[2].hist([len(r["messages"][0]["content"].split()) for r in rs], bins=range(0, 200, 8), alpha=.7, color=col,
                   label=src, density=True)
    ax[0].set(title="Messages per conversation", xlabel="Messages (system excluded)", ylabel="Share")
    ax[1].set(title="Tutor message length", xlabel="Words")
    ax[2].set(title="System prompt (problem) length", xlabel="Words")
    ax[0].legend(frameon=False)
    save(fig, "chat_inputs.png")

    acts = ("probing", "focus", "generic", "telling")
    fig, ax = plt.subplots(1, 2, figsize=(11, 3.6))
    w = 0.25
    for i, s in enumerate(parts):
        c = Counter(a for r in parts[s] if r["tutor_acts"] for a in r["tutor_acts"])
        tot = sum(c.values())
        ax[0].bar(np.arange(4) + (i - 1) * w, [c[a] / tot for a in acts], w, label=s, color=(BLUE, GREEN, GREY)[i])
    ax[0].set_xticks(range(4), acts)
    ax[0].set(title="MathDial tutor-act label (share of tutor turns)", ylabel="Share")
    ax[0].legend(frameon=False)
    leak = {src: np.mean([f for r in allrows if r["source"] == src for f in r["tutor_leaks_answer"]]) for src in sources}
    bars = ax[1].bar(list(leak), list(leak.values()), color=(GREY, BLUE))
    ax[1].bar_label(bars, labels=[f"{v:.1%}" for v in leak.values()])
    ax[1].set(title="Tutor turns that contain the final answer", ylabel="Share of tutor turns")
    save(fig, "chat_labels.png")

    new = Counter(x for rows in parts.values() for r in rows if r["id"].startswith("mathdial-train-")
                  for m in r["messages"][1:] for x in m["content"] if x in "()/")
    fig, ax = plt.subplots(figsize=(6, 3.4))
    for i, (lab, c, col) in enumerate((("first file (Hugging Face copy)", FIRST_FILE, RED), ("rebuilt from original", new, BLUE))):
        ax.bar(np.arange(3) + (i - .5) * .38, [c["("], c[")"], c["/"]], .38, label=lab, color=col)
    ax.set_xticks(range(3), ["(", ")", "/"])
    ax.set(ylabel="Count (same 2,262 MathDial training conversations)", title="MathDial: symbol counts, first file vs rebuilt")
    ax.legend(frameon=False)
    save(fig, "chat_symbol_fix.png")


def label_figures():
    stats = json.loads((ROOT / "test_scenarios" / "stats.json").read_text())
    ev = json.loads((P / "misconception_eval.json").read_text())
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    bt = stats["backtracking"]["type"]
    ax[0].barh(list(bt)[::-1], list(bt.values())[::-1], color=BLUE)
    ax[0].set(title="Backtracking labels (82)", xlabel="Items")
    mc = stats["misconceptions"]["misconception"]
    ax[1].hist(list(mc.values()), bins=range(1, 6), color=BLUE, align="left")
    ax[1].set(title=f"Misconceptions: {len(mc)} kinds in {sum(mc.values())} items", xlabel="Items per kind", ylabel="Kinds")
    gr = stats["guardrails"]["label"]
    ax[2].bar(list(gr), list(gr.values()), color=BLUE)
    ax[2].set(title="Guardrail labels (47)", ylabel="Items")
    ax[2].tick_params(axis="x", labelsize=8)
    save(fig, "scenario_labels.png")

    fig, ax = plt.subplots(figsize=(6, 3.4))
    keys = ["scenarios", "held_out_new_numbers"]
    ax.bar(np.arange(2) - .19, [ev[k]["detected"] / ev[k]["items"] for k in keys], .38, label="a diagnosis returned", color=GREY)
    ax.bar(np.arange(2) + .19, [ev[k]["exact_name"] / ev[k]["items"] for k in keys], .38, label="same name as label", color=BLUE)
    ax.set_xticks(range(2), ["scenarios\n(32)", "new numbers\n(held out)"])
    ax.set(ylim=(0, 1.15), ylabel="Share of items", title="Misconception detector")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "misconception_detector.png")


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    dkt_figures()
    chat_figures()
    label_figures()
