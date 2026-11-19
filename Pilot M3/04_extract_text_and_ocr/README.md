# Phase 04_extract_text_and_ocr — Produce canonical page/block records with OCR where required

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Draft extraction executed: 191 pages, 3,980 blocks, 342 assets; cached rerun passes. Content acceptance remains pending.**
Estimated active effort: 2–4 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Update 2 Nov (evening)

Routing is decided: maths pages and all solution/answer-key pages → MinerU; science pages → PyMuPDF unless a table or formula is detected. Implementation details and the check to run: [PLAN §13.1](../PLAN.md#131-parser-routing-pymupdf-and-mineru-by-subject).


## Purpose

Original PDF plus parser-specific text/layout output.  
Produce: Canonical source-traceable page/block records; unreviewed warnings retained.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Verified source manifest, page audit and chosen parser policy.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Process the pilot using the chosen route per page/source. Use OCR when evidence requires it; do not blindly OCR clean native text.
2. Save parser-native output unchanged under native_outputs/. Then normalize its representation into a common page/block format; representation normalization must not rewrite scientific meaning.
3. Retain source_id, PDF hash, page number/printed label, block ID/order, section hint, bounding box, content_type, raw_text/markdown/latex and asset references where available.
4. Extract equations/tables as structured content when supported, retaining both readable text and source image references for difficult cases.
5. Save diagram/image assets with source coordinates. OCR can read labels but does not establish what a diagram means. Flag diagram-dependent questions as supported only after review; otherwise exclude them from the M3 demo.
6. Record parser/engine revision, route, OCR flag, extraction warnings and manual review status. Missing confidence from a tool must remain missing, not become an invented confidence score.
7. Account for every page: extracted, accepted-empty, failed or quarantined. Sparse pages must not be discarded merely because they have fewer than 200 characters.
8. Implement resumable batches by input hash and parser configuration. Preserve failed outputs/logs; retry narrowly and avoid overwriting an approved prior version.
9. Use strict JSONL validation for required fields, unique IDs, valid page bounds and UTF-8 serialization.

## Code and proposed locations

- `code/extract_content.py` — orchestrate selected routes, retries and canonical records.
- `code/validate_extraction.py` — schemas, page accounting and provenance checks.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `native_outputs/<run_id>/`
- `outputs/pages.jsonl`
- `outputs/blocks.jsonl`
- `outputs/assets_manifest.csv`
- `assets/`
- `outputs/extraction_failures.csv`
- `outputs/page_accounting.csv`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] All pages accounted for, including empty/failing pages.
- [ ] No accepted record lacks source/page/parser provenance.
- [ ] Unsupported diagrams and unresolved critical formulas are excluded or quarantined.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Native-text/OCR/parser route totals and failures.
- Examples from prose, mathematics and science pages.
- Source-page rendering beside raw extraction and canonical representation.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Compare PyMuPDF, MinerU and conditional OCR](../03_parser_benchmark/README.md).

Next numbered phase: [Clean conservatively without damaging mathematics](../05_clean_and_preprocess/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

