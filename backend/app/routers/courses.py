from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import ChapterTopics, ConceptPublic, CourseGraph, CoursePack, CourseSummary
from ..services import course_store, ncert

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseSummary])
def list_courses(db: Session = Depends(get_db)):
    return [c for c in course_store.list_courses(db) if c.id != ncert.COURSE_ID or ncert.configured()]


@router.get("/ncert/chapters", response_model=list[ChapterTopics])
def list_chapters(grade: int = Query(ge=6, le=10), subject: Literal["maths", "science"] = Query()):
    return ncert.catalogue(grade, subject)


@router.post("", response_model=CourseSummary, status_code=201)
def ingest_course(pack: CoursePack, db: Session = Depends(get_db)):
    """Ingest a course pack (concepts, prerequisite links, material, questions); replaces a pack with the same id."""
    if pack.id == ncert.COURSE_ID:
        raise HTTPException(422, "This course ID is reserved for the NCERT corpus.")
    p = course_store.add_pack(db, pack)
    return CourseSummary(id=p.id, title=p.title, subject=p.subject, concept_count=len(p.concepts))


@router.get("/{course_id}/concepts", response_model=list[ConceptPublic])  # no answer key
def list_concepts(course_id: str, db: Session = Depends(get_db)):
    return course_store.get_pack(db, course_id).concepts


@router.get("/{course_id}/graph", response_model=CourseGraph)
def get_graph(course_id: str, db: Session = Depends(get_db)):
    return course_store.graph(db, course_id)
