> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Shared subject/role routing is active. A full 22-page Grade 9 science chapter check routed 18 pages to MinerU and missed zero MinerU-reference formula/table pages. Run `20261102T182410-6c2b9eda`. This structural reference does not establish semantic accuracy. Four reference snippets were checked by Codex under user delegation; no independent human transcription or held-out accuracy is claimed.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 03 execution report

Date: 2 November 2026. Owner: Hariom Kumar; execution assisted by Codex.
Status: **In progress — both parser runs completed; human reference/quality review pending.**
Accepted parser policy/content release: **None**.

Implemented `code/benchmark_parsers.py` and two offline checks rejecting invalid,
duplicate, omitted or renumbered benchmark pages. Checks passed **2/2**. The runner
verified original source hashes, extracted the fixed page set natively, then ran
local MinerU on the exact same unchanged PDFs with explicit physical page ranges.
Returned MinerU page indices reconcile **15/15** against the native baseline.
No derived PDF/page renumbering was used. Parser failures: **0/8 source/parser
batches** (four sources × two parsers).

Run: `20261102T130357-d1ef3c6f`, 2026-11-02 13:03:57–13:12:30 UTC
(18:33:57–18:42:30 IST). Full local run log:
`logs/run_manifest.jsonl`; commands, input/code/config/output hashes:
[root execution summary](../execution_summary.json). Config changed later only to
record the user's decision to defer mapping; the run retains its start-time hash.

## Measured time, with scope limits

[parser_comparison.csv](outputs/parser_comparison.csv) retains unrounded values,
page lists, source hashes, output references, engine and review status.

| Source batch | Physical pages | PyMuPDF seconds | MinerU seconds |
| --- | --- | ---: | ---: |
| Grade 6 fractions | 1, 5, 8, 15, 29 | 0.029 | 142.785 |
| Grade 7 fraction operations | 1, 26, 29, 37 | 0.034 | 90.377 |
| Grade 8 comparing quantities | 1, 10, 14 | 0.020 | 61.007 |
| Grade 7 heat transfer | 1, 7, 8 | 0.074 | 21.996 |

PyMuPDF timing includes source open, selected native page extraction and JSONL
write in an already-running Python process. MinerU timing includes a separate CLI
startup per source, local inference and ZIP export, with model downloads cached.
The first process also initializes model sessions/derived runtime resources. These
columns describe actual task costs; they are not an isolated inference-speed or
quality-equivalent benchmark. The whole run includes about 191 s of initial model
file downloads. Complete peak RAM/VRAM was **not measured**; no memory-fit guarantee
is inferred from successful execution. No GPU comparison or repeated-run variance.

## Exact local runtime and model identity

- Baseline: PyMuPDF **1.25.1**, native CPU, no OCR.
- Candidate: MinerU **4.1.3**, Basic tier, ONNX CPU, `--ocr-mode auto`.
- Python 3.13.15 on the inventoried Windows/i7-1260P/16 GB machine.
- Created a separate `.mineru-venv`; installed 119 packages without changing the
  Phase 00–02 environment. Exact installed versions: [mineru_requirements.txt](outputs/mineru_requirements.txt).
- Model: `opendatalab/MinerU-4_models_onnx`, downloaded revision
  `358310b4f64b95f9fefc372ad899356e4111f376`, verified by MinerU's model verifier.
  Per-file hashes: [mineru_model_files.json](outputs/mineru_model_files.json);
  actual download metadata revisions: [model_provenance.json](outputs/model_provenance.json).
- All parsing is local; no remote parse/VLM service, API key or student data used.
  No Standard/Advanced VLM or separate Tesseract run was added.

Native result metadata resolves `auto` to `txt` for Grades 6/7 maths and science,
and `ocr` for the legacy Grade 8 PDF. **All four MinerU logs show internal OCR
recognition/detection**, including the `txt` routes. Therefore `txt` must not be
reported as no OCR. [parser_runtime_observations.json](outputs/parser_runtime_observations.json)
records actual routes, producer versions, page IDs, archive hashes and OCR-log
observations. No replacement characters occur in the exported Markdown; this is
an encoding diagnostic, not a formula accuracy score.

## Source comparisons and review boundary

The [review packet](evidence/review_packet.md) contains four source-linked proposed
reference transcriptions and real baseline/candidate observations: a unit fraction,
fraction division, an exponent/compound-amount equation and a radiation statement.
Codex visually inspected all 15 selected source renders; no independent human
review is claimed. Local reference JSONL includes source hashes, physical/visible
print pages and full-page PDF coordinate bounds.

MinerU reconstructs structured fraction/exponent candidates where native text
flattens layouts, but a Grade 6 opener also yields a spurious header and a chapter
number classified as a page number. Its fraction-wall table and diagram content
remain unverified. A recognized expression is not automatically correct. The
Grade 7 answer-key sample remains private; no answer content is quoted publicly.

