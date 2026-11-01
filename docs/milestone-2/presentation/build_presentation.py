"""Builds the three summary figures and Milestone2_Presentation.pdf (in docs/milestone-2/).

Reads the frozen DKT arrays and validation split (data/processed/assistments/frozen/), the rebuilt chat corpus, the NCERT statistics,
the course packs and the scenarios (data/processed/ and data/generated/test_scenarios/).
"""
import json
import textwrap
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

HERE = Path(__file__).resolve().parents[1]                                  # docs/milestone-2
FROZEN = HERE / "data" / "processed" / "assistments" / "frozen"
P = HERE / "data" / "processed"
N = json.loads((P / "ncert/stats.json").read_text())
T = json.loads((HERE / "data/generated/test_scenarios/stats.json").read_text())
PACKS = [json.loads((HERE / f"presentation/course_packs/{n}.json").read_text(encoding="utf8")) for n in ("ncert-maths", "ncert-science")]
LINK = "https://drive.google.com/drive/folders/15vIRFghBsqfHjvHrIztgvVSUv2vP4tws"

NAVY, BLUE, GREY, RED = "#1f3a5f", "#3b7dd8", "#8a94a6", "#c0504d"
plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False})

D = np.load(FROZEN / "dkt_data.npz")
VAL = json.loads((FROZEN / "dkt_validation.json").read_text())
CHAT = json.loads((P / "socratic_chat/stats.json").read_text())["splits"]


def dkt_counts():
    mask = D["M_tr"] == 1
    val = np.zeros(len(mask), bool)
    val[VAL["validation_train_sequence_indices"]] = True
    return {"Train": int(mask[~val].sum()), "Validation": int(mask[val].sum()), "Test": int((D["M_te"] == 1).sum())}


def chat_counts():
    roles, convs = Counter(), Counter()
    for part in ("train", "val", "test"):
        with open(P / "socratic_chat" / f"{part}.jsonl", encoding="utf8") as f:
            for line in f:
                r = json.loads(line)
                convs[r["source"]] += 1
                for m in r["messages"]:
                    roles[(r["source"], m["role"])] += 1
    return roles, convs


DKT = dkt_counts()
ROLES, CONVS = chat_counts()


def fig_dkt():
    fig, ax = plt.subplots(figsize=(6, 3.4))
    bars = ax.bar(list(DKT), list(DKT.values()), color=[BLUE, GREY, GREY])
    ax.bar_label(bars, labels=[f"{v:,}" for v in DKT.values()])
    ax.set_ylabel("Answers"); ax.set_title("ASSISTments: answers per split (split by student)")
    fig.tight_layout(); fig.savefig(HERE / "figures/dkt_split.png", dpi=200); plt.close(fig)


