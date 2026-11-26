"""Local browser fixture with a temporary database and approved-looking test passages."""
import os
from pathlib import Path
from secrets import token_urlsafe
from tempfile import TemporaryDirectory

import uvicorn


with TemporaryDirectory() as directory:
    os.environ.update(
        DATABASE_URL=f"sqlite:///{(Path(directory) / 'browser.db').as_posix()}",
        ADMIN_USERNAME="browser-tester",
        ADMIN_PASSWORD="browser-test-fixture",
        SECRET_KEY=token_urlsafe(32),
        APP_ENV="development",
        SOCRATIC_PROVIDER="templates",
        STEP_FINDER_PROVIDER="none",
        NCERT_ENABLED="1",
        NCERT_MODEL_URL="",
    )
    from app.main import app
    from app.services import ncert

    chapter = {"grade": 10, "subject": "science", "book_code": "jesc1", "chapter": 11}
    passage = {**chapter, "passage_id": "fixture-current", "heading": "Electric current", "physical_page": 8,
               "source_url": "https://ncert.nic.in/textbook/pdf/jesc111.pdf",
               "content": "Electric current measures the flow of electric charge through a conductor.",
               "score": 0.9}

    def catalogue(grade, subject):
        return [{**chapter, "title": "Electricity", "topics": [passage["heading"]]}] if (grade, subject) == (10, "science") else []

    def rank(query, scope, **options):
        return [passage] if all(scope.get(key) in (None, value) for key, value in chapter.items()) else []

    ncert.catalogue = catalogue
    ncert.rank = rank
    ncert.topic_passage = lambda scope, heading: passage if scope == chapter and heading == passage["heading"] else None
    ncert.cited_passage = lambda scope, pid: passage if scope == chapter and pid == passage["passage_id"] else None

    # A tiny learning graph and fixed mastery for the "What to study" panel: charge is mastered, so current is
    # ready to learn; resistance is weak, so it is worth reviewing.
    from app.schemas import GraphConcept, LearningGraph, LearningGraphEdge
    from app.services import learner_model, ncert_graph

    def concept(cid, name, prerequisites=()):
        return GraphConcept(id=cid, name=name, level=1, prerequisites=list(prerequisites), **chapter)

    ncert_graph.learning_graph = lambda scope: LearningGraph(
        course_id="ncert", run_id="fixture-run",
        nodes=[concept("charge", "Electric charge"), concept("current", "Electric current", ["charge"]),
               concept("resistance", "Resistance")],
        edges=[LearningGraphEdge(prerequisite="charge", concept="current", confidence=0.9)])
    ncert.concept_passage = lambda cid: {**passage, "concept": "Electric current"} if cid == "current" else None
    mastery = {"charge": (0.8, "accuracy", 3, 3), "resistance": (0.25, "accuracy", 2, 0)}
    learner_model.concept_mastery = lambda db, learner, course, ids: {
        cid: mastery.get(cid, (None, None, 0, 0)) for cid in ids}
    uvicorn.run(app, host="127.0.0.1", port=8766)
