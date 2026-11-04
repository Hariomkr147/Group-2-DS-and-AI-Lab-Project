# Phase 07_concepts_questions_and_chunks — Build source-grounded concepts, practice questions and evidence chunks

Owner: Hariom Kumar; shared contributions as specified below.  
Status: **Planned — scripts and processing outputs do not exist yet.**  
Estimated active effort: 4–6 hours for a bounded pilot, unless otherwise stated.

[Master plan](../PLAN.md) · [Data contracts](../DATA_CONTRACTS.md) · [Actual-run report](report.md) · [Root index](../README.md)

## Update 2 Nov (evening)

No AI-written questions or answers. Content chunks, NCERT questions, private NCERT answers and worked examples are split from one extraction; see [PLAN §13.2](../PLAN.md#132-extract-once-then-split-into-four-record-types). Existing script: `code/extract_ncert_questions.py`. This replaces step 9's "review enough practice questions" target: use only what NCERT provides.


## Purpose

Accepted section/block content with embedded exercises and explanations.  
Produce: Separate source-grounded concept, evidence, question and private-answer records.

This phase is part of the source-to-tutor plan. The README describes intended work; the report records actual execution. Update reports from real outputs and logs, not expectations.

## Required inputs

- Accepted cleaned release and book/section metadata.

Check these inputs and their versions before running. Missing inputs are a named dependency, not a reason to invent a substitute result.

## Step-by-step work

1. Build the hierarchy subject→grade/book/edition→chapter→section→concept using actual headings and learning objectives. Distinguish the hierarchy relation from a prerequisite relation.
2. Assign stable concept IDs and normalize aliases across chapters/grades without collapsing different learning objectives. A higher-grade extension can remain a separate concept.
3. Create concept records with title, objective, description, source block/page IDs, aliases and review status. LLM-assisted proposals must cite supplied blocks and remain proposals until checked.
4. Separate explanations/definitions/formulas/worked examples from exercises, questions, answers, hints and solutions. Do not place active-question answer keys into unrestricted explanation retrieval.
5. Extract exercise/subquestion IDs, prompt text, options/assets, concept tags and answer availability. Do not manufacture absent answer keys; separately derived solutions need provenance and review.
6. Create section/concept-aware chunks from accepted evidence. Start with about 300–400 embedding-model tokens, then check actual tokenizer lengths, metadata overhead and boundary quality before choosing settings.
7. Keep formula units, question/subquestion boundaries and source references intact. Split long blocks without silently truncating text; use limited overlap only within compatible source/section boundaries.
8. Retain PDF page spans and printed labels for all chunks. Maintain block-to-chunk and chunk-to-concept links; content hashes distinguish changed text from stable identities.
9. Review enough valid practice questions for every supported demo concept to permit diagnosis, prerequisite practice and retesting. Five approved items per demo concept is a proposed planning target, not a TA-prescribed quota.
10. Produce pre/post chunk statistics and a clear support matrix for unanswered, diagram-dependent and unreviewed content.

## Planned code and locations

- `code/build_concepts.py` — hierarchy/concept candidates and review import.
- `code/extract_questions.py` — question records and hidden answer references.
- `code/build_chunks.py` — token-aware evidence chunks and source mappings.
- `code/validate_content_pack.py` — IDs, spans, answers/reviews and token limits.

These are implementation tasks, not existing runnable commands. Reuse a compatible team helper/harness before writing another one. Put dependency/environment decisions in Phase 00; record exact installed versions after setup. Keep Windows/local and notebook path handling portable.

## Expected artifacts

- `outputs/concepts.jsonl`
- `outputs/hierarchy_edges.csv`
- `outputs/questions.jsonl`
- `outputs/answers_private.jsonl`
- `outputs/chunks.jsonl`
- `outputs/chunk_concepts.csv`
- `outputs/chunk_blocks.csv`
- `outputs/content_support_matrix.csv`

All paths are relative to this phase folder. Create outputs only when real work runs. Preserve manifests, versions and source lineage; the presence of a directory is not evidence that artifacts exist.

## Local execution and notebooks

Start locally when feasible. If a GPU notebook is required, transfer only the required permitted inputs, preserve source IDs/hashes and save outputs/run metadata back to these folders. Do not rely on temporary notebook paths or hidden interactive state. Record notebook hardware and environment separately from local measurements.

## Completion checks

- [ ] Every accepted concept/chunk/question has valid source references.
- [ ] No silent tokenizer truncation; all evidence chunks meet chosen model limits.
- [ ] Only reviewed, answerable questions appear in the supported demo bank.
- [ ] Question answers and solutions have an explicit backend-only access policy.
- [ ] Required artifacts validate against [DATA_CONTRACTS.md](../DATA_CONTRACTS.md).
- [ ] Inputs, code/config/model revisions, hardware, command, failures and hashes are recorded.
- [ ] The [report](report.md) contains actual counts, evidence and limitations.
- [ ] A rerun or minimal meaningful boundary check has been performed where applicable.

## Report-specific requirements

- Concept/question/chunk counts by source and support state.
- One real section→concepts→chunks example and one exercise→subquestions example.
- Chunk boundary, answer availability and diagram exclusions explained.

For actual before/after evidence: include source/page/block identity, original representation, output representation, rule/decision, source-check result and evidence path. Show an unchanged or rejected case when relevant. Do not present illustrative examples as measured results.

## Handoff and next phase

Previous numbered phase: [Post-extraction EDA, quality evaluation and freeze](../06_eda_and_quality/README.md).

Next numbered phase: [Propose, review and publish prerequisite links](../08_prerequisite_graph/README.md).

Follow the master dependency diagram rather than assuming all branches are strictly serial. Record missing shared inputs, such as Pandey's vocabulary or Sandeep's agreed interface, explicitly.

