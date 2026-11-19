> **Historical notes.** This document describes earlier runs and is not current status. Read [CURRENT_CHECKPOINT.md](CURRENT_CHECKPOINT.md), generated from current release manifests. Earlier human-review/local-model instructions do not apply to the current app.

# Pilot repairs and decision — 4 November 2026

The bounded NCERT tutor has stronger source and scoring gates. **The broad retrieval/diagnosis pilot has not passed a final accuracy gate.** Automatic topic routing and Qwen misconception-ID selection are disabled. Live teaching with the hosted model is deferred at the user's request. No local generative model was started.

## Sources and grading

- The nine original PDFs and raw extraction remain unchanged. A pre-change derived-data snapshot is retained in `00_setup_and_scope/logs/pre-hardening-20261104T165235.zip`.
- **57 cleaned blocks corrected**, with exact original-source hashes and before/after values. These include `h0ur` → `hour`, the missing sugarcane-answer blank, and recoverable ₹ symbols from the original PDF font/coordinates. Physical science page 6 now places upper convection text before lower Land and Sea Breeze text.
- **55 ambiguous currency positions remain unresolved and excluded from active evidence.** The source-symbol audit still flags 16 native-font pages; flags are not automatically erased because some glyphs remain ambiguous. No corpus-wide OCR accuracy claim is made.
- **89 blocks pass transcription/source checks.** Transcription agreement alone does not make a useful retrieval passage: incomplete dialogue, teacher instructions, diagram references and incorrectly assigned objectives were excluded separately.
- **984 chunk candidates dispositioned:** 22 approved and indexed, 546 quarantined, 416 outside the bounded release, zero pending. Disposition is not approval. The 22 passages cover the same six objectives; no arbitrary currency formula, answer key or worked example entered the evidence index.
- **119 question records and 297 official solution items dispositioned:** 22 source-checked prompts, 97 quarantined prompts; 21 approved key items, 67 quarantined and 209 outside the included question bank. **20 complete source/key pairs are eligible for rubric-based assessment.** Only 86 linked answer records are stored in the question-bank database; unlinked items remain in the local extracted solution file.
- The official key for the question asking how many students are not interested gives “28% students”. The original question and publisher key disagree in units, so this pair cannot be scored. A Moon-setting question also requires a time rubric rather than parsing the key's first number. Neither was silently replaced with an invented official answer.
- The mock tutor retains its **seven explicitly selected, checked maths checkpoints**, including one isolated percentage subpart. The 20 rubric pairs are not 20 interchangeable scalar questions. Science teaching has evidence but no automatic scored science checkpoint.

Source gates: [release checks](06_eda_and_quality/outputs/release_gate_checks.json), [item decisions](07_concepts_questions_and_chunks/outputs/item_review_summary.json), [content manifest](07_concepts_questions_and_chunks/outputs/content_manifest.json). The user does not need to inspect embeddings or approve every item.

## Larger retrieval check

The new protocol uses **all 83 publisher-text question records**, rather than paraphrasing the old 26 synthetic queries. Labels were assigned against the six objectives before ranking. Whole source/section/page groups stay in one split. There are 19 supported questions, 11 partial questions, 16 visual cases, 12 extraction/boundary challenges and 25 outside-objective questions. Three oversized inputs are rejected intact, without truncation.

The split has 24 calibration cases (four supported) and 59 test cases (15 supported). This is a wider challenge, **not 83 positive independent learner queries**. After an initial 52-chunk run, standalone passage checks pruned the corpus to 22. Relevance labels/splits were preserved; the test questions were reused, so this is not a fresh independent confirmation.

| Method, 15 supported test questions | Concept Hit@1 | Concept Hit@5 | Concept MRR@5 |
| --- | ---: | ---: | ---: |
| BM25 | 46.7% | 80.0% | 0.546 |
| BGE cosine | 53.3% | 86.7% (13/15) | 0.649 |
| BM25 + BGE rank fusion | 46.7% | 86.7% (13/15) | 0.582 |

