# Milestone 1 Report: Socratic AI Tutor

**Course:** Data Science and AI Lab, IIT Madras BS
**Team:** Group 2
**Submission:** Milestone 1, 22 October 2026

| Name | Roll number | Primary role |
|---|---|---|
| Sandeep Nalla | 21f1006125 | Backend developer |
| Hariom Kumar | 23f2004225 | Build the RAG (search) agent |
| Hariom Pandey | 21f3002112 | Build the fine-tuned models |
| Mrityunjay Chakraborty | 21f3001385 | Frontend developer |

*Roles are not fixed; members contribute to other parts as the project needs.*

> This is a planning report. Nothing has been built or trained yet. Numbers marked "target" are our goals. Other numbers come from published work (see References).

---

## 1. Objective

**Project statement:** *Development of an intelligent small-scale tutor that guides a learner to the answer through a set of probing questions.*

**Why "Socratic"?** The name comes from the Greek philosopher Socrates, who taught by asking questions that led students to discover answers themselves instead of telling them. That is exactly how our tutor works.

Our primary goal is a **study companion for IIT Madras BS learners**, built on the same material they use on the IITM BS portal: lecture videos, slides and weekly assignments.

When a learner has a doubt, the tutor should **help them reach the answer themselves** instead of giving it directly. To do this, the tutor:

1. **Breaks the question down** into the smaller ideas it depends on (its *prerequisites*).
2. **Asks probing questions** about each idea, one at a time.
3. **Checks the learner's answer**, spots likely misconceptions and gives feedback.
4. **Points to the right resource** (lecture video with timestamp, slide or assignment) when the learner makes a mistake.
5. **Goes back to earlier courses when needed:** if a learner is stuck, the tutor finds the gap in an earlier course, practises it with questions, and then climbs back up to the learner's current course.
6. **Tests and adapts:** a short test finds the learner's level, and practice questions are generated at the learner's own pace.

### Learning builds across courses

IITM BS courses build on each other. For example, MLT uses ideas from Maths, Stats and MLF. The tutor traces a doubt back through these earlier courses.

```mermaid
flowchart LR
    subgraph L1[Foundation: Maths 1, Stats 1]
        F1[Functions and<br/>slope of a line]
        F2[Mean and variance]
    end
    subgraph L2[Foundation: Maths 2]
        V[Vectors and<br/>dot product]
        D[Derivatives and<br/>chain rule]
    end
    subgraph L3[Diploma: MLF]
        LF[Loss functions] --> GD[Gradient descent]
    end
    subgraph L4[Diploma: MLT]
        LR[Training linear<br/>regression]
    end
    F1 --> D
    F2 --> LF
    V --> LF
    D --> GD
    GD --> LR
    V --> LR
```

**Example (from the project brief):** a learner asks *"How does training happen in Linear Regression?"* (MLT). The tutor guides them through supervised learning, the model `y = w·x`, the loss and gradient descent. If the learner can't work out the gradient, the tutor goes back to **derivatives** (Maths 2), and if needed to **slope of a line** (Maths 1). It practises the weak skill with a few questions, then climbs back up to MLT.

*The concept-to-course mapping is illustrative; we will confirm it from the IITM BS course content.*

### Scope: one pipeline, any course

IITM BS is our primary goal, but the **pipeline is domain-agnostic and reusable**. All subject knowledge is kept in a **course pack**, never in the code:

| Course pack part | What it contains |
|---|---|
| Concepts | Topics with IDs and levels, e.g. `derivatives` (Maths 2) |
| Prerequisite links | "A is needed before B", including links across courses |
| Study material | Lecture transcripts, slides, notes, textbook PDFs |
| Questions | Practice questions with answers, hints and difficulty |

We will build two course packs:

- **Primary: IITM BS courses that build on each other** (Maths & Stats → MLF → MLT). We will gather the lecture transcripts, slides and assignments ourselves.
- **Second domain: NCERT Mathematics across several classes** (e.g. multiplication → division → fractions → percentages). This shows the same pipeline works for a completely different subject and level, with no code changes.

### Visual aids and what is out of scope

The tutor is conversational, but not text-only:

- **Links to existing videos:** when the learner makes a mistake, the tutor points to the exact lecture video and timestamp (e.g. "MLT Week 2, Lecture 3 at 12:40"), found by searching lecture transcripts.
- **Simple diagrams in the conversation:** graphs (e.g. a loss curve with gradient-descent steps), vector diagrams, number lines and fraction bars, drawn from templates by small scripts, plus properly rendered formulas.

