# milestone-5-prerequisite-audit-and-docs (2026-11-26)

## Prompts
1. Build a reusable Kaggle notebook (`final_prerequisite_graph.ipynb`) that pulls passages from any Postgres table via configurable SQL, extracts concepts and prerequisite edges with JSON Schema structured output, removes cycles, grounds every edge in source quotes, and saves versioned runs to `learning_graph` tables.
2. Run the pipeline across all 6,858 eligible NCERT Classes 6-10 Maths and Science passages, run a second-model audit on isolated concepts and weak links to eliminate orphans, and export a standalone offline HTML viewer (`ncert-prerequisite-graph.html`) with search, grade/subject filters, and dual-endpoint citations.
3. Verify the notebook works generically on custom courses (test with a CA Foundation fixture in local Postgres) and write a clean `README.md` for Kaggle setup and `view`/`reaudit`/`build` modes.
4. Audit the live Supabase `ncert_research` database for release `3371af5f8052352316dad173`: check chapter-wise chunk counts, verify zero missing textbook pages, check runtime answer-key filters in `ncert.py`, diff the two existing releases, safely purge the old duplicate release, and verify how `learning_graph` links back to `ncert_research.passages`.
5. Audit the team's Milestone 3-5 deliverables (KT models, Socratic datasets, OCR/embedding/guardrail benchmarks, backend RAG routing, and prerequisite graph) against live DB metrics and repo artifacts, and compile the Milestone 5 audit report and AI-usage documentation.

## Tools and packages
- **OpenAI Sol 6.2** — used for Part 1 (prerequisite graph notebook, multi-model audit pipeline, HTML viewer) and Part 2 (live Supabase DB audit, release diffing, cleanup, and schema interlink verification).
- **Claude Opus 5.5** — used for Part 3 (cross-milestone audit of team evals, models, datasets, and Milestone 5 documentation).
- Python, `psycopg`, `nbformat`, `scikit-learn`, `python-dotenv`, Playwright, PostgreSQL / pgvector, Kaggle Model Proxy, and Git.

## What the AI did
- **Prerequisite Graph Notebook & Visual HTML (OpenAI Sol 6.2):**
  - Built `final_prerequisite_graph.ipynb` with configurable `SOURCE_SQL`, `view`/`reaudit`/`build` modes, SQLite response caching, cycle removal, and transactional `learning_graph` persistence.
  - Processed 6,858 eligible NCERT passages across 130 chapters, ran second-model verification to resolve 210 isolated concepts (186 prerequisite links + 24 related study topics), and published approved run `a0716faaa4d372850af91b6e09d0f5107254e427a2ee3bb40e82a4a794ab4870` (840 concepts, 741 approved links, 0 cycles).
  - Exported `ncert-prerequisite-graph.html` (verified in Playwright on desktop/mobile) and `README.md`, tested custom-course support on a CA Foundation fixture, and pushed `notes/hariom kumar/milestone-5/Prerequisite/` to `origin/main` (commit `41d27ecc`).
- **Supabase DB Status & Cleanup Audit (OpenAI Sol 6.2):**
  - Audited active release `3371af5f8052352316dad173` (7,221 passages, 130 chapters, 130 unique source PDFs, 7,153 approved, 68 quarantined `answer_risk`, 0 NULL content/embeddings).
  - Audited chapter-wise chunk counts and verified all 15 physical page gaps across 6 chapters are image-only pages (tangram cutouts, fraction walls, isometric grids, graph paper), confirming full text coverage.
  - Verified runtime safety filters in `backend/app/services/ncert.py` (`length >= 80`, `answer_risk`/`replacement_character` exclusion, `Ans:`/`Ans.`/`Solution` heading regex).
  - Diffed `9aea0ce28990f86074b2d813` vs `3371af5f8052352316dad173` (identical text/flags, 6 minor embedding diffs) and transactionally purged the old release (7,221 rows) without disrupting retrieval.
  - Verified 100% cross-schema linkage from `learning_graph` to `ncert_research.passages` via JSONB `evidence.source_id` -> `passage_id` (7,595/7,595 node refs; 3,813/3,813 edge refs).
- **Team Evals, Models & Datasets Audit + Milestone 5 Docs (Claude Opus 5.5):**
  - Audited all Milestone 3-5 assets (KT models, Socratic fine-tuning datasets, OCR/embedding/guardrail benchmarks, backend retrieval, and prerequisite graph outputs) against live database metrics and repository state.
  - Authored `notes/hariom kumar/milestone-5/audit/REPORT.md` documenting verified metrics, safety checks, non-blocking corpus observations, and transparent AI-assistance attribution.
