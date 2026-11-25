"""GET /courses/ncert/graph: the learning graph, whole or narrowed to a chapter."""
from app.services import ncert, ncert_graph


def _cited(pid, grade, chapter, heading, page):
    return {"passage_id": pid, "grade": grade, "subject": "maths", "book_code": f"b{grade}", "chapter": chapter,
            "heading": heading, "physical_page": page, "source_url": "https://ncert.nic.in/textbook/pdf/x.pdf"}


NODES = [  # integer (class 6) -> linear equation (class 8 ch 2) <- variable (class 8 ch 2); area is unrelated
    {"run_id": "r1", "concept_id": "int", "name": "Integer", "description": "Whole numbers and negatives.", "level": 1,
     "position": 1, "quote": "Integers are ...", "source_ref": "", **_cited("p1", 6, 1, "1.2 Integers", 4)},
    {"run_id": "r1", "concept_id": "var", "name": "Variable", "description": "", "level": 1,
     "position": 1, "quote": "A variable ...", "source_ref": "", **_cited("p2", 8, 2, "2.1 Variables", 10)},
    {"run_id": "r1", "concept_id": "lin", "name": "Linear equation", "description": "", "level": 2,
     "position": 1, "quote": "An equation ...", "source_ref": "", **_cited("p3", 8, 2, "2.3 Linear equations", 12)},
    {"run_id": "r1", "concept_id": "area", "name": "Area", "description": "", "level": 1,
     "position": 1, "quote": "Area is ...", "source_ref": "", **_cited("p4", 7, 9, "9.1 Area", 30)},
]
EDGES = [
    {"prerequisite_id": "int", "concept_id": "lin", "confidence": 0.95, "reason": "Solving needs integers.",
     "quote": "An equation ...", "source_ref": "", **_cited("p3", 8, 2, "2.3 Linear equations", 12)},
    {"prerequisite_id": "var", "concept_id": "lin", "confidence": 0.9, "reason": "", "quote": None,
     "source_ref": "", **{k: None for k in _cited("", 0, 0, "", 0)}},
]


def _fake(monkeypatch, nodes=NODES):
    monkeypatch.setattr(ncert, "_query", lambda statement, scope, **extra:
                        nodes if statement is ncert_graph._NODES else EDGES)


def test_whole_graph_has_every_concept_and_cited_edges(ncert_client, monkeypatch):
    _fake(monkeypatch)
    graph = ncert_client.get("/courses/ncert/graph").json()
    assert graph["run_id"] == "r1" and {n["id"] for n in graph["nodes"]} == {"int", "var", "lin", "area"}
    lin = next(n for n in graph["nodes"] if n["id"] == "lin")
    assert lin["prerequisites"] == ["int", "var"] and (lin["grade"], lin["chapter"]) == (8, 2)
    assert lin["materials"][0]["source"].startswith("NCERT Class 8 Maths, Chapter 2")
    first = graph["edges"][0]
    assert first["confidence"] == 0.95 and first["evidence"]["url"].endswith("#page=12")
    assert graph["edges"][1]["evidence"] is None


def test_chapter_graph_keeps_prerequisites_from_earlier_classes(ncert_client, monkeypatch):
    _fake(monkeypatch)
    graph = ncert_client.get("/courses/ncert/graph", params={"grade": 8, "subject": "maths", "chapter": 2}).json()
    assert {n["id"] for n in graph["nodes"]} == {"int", "var", "lin"}       # area dropped, class 6 integer kept
    assert {(e["prerequisite"], e["concept"]) for e in graph["edges"]} == {("int", "lin"), ("var", "lin")}


def test_no_approved_run_is_404_and_bad_filters_are_422(ncert_client, monkeypatch):
    _fake(monkeypatch, nodes=[])
    assert ncert_client.get("/courses/ncert/graph").status_code == 404
    assert ncert_client.get("/courses/ncert/graph", params={"grade": 12}).status_code == 422
    assert ncert_client.get("/courses/ncert/graph", params={"subject": "history"}).status_code == 422


def test_pack_graphs_still_use_the_generic_route(client):
    assert len(client.get("/courses/ncert-maths/graph").json()["edges"]) == 3
