"""Route and retrieve approved NCERT evidence in Supabase."""
import json
import logging
import os
import re
from functools import lru_cache
from threading import Lock
from urllib.parse import urldefrag, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..db import engine
from ..schemas import Chapter, ChapterTopics, Material, Resource

COURSE_ID = "ncert"
COURSE_TITLE = "NCERT Classes 6–10 · Maths and Science"
RELEASE = "9aea0ce28990f86074b2d813"
MODEL = "Qwen/Qwen3-Embedding-0.6B"
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
QUERY_PREFIX = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "
EMBEDDING_DIMENSION = 1024
# shortcut: these scores come from a small routing benchmark, recalibrate on fresh student queries.
MIN_SCORE = 0.60
CHAPTER_MARGIN = 0.025
log = logging.getLogger(__name__)
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
_PASSAGES = text("""
    WITH eligible AS (
        SELECT p.passage_id, p.grade, p.subject, p.book_code, p.chapter, p.heading,
               p.physical_page, p.source_url, p.content,
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
_IMAGE = r"!\[[^]]*\]\([^)]*\)"


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
    return [ChapterTopics.model_validate(row)
            for row in _query(_CATALOGUE, {"grade": grade, "subject": subject})]


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


def chapter_of(row: dict) -> Chapter:
    return Chapter.model_validate(row)


def concept_id(row: dict) -> str:
    return f"{row['grade']}-{row['subject']}-{row['book_code']}-{row['chapter']}"


def passage_text(row: dict) -> str:
    return re.sub(_IMAGE, "", row["content"]).strip()


def resource(row: dict) -> Resource:
    url, _ = urldefrag(row["source_url"])
    if urlsplit(url).scheme == "https":
        url = f"{url}#page={row['physical_page']}"
    else:
        url = ""
    subject = "Maths" if row["subject"] == "maths" else "Science"
    return Resource(source=f"NCERT Class {row['grade']} {subject}, Chapter {row['chapter']} · {row['heading']}",
                    page=str(row["physical_page"]), url=url, passage_id=row["passage_id"])


def material(row: dict) -> Material:
    citation = resource(row)
    return Material(source=citation.source, page=citation.page, url=citation.url, text=passage_text(row))
