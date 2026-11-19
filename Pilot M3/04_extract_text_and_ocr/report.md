> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Final canonical rerun: 203 pages, 3,090 blocks, 396 assets; 115 MinerU pages, 10 native science pages and 78 native excluded pages. All 34 solution pages use MinerU. Eleven newly parsed solution pages and 104 verified cached MinerU pages; no extraction failures. Run `20261102T184500-bd4ecd59`. All original raw outputs and source lineage are retained.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 04 execution report

Date: 2 November 2026. Owner: Hariom Kumar; execution assisted by Codex.
Status: **Draft extraction executed and validated; content review/release pending.**
Accepted content release: **None**.

Implemented `code/extract_content.py`, `code/validate_extraction.py` and four boundary
checks. The working [route policy](../03_parser_benchmark/outputs/working_parser_policy.json)
chooses parsers for local preparation; it does not approve a content release or
replace the still-pending accepted parser policy.

## Actual counts and routes

- **191/191 physical pages**, **3,980 canonical blocks**, **342 extracted assets**.
- **91** chapter-content pages through MinerU Basic ONNX CPU: 36 Grade 6 maths,
  26 Grade 7 maths, 13 Grade 8 maths and 16 Grade 7 science.
- **100** native PyMuPDF pages retained with exclusions/privacy: 72 prelims,
  23 private solutions, two visual activity sheets, two notes pages and one
  out-of-scope enrichment page. No source page was dropped or inferred empty.
- Native capture covers all 191 pages, with zero page errors. Final extraction
  failures: **0**. Full page/block/asset lineage validation passes.
- The first full run reused 12 relevant benchmark pages and parsed 79 new pages
  in 11 source/page batches of at most eight. The other benchmark-only pages
  remain preserved, while their canonical routes follow their exclusions.

Source dispositions now cover every physical page in
[source_page_dispositions.csv](../02_pdf_audit/outputs/source_page_dispositions.csv).
The full appended solution ranges are Grade 6 p37–50 and Grade 7 p31–39. They
produce 1,564 answer-typed blocks, all private. Page headings referring to exercise
print pages are not mistaken for physical or printed labels of the answer appendix.

Current canonical files: local ignored `outputs/pages.jsonl`, `outputs/blocks.jsonl`;
[page_accounting.csv](outputs/page_accounting.csv),
[assets_manifest.csv](outputs/assets_manifest.csv),
[extraction_failures.csv](outputs/extraction_failures.csv).
Assets retain source/PDF hashes, physical pages, parent block coordinates, native
references and meaning-review status. Nested tight asset coordinates remain in
unchanged native JSON; the CSV explicitly labels its parent-block bounds.

## Representation, identity and safeguards

Parser-native JSONL/ZIP bytes are retained under `native_outputs/`. Canonical
normalization preserves text, inline/standalone LaTeX, table HTML, block order,
coordinates, original parser type and image references. Classifications are
proposals; no diagram interpretation or calibrated confidence is invented.
Printed labels remain null rather than trusting parser page-number predictions.

Cache receipts bind source SHA-256, exact page IDs, parser version/tier/engine,
OCR mode, model-file manifest hash and output checksum. Source/model/cache changes
are rejected; a failed batch can be retried without repeating completed batches.
Benchmark cache imports check their original run's archive hash. Source PDFs are
reopened/hashed; originals are never overwritten. Asset paths reject ZIP traversal.

IDs bind source/page, raw-output hash and adapter revision. A provenance fix
intentionally changed the adapter revision and regenerated dependent records;
no previous vectors/accepted release existed to be reused incorrectly.
A pre-fix cached rerun produced identical block records/IDs. The final provenance
correction preserved text/LaTeX/HTML, privacy and all cleaned content hashes.
Evidence: [rerun_check.json](outputs/rerun_check.json).

## OCR evidence granularity

Native pages have `ocr_used=false`. MinerU does not expose a per-page invocation
boolean here, so its **91 page flags are null**, with batch OCR observations,
resolved parser mode and observation scope retained separately. Current modes are
89 `txt`, two `ocr` and 100 native pages. These mode counts depend on actual batch
selection; `txt` does not mean no internal OCR. Earlier draft booleans based on
batch logs were superseded by this explicit unknown state before handoff.

## Runs and checks

First full extraction: `20261102T133039-0815d815`, 13:30:39–13:51:12 UTC,
approximately 20 min 33 s including model inference/normalization/asset writes.
A fully cached rerun `20261102T135527-faeb81a0` took approximately 2.89 s and reused
all 91 MinerU pages without inference. Final normalization: `20261102T135840-a31751d0`,
again zero new inference pages, 191 pages / 3,980 blocks / 342 assets.
First-run output snapshots remain in local `logs/<run_id>/artifacts/`; run-specific
canonical snapshots are also retained in `outputs/<run_id>/`.

Four checks passed: real MinerU math/table/asset normalization and stable IDs;
sparse native/fallback/private-answer handling; ZIP path escape rejection;
and omitted-page/open-answer/tampered-native rejection. Unknown per-page OCR is
checked against the real archive. Full dataset validation reconciles every page,
unique block IDs/orders, physical bounds, raw hashes, asset references and privacy.
All text-bearing outputs remain local and ignored by Git.

Reproduce after Phases 00–03:

```powershell
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\04_extract_text_and_ocr\code\test_extraction.py'
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\04_extract_text_and_ocr\code\extract_content.py'
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\04_extract_text_and_ocr\code\validate_extraction.py'
```

Canonical JSONL validation does not prove formula correctness, reading order,
question support or source reuse permission. Native fallback for an unavailable
chapter route stays quarantined. Independent quality/content reviews remain pending.
