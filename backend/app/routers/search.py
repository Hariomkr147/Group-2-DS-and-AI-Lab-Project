from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import SearchHit
from ..services import retrieval

router = APIRouter(tags=["search"])


@router.get("/search", response_model=list[SearchHit])
def search(course_id: str, q: str = Query(min_length=1), k: int = Query(5, ge=1, le=20),
           db: Session = Depends(get_db)):
    """Find the textbook page, notes or lecture that explains a concept."""
    return retrieval.search(db, course_id, q, k)
