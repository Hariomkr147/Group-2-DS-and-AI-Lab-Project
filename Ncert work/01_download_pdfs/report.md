> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Verified nine official PDFs, now 203 physical pages, including the separate 12-page Grade 8 answer key. The answer key has 11 private solution pages and one excluded notes page. Run `20261102T184438-25589d6c`.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 01 execution report

Date: 2 November 2026. Owner: Hariom Kumar; execution assisted by Codex.
Status: **Completed — acquisition/integrity checks; independent content review pending.**
Accepted content release: **None**.

Implemented `code/download_pdfs.py` and `code/verify_downloads.py`, reusing Phase 00
validation. Downloaded **8/8** selected official PDFs: four chapters and four
prelims. Total **20,413,502 bytes**, **191 physical pages** (119 chapter pages;
72 prelim pages). All have official URLs, edition-specific IDs, timestamps, local
paths, SHA-256 hashes and rights notes in [manifests/sources.csv](manifests/sources.csv).
Zero duplicate hash groups were found. The other 39 scope chapters were not requested.

| Source file | Role | Physical pages |
| --- | --- | ---: |
| fegp107.pdf | Grade 6 fractions | 50 |
| fegp1ps.pdf | Grade 6 edition/contents | 20 |
| gegp108.pdf | Grade 7 fraction operations | 39 |
| gegp1ps.pdf | Grade 7 edition/contents | 18 |
| hemh107.pdf | Grade 8 comparing quantities | 14 |
| hemh1ps.pdf | Grade 8 edition/contents | 14 |
| gecu107.pdf | Grade 7 heat transfer | 16 |
| gecu1ps.pdf | Grade 7 edition/contents | 20 |

Acquisition checks HTTP success, content type, PDF signature, opening, encryption,
positive page count and title/edition probes before publishing a local file. A
same-directory hard link publishes verified bytes without replacing an existing
file. Each successful source is persisted to the manifest immediately. On rerun,
existing manifest entries must still match scope, identity, size, pages and hash.
An unmanifested existing file is refused for explicit recovery inspection.

Actual failure/recovery:
- `20261102T124959-77065d06`: downloaded seven PDFs; Grade 6 prelim failed with
  curl error 35, connection reset. Preserved in [download_failures.csv](manifests/download_failures.csv).
  The initial failure row describes configured retries; curl's original `--retry 2`
  did not retry error 35. `--retry-all-errors` was then added.
- `20261102T125142-b4fbdb06`: downloaded the missing PDF and reverified seven.
- `20261102T125343-d46d7687`: **0 downloaded / 8 reverified**; no existing original
  or download timestamp replaced. Manifest hash remained unchanged.
- `20261102T125344-eb5c7474`: independent reopen/hash/page reconciliation, 8 PDFs/191 pages.

Run UTC start/end, actual commands, code/config/input/output hashes, failures and
duplicate checks: local `logs/run_manifest.jsonl`; versionable copy in the
[root execution summary](../execution_summary.json). Download/recovery runtimes
were 9.35 s (partial), 3.42 s (recovery), 0.54 s (verified reuse) on this local
machine. These are these small runs, not bulk-download throughput promises.

Representation examples: `fegp107.pdf` became an edition-specific source row
with 50 physical pages; `hemh107.pdf` retained its older 2024–25 identity;
`gecu1ps.pdf` became metadata-only evidence; the failed Grade 6 prelim was omitted
from successful coverage until its recovered download. All original PDF bytes
remain unchanged; no cleaning or repair was applied.

Python certificate checks failed against NCERT during discovery; Windows curl
succeeded with TLS verification enabled. No certificate verification was disabled.
Offline checks reject HTML, wrong identity/edition, changed hashes and overwrite attempts.

NCERT's official textbook notice and prelims restrict reuse. Originals stay local
under ignored `pdfs/`; no public PDF/excerpt or retrieval-system permission is
claimed. Review terms/permission before downstream publication or content release.
Commands: [environment.md](../00_setup_and_scope/config/environment.md).
