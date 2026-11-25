# prerequisite graph integration (2026-11-25)

## Prompts
1. My teammate created a prerequisite graph (learning_graph schema, linked to ncert_research.passages through evidence->>'source_id'). Let's incorporate it into our framework.

2. Explain the _GRAPH_PREREQUISITES query.
3. Add the /courses/ncert/graph endpoint.
4. Add tests for forward tracking.
5. Fix the help counter reset.

## Links
- Teammate's join notes (graph_nodes.evidence and prerequisite_edges.evidence to passages.passage_id)

## Tools and packages
- Claude Code (Opus 5.5)
- SQLAlchemy, PostgreSQL (Supabase), pytest

## What the AI did
- Inspected learning_graph: 9 runs; the latest full run has 840 concepts and 741 approved edges, all checked for cycles. Its concepts cite 685 of 2,651 topic headings.
- Found that the database now holds only release 3371af5f8052352316dad173 (same embedding model and revision), so updated RELEASE in backend/app/services/ncert.py.
- backend/app/services/ncert.py: added the _GRAPH_PREREQUISITES query and graph_prerequisites(). ncert.prerequisites() now asks the graph first and falls back to embedding similarity. It uses the latest run with approved edges for the current release, offers only topics at or below the learner's class, and returns one teaching topic per concept (summaries come last).
- backend/app/services/tutor.py: detour and "what are the prerequisites?" replies name the graph concept when there is one.
- backend/app/services/ncert_path.py: docstring updated.
- backend/.env.example: NCERT_GRAPH (on/off) and NCERT_GRAPH_RUN (pin a run).
- backend/tests/test_ncert_backtracking.py: tests for graph-first order, fallback, missing tables and reply wording.
- GET /courses/ncert/graph (backend/app/routers/courses.py, new backend/app/services/ncert_graph.py, new models in backend/app/schemas.py): concepts with evidence citations and approved edges with confidence and reason. Optional grade, subject, book_code and chapter filters keep a chapter's concepts plus their direct prerequisites.
- Moved the run-selection CTE into ncert.GRAPH_RUN and added ncert.graph_run(); new backend/tests/test_ncert_graph.py.

- backend/tests/test_ncert_backtracking.py: 7 forward-tracking tests (climbing back level by level, depth limit, help counter reset, next topic, end of chapter, understood inside a detour, saved topic gone).

## Notes
- Edges are "approved" by a model audit (gpt-oss-120b), not by an educator; say this in the report.
- Each lookup takes about 1 s, mostly network round-trips to Supabase.
- Some corpus headings are garbled (for example "Cwmwmmmo", Class 7 science ch 9).
- NCERT_GRAPH_RUN default is "" again, so the newest approved run (a0716faa) is used.
- Fixed: the help counter now resets when the tutor steps back (tutor._step_back), so the earlier topic gets its own hint before going deeper. Test: test_help_counter_starts_again_inside_a_detour.
