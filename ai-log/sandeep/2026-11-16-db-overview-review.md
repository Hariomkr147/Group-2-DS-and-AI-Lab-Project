# db-overview-review (2026-11-16)

## Prompts
1. Review `backend/database_complete_overview.md` and check it is consistent with the existing backend code.

## Links
- None (repo files only).

## Tools and packages
- Claude Code (Claude Fable 5.2) in VS Code

## What the AI did
- Read `backend/database_complete_overview.md`, `backend/app/` (db, main, schemas, routers, services) and `Ncert work/10_embeddings_and_database/code/schema.sql`.
- Reported mismatches; the code was taken as correct.
- Edited `backend/database_complete_overview.md` only: removed the plain-text database password, fixed the turn role (`learner`), the route (`/sessions/{id}/messages`), cascades, indexes, the `pending` and `tries` descriptions and the sample JSON, and marked section 2 and the section 4 flowchart as planned. No code was changed.

## Prompts (continued)
2. Which is right, the doc or the code? The RAG part is handled by another team member.
3. Take the necessary actions.

## Notes
- The database password was in the file in plain text and has been in chat. Value omitted here. It still needs to be reset in Supabase.
- The `ncert_research` schema is not defined or used anywhere in the repo, and the live database was not queried, so section 2 and all row counts are unverified. The RAG owner should confirm it against `Ncert work/10_embeddings_and_database/code/schema.sql` (`ncert_content.chunks`, 384-d).
