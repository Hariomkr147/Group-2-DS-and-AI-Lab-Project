"""The NCERT learning graph (learning_graph schema) as a course graph: concepts, approved prerequisite edges,
and the NCERT passages each one is quoted from.

A concept belongs to a chapter when any of its evidence quotes comes from that chapter. A scoped graph holds the
concepts of the scope plus their direct prerequisites (which may sit in earlier chapters or classes), and the edges
into the scoped concepts.
"""
import re

from fastapi import HTTPException
from sqlalchemy import text

from ..schemas import GraphConcept, LearningGraph, LearningGraphEdge, Material
from . import math_text, ncert

_FIELDS = ("grade", "subject", "book_code", "chapter")
_CITED = """
    p.passage_id, p.grade, p.subject, p.book_code, p.chapter, p.heading, p.physical_page, p.source_url
"""
_NODES = text("WITH " + ncert.GRAPH_RUN + """
    SELECT run.run_id, n.concept_id, n.name, n.description, n.level, ev.position,
           ev.value->>'quote' AS quote, ev.value->>'source_ref' AS source_ref, """ + _CITED + """
    FROM run JOIN learning_graph.graph_nodes n ON n.run_id = run.run_id
    CROSS JOIN LATERAL jsonb_array_elements(n.evidence) WITH ORDINALITY AS ev(value, position)
    LEFT JOIN ncert_research.passages p ON p.release_id = :release AND p.passage_id = ev.value->>'source_id'
    ORDER BY n.level, n.name, n.concept_id, ev.position
""")
_EDGES = text("""
    SELECT e.prerequisite_id, e.concept_id, e.confidence, e.reason,
           e.evidence->>'quote' AS quote, e.evidence->>'source_ref' AS source_ref, """ + _CITED + """
    FROM learning_graph.prerequisite_edges e
    LEFT JOIN ncert_research.passages p ON p.release_id = :release AND p.passage_id = e.evidence->>'source_id'
    WHERE e.run_id = :run_id AND e.review_status = 'approved'
    ORDER BY e.concept_id, e.confidence DESC, e.prerequisite_id
""")


def _evidence(row: dict) -> Material | None:
    quote = math_text.readable(re.sub(ncert._IMAGE, "", row.get("quote") or "")).strip()
    if not quote:
        return None
    if row.get("passage_id"):
        cited = ncert.resource(row)
        return Material(source=cited.source, page=cited.page, url=cited.url, text=quote)
    return Material(source=row.get("source_ref") or "NCERT", text=quote)


def _in_scope(row: dict, scope: dict) -> bool:
    return row.get("passage_id") is not None and all(scope[f] is None or row[f] == scope[f] for f in _FIELDS)


def learning_graph(scope: dict) -> LearningGraph:
    """The latest approved graph run, optionally narrowed to a class, subject, book or chapter."""
    scope = {f: scope.get(f) for f in _FIELDS}
    rows = ncert._query(_NODES, {}, course_key=ncert.GRAPH_COURSE_KEY, run_id=ncert.graph_run())
    if not rows:
        raise HTTPException(404, "No approved learning graph run for this NCERT release.")
    run_id = rows[0]["run_id"]
    edge_rows = ncert._query(_EDGES, {}, run_id=run_id)

    nodes: dict[str, dict] = {}
    for row in rows:
        node = nodes.setdefault(row["concept_id"], {"row": row, "evidence": [], "places": [], "in_scope": False})
        if (material := _evidence(row)) is not None:
            node["evidence"].append(material)
        if row.get("passage_id"):
            node["places"].append(row)
        node["in_scope"] |= _in_scope(row, scope)

    scoped = any(scope.values())
    targets = {cid for cid, n in nodes.items() if n["in_scope"] or not scoped}
    edges = [r for r in edge_rows if r["concept_id"] in targets and r["prerequisite_id"] in nodes]
    keep = targets | {e["prerequisite_id"] for e in edges}
    prerequisites: dict[str, list[str]] = {}
    for e in edges:
        prerequisites.setdefault(e["concept_id"], []).append(e["prerequisite_id"])

    concepts = []
    for cid, n in nodes.items():
        if cid not in keep:
            continue
        home = min(n["places"], key=lambda r: (r["grade"], r["book_code"], r["chapter"], r["physical_page"]),
                   default={})
        concepts.append(GraphConcept(
            id=cid, name=n["row"]["name"], level=n["row"]["level"], description=n["row"]["description"] or "",
            prerequisites=prerequisites.get(cid, []), materials=n["evidence"],
            **{f: home.get(f) for f in _FIELDS}))
    return LearningGraph(
        course_id=ncert.COURSE_ID, run_id=run_id, nodes=concepts,
        edges=[LearningGraphEdge(prerequisite=e["prerequisite_id"], concept=e["concept_id"],
                                 confidence=e["confidence"], reason=e["reason"] or "", evidence=_evidence(e))
               for e in edges])
