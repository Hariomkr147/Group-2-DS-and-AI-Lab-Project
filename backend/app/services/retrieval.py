"""Search over course material.

Stub: keyword overlap (the BM25-style baseline). Replace with pgvector
embedding search; keep the function signatures.
"""
import re

from sqlalchemy.orm import Session

from ..schemas import SearchHit
from . import course_store

_STOP = {"the", "a", "an", "of", "is", "what", "how", "to", "in", "and", "do", "does", "i", "me", "my"}


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP}


def search(db: Session, course_id: str, query: str, k: int = 5) -> list[SearchHit]:
    q = _tokens(query)
    hits = []
    for c in course_store.get_pack(db, course_id).concepts:
        for m in c.materials:
            words = _tokens(m.text) | _tokens(c.name) | {c.id}
            if c.id.rstrip("s") in query.lower() or c.name.lower() in query.lower():
                words |= q
            score = len(q & words) / (len(q) or 1)
            if score > 0:
                hits.append(SearchHit(concept_id=c.id, score=round(score, 3), material=m))
    return sorted(hits, key=lambda h: h.score, reverse=True)[:k]


def best_concept(db: Session, course_id: str, query: str) -> str | None:
    q = query.lower()
    pack = course_store.get_pack(db, course_id)
    for c in pack.concepts:  # a concept named in the question wins
        if c.name.lower() in q or c.id in q or (c.id.endswith("s") and c.id[:-1] in q):
            return c.id
    if "%" in q:
        for c in pack.concepts:
            if c.id == "percentages":
                return c.id
    hits = search(db, course_id, query, k=1)
    return hits[0].concept_id if hits and hits[0].score >= 0.3 else None
