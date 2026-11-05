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

| Component | Role | Milestone 3 choice |
|---|---|---|
| Learner model (knowledge tracing) | Estimates what the learner knows for each concept | AKT with Rasch question difficulty, test AUC 0.843 on ASSISTments 2009 (best of 7 models) |
| Tutor controller | Decides the next step: probe, hint, backtrack, retest, move up | Rule-based, in the demo app |
| Socratic question model | Writes the next probing question, never the answer | Qwen 3.5-4B fine-tuned with QLoRA on SocraTeach + MathDial; 0 answer leaks, ROUGE-L 0.19 → 0.33 |
| Search (RAG) | Finds the relevant NCERT passage and cites the page | BM25 + BGE-small rank fusion over 124 automatically built passages; Hit@5 80% |
| Web app | Class → Chapter → Topic → chat | FastAPI demo (`mock-app/`); planned production stack React + FastAPI + PostgreSQL (pgvector) |

The tutor is domain-agnostic: each subject is added as a *course pack* (concepts, prerequisite links, study material, questions). We build two:

- NCERT content across several classes that build on each other (primary, chosen because the textbooks are public and complete). Any subject with study material uses the same pipeline.
- IITM BS course material: Maths & Stats → MLF → MLT (secondary, to show the pipeline is reusable).

## Status

Milestone 3 is done: model selection, baselines, hyperparameter tuning and an end-to-end pipeline.

- Four small LLMs compared (Qwen 3.5-4B, Gemma 4 E4B, Phi-4-mini, Qwen3-4B trial); Qwen 3.5-4B selected.
- Seven knowledge-tracing models compared (DKT LSTM/GRU/RNN, SAKT, SAKT + positions, AKT, AKT + Rasch); AKT + Rasch selected.
- NCERT pilot release built automatically: 124 passages, 25 topics, 84 approved questions.
- Demo app built on the pilot release; it calls the hosted Qwen model. The live Qwen step with retrieved passages is not yet tested, and the app still loads the earlier DKT checkpoint. Both are planned for Milestone 4.

Milestone 2 (datasets, EDA, course packs) is in `docs/milestone-2/`. The IITM BS pack is not built yet.

### Milestone 3 deliverables

| Document | Files |
|---|---|
| Report | [`M3_Report.md`](docs/milestone-3/M3_Report.md), [`.pdf`](docs/milestone-3/M3_Report.pdf), [`.docx`](docs/milestone-3/M3_Report.docx) |
| Presentation | [`M3_Presentation.pdf`](docs/milestone-3/M3_Presentation.pdf), [`.pptx`](docs/milestone-3/M3_Presentation.pptx) |
| Work log | [`Work_Contribution_Log.md`](docs/milestone-3/Work_Contribution_Log.md), [`.pdf`](docs/milestone-3/Work_Contribution_Log.pdf), [`.docx`](docs/milestone-3/Work_Contribution_Log.docx) |

Fine-tuned adapters and the processed dialogue dataset: https://huggingface.co/IITM-2026T3-DSAI-GROUP2

## Repository layout

| Path | Contents |
|---|---|
| `docs/milestone-1/`, `docs/milestone-2/`, `docs/milestone-3/` | Milestone reports, slides and work logs |
| `docs/milestone-3/socratic_data_prep/` | Dialogue data preparation and candidate subset |
| `docs/milestone-3/model_finetune/` | QLoRA notebooks, results and the four-model comparison |
| `docs/milestone-3/model_hosting/` | Notebook that serves the Qwen adapter over HTTPS |
| `docs/milestone-3/KT_model/` | Knowledge-tracing comparison notebook, results, AKT weights, skill and question maps |
| `Ncert work/` | NCERT pipeline: parsing, passage builder, questions, embeddings, retrieval evaluation ([`PILOT_REPORT.md`](Ncert%20work/PILOT_REPORT.md)) |
| `mock-app/` | FastAPI demo tutor ([`README.md`](mock-app/README.md)) |
| `backend/` | Backend service |
| `notes/` | Each member's working notes |

## Run the demo

On Windows, from `mock-app/`, run `./start.ps1` in PowerShell and open http://127.0.0.1:8765. It needs the Python environment in `Ncert work/.venv` and a running hosted Qwen endpoint; see [`mock-app/README.md`](mock-app/README.md) for setup and checks.

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
