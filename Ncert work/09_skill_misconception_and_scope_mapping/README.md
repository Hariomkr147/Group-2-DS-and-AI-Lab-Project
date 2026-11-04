# Phase 09_skill_misconception_and_scope_mapping — Map curriculum to KT skills, misconception labels and supported topics

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 3–5 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Update 2 Nov (evening)

Misconceptions come from datasets: the Eedi graph as catalogue; Eedi Kaggle and MAP for evaluation; BSCS and SciEntsBank for science. Runtime is rules → retrieval over the full catalogue → Qwen pick or ask for working. Concept mapping is optional. See [PLAN §13.4](../PLAN.md#134-misconceptions-datasets-not-hand-written-lists). Replace the synthetic `outputs/diagnostic_examples.jsonl`. Skill (KT) mapping remains deferred.


## Purpose

NCERT concept/question without a verified link to trained KT or diagnostic labels.  
Produce: Reviewed mapping tables with coverage gaps and defined fallback behavior.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Concepts/questions and reviewed prerequisite graph.
- Pandey's selected checkpoint vocabulary with original skill IDs/names.
- Optional misconception taxonomy/examples with recorded provenance and permitted use.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Obtain the vocabulary bundled with the selected KT checkpoint. Reconcile original skill IDs and checkpoint indices before any mapping; the two existing repository mappings have different index sequences.
2. Describe NCERT concepts and questions as specific assessable objectives. Propose candidate ASSISTments matches using skill descriptions/examples and text similarity, then review actual assessment compatibility.
3. Save original skill ID, checkpoint index, checkpoint/vocabulary hash, NCERT concept/question ID, exact/partial/unmapped relation, evidence and reviewer. Never assume an integer index is portable between preprocessors.
4. Allow multiple skill annotations only under the event/model policy agreed with Pandey. Do not duplicate a single response as if it were independent evidence or average arbitrary mastery scores.
5. Mark unmapped concepts and science as unsupported by a mathematics-trained KT checkpoint. Agree a clearly labelled per-concept-history/cold-start fallback with Sandeep.
6. Filter an external misconception taxonomy to supported concepts. Preserve source label IDs, source release and attribution; distinguish taxonomy descriptions from actual labelled student-answer examples.
7. With Pandey/Sandeep, prepare a bounded pilot label set: systematic error, arithmetic slip, unknown/insufficient working and correct alternative methods. Review generated examples and keep their synthetic provenance.
8. Create context-rich examples containing question, learner answer/working, concept and diagnostic label; group variants by original problem for splitting. The 161 existing team scenarios remain test-only.
9. Supply supported-topic descriptions and ambiguous/topic-switch examples for Sandeep's input guardrail. Guardrail and misconception classifier implementation remains his integration work; data/training support remains shared with Pandey.
10. Do not turn Eedi misconception↔construct weights into prerequisite edges or probabilities that an individual student has a misconception.

## Planned code and locations

- `code/propose_skill_mapping.py` — candidate mappings, not automatic approval.
- `code/validate_mappings.py` — foreign keys, vocabulary identity and review coverage.
- `code/prepare_diagnostic_examples.py` — reviewed labelled examples/exports if required.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/concept_skill_map.csv`
- `outputs/question_skill_map.csv`
- `outputs/concept_misconception_map.csv`
- `outputs/misconception_labelbook.md`
- `outputs/diagnostic_examples.jsonl`
- `outputs/supported_scope.csv`
- `outputs/mapping_coverage.json`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Every accepted skill mapping resolves against the exact selected vocabulary.
- [ ] Unmapped/partial/science cases have explicit status and fallback.
- [ ] No test scenario or paraphrase enters training/development exports.
- [ ] Catalogue entries are not misrepresented as student-response training records.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Exact/partial/unmapped coverage by concept/question/subject.
- One real candidate→reviewed skill mapping and one misconception mapping.
- Owners, data terms, example provenance and remaining domain-transfer risks.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Propose, review and publish prerequisite links](../08_prerequisite_graph/README.md).

Next numbered phase: [Embed accepted evidence and create a local retrieval database](../10_embeddings_and_database/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

