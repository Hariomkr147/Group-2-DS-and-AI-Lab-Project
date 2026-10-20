"""Build the figures used by the Milestone 1 report and presentation.

Run from the repository root:
    python docs/milestone-1/build_figures.py
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

SURFACE = "#fcfcfb"
TEXT = "#0b0b0b"
MUTED = "#52514e"
GRID = "#e4e3df"
HIGHLIGHT = "#2a78d6"  # categorical slot 1
NEUTRAL = "#b9b8b2"

# Published AUC on ASSISTments 2009-2010 under one protocol: pyKT benchmark
# (Liu et al., NeurIPS 2022 Datasets & Benchmarks, Table 3, question-level
# split after de-duplication). Re-verify against the paper before final submission.
PYKT_ASSIST2009 = [
    ("SAKT (2019)", 0.7246),
    ("DKVMN (2017)", 0.7473),
    ("DKT (2015)", 0.7541),
    ("AKT (2020)", 0.7853),
]


def auc_bar_chart():
    names = [n for n, _ in PYKT_ASSIST2009]
    values = [v for _, v in PYKT_ASSIST2009]
    colors = [HIGHLIGHT if n.startswith("DKT") else NEUTRAL for n in names]

    fig, ax = plt.subplots(figsize=(7.5, 3.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)
    bars = ax.barh(names, values, color=colors, height=0.55, edgecolor=SURFACE, linewidth=2)
    for bar, v in zip(bars, values):
        ax.text(v + 0.002, bar.get_y() + bar.get_height() / 2, f"{v:.3f}",
                va="center", ha="left", fontsize=10, color=TEXT)

    ax.set_xlim(0.50, 0.80)
    ax.axvline(0.5, color=MUTED, linewidth=1)
    ax.set_xlabel("AUC on held-out learners (0.5 = chance; higher is better)", color=MUTED, fontsize=9)
    ax.tick_params(colors=MUTED, labelsize=9, length=0)
    ax.xaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Knowledge-tracing AUC on ASSISTments 2009 (pyKT benchmark)",
                 loc="left", fontsize=11, color=TEXT, pad=10)
    fig.text(0.01, 0.01,
             "Blue = model family we will train (DKT). Source: Liu et al. 2022, pyKT. "
             "Original DKT paper reported 0.86 before duplicate rows were removed.",
             fontsize=7, color=MUTED)
    fig.tight_layout(rect=(0, 0.05, 1, 1))
    fig.savefig(OUT / "kt_auc_assist2009.png", facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    auc_bar_chart()
    print("wrote", OUT / "kt_auc_assist2009.png")
