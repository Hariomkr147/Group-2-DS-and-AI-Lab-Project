# rag query testing (2026-11-25)

## Prompts
1. Share a sample RAG query to test.
2. I mean a database query.
3. Log the query in `topic_passage` so I can run it in the database directly.

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5)
- SQLAlchemy 2.0 (`literal_binds` compile), pgvector

## What the AI did
- Gave sample `/api/search` calls and SQL for the NCERT passages table (counts, keyword search, vector search seeded by a passage).
- `backend/app/services/ncert.py`: added `_runnable_sql()`, which returns a query with its values filled in. `topic_passage()` now logs that SQL and the row count at WARNING level.
- Checked the rendered SQL with sample values, without connecting to the database.

## Notes
- The log line is a debug aid. Remove it or lower it to DEBUG before merging.
- The log contains the student's topic heading, but no secrets.