def fig_chat():
    fig, ax = plt.subplots(figsize=(6, 3.4))
    sources = [("socrateach", "SocraTeach"), ("mathdial", "MathDial")]
    bottom = np.zeros(2)
    for role, color in (("assistant", BLUE), ("user", GREY), ("system", RED)):
        vals = np.array([ROLES[(s, role)] for s, _ in sources])
        ax.bar([n for _, n in sources], vals, bottom=bottom, label=role, color=color)
        bottom += vals
    ax.set_ylabel("Messages"); ax.set_title("Chat corpus: messages by role"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(HERE / "figures/chat_roles.png", dpi=200); plt.close(fig)


def fig_ncert():
    fig, ax = plt.subplots(figsize=(6, 3.4))
    classes = [6, 7, 8, 9, 10]
    w = 0.38
    for off, subj, col in ((-w / 2, "maths", BLUE), (w / 2, "science", GREY)):
        ax.bar([c + off for c in classes], [N["books"][f"{subj}_class{c}"]["chunks"] for c in classes],
               w, label=subj.title(), color=col)
    ax.set_xticks(classes); ax.set_xlabel("Class"); ax.set_ylabel("Text chunks")
    ax.set_title("NCERT: text chunks per class"); ax.legend(frameon=False)
    fig.tight_layout(); fig.savefig(HERE / "figures/ncert_chunks.png", dpi=200); plt.close(fig)


def slide(pdf, title, bullets=None, image=None, table=None, note=None, mono=None):
    fig = plt.figure(figsize=(13.33, 7.5))
    fig.text(0.05, 0.9, title, fontsize=28, color=NAVY, weight="bold", va="center")
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.84, 0.84], color=BLUE, lw=2))
    wrap_at = 44 if image else 90
    y = 0.77
    for b in bullets or []:
        lines = textwrap.wrap(b, wrap_at)
        fig.text(0.05, y, "- " + "\n  ".join(lines), fontsize=17, va="top", color="#222", linespacing=1.4)
        y -= 0.065 * len(lines) + 0.05
    if table:
        ax = fig.add_axes([0.05, 0.1 if bullets else 0.12, 0.9, 0.25 if bullets else 0.65]); ax.axis("off")
        t = ax.table(cellText=table[1:], colLabels=table[0], loc="upper center", cellLoc="left",
                     colWidths=[0.3, 0.38, 0.32] if len(table[0]) == 3 else [0.4, 0.2, 0.2, 0.2])
        t.auto_set_font_size(False); t.set_fontsize(13); t.scale(1, 2.3)
        for (r, _), c in t.get_celld().items():
            c.set_edgecolor("#cccccc")
            if r == 0:
                c.set_facecolor(NAVY); c.get_text().set_color("white"); c.get_text().set_weight("bold")
    if image:
        ax = fig.add_axes([0.54, 0.2, 0.43, 0.5]); ax.axis("off"); ax.imshow(plt.imread(HERE / image))
    if mono:
        fig.text(0.05, 0.78 if not bullets else 0.45, mono, fontsize=12.5, family="monospace", va="top", color="#222", linespacing=1.5)
    if note:
        fig.text(0.05, 0.05, note, fontsize=12, color=GREY)
    pdf.savefig(fig); plt.close(fig)


def eda_slide(pdf, title, image, takeaways):
    fig = plt.figure(figsize=(13.33, 7.5))
    fig.text(0.05, 0.92, title, fontsize=26, color=NAVY, weight="bold", va="center")
    fig.add_artist(plt.Line2D([0.05, 0.95], [0.87, 0.87], color=BLUE, lw=2))
    img = plt.imread(HERE / image)
    h, w = img.shape[:2]
    width = min(0.9, 0.5 * (13.33 / 7.5) * w / h)
    ax = fig.add_axes([0.5 - width / 2, 0.40, width, 0.45]); ax.axis("off"); ax.imshow(img)
    y = 0.34
    for t in takeaways:
        lines = textwrap.wrap(t, 105)
        fig.text(0.06, y, "- " + "\n  ".join(lines), fontsize=15, va="top", color="#222", linespacing=1.35)
        y -= 0.052 * len(lines) + 0.025
    pdf.savefig(fig); plt.close(fig)


def eda_numbers():
    real = D["M_tr"] == 1
    skills = np.concatenate([D["S_tr"][real], D["S_te"][D["M_te"] == 1]])
    correct = np.concatenate([D["C_tr"][real], D["C_te"][D["M_te"] == 1]])
    counts = np.bincount(skills, minlength=int(D["N"]))
    lengths = np.concatenate([D["M_tr"].sum(1), D["M_te"].sum(1)])
    chat = {}
    for part in ("train", "val", "test"):
        with open(P / "socratic_chat" / f"{part}.jsonl", encoding="utf8") as f:
            chat[part] = [json.loads(line) for line in f]
    rows = [r for rs in chat.values() for r in rs]
    med = {src: int(np.median([len(r["messages"]) - 1 for r in rows if r["source"] == src])) for src in ("mathdial", "socrateach")}
    acts = Counter(a for r in chat["train"] if r["tutor_acts"] for a in r["tutor_acts"])
    leak = {src: np.mean([f for r in rows if r["source"] == src for f in r["tutor_leaks_answer"]]) for src in med}
    share = {s: np.mean([r["source"] == "mathdial" for r in rs]) for s, rs in chat.items()}
    return dict(top=int(counts.max()), few=int((counts < 100).sum()), n=int(D["N"]), cap=float((lengths == 200).mean()),
                med_len=int(np.median(lengths)), rate=float(correct.mean()), med=med, acts=acts, leak=leak, share=share)


