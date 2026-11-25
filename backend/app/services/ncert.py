"""Route and retrieve approved NCERT evidence in Supabase."""
import json
import logging
import os
import re
from functools import lru_cache
from pathlib import Path
from threading import Lock
from urllib.parse import urldefrag, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..db import engine
from ..schemas import Chapter, ChapterTopics, Material, Resource
from . import math_text

COURSE_ID = "ncert"
COURSE_TITLE = "NCERT Classes 6–10 · Maths and Science"
RELEASE = "3371af5f8052352316dad173"
MODEL = "Qwen/Qwen3-Embedding-0.6B"
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
QUERY_PREFIX = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "
EMBEDDING_DIMENSION = 1024
# shortcut: these scores come from a small routing benchmark, recalibrate on fresh student queries.
MIN_SCORE = 0.60
PREREQUISITE_MIN_SCORE = 0.45   # shortcut: passage-to-passage similarity; 0.55 found nothing (best match 0.497), not yet calibrated on the corpus
FOLLOWUP_MIN_SCORE = 0.35       # shortcut: message-to-active-passage similarity for follow-ups, not yet calibrated
CHAPTER_MARGIN = 0.025
GRAPH_COURSE_KEY = "ncert-class-6-10-maths-science"   # learning_graph run built over the whole corpus
log = logging.getLogger(__name__)
_info_log = logging.getLogger("uvicorn.error")  # info lines show under uvicorn; no app logging config exists
_encoder_lock = Lock()

_ELIGIBLE = """
        FROM ncert_research.passages p
        JOIN ncert_research.releases r USING (release_id)
        WHERE p.release_id = :release
          AND r.review_status = 'approved'
          AND r.embedding_model = :model AND r.embedding_revision = :revision
          AND p.review_status = 'approved'
          AND NOT p.review_flags && ARRAY['answer_risk', 'replacement_character']
          AND btrim(p.heading) !~* '^(ans(wer)?s?|solutions?)([.:[:space:]]|$)'
          AND btrim(p.heading) !~* '^(a note to the reader|preface|foreword|table of contents|acknowledg(e)?ments)$'
          AND length(btrim(regexp_replace(p.content, :image_pattern, '', 'g'))) >= 80
          AND (CAST(:grade AS smallint) IS NULL OR p.grade = :grade)
          AND (CAST(:subject AS text) IS NULL OR p.subject = :subject)
          AND (CAST(:book_code AS text) IS NULL OR p.book_code = :book_code)
          AND (CAST(:chapter AS integer) IS NULL OR p.chapter = :chapter)
"""
_CATALOGUE = text("""
    SELECT p.grade, p.subject, p.book_code, p.chapter,
           array_agg(DISTINCT p.heading ORDER BY p.heading) AS topics
""" + _ELIGIBLE + """
    GROUP BY p.grade, p.subject, p.book_code, p.chapter
    ORDER BY p.book_code, p.chapter
""")
_PASSAGE_FIELDS = """
    p.passage_id, p.grade, p.subject, p.book_code, p.chapter, p.heading,
    p.physical_page, p.source_url, p.content
"""
_TOPIC_PASSAGE = text("SELECT " + _PASSAGE_FIELDS + _ELIGIBLE + """
    AND p.heading = :heading
    ORDER BY p.physical_page, (position(p.heading in split_part(ltrim(p.content), chr(10), 1)) > 0) DESC,
             p.passage_id
    LIMIT :limit
""")
_BY_ID = text("SELECT " + _PASSAGE_FIELDS + _ELIGIBLE + " AND p.passage_id = :passage_id LIMIT 1")
_PASSAGES = text("""
    WITH eligible AS (
        SELECT """ + _PASSAGE_FIELDS + """,
               p.embedding <=> CAST(:embedding AS vector) AS distance
""" + _ELIGIBLE + """
    ), ranked AS (
        SELECT *, row_number() OVER (
            PARTITION BY grade, subject, book_code, chapter ORDER BY distance, passage_id
        ) AS position
        FROM eligible
    )
    SELECT *, 1 - distance AS score FROM ranked
    WHERE position <= :per_chapter
    ORDER BY distance, passage_id
    LIMIT :limit
""")
# Earlier topics (lower class, earlier chapter, or earlier in the same chapter) closest in meaning to one passage.
# Fallback when the learning graph has no concept for a topic: derived at run time from the stored embeddings.
_PREREQUISITES = text("""
    WITH eligible AS (
        SELECT """ + _PASSAGE_FIELDS + """,
               1 - (p.embedding <=> (SELECT c.embedding FROM ncert_research.passages c
                                     WHERE c.release_id = :release AND c.passage_id = :passage_id)) AS score
""" + _ELIGIBLE + """
          AND p.passage_id <> :passage_id
          AND p.heading <> :heading
          AND (p.grade, p.book_code, p.chapter, p.physical_page)
              < (CAST(:cur_grade AS smallint), CAST(:cur_book AS text), CAST(:cur_chapter AS integer),
                 CAST(:cur_page AS integer))
    ), ranked AS (
        SELECT *, row_number() OVER (PARTITION BY grade, book_code, chapter ORDER BY score DESC, passage_id) AS position
        FROM eligible
    )
    SELECT * FROM ranked WHERE position = 1 AND score >= :min_score
    ORDER BY score DESC, passage_id
    LIMIT :limit
""")
# Prerequisites from the learning graph (learning_graph schema, built from this release). The current topic's
# concepts are the graph nodes whose evidence quotes a chunk under the same heading; each approved edge into one of
# them names a prerequisite concept, and that concept's own evidence passages are the topics to step back to.
# Only topics before this one are offered: a lower class, another book of the same class, or earlier in this book.
# One row per topic, strongest edge first.
# The graph run to read: the newest whole-corpus run built from this release that has approved edges,
# or the run graph_run() names. Shared with ncert_graph.
GRAPH_RUN = """
    run AS (
        SELECT g.run_id FROM learning_graph.graph_runs g
        WHERE g.course_key = :course_key AND g.metadata->'source_scope'->>'release' = :release
          AND (CAST(:run_id AS text) IS NULL OR g.run_id = :run_id)
          AND EXISTS (SELECT 1 FROM learning_graph.prerequisite_edges e
                      WHERE e.run_id = g.run_id AND e.review_status = 'approved')
        ORDER BY g.created_at DESC
        LIMIT 1
    )"""
