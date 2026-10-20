# Socratic AI Tutor

An intelligent small-scale tutor that **guides a learner to the answer through probing questions**, instead of giving the answer directly.

Group 2 project for the **Data Science and AI Lab**, IIT Madras BS.

> **Why "Socratic"?** Named after the Greek philosopher Socrates, who taught by asking questions that led students to discover answers themselves.

## What it does

When a learner has a doubt, the tutor:

1. **Breaks the question down** into the smaller ideas it depends on.
2. **Asks probing questions**, one at a time.
3. **Checks the answer**, spots misconceptions and gives feedback with a link to the right page, slide or video.
4. **Backtracks to earlier levels** if there is a gap (e.g. stuck on percentages → revisit fractions and division), then climbs back up.
5. **Adapts** with a short diagnostic test and generated practice questions at the learner's pace.

## How it works

| Component | Role |
|---|---|
| Learner model (DKT) | Our trained LSTM that estimates what the learner knows for each concept |
| Tutor controller | Our logic that decides the next step: probe, hint, backtrack, retest, move up |
| Socratic question model | Qwen3-4B fine-tuned by us with LoRA on MathDial: writes probing questions |
| Search (RAG) | Finds the relevant study material |
| Web app | React + FastAPI + PostgreSQL (pgvector) |

The tutor is **domain-agnostic**: each subject is added as a *course pack* (concepts, prerequisite links, study material, questions). We use two examples:

- **NCERT Mathematics** across several levels (main pilot)
- **IITM BS courses** (Maths → MLF → MLT)

## Repository contents

| Path | Contents |
|---|---|
| [docs/milestone-1/Milestone1_Report.md](docs/milestone-1/Milestone1_Report.md) | Milestone 1 report |
| [docs/milestone-1/Milestone1_Presentation.pptx](docs/milestone-1/Milestone1_Presentation.pptx) | Milestone 1 presentation |
| [docs/milestone-1/Work_Contribution_Log.md](docs/milestone-1/Work_Contribution_Log.md) | Team contribution log |
| `docs/milestone-1/build_figures.py`, `build_presentation.py` | Scripts that regenerate the figure and slides |

**Status:** planning stage (Milestone 1). Code will be added in later milestones.

## Team

| Name | Roll number |
|---|---|
| Sandeep Nalla | 21f1006125 |
| Hariom Kumar | 23f2004225 |
| Hariom Pandey | 21f3002112 |
| Mrityunjay Chakraborty | 21f3001385 |

## License

[Apache License 2.0](LICENSE)
