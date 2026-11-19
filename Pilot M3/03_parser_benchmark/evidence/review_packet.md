# Parser/reference review packet

Date: 2 November 2026. Benchmark run: `20261102T130357-d1ef3c6f`.
Prepared by Codex for Hariom Kumar. **Independent human review: pending.**

Both parsers processed the same 15 physical pages from unchanged original PDFs.
Raw output is local under `parser_outputs/20261102T130357-d1ef3c6f/`.
Source hashes, physical page IDs and parser versions are recorded in
[parser_comparison.csv](../outputs/parser_comparison.csv).

The four proposed reference transcriptions below were visually transcribed by
Codex, not a human. Please verify them against the linked originals. Confirm or
correct the mathematical grouping as well as the characters. Their machine-readable
local file is `reference_transcriptions.jsonl`; it retains source hashes, full-page
coordinate bounds, print labels and pending review status.

| Reference | Original PDF physical page / visible print label | Proposed reference |
| --- | --- | --- |
| R1 | [Grade 6 Fractions p15](../../01_download_pdfs/pdfs/mathematics/class_6/2026-27/fegp1/fegp107.pdf#page=15) / 165 | Fractional unit above the wall: `1/10` |
| R2 | [Grade 7 Fractions p26](../../01_download_pdfs/pdfs/mathematics/class_7/2026-27/gegp1/gegp108.pdf#page=26) / 198 | `a/b ÷ c/d = a/b × d/c = (a × d)/(b × c)` |
| R3 | [Grade 8 Quantities p10](../../01_download_pdfs/pdfs/mathematics/class_8/2024-25/hemh1/hemh107.pdf#page=10) / 88 | `A = P (1 + R/100)^n` |
| R4 | [Grade 7 Science p8](../../01_download_pdfs/pdfs/science/class_7/2026-27/gecu1/gecu107.pdf#page=8) / 96 | Heat transfer by radiation does not require any medium. |

## Actual parser observations

- R1: PyMuPDF emits the numerator and denominator on separate lines. MinerU
  emits a fraction expression with denominator digits spaced as `1 0`; it also
  proposes a table for the fraction wall. Correct table cells/semantics still
  need checking, separately from the small R1 expression.
- R2: PyMuPDF emits numerator/denominator lines. MinerU emits the reviewed-form
  candidate `\frac{a}{b} \div \frac{c}{d} = \frac{a}{b} \times \frac{d}{c} = \frac{a \times d}{b \times c}`.
- R3: PyMuPDF emits private-use glyphs and separates powers/fraction components.
  MinerU emits `\mathrm{A} = \mathrm{P}\left(1 + \frac{\mathrm{R}}{100}\right)^n`.
- R4: native extraction retains the prose with layout breaks. MinerU gives
  structured prose and separate image regions. This does not establish diagram
  understanding or correct complete-page reading order.

Counterexample: Grade 6 physical p1 contains a MinerU header prediction `X 8 VV`
from visual material and a `page_number` prediction of `7`, which is the chapter
number. Parser-generated page labels must not replace physical PDF page identity
or become trusted printed labels without source review.

Private-material boundary: Grade 7 physical p37 is an answer key. Its text is
retained only in local parser artifacts; it is not quoted in this packet or
approved for open retrieval. See [page dispositions](../../02_pdf_audit/outputs/source_page_dispositions.csv).

## Review record to complete

- R1–R4 reference correctness/corrections: **Pending human input**.
- Formula grouping, reading order and table checks: **Pending**.
- False/missing-content findings and disagreements: **Pending**.
- Reviewer/date: **Pending; no signature or approval supplied**.
- Accepted parser/OCR policy: **None yet**.

Phase 03 asks for a human-checked transcription subset before reporting error
rates. No CER/WER, formula accuracy, confidence score or winner is supplied here.
These four snippets are a review starting point, not full-page gold transcriptions.
