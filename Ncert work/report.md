> **Historical notes.** This document describes earlier runs and is not current status. Read [CURRENT_CHECKPOINT.md](CURRENT_CHECKPOINT.md), generated from current release manifests. Earlier human-review/local-model instructions do not apply to the current app.

<!-- pilot-hardening-2026-11-04 -->
# Current pilot result — 4 November 2026

Source/score gates, current vector integrity and offline app/controller checks pass. Retrieval was tested on 83 original textbook questions/challenges over 22 usable passages. General automatic routing failed coverage and is disabled. Native Eedi retrieval improved from 16% to 26% on a fresh same-task 300-group test; broad misconception diagnosis remains experimental. Qwen ID selection is removed; only six calculation-corroborated, unconfirmed rule families can produce suggestions. Live model teaching is deferred by the user.

[Full changes, measurements and remaining work](PILOT_HARDENING.md). Earlier entries below are historical and superseded where they conflict.

---

<!-- automatic-validation-2026-11-03 -->
# Automatic validation — 3 November 2026

No human review is required. [Automatic validation](AUTOMATIC_VALIDATION.md) reports the passing vector integrity audit and Codex source sampling. The latter found unresolved OCR, currency and reading-order issues; flags are advisory until future question promotion consumes them. The full NCERT/tutor work is not yet complete.

---

<!-- model-human-db-handoff-2026-11-03 -->
## Model, human-review and database access handoff — 3 November 2026

[Review and model handoff guide](REVIEW_AND_MODEL_HANDOFF.md) now includes the temporary authenticated Kaggle notebook, a 241-record private human review packet, the proposed unseen-evaluation decision gates and verified pgAdmin/SQL/storage paths. No new diagnosis/model-quality result is claimed. All 38 unit tests pass; notebook code compiles; read-only database queries pass. The owned local cluster was started. User model identity/training exposure and human decisions remain pending.

---

<!-- revised-plan-checkpoint-2026-11-03 -->
# Current revised-plan result — 3 November 2026

[Current checkpoint, evidence and remaining work](CURRENT_CHECKPOINT.md) supersedes the historical execution notes below. The pilot rerun, official Kaggle acquisition/local loads and bounded retrieval baselines are complete. The full plan remains unfinished; the previous goal was cleared by the user; Qwen diagnostic selection, source-bank item review, backend demo and Classes 6–10 expansion remain.

**Current counts:** 9 PDFs / 203 pages / 3,090 blocks / 396 assets; all 34 solution pages use MinerU. 119 source questions / 86 extracted official keys / 14 worked examples; 984 candidate chunks, 12 accepted retrieval chunks. 38 unit tests plus real Grade 8 parser assertions passed.

---

# Consolidated NCERT execution report

Updated: 2 November 2026. Owner: Hariom Kumar; execution assisted by Codex.
Status: **Draft pipeline through extraction, cleaning and EDA executed. No accepted
content/database/model release yet; the full M3 goal remains in progress.**

## Actual results

- Verified 8 official edition-specific PDFs, **20,413,502 bytes / 191 physical pages**.
- Audited 191/191 pages; ran PyMuPDF/MinerU on 15 identical benchmark pages.
- Built canonical records for **191 pages / 3,980 blocks / 342 assets** with complete
  page/source/raw-output lineage and no extraction failures.
- Used MinerU on 91 chapter-content pages; retained 100 native private/excluded
  pages, including **23 solution pages / 1,564 private answer blocks**.
- Reused 12 benchmark pages and parsed 79 new pages in 11 resumable batches. A
  cached rerun reused all 91 pages with **zero new inference**. Before the explicit
  OCR-provenance adapter revision, canonical block IDs/records matched exactly;
  after the correction, text/LaTeX/HTML/privacy and cleaned hashes still match.
- Cleaned 3,980 → 3,980 traceable block records, logging **1,537** changes and **228**
  candidate margin removals; **705** blocks remain quarantined. LaTeX/table HTML
  remain unchanged; numeric lines/operators/units are preserved.
- Generated reconciled EDA, source/content-type counts, a chart and review queues.
  The clean-release manifest is **pending, with 0 accepted records**.
