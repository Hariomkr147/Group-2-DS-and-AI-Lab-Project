from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import Concept, CourseGraph, CoursePack, CourseSummary
from ..services import course_store

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)):
    return course_store.list_courses(db)


@router.post("", response_model=CourseSummary, status_code=201)
def ingest_course(pack: CoursePack, db: Session = Depends(get_db)):
    """Ingest a course pack (concepts, prerequisite links, material, questions); replaces a pack with the same id."""
    p = course_store.add_pack(db, pack)
    return CourseSummary(id=p.id, title=p.title, subject=p.subject, concept_count=len(p.concepts))


@router.get("/{course_id}/concepts", response_model=list[Concept])
def list_concepts(course_id: str, db: Session = Depends(get_db)):
    return course_store.get_pack(db, course_id).concepts


@router.get("/{course_id}/graph", response_model=CourseGraph)
def get_graph(course_id: str, db: Session = Depends(get_db)):
    return course_store.graph(db, course_id)
