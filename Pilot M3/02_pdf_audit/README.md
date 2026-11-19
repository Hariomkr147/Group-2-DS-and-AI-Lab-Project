# Phase 02_pdf_audit — Pre-extraction audit and initial EDA

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **In progress — all 191 pages audited; 15 benchmark candidates rendered; independent review pending. See report.md.**
Estimated active effort: 1–2 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

PDFs whose extraction characteristics are unknown.  
Produce: Page inventory, benchmark selection and tentative extraction routes.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Verified original PDFs and sources.csv.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Inventory books, chapters, grades, subjects, editions, file sizes and pages. Show missing expected sources; do not silently ignore unavailable files.
2. Inspect PDF metadata, bookmarks/table of contents where present, native text availability, image presence and extraction errors. Use a lightweight PyMuPDF text probe as an audit, not final cleaned extraction.
3. Assign provisional page routes: native-text candidate, layout/formula-heavy, scan/image-heavy, mixed, or manual-review. A single character-count threshold is insufficient.
4. Select a stratified parser benchmark: prose, fractions/operators, superscripts/subscripts, tables, multicolumn reading order, diagrams, exercises and a scanned/mixed page if available.
5. Record PDF physical page number as 1-based and printed textbook page label separately, including unnumbered pages and chapter-PDF offsets.
6. Render only the selected audit pages for visual comparison. Inspect originals without changing their text or compressing the source PDF.
7. Quarantine corrupt/encrypted/unreadable sources with a reason and recovery plan. Reacquire first where possible rather than patch silently.
8. Produce plots of coverage, page characteristics and source sizes; clearly label heuristic flags rather than treating them as ground truth.

## Code and proposed locations

- `code/audit_pdfs.py` — page metadata, text probes and candidate routes.
- `code/eda_pdf_inventory.ipynb` — reproducible exploratory charts from audit outputs.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/pdf_inventory.csv`
- `outputs/page_audit.csv`
- `outputs/parser_benchmark_pages.csv`
- `evidence/selected_page_renders/`
- `figures/pdf_coverage.png`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Every physical page has an audit disposition or logged failure.
- [ ] Benchmark covers difficult content types.
- [ ] No mathematical content was removed before extraction.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Pre-extraction coverage and missingness plots.
- Page-route counts and known heuristic limitations.
- Why each benchmark page was selected.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Acquire and preserve original NCERT PDFs](../01_download_pdfs/README.md).

Next numbered phase: [Compare PyMuPDF, MinerU and conditional OCR](../03_parser_benchmark/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

