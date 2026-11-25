# answer leak guardrails (2026-11-25)

## Prompts
1. Didn't we integrate AKT with NCERT classes 6 to 10? What is needed for AKT on NCERT? Current vs text-embedding approach.
2. The tutor revealed the answer (2 x 3 x 5 = 30) to a word problem. What is wrong? Don't we have guardrails?
3. Replace the regex with an LLM classifier, make the changes and add the test.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5)
- pytest, uv

## What the AI did
- Checked AKT wiring: AKT runs only for course packs; the NCERT path records no answers and never calls readiness.
- `backend/app/services/socratic.py`: added `is_problem` (model classifier: problem or concept); no-reveal rule now applies in every mode; grounded replies are checked with `leaks_result` and fall back to a guide prompt.
- `backend/app/services/guardrails.py`: added `likely_results` and `leaks_result` (blocks sums, products and other likely results of the student's numbers, without a stored answer).
- `backend/app/services/tutor.py`: `_is_exercise` uses the model first, the `_PROBLEM` regex only as fallback.
- `backend/tests/test_ncert.py`: regression test with the exact message, classifier and `leaks_result` tests.
- Ran `uv run pytest`: 214 passed, 3 errors in `test_akt.py`.

## Notes
- The `test_akt.py` errors are not from this change: local `models/akt/skill_map.csv` has a different checksum from the committed file (likely line-ending conversion).
- The problem classifier adds one model call per NCERT question message.
- `leaks_result` only sees digits, not number words ("two, three and five").
- README line on AKT and NCERT is out of date.
