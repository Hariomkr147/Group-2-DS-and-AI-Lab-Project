# prerequisite query logging (2026-11-25)

## Prompts
1. Log the prerequisites query so I can debug when prerequisites are not picked up correctly.
2. Also log the topics it picked, and log them as info.
3. Why does the embedding prerequisites query return nothing for "2.4.3 Amazing microalgae" (Class 8)?

## Links
- None

## Tools and packages
- Claude Code (Claude Opus 5.5), SQLAlchemy

## What the AI did
- backend/app/services/ncert.py: graph_prerequisites and prerequisites log the SQL with values filled in (via _runnable_sql), the row count and the topic heading. A line is logged when NCERT_GRAPH=0 skips the graph.
- Added _log_picked: one line per picked topic (source, class, book, chapter, page, heading, score, and concept for graph rows).
- These logs are at info level on the uvicorn.error logger, since the app has no logging config. A failed graph query still logs at warning.
- Ran the backend tests: 199 passed, 1 skipped.

- Ran read-only diagnostic queries. Finding: the best embedding match scores 0.497, below the 0.55 cutoff. The graph's only prerequisite (eutrophication) appears only in Class 9, so the "earlier topics only" rule drops it. No code changed for this.
- Prompt 4 (lower the cutoff to 0.45): changed PREREQUISITE_MIN_SCORE from 0.55 to 0.45 in ncert.py.

## Notes
- 0.45 is still a guess from one topic. Check the "prerequisites picked" logs on more topics for poor matches.
- The graph edge eutrophication -> Microalgae looks reversed; tell the graph owner.
- Remove or quieten the SQL logs once prerequisites work as expected; they are long.
