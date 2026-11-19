# Work Contribution Log: Milestone 4

**Project:** Socratic AI Tutor for NCERT Classes 6–10: guiding a learner to the answer through probing questions
**Team:** Group 2, Data Science and AI Lab, IIT Madras BS
**Date:** 19 November 2026
**Live app:** https://socratic-ai-tutor-z2s0.onrender.com/
**Repository:** `Hariomkr147/Group-2-DS-and-AI-Lab-Project`
**Models and dataset:** https://huggingface.co/IITM-2026T3-DSAI-GROUP2

## Team

| Name | Roll number | Primary role |
|---|---|---|
| Sandeep Nalla | 21f1006125 | Backend developer |
| Hariom Kumar | 23f2004225 | Build the RAG (search) agent |
| Hariom Pandey | 21f3002112 | Build the fine-tuned models |
| Mrityunjay Chakraborty | 21f3001385 | Frontend developer |

These are primary roles only. They are not fixed: as the project needs, members contribute to other parts as well, and in M4 roles overlapped across components.

## Work split for this milestone

| Area | Owner | Models / components |
|---|---|---|
| Full Qwen Socratic model training and benchmarking | Hariom Pandey | Qwen3.5-4B, LoRA, full pool of 20,104 examples |
| Knowledge-tracing fix and NCERT-to-skill mapping | Mrityunjay Chakraborty | DKT (LSTM, GRU, RNN), SAKT, AKT, simpleKT, AT-DKT, QIKT; mapping review queue |
| Backend, misconception detection and prerequisite graph | Sandeep Nalla | FastAPI backend, AKT loader, session stack, step finder, prerequisite graph |
| NCERT corpus, retrieval, hosting and guardrails | Hariom Kumar | Qwen3-Embedding-0.6B, pgvector, HF Space, TF-IDF message router |


## Contributions

| Name | Work done |
|---|---|
| Sandeep Nalla | Built the backend (auth, sessions, AKT loader and checkpoint swap, controller and session stack; `backend/`, `backend/models/akt/`); built the misconception and step finder (`step_finder.py`) and evaluated it on 50 cases (`backend/eval/misconception/`); compiled the end-to-end pipeline; built the dynamic prerequisite graph from the notebook (`Ncert work/08_prerequisite_graph/`); wrote the Tier A shortlist and merge script; tested the working app |
| Hariom Kumar | Benchmarked RAG retrievers; prepared the full NCERT database on GPU (130 PDFs, 3,066 pages, 7,221 passages, Qwen3 embeddings, Supabase pgvector; `Ncert Extraction Notebook/`, notebooks 01–06, including the full-corpus routing check); hosted the LLM (`backend/model_hosting/hf-space/`); built the message router and guardrails (`backend/eval/message_router/`, `message_router.joblib`); ran the backend topic audit and fixed tutoring behaviour; ran the frontend audit (`docs/frontend-audit.md`) and the chat-history layout; launched the mixed maths + science Qwen run (`qwen35_unsloth_full.ipynb`); documentation |
| Hariom Pandey | Ran the full Qwen3.5-4B training end to end on the complete dataset (`qwen-3-5.ipynb`, 1,500 steps on one T4) with all metrics and hyperparameters; produced the final adapter (`lora_adapter.zip`); benchmarking; wrote the analysis of whether NCERT data is needed for training (report Section 3.3) |
| Mrityunjay Chakraborty | Fixed the knowledge-tracing pipeline (merged multi-skill steps) and ran the ten-model comparison (`kt-models-comparision.ipynb`, checkpoint and ID maps); built the NCERT-to-skill mapping pack (skill vocabulary, 365-concept review sheet, science list; `Ncert Pack/`); tested the working app; documentation |

## Documents

| Document | File |
|---|---|
| Report | `M4_Report.md` |
| Presentation | `M4_Presentation.pdf` (also `.pptx`) |
| Work log | `Work_Contribution_Log.md` |
| AI usage logs | `ai-log/<person>/` |

## Sign-off

By signing, each member confirms that this log is accurate and that they have reviewed the report and presentation.

| Name | Roll number | Signature | Date |
|---|---|---|---|
| Sandeep Nalla | 21f1006125 | <img src="../signatures/sandeep_nalla.png" alt="signature" height="48"> | 19-11-2026 |
| Hariom Kumar | 23f2004225 | <img src="../signatures/hariom_kumar.png" alt="signature" height="48"> | 19-11-2026 |
| Hariom Pandey | 21f3002112 | <img src="../signatures/hariom_pandey.png" alt="signature" height="48"> | 19-11-2026 |
| Mrityunjay Chakraborty | 21f3001385 | <img src="../signatures/mrityunjay_chakraborty.png" alt="signature" height="48"> | 19-11-2026 |
