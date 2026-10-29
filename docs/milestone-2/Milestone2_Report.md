# Milestone 2 Report: Dataset Preparation

**Course:** Data Science and AI Lab, IIT Madras BS
**Team:** Group 2
**Submission:** Milestone 2, 29 October 2026

| Name | Roll number | Primary role |
|---|---|---|
| Sandeep Nalla | 21f1006125 | Backend developer |
| Hariom Kumar | 23f2004225 | Build the RAG (search) agent |
| Hariom Pandey | 21f3002112 | Build the fine-tuned models |
| Mrityunjay Chakraborty | 21f3001385 | Frontend developer |

*Roles are not fixed; members contribute to other parts as the project needs.*

**Goal of this milestone:** collect suitable datasets and prepare them for training and validation.

The data was prepared in two versions, so that Milestone 3 can compare them:
- **Version A** (Sandeep Nalla): scripts in `notes/sandeep/milestone-2/data/scripts/`, outputs in `notes/sandeep/milestone-2/data/processed/`. Raw files and large outputs are not committed; `notes/sandeep/milestone-2/data/README.md` shows how to rebuild them.
- **Version B** (Hariom Pandey): Colab workflow, outputs and write-ups in `notes/hariom pandey/milestone-2/`. Ready-made arrays for DKT and a chat corpus for fine-tuning.

Sections 2 and 6 give both side by side.

## 1. Datasets

| Dataset | Used for | Prepared in | Source | License |
|---|---|---|---|---|
| ASSISTments 2009-2010 | Train and test the learner model (DKT) | A and B | assistmentsdata site [1, 3] | Research use; cite the data page and Feng et al. (2009) |
| MathDial (2,861 dialogues) | Fine-tune the Socratic model | A and B | github.com/eth-nlped/mathdial; `eth-nlped/mathdial-chat` on Hugging Face | CC BY-SA 4.0 on GitHub, CC BY 4.0 on Hugging Face; we follow the stricter one |
| SocraTeach Multi (10,273 problems, 35,151 dialogues) | Fine-tune the Socratic model | B only | `ulises-c/SocraTeach_Multi` on Hugging Face [2] | CC BY-NC 4.0 (non-commercial) |
| NCERT Maths and Science, classes 6-10 | Course pack (study material for search) | A only | ncert.nic.in | Public; text kept local, not redistributed |

EdNet was not used: ASSISTments is enough for the DKT baseline.

## 2. Preparation steps and results

### ASSISTments, version A (learner model)
1. Sort each student's answers in time order; remove duplicates.
2. Remove 63,755 answers with no skill label, and students with fewer than 3 answers (same recipe as pyKT).
3. Number the skills 0..148 and cut each history into windows of at most 200 answers.
4. Split **by student** so no student is in two sets.

| | Students | Windows | Answers | Correct rate |
|---|---|---|---|---|
| Train | 3,081 | 3,571 | 228,924 | 65.9% |
| Validation | 385 | 449 | 28,037 | 66.4% |
| Test | 386 | 434 | 25,644 | 64.8% |

Raw: 346,860 answers, 4,217 students. Clean: 282,619 answers, 3,852 students, 149 skills. (Milestone 1 quoted 123 skills from pyKT; the raw file has 149 skill ids, and we did not merge any.)

### ASSISTments, version B (learner model, Hariom Pandey)
Starts from a 303,260-row skill-builder file and keeps four columns: student, order, skill and correct (first try).

| Step | What was done | Rows after |
|---|---|---|
| 1 | Load the 4 columns | 303,260 |
| 2 | Remove 1 row with missing values | 303,259 |
| 3 | Remove 46,668 duplicates (same student, order and skill) | 256,591 |
| 4 | Remove 325 students with fewer than 3 answers | 256,073 |

5. Number the skills 0..81 (82 skills). Encode each answer as one number: `x = skill + 82 x correct` (0 to 163, so 164 possible inputs).
6. Sort by student and time. Questions with several skills stay as separate steps. Long histories are cut into chunks of 200 answers (cutting at 200 would lose about 27% of the rows); chunks under 3 steps are dropped (8 chunks, 13 answers); short chunks are padded with zeros and a mask marks real steps.
7. Split **by student**, 80% train and 20% test, seed 42. There is no validation set.

| | Students | Sequences | Answers | Correct rate | Skills used |
|---|---|---|---|---|---|
| Train | 2,726 | 3,168 | 205,418 | 65.7% | 82 |
| Test | 682 | 781 | 50,642 | 64.4% | 80 |
| Total | 3,408 | 3,949 | 256,060 | | |

Files: `dkt_data.npz` (arrays X, S, C, M for train and test, plus N), `dkt_processed_steps.csv` (every step with its split, student, chunk and original skill id), `skill_map.csv` (82 rows: new index to original skill id), `SHA256.txt`.

