# Backend (FastAPI + PostgreSQL)

Skeleton of the Socratic AI Tutor API. Data lives in PostgreSQL; the models are stubs, so it runs without a GPU. Interactive docs are at `/docs` once it is running.

## Run

Needs [uv](https://docs.astral.sh/uv/) (`pip install uv` or see its install page) and Docker for the database.

```bash
cd backend
cp .env.example .env              # then fill in ADMIN_PASSWORD and SECRET_KEY (see Security)
docker compose up -d              # PostgreSQL 16 with pgvector on localhost:5432
uv sync                           # creates .venv with Python 3.12 and installs locked dependencies
uv run --env-file .env uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
uv run pytest -q                  # runs against an embedded PostgreSQL, no Docker needed
```

The connection string is read from `DATABASE_URL` (default in `.env.example`). Tables are created at startup and a sample course pack is seeded. Use `uv add <package>` to add a dependency; commit `pyproject.toml` and `uv.lock`.

## Connecting pgAdmin to the local database

Start the database first with `docker compose up -d`. Then in pgAdmin, go to Register → Server and enter:

| Field | Value |
|---|---|
| Host | `127.0.0.1` |
| Port | `5432` |
| Maintenance database | `tutor` |
| Username | `tutor` |
| Password | `tutor` |

On the **Parameters** tab, add these two settings:

- `SSL mode` = `disable`
- `GSS encryption mode` = `disable`

Without them, some pgAdmin 9.x builds on Windows crash with `access violation writing 0x0000000000000000` when connecting. Use `127.0.0.1` rather than `localhost`, because `localhost` can resolve to a different listener on IPv6.

## Enabling the vector extension (pgvector)

The Docker image already includes pgvector, but it has to be enabled once per database. In pgAdmin, open Query Tool on the `tutor` database and run:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Check that it worked:

```sql
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

It should return one row with `vector`. Without pgAdmin, run it from the command line instead:

```bash
docker exec -it backend-db-1 psql -U tutor -d tutor -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Use the `tutor` database, not the default `postgres` one. The extension is enabled per database, so a new database or a fresh `docker compose down -v` needs it again.

## Security

The API has one account, set in `.env`. Every route except `GET /health` and `POST /auth/login` needs a bearer token.

| Variable | Purpose |
|---|---|
| `ADMIN_USERNAME` | Login name (default `admin`) |
| `ADMIN_PASSWORD` | Login password. Make a random one: `python -c "import secrets; print(secrets.token_urlsafe(16))"` |
| `SECRET_KEY` | Signs login tokens (same command, longer: `token_urlsafe(48)`) |
| `APP_ENV=production` | Refuses to start without the two secrets above and hides `/docs` |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated (default: localhost 3000 and 5173) |
| `TOKEN_MINUTES`, `MESSAGES_PER_MINUTE` | Token lifetime (480) and tutor message limit (30) |

- Log in: `POST /auth/login {"username", "password"}` returns `access_token`. Send it as `Authorization: Bearer <token>`. In `/docs`, use Authorize.
- Wrong logins are limited to 10 a minute per address; tutor messages to 30 a minute. Limits are in memory, per process.
- Course concepts and the graph never include the question answers.
- Keep `.env` out of git (it is in `.gitignore`) and use HTTPS in front of the API when deployed. Behind a proxy, the per-address limit sees the proxy's address.
- If `ADMIN_PASSWORD` is unset in development, a random one is printed once at startup.

## Postman

Log in first (`POST /auth/login`) and send the token as a bearer token; the collection does not do this yet. Import `postman/Socratic_AI_Tutor.postman_collection.json` (and `postman/local.postman_environment.json`). Run the folders in order: Setup, then Tutoring loop. "Start session" stores `session_id` for the later requests. Command line: `npx newman run postman/Socratic_AI_Tutor.postman_collection.json`.

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Liveness check (open) |
| `POST /auth/login` | Sign in, returns a token (open) |
| `GET /auth/me` | Who the token belongs to |
| `GET /courses` | List course packs |
| `POST /courses` | Ingest a course pack (concepts, prerequisites, material, questions) |
| `GET /courses/{id}/concepts` | Concepts of a course |
| `GET /courses/{id}/graph` | Prerequisite graph across levels (nodes and edges) |
| `POST /sessions` | Start a session `{learner_id, course_id}` |
| `GET /sessions/{id}` | Session state and conversation history |
| `POST /sessions/{id}/messages` | Send learner text, get the tutor reply `{reply, action, label, concept_id, level, resource}` |
| `POST /learners/{id}/answers` | Record an answer given outside the chat |
| `GET /learners/{id}/progress?course_id=` | Readiness per concept |
| `GET /search?course_id=&q=` | Find the page, notes or lecture for a concept |
| `POST /practice` | Practice questions for a concept (answers hidden) |
| `POST /diagnostics` | Short test, lowest level first (answers hidden) |

A sample NCERT-style pack (`ncert-maths`: multiplication → division → fractions → percentages) is loaded at startup.

## Where the models plug in

Each is a stub in `app/services/` with the interface the real model must keep.

| File | Stub now | Replace with |
|---|---|---|
| `learner_model.py` | smoothed accuracy per concept | trained DKT (per learner, per course, per session) |
| `controller.py` | fixed rules (the comparison baseline) | trained controller model |
| `socratic.py` | templates | fine-tuned Qwen3-4B + LoRA |
| `misconception.py` | returns nothing | trained misconception detector |
| `guardrails.py` | keyword rules | input classifier and output checker |
| `retrieval.py` | keyword overlap | pgvector embedding search (the database image already includes pgvector) |

`app/services/tutor.py` runs one turn: input check → learner model → controller → Socratic model → output check. Off-topic messages and answer requests get a redirect and are never written to the learner model.

Tables (`app/db.py`): `courses`, `concepts` (prerequisites, material and questions stored as JSON), `sessions`, `turns`, `answers`. Learner history is the `answers` table, so DKT reads it per learner, per course and per session.