These are **concept relevance metrics**, not document Recall@5 or answer accuracy. Calibration chose conservative 0.90/0.10 cutoffs, which abstained on every test question: zero false acceptances among 44 challenges, **but zero accepted supported questions out of 15**. That is a failed automatic-router result, not a successful safety/coverage trade-off. The shared retriever now asks for one selected topic; the mock app already uses that selected topic to filter evidence. A topic selection does not prove that an arbitrary question is answerable from the corpus.

Evidence: [frozen protocol](11_retrieval_and_evaluation/evaluation/textbook_protocol_v2.json), [metrics](11_retrieval_and_evaluation/outputs/textbook_retrieval_metrics.json). The old synthetic results are retained as historical evidence, not the latest acceptance result.

## Misconceptions

The new local-only Eedi comparison uses **200 calibration and 300 previously unused test question groups**, excluding the old exposed test groups. Native Kaggle IDs (2,587 labels) and public graph IDs (8,117 labels) stay separate. Publisher competition rows were not sent to a hosted model.

| Same 300-case native-label task | Recall@5 | MRR@5 | Top-1 |
| --- | ---: | ---: | ---: |
| Question + incorrect-answer BGE baseline | 16.0% | 0.099 | 6.3% |
| Calibration-selected correct-answer/construct contrast + BM25 | 26.0% | 0.153 | 10.0% |

The public graph baseline covers 187/300 labels through exact text bridging (62.3%); covered-label Recall@5 is 10.7%. This is not comparable with the native-label score or the historical 19.2% result. The native contrast ranker is an evaluated research alternative, **not a claimed 26%-accurate deployed graph diagnosis system**.

The historical Qwen 1/6 label match does not establish classifier quality. Qwen is trained for Socratic replies, and its arbitrary candidate-ID selector has been removed from the runtime. The app now shows an unconfirmed Eedi suggestion only when an explicitly submitted wrong final answer and learner equations reproduce one of **six bounded wrong-method families**, checked using exact rational arithmetic. General English working, ambiguous steps, missing working, invalid arithmetic and unsupported methods return no selected label. A single answer never creates a persistent misconception label. Unit/property checks and synthetic calculation traces verify this program behaviour; they are not real-learner diagnosis accuracy.

Evidence: [new metrics](09_skill_misconception_and_scope_mapping/outputs/diagnostic_improvement_metrics.json), [frozen protocol](09_skill_misconception_and_scope_mapping/evaluation/diagnostic_improvement_protocol.json), `09_skill_misconception_and_scope_mapping/code/test_working_verifier.py`. The full public catalogue remains available for attributed research retrieval.

## Integration and remaining gates

The current release is `ncert-pilot-2ecfcf34cd6278d0`: six concepts, 22 BGE vectors and three prerequisite edges. PostgreSQL `ncert_pilot` on `127.0.0.1:54329` has the current content and approved-pair view. Older immutable corpus versions remain stored. The question-bank view and mock preparation both require approved, scoring-eligible question/key pairs. The mock app at `http://127.0.0.1:8765` was restarted against the current artifacts.

All 22 NCERT vectors were recomputed; all 8,117 Eedi vector IDs, texts, norms and database values were checked, with 20 Eedi vectors recomputed by a deterministic sample. [Embedding audit](10_embeddings_and_database/outputs/automatic_embedding_audit.json) passed. This checks integrity, not whether embedding coordinates are human-readable or every retrieval is useful.

**52 unit tests pass** across the affected phase suites and mock app, plus the real Grade 8 answer-splitting assertions. The offline real-artifact check uses ephemeral learner history and prohibits model calls; see [offline app checks](../mock-app/logs/offline_hardening_checks.json). UI visuals and live Qwen explanations/hints were not rechecked in this repair pass.

The remaining work before broader deployment is reliable free-form routing with useful positive coverage, source repair/coverage expansion for excluded material, held-out learner-query validation, and a separately validated misconception classifier or ranking model with learner-working labels. Live teaching must also be rerun against the user's hosted model. Updated DKT/skill mapping remains deferred; the mock keeps its previously attached temporary original DKT. **These repairs support a bounded demonstration, not a claim that all NCERT extraction or general misconception diagnosis is finished.**
