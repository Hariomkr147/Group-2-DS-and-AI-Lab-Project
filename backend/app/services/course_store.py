"""Course pack access and the cross-level prerequisite graph."""
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db import ConceptRow, CourseRow
from ..schemas import Concept, CourseGraph, CoursePack, CourseSummary, GraphEdge


def _concept(row: ConceptRow) -> Concept:
    return Concept(id=row.id, name=row.name, level=row.level, prerequisites=row.prerequisites,
                   materials=row.materials, questions=row.questions)


def add_pack(db: Session, pack: CoursePack) -> CoursePack:
    """Insert a course pack, replacing an existing one with the same id."""
    ids = {c.id for c in pack.concepts}
    for c in pack.concepts:
        missing = [p for p in c.prerequisites if p not in ids]
        if missing:
            raise HTTPException(422, f"{c.id}: unknown prerequisites {missing}")
    db.execute(delete(ConceptRow).where(ConceptRow.course_id == pack.id))
    db.merge(CourseRow(id=pack.id, title=pack.title, subject=pack.subject))
    db.flush()  # the course row must exist before its concepts (foreign key)
    db.add_all(ConceptRow(course_id=pack.id, **c.model_dump()) for c in pack.concepts)
    db.commit()
    return pack


def get_pack(db: Session, course_id: str) -> CoursePack:
    course = db.get(CourseRow, course_id)
    if course is None:
        raise HTTPException(404, f"course '{course_id}' not found")
    rows = db.scalars(select(ConceptRow).where(ConceptRow.course_id == course_id)
                      .order_by(ConceptRow.level, ConceptRow.id)).all()
    return CoursePack(id=course.id, title=course.title, subject=course.subject,
                      concepts=[_concept(r) for r in rows])


def get_concept(db: Session, course_id: str, concept_id: str) -> Concept:
    row = db.get(ConceptRow, (course_id, concept_id))
    if row is None:
        get_pack(db, course_id)  # 404 for an unknown course
        raise HTTPException(404, f"concept '{concept_id}' not found in '{course_id}'")
    return _concept(row)


def list_courses(db: Session) -> list[CourseSummary]:
    out = []
    for c in db.scalars(select(CourseRow).order_by(CourseRow.id)):
        n = len(db.scalars(select(ConceptRow.id).where(ConceptRow.course_id == c.id)).all())
        out.append(CourseSummary(id=c.id, title=c.title, subject=c.subject, concept_count=n))
    return out


def graph(db: Session, course_id: str) -> CourseGraph:
    pack = get_pack(db, course_id)
    edges = [GraphEdge(prerequisite=p, concept=c.id) for c in pack.concepts for p in c.prerequisites]
    return CourseGraph(course_id=course_id, nodes=pack.concepts, edges=edges)
