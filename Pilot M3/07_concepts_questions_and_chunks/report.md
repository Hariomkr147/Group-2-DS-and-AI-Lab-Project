> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- pilot-hardening-2026-11-04 -->
## Current repair result — 4 November 2026

Current corpus ncert-pilot-2ecfcf34cd6278d0 has 22 approved evidence chunks over six objectives. All 984 candidates have dispositions: 22 approved, 546 quarantined, 416 outside the bounded release, zero pending. All 119 questions and 297 solution items have dispositions; 22 prompts and 21 key items are approved, with 20 complete rubric-eligible pairs. The mock uses only seven explicitly selected scalar checkpoints. Publisher key/unit conflicts are blocked.

See [Pilot repairs and decision](../PILOT_HARDENING.md) for evidence, measured limits and remaining gates. Earlier entries below are historical and superseded where they conflict.

---

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Source-only bank: 119 questions / 86 official extracted answers / 14 worked examples, all pending item review; every cleaned block has exactly one role, with zero conflicts. Grade 8 answers are linked by explicit exercise/question identifiers and actual physical pages. All eligible explanation blocks produce 984 candidates (18 approved, 642 pending, 324 quarantined); only 12 approved mapped chunks enter retrieval. Six concepts; no generated content questions/keys. Bank run `20261102T190716-21ddee50`; build run `20261102T190717-d32ce163`, release `ncert-pilot-fd981363bc7f493a`.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 07 execution report — concepts, chunks and NCERT questions

Updated: 2 November 2026 (evening). Owner: Hariom Kumar.

## Content pack (run 20261102T150240-2cd3ef2e, earlier today)
6 concepts and 12 evidence chunks (max 182 BGE tokens) from the 44-block accepted cleaned release.
Reviewer: Codex on the user's behalf; no independent human review.

## Change: no AI-written questions or answers
The pack's 20 practice questions (18 written by Codex, 2 transcribed) and their 20 Codex-derived
answers were removed at the user's request. The files were moved, not deleted, to
`evidence/_retired_codex_authored/`. `build_content_pack.py` no longer reads them, so the next pack
run creates a **new corpus_version**. That means re-running the embedding, graph, database load and retrieval steps (see the root report).

## NCERT question bank (`code/extract_ncert_questions.py`)
Questions come only from NCERT text. Answers come only from NCERT's appended solution pages
(Grade 6 p37–50, Grade 7 p31–39). Those 23 pages were re-parsed with MinerU 4.1.3 Basic ONNX CPU
using the same model revision (all 13 model-file hashes match `mineru_model_files.json`), because
the PyMuPDF text flattened every fraction. Raw output:
`04_extract_text_and_ocr/native_outputs/answer-key-mineru/` (Grade 6 took 519 s, Grade 7 178 s, on a 2-CPU cloud machine).

| Output | Count |
| --- | ---: |
| Questions ([ncert_questions.jsonl](outputs/ncert_questions.jsonl)) | 116 |
| — from chapter pages: Figure it Out / Try These / Exercise / Let Us Enhance Our Learning | 87 |
| — from NCERT solution pages, not matched to a chapter-page question | 29 |
| Questions with an NCERT answer ([ncert_answers_private.jsonl](outputs/ncert_answers_private.jsonl)) | 70 (G6 50, G7 20) |
| Questions marked as needing a diagram | 29 |
| Worked examples with NCERT solution ([ncert_worked_examples.jsonl](outputs/ncert_worked_examples.jsonl)) | 14 (G7 4, G8 10) |
| Invented questions / answers | 0 / 0 |

Answer-key questions are linked to chapter questions by word similarity of the question opening
(≥0.6). 5 links scored 0.6–0.8 and are flagged `link_needs_review`. The printed-page offsets learned
from the links (150 for G6, 172 for G7) match the labels visually checked in Phase 02.

Gaps:
- Grade 8 and science have no answer pages in these PDFs (`answer_available=false`). For Grade 8,
  NCERT publishes a separate answers PDF that can be added the same way.
- Science answers can be generated later by the Socratic model, stored as model-generated and kept separate.
- Not extracted: questions inside the narrative text, activities, and unlabelled prompts.
- Questions are not yet tagged to concepts.
- Two answers exist only as pictures.
- One OCR slip is visible: G6 p155 answer (e) reads "18" where 1/8 is expected.
- All rows are `review_status=pending`.

Check: `code/test_extract_ncert_questions.py` (answer-key parsing and linking) passes.
Load into separate DB tables, independent of the frozen pilot version:
`10_embeddings_and_database/code/load_ncert_questions.py` → `ncert_content.ncert_questions`,
`ncert_content.ncert_worked_examples`, `ncert_private.ncert_answers`.
**Not yet loaded**: the Postgres cluster runs on Windows localhost, which this session cannot reach.