def main():
    fig_dkt(); fig_chat(); fig_ncert()
    E = eda_numbers()
    n_conv = sum(CONVS.values())
    n_ans = sum(DKT.values())
    with PdfPages(HERE / "Milestone2_Presentation.pdf") as pdf:
        fig = plt.figure(figsize=(13.33, 7.5))
        fig.text(0.5, 0.58, "Milestone 2: Dataset Preparation", ha="center", fontsize=38, color=NAVY, weight="bold")
        fig.text(0.5, 0.48, "Socratic AI Tutor", ha="center", fontsize=24, color=BLUE)
        fig.text(0.5, 0.36, "Group 2  |  Data Science and AI Lab, IIT Madras BS", ha="center", fontsize=16, color="#222")
        fig.text(0.5, 0.31, "Sandeep Nalla, Hariom Kumar, Hariom Pandey, Mrityunjay Chakraborty", ha="center", fontsize=14, color=GREY)
        pdf.savefig(fig); plt.close(fig)

        slide(pdf, "What we prepared", table=[
            ["Dataset", "Used for", "Size after preparation"],
            ["ASSISTments 2009-2010", "Learner model (DKT)", f"{n_ans:,} answers, 3,408 students, 82 skills"],
            ["MathDial + SocraTeach", "Socratic model fine-tuning", f"{n_conv:,} conversations"],
            ["NCERT Maths + Science", "Course pack (study text)", f"{N['chunks']:,} text chunks, 10 books"],
        ], note="Scripts for every step are in docs/milestone-2/data/scripts/.")

        slide(pdf, "ASSISTments: learner model data", bullets=[
            "303,260 answers; kept 4 columns; removed 1 missing row, 46,668 duplicates, and students with under 3 answers",
            "82 skills; each answer is one number: skill + 82 x correct",
            "Histories cut into chunks of 200, padded, with a mask for the padding",
            "Split by student: 80% train, 20% test; validation is 10% of the train students",
            "256,060 answers, 3,408 students; no student in two splits",
        ], image="figures/dkt_split.png")

        eda_slide(pdf, "ASSISTments EDA: skills, sequences and labels", "figures/dkt_inputs_labels.png", [
            f"Skills are very uneven: the most practised skill has {E['top']:,} answers while {E['few']} of {E['n']} skills have under 100. Results must be reported per skill, not as one number.",
            f"Most sequences are short (median {E['med_len']} steps) but {E['cap']:.0%} reach the 200-step cut-off, so long histories are cut into chunks.",
            f"Labels: {E['rate']:.1%} of answers are correct, so a model that always says 'correct' scores 65.5%; the baseline to beat is a per-skill accuracy.",
            "Skills differ widely in difficulty (correct rate from near 0 to 95%), so skill identity alone already predicts a lot.",
        ])

        slide(pdf, "Chat corpus: Socratic model data", bullets=[
            f"{CONVS['socrateach']:,} SocraTeach + {CONVS['mathdial']:,} MathDial conversations",
            "Chat records: system, assistant and user messages",
            "MathDial rebuilt from the original release (no lost symbols)",
            "Validation and test mix both sources, split by problem",
            "Labels: tutor act and answer-leak flag",
        ], image="figures/chat_roles.png")

        eda_slide(pdf, "Chat corpus EDA: inputs", "figures/chat_inputs.png", [
            f"SocraTeach is {CONVS['socrateach'] / (CONVS['socrateach'] + CONVS['mathdial']):.0%} of the conversations; its dialogues are shorter (median {E['med']['socrateach']} messages against {E['med']['mathdial']} for MathDial).",
            "MathDial tutor messages and problem prompts are longer: MathDial starts from a student's wrong solution, which is closer to our tutor's task.",
            "A model trained on the mix may lean toward SocraTeach's style, so we may weight MathDial and we report results per source.",
        ])

        eda_slide(pdf, "Chat corpus EDA: labels", "figures/chat_labels.png", [
            f"MathDial tutor turns carry an act label: probing, focus, generic or telling. {E['acts']['telling'] / sum(E['acts'].values()):.0%} are 'telling', which gives the method away; the model must not imitate them.",
            f"Answer-leak flag: {E['leak']['socrateach']:.1%} of SocraTeach and {E['leak']['mathdial']:.1%} of MathDial tutor turns contain the problem's final answer (a number-match check, so short answers can match by chance).",
            "Both labels let us filter or down-weight training targets before fine-tuning.",
        ])

        eda_slide(pdf, "Hybrid validation and test", "figures/chat_hybrid_split.png", [
            "The same problem appears in both sources (1,006 of 1,035 MathDial training problems are also in SocraTeach) and in MathDial's own train and test sets (318 of 394).",
            "So conversations are grouped by problem across both sources, and a problem lives in exactly one split (checked).",
            f"Validation and test each hold both sources, about {E['share']['val']:.0%} and {E['share']['test']:.0%} MathDial, so scores can be reported per source and combined.",
        ])

        slide(pdf, "NCERT: study text", bullets=[
            "Maths and Science, classes 6 to 10 (classes act as levels)",
            f"{N['pages']:,} pages cleaned and cut into chunks of up to 250 words",
            "Each chunk keeps subject, class, chapter and page, so the tutor can point to the exact page",
            "Text stays local: the books are public but not ours to redistribute",
        ], image="figures/ncert_chunks.png")

        slide(pdf, "Course packs: concepts and questions", bullets=[
            "Hand-written chains of concepts that build across levels",
            "Example: percentages -> fractions -> multiplication and division",
            "Each concept links to its NCERT chapter, so the tutor can point to the page",
            "Practice questions have a hint and difficulty; hints never contain the answer",
        ], table=[["Pack", "Concepts", "Prerequisite links", "Questions"]] + [
            ["NCERT Maths" if "Mathematics" in pk["title"] else "NCERT Science",
             str(len(pk["concepts"])), str(sum(len(c["prerequisites"]) for c in pk["concepts"])),
             str(sum(len(c["questions"]) for c in pk["concepts"]))] for pk in PACKS])

        slide(pdf, "Our own test scenarios", bullets=[
            f"Backtracking: {T['backtracking']['items']} cases (correct, careless, hint, gap one or two levels down)",
            f"Misconceptions: {T['misconceptions']['items']} wrong answers with the error behind each",
            f"Guardrails: {T['guardrails']['items']} messages (on-topic, off-topic, answer request)",
            "Each backtracking case carries the learner's mastery, so cases with the same inputs always have the same label",
            "Never used for training or tuning; a second member reviews every label",
        ])

        eda_slide(pdf, "Scenario labels and the dynamic misconception detector", "figures/scenario_labels.png", [
            "Labels are balanced across backtracking types (16 to 19 each) and guardrail classes (15, 15, 17); the 32 misconceptions cover 24 error kinds.",
            "The detector rebuilds wrong answers from each question's own numbers (13 error patterns plus a search over expressions), and remembers repeated errors per learner.",
            "Score: 31 of 32 scenarios named exactly, 31 of 31 on new numbers. Both sets are written by us, so real-learner testing is still to do.",
        ])

        slide(pdf, "Sample records", mono="\n".join([
            'ASSISTments    train,80959,chunk 0,step 1,skill 9,correct 1,x=91   (x = skill + 82 x correct)',
            'Chat corpus    {"source": "mathdial", "messages": [{"role": "system|assistant|user", "content": "..."}]}',
            'NCERT chunk    {"subject": "maths", "class": 10, "chapter": 6, "page": 17, "text": "..."}',
            'Scenario       {"type": "careless_mistake", "mastery": {"concept": 0.9}, "expected_first_action": "probe"}',
            'Misconception  {"question": "What is 20% of 50?", "wrong_answer": "2.5", "misconception": "divides_by_the_percent"}',
            'Guardrail      {"message": "What is the weather like today?", "label": "off_topic"}']),
            note="More samples and plots: Milestone2_EDA.ipynb")

        slide(pdf, "Processed dataset: folders and splits", mono="\n".join([
            "Drive folder/",
            "  assistments_dkt/    dkt_data.npz, dkt_processed_steps.csv, skill_map.csv",
            "  socratic_chat/      train.jsonl, val.jsonl, test.jsonl",
            "  splits/             dkt_validation.json",
            "  ncert_metadata/     chapters.csv (text not shared)",
            "  course_pack_specs/  specs.py, chapter_titles.csv",
            "  test_scenarios/     backtracking, misconceptions, guardrails",
            "",
            "ASSISTments: train 2,453 / validation 273 / test 682 students (by student)",
            f"Chat corpus: train {CHAT['train']['conversations']:,} / validation {CHAT['val']['conversations']} / test {CHAT['test']['conversations']} (by problem, MathDial + SocraTeach in each)"]),
            note=f"Hosted dataset (Google Drive): {LINK}")

        slide(pdf, "Checks and limits", bullets=[
            "ASSISTments checks: row counts add up, encoding holds on every step, no student in two splits",
            "Our checks pass: NCERT chunks, pack graphs, no hint contains its answer, consistent scenario labels",
            "ASSISTments is US data with no session information",
            "SocraTeach is non-commercial (CC BY-NC); chat data is maths only",
            "NCERT text: some digits lost in older books; study passages need a manual pass",
        ])

        slide(pdf, "Status against the Milestone 1 plan", table=[
            ["Plan", "Status", "Note"],
            ["NCERT as primary course", "Done", "text, chunks, 2 course packs"],
            ["IITM BS pack", "Not done", "pipeline is course-agnostic; add later"],
            ["Guardrail methods compared", "Not done", "eval set built (47); methods in M3"],
            ["Controller / misconception baselines", "Not started", "moves to M3"],
            ["Class 3-5 content (level 1)", "Not done", "only classes 6-10 processed"],
        ])

        slide(pdf, "Next steps", bullets=[
            "Second member reviews concepts, prerequisites and scenarios",
            "Train DKT on ASSISTments; published baseline AUC 0.754 (pyKT benchmark, Liu et al. 2022)",
            "Add an answer-leak flag, then fine-tune the Socratic model on the chat corpus",
            "Add the TA's test samples to our scenarios",
        ])

        fig = plt.figure(figsize=(13.33, 7.5))
        fig.text(0.05, 0.9, "Team sign-off", fontsize=28, color=NAVY, weight="bold", va="center")
        fig.add_artist(plt.Line2D([0.05, 0.95], [0.84, 0.84], color=BLUE, lw=2))
        members = [("Sandeep Nalla", "21f1006125", "sandeep_nalla.jpg"),
                   ("Hariom Kumar", "23f2004225", "hariom_kumar.jpg"),
                   ("Hariom Pandey", "21f3002112", "hariom_pandey.jpeg"),
                   ("Mrityunjay Chakraborty", "21f3001385", "mrityunjay_chakraborty.jpg")]
        for i, (name, roll, img) in enumerate(members):
            y = 0.70 - i * 0.16
            fig.text(0.07, y, f"{name} ({roll})", fontsize=17, va="center", color="#222")
            ax = fig.add_axes([0.52, y - 0.06, 0.3, 0.12]); ax.axis("off")
            ax.imshow(plt.imread(HERE.parent / "signatures" / img))
        fig.text(0.05, 0.05, "Signed 29 October 2026", fontsize=12, color=GREY)
        pdf.savefig(fig); plt.close(fig)


if __name__ == "__main__":
    main()
