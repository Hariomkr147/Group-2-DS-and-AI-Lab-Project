# Phase 11_retrieval_and_evaluation — Compare retrieval, resolve concepts and verify citations

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 4–6 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Update 2 Nov (evening)

The cutoff decision is deferred until the full corpus exists; rerun `code/sweep_cutoffs.py` then. See [PLAN §13.5](../PLAN.md#135-deferred-until-all-extraction-is-finished).


## Purpose

Student query or concept ID without evaluated retrieval behavior.  
Produce: Ranked source-grounded evidence, calibrated development choices and held-out results.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Loaded content release and embedding index.
- Independent query/relevance annotations for supported pilot concepts.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Create development queries from pilot objectives: direct doubts, paraphrases, learner errors, cross-grade needs, ambiguous concepts and out-of-scope requests. Do not reuse the 161 held-out team scenarios for tuning.
2. Annotate relevant chunk/concept IDs with source pages. Freeze separate development/test query families before ranking/threshold tuning; keep problem paraphrases together.
3. Compare actual BM25, dense BGE similarity and hybrid ranking on the same corpus and queries. The current backend keyword-overlap stub is not a true BM25 baseline.
4. Implement concept resolution for free-form doubts with an uncertainty/clarification path. Topic-selected learning supplies a known concept; retrieval should not invent a concept ID.
5. Retrieve evidence under selected course/subject/concept and review-status constraints. Include prerequisites when the controller asks for them; avoid irrelevant nearest neighbors.
6. Keep active exercise answers/solutions out of explanatory retrieval. For HINT/EXPLAIN, use permitted source examples or definitions without leaking the current exercise answer.
7. Return chunk ID/text, concept IDs, source title/URL, PDF page/printed label, ranking score and corpus version. Validate citations point to retrieved source evidence.
8. Measure Recall@5, MRR and relevant top-k precision on supported queries; evaluate off-topic false retrieval and concept-resolution accuracy separately.
9. Measure runtime/latency on actual hardware. Tune thresholds and hybrid parameters using development queries only, then report the held-out result once.
10. Keep no-evidence/ambiguous/error states explicit. A generated citation ID check does not prove a response is semantically supported; human-review a response/evidence sample.

## Planned code and locations

- `code/retrieve.py` — candidate retrieval interface to be integrated with existing backend service.
- `code/evaluate_retrieval.py` — common query manifests, metrics and error cases.
- `code/build_retrieval_figures.py` — report-ready comparison plots.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `evaluation/queries_dev.jsonl`
- `evaluation/queries_test.jsonl`
- `evaluation/relevance_labels.csv`
- `outputs/retrieval_runs.jsonl`
- `outputs/retrieval_metrics.json`
- `outputs/concept_resolution_metrics.json`
- `figures/retrieval_comparison.png`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Every displayed reference resolves to the correct source and physical page.
- [ ] All methods use the same corpus and frozen query protocol.
- [ ] No answer key leaks in returned evidence.
- [ ] Ambiguous/no-evidence/out-of-scope inputs follow explicit paths.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Measured baseline table with query count, settings and hardware.
- Good and failed retrieval examples with relevance judgements.
- Tuning choices, held-out scores and remaining coverage gaps.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Embed accepted evidence and create a local retrieval database](../10_embeddings_and_database/README.md).

Next numbered phase: [Hariom's model research and deployment feasibility evidence](../12_socratic_model_feasibility/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

