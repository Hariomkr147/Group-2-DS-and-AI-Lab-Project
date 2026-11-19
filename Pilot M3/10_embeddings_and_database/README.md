# Phase 10_embeddings_and_database — Embed accepted evidence and create a local retrieval database

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 3–5 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Accepted textual evidence and reviewed curriculum records.  
Produce: Versioned embeddings and validated local content database.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Accepted chunks/concepts/questions, approved edges and mapping versions.
- Chosen embedding model/revision and database connection configuration.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Create an embedding release manifest linking corpus, chunk configuration, tokenizer/model revision and source hashes. Retain the text; vectors do not replace source content.
2. Start with BAAI/bge-small-en-v1.5 as a candidate: English, 384 dimensions and a 512-token model sequence limit. Count the complete encoded input, including any metadata/special tokens.
3. Encode accepted evidence in CPU batches; measure throughput/RAM and adjust batch size. Use the model's documented query formatting and normalization consistently.
4. Validate vector count, dimension, finite values, nonzero norms and chunk-ID correspondence. Re-embed changed text; changing model/revision/normalization requires an explicitly compatible rebuilt index.
5. Create a dedicated local development database/schema with PostgreSQL and pgvector if available. Confirm Windows extension availability; exact local vector search is an acceptable small-pilot fallback if extension setup blocks progress, labelled in results.
6. Plan tables for sources, concepts, chunks, chunk_concepts, questions, private answers, prerequisite_edges, curriculum mappings and corpus releases. Agree names/types with Sandeep before writing a migration.
7. Load approved records transactionally; validate foreign keys and unique keys. Scope replacement to the intended corpus/source version, never unrelated learner/session tables.
8. Store private answer material separately from learner-facing exports and retrieval responses. Keep credentials outside committed files and sanitized reports.
9. Save a machine-readable export manifest and reproducible schema/load instructions. A .dump file is an optional backup artifact, not the primary source of the pipeline.
10. Verify rerunning the same release does not duplicate records and a failed load rolls back. No restore/import should target a shared database without an explicit agreed destination.

## Planned code and locations

- `code/embed_chunks.py` — batched encoding and embedding manifest.
- `code/schema.sql` — agreed content tables/indexes, not a replacement for application migrations.
- `code/load_database.py` — validated transactional content ingestion.
- `code/verify_database.py` — counts, IDs, version and privacy checks.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/embedding_manifest.json`
- `outputs/chunk_ids.jsonl`
- `vectors/<release_id>/`
- `outputs/database_counts.json`
- `exports/<release_id>/`
- `evidence/load_checks.json`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Vector dimensions/counts match the selected model and accepted chunks.
- [ ] Query/document embeddings use a compatible recorded configuration.
- [ ] Repeat load is idempotent; invalid load cannot partially replace content.
- [ ] Gold answers never appear in learner-safe search exports.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Embedding settings, hardware, time, memory and counts.
- One chunk→vector shape→stored record example; do not print hundreds of vector values.
- Database version/schema, count reconciliation, repeat-load/rollback evidence.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Map curriculum to KT skills, misconception labels and supported topics](../09_skill_misconception_and_scope_mapping/README.md).

Next numbered phase: [Compare retrieval, resolve concepts and verify citations](../11_retrieval_and_evaluation/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

