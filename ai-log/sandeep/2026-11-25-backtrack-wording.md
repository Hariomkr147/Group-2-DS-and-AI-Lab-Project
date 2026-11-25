# backtrack wording (2026-11-25)

## Prompts
1. What's causing the "Let's step back to ... Say 'back to the previous topic' ..." message? It's annoying.
2. Remove the wording.
3. I changed "Welcome back to" to "Welcome to"; adjust unit tests.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5), pytest

## What the AI did
- Explained the trigger: two help requests in a row (STUCK_LIMIT = 2) or the path classifier label "basics" makes the tutor step back to a prerequisite.
- backend/app/services/tutor.py: removed the "Say 'back to the ...'" hint from the step-back reply and the "Welcome back" reply. It still appears in the "where are we?" reply.
- backend/tests/test_ncert_backtracking.py: updated one test to match.
- backend/tests/test_ncert_backtracking.py: changed "Welcome back" to "Welcome to" in 11 assertions to match the user's edit.
- Ran tests/test_ncert_backtracking.py and tests/test_ncert.py: 72 passed.

## Notes
- Still open: step-back happens automatically; consider asking first, raising STUCK_LIMIT, and skipping box headings like "Think and Reflect" as topics.
