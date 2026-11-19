> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- pilot-hardening-2026-11-04 -->
## Current repair result — 4 November 2026

57 source-bound block corrections are applied with exact before/after checks: hour OCR, recoverable currency symbols and an omitted answer blank. A source-coordinate order fixes science physical page 6. Original PDFs/raw records are unchanged; 55 ambiguous currency positions stay excluded. Cleaning reconciles 3,090 records, 685 logged transformations and 241 removed margin records.

See [Pilot repairs and decision](../PILOT_HARDENING.md) for evidence, measured limits and remaining gates. Earlier entries below are historical and superseded where they conflict.

---

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Final cleaning: 3,090 input/output records, 628 logged changes, 241 margin records removed from usable text (179 repeated reprint footers, 62 headers), 685 quarantined records. LaTeX and table HTML unchanged. Run `20261102T190253-89516b4f`.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 05 execution report

Date: 2 November 2026. Owner: Hariom Kumar; execution assisted by Codex.
Status: **Draft cleaning executed; semantic/source review pending.**
Accepted cleaned release: **None**.

Implemented `code/clean_content.py` and four regression checks. Latest run:
`20261102T140235-b19da6c8`. Inputs are the validated canonical 191 pages / 3,980 blocks;
all **3,980** raw block identities remain present in cleaned records.

## Actual transformations

**1,537 changed blocks**, **228 removed from candidate text** (raw records retained),
**705 quarantined blocks**. Rule counts overlap when multiple rules affect one block:

| Rule | Affected blocks | Boundary |
| --- | ---: | --- |
| Repeated reprint footer | 166 | Exact source edition, bottom position, at least three pages |
| Repeated running header | 62 | Exact book/chapter allowlist, top position, at least three pages |
| Trailing/outer ASCII spacing | 1,303 | Internal spacing/line structure retained |
| Unsafe control → space | 38 | Does not join adjacent tokens; block quarantined |

[cleaning_rules.csv](outputs/cleaning_rules.csv) records rationale, limits,
implementation and reversibility. [quarantine.csv](outputs/quarantine.csv) records
block/page reasons. Critical formula/table/visual content stays quarantined until
review; unknown glyphs, controls and duplicate artifacts receive explicit reasons.
Exact same-page/source/coordinates/content duplicate candidates retain `duplicate_of`
lineage rather than erasing legitimate repetitions across books or pages.

LaTeX and HTML remain byte-for-byte unchanged in their derivatives. No fraction
slash repair, Unicode folding, punctuation removal, numeric-line filter, blanket
dehyphenation or paragraph reflow was applied. Every non-removal change preserves
the sequence of non-whitespace/control characters. That invariant detects data
loss; it does not establish mathematical meaning.

## Real before/after evidence

Local ignored `evidence/before_after.jsonl` selects actual chapter-content examples,
including every applied rule, unchanged maths and quarantine. Native references,
full block IDs, source IDs and physical pages accompany exact before/after fields.

| Source / physical page | Actual change | Reason / disposition |
| --- | --- | --- |
| Grade 6 fractions p1 footer | `Reprint 2026-27` → empty candidate text | Exact repeated bottom footer; raw text recoverable |
| Grade 6 fractions p2 header | `Ganita Prakash \| Grade 6` → empty candidate text | Exact repeated running header at top |
| Grade 6 fractions p3 exercise block | Embedded U+0007 replaced by a space; fraction LaTeX unchanged | Unsafe-control case stays quarantined |
| Grade 6 fractions p1 inline maths | Formula representation unchanged | No invented slash/denominator correction; semantic review still pending |

Original-page references are the unchanged [Grade 6 PDF](../01_download_pdfs/pdfs/mathematics/class_6/2026-27/fegp1/fegp107.pdf).
Numeric-only lines and subtraction/line-wrap ambiguity are retained. No fabricated
transformation was added to fill an example slot. Private answer material is not
quoted in the public-facing report or selected chapter-content evidence examples.

## Traceability and rerun

Local outputs: `outputs/clean_blocks.jsonl`, `clean_pages.jsonl`,
`transform_log.jsonl` and run-specific cleaned/log snapshots. Every changed/removed
block has raw identity, exact before/after text/LaTeX/HTML, rule IDs, reason,
source/page reference and pending/quarantined review status. Selected no-ops are
in the evidence file rather than invented changes. A draft cannot overwrite an
approved cleaned artifact. First-run outputs were retained before reruns.

Reruns preserve block count, all cleaned content hashes, rule counts, removals and
quarantine count. The extraction adapter's provenance-version change did not change
cleaned content. Four tests passed: operators/fractions/percent/units/numeric lines;
control-character number joining; repeated-margin boundaries versus real numbers;
and unchanged formula/table/private fields with quarantine.

```powershell
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\05_clean_and_preprocess\code\test_cleaning.py'
& 'Ncert work\.venv\Scripts\python.exe' 'Ncert work\05_clean_and_preprocess\code\clean_content.py'
```

No block is approved for retrieval by this cleaning pass. Human corrections and
semantic source reviews remain a separate auditable step before release.
