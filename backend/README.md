# Backend (FastAPI + PostgreSQL)

Skeleton of the Socratic AI Tutor API. Data lives in PostgreSQL; the models are stubs, so it runs without a GPU. Interactive docs are at `/docs` once it is running.

## Run

Needs [uv](https://docs.astral.sh/uv/) (`pip install uv` or see its install page) and Docker for the database.

```bash
cd backend
cp .env.example .env              # then fill in ADMIN_PASSWORD and SECRET_KEY (see Security)
docker compose up -d              # PostgreSQL 16 with pgvector on localhost:5432
uv sync --extra rag               # creates .venv with Python 3.12 and installs locked dependencies; --extra rag adds torch and transformers for NCERT retrieval (large)
uv run --extra rag --env-file .env uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
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
| `GET /courses/ncert/chapters?grade=&subject=` | Approved textbook chapters and topic headings |
| `POST /sessions` | Start a session `{learner_id, course_id}` |
| `GET /sessions/{id}` | Session state and conversation history |
| `POST /sessions/{id}/messages` | Send learner text (an answer, or working with one step per line), get the tutor reply `{reply, action, label, concept_id, level, resource, misconception, wrong_step}` |
| `POST /learners/{id}/answers` | Record an answer given outside the chat |
| `GET /learners/{id}/progress?course_id=` | Readiness per concept |
| `GET /search?course_id=&q=` | Find the page, notes or lecture for a concept |
| `POST /practice` | Practice questions for a concept (answers hidden) |
| `POST /diagnostics` | Short test, lowest level first (answers hidden) |
| `POST /assessments` | Issue practice or diagnostic questions for a session |
| `POST /assessments/{item_id}/answer` | Grade one issued question and record its first result |

## NCERT Classes 6–10 Textbook Retrieval & Tutoring

In addition to sample course packs, the backend supports direct grounded tutoring against the approved NCERT textbook corpus (Classes 6–10 Maths and Science).

| Setting | Purpose |
|---|---|
| `NCERT_ENABLED` | Set to `1` to retrieve from the `ncert_research` schema of `DATABASE_URL` (textbook corpus with pgvector). |
| `NCERT_MODEL_URL` | Hosted Socratic tutoring model URL (`/predict`). |
| `NCERT_MODEL_API_KEY` | Bearer or API key for the model endpoint. |
| `NCERT_MODEL_AUTH_HEADER` | Header format: `Authorization` (default) or `X-API-Key`. |

NCERT retrieval needs the `rag` extra (torch and transformers); without it `POST /sessions/{id}/messages` returns 503 "The NCERT question encoder is unavailable". Install it with `uv sync --extra rag` and start the server with `uv run --extra rag ...`. The first request downloads the Qwen3-Embedding-0.6B model (about 1.2 GB). The VS Code launch config "Backend: API (uvicorn)" already sets `NCERT_ENABLED=1` and uses `backend/.venv`.

- **Sessions with NCERT**: `POST /sessions` with `course_id: "ncert"` and optional `grade` (6-10) and `subject` (`maths` or `science`). Send a `chapter` selected from the catalogue to constrain the session to that chapter.
- **Query / Search**: `GET /search?course_id=ncert&q=...&grade=10&subject=science`.
- **Grounded Tutoring**: `POST /sessions/{id}/messages` automatically matches relevant textbook passages, cites the chapter and physical PDF page, and provides Socratic guidance. Send `new_topic: true` to clear chapter context.

Message clients can supply a stable UUID as `request_id` when retrying a turn. The saved reply is returned for a matching retry. Session history includes per-turn reply details for turns recorded by this version.

A sample NCERT-style pack (`ncert-maths`: multiplication → division → fractions → percentages) is loaded at startup.

## Where the models plug in

Each is a stub in `app/services/` with the interface the real model must keep.

| File | Stub now | Replace with |
|---|---|---|
| `learner_model.py` | smoothed accuracy per concept; trained AKT when `KT_MODEL=akt` (see below) | trained DKT (per learner, per course, per session) |
| `controller.py` | fixed rules (the comparison baseline) | trained controller model |
| `socratic.py` | fine-tuned Qwen (`qwen_finetuned`) writes hint and probe turns; templates for the rest and as fallback | Qwen for every turn, with conversation history |
| `misconception.py` | error patterns and expression search on a bare wrong answer | kept as the fallback when no working is sent |
| `step_finder.py` | first wrong step in the learner's working: code checks the sums, fine-tuned Qwen names a wrong method (`STEP_FINDER_PROVIDER`) | model fine-tuned for this task; evaluation in `eval/misconception/` |
| `guardrails.py` | packaged TF-IDF and logistic-regression intent and scope classifier, plus answer-disclosure checks | evaluate on reviewed learner conversations |
| `retrieval.py` | keyword overlap | pgvector embedding search (the database image already includes pgvector) |

To use the fine-tuned Qwen, run `docs/milestone-3/model_hosting/hosting-qwen.ipynb` on a Kaggle or Colab GPU and set `QWEN_URL` and `QWEN_API_KEY` in `.env`. If the model is not set up, unreachable, cut off or gives away the answer, the template reply is used. `SOCRATIC_PROVIDER=templates` switches the model off.

`app/services/tutor.py` classifies each chat message before choosing the course-pack or NCERT path. The classifier predicts intent and curriculum scope from the message and up to six recent turns. Topic switches require a match in the selected course. In course-pack chat, only a recognizable answer to a pending assessment reaches grading. NCERT chapter chat provides ungraded guidance. When classification is uncertain or unavailable, explicit requests and recognizable answers use backend checks. Other ambiguous turns prompt for clarification.

The app loads `app/services/message_router.joblib` once on demand. To rebuild it from the repository root, run the command below in an environment with the backend dependencies. See the [router evaluation notes](eval/message_router/README.md) for training data and results.

```bash
python backend/eval/message_router/export_router.py
```

Tables (`app/db.py`): `courses`, `concepts` (prerequisites, material and questions stored as JSON), `sessions`, `turns`, `answers`. Learner history is the `answers` table, so DKT reads it per learner, per course and per session.

### Knowledge tracing (AKT)

Set `KT_MODEL=akt` (needs torch, the `rag` extra) to score readiness with the trained AKT in `models/akt/` (Mrityunjay's ASSISTments 2009 run, one step per problem attempt, split by student, test AUC 0.779). `readiness` uses AKT only for concepts listed in `models/akt/concept_skill_map.json` that have mapped answer history; every other case uses smoothed accuracy, and so does a missing torch, file or checksum. Only `percentages` (and the NCERT fraction ids) are mapped so far, from `mock-app/README.md`; the skill mapping for other concepts is still open. NCERT questions use the neutral difficulty entry, so this is an unvalidated curriculum transfer.

### Session state

The `sessions` table keeps the tutor's position between turns, so each request can load it, decide the next step and save it back. A session can also resume after a page refresh. The controller reads and writes these columns (`app/services/controller.py`, `app/services/tutor.py`).

| Column | Meaning | Used for |
|---|---|---|
| `target_concept` | The concept the learner chose to learn. Set on the first message. | The goal. A correct answer on it ends the session (`DONE`). It is also where the tutor returns when the stack is empty. |
| `current_concept` | The concept being questioned now. It differs from the target after a backtrack. | Questions are generated for it, and answers are scored and written to the learner model against it. |
| `pending` | The question asked and not yet answered (JSON), or null. | The next message is checked against it. An answer is graded. Any other message, such as a doubt, can get the same question again. |
| `stack` | Concepts to return to after a prerequisite detour (JSON list). | A wrong answer with a weak prerequisite (readiness below `WEAK` = 0.6) pushes the current concept and moves to that prerequisite (`BACKTRACK`). A correct answer pops the stack (`ADVANCE`). This allows multi-level backtracking. |
| `tries` | Wrong answers on the current concept. | Resets on a correct answer or a backtrack. With no weak prerequisite, the first `MAX_TRIES` (2) wrong answers get a `HINT`, then the tutor switches to `PROBE`. |

Example: target C needs B, and B needs A.

1. Wrong on C, B is weak: `stack=[C]`, `current=B`, `BACKTRACK`.
2. Wrong on B, A is weak: `stack=[C,B]`, `current=A`, `BACKTRACK`.
3. Correct on A: pop B, `ADVANCE`.
4. Correct on B: pop C, `ADVANCE`.
5. Correct on C (the target): `DONE`.

The trained controller model will receive these same fields as input.