**Out of scope: AI-generated videos or animations.** Generating them is expensive, slow and error-prone for maths. It is also not the focus of this project, which is the tutoring "brain": finding the learner's gap and asking the right next question. We reuse the existing IITM lecture videos instead.

---

## 2. Existing solutions

| Solution | What it does well | What it lacks for our objective |
|---|---|---|
| **Khanmigo** (Khan Academy) [12] | Helps students understand concepts by questioning them, and builds understanding based on their answers | Runs on an external LLM (GPT-4) guided by prompts, not its own trained tutoring model; no explicit backtracking across levels; tied to Khan Academy content; not open |
| **ChatGPT / Gemini (study or guided-learning modes)** | Good conversation; tries to guide instead of answering | Driven by a system prompt; does not track what the student knows across courses; can still give away answers; does not know IITM course material |
| **MATHia** (Carnegie Learning) [11] | Adapts to each student's needs; guides through every step of a problem with real-time feedback and targeted practice | Paid and closed; only its own fixed maths curriculum; hints follow fixed step-by-step paths, with no free conversation about the learner's own doubt; new courses can't be added |
| **ALEKS** (McGraw Hill) [13]: adaptive learning system, not a chat assistant | Uses Knowledge Space Theory to find what a student knows and is ready to learn next, based on prerequisites | No conversation or probing questions; paid and closed; fixed curriculum |
| **ASSISTments** (WPI) [14] | Free platform for teachers to assign practice and give students personalized feedback; public research data | Feedback and hints are written by teachers in advance; no conversation; no automatic backtracking to prerequisites |
| **IITM BS portal and other course platforms (DIKSHA, YouTube lectures)** | Host lecture videos, slides, notes and assignments | Do not diagnose why a student is stuck or guide them step by step |

**Closest existing solutions: MATHia and Khanmigo.** MATHia adapts to each student and guides them step by step with feedback. Khanmigo builds understanding by questioning the student. Our tutor combines both ideas and differs in four ways: it **converses** about the learner's own doubt with probing questions, it **backtracks across courses** to fix earlier gaps, it is **domain-agnostic** (any course can be added as a course pack), and it is **open and built from our own models**.

---

## 3. Baselines and benchmarks from research

### 3.1 Tracking what a student knows ("knowledge tracing")

**DKT (Deep Knowledge Tracing)** [1] is a small neural network (an LSTM) that reads a student's answer history, for example "derivatives: wrong, derivatives: right, gradient descent: wrong", and predicts the chance of a correct answer on each concept next. The standard metric is **AUC**, where 0.5 is random guessing and 1.0 is perfect.

| Model | How it works | AUC on ASSISTments 2009 |
|---|---|---|
| **BKT**: Bayesian Knowledge Tracing (1994) [2] | Classic probability model; each skill is either "known" or "not known" | 0.69 [1] |
| **DKT**: Deep Knowledge Tracing (2015) [1] | One LSTM reads the whole answer history | 0.754 [3] |
| **DKVMN**: Dynamic Key-Value Memory Network (2017) [16] | Memory table with one slot per concept, updated after each answer | 0.747 [3] |
| **SAKT**: Self-Attentive Knowledge Tracing (2019) [17] | Self-attention (as in Transformers) picks the most relevant past answers | 0.725 [3] |
| **AKT**: Attentive Knowledge Tracing (2020) [15] | Attention with time-based decay and question-difficulty embeddings | 0.785 [3] |

*AUC = Area Under the ROC (Receiver Operating Characteristic) Curve. LSTM = Long Short-Term Memory, a type of recurrent neural network. The BKT value comes from the original DKT paper [1]; the others come from the pyKT benchmark [3], which uses one standard, cleaned setup, so the BKT value is only a rough comparison.*

![Knowledge-tracing AUC on ASSISTments 2009](figures/kt_auc_assist2009.png)

*The original DKT paper reported 0.86, but later work found that duplicate rows had inflated this figure [4]. The pyKT benchmark [3] gives fair, cleaned numbers.*

### Why we chose Deep Knowledge Tracing (DKT)

DKT is the **simplest model that performs well**. Compared with each alternative:

