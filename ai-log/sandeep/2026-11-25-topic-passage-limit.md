# topic passage limit (2026-11-25)

## Prompts
1. Why is `topic_passage` returning a single passage?
2. Increase the limit to 5, make it configurable from .env, default 5.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5), pytest

## What the AI did
- Explained that `_TOPIC_PASSAGE` ended with `LIMIT 1` and returned only the chunk where the topic starts.
- `backend/app/services/ncert.py`: changed `LIMIT 1` to `LIMIT :limit`, read the limit from `NCERT_TOPIC_PASSAGES` (default 5, at least 1), and joined the chunks' content into one passage dict that keeps the first chunk's id, page and link.
- `backend/.env.example`: added `NCERT_TOPIC_PASSAGES=5`.
- Ran `pytest tests/test_ncert.py tests/test_ncert_backtracking.py`: 44 passed.

## Notes
- Follow-ups reload the passage by id through `cited_passage`, which still returns only the first chunk.
- Socratic practice prompts cut passage text at 1200 characters, so later chunks may be dropped there.
