# Current checkpoint

Generated from current manifests by `00_setup_and_scope/code/update_checkpoint.py`. This is the current status entry point; dated reports describe snapshots.

- Release: `ncert-pilot-a2ac2147befaf6e1` (build `20261104T182837-db44cee3`).
- Content: **124 passages / 25 topics**. Figures, private keys and excluded source blocks remain outside evidence.
- Question bank: 85 questions; 84 approved, 1 held back; **43 rubric-eligible question–key pairs**. The mock uses seven selected scalar checkpoints.
- Vector integrity: **passed**. This does not establish retrieval relevance or transcription accuracy.
- Offline app check: **passed without response-model calls**.
- Automatic topic routing: **disabled; select a topic**. The existing retrieval labels cover the six original objectives, not all current section topics.
- Misconceptions: six calculation-corroborated, unconfirmed rule families; no runtime Eedi vector search or remote ID selector. General diagnosis remains experimental.
- Teaching model: the user's remote fine-tuned model only. Live model testing remains deferred by the user; no local generative model is started.
- DKT: Hariom Kumar supplied trained DKT checkpoint (5 November 2026) (123 skills). Named NCERT mappings remain an unvalidated curriculum bridge; see [mock-app verification](../mock-app/VERIFICATION.md).

[Detailed release report](PILOT_REPORT.md) · [Release manifest](07_concepts_questions_and_chunks/outputs/content_manifest.json) · [Item decisions](07_concepts_questions_and_chunks/outputs/item_review_summary.json) · [Offline app checks](../mock-app/logs/offline_hardening_checks.json) · [Retired workflows](_archive/README.md)

Broader deployment still needs fresh retrieval labels/learner-query evaluation, validated misconception diagnosis, wider curriculum coverage and the later hosted-model teaching test. No human inspection of individual embeddings is required.
