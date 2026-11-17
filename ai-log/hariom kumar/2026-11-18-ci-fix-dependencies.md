# ci-fix-dependencies (2026-11-18)

## Prompts
1. `why ci failed on my pr`
2. `audit the branch, fix what's broken and update uv.lock, stage it so i can see the diff`
3. `add requirements.txt for backend and render.yaml in separate commits`
4. `push all and give me a pr description`
5. `why is it showing 404 in the render logs?`

## Links
- PR: https://github.com/Hariomkr147/Group-2-DS-and-AI-Lab-Project/pull/9
- CI run: https://github.com/Hariomkr147/Group-2-DS-and-AI-Lab-Project/actions/runs/44080919844
- Render deployment: https://socratic-ai-tutor-z2s0.onrender.com

## Tools and packages
- Antigravity, uv, pytest, git, npm, Python 3.13

## What the AI did
- Traced the CI failure on PR #9: `uv sync --locked` exited with an error because `backend/pyproject.toml` had been updated without committing the matching `uv.lock`.
- Restored `pyjwt` and `google-genai` in `backend/pyproject.toml`, which were accidentally dropped in an earlier commit and broke authentication.
- Regenerated `backend/uv.lock` with `uv lock` to include `pg8000` and optional dependencies.
- Verified that all 69 backend tests passed in pytest and confirmed the frontend built cleanly.
- Added `backend/requirements.txt` and `render.yaml` as separate commits, then pushed them to `origin/rag-wiring`.
- Diagnosed the 404 logged on Render for `GET /` and `HEAD /`: FastAPI had no route mounted for root `/` or static assets.
- Updated `backend/app/main.py` to serve `frontend/dist/index.html` at `/`, mounted `/assets` to static files, and routed API calls to `/api`. Also updated `backend/app/db.py` to convert `postgresql://` connection strings to `postgresql+psycopg://`.

## Notes
- PR #9 passed CI and merged cleanly into main.
- Production Render deployment now serves the full frontend UI with 200 OK.
