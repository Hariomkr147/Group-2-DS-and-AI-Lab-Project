> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- pilot-hardening-2026-11-04 -->
## Current repair result — 4 November 2026

Current release ncert-pilot-2ecfcf34cd6278d0 contains 22 NCERT vectors (384 dimensions) in the dedicated local PostgreSQL database. All 22 were recomputed and all 8,117 Eedi vector rows were checked against local files/database, with 20 recomputed. Current question-bank view exposes only approved scoring-eligible source/key pairs (20). Older immutable corpus versions remain stored; select the current corpus version when inspecting content.

See [Pilot repairs and decision](../PILOT_HARDENING.md) for evidence, measured limits and remaining gates. Earlier entries below are historical and superseded where they conflict.

---

<!-- automatic-validation-2026-11-03 -->
## Automatic validation — 3 November 2026

Automated embedding audit run `20261103T165459-9e42c7d8` passed all 12 current NCERT and 8,117 Eedi vectors: source/model/vector hashes, IDs, row order, finite dimensions/norms, and all database text/vector values agree. Recomputed all 12 NCERT embeddings and 20 deterministic Eedi samples; values agree. No embedding-by-embedding human inspection is required. These are technical integrity checks, not proof of retrieval relevance or transcription accuracy.

---

<!-- model-human-db-handoff-2026-11-03 -->
## Model, review and database handoff — 3 November 2026

Started and verified the existing owned PostgreSQL cluster on 3 November (run 20261103T115225-66964b6c). Read-only queries confirm ncert_pilot on 127.0.0.1:54329, 119 source questions, 14 worked examples, 86 private answers, 8,117 Eedi misconceptions and 2,258 constructs. The chunks table retains three historical releases / 36 total rows; current ncert-pilot-fd981363bc7f493a has 12 rows. Added and executed inspect_database.sql with a read-only transaction and a current-release filter. pgAdmin 4 is installed. No content rows or credentials were changed by inspection; connection instructions and text/vector paths are in REVIEW_AND_MODEL_HANDOFF.md.

---

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Current release has 12 verified 384-dimensional BGE vectors, six concepts, nine sources and three graph edges. Dedicated loopback PostgreSQL / pgvector load passed idempotence, foreign-key rollback, frozen-release and learner-export private-field checks. Separate source-bank tables contain 119 questions, 14 worked examples and 86 private answers; no questions are approved for scoring. Runs `20261102T190912-515a0b9f`, `20261102T190947-683331c3`, `20261102T190948-b3f7223e`.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 10_embeddings_and_database report — Embed accepted evidence and create a local retrieval database

Prepared: 2 November 2026  
Owner: Hariom Kumar  
Status: **Planned / Not run**  
Related instructions: [README.md](README.md)  
Accepted output release: **None**

## 1. Actual work performed

No processing work for this phase has run in this new folder. Replace this statement only after execution. The README is the intended procedure, not evidence of completion.

## 2. Run and input identity

| Field | Actual value |
| --- | --- |
| Run ID and actual date/time | Not run |
| Responsible person / reviewer | Not recorded |
| Code revision / uncommitted diff | Not recorded |
| Input artifact paths, versions and hashes | Not recorded |
| Configuration / seed / parser-model revision | Not recorded |
| Command or notebook path | Not executed |
| Hardware / OS / Python / dependencies | Not recorded for a run |
| Start / finish / duration | Not measured |
| Output paths and hashes | None |

## 3. Procedure actually executed

List the steps actually executed, their order, exact settings and any departures from the plan. Explain why. Do not copy the entire intended checklist as if it happened.

## 4. Counts, checks and outcomes

| Item | Input/before | Output/after | Rejected/failed/quarantined | Evidence |
| --- | --- | --- | --- | --- |
| Main phase records | Not measured | Not measured | Not measured | Pending |
| Source/page/concept coverage as applicable | Not measured | Not measured | Not measured | Pending |
| Relevant quality metric | Not measured | Not measured | Not measured | Pending |
| Runtime / memory | Not measured | Not measured | Not measured | Pending |

Use the units appropriate to this phase. Explain denominators, sample sizes and missing values. Do not substitute historical repository counts for this run.

## 5. Before/after or representation-change evidence

No actual transformations are available yet.

| Example | Source/page/block or input artifact | Before: exact actual representation | After: exact actual representation | Rule/decision, reason, source review and evidence |
| --- | --- | --- | --- | --- |
| 1 | Pending | Pending | Pending | Pending |
| 2 | Pending | Pending | Pending | Pending |
| 3 | Pending | Pending | Pending | Pending |
| 4 | Pending | Pending | Pending | Pending |

**What this phase should eventually demonstrate:**  
Before: Accepted textual evidence and reviewed curriculum records.  
After: Versioned embeddings and validated local content database.

Those two descriptions specify expected evidence; they are not an actual before/after result. Include at least one unchanged or rejected/uncertain case where appropriate. For embeddings, show vector shape/model/record correspondence rather than dumping the full vector.

## 6. Phase-specific findings to fill

- [ ] Embedding settings, hardware, time, memory and counts.
- [ ] One chunk→vector shape→stored record example; do not print hundreds of vector values.
- [ ] Database version/schema, count reconciliation, repeat-load/rollback evidence.

Link figures and selected evidence using relative paths. Report only plots generated from the identified release, with captions describing denominators and limitations.

## 7. Validation and acceptance

- [ ] Vector dimensions/counts match the selected model and accepted chunks.
- [ ] Query/document embeddings use a compatible recorded configuration.
- [ ] Repeat load is idempotent; invalid load cannot partially replace content.
- [ ] Gold answers never appear in learner-safe search exports.
- [ ] Run/output manifests and hashes are complete.
- [ ] Required source/review/privacy boundaries pass.
- [ ] A meaningful rerun/boundary check was completed where applicable.

Check result details: **Not run**.  
Accepted/rejected release decision and reviewer: **Pending**.

## 8. Failures, limitations and decisions

| Issue / alternative considered | Actual evidence | Decision / reason | Owner / next step |
| --- | --- | --- | --- |
| Pending execution | None | No completion claim | Hariom Kumar |

Preserve failed attempts and explain exclusions. Self-reported model confidence, heuristics and synthetic examples must be labelled correctly.

## 9. Handoff and reproducibility

- Accepted artifacts and exact release: None.
- Next-phase input paths: Pending.
- Actual rerun instructions: Not available until code is implemented.
- Shared-team dependency and response: Pending if applicable.
- Public/permitted evidence links: Pending.
- Reviewer / actual review date / sign-off: Pending.

Update the [root report](../report.md) after acceptance. Do not fill signatures or success values in advance.