- Passed **18 boundary checks**: 6 setup/data-loss, 2 benchmark identity, 4 extraction,
  4 cleaning and 2 release-quality checks. A separate one-page parser memory case
  passed its runtime/source-page assertions and measured the main process only.
- Researched three response-model candidates and pinned their public revisions;
  no response-model inference, training or teaching-quality result is claimed.

Evidence: [source manifest](01_download_pdfs/manifests/sources.csv),
[page accounting](04_extract_text_and_ocr/outputs/page_accounting.csv),
[asset lineage](04_extract_text_and_ocr/outputs/assets_manifest.csv),
[rerun check](04_extract_text_and_ocr/outputs/rerun_check.json),
[cleaning rules](05_clean_and_preprocess/outputs/cleaning_rules.csv),
[quarantine](05_clean_and_preprocess/outputs/quarantine.csv),
[EDA summary](06_eda_and_quality/outputs/eda_summary.json),
[release gate](06_eda_and_quality/outputs/clean_release_manifest.json).
Local bulk text, originals, images, model files and logs remain ignored by Git.

## Scope and coverage

| Initial chapter PDF | Book/edition | Intended objective |
| --- | --- | --- |
| Grade 6 Ch 7 Fractions | Ganita Prakash, reprint 2026–27 | Equal sharing, unit/equivalent fractions |
| Grade 7 Ch 8 Working with Fractions | Ganita Prakash Part I, reprint 2026–27 | Fraction multiplication/division |
| Grade 8 Ch 7 Comparing Quantities | Mathematics, reprint 2024–25 | Fractions/percentages and percent of a quantity |
| Grade 7 Ch 7 Heat Transfer in Nature | Curiosity, reprint 2026–27 | Conduction/convection/radiation |

The denominator is 43 chapters in these four book/part contents lists: 4/43 =
**9.30%**, with 39 excluded chapters. This is an initial processing sample, not
10–20% of the full Classes 6–10 curriculum. The older Grade 8 edition stays
explicit. Four prelim PDFs supply provenance and do not become retrieval evidence.
Chapter files also contain appended solutions, activities or notes; all physical
pages are retained but their roles differ. Twenty-two questions remain a target,
not a produced/approved practice bank. Supported concepts remain unapproved.

## Phase status

| Phase | Actual status | Evidence |
| --- | --- | --- |
| 00 Setup/scope | Setup/validation ran; independent scope/interface confirmations pending | [Report](00_setup_and_scope/report.md) |
| 01 Acquisition | Integrity checks completed; 8/8 PDFs | [Report](01_download_pdfs/report.md) |
| 02 Audit | 191 pages audited; 15 visual observations, independent review pending | [Report](02_pdf_audit/report.md) |
| 03 Parser benchmark | Same-page runs and scoped process memory measured; quality/policy review pending | [Report](03_parser_benchmark/report.md) |
| 04 Extraction | Draft 191 pages / 3,980 blocks / 342 assets; validation/cache rerun pass | [Report](04_extract_text_and_ocr/report.md) |
| 05 Cleaning | Draft transforms/logs/quarantine executed | [Report](05_clean_and_preprocess/report.md) |
| 06 Quality/EDA | Counts/figures/gates executed; accepted release pending | [Report](06_eda_and_quality/report.md) |
| 07 Content/questions/chunks | 6 concepts, 12 chunks. Codex questions removed; 116 NCERT questions, 70 NCERT answers, 14 worked examples extracted | [Report](07_concepts_questions_and_chunks/report.md) |
| 08 Graph | 15 grade-ordered candidate pairs, 3 approved by Codex review; no semantic similarity used | [Outputs](08_prerequisite_graph/outputs/graph_metrics.json) |
| 09 Diagnostic/scope mapping | 6 misconception labels and 18 synthetic examples written by Codex; KT mapping deferred | [Outputs](09_skill_misconception_and_scope_mapping/outputs/mapping_coverage.json) |
| 10 Embeddings/database | 12 chunks embedded (BGE-small, 384-d) and loaded into local Postgres+pgvector; reload pending after question change | [Outputs](10_embeddings_and_database/outputs/database_counts.json) |
| 11 Retrieval evaluation | 26 synthetic queries; cutoff sweep says 0.67 / 0.01 (provisional) | [Report](11_retrieval_and_evaluation/report.md) |
| 12 Model feasibility | Three model cards/API revisions researched; no inference comparison | [Report](12_socratic_model_feasibility/report.md) |
| 13 Backend/M3 demo | Not run | [Instructions](13_backend_handoff_and_m3_demo/README.md) |
| 14 Scale/maintenance | Later, after accepted M3 | [Instructions](14_scale_and_maintenance/README.md) |

