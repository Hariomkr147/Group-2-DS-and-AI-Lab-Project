# Phase 03_parser_benchmark — Compare PyMuPDF, MinerU and conditional OCR

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **In progress — PyMuPDF/MinerU ran on 15 identical physical pages; human reference/quality review pending. See report.md.**
Estimated active effort: 3–5 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

A source page and competing unverified text representations.  
Produce: Measured parser comparison and a documented routing policy.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Stratified benchmark page IDs and unchanged source PDFs.
- A small visually transcribed reference set with source coordinates.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Run PyMuPDF native text extraction as the inexpensive baseline on the selected pages. Preserve page/block locations and raw output.
2. Run a locally compatible MinerU configuration on the same pages. Record exact release, engine, settings, model revisions and whether OCR/formula recognition occurred.
3. Treat MinerU as a parser that may include OCR internally. 'No separate OCR tool' does not mean 'no OCR'. Do not cascade two full OCR systems over every page without evidence.
4. For truly scanned prose, optionally test PyMuPDF's Tesseract OCR path if the baseline cannot read it. For mathematical layout/formulas, judge the math-aware parser on the actual output.
5. Score critical symbol fidelity, fractions/powers, units, equation grouping, reading order, table/question boundaries, missing content and hallucinated content. Assess diagram handling separately.
6. Measure elapsed time/page, failure count and RAM/VRAM under the same hardware conditions. CPU and GPU measurements must be labelled separately.
7. Use character/word error rates only on a human-checked transcription subset; score formula semantics and layout separately. Do not call a token-presence check a complete accuracy measurement.
8. Select a default route plus fallback rules from observed results. Keep ambiguous/failed pages quarantined; write a decision record with rejected alternatives.
9. Pin the chosen parser version/config. If package APIs differ from older examples, follow the installed release documentation rather than assuming old CLI commands work.

## Code and proposed locations

- `code/benchmark_parsers.py` — execute the fixed page set and save raw outputs.
- `code/score_extraction.py` — compare transcriptions and reviewed quality rubric.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/parser_comparison.csv`
- `outputs/selected_parser_policy.json`
- `evidence/reference_transcriptions.jsonl`
- `evidence/parser_outputs/`
- `figures/quality_vs_runtime.png`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Both parsers used identical page IDs.
- [ ] Critical formulas are compared visually against originals.
- [ ] Chosen route, limitations and fallback triggers are documented.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Actual comparison table, hardware and settings.
- At least 3–4 page snippets: original, each parser output and judged result.
- Selection rationale; unresolved diagram/formula limitations.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Pre-extraction audit and initial EDA](../02_pdf_audit/README.md).

Next numbered phase: [Produce canonical page/block records with OCR where required](../04_extract_text_and_ocr/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

