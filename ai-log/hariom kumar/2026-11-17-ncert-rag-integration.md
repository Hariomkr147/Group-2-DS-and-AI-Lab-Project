# Individual AI usage log: Backend review and NCERT RAG

**Contributor:** Hariom Kumar  
**Work covered:** 17 November 2026  
**AI tool:** Antigravity and Codex (code inspection, RAG wiring, citation formatting, test drafting)  
**Context:** NCERT Classes 6 to 10 textbook content previously extracted, chunked, and stored in Supabase with pgvector.

## My contribution

I directed the integration of our pre-extracted NCERT textbook dataset into the FastAPI backend. I provided the database setup details: passage embeddings had already been generated with `Qwen/Qwen3-Embedding-0.6B` and loaded into a Supabase Postgres instance. When initial code drafts defaulted to a Class 7 demonstration, I pushed back and required full support for Classes 6 to 10 across both Maths and Science.

I designed the retrieval and fallback flow. Incoming queries are embedded with the matching Qwen model and queried against pgvector using cosine distance, filtered by grade and subject. To handle free-tier hosting limits, I decided that if the fine-tuned hosted model endpoint (`NCERT_MODEL_URL`) is unreachable or unconfigured, the system must fall back to an extractive clue directly from the retrieved textbook passage and provide exact physical PDF page citations. I also kept database credentials isolated in environment variables.

## Prompts and responses

| Work | Prompt (as typed) | AI contribution and action taken |
|---|---|---|
| Backend inspection | `look at backend code, how can we hook up the ncert vectors i already loaded into supabase?` | Inspected `app/main.py`, `routers/`, and database models. Pointed out that existing endpoints used keyword course-pack search, and outlined an NCERT retrieval service connecting to Supabase via `pg8000`. |
| Scope enforcement | `is auto routing only done for class 7? i need it to work for all class 6 to 10 maths and science` | Checked the notebook pipeline outputs. Updated the SQL query parameters and schema filters to support multi-grade dynamic filtering (grades 6 to 10) and subject scoping (`maths`, `science`). |
| RAG implementation | `write the fastapi code to query supabase pgvector with the qwen embeddings and return citations` | Drafted `backend/app/services/ncert.py` with SQLAlchemy read-only transaction queries, pgvector cosine distance ranking (`<=>`), and deep-linked URL formatting (`#page=<physical_page>`). |
| Fallback design | `what if the hosted model url is down? make an extractive fallback that quotes the textbook passage` | Implemented `grounded()` in `app/services/socratic.py` with dual-mode generation: queries `NCERT_MODEL_URL` when available, otherwise pulls a 1-2 sentence excerpt from the textbook passage as a clue. |
| Test suite | `add pytest unit tests for ncert router, search, and citation fallback` | Created `backend/tests/test_ncert.py` with monkeypatched embedding and database fixtures. Verified chapter locking across turns, citation URLs, clarification probes on ambiguous queries, and 503 handling. |

## Reasoning I can substantiate in review

- Vector consistency: The backend query encoder must use the exact same tokenizer revision and pooling method (`Qwen/Qwen3-Embedding-0.6B`, revision `97b0c614`) as used during corpus indexing, or cosine similarity scores collapse.
- Extractive fallback over hallucination: When the external LLM is offline or times out, extracting a verified passage sentence ensures hints remain grounded in the official syllabus without fabricating facts or answer leaks.
- Deep-linked page citations: Formatting URLs with `#page=<physical_page>` lets learners and reviewers check retrieved evidence directly in the official NCERT PDF.
- Reserved Course ID: Protecting `"ncert"` in `routers/courses.py` prevents external POST requests from overwriting system textbook tables.

## Validation record

- Checked vector search queries against live database schema (`ncert_research.passages` with pgvector `<=>`).
- Tested query routing across Class 6 to 10 sample queries (such as Electricity and Linear Equations).
- Verified that direct answer requests trigger guardrail redirection (`guardrails.requests_answer`).
- Confirmed all unit tests in `backend/tests/test_ncert.py` pass cleanly offline.
- Kept connection strings and API keys out of repository files and logs.

**References:** `backend/app/services/ncert.py`, `backend/app/services/tutor.py`, `backend/app/services/socratic.py`, `backend/tests/test_ncert.py`.