## Update, 2 November evening

- **Parser routing**: maths goes to MinerU (74/75 pages have formulas), science goes to PyMuPDF
  unless a table is found (2/16 pages to MinerU). See the [Phase 03 report](03_parser_benchmark/report.md).
- **Questions**: Codex-written practice items were removed. The bank is now NCERT-only: 116 questions,
  70 answers from NCERT's solution pages, 14 worked examples, stored in separate tables. See the [Phase 07 report](07_concepts_questions_and_chunks/report.md).
- **Concept cutoff**: 0.67 / 0.01 instead of 0.70 / 0.02 gets 25/26 queries right, up from 21/26. The safety gap is only 0.006. See the [Phase 11 report](11_retrieval_and_evaluation/report.md).
- **Still AI-written**: Phase 09 misconception examples and Phase 12's `evaluation/answers_private.jsonl`.
- **Run on Windows** after the question change (new corpus_version), in this order: `07.../build_content_pack.py`, `08.../build_graph.py`,
  `10.../embed_chunks.py`, `10.../load_database.py`, `10.../load_ncert_questions.py`, `11.../evaluate_retrieval.py`.

## Quality boundaries and next work

No semantic correctness score is claimed. All remaining 28 private-use glyphs
occur in private/excluded material; chapter-content blocks contain zero, but
character presence does not establish formula meaning. A spurious MinerU header
and chapter-number/page-number confusion remain review examples. Physical pages
always bind to source PDFs, and printed labels are not inferred from predictions.

MinerU provides batch-level mode/log evidence. Its 91 per-page OCR booleans remain
unknown, alongside resolved batch modes/internal OCR observations; 100 native
pages have OCR false. Auto mode can vary with selected page batches, so source,
page set/configuration and exact raw outputs are retained. No blanket second OCR
system was run.

Four quality pages are disjoint from the 15 parser-development pages. Pre-extraction
native audit/boundary probes existed and are disclosed; no human quality references
were used to tune the parser. Human source/reference/critical checks remain pending
in [quality_annotations.csv](06_eda_and_quality/outputs/quality_annotations.csv).
The [reference review packet](03_parser_benchmark/evidence/review_packet.md) and
[working route policy](03_parser_benchmark/outputs/working_parser_policy.json)
make the remaining decisions inspectable. The working policy is distinct from an
accepted parser/content policy.

Next: source/semantic review and a release decision, then concepts/questions,
private answers, token-aware evidence, reviewed graph and retrieval/database work.
Response-model runtime/independent teaching comparisons can progress separately.
Sandeep's integration contract and actual team reviews are not fabricated. Skill
mapping remains deferred; no checkpoint index is guessed. The 161 held-out team
scenarios have not been used for prompt/model/data selection.

A one-page MinerU CPU run measured **1,933,508,608 bytes** main-process peak working
set through parse/export. Descendant/whole-corpus peak, response-model throughput
and retrieval accuracy remain unmeasured. This is not a general hardware-fit claim.

Reproduction: [environment commands](00_setup_and_scope/config/environment.md)
and each phase report. [Execution summary](execution_summary.json) records actual
commands, runs and hashes; [artifact index](artifact_index.json) identifies current
small artifacts/code. First-run snapshots and append-only logs remain local.
The repository revision plus per-file hashes identify currently uncommitted work;
no claim is made that the old commit already contains these scripts.

Backend and the old preparation script remain unchanged. No graph approval,
model training, vector/database load, public content release or connected demo
has occurred. Source-specific permissions and all independent sign-offs remain
pending; no real learner data was introduced.
