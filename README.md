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

**Visuals:** the tutor links to the exact moment in existing lecture videos and shows simple diagrams (fraction bars, percentage grids, number lines, graphs). AI-generated videos or animations are **out of scope**: they are expensive, slow and error-prone for maths.

## How it works

| Component | Role |
|---|---|
| Learner model (DKT) | Our trained LSTM that estimates what the learner knows for each concept |
| Tutor controller | Our logic that decides the next step: probe, hint, backtrack, retest, move up |
| Socratic question model | Qwen3-4B fine-tuned by us with LoRA on MathDial: writes probing questions |
| Search (RAG) | Finds the relevant study material |
| Web app | React + FastAPI + PostgreSQL (pgvector) |

The tutor is **domain-agnostic**: each subject is added as a *course pack* (concepts, prerequisite links, study material, questions). We build two:

- **NCERT content** across several classes that build on each other (primary, chosen because the textbooks are public and complete). Any subject with study material uses the same pipeline.
- **IITM BS course material**: Maths & Stats → MLF → MLT (secondary, to show the pipeline is reusable)

**Status:** planning stage (Milestone 1). Code will be added in later milestones.

## Team

| Name | Roll number | Primary role |
|---|---|---|
| Sandeep Nalla | 21f1006125 | Backend developer |
| Hariom Kumar | 23f2004225 | Build the RAG (search) agent |
| Hariom Pandey | 21f3002112 | Build the fine-tuned models |
| Mrityunjay Chakraborty | 21f3001385 | Frontend developer |

Roles are not fixed; members contribute to other parts as the project needs.

## License

[Apache License 2.0](LICENSE)
