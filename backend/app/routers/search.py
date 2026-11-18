from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SearchHit
from ..services import ncert, retrieval

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchHit])
def search(course_id: str, q: str = Query(min_length=1, max_length=8000), k: int = Query(5, ge=1, le=20),
           grade: int | None = Query(default=None, ge=6, le=10),
           subject: Literal["maths", "science"] | None = None, book_code: str | None = None,
           chapter: int | None = None,
           db: Session = Depends(get_db)):
    """Find the textbook page, notes or lecture that explains a concept."""
    if course_id == ncert.COURSE_ID:
        return [SearchHit(concept_id=ncert.concept_id(row), score=row["score"], material=ncert.material(row),
                          chapter=ncert.chapter_of(row), passage_id=row["passage_id"])
                for row in ncert.rank(q, {key: value for key, value in (
                    ("grade", grade), ("subject", subject), ("book_code", book_code), ("chapter", chapter)
                ) if value is not None or key in {"grade", "subject"}}, limit=k)
                if row["score"] >= ncert.MIN_SCORE]
    return retrieval.search(db, course_id, q, k)
