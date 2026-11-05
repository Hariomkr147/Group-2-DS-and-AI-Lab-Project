# App verification — 5 November 2026

Current release counts/status come from [CURRENT_CHECKPOINT.md](../Ncert%20work/CURRENT_CHECKPOINT.md). The checked release is `ncert-pilot-a2ac2147befaf6e1`: 124 passages and 25 topics. The app retains seven selected source checkpoints and SQLite sessions, and now uses the supplied trained AKT.

## Cleanup

- Removed runtime Eedi vector loading and similarity search. Suggestions now use exact working checks and direct lookup of the original catalogue text; catalogue/source integrity checks remain.
- Moved remote endpoint configuration/redirect protection into `llm.py`; removed the obsolete remote-diagnosis option. NCERT retrieval owns its pinned BGE encoder.
- Removed the unused curated chunk encoder; its tokenizer-boundary check now exercises the production automatic passage builder.
- Archived retired human-review, local-LLM and 26-query evaluation scripts. Kept datasets, models, benchmark results and private keys in their existing locations.
- Replaced conflicting current-status counts with a manifest-generated checkpoint and historical report labels. The rebuild now stops if a test fails.

## Checks completed

52 tests pass across the setup/checkpoint suite (7), passage/content suite (9), diagnostic suite (16), retrieval suite (5) and mock app (15). Endpoint URL/key/redirect validation and missing-catalogue failures remain covered.

The real-artifact [offline check](logs/offline_hardening_checks.json) passes with ephemeral learner history and zero response-model calls: mapped evidence for all 25 topics; all seven maths checkpoints; review continuation with history preserved; six working-supported suggestions; and six unsupported-working abstentions. Release/source gates also pass. No source content or embedding vectors were rebuilt for this code cleanup.

Live hosted-model teaching/hints and browser visuals were not rechecked. General diagnosis and automatic free-form topic routing remain unvalidated/disabled. Historical live traces remain in the local logs; they do not establish accuracy for this release. Use `check_live.py` later when the user-hosted endpoint is available.

## Over-engineering audit follow-up

- Cached validated endpoint settings and reused the HTTP opener. Successful reconnection clears the cache; failed reconnection preserves the saved URL. Redirect blocking and proxy bypass remain in place.
- Removed the unused `/api/sessions/{sid}/hints` route and migrated its live-check caller to `/messages` with an explicit hint intent and request ID. The Hint button calls `submitMessage('hint')` directly. Removed the unreferenced partial skill-name file.
- Kept the help filter: replacing it with intent membership would admit off-topic requests such as "Explain football". Kept both fraction cleaners: preparation emits `1/3` for numeric-key extraction, while display emits `(1)/(3)`; importing the server would also pull model dependencies into data preparation.
- Kept the short, accessible breadcrumb helpers, the persistence helper used by creation and tests, and the small DKT scan that preserves ambiguous-name handling. Their proposed replacements offer no meaningful simplification.

All 18 mock-app tests pass, including cache reuse/invalidation, failed reconnect preservation, blocked authenticated redirects, and hint retries without scoring. JavaScript syntax validation and the real-artifact offline check pass: evidence for all 25 topics, all seven checkpoints, review continuation, and six supported/unsupported diagnosis pairs, using ephemeral history and zero hosted-model calls. Live hosted-model and browser checks were not run for this follow-up.

## Supplied DKT checkpoint (superseded by AKT)

Imported `notes/hariom kumar/milestone-3/KT_model/dkt_model.pt` with its supplied `skill_map.csv`. The 123-skill checkpoint matches the existing 64-embedding/128-hidden LSTM architecture and interaction encoding. All tensors are preserved exactly; `models/dkt/metadata.json` records source and exported hashes. The previous 82-skill demo export is preserved in `models/dkt-demo-baseline`.

Named mappings are fraction multiplication (42), fraction division (38), and percentages (75, Percents). The general Percents skill takes priority over the distinct Percent Of skill (44). Fractions and science topics remain unmapped. Session history is unchanged; readiness is recomputed from the new model after restart. This verifies integration, not transfer accuracy on NCERT learners.

All 19 mock-app tests and the checkpoint-summary test pass. The added integration test verifies tensor equality with the supplied checkpoint, prediction parity, percentage-skill selection, and abstention on unmapped history. The real-artifact offline check passes with the new 123-skill model, confirms the three DKT readiness rows, completes all seven questions and a review restart, and makes zero hosted-model calls. Live model and browser checks were not run.

## AKT replacement

The active model is now the supplied `akt_best.pt.zip`, copied byte-for-byte to `models/akt/akt_best.pt` and loaded with `weights_only=True`. The archive is itself a PyTorch checkpoint; its contents are not unpacked or executed. The app uses the inference architecture from `KT_Models_Comparison_AKT_firstnb_processing.ipynb`: Rasch embeddings, monotonic attention, question/knowledge encoders and a causal knowledge retriever. Training-only methods are omitted. Checkpoint tensors load strictly without conversion or retraining.

The model has 123 skills and 15,922 training question IDs. Every skill index and original ID matches the previous named export, so the three topic mappings remain 42/38/75. The app uses 199 past mapped interactions plus the next question, matching the training window of 200. Unmapped-only history produces no model estimate. NCERT questions use the checkpoint's verified zero-difficulty padding entry because they have no matching training IDs. This does not validate curriculum transfer or reproduce question-specific ASSISTments evaluation.

The UI labels and status/progress responses now identify AKT; model status fields use `kt`, `kt_loaded`, `kt_mappings` and `kt_status`, and model readiness rows use `akt_prediction`. The DKT exports remain preserved; SQLite learner history is unchanged.

All 21 app tests pass, including the new status/progress API check. Numerical outputs match the original notebook classes for single-step, multi-step and truncated histories, including Rasch question embeddings. Future response changes do not affect earlier predictions, and modified skill names fail the checksum gate. The checkpoint-summary test, JavaScript syntax check and real-artifact offline check also pass: all 25 topics, seven checkpoints, review continuation and three AKT readiness rows, with zero hosted-model calls. Browser visuals and live teaching were not checked.
