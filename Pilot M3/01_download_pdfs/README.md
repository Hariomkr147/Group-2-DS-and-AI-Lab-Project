# Phase 01 — Acquire and preserve original NCERT PDFs

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Completed acquisition/integrity checks: 8 PDFs, 191 physical pages; no accepted content release. See report.md.**
Estimated active effort: 1–2 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Purpose

Official URL and unverified downloaded file.  
Produce: Verified unchanged PDF plus identity, hash, provenance and access notes.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Approved pilot scope from Phase 00.
- Verified official NCERT source pages/URLs.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Locate the correct official NCERT book/edition for each selected class and subject. Verify titles manually; do not infer class/chapter only from a filename.
2. Prefer chapter PDFs if those are official available sources. Record whole-book versus chapter-PDF identity and keep their page offsets separate.
3. Download into pdfs/<subject>/class_<grade>/<edition>/<book_id>/. Keep original filenames in metadata even if local filenames are normalized.
4. Check HTTP/download success, plausible content type, PDF signature, file opening, byte size and page count. Detect HTML error pages saved with a .pdf extension.
5. Compute SHA-256 for each file; detect exact duplicate downloads without deleting the only source copy.
6. Write sources.csv: source_id, subject, grade, language, edition, book_title, chapter_title, source_url, downloaded_at, sha256, local_path, bytes, pdf_pages, rights_note.
7. Keep originals immutable. Save repaired/converted PDFs as derivatives with parent hashes. Record broken URLs and unsupported sources in a failure register.
8. Record citation/access conditions. Do not assume an official/public PDF can be redistributed as a public dataset.

## Code and proposed locations

- `code/download_pdfs.py` — acquire sources with retries and a failure register.
- `code/verify_downloads.py` — signature/openability/hash/manifest checks.

Actual implementation and runnable commands are recorded in report.md; notebook names and any unimplemented scripts remain proposals. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `pdfs/<subject>/class_<grade>/<edition>/<book_id>/*.pdf`
- `manifests/sources.csv`
- `manifests/download_failures.csv`
- `logs/download_runs.jsonl`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Every included PDF opens and has a source row and hash.
- [ ] No source URL/path conflict; duplicates are identified.
- [ ] Originals have not been overwritten or cleaned.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Expected versus successful downloads; bytes/pages by book.
- Unavailable sources, duplicates and rights/access notes.
- At least one real source PDF-to-manifest example.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Setup, pilot scope and reproducibility](../00_setup_and_scope/README.md).

Next numbered phase: [Pre-extraction audit and initial EDA](../02_pdf_audit/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