| Model | Why not chosen as our main model |
|---|---|
| **BKT** (Bayesian Knowledge Tracing) | Clearly less accurate (0.69 vs 0.754). It treats each skill separately, so it cannot learn links between concepts, which matters for backtracking across courses. |
| **DKVMN** (Dynamic Key-Value Memory Network) | Slightly less accurate than DKT (0.747 vs 0.754) and more complex to build and tune. The extra memory network brings no gain. |
| **SAKT** (Self-Attentive Knowledge Tracing) | Less accurate (0.725 vs 0.754). Self-attention needs many students and long histories to work well; the pyKT authors found that sequential models like DKT beat SAKT in most cases [3]. IITM courses will start with little data. |
| **AKT** (Attentive Knowledge Tracing) | The most accurate, but only about 0.03 AUC better (0.785 vs 0.754). It needs many students per question to learn question difficulty, and it is much more complex (attention layers, time-based decay, many settings to tune). |

Further reasons for DKT:

1. **Simple to build, train and explain:** a single LSTM over the answer sequence that trains quickly on a free GPU.
2. **Copes better with little data,** which suits new IITM courses with no student history yet.
3. **The standard reference point:** most research compares against DKT, so our results are easy to check against published numbers.
4. **The learner model is not our main contribution.** Our focus is the whole tutor: the fine-tuned Socratic model, backtracking across courses and links to study material.

**If time allows, we will also train AKT on the same data split** (the pyKT library includes all of these models) and report both results.

### 3.2 AI chat tutors

| Study | Finding |
|---|---|
| **Bastani et al.** (PNAS 2025) [5] | Students using plain GPT-4 did 48% better in practice but **17% worse on the exam** afterwards. A version with guardrails avoided this drop. |
| **Tack & Piech** (2022) [6] | AI chatbots scored lower than human teachers on helpfulness. |

**Main finding:** a chatbot driven only by a system prompt is not a good tutor. It needs **its own trained models** that decide *what to ask next* and *how much to reveal*.

---

## 4. Gaps and how we address them

| Gap in existing solutions | How our project addresses it |
|---|---|
| Chatbots give the answer directly | **Our fine-tuned Socratic model** asks probing questions, and the controller limits how much is revealed |
| Chatbots don't remember what the student knows | **Learner model (DKT)** tracks every concept |
| No backtracking across courses | A **prerequisite graph across courses** plus a controller that goes back, practises, and climbs back up |
| Mistakes don't lead to study material | **Search (RAG)** links each mistake to the exact lecture video, slide or assignment |
| Same questions for every learner | **Diagnostic test + generated practice questions** at the learner's pace |
| Tied to one subject | **Course packs** make the pipeline domain-agnostic |

---

## 5. Our approach

### 5.1 Our own models are the "main brain"

The core of the tutor is **models we build and train ourselves**, not an LLM API controlled by a system prompt.

| Component | Built by us? | Role |
|---|---|---|
| **Learner model (DKT)** | ✓ trained by us | Estimates what the learner knows for each concept |
| **Tutor controller** | ✓ written by us | Decides the next step: probe, hint, backtrack to an earlier course, retest, move up |
| **Socratic question model** | ✓ fine-tuned by us (Qwen3-4B + LoRA on tutoring dialogues and our own IITM BS examples) | Writes probing questions and feedback |
| **Misconception detector** | ✓ built by us | Spots common error patterns (e.g. a sign error in the gradient) |
| Search (RAG) | Uses a pretrained embedding model | Finds the relevant lecture, slide or assignment |
| External LLM API (optional) | ✗ | Only helps draft practice questions offline (each checked before use), and serves as a **baseline** for comparison |

### 5.2 Architecture

```mermaid
flowchart LR
    S[Student] --> UI[Web app<br/>React]
    UI --> API[Backend<br/>FastAPI]
    API --> C[Tutor controller]
    C --> LM[Learner model<br/>DKT]
    C --> MD[Misconception<br/>detector]
    C --> R[Search<br/>RAG]
    C --> G[Our fine-tuned<br/>Socratic model]
    LM & MD & R & G --> DB[(Database<br/>PostgreSQL)]
    CP[Course pack<br/>IITM BS / NCERT / any] --> DB
```

### 5.3 Tutor loop with backtracking

