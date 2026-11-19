# Phase 14_scale_and_maintenance — M4 onward: expand the same pipeline and maintain releases

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: Estimate after pilot measurements hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Accepted small M3 pilot and documented missing coverage.  
Produce: Incrementally expanded, evaluated and recoverable curriculum releases.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Accepted M3 pipeline, measured throughput and documented coverage gaps.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Expand the scope manifest in controlled batches toward the agreed Classes 6–10 Mathematics/Science coverage. Estimate effort from measured extraction, review and graph/mapping throughput.
2. Reuse the M3 scripts/configuration and quality gates. Add a new parser/transform only when a documented failure justifies it.
3. Process only new/changed source hashes; invalidate downstream cleaned content, concepts/chunks, embeddings, edges and mappings that depend on changed material.
4. Review new graph candidates and mappings; monitor false links, unsupported science skills and misconception coverage. Keep prior accepted versions reproducible.
5. Rebuild indexes explicitly if the embedding model/dimension/configuration changes; never mix incompatible vectors in one searchable release.
6. Increase training data with Pandey using the established split protocol; adding textbook pages does not create genuine KT learner histories.
7. Rerun representative regression and held-out release checks according to a documented evaluation policy. Do not continually tune against the same test set.
8. Prepare separate permitted release bundles, backup/restore instructions for the dedicated content database, and a rollback rehearsal before replacing a deployed corpus.
9. Maintain an issue backlog for diagrams, OCR failures, question-answer review and curriculum updates. State real supported scope in the product and report.

## Planned code and locations

- `code/reuse earlier phase scripts` — avoid a separate full-scale implementation.
- `code/validate_release.py` — extend existing release checks only when needed.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/scale_plan.md`
- `outputs/release_history.csv`
- `outputs/coverage_matrix.csv`
- `outputs/change_impact_report.json`
- `evidence/rollback_rehearsal.md`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] New release passes the same content/graph/retrieval boundaries.
- [ ] Prior release remains reproducible and recoverable.
- [ ] Full-scale coverage claims match the actual support matrix.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Added coverage versus prior release; new errors and review cost.
- Measured scaling time/memory and updated estimates.
- Version changes, regression findings and rollback evidence.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Package Hariom's outputs and demonstrate the connected M3 tutor](../13_backend_handoff_and_m3_demo/README.md).

Maintain releases and return to the relevant upstream phase when sources/configuration change.

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

