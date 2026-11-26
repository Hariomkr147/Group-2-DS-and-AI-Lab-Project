# Prerequisite graph notebook

[Open the final Kaggle notebook](final_prerequisite_graph.ipynb). It reads course passages from Supabase Postgres, builds and audits a prerequisite graph, and exports an interactive HTML viewer. You can open an existing graph without running inference.

An arrow points from the skill a student needs first to the concept that uses it. For example, **Addition → Number Pyramid** means the student uses addition to work out the entries in a number pyramid. Click an arrow in the viewer to see the reason for the link and its supporting textbook passages.

## Saved NCERT graph

The approved run covers NCERT Classes 6–10 Mathematics and Science. It used **6,858 passages from 130 chapters** and contains **840 concepts and 741 approved prerequisite links**. Of the 210 previously unlinked concepts, 186 gained a prerequisite link and 24 gained a sourced related study topic. The viewer shows related topics without assigning a learning order.

**Run ID** `a0716faaa4d372850af91b6e09d0f5107254e427a2ee3bb40e82a4a794ab4870`

Open the team's Supabase project and filter by `run_id` to inspect this graph. [Graph runs](https://supabase.com/dashboard/project/cztuzjasxgmrznmdceev/editor/40037) · [Concepts](https://supabase.com/dashboard/project/cztuzjasxgmrznmdceev/editor/40045) · [Prerequisite links](https://supabase.com/dashboard/project/cztuzjasxgmrznmdceev/editor/40058)

## Run on Kaggle

1. Import [the final notebook](final_prerequisite_graph.ipynb) into Kaggle. Use a CPU session with Internet enabled. [Kaggle notebook guide](https://www.kaggle.com/docs/notebooks)
2. Add `SUPABASE_DB_URL` in Kaggle Secrets using the **Session pooler** connection string. Your database role needs access to the source tables and the saved graph. Publishing also requires graph write access and permission to create the graph schema and tables on first use. [Supabase connection guide](https://supabase.com/docs/guides/database/connecting-to-postgres)
3. Set `RUN_WORKFLOW = True` in the configuration cell and choose a mode. Run the notebook from the top.
4. Open `prerequisite-graph.html` in the notebook outputs. Search for a concept, filter by class or subject, or expand the number of steps to follow a longer learning path. The viewer itself works offline after export.

| Mode | What it does |
| --- | --- |
| `view` | Opens `APPROVED_RUN_ID` and exports its viewer. Uses no model quota. |
| `reaudit` | Checks the links in `BASE_RUN_ID`, searches for missing prerequisites, and produces a new review result. Keep the source query and parameters aligned with the base run. |
| `build` | Extracts concepts from the selected passages and audits a new graph. Use this for a new course or a new source scope. |

### Model access for `reaudit` and `build`

- **Kaggle Model Proxy.** Keep `MODEL_PROVIDER = "kaggle"`. The notebook uses Model Proxy credentials supplied by the environment or requests them through the Kaggle CLI using `KAGGLE_API_TOKEN`. The Kaggle account needs Benchmarks access. Check the available balance with `kaggle benchmarks quota`. [Kaggle CLI guide](https://github.com/Kaggle/kaggle-cli/blob/main/docs/benchmarks.md)
- **OpenAI-compatible API.** Set `MODEL_PROVIDER = "openai_compatible"`, configure `LLM_BASE_URL`, and add `LLM_API_KEY` in Kaggle Secrets. Choose model IDs for `PROPOSER`, `REVIEWER`, and `SECOND_REVIEWER` that support `json_schema` structured output. Use different models for proposing and reviewing.

The models receive selected passage excerpts. Use course material you are allowed to send to the provider. Successful responses are cached in `prerequisite-model-cache.sqlite` in the working directory. Keep the cache private when it contains private course material. `MAX_MODEL_CALLS` includes retries and excludes cache hits.

## Build a graph for another course

Store the course as text passages in Postgres first. Extract text from PDFs and images before loading them. In the notebook's configuration cell, replace the source query and parameters with your own. Below is an example for CA Foundation using illustrative table and column names.

```python
RUN_WORKFLOW = True
MODE = "build"
COURSE_KEY = "ca-foundation-accounting"
COURSE_LABEL = "CA Foundation Accounting"
APPLY_NCERT_TEXTBOOK_CHECKS = False
EMBEDDING_SQL = None

SOURCE_SQL = """
    SELECT id::text AS source_id,
           heading AS title,
           body AS content,
           document_url AS url
    FROM learning.course_passages
    WHERE course_slug = %(course)s
"""
SOURCE_PARAMS = {"course": "ca-foundation-accounting"}
```

The query must return `source_id`, `title`, and `content`. Give each passage a stable, unique ID and nonempty text. Optional fields `subject`, `grade`, `book_code`, `chapter`, `page`, `url`, and `source_ref` provide filter and citation details. The supplied NCERT embedding query applies to the NCERT release. For a custom source, the notebook uses text-based matching with `EMBEDDING_SQL = None`.

## Review and publish

The pipeline proposes dependencies, checks their direction and evidence with a second model, and removes cycles and redundant links whose learning order is already represented by another path. Review the output and its citations before enabling `SAVE_APPROVED = True` in the last cell. In Supabase, `approved` means the link passed the AI-assisted source audit. Educator validation is a separate step.

| Supabase table | Contents |
| --- | --- |
| `learning_graph.graph_runs` | Course key, source scope, review metrics, and related study topics for each graph version |
| `learning_graph.graph_nodes` | Concepts with descriptions, learning levels, and source excerpts |
| `learning_graph.prerequisite_edges` | Directed links with review status, instructional reasons, and evidence for both concepts |

To read the approved NCERT links by concept name, run this query in the Supabase SQL Editor.

```sql
SELECT p.name AS learn_first, t.name AS dependent_concept, e.reason
FROM learning_graph.prerequisite_edges AS e
JOIN learning_graph.graph_nodes AS p
  ON (p.run_id, p.concept_id) = (e.run_id, e.prerequisite_id)
JOIN learning_graph.graph_nodes AS t
  ON (t.run_id, t.concept_id) = (e.run_id, e.concept_id)
WHERE e.run_id = 'a0716faaa4d372850af91b6e09d0f5107254e427a2ee3bb40e82a4a794ab4870'
  AND e.review_status = 'approved'
ORDER BY t.level, t.name, p.name;
```

## Verification

The [final notebook](final_prerequisite_graph.ipynb) includes the complete workflow, NCERT checks, and HTML viewer template in a single file.

The approved NCERT graph was generated by local pipeline runs with live inference through Kaggle Model Proxy. The final notebook's `view` mode and HTML export were verified against that Supabase run. Its custom-course build, re-audit, and publish flow was tested on a CA Foundation fixture in local PostgreSQL with mocked model responses.
