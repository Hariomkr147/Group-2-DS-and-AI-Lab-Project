"""One learner's view of the NCERT learning graph: their mastery on every concept and what to learn next.

Status of a concept, from learner_model.concept_mastery (answers linked to the concept, or AKT where it has a skill):
  mastered    readiness at or above MASTERED
  learning    readiness between controller.WEAK and MASTERED
  struggling  readiness below controller.WEAK
  ready       no evidence yet, and every prerequisite in the graph is mastered (needs at least one prerequisite)
  unseen      no evidence yet, otherwise
`next` lists the ready concepts in textbook order; `review` the struggling ones, weakest first.
In a scoped graph, prerequisites brought in from outside the scope show no prerequisites of their own, so they
are never `ready`.
"""
from sqlalchemy.orm import Session

from ..schemas import LearnerConcept, LearnerGraph
from . import controller, learner_model, ncert, ncert_graph

MASTERED = 0.8     # smoothed accuracy reaches it after 3 right of 3: (3 + 1) / (3 + 2)
LIST_LIMIT = 10


def _status(p: float | None) -> str:
    if p is None:
        return "unseen"
    if p >= MASTERED:
        return "mastered"
    return "struggling" if p < controller.WEAK else "learning"


def learner_graph(db: Session, learner_id: str, scope: dict) -> LearnerGraph:
    graph = ncert_graph.learning_graph(scope)
    mastery = learner_model.concept_mastery(db, learner_id, ncert.COURSE_ID, [n.id for n in graph.nodes])
    status = {n.id: _status(mastery[n.id][0]) for n in graph.nodes}
    for n in graph.nodes:
        if status[n.id] == "unseen" and n.prerequisites and all(status.get(p) == "mastered" for p in n.prerequisites):
            status[n.id] = "ready"
    nodes = []
    for n in graph.nodes:
        p, source, attempts, correct = mastery[n.id]
        nodes.append(LearnerConcept(
            id=n.id, name=n.name, level=n.level, grade=n.grade, subject=n.subject, book_code=n.book_code,
            chapter=n.chapter, prerequisites=n.prerequisites, status=status[n.id],
            readiness=None if p is None else round(p, 3), source=source, attempts=attempts, correct=correct))
    order = {n.id: (n.grade or 99, n.book_code or "", n.chapter or 0, n.level, n.name) for n in graph.nodes}
    ready = sorted((n.id for n in nodes if n.status == "ready"), key=order.__getitem__)
    review = sorted((n for n in nodes if n.status == "struggling"), key=lambda n: (n.readiness, order[n.id]))
    counts = {s: 0 for s in ("mastered", "learning", "struggling", "ready", "unseen")}
    for s in status.values():
        counts[s] += 1
    return LearnerGraph(learner_id=learner_id, course_id=ncert.COURSE_ID, run_id=graph.run_id, nodes=nodes,
                        edges=graph.edges, next=ready[:LIST_LIMIT], review=[n.id for n in review][:LIST_LIMIT],
                        counts=counts)
