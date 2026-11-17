"""Route and retrieve approved NCERT evidence in Supabase."""
import logging
import os
import re
from functools import lru_cache
from threading import Lock
from urllib.parse import urldefrag, urlsplit

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..db import engine
from ..schemas import Chapter, Material, Resource

COURSE_ID = "ncert"
COURSE_TITLE = "NCERT Classes 6–10 · Maths and Science"
RELEASE = "9aea0ce28990f86074b2d813"
MODEL = "Qwen/Qwen3-Embedding-0.6B"
REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
QUERY_PREFIX = "Instruct: Given a question, retrieve relevant passages that answer the question\nQuery: "
# shortcut: these scores come from a small routing benchmark, recalibrate on fresh student queries.
MIN_SCORE = 0.60
CHAPTER_MARGIN = 0.025
log = logging.getLogger(__name__)
_encoder_lock = Lock()

_PASSAGES = text("""
    WITH eligible AS (
        SELECT p.passage_id, p.grade, p.subject, p.book_code, p.chapter, p.heading,
               p.physical_page, p.source_url, p.content,
               p.embedding <=> CAST(:embedding AS vector) AS distance
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


def embed(query: str) -> list[float]:
    import torch

    with _encoder_lock:
        tokenizer, model, device = _encoder()
    inputs = tokenizer(QUERY_PREFIX + query, truncation=True, max_length=2048,
                       return_tensors="pt").to(device)
    with torch.inference_mode():
        hidden = model(**inputs).last_hidden_state[:, -1].float()
        return torch.nn.functional.normalize(hidden, dim=1)[0].tolist()


def rank(query: str, scope: dict, limit: int = 5, *, chapters: bool = False) -> list[dict]:
    if not configured():
        raise HTTPException(503, "NCERT retrieval is not configured.")
    try:
        vector = embed(query)
    except (ImportError, OSError, RuntimeError, ValueError) as error:
        log.warning("NCERT encoder unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "The NCERT question encoder is unavailable.") from None

    params = {key: scope.get(key) for key in ("grade", "subject", "book_code", "chapter")}
    params.update(embedding=str(vector), release=RELEASE, revision=REVISION, model=MODEL,
                  image_pattern=_IMAGE, per_chapter=1 if chapters else limit, limit=limit)
    try:
        with engine.begin() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            conn.execute(text("SET LOCAL statement_timeout = '12s'"))
            conn.execute(text("SET LOCAL search_path = pg_catalog, extensions, public"))
            return [dict(row) for row in conn.execute(_PASSAGES, params).mappings()]
    except (SQLAlchemyError, OSError, ValueError) as error:
        log.warning("NCERT database unavailable (%s)", type(error).__name__)
        raise HTTPException(503, "The NCERT evidence database is unavailable.") from None


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
