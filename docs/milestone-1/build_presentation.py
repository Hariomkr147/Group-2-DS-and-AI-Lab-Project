"""Build the Milestone 1 presentation (10 slides, 16:9).

Run from the repository root after build_figures.py:
    python docs/milestone-1/build_presentation.py
Requires: pip install python-pptx
"""
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).parent
FIG = HERE / "figures" / "kt_auc_assist2009.png"
OUT = HERE / "Milestone1_Presentation.pptx"

NAVY = RGBColor(0x1B, 0x36, 0x4B)
TEAL = RGBColor(0x0F, 0x7C, 0x8C)
PALE = RGBColor(0xE6, 0xF2, 0xF3)
INK = RGBColor(0x1F, 0x1F, 0x1F)
MUTED = RGBColor(0x55, 0x55, 0x55)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xCF, 0xE6, 0xE9)
FONT = "Calibri"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 10


def text(slide, x, y, w, h, runs, size=16, color=INK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, font=FONT):
    """runs: str or list of str / (str, dict) paragraphs."""
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    paras = runs if isinstance(runs, list) else [runs]
    for i, p in enumerate(paras):
        opts = {}
        if isinstance(p, tuple):
            p, opts = p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = opts.get("align", align)
        para.space_after = Pt(opts.get("space", 4))
        r = para.add_run()
        r.text = p
        r.font.name = opts.get("font", font)
        r.font.size = Pt(opts.get("size", size))
        r.font.bold = opts.get("bold", bold)
        r.font.color.rgb = opts.get("color", color)
    return box


def bullets(slide, x, y, w, h, items, size=16):
    return text(slide, x, y, w, h, [("•  " + i, {"space": 8}) for i in items], size=size)


def box(slide, x, y, w, h, fill=PALE, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    s.shadow.inherit = False
    return s


def label_box(slide, x, y, w, h, title, body="", fill=PALE, dark=False, size=13):
    box(slide, x, y, w, h, fill=fill)
    fg = WHITE if dark else INK
    paras = [(title, {"bold": True, "size": size + 1, "color": fg, "align": PP_ALIGN.CENTER})]
    if body:
        paras.append((body, {"size": size, "color": fg, "align": PP_ALIGN.CENTER}))
    text(slide, x + 0.08, y, w - 0.16, h, paras, anchor=MSO_ANCHOR.MIDDLE)


def arrow(slide, x1, y1, x2, y2):
    c = slide.shapes.add_connector(1, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = MUTED
    c.line.width = Pt(1.5)
    c.line._get_or_add_ln().append(
        c.line._get_or_add_ln().makeelement(
            "{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd",
            {"type": "triangle"}))
    return c


def table(slide, x, y, w, rows, col_w, size=12, row_h=0.4, header_fill=NAVY):
    shp = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y),
                                 Inches(w), Inches(row_h * len(rows)))
    tbl = shp.table
    for j, cw in enumerate(col_w):
        tbl.columns[j].width = Inches(cw)
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = tbl.cell(i, j)
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.fill.solid()
            if i == 0:
                cell.fill.fore_color.rgb = header_fill
            else:
                cell.fill.fore_color.rgb = WHITE if i % 2 else RGBColor(0xF4, 0xF6, 0xF7)
            tf = cell.text_frame
            tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = val
            r.font.name = FONT
            r.font.size = Pt(size)
            r.font.bold = i == 0 or j == 0
            r.font.color.rgb = WHITE if i == 0 else INK
    return tbl


def slide_frame(title, subtitle=None, n=None):
    s = prs.slides.add_slide(BLANK)
    box(s, 0, 0, 13.333, 0.12, fill=TEAL, shape=MSO_SHAPE.RECTANGLE)
    text(s, 0.6, 0.35, 12.1, 0.7, title, size=30, bold=True, color=NAVY)
    if subtitle:
        text(s, 0.6, 1.0, 12.1, 0.5, subtitle, size=16, color=TEAL)
    text(s, 0.6, 7.0, 9, 0.35, "Group 2 · Socratic AI Tutor · Milestone 1", size=10, color=MUTED)
    if n:
        text(s, 11.7, 7.0, 1.0, 0.35, f"{n} / {TOTAL}", size=10, color=MUTED, align=PP_ALIGN.RIGHT)
    return s


