# Backend (FastAPI + PostgreSQL)

Skeleton of the Socratic AI Tutor API. Data lives in PostgreSQL; the models are stubs, so it runs without a GPU. Interactive docs are at `/docs` once it is running.

## Run

Needs [uv](https://docs.astral.sh/uv/) (`pip install uv` or see its install page) and Docker for the database.

```bash
cd backend
docker compose up -d              # PostgreSQL 16 with pgvector on localhost:5432
uv sync                           # creates .venv with Python 3.12 and installs locked dependencies
uv run uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
uv run pytest -q                  # runs against an embedded PostgreSQL, no Docker needed
```

The connection string is read from `DATABASE_URL` (default in `.env.example`). Tables are created at startup and a sample course pack is seeded. Use `uv add <package>` to add a dependency; commit `pyproject.toml` and `uv.lock`.

## Postman

Import `postman/Socratic_AI_Tutor.postman_collection.json` (and `postman/local.postman_environment.json`). Run the folders in order: Setup, then Tutoring loop. "Start session" stores `session_id` for the later requests. Command line: `npx newman run postman/Socratic_AI_Tutor.postman_collection.json`.

## Endpoints

| Method and path | Purpose |
|---|---|
| `GET /health` | Liveness check |
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