```mermaid
flowchart TD
    Q[Learner's question<br/>e.g. how is linear regression trained?] --> T[Diagnostic question]
    T -->|correct| A[Guide to the answer<br/>with probing questions]
    T -->|wrong| B[Check prerequisite<br/>in an earlier course]
    B -->|gap found| B2[Go back another course<br/>if needed]
    B2 --> PR[Practise the weak skill<br/>with hints + lecture link]
    PR --> UP[Raise difficulty<br/>course by course]
    UP --> A
    A --> E[Learner reaches the answer]
```

### 5.4 How the pipeline stays domain-agnostic

- Subject knowledge lives only in the **course pack** (data files and documents).
- The **learner model** is first trained on public datasets. For a course with no student data yet, the tutor uses a simple fallback (recent accuracy per concept). If anonymised IITM assignment data becomes available, DKT can be retrained on it.
- The **Socratic model** learns a general *style* (probe, don't tell), so it can be reused across subjects. The course pack supplies the facts through search.
- Adding a new course = writing its course pack + running the ingestion script.

### 5.5 Difference from a normal chatbot tutor

| | LLM API + system prompt | Our tutor |
|---|---|---|
| Main brain | External LLM | Our own DKT + controller + fine-tuned model |
| Gives the answer | Often | No: guides with questions |
| Remembers student skills | No | Yes, per concept |
| Backtracks across courses | Not reliably | Yes, using the prerequisite graph |
| Links to study material | Generic or invented | Exact IITM lecture, slide or assignment from the course pack |

---

## 6. Datasets

| Dataset | Use | Size | License (to verify before use) |
|---|---|---|---|
| **IITM BS transcripts, slides and assignments** | Course pack (primary) | Gathered by the team | For course use only |
| **ASSISTments 2009–2010** [7] | Train and test DKT | ~346k answers, 4,217 students, 123 skills [3] | Research use, per provider terms |
| **EdNet KT1** [8] (optional) | Larger learning-pattern data for DKT | ~95M answers, ~784k students | CC BY-NC 4.0 |
| **FoundationalASSIST** (candidate) | Learning patterns | To review | To verify |
| **MathDial** [18] (public tutoring dialogues) + our IITM BS examples | Fine-tune the Socratic model | 2,861 dialogues + examples written by us | CC BY-SA 4.0 (MathDial) |
| **NCERT textbooks** | Course pack (second domain) | Several classes of Mathematics | Public; no redistribution of raw files |

### Why ASSISTments for training Deep Knowledge Tracing (DKT)

DKT must first learn how students' knowledge develops, from many **real student answer histories** (which question, which skill, right or wrong, in what order). We use ASSISTments 2009–2010 because:

1. **It has the data DKT needs.** It contains about 346,000 real answers from 4,217 students, each tagged with a skill and ordered in time. IITM does not publish student answer data of this kind.
2. **It is the standard benchmark for DKT.** The original DKT paper and the pyKT benchmark both use it, so we can check our model against published scores (DKT: 0.754 AUC) and know our training is correct.
3. **It is mathematics.** Its skills (fractions, equations, graphs, etc.) are close to the foundation maths behind IITM courses and to the NCERT course pack.
4. **It is free for research** and widely used, with known data issues (such as duplicate rows) already documented, so we can clean it properly.

**Limitation:** ASSISTments is from US school students, not IITM learners. It teaches DKT *how learning generally progresses*, not IITM concepts. For IITM courses, the tutor starts with a simple fallback (recent accuracy per concept) and retrains DKT if anonymised IITM student data becomes available.

---

## 7. Baseline metrics and our targets

| Part | Metric | Baseline (what we compare with) | Our target |
|---|---|---|---|
| Learner model | AUC | Simple per-concept accuracy; published DKT: 0.754 | AUC ≥ 0.74 and better than the simple baseline |
| Socratic model | % of replies that reveal the answer | Base model (before fine-tuning); LLM API + system prompt | ≤ 5%, lower than both baselines |
| Socratic model | Quality score from a rubric (1–5): relevant, one question at a time, correct | Same baselines | Higher than the base model |
| Backtracking | % of test learners whose gap course/concept is correctly found | LLM API + system prompt | ≥ 85% |
| Search (RAG) | Correct resource in top 5 (Recall@5) | Keyword search (BM25) | ≥ 0.80 |
| Full tutor | % of test scenarios handled correctly | Fixed rules; LLM API + system prompt | ≥ 90% |

---

## 8. Evaluation plan

1. **Annotated test set:** we will write and label 60–100 test scenarios, mainly from IITM BS courses (e.g. careless mistake, gap one course back, gap two courses back, no gap, success only after a hint). Any test samples provided for the course will also be used.
2. **Compare three tutors on the same scenarios:**
   - a standard chatbot that answers directly,
   - **an LLM API with a Socratic system prompt** (the typical industry approach),
   - **our tutor**.
3. **Learner model:** DKT vs the simple baseline on students not seen in training; compare with published research numbers [3].
4. **Socratic model:** base model vs our fine-tuned model vs LLM API, scored on answer leakage and the rubric, on held-out tutoring dialogues and our IITM scenarios.
5. **Domain-agnostic check:** the same tests on the IITM BS and NCERT packs, with no code changes.
6. **Fairness:** test scenarios are fixed before the final comparison and never used for tuning.

---

## 9. Data samples

### 9.1 ASSISTments 2009–2010 (for training DKT)

Each row is one answer by one student:

| user_id | skill_name | correct | hint_count | attempt_count |
|---|---|---|---|---|
| 64525 | Equivalent Fractions | 0 | 2 | 3 |
| 64525 | Equivalent Fractions | 1 | 0 | 1 |
| 64525 | Box and Whisker | 1 | 0 | 1 |

*Values show the format. `correct` is 1 only if the first attempt was right without hints.*

### 9.2 IITM BS training example (for fine-tuning the Socratic model)

Each training example pairs a tutoring situation with a good tutor reply:

| | Content |
|---|---|
| **Concept** | Derivatives (Maths 2) |
| **Question** | For L(w) = (6 − 2w)², what is dL/dw? |
| **Learner's reply** | "I don't know" |
| **Controller action** | PROBE a prerequisite; do not reveal the answer |
| **Resource** | Maths 2, Week 5, Lecture 2 (08:15) |
| **Target tutor reply** *(probing)* | "Let's step back. For y = 3x + 1, how much does y change when x increases by 1?" |

Each tutor reply is labelled (*probing*, *focus*, *telling*), so the model learns to probe instead of tell. *Illustrative example written by the team.*

### 9.3 Course pack examples (illustrative)

**IITM BS, across courses (primary):**
```text
Maths 1: functions, slope of a line        Stats 1: mean, variance
   → Maths 2: vectors, dot product, derivatives, chain rule
      → MLF: loss functions, gradient descent
         → MLT: training linear regression
```

**NCERT Mathematics, across classes (second domain):**
```text
multiplication → division → fractions → decimals, percentages
```

A study-material entry (the same format for every course):
```json
{
  "course": "iitm-maths2",
  "concept": "derivatives",
  "type": "video",
  "source": "Maths 2, Week 5, Lecture 2",
  "location": "08:15–11:30",
  "text": "The derivative of a function at a point is the slope of the tangent at that point ..."
}
```

---

## 10. Expected outputs

### 10.1 Tutoring session with backtracking (IITM example from the brief, mock-up)

```text
Learner:  How does training happen in Linear Regression?

Tutor:    Let's work it out together. In supervised learning, what do we
          give the model during training?
Learner:  Inputs and their correct outputs.                          ✓
Tutor:    Our model predicts y = w·x. If w = [2, 1] and x = [3, 4],
          what does it predict?
Learner:  10                                                         ✓
Tutor:    The true y is 12. What is the squared error?
Learner:  4                                                          ✓
Tutor:    To reduce the error, we need to know how it changes as w changes.
          For L(w) = (6 − 2w)², what is dL/dw?
Learner:  I don't know.
          [gap found in Maths 2: derivatives → checking Maths 1: slope]
Tutor:    Let's step back. For the line y = 3x + 1, how much does y change
          when x increases by 1?
Learner:  3                                                          ✓
Tutor:    Right, that's the slope. A derivative is the slope at a point.
          What is the derivative of w²?   📺 Maths 2, Week 5, Lecture 2 (08:15)
Learner:  2w                                                         ✓
          [back to Maths 2]
Tutor:    Now use the chain rule on (6 − 2w)². Hint: the inside changes at −2.
Learner:  2(6 − 2w)(−2) = −4(6 − 2w)                                 ✓
          [back to MLF / MLT]
Tutor:    At w = 1 the gradient is −16. It's negative, so should w go up or
          down to reduce the loss?
Learner:  Up.                                                        ✓
Tutor:    Exactly: w ← w − (learning rate) × gradient. That's gradient
          descent, and repeating it is how linear regression is trained!
          📺 MLT Week 2, Lecture 3 (12:40)
```

### 10.2 Progress report (shown to the learner)

| Course | Concept | Correct (without help) | Readiness estimate |
|---|---|---|---|
| Maths 1 | Slope of a line | 2 / 2 | 0.90 |
| Maths 2 | Derivatives and chain rule | 1 / 2 | 0.64 |
| MLF | Gradient descent | 1 / 1 | 0.70 |
| MLT | Training linear regression | 1 / 2 | 0.60, more practice suggested |

### 10.3 Current vs expected (LLM API + system prompt vs our tutor)

| | Response to "How does training happen in Linear Regression?" |
|---|---|
| **LLM API with a Socratic prompt (typical today)** | Usually gives the full explanation at once: "We minimise the mean squared error with gradient descent, updating w ← w − η∇L…". The learner reads the answer but is never checked, and a gap in derivatives stays hidden. |
| **Our tutor (expected)** | Guides step by step, finds the derivative gap, revisits Maths 1 and Maths 2 with lecture links, then returns to MLT. The learner works out the update rule themselves. |

### 10.4 Same pipeline, second domain (NCERT, short example)

A learner answers "20% of 50" with 2.5. The tutor asks what "20%" means, finds a gap in fractions, practises a few fraction and division questions with a link to the NCERT page, then returns to the percentage question. The learner finds 10. Only the course pack changes; the code is the same.

---

## 11. References

1. Piech et al. (2015). *Deep Knowledge Tracing.* NeurIPS.
2. Corbett & Anderson (1994). *Knowledge Tracing.* User Modeling and User-Adapted Interaction. (AUC as reported in [1].)
3. Liu et al. (2022). *pyKT: A Python Library to Benchmark Deep Learning based Knowledge Tracing Models.* NeurIPS Datasets & Benchmarks. https://arxiv.org/abs/2206.11460. AUC values: Table 2 and Table 8 (question level, ASSISTments 2009); dataset statistics: Table 1.
4. Xiong et al. (2016). *Going Deeper with Deep Knowledge Tracing.* EDM.
5. Bastani et al. (2025). *Generative AI without guardrails can harm learning.* PNAS.
6. Tack & Piech (2022). *The AI Teacher Test.* EDM.
7. ASSISTments 2009–2010 Skill Builder data. https://sites.google.com/site/assistmentsdata
8. Choi et al. (2020). *EdNet: A Large-Scale Hierarchical Dataset in Education.* AIED. https://github.com/riiid/ednet
9. Hu et al. (2022). *LoRA: Low-Rank Adaptation of Large Language Models.* ICLR.
10. Qwen3-4B-Instruct-2507 model card. https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
11. Carnegie Learning. *MATHia* overview video. https://youtu.be/sjfw_7jXoBk
12. Khan Academy. *Khanmigo* overview video. https://youtu.be/I1JVQg52DDI
13. McGraw Hill. *ALEKS* overview video. https://youtu.be/mxOWeJ_lhEc
14. ASSISTments. Overview video. https://youtu.be/8t62Aj-VGig
15. Ghosh, Heffernan & Lan (2020). *Context-Aware Attentive Knowledge Tracing.* KDD.
16. Zhang, Shi, King & Yeung (2017). *Dynamic Key-Value Memory Networks for Knowledge Tracing.* WWW.
17. Pandey & Karypis (2019). *A Self-Attentive Model for Knowledge Tracing.* EDM.
18. Macina et al. (2023). *MathDial: A Dialogue Tutoring Dataset with Rich Pedagogical Properties Grounded in Math Reasoning Problems.* Findings of EMNLP. https://github.com/eth-nlped/mathdial

---

## 12. Team sign-off

By signing, each member confirms they have read this report, understand it and agree to submit it.

| Name | Roll number | Signature | Date |
|---|---|---|---|
| Sandeep Nalla | 21f1006125 | | |
| Hariom Kumar | 23f2004225 | | |
| Hariom Pandey | 21f3002112 | | |
| Mrityunjay Chakraborty | 21f3001385 | | |

*Drafted with help from an AI assistant and reviewed by the team.*