def notes(slide, t):
    slide.notes_slide.notes_text_frame.text = t


# 1 ── Title ────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(BLANK)
box(s, 0, 0, 13.333, 7.5, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
box(s, 0.8, 2.95, 1.2, 0.06, fill=TEAL, shape=MSO_SHAPE.RECTANGLE)
text(s, 0.8, 1.3, 11.5, 1.6, [
    ("Socratic AI Tutor", {"size": 44, "bold": True, "color": WHITE}),
    ("Guiding learners to the answer", {"size": 32, "color": WHITE}),
])
text(s, 0.8, 3.2, 11.5, 1.0,
     "An intelligent small-scale tutor that guides a learner to the answer through probing questions, "
     "backtracking across levels when needed. One pipeline, any course.", size=20, color=LIGHT)
text(s, 0.8, 4.6, 11.5, 1.8, [
    ("Milestone 1  ·  Group 2  ·  Data Science and AI Lab, IIT Madras BS", {"size": 16, "color": WHITE}),
    ("Sandeep Nalla (21f1006125)  ·  Hariom Kumar (23f2004225)  ·  Hariom Pandey (21f3002112)  ·  "
     "Mrityunjay Chakraborty (21f3001385)", {"size": 14, "color": LIGHT}),
])
text(s, 0.8, 6.7, 11.5, 0.4, "October 2026", size=12, color=LIGHT)

# 2 ── Objective ────────────────────────────────────────────────────────────
s = slide_frame("Objective", "Help the learner reach the answer themselves, instead of giving it directly", 2)
steps = [("1. Break down", "the doubt into\nsub-ideas"), ("2. Probe", "one question\nat a time"),
         ("3. Feedback", "spot misconceptions,\nlink a resource"), ("4. Backtrack", "to an earlier level\nif there is a gap"),
         ("5. Climb back", "raise difficulty\nstep by step")]
for i, (t, b) in enumerate(steps):
    x = 0.6 + i * 2.5
    label_box(s, x, 1.75, 2.15, 1.4, t, b, fill=NAVY, dark=True, size=13)
    if i < len(steps) - 1:
        arrow(s, x + 2.15, 2.45, x + 2.5, 2.45)
text(s, 0.6, 3.55, 12.1, 0.45, "Domain-agnostic: each subject is a “course pack”", size=18, bold=True, color=TEAL)
table(s, 0.6, 4.05, 12.1, [
    ["Concepts", "Prerequisite links", "Study material", "Questions"],
    ["topics with IDs and levels", "“A is needed before B”, across levels", "PDFs, slides, transcripts",
     "answers, hints, difficulty"],
], col_w=[3.0, 3.0, 3.05, 3.05], size=14, row_h=0.5)
label_box(s, 0.6, 5.35, 5.9, 1.3, "Main pilot: NCERT Mathematics",
          "several classes that build on each other (Level 1 → 2 → 3)", size=13)
label_box(s, 6.8, 5.35, 5.9, 1.3, "Second domain: IITM BS",
          "Maths → MLF → MLT, e.g. “How does training happen in Linear Regression?”", size=13)

# 3 ── Levels & backtracking ────────────────────────────────────────────────
s = slide_frame("Learning builds across levels", "If a learner is stuck, the tutor finds the gap in an earlier level", 3)
levels = [("Level 1", "Addition · Subtraction\nMultiplication"), ("Level 2", "Division\nFractions"),
          ("Level 3", "Decimals\nPercentages")]
for i, (t, b) in enumerate(levels):
    x = 0.6 + i * 4.2
    label_box(s, x, 1.75, 3.6, 1.4, t, b, fill=TEAL if i == 2 else PALE, dark=i == 2, size=15)
    if i < 2:
        arrow(s, x + 3.6, 2.45, x + 4.2, 2.45)
text(s, 0.6, 3.45, 12.1, 0.45, "Example: stuck on “What is 20% of 50?”", size=18, bold=True, color=TEAL)
table(s, 0.6, 3.95, 12.1, [
    ["Step", "What the tutor does"],
    ["1. Probe", "“What does 20% mean: 20 out of how many?”"],
    ["2. Backtrack", "Gap found in fractions (Level 2) → checks division → multiplication (Level 1) if needed"],
    ["3. Practise", "A few division and fraction questions with hints and a link to the NCERT page"],
    ["4. Climb back", "1/5 of 50 → 1/4 of 20 → back to 20% of 50 → harder: 15% of 60"],
], col_w=[2.2, 9.9], size=14, row_h=0.52)
notes(s, "This follows the TA's guidance: cross-reference and propagate learning across levels.")

# 4 ── Existing solutions & gaps ─────────────────────────────────────────────
s = slide_frame("Existing solutions and their gaps", None, 4)
table(s, 0.6, 1.3, 12.1, [
    ["Solution", "Good at", "Missing for our problem"],
    ["ChatGPT / Gemini study modes, Khanmigo", "Natural conversation",
     "Driven by a system prompt; no memory of skills; can give away answers"],
    ["MATHia, ALEKS", "Track student skills", "Paid, closed, no conversation, fixed curriculum"],
    ["ASSISTments", "Free practice with hints", "Fixed teacher-written hints"],
    ["Course portals (IITM BS, DIKSHA)", "Host content", "Don't diagnose why a student is stuck"],
], col_w=[3.8, 2.8, 5.5], size=14, row_h=0.55)
text(s, 0.6, 4.4, 12.1, 0.45, "What we add", size=18, bold=True, color=TEAL)
bullets(s, 0.6, 4.9, 12.1, 2.0, [
    "Our own trained models as the main brain, not an LLM API with a system prompt",
    "A learner model that remembers which concepts the student knows",
    "Backtracking across levels, then climbing back up to the learner’s question",
    "Feedback with the exact page, slide or video to revisit; works for any course",
], size=16)

# 5 ── Research baselines ───────────────────────────────────────────────────
s = slide_frame("Research baselines", None, 5)
s.shapes.add_picture(str(FIG), Inches(0.5), Inches(1.3), width=Inches(7.3))
text(s, 0.6, 4.75, 7.2, 1.8, [
    ("Predicting student knowledge", {"bold": True, "size": 16, "color": TEAL}),
    ("DKT (Deep Knowledge Tracing, an LSTM we will train) scores AUC 0.754 on cleaned "
     "ASSISTments data. 0.5 = random guess, 1.0 = perfect.", {"size": 14}),
])
text(s, 8.2, 1.3, 4.6, 0.45, "AI chat tutors", size=16, bold=True, color=TEAL)
bullets(s, 8.2, 1.8, 4.6, 4.9, [
    "MathDial (2,861 dialogues): prompted AI teachers often reveal the answer; fine-tuned models guide better",
    "Bastani et al. 2025: plain GPT-4 → +48% in practice but −17% on the exam",
    "Lesson: a system-prompted chatbot is not enough; the tutor needs its own trained models",
], size=15)

# 6 ── Our approach ─────────────────────────────────────────────────────────
s = slide_frame("Our approach: our own models are the main brain", None, 6)
table(s, 0.6, 1.3, 12.1, [
    ["Component", "Built by us?", "Role"],
    ["Learner model (DKT)", "✓ trained", "Estimates what the learner knows for each concept"],
    ["Tutor controller", "✓ written", "Decides: probe, hint, backtrack a level, retest, move up"],
    ["Socratic question model", "✓ fine-tuned", "Qwen3-4B + LoRA on MathDial + our examples: writes probing questions"],
    ["Misconception detector", "✓ built", "Spots common error patterns (e.g. 50 ÷ 20 instead of 20/100 × 50)"],
    ["Search (RAG)", "pretrained embeddings", "Finds the page, slide or video for a concept"],
    ["External LLM API", "✗ optional", "Only drafts practice questions offline (checked) and serves as a baseline"],
], col_w=[3.0, 2.3, 6.8], size=14, row_h=0.52)
text(s, 0.6, 5.2, 12.1, 1.5, [
    ("Stack: React web app · FastAPI backend · PostgreSQL + pgvector · PyTorch", {"size": 15}),
    ("New course = new course pack + ingestion script. New course with no student data → simple "
     "fallback until DKT is retrained.", {"size": 14, "color": MUTED}),
])
notes(s, "TA: LLM APIs only as a minor part; the main brain must be our own DL/GenAI model.")

# 7 ── Datasets & samples ───────────────────────────────────────────────────
s = slide_frame("Datasets and samples", None, 7)
table(s, 0.6, 1.3, 6.4, [
    ["Dataset", "Use", "Size"],
    ["ASSISTments 2009–10", "Train DKT", "~346k answers, 4,217 students"],
    ["EdNet KT1 (optional)", "Train DKT (larger)", "~95M answers"],
    ["MathDial", "Fine-tune Socratic model", "2,861 dialogues"],
    ["NCERT Maths", "Course pack (main)", "several classes"],
    ["IITM BS transcripts", "Course pack (second)", "gathered by us"],
], col_w=[2.1, 2.2, 2.1], size=12, row_h=0.45)
text(s, 0.6, 4.2, 6.4, 0.8, "Licenses checked before use (e.g. MathDial CC BY-SA 4.0, EdNet CC BY-NC 4.0).",
     size=12, color=MUTED)
text(s, 0.6, 4.8, 6.4, 0.45, "ASSISTments row format", size=16, bold=True, color=TEAL)
table(s, 0.6, 5.3, 6.4, [
    ["student", "skill", "correct", "hints"],
    ["64525", "Equivalent Fractions", "0", "2"],
    ["64525", "Equivalent Fractions", "1", "0"],
], col_w=[1.2, 3.0, 1.1, 1.1], size=12, row_h=0.4)
text(s, 7.4, 1.3, 5.4, 0.45, "MathDial (real record) → trains probing style", size=16, bold=True, color=TEAL)
box(s, 7.4, 1.8, 5.4, 4.3, fill=PALE)
text(s, 7.55, 1.9, 5.1, 4.2, [
    ("Problem: aquarium filled halfway, half spilled, then tripled. Answer: 54. Student said 72.",
     {"size": 13}),
    ("Teacher (probing): If you had 4 of something and tripled it, how much would you have?",
     {"size": 13, "bold": True}),
    ("Student: 12.", {"size": 13}),
    ("Teacher (probing): So if Nancy triples the 18 cubic feet, how much would she have?",
     {"size": 13, "bold": True}),
    ("Student: 54 cubic feet.", {"size": 13}),
    ("Teacher (generic): Exactly correct!", {"size": 13, "bold": True}),
    ("Every teacher turn is labelled (probing / focus / telling / generic), so we can train our "
     "model to probe instead of tell.", {"size": 13, "color": TEAL}),
])

# 8 ── Metrics & evaluation ─────────────────────────────────────────────────
s = slide_frame("Baselines, targets and evaluation", None, 8)
table(s, 0.6, 1.3, 12.1, [
    ["Part", "Metric", "Compared with", "Target"],
    ["Learner model", "AUC", "Simple accuracy; published DKT 0.754", "≥ 0.74, better than simple"],
    ["Socratic model", "% replies revealing the answer", "Base model; LLM API + system prompt", "≤ 5%, lower than both"],
    ["Backtracking", "% gaps found at the right level", "LLM API + system prompt", "≥ 85%"],
    ["Search", "Correct resource in top 5", "Keyword search", "≥ 0.80"],
    ["Full tutor", "% test scenarios handled", "Fixed rules; LLM API + system prompt", "≥ 90%"],
], col_w=[2.2, 3.4, 3.8, 2.7], size=13, row_h=0.5)
text(s, 0.6, 4.55, 12.1, 0.45, "How we will evaluate", size=18, bold=True, color=TEAL)
bullets(s, 0.6, 5.05, 12.1, 1.9, [
    "60–100 annotated scenarios we write (careless slip, gap 1 level down, gap 2 levels down…) + the TA’s test samples",
    "Compare: direct-answer chatbot vs LLM API with Socratic prompt vs our tutor; also vs published research numbers",
    "Same tests on NCERT and IITM BS course packs, with no code changes",
], size=15)

# 9 ── Expected output ──────────────────────────────────────────────────────
s = slide_frame("Expected output (mock-up)", None, 9)
box(s, 0.6, 1.25, 7.4, 3.9, fill=WHITE, line=TEAL)
text(s, 0.75, 1.3, 7.2, 5.0, [
    ("Learner: What is 20% of 50?  My answer: 2.5", {"bold": True, "size": 13, "color": NAVY}),
    ("Tutor: What does 20% mean: 20 out of how many?   Learner: 100 ✓", {"size": 12}),
    ("Tutor: So 20% = 20/100. Simplest form?   Learner: I don’t know", {"size": 12}),
    ("[gap at Level 2 → checking division]", {"size": 12, "color": TEAL}),
    ("Tutor: What is 100 ÷ 20?   Learner: 5 ✓", {"size": 12}),
    ("Tutor: So 20/100 = 1/5. What is 1/5 of 50?  Hint: 5 equal groups 📖", {"size": 12}),
    ("Learner: 10 ✓      Tutor: And 1/4 of 20?   Learner: 5 ✓", {"size": 12}),
    ("[back to Level 3]", {"size": 12, "color": TEAL}),
    ("Tutor: Try again: 20% of 50?   Learner: 10 ✓", {"size": 12, "bold": True}),
    ("Tutor: Earlier you divided 50 by 20; a percentage means “out of 100”.", {"size": 12}),
    ("         Next: 15% of 60?", {"size": 12}),
])
text(s, 8.4, 1.25, 4.4, 0.45, "Progress report", size=16, bold=True, color=TEAL)
table(s, 8.4, 1.75, 4.4, [
    ["Concept (level)", "Correct", "Readiness"],
    ["Multiplication (1)", "3/3", "0.90"],
    ["Division (2)", "2/2", "0.84"],
    ["Fractions (2)", "1/2", "0.66"],
    ["Percentages (3)", "1/2", "0.58 · practise"],
], col_w=[1.8, 0.9, 1.7], size=12, row_h=0.42)
text(s, 8.4, 4.1, 4.4, 0.45, "LLM API vs our tutor", size=16, bold=True, color=TEAL)
text(s, 8.4, 4.55, 4.4, 2.0, [
    ("API + prompt: “20/100 × 50 = 10.” Answer revealed; gap not found.", {"size": 13}),
    ("Ours: finds the fraction gap, practises Level 2, returns to Level 3; learner finds 10.",
     {"size": 13, "bold": True}),
])

# 10 ── Next steps & sign-off ───────────────────────────────────────────────
s = slide_frame("Next steps, TA decisions and sign-off", None, 10)
text(s, 0.6, 1.2, 6.0, 0.45, "Milestone 2 plan", size=18, bold=True, color=TEAL)
bullets(s, 0.6, 1.7, 6.0, 2.6, [
    "Clean ASSISTments; train the baseline and DKT",
    "First LoRA fine-tune of the Socratic model on MathDial",
    "Multi-level NCERT course pack; gather IITM transcripts",
    "First controller, search and web app; 30 test scenarios",
], size=15)
text(s, 0.6, 4.0, 6.0, 0.45, "Decisions recorded from the TA", size=18, bold=True, color=TEAL)
bullets(s, 0.6, 4.5, 6.0, 2.4, [
    "External datasets and NCERT allowed (check licenses)",
    "Main brain must be our own model; LLM API only a minor part",
    "Several connected levels, with backtracking",
    "Compare against an LLM-API + system-prompt tutor",
], size=14)
table(s, 7.0, 1.3, 5.8, [
    ["Member", "Signature"],
    ["Sandeep Nalla (21f1006125)", ""],
    ["Hariom Kumar (23f2004225)", ""],
    ["Hariom Pandey (21f3002112)", ""],
    ["Mrityunjay Chakraborty (21f3001385)", ""],
], col_w=[3.6, 2.2], size=13, row_h=0.6)

prs.save(OUT)
print("wrote", OUT)
