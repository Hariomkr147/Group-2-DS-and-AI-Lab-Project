> **Current workflow:** automatic source/integrity checks and the remote-model-only mock app. Human-review generation and local response-model benchmarks are [archived](../_archive/README.md). The phase plan below is historical where it conflicts; use the [current checkpoint](../CURRENT_CHECKPOINT.md).

# Phase 06_eda_and_quality — Post-extraction EDA, quality evaluation and freeze

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Draft EDA/release gates executed and counts reconcile; accepted records remain zero pending source reviews/parser acceptance.**
Estimated active effort: 2–3 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Raw/cleaned records whose aggregate quality is not yet established.  
Produce: Audited accepted release with reconciled counts, figures and known exclusions.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Raw and cleaned records, source/page manifests and transformation logs.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Generate raw→extracted→cleaned→accepted/quarantined count tables by book, subject, grade, edition and content type.
2. Analyze missing fields, blank pages, duplicate artifacts, Unicode/replacement glyphs, block/page length distributions, formula/table/question coverage and OCR-route distributions.
3. Compare raw versus cleaned lengths and critical notation around reviewed examples. Symbol counts detect changes; they do not prove equation correctness.
4. Review a stratified sample including every flagged critical page and difficult mathematics/science content. Keep reference annotations separate from parser/cleaning decisions.
5. Distinguish the benchmark/development pages used to select extraction settings from an untouched extraction quality sample used for final reporting.
6. Record failure/exclusion reasons, manual effort, reviewed sample size and measurable quality findings. Report uncertainty and sample limits rather than unsupported whole-corpus accuracy.
7. Generate reproducible charts and a machine-readable statistics file from the same accepted release used downstream.
8. Freeze an accepted cleaned release manifest with hashes. Unresolved critical errors go back to extraction/cleaning; no silent edits to a frozen release.

## Code and proposed locations

- `code/eda_content.ipynb` — charts and analysis from exported records.
- `code/build_quality_report.py` — stage counts, checks and release manifest.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/eda_summary.json`
- `outputs/stage_counts.csv`
- `outputs/quality_annotations.csv`
- `outputs/clean_release_manifest.json`
- `figures/`
- `evidence/reviewed_examples.jsonl`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Stage counts reconcile and every exclusion has a reason.
- [ ] Release data and reported statistics have the same hashes/version.
- [ ] No critical unreviewed formula is in the supported demo content.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- EDA conclusions that changed preprocessing or scope.
- Before/after distributions and 3–4 evidence examples.
- Measured quality on the untouched sample; review coverage and limitations.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Clean conservatively without damaging mathematics](../05_clean_and_preprocess/README.md).

Next numbered phase: [Build source-grounded concepts, practice questions and evidence chunks](../07_concepts_questions_and_chunks/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

