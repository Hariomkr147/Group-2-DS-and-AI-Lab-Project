# supabase-setup (2026-11-12)

## Prompts
1. "setup supadatabase setup", with the pip install command, the Supabase URL and publishable key, and a Flask + supabase-py sample app.
2. Shared a Postgres connection string (password omitted) so the table could be created.
3. Asked for an AGENTS.md to log prompts, links and tools, then a VS Code launch.json, then a per-person log folder convention.

## Links
- Supabase project: https://cztuzjasxgmrznmdceev.supabase.co
- Postgres host: aws-1-ap-northeast-1.pooler.supabase.com:5432 (session pooler)

## Tools and packages
- Claude Code (Claude Sonnet 5.5) in VS Code
- Python packages: supabase, flask, python-dotenv, psycopg[binary]
- Supabase (Postgres plus REST API)

## What the AI did
- Installed the packages.
- Wrote a Flask demo app, a setup script and a `.env` outside the repo.
- Created the `public.todos` table with row level security, a public read policy and 2 sample rows.
- Verified a read through the API with the publishable key.
- Added `AGENTS.md` and `.vscode/launch.json` to the repo.

## Notes
- The database password was pasted into chat and should be reset.
- Secrets are omitted from this log.

## Later in the session (folders, frontend, security)
Prompts: create the folder structure; create the frontend from the mock-app; integrate it with the backend and add a security layer; simplify to one admin account with a random password.

- Added `frontend/` (Vite + React, port of the mock-app UI), `ml/` (rag, kt) with READMEs, and `.vscode/launch.json`.
- Frontend now calls the real backend (`/courses`, `/sessions`, `/learners`) through a `/api` proxy, behind a login page.
- Backend: single account from env (`ADMIN_USERNAME`, `ADMIN_PASSWORD`, `SECRET_KEY`), bearer token on every route except `/health` and `/auth/login`, login and message rate limits, restricted CORS, security headers, and the answer key removed from `/courses/{id}/concepts` and `/graph`. Added `tests/test_auth.py`; 21 tests pass.
- `backend/.env` holds a generated password and is gitignored. The password is not recorded here.
