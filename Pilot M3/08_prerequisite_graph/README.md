# Phase 08_prerequisite_graph — Propose, review and publish prerequisite links

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 4–6 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Update 2 Nov (evening)

Build the full graph only after all extraction is done; no paid API needed. See [PLAN §13.5](../PLAN.md#135-deferred-until-all-extraction-is-finished).


## Purpose

Concepts with candidate/uncertain dependency proposals.  
Produce: Reviewed directed prerequisite graph with traceable decisions and evaluation.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Reviewed concept catalogue, learning objectives and source passages.
- Optional external prerequisite research/benchmarks after checking relevance and terms.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Define the stored direction: prerequisite_id → dependent_id. Keep hierarchy, related-to and prerequisite relationships in different fields/tables.
2. Generate candidate pairs using explicit mentions, learning objectives, curriculum sequence and semantic retrieval. Include plausible cross-grade and math-for-science dependencies; earlier grade/order alone is not proof.
3. Use a pretrained instruction model offline if helpful. Supply concept A/B objectives and source snippets; request A→B, B→A, related-only, neither or uncertain, with evidence IDs and a reason.
4. Do not require the trained Socratic adapter for graph generation. Record the graph-judge model/revision/prompt separately; no model training is required for the first baseline.
5. Validate returned IDs and quoted evidence against inputs. Model confidence is not a calibrated probability; use it to prioritize review, not automatically trust edges.
6. Review the M3 pilot links and a sample of rejected/negative candidates. Save reviewer, decision, reason, date and evidence. Review proposals rather than author every possible edge manually.
7. Check self-links, duplicate/inverse conflicts and cycles. Flag suspicious direction/grade jumps without rejecting every legitimate cross-subject dependency.
8. Build a small independently labelled graph evaluation set containing positives, negatives, reversed directions and merely related concepts. Separate it from tuning examples; report precision/recall with the candidate-generation scope.
9. Store approved edges and simple traversal results in files/PostgreSQL. Test depth-limited prerequisite lookup on a reviewed cross-grade chain; do not add Neo4j/full GraphRAG for this pilot.
10. Keep external dataset direction conventions explicit when adapting examples. External graphs are evidence/benchmarks, not automatically valid NCERT edges.

## Planned code and locations

- `code/propose_prerequisites.py` — curriculum/content candidates and optional LLM judgments.
- `code/validate_graph.py` — identity/direction/cycle checks.
- `code/evaluate_prerequisites.py` — independently reviewed pair evaluation.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/candidate_edges.jsonl`
- `outputs/edge_reviews.csv`
- `outputs/approved_edges.csv`
- `outputs/graph_gold_dev.csv`
- `outputs/graph_gold_test.csv`
- `outputs/graph_metrics.json`
- `figures/pilot_prerequisites.svg`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] All active M3 edges are reviewed and source-justified.
- [ ] Active graph has no cycles or self-links.
- [ ] At least one meaningful cross-grade backtracking chain is demonstrable.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Candidate→reviewed→accepted/rejected counts and review effort.
- Real before/after edge proposal with evidence and corrected direction if applicable.
- Graph precision/recall, evaluation sample and unsupported areas.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Build source-grounded concepts, practice questions and evidence chunks](../07_concepts_questions_and_chunks/README.md).

Next numbered phase: [Map curriculum to KT skills, misconception labels and supported topics](../09_skill_misconception_and_scope_mapping/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

