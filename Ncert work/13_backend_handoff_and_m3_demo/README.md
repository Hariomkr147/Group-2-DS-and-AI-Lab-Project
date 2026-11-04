# Phase 13_backend_handoff_and_m3_demo — Package Hariom's outputs and demonstrate the connected M3 tutor

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 3–5, shared integration time hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Separately prepared content, graph, retrieval and model components.  
Produce: Versioned handoff and an observable connected tutoring demonstration.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Accepted content/database release, retrieval interface, graph, mappings and reports.
- Sandeep's backend and Pandey's learner/response-model artifacts.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Deliver a versioned content bundle with manifest/hashes, supported scope, schema and load/rerun instructions. Keep source URLs available even where source redistribution is restricted.
2. Agree retrieval, concept lookup, approved-question lookup and prerequisite lookup input/output shapes with Sandeep. Preserve the current public search signature unless a coordinated caller update is necessary.
3. Provide explicit statuses for unknown concept, no evidence, unmapped skill, unsupported question asset and unavailable source; include minimum examples for each.
4. Use the same accepted corpus release in backend and evaluation. Verify real pilot content is loaded rather than the old four-concept sample pack.
5. Run one mathematics backtracking-and-return session and one bounded science explanation example. Include a free-form doubt and a topic-selected start.
6. Capture learner input, input label, resolved concept, assessment, learner-state origin, misconception/uncertainty, approved prerequisite path, controller action, retrieved IDs/pages, response and output-check result.
7. Also show a valid short answer, a supported topic switch, an off-topic message excluded from KT history and a no-evidence clarification. Do not force an incorrect learner-state update just to complete a demo.
8. Have Sandeep integrate the data/retrieval without taking ownership of NCERT processing. Have Pandey supply exact checkpoint vocabularies and model load instructions.
9. Run final held-out evaluation only after development choices are frozen. Coordinate the independent 161 team scenarios with the team; store sanitized traces without real student personal data.
10. Prepare M3 report-ready EDA, before/after examples, comparison plots, static pipeline diagram, remaining failures, work log and real review/sign-off fields.
11. Publish only permitted code/data/artifacts with working links. Record what is downloadable versus reproducible-from-source.
12. Treat the repository's 5 November 2026 M3 date as recorded planning guidance; the MoM itself does not state the exact deadline.

## Planned code and locations

- `code/export_content_bundle.py` — reviewed artifacts, hashes and support matrix.
- `code/smoke_handoff.py` — exercise agreed interfaces with safe local test inputs.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `exports/<release_id>/`
- `outputs/interface_contract.md`
- `outputs/handoff_checklist.md`
- `evidence/demo_trace_math.jsonl`
- `evidence/demo_trace_science.jsonl`
- `outputs/m3_evidence_index.md`
- `figures/pipeline.png`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] A learner input reaches an observable model response through the connected backend.
- [ ] Intermediate component decisions and NCERT citations are inspectable.
- [ ] Off-topic text never becomes an assessed KT event.
- [ ] Sandeep can reproduce the load/retrieval without hidden notebook state.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Actual integrated behavior, owners and artifact versions.
- Full demo trace plus limitations and failed checks.
- Links to all phase evidence, TA-action coverage and completed real review fields.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Hariom's model research and deployment feasibility evidence](../12_socratic_model_feasibility/README.md).

Next numbered phase: [M4 onward: expand the same pipeline and maintain releases](../14_scale_and_maintenance/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

