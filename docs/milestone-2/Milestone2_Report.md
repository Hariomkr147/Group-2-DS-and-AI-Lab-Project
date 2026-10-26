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

All code is in `data/scripts/`. Raw files and large outputs are not committed; `data/README.md` shows how to rebuild them.

## 1. Datasets

| Dataset | Used for | Source | License |
|---|---|---|---|
| ASSISTments 2009-2010 (corrected) | Train and test the learner model (DKT) | assistmentsdata site | Research use |
| MathDial (2,861 dialogues) | Fine-tune the Socratic model | github.com/eth-nlped/mathdial | CC BY-SA 4.0 on GitHub, CC BY 4.0 on Hugging Face; we follow the stricter one |
| NCERT Maths and Science, classes 6-10 | Course pack (study material for search) | ncert.nic.in | Public; text kept local, not redistributed |

EdNet was not used: ASSISTments is enough for the DKT baseline.

## 2. Preparation steps and results

### ASSISTments (learner model)
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

### MathDial (Socratic model)
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

### NCERT (course pack)
Maths and Science classes 6-10, 10 books, 114 chapters, 2,401 pages. Text is extracted page by page, cleaned, and split into chunks of up to 250 words, each tagged with subject, class, chapter and page: **3,261 chunks**. Classes are used as levels (6 to 10). Four pages failed extraction (drawings) and were skipped.

## 3. Checks
`check_data.py` passes: no student shared between splits, no problem shared between MathDial train and validation, skill ids in range, labels 0/1, kept examples never tell or leak the answer, NCERT chunk ids unique.

## 4. Limits and next steps
- ASSISTments is US data; it teaches DKT how learning progresses, not NCERT concepts.
- It has no session information, so session-scoped DKT (mentor feedback) cannot be tested on it; windows of 200 answers are used instead.
- The answer-leak check is a simple number match and can miss answers written in words.
- NCERT chapter titles are guesses and need a manual pass. Concepts, prerequisite links and practice questions are still to be written.
- Our own labelled scenarios for the test set (backtracking, misconceptions, guardrails) are not started.

## 5. Team sign-off

By signing, each member confirms they have read this report, understand it and agree to submit it.

| Name | Roll number | Signature | Date |
|---|---|---|---|
| Sandeep Nalla | 21f1006125 | | |
| Hariom Kumar | 23f2004225 | | |
| Hariom Pandey | 21f3002112 | | |
| Mrityunjay Chakraborty | 21f3001385 | | |

*Drafted with help from an AI assistant and reviewed by the team.*
