# Phase 05_clean_and_preprocess — Clean conservatively without damaging mathematics

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Draft cleaning executed: 1,537 logged changes, 228 candidate removals, 705 quarantined blocks; source/semantic review pending.**
Estimated active effort: 3–5 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Extracted blocks containing verified noise or layout artifacts.  
Produce: Cleaned blocks with mathematical meaning preserved and a reversible audit trail.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Canonical blocks/pages and unchanged parser output.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Create cleaned derivatives; retain raw_text and a stable link to the raw block. Keep cleaning separate from extraction.
2. Normalize safe whitespace/control characters; preserve paragraphs, equations, question numbering and tabular boundaries where meaningful.
3. Identify repeated running headers/footers using position and repetition across pages. Quarantine numeric/equation-only lines before removal; a bare number may be an answer, label or scientific value.
4. Repair line-wrap hyphenation only when the token/context supports it. Do not join subtraction expressions, negative numbers, units or chemical names automatically.
5. Preserve /, −, -, ×, ÷, =, <, >, %, decimal points, brackets, exponents, subscripts and units. Avoid blanket ASCII conversion and punctuation removal.
6. Deduplicate repeated extraction artifacts using provenance and normalized hashes while retaining all legitimate source references. Repeated definitions across chapters are not automatically noise.
7. Define a rule register with rule ID, rationale, implementation location, affected fields, known limits and reversibility/provenance.
8. Log every changed/removed block with before, after, rule IDs, source page, reason and review state. Manual fixes require the same audit trail.
9. Build small meaningful checks around failure-prone transformations: fractions, subtraction/newline ambiguity, decimals/units and header removal. Do not invent missing symbols from context without review.
10. Use a quarantine queue for ambiguous text instead of passing corrupted equations into embeddings.

## Code and proposed locations

- `code/clean_content.py` — explicit reviewed transforms and change log.
- `code/test_cleaning.py` — small regression cases for harmful-transform risks.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/clean_blocks.jsonl`
- `outputs/clean_pages.jsonl`
- `outputs/transform_log.jsonl`
- `outputs/quarantine.csv`
- `outputs/cleaning_rules.csv`
- `evidence/before_after.jsonl`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Raw records are recoverable and all changes traceable.
- [ ] Representative critical notation matches the source rendering.
- [ ] Quarantined content cannot silently enter accepted chunks.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Counts per cleaning rule and retained/excluded/quarantined blocks.
- At least 3–4 REAL before/after examples with source screenshots and safety rationale.
- Remaining quality problems and why each exclusion is necessary.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Produce canonical page/block records with OCR where required](../04_extract_text_and_ocr/README.md).

Next numbered phase: [Post-extraction EDA, quality evaluation and freeze](../06_eda_and_quality/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

