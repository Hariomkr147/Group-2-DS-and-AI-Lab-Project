# ncert backtracking (2026-11-20)

## Prompts
1. Is backtracking implemented in the UI path? Check if prerequisite mapping works, and fix it if not.
2. In the UI I selected a maths topic and asked where we are; it could not tell.
3. Can misconception mapping be derived at run time instead of hardcoded?

## Links
- None

## Tools and packages
- Claude Code (Sonnet 5.5), pytest

## What the AI did
- Found: backtracking only worked for course packs; NCERT lessons (the maths UI path) had no prerequisite graph and no backtracking.
- backend/app/services/ncert.py: `prerequisites()` finds earlier topics closest in meaning from stored embeddings (no hand-made map).
- backend/app/services/ncert_path.py (new): stuck limit, detour stack, resume and "basics" phrases.
- backend/app/services/tutor.py: after two help requests in a row the tutor steps back to a prerequisite; "back to the main topic" returns; "what are the prerequisites?" lists them; where-are-we now works in NCERT and course-pack lessons and mentions a detour.
- backend/app/services/conversation.py: `asks_where()` replaces a narrow regex.
- backend/tests/test_ncert_backtracking.py (new): 24 tests. Full suite: 178 passed, 3 AKT errors that were already failing.
- Misconceptions: already built at run time from each question's numbers (patterns plus a search); only the error-pattern templates are hand-written. No change made.

## Notes
- The prerequisite SQL and the 0.55 similarity cut-off were not run against the real corpus; check on the Supabase data.
- NCERT lessons are ungraded, so misconception detection does not apply there yet.
