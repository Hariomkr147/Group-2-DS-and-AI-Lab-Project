# Backend review and NCERT RAG (2026-11-13)

**Contributor:** Hariom Kumar  
**Context:** NCERT Classes 6 to 10 textbook content previously extracted, chunked, and stored in Supabase with pgvector.

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex
- **Purpose of Use:** Codebase inspection, FastAPI route wiring, SQL vector query syntax, and pytest fixture drafting.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I directed the integration architecture, set multi-grade requirements, and designed the fallback flow. The AI was used for syntax scaffolding and test generation. All SQL queries, SQLAlchemy models, and API responses were manually verified against local database fixtures and unit tests.

## 2. My Contribution and Independent Engineering

I directed the integration of our pre-extracted NCERT textbook dataset into the FastAPI backend:
1. Database integration: Provided the connection structure for the Supabase Postgres instance where `Qwen/Qwen3-Embedding-0.6B` embeddings were stored.
2. Multi-grade scope enforcement: When initial code drafts defaulted to a single-grade demonstration, I required full support for Classes 6 to 10 across both Mathematics and Science.
3. Fallback and citation flow: Designed the dual-mode retrieval flow. Incoming queries are embedded with the matching Qwen model and matched via pgvector cosine distance. If the fine-tuned model endpoint (`NCERT_MODEL_URL`) is offline, the system falls back to an extractive clue taken directly from the retrieved textbook passage with deep-linked physical PDF page citations.
4. Security: Kept all database credentials and API keys in environment variables, ensuring zero secrets in repository code or logs.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Backend inspection | `look at backend code, how can we hook up the ncert vectors i already loaded into supabase?` | Outlined service structure connecting Supabase via `pg8000` alongside existing course pack routes. | Designed `backend/app/services/ncert.py` to handle read-only pgvector queries without disrupting course pack tables. |
| Scope enforcement | `is auto routing only done for class 7? i need it to work for all class 6 to 10 maths and science` | Identified single-grade filters in initial query draft. | Updated SQL schema filters and parameters to support multi-grade dynamic filtering (Classes 6 to 10) and subject scoping. |
| RAG implementation | `write the fastapi code to query supabase pgvector with the qwen embeddings and return citations` | Drafted SQLAlchemy queries with cosine distance operator (`<=>`). | Refined query to include deep-linked PDF URLs (`#page=<physical_page>`) and relevance thresholding. |
| Fallback design | `what if the hosted model url is down? make an extractive fallback that quotes the textbook passage` | Drafted dual-mode generation logic in `app/services/socratic.py`. | Tested fallback path: extracts verified 1-2 sentence clues from retrieved textbook passages when external LLMs time out. |
| Test suite | `add pytest unit tests for ncert router, search, and citation fallback` | Created parameterized pytest fixtures with monkeypatched embeddings. | Executed and validated all unit tests in `backend/tests/test_ncert.py`, verifying chapter locking, citation URLs, and 503 handling. |

## 4. Reasoning I Can Substantiate in Review

- Vector consistency: The backend query encoder must use the exact same tokenizer revision and pooling method (`Qwen/Qwen3-Embedding-0.6B`, revision `97b0c614`) as used during corpus indexing, or cosine similarity scores collapse.
- Extractive fallback over hallucination: When the external LLM is offline or times out, extracting a verified passage sentence ensures hints remain grounded in the official syllabus without fabricating facts or answer leaks.
- Deep-linked page citations: Formatting URLs with `#page=<physical_page>` lets learners and reviewers check retrieved evidence directly in the official NCERT PDF.
- Reserved Course ID: Protecting `"ncert"` in `routers/courses.py` prevents external POST requests from overwriting system textbook tables.

## 5. Validation Record

- Checked vector search queries against live database schema (`ncert_research.passages` with pgvector `<=>`).
- Tested query routing across Class 6 to 10 sample queries (such as Electricity and Linear Equations).
- Verified that direct answer requests trigger guardrail redirection (`guardrails.requests_answer`).
- Confirmed all unit tests in `backend/tests/test_ncert.py` pass cleanly offline.
- Kept connection strings and API keys out of repository files and logs.

## 6. Team Accountability Declaration

- All AI-assisted code, queries, and test fixtures incorporated into this stage have been reviewed and appropriately validated by me.
- Architectural decisions, retrieval logic, and fallback strategies are supported by my independent reasoning and experimental verification.
- I understand all contributions and can explain and defend the relevant work independently during review and assessment.

**References:** `backend/app/services/ncert.py`, `backend/app/services/tutor.py`, `backend/app/services/socratic.py`, `backend/tests/test_ncert.py`.