_GRAPH_PREREQUISITES = text("""
    WITH """ + GRAPH_RUN + """, here AS (
        SELECT DISTINCT n.concept_id, n.name
        FROM run JOIN learning_graph.graph_nodes n ON n.run_id = run.run_id
        CROSS JOIN LATERAL jsonb_array_elements(n.evidence) ev
        JOIN ncert_research.passages c ON c.release_id = :release AND c.passage_id = ev->>'source_id'
        WHERE c.book_code = :cur_book AND c.chapter = :cur_chapter AND c.heading = :heading
    ), needed AS (
        SELECT e.prerequisite_id, e.confidence, e.reason, h.name AS for_concept
        FROM run JOIN learning_graph.prerequisite_edges e ON e.run_id = run.run_id
        JOIN here h ON h.concept_id = e.concept_id
        WHERE e.review_status = 'approved'
          AND e.prerequisite_id NOT IN (SELECT concept_id FROM here)
    ), sources AS (
        SELECT n.concept_id, n.name AS concept, d.reason, d.for_concept, d.confidence, ev->>'source_id' AS passage_id
        FROM needed d
        JOIN run ON true
        JOIN learning_graph.graph_nodes n ON n.run_id = run.run_id AND n.concept_id = d.prerequisite_id
        CROSS JOIN LATERAL jsonb_array_elements(n.evidence) ev
    ), eligible AS (
        SELECT """ + _PASSAGE_FIELDS + _ELIGIBLE + """
          AND p.passage_id IN (SELECT passage_id FROM sources)
          AND (p.grade < CAST(:cur_grade AS smallint)          -- a lower class, or the same class in another book,
               OR (p.grade = CAST(:cur_grade AS smallint)      -- or earlier in this book: never a later chapter
                   AND (p.book_code <> :cur_book
                        OR (p.chapter, p.physical_page) <= (CAST(:cur_chapter AS integer), CAST(:cur_page AS integer)))))
          AND NOT (p.book_code = :cur_book AND p.chapter = :cur_chapter AND p.heading = :heading)
    ), per_concept AS (      -- one topic per prerequisite concept: a teaching section before a summary or exercise
        SELECT p.*, s.concept_id, s.concept, s.reason, s.for_concept, s.confidence AS score,
               row_number() OVER (PARTITION BY s.concept_id
                                  ORDER BY s.confidence DESC,
                                           p.heading ~* '(summary|exercise|what have we (discussed|learnt))',
                                           p.physical_page, p.passage_id) AS position
        FROM sources s JOIN eligible p ON p.passage_id = s.passage_id
    ), per_topic AS (
        SELECT *, row_number() OVER (PARTITION BY book_code, chapter, heading
                                     ORDER BY score DESC, passage_id) AS topic_position
        FROM per_concept WHERE position = 1
    )
    SELECT * FROM per_topic WHERE topic_position = 1
    ORDER BY score DESC, grade, book_code, chapter, physical_page, passage_id
    LIMIT :limit
""")
_SIMILARITY = text("""
    SELECT 1 - (p.embedding <=> CAST(:embedding AS vector)) AS score
""" + _ELIGIBLE + """
    AND p.passage_id = :passage_id
""")
_IMAGE = r"!\[[^]]*\]\([^)]*\)"
# Titles follow the indexed PDFs in the corpus inventory.
_CHAPTER_TITLES = json.loads(Path(__file__).with_name("ncert_chapter_titles.json").read_text(encoding="utf-8"))


