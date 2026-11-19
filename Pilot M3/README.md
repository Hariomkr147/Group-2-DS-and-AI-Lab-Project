# NCERT content pipeline

[Current checkpoint](CURRENT_CHECKPOINT.md) is generated from release manifests. [PILOT_REPORT.md](PILOT_REPORT.md) explains the latest release methodology and measured limits. Older reports are historical.

- Rebuild content: `./rebuild_release.ps1` (PowerShell, from this folder).
- Start the tutor: `../mock-app/start.ps1`. PostgreSQL is used by offline build/evaluation; the mock reads the frozen files and keeps sessions in SQLite.
- The app uses the user-hosted fine-tuned model only. Live model testing is deferred; no human review of individual embeddings is required.
- [Retired workflows](_archive/README.md) preserve old human-review, local-LLM and synthetic-evaluation scripts.

## Start here

1. Read [PLAN.md](PLAN.md) for the workflow, priorities, dependencies, M3 acceptance and effort estimates.
2. Read [DATA_CONTRACTS.md](DATA_CONTRACTS.md) before writing processing code or generating IDs.
3. Follow the numbered phase [READMEs](#phase-index), which specify tasks, proposed scripts, inputs, outputs and completion checks.
4. Update the phase `report.md` after each real run. Begin with real counts and evidence; leave unmeasured values as **Not measured**.
5. Regenerate [CURRENT_CHECKPOINT.md](CURRENT_CHECKPOINT.md) after a release (`00_setup_and_scope/code/update_checkpoint.py`, included in `rebuild_release.ps1`). Keep dated reports as snapshots; do not duplicate current counts across documents.

## Ownership and scope

Hariom Kumar owns PDF acquisition, NCERT extraction/OCR decisions, preprocessing/EDA, content/questions, RAG, prerequisite content, curriculum mapping review and Socratic-model research. The pilot is from English-medium NCERT Mathematics and Science Classes 6–10, with exact book editions and supported objectives declared before processing.

Hariom Pandey owns assessment/chat preparation and KT/response-model training. He supplies the exact trained skill vocabulary and checkpoints. Sandeep owns backend/controller/guardrail integration and consumes Hariom's content and retrieval outputs. Misconception examples and skill mapping need their collaboration. NCERT preparation and RAG development are not assigned to Sandeep.

This is a fresh source-to-artifact process. No GyanSetu content or prior database dump is required. Existing source code may be inspected for reusable behavior, but old derived data is not treated as the new pipeline's output.

## Phase index

| Phase | Detailed instructions | Actual-run report | Estimated active effort, hours | Status (5 Nov) |
| --- | --- | --- | --- | --- |
| 00 | [Setup, pilot scope and reproducibility](00_setup_and_scope/README.md) | [Execution report](00_setup_and_scope/report.md) | 1–2 | Done (pilot) |
| 01 | [Acquire and preserve original NCERT PDFs](01_download_pdfs/README.md) | [Execution report](01_download_pdfs/report.md) | 1–2 | Done (pilot) |
| 02_pdf_audit | [Pre-extraction audit and initial EDA](02_pdf_audit/README.md) | [Execution report](02_pdf_audit/report.md) | 1–2 | Done (pilot) |
| 03_parser_benchmark | [Compare PyMuPDF, MinerU and conditional OCR](03_parser_benchmark/README.md) | [Execution report](03_parser_benchmark/report.md) | 3–5 | Done (pilot) |
| 04_extract_text_and_ocr | [Produce canonical page/block records with OCR where required](04_extract_text_and_ocr/README.md) | [Execution report](04_extract_text_and_ocr/report.md) | 2–4 | Done (pilot) |
| 05_clean_and_preprocess | [Clean conservatively without damaging mathematics](05_clean_and_preprocess/README.md) | [Execution report](05_clean_and_preprocess/report.md) | 3–5 | Done (pilot) |
| 06_eda_and_quality | [Post-extraction EDA, quality evaluation and freeze](06_eda_and_quality/README.md) | [Execution report](06_eda_and_quality/report.md) | 2–3 | Done (pilot) |
| 07_concepts_questions_and_chunks | [Build source-grounded concepts, practice questions and evidence chunks](07_concepts_questions_and_chunks/README.md) | [Execution report](07_concepts_questions_and_chunks/report.md) | 4–6 | Done (automatic release) |
| 08_prerequisite_graph | [Propose, review and publish prerequisite links](08_prerequisite_graph/README.md) | [Execution report](08_prerequisite_graph/report.md) | 4–6 | Done (3 edges) |
| 09_skill_misconception_and_scope_mapping | [Map curriculum to KT skills, misconception labels and supported topics](09_skill_misconception_and_scope_mapping/README.md) | [Execution report](09_skill_misconception_and_scope_mapping/report.md) | 3–5 | Partial (KT mapping deferred) |
| 10_embeddings_and_database | [Embed accepted evidence and create a local retrieval database](10_embeddings_and_database/README.md) | [Execution report](10_embeddings_and_database/report.md) | 3–5 | Done (pilot) |
| 11_retrieval_and_evaluation | [Compare retrieval, resolve concepts and verify citations](11_retrieval_and_evaluation/README.md) | [Execution report](11_retrieval_and_evaluation/report.md) | 4–6 | Done (labels need refresh) |
| 12_socratic_model_feasibility | [Hariom's model research and deployment feasibility evidence](12_socratic_model_feasibility/README.md) | [Execution report](12_socratic_model_feasibility/report.md) | 2–4, parallel with other phases | Done (remote model only) |
| 13_backend_handoff_and_m3_demo | [Package Hariom's outputs and demonstrate the connected M3 tutor](13_backend_handoff_and_m3_demo/README.md) | [Execution report](13_backend_handoff_and_m3_demo/report.md) | 3–5, shared integration time | Partial (demo app; team backend pending) |
| 14_scale_and_maintenance | [M4 onward: expand the same pipeline and maintain releases](14_scale_and_maintenance/README.md) | [Execution report](14_scale_and_maintenance/report.md) | Estimate after pilot measurements | Planned |

Estimates are planning ranges for a bounded pilot, not measured runtimes, deadlines or full Classes 6–10 coverage promises.

## Folder layout

```text
Ncert work/
|-- README.md
|-- PLAN.md
|-- DATA_CONTRACTS.md
|-- report.md
|-- .gitignore
|-- 00_setup_and_scope/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- config/
|   |-- logs/
|-- 01_download_pdfs/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- pdfs/
|   |-- manifests/
|   |-- logs/
|-- 02_pdf_audit/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- figures/
|   |-- evidence/
|   |-- logs/
|-- 03_parser_benchmark/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 04_extract_text_and_ocr/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- native_outputs/
|   |-- outputs/
|   |-- assets/
|   |-- evidence/
|   |-- logs/
|-- 05_clean_and_preprocess/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 06_eda_and_quality/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- figures/
|   |-- evidence/
|   |-- logs/
|-- 07_concepts_questions_and_chunks/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 08_prerequisite_graph/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 09_skill_misconception_and_scope_mapping/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 10_embeddings_and_database/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- vectors/
|   |-- exports/
|   |-- evidence/
|   |-- logs/
|-- 11_retrieval_and_evaluation/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- evaluation/
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 12_socratic_model_feasibility/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- evaluation/
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 13_backend_handoff_and_m3_demo/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- exports/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
|-- 14_scale_and_maintenance/
|   |-- README.md
|   |-- report.md
|   |-- code/                  # planned scripts; not implemented
|   |-- outputs/
|   |-- evidence/
|   |-- figures/
|   |-- logs/
```

Phase 00–06 scripts are implemented and have run; Phase 12 research has started. Later content/database/integration code remains to be implemented. The original layout above is the planning scaffold. Consult each actual-run report for executed work. Git does not preserve empty directories.

## Operating rules

- Original PDFs are immutable; downloaded PDFs live only under `01_download_pdfs/pdfs/`.
- Code belongs in its phase's `code/`; configuration and manifests have their named folders.
- Run scripts from a consistent root and resolve paths from the project root, not an assumed current directory. Quote the root path because it contains a space.
- Parser-native output, raw canonical extraction, cleaned content and embedded releases are separate stages.
- EDA happens before extraction, after extraction/cleaning, and after chunking/mapping; it is not a one-time transformation.
- OCR is conditional. MinerU can already perform OCR internally; record what actually happened.
- Proposed filenames and schema fields are contracts to implement and validate; they are not existing callable commands.
- Keep source provenance and review status through every stage. Keep private answer keys and real learner identifiers out of public reports/exports.
- All measured results need run ID, inputs/configuration, artifact version, sample size, hardware, failures and reproducible evidence.
- The 161 existing team scenarios stay independent test-only; no training, prompt selection or threshold tuning on them.

