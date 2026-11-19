> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- pilot-hardening-2026-11-04 -->
## Current repair result — 4 November 2026

The current 83-publisher-question challenge runs over 22 checked passages: 24 calibration and 59 test cases, including 15 supported test questions. BGE and rank fusion both find the relevant concept in the top five for 13/15; BGE concept MRR@5 is 0.649. This is concept relevance, not document recall or answer accuracy. Conservative routing abstains on all 15 supported cases and all 44 challenges, so automatic routing is disabled and one user-selected topic is required. Corpus pruning reused the held-out questions; no fresh independent confirmation is claimed. Latest metrics are outputs/textbook_retrieval_metrics.json; old 26-query metrics below are historical.

See [Pilot repairs and decision](../PILOT_HARDENING.md) for evidence, measured limits and remaining gates. Earlier entries below are historical and superseded where they conflict.

---

<!-- revised-plan-checkpoint-2026-11-03 -->
## Current revised-plan result — 3 November 2026

Repeated the frozen, already exposed 26-query synthetic pilot on the current 12-chunk release; this is not a fresh independent test. BGE test Recall@5 0.9583 / MRR@5 0.9333 across 12 positive test queries; correct accepted concepts 8/12 with four abstentions; zero false acceptances among four negative/ambiguous queries. All 12 source/citation checks passed. Fixed working cutoffs 0.70/0.02; no new sweep decision. Run `20261102T190949-4b7cb0b0`.

Earlier notes below describe earlier runs and are superseded where counts/status conflict.

---

# Phase 11 execution report — retrieval and concept resolution

Updated: 2 November 2026 (evening). Owner: Hariom Kumar.

Retrieval run `20261102T152029-c2c6a311` (earlier today): 12 chunks, 26 synthetic queries.
On the held-out synthetic split, BGE cosine scored recall@5 0.958 and MRR@5 0.933, against
BM25 at 0.875 / 0.826 and the backend's keyword overlap at 0.958 / 0.708. All 12 chunk citations
check out. See [retrieval_metrics.json](outputs/retrieval_metrics.json).

## Cutoff sweep (`code/sweep_cutoffs.py`)
Re-scored the stored top-2 concept similarities over threshold 0.50–0.85 and margin 0.00–0.10.
Outputs: [cutoff_sweep.csv](outputs/cutoff_sweep.csv), [cutoff_sweep_summary.json](outputs/cutoff_sweep_summary.json).

| Policy | Correct / 26 | Missed real questions | False accepts |
| --- | ---: | ---: | ---: |
| Current (0.70, margin 0.02) | 21 | 5 | 0 |
| Best with zero false accepts (0.67, margin 0.01) | 25 | 1 | 0 |

The lowest-scoring real question was 0.671 and the highest off-topic query ("photosynthesis") was
0.665, a gap of only 0.006. The new cutoff was picked using all 26 queries, so it is not a
held-out result. Treat 0.67 as provisional and rerun the sweep once the full Classes 6–10
corpus and a larger query set exist.