def configured() -> bool:
    # The corpus lives in the ncert_research schema of the app's own DATABASE_URL database.
    return os.getenv("NCERT_ENABLED", "").lower() in ("1", "true", "yes")


@lru_cache(maxsize=1)
def _encoder():
    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, padding_side="left")
    model = AutoModel.from_pretrained(MODEL, revision=REVISION, use_safetensors=True).eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device)
    model.config.use_cache = False
    return tokenizer, model, device


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _remote_embedding(query: str, url: str, key: str) -> list[float]:
    target = urlsplit(url)
    if (target.scheme != "https" or not target.hostname or target.username is not None
            or target.password is not None or target.query or target.fragment
            or not re.fullmatch(r"[!-~]{1,512}", key)):
        raise ValueError("Configure a valid NCERT embedding HTTPS URL and API key.")

    request = Request(f"{url.rstrip('/')}/embed", data=json.dumps({"query": query}).encode(),
                      headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"})
    with build_opener(_NoRedirect()).open(request, timeout=25) as response:
        result = json.loads(response.read(65536))
    if not isinstance(result, dict) or result.get("model") != MODEL or result.get("revision") != REVISION:
        raise ValueError("The NCERT embedding model does not match the corpus.")
    vector = result.get("embedding")
    if (not isinstance(vector, list) or len(vector) != EMBEDDING_DIMENSION
            or any(type(value) not in (int, float) or not -1 <= value <= 1 for value in vector)
            or abs(sum(value * value for value in vector) - 1) > 0.001):
        raise ValueError("The NCERT embedding vector is invalid.")
    return vector


def embed(query: str) -> list[float]:
    url = os.getenv("NCERT_EMBEDDING_URL", "").strip()
    key = os.getenv("NCERT_EMBEDDING_API_KEY", "")
    if url or key or os.getenv("APP_ENV", "").strip().lower() == "production":
        return _remote_embedding(query, url, key)

    import torch

    with _encoder_lock:
        tokenizer, model, device = _encoder()
    inputs = tokenizer(QUERY_PREFIX + query, truncation=True, max_length=2048,
                       return_tensors="pt").to(device)
    with torch.inference_mode():
        hidden = model(**inputs).last_hidden_state[:, -1].float()
        return torch.nn.functional.normalize(hidden, dim=1)[0].tolist()


def _query(statement, scope: dict, **extra) -> list[dict]:
    if not configured():
        raise HTTPException(503, "NCERT retrieval is not configured.")
    params = {key: scope.get(key) for key in ("grade", "subject", "book_code", "chapter")}
    params.update(release=RELEASE, revision=REVISION, model=MODEL, image_pattern=_IMAGE, **extra)
    try:
        with engine.begin() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '12s'"))
            conn.execute(text("SET LOCAL search_path = pg_catalog, extensions, public"))
            return [dict(row) for row in conn.execute(statement, params).mappings()]
    except (SQLAlchemyError, OSError, ValueError) as error:
        log.warning("NCERT database unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "The NCERT evidence database is unavailable.") from None


def catalogue(grade: int, subject: str) -> list[ChapterTopics]:
    chapters = _query(_CATALOGUE, {"grade": grade, "subject": subject})
    for chapter in chapters:
        chapter["title"] = _CHAPTER_TITLES.get(chapter["book_code"], {}).get(str(chapter["chapter"]))
    return [ChapterTopics.model_validate(chapter) for chapter in chapters]


def topic_passage(scope: dict, heading: str) -> dict | None:
    if any(scope.get(field) is None for field in ("grade", "subject", "book_code", "chapter")):
        return None
    limit = _topic_passage_limit()
    rows = _query(_TOPIC_PASSAGE, scope, heading=heading, limit=limit)
    log.warning("topic_passage SQL (%d rows):\n%s;", len(rows), _runnable_sql(_TOPIC_PASSAGE, scope, heading=heading, limit=limit))
    if not rows:
        return None
    # The first chunk opens the topic and keeps its id, page and link; later chunks extend its text.
    return {**rows[0], "content": "\n\n".join(row["content"] for row in rows)}


def _runnable_sql(statement, scope: dict, **extra) -> str:
    """Debug aid: the statement with its values inlined, ready to paste into the SQL editor."""
    params = {key: scope.get(key) for key in ("grade", "subject", "book_code", "chapter")}
    params.update(release=RELEASE, revision=REVISION, model=MODEL, image_pattern=_IMAGE, **extra)
    return str(statement.bindparams(**params).compile(dialect=engine.dialect, compile_kwargs={"literal_binds": True}))


def _topic_passage_limit() -> int:
    """How many chunks of one topic to teach from (NCERT_TOPIC_PASSAGES, default 5)."""
    try:
        return max(1, int(os.getenv("NCERT_TOPIC_PASSAGES", "5")))
    except ValueError:
        return 5


def chapter_title(scope: dict) -> str:
    return _CHAPTER_TITLES.get(scope.get("book_code"), {}).get(str(scope.get("chapter")), "") or ""


def topic_title(heading: str) -> str:
    return math_text.readable(re.sub(r"^\s*\d+(?:\.\d+)+\.?\s+", "", heading)).strip()


def cited_passage(chapter: dict, passage_id: str) -> dict | None:
    rows = _query(_BY_ID, chapter, passage_id=passage_id)
    return rows[0] if rows else None


def rank(query: str, scope: dict, limit: int = 5, *, chapters: bool = False) -> list[dict]:
    if not configured():
        raise HTTPException(503, "NCERT retrieval is not configured.")
    try:
        vector = embed(query)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        log.warning("NCERT encoder unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "The NCERT question encoder is unavailable.") from None
    return _query(_PASSAGES, scope, embedding=str(vector), limit=limit,
                  per_chapter=1 if chapters else limit)


def similarity(query: str, chapter: dict, passage_id: str) -> float:
    """Cosine similarity between a message and one passage (0.0 if the passage is not found)."""
    if not configured():
        raise HTTPException(503, "NCERT retrieval is not configured.")
    try:
        vector = embed(query)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        log.warning("NCERT encoder unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "The NCERT question encoder is unavailable.") from None
    rows = _query(_SIMILARITY, chapter, embedding=str(vector), passage_id=passage_id)
    return float(rows[0]["score"]) if rows else 0.0


def graph_enabled() -> bool:
    """The teammate-built prerequisite graph is used unless NCERT_GRAPH=0."""
    return os.getenv("NCERT_GRAPH", "1").strip().lower() not in ("0", "false", "no", "off")


def graph_run() -> str | None:
    """The run NCERT_GRAPH_RUN pins (None: the newest approved run)."""
    return os.getenv("NCERT_GRAPH_RUN", "").strip() or None


def graph_prerequisites(row: dict, limit: int = 2) -> list[dict]:
    """Topics holding the approved graph prerequisites of this passage's concepts. Rows add concept, for_concept,
    reason and score (edge confidence). [] when the topic has no graph concepts or the graph tables are missing."""
    params = dict(course_key=GRAPH_COURSE_KEY, run_id=graph_run(), heading=row["heading"],
                  cur_grade=row["grade"], cur_book=row["book_code"], cur_chapter=row["chapter"],
                  cur_page=row["physical_page"], limit=limit)
    try:
        rows = _query(_GRAPH_PREREQUISITES, {}, **params)
    except HTTPException:
        log.warning("graph_prerequisites SQL failed for %r:\n%s;", row["heading"],
                    _runnable_sql(_GRAPH_PREREQUISITES, {}, **params))
        return []
    _info_log.info("graph_prerequisites SQL (%d rows) for %r:\n%s;", len(rows), row["heading"],
                   _runnable_sql(_GRAPH_PREREQUISITES, {}, **params))
    found = [{**r, "source": "graph"} for r in rows]
    _log_picked(row, found)
    return found


def _log_picked(row: dict, found: list[dict]) -> None:
    """Debug aid: the prerequisite topics picked for one topic, one line each."""
    lines = [f"  [{r['source']}] Class {r['grade']} {r['book_code']} ch {r['chapter']} p {r['physical_page']} "
             f"{r['heading']!r} score={float(r['score']):.3f}"
             + (f" concept={r.get('concept')!r} for={r.get('for_concept')!r}" if r["source"] == "graph" else "")
             for r in found]
    _info_log.info("prerequisites picked for %r: %d topic(s)%s", row["heading"], len(found),
                   "".join("\n" + line for line in lines))


def prerequisites(row: dict, limit: int = 2) -> list[dict]:
    """Topics this passage builds on. The learning graph is asked first; when it has nothing for this topic, fall
    back to earlier topics of the same subject nearest in meaning (embeddings). [] when neither finds one."""
    if graph_enabled():
        found = graph_prerequisites(row, limit)
        if found:
            return found
    else:
        _info_log.info("prerequisites: learning graph off (NCERT_GRAPH=0), using embeddings")
    scope = {"subject": row["subject"]}
    params = dict(passage_id=row["passage_id"], heading=row["heading"],
                  cur_grade=row["grade"], cur_book=row["book_code"], cur_chapter=row["chapter"],
                  cur_page=row["physical_page"], min_score=PREREQUISITE_MIN_SCORE, limit=limit)
    rows = _query(_PREREQUISITES, scope, **params)
    _info_log.info("embedding prerequisites SQL (%d rows) for %r:\n%s;", len(rows), row["heading"],
                   _runnable_sql(_PREREQUISITES, scope, **params))
    found = [{**r, "source": "embedding"} for r in rows]
    _log_picked(row, found)
    return found


def chapter_of(row: dict) -> Chapter:
    return Chapter.model_validate(row)


def concept_id(row: dict) -> str:
    return f"{row['grade']}-{row['subject']}-{row['book_code']}-{row['chapter']}"


def passage_text(row: dict) -> str:
    return math_text.readable(re.sub(_IMAGE, "", row["content"])).strip()


def resource(row: dict) -> Resource:
    url, _ = urldefrag(row["source_url"])
    if urlsplit(url).scheme == "https":
        url = f"{url}#page={row['physical_page']}"
    else:
        url = ""
    subject = "Maths" if row["subject"] == "maths" else "Science"
    return Resource(source=f"NCERT Class {row['grade']} {subject}, Chapter {row['chapter']} · {math_text.readable(row['heading'])}",
                    page=str(row["physical_page"]), url=url, passage_id=row["passage_id"])


def material(row: dict) -> Material:
    citation = resource(row)
    return Material(source=citation.source, page=citation.page, url=citation.url, text=passage_text(row))
