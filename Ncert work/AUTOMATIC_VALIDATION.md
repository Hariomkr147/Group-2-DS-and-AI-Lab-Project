> **Historical notes.** This document describes earlier runs and is not current status. Read [CURRENT_CHECKPOINT.md](CURRENT_CHECKPOINT.md), generated from current release manifests. Earlier human-review/local-model instructions do not apply to the current app.

# Automatic validation — 4 November 2026

The user delegates source judgment to Codex and does not need to review each item or embedding. Technical integrity, transcription checks, passage suitability and model accuracy are reported separately.

- [Source release gates](06_eda_and_quality/outputs/release_gate_checks.json): pass; 57 block corrections, one page-order correction, 55 unresolved currency positions excluded.
- [Sample source observations and resolutions](06_eda_and_quality/outputs/automatic_source_sample.json): hour/exercise-currency/reading-order findings repaired; diagram-dependent material excluded. The native-font audit still flags 16 pages and is not a corpus accuracy score.
- [Item gate](07_concepts_questions_and_chunks/outputs/item_review_summary.json): 119 questions / 297 solution items dispositioned; 20 complete rubric-eligible source/key pairs. Unverified material and publisher-key conflicts cannot be scored.
- [Embedding integrity](10_embeddings_and_database/outputs/automatic_embedding_audit.json): pass for 22 current NCERT and 8,117 Eedi stored vectors; all NCERT vectors and a deterministic 20-Eedi sample recomputed. No visual review of numeric embedding coordinates is required.
- [Retrieval challenge](11_retrieval_and_evaluation/outputs/textbook_retrieval_metrics.json): 83 publisher question/challenge cases. Relevant concept in top five for 13/15 supported test questions. Automatic routing fails positive coverage and is disabled.
- [Diagnostic comparison](09_skill_misconception_and_scope_mapping/outputs/diagnostic_improvement_metrics.json): native Eedi Recall@5 improves 16% → 26% on the same fresh 300-group task. This is insufficient for broad diagnosis. Six exact-calculation families can produce unconfirmed suggestions; Qwen no longer selects arbitrary labels.
- [Offline integrated check](../mock-app/logs/offline_hardening_checks.json): passes without response-model calls, using real artifacts and ephemeral learner history. Fifty-two affected unit tests pass.

[Full decision and remaining work](PILOT_HARDENING.md). Historical human-review packets are not a requirement. Live Qwen/UI testing is deferred; source quarantine and broad model-quality limits remain visible.