The [parser policy](outputs/selected_parser_policy.json) is explicitly pending,
with no accepted default. No CER/WER/formula accuracy, calibrated confidence or
parser winner is reported. Human reference/semantic review, a complete memory
measurement and a policy decision remain before the Phase 04 acceptance gate.
There is no scanned-page example in this sample; its absence is recorded.

## Reproduce

From repository root in PowerShell, after the Phase 00–02 inputs exist:

```powershell
uv venv --python 3.13 'Ncert work\.mineru-venv'
uv pip install --python 'Ncert work\.mineru-venv\Scripts\python.exe' -r 'Ncert work\03_parser_benchmark\outputs\mineru_requirements.txt'
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\03_parser_benchmark\code\test_benchmark.py'
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\03_parser_benchmark\code\benchmark_parsers.py'
```

The runner uses local `.mineru-state`, explicitly requests CPU, downloads/verifies
Basic models, creates new run-specific raw output paths and retains logs. A
fully offline exact-weight rerun requires preserving the verified model files;
the downloader contacts the current Hub repository when fetching missing files,
so compare its resulting hashes/revision before treating a future run as identical.
Historical output hashes are retained in run logs when the comparison CSV changes.

Current official references checked: [MinerU runtime tiers](https://opendatalab.github.io/MinerU/usage/tiers/),
[CLI/page selection](https://opendatalab.github.io/MinerU/usage/cli_tools/),
[ONNX model card](https://huggingface.co/opendatalab/MinerU-4_models_onnx),
[project licence](https://github.com/opendatalab/MinerU/blob/master/LICENSE.md).
Model-specific original licences/attribution remain applicable; no public software
or source-content release permission is implied by this local experiment.

## Supplemental measured process memory

A bounded single-page CPU run, `20261102T135157-1b32f32f`, parsed Grade 8 physical
p10 and verified the returned physical page ID. Windows reported a **1,933,508,608
byte** peak working set for the main process through parse/export (about 1.80 GiB).
The baseline lifetime peak before importing/running MinerU was 28,319,744 bytes.
[parser_process_memory.json](outputs/parser_process_memory.json) records scope and
actual producer version. Descendant/render-worker memory, VRAM and whole-corpus
peak remain unmeasured; this is not a total system-memory or arbitrary-batch fit
claim. Cleaning/EDA postprocessing was active concurrently; this run was used for
the scoped memory counter, not an isolated latency comparison.

The standard-library Windows counter checks positive working-set/peak ordering;
the parser case asserts exact returned page 10 before claiming inference success.
No new dependency or GPU runtime was added. Reproduce with:

```powershell
& 'Ncert work\.mineru-venv\Scripts\python.exe' 'Ncert work\03_parser_benchmark\code\measure_parser_memory.py'
```

## Hybrid routing test: PyMuPDF on every page, MinerU only where needed (2 Nov, evening)

Script: [code/hybrid_route_test.py](code/hybrid_route_test.py); outputs in `outputs/hybrid/`
([summary.json](outputs/hybrid/summary.json), [page_routes.csv](outputs/hybrid/page_routes.csv),
[router_grid.csv](outputs/hybrid/router_grid.csv)). Ran PyMuPDF 1.28.2 (Linux, the project venv
has 1.25.1) on all 91 chapter pages and compared with the existing MinerU output. Reference
"page needs MinerU" = MinerU found an equation, inline formula or table on that page.

- **76/91 chapter pages need MinerU**: 74 of the 75 maths pages, but only 3 of the 16 science pages (all because of tables).
- The audit's heuristic flags do not help: tested 125 threshold combinations, and the only one
  that misses no maths page sends all 91 pages to MinerU. Page numbers and icon glyphs trigger the flags on almost every page.
- **Subject router**: maths goes to MinerU, science goes to PyMuPDF unless `find_tables()` finds a
  table or there are ≥4 number-only lines. Result: 77 MinerU pages instead of 91. Science drops from 16 to 2 MinerU pages.
  It misses one page (science p3, a table MinerU detected but PyMuPDF did not) and sends 2 plain maths pages to MinerU.
- On plain pages, PyMuPDF and MinerU text agree at median word similarity 0.898. Science p6 and
  p11 are lower (0.53, 0.54) because of reading order around diagram labels.
- Rough Classes 6–10 estimate (page count unmeasured, ~2,500–3,000 pages): MinerU on every page is
  ~10–13 h of CPU. The subject router puts nearly all the saving on science, ~6–8 h total.

Conclusion: use MinerU for maths, and PyMuPDF plus table detection for science.
Diagram-heavy science pages still need a visual check for reading order.