### MathDial, version A (Socratic model)
1. Split each dialogue into turns and read MathDial's label for each tutor reply (probing, focus, generic, telling).
2. Make one training example per tutor reply: problem, hidden reference solution, the student's wrong solution and the conversation so far, then the next tutor reply as the target.
3. Mark `keep = false` for "telling" replies and replies containing the final answer. They are saved but not used as targets.
4. Keep MathDial's own test set. Validation is cut from train **by problem**, because the same problem appears in several dialogues.

| | Dialogues | Examples | Kept | Leak the answer |
|---|---|---|---|---|
| Train | 2,045 | 13,380 | 10,797 | 838 |
| Validation | 217 | 1,475 | 1,182 | 81 |
| Test | 599 | 3,686 | 2,972 | 275 |

Note: 283 of the 394 test problems also appear in train (MathDial's own split). We keep it so results match the paper, but a score on unseen problems should be reported separately.

### MathDial and SocraTeach, version B (Socratic model, Hariom Pandey)
Each dialogue becomes one chat record with a `messages` list (system, assistant, user), for fine-tuning Qwen2.5-1.5B-Instruct.
1. **SocraTeach:** expand the 10,273 problems into their 35,151 dialogues. The tutor's text becomes an `assistant` message and the student's reply a `user` message; turn order is kept. All dialogues were kept.
2. **MathDial** (`mathdial-chat`, train split): keep the existing system/assistant/user messages, trim whitespace, remove 4 empty messages. All 2,262 conversations were kept. The 599 test conversations are held out and not in the file.
3. Merge into `socratic_tutor_combined.jsonl`, with a `source` tag on each record (the tag is spelled `soctrateach` in the file).

| Source | Conversations | Assistant messages | User messages | System messages |
|---|---|---|---|---|
| SocraTeach | 35,151 | 185,600 | 150,451 | 0 |
| MathDial (train) | 2,262 | 14,448 | 13,410 | 2,262 |
| Total | 37,413 | 200,048 | 163,861 | 2,262 |

Checks reported: no empty messages, no invalid records, no duplicate SocraTeach dialogue ids, JSON valid. In SocraTeach, 2 turns had no tutor text. Every SocraTeach dialogue starts with a tutor message.

### NCERT (study text)
Maths and Science, classes 6-10: 10 books, 116 chapters, 2,401 pages. Text is extracted page by page, cleaned, and split into chunks of up to 250 words, each tagged with subject, class, chapter and page: **3,164 chunks**. Four pages failed extraction (drawings) and were skipped. Chapter titles are verified for the 20 chapters we use; the rest are marked `needs_review`.

## 3. Course packs (concepts, prerequisites, practice questions)

Hand-written in `notes/sandeep/milestone-2/data/course_packs/specs.py` and built into the backend's course-pack format by `build_course_packs.py`. Each concept points to the NCERT chapter that teaches it, and the builder attaches the best-matching text from that chapter.

| Pack | Concepts | Prerequisite links | Practice questions |
|---|---|---|---|
| NCERT Maths (classes 6-8) | 10 | 13 | 52 |
| NCERT Science: motion and force (classes 6-9) | 6 | 6 | 18 |

- **Levels:** 1 whole-number operations, factors; 2 fractions, integers; 3 decimals, ratio, percentages, letter expressions; 4 linear equations. The main example follows this chain: percentages -> fractions -> multiplication and division.
- **Questions:** written by the team in the style of the NCERT exercises, each with a hint and difficulty. Answers are computed in code, not typed, so they cannot be mistyped.
- **Checks:** every prerequisite exists, none is at a higher level, no cycles, every concept has questions and study text.

## 4. Test scenarios (our own, 159 in total)

Written by the team, kept separate from training data and never used for tuning (`notes/sandeep/milestone-2/data/test_scenarios/`).

| Set | Items | What it tests |
|---|---|---|
| Backtracking | 82 | Learner is correct (16), careless mistake (16), correct after a hint (16), gap one level down (19), gap two levels down (15). Label: the first tutor action and the weak prerequisite to go back to. |
| Misconceptions | 32 | A wrong answer and the error behind it (24 kinds, e.g. dividing 50 by 20 for "20% of 50", adding tops and bottoms of fractions). |
| Guardrails | 45 | 15 on-topic, 15 off-topic (including other subjects and "ignore your instructions"), 15 answer requests. |

Backtracking labels come from the prerequisite graph, so they are consistent by construction; they test the tutor's logic, not real learners. Every item has an empty `reviewed_by` field for a second team member to check. TA-provided samples will be added when received.

## 5. Checks
`check_data.py` passes: no student shared between splits, no problem shared between MathDial train and validation, skill ids in range, labels 0/1, kept examples never tell or leak the answer, NCERT chunk ids unique, pack graphs valid, scenario labels consistent (23 checks). These cover version A.

Version B checks (Hariom Pandey): row counts add up (303,260 - 1 - 46,668 = 256,591), `x = skill + 82 x correct` holds for every real step, student counts match (2,726 and 682), and train and test correct rates are close (65.7% and 64.4%). The 13-answer gap between 256,073 and 256,060 is the dropped short chunks. `test_dkt_data.py` re-prints the shapes and statistics from the `.npz` file, and `SHA256.txt` holds file hashes.

## 6. Version A and version B compared

| | Version A (Sandeep) | Version B (Hariom Pandey) |
|---|---|---|
| **ASSISTments** | | |
| Input file | corrected file, 346,860 answers | skill-builder file, 303,260 answers |
| Skills | 149 | 82 |
| Answers after cleaning | 282,619 | 256,060 |
| Students | 3,852 | 3,408 |
| Splits | train / validation / test (80/10/10 by student) | train / test (80/20 by student), seed 42 |
| Format | JSONL, one window per line | `.npz` arrays with mask, plus a step-level CSV |
| **Socratic model data** | | |
| Sources | MathDial | MathDial and SocraTeach |
| Unit | one tutor reply per example, with the problem, solution and history | one whole conversation |
| Size | 18,541 examples (13,380 + 1,475 + 3,686) | 37,413 conversations |
| Splits | train / validation (by problem) / test | train only; MathDial test held out |
| Answer-leak flag | yes (`keep`) | no |
| **Other** | NCERT chunks, 2 course packs, 159 test scenarios | none |

How the two relate:
- **MathDial:** version B's 2,262 conversations are version A's train and validation dialogues (2,045 + 217). Both hold out the same 599 test dialogues.
- **ASSISTments:** the two should not be mixed. They differ in input file, skill count and split, so models trained on one cannot be scored on the other.
- **Version B is the more convenient for fast model training** (fixed-length arrays, chat format); **version A is the more careful for evaluation** (validation set, answer-leak flag, problem-level split).
- **Licence:** SocraTeach is CC BY-NC 4.0, so the corpus is fine for coursework but not for redistribution or a commercial product.
- **Not yet done on version B's chat corpus:** no deduplication across the two sources, no marking of answer-telling replies, and SocraTeach's step and persona fields are dropped. Both sources are maths only.

## 7. Limits and next steps
- ASSISTments is US data and has no session information, so session-scoped DKT (mentor feedback) cannot be tested on it; windows of 200 answers are used instead.
- Version B: a chunk after a student's first starts without that student's earlier history, rows for questions with several skills count as several steps, and its test set uses 80 of the 82 skills.
- The answer-leak check is a simple number match and can miss answers written in words. We accept this for now.
- NCERT text quality: the older Class 8-10 maths books lose some digits and symbols in extraction (e.g. "80/100" appears as "80100"), and the study passages attached to each concept are picked automatically, so some are exercise text. Each needs a manual pass before use in search.
- The packs cover one chain per subject (10 Maths and 6 Science concepts). More chapters can be added by extending `specs.py`; no code change is needed.
- Concepts and prerequisite links are our own judgement, so a second member should review them.
- Next: train DKT on both ASSISTments versions and compare, fine-tune the Socratic model on MathDial (and SocraTeach if the licence allows), and have a second member check the scenarios.

## 8. References
1. ASSISTments data page (Goldstein, Baker and Heffernan, 2011): https://sites.google.com/site/assistmentsdata/datasets/2011-goldstein-baker-heffernan
2. SocraTeach_Multi dataset card, Hugging Face (CC BY-NC 4.0): https://huggingface.co/datasets/ulises-c/SocraTeach_Multi
3. ASSISTments data file (Google Drive): https://drive.google.com/file/d/0B2X0QD6q79ZJUFU1cjYtdGhVNjg/view?resourcekey=0-OyI8ZWxtGSAzhodUIcMf_g

## 9. Team sign-off

By signing, each member confirms they have read this report, understand it and agree to submit it.

| Name | Roll number | Signature | Date |
|---|---|---|---|
| Sandeep Nalla | 21f1006125 | <img src="../signatures/sandeep_nalla.jpg" alt="Signature of Sandeep Nalla" height="40"> | 2026-10-29 |
| Hariom Kumar | 23f2004225 | <img src="../signatures/hariom_kumar.jpg" alt="Signature of Hariom Kumar" height="40"> | 2026-10-29 |
| Hariom Pandey | 21f3002112 | <img src="../signatures/hariom_pandey.jpeg" alt="Signature of Hariom Pandey" height="40"> | 2026-10-29 |
| Mrityunjay Chakraborty | 21f3001385 | <img src="../signatures/mrityunjay_chakraborty.jpg" alt="Signature of Mrityunjay Chakraborty" height="40"> | 2026-10-29 |

*Drafted with help from an AI assistant and reviewed by the team.*
