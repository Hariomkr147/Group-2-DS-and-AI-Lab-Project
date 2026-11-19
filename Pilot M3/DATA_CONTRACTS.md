# Planned data contracts and evidence conventions

Prepared: 2 November 2026  
Status: **Shared specification; actual implementation, run evidence and remaining gaps are tracked in [report.md](report.md).**

These contracts keep all phases compatible. Confirm exact database names/types with Sandeep and checkpoint fields with Pandey before implementation. Prefer UTF-8 JSONL for nested text records, CSV for small review/manifests and JSON for summaries. Treat strings beginning with =, +, - or @ safely when displaying untrusted CSV text in spreadsheet software; do not alter the stored mathematical text to work around a viewer.

## 1. Shared identifiers and lineage

- `source_id`: stable identity of a specific book/chapter edition/language; separate from its downloaded file hash.
- `source_sha256`: immutable downloaded PDF bytes, not a title or URL.
- `run_id`: unique execution identifier; store actual run times and responsible owner.
- `corpus_version`: identifies a frozen accepted content release.
- `page_number`: **1-based physical page within the exact PDF file**.
- `printed_page_label`: the printed label, a string or null; never assume it equals the PDF page.
- `block_id`: source/page/extraction-version identity. Preserve a parent ID when cleaning or splitting.
- `concept_id`: stable reviewed learning objective. Changes to definitions/objectives require version/provenance decisions.
- `chunk_id`: stable logical identity within a release; `content_hash` identifies text changes. Never silently reuse old vectors for changed text.
- `question_id`: source exercise/subquestion plus edition identity; variants have parent/group IDs.
- `review_status`: pending / approved / rejected / quarantined, with reviewer and evidence when approved.
- `local_path`: relative to the Ncert work root where possible, for local/notebook portability.
- `code_revision`: repository commit plus uncommitted-diff identifier when applicable; do not imply a commit contains uncommitted code.

Different editions with matching chapter titles remain distinct sources. Whole-book and chapter-PDF page offsets must be explicitly mapped. Do not encode a guessed printed page into a citation.

## 2. Source manifest: Phase 01

`sources.csv` fields:
`source_id, subject, grade, language, edition, book_title, chapter_title, source_url, downloaded_at, sha256, local_path, bytes, pdf_pages, rights_note`.

Validate grade/subject against scope, successful PDF opening, positive page count, unique source/version identity, hash shape and local-path existence. Source URL availability and rights notes are not inferred from file extension.

Download failures have source/URL, attempt time, error, retry decision and final disposition. A failed source is not counted as successfully covered.

## 3. Raw extracted page/block: Phase 04

Page-level fields:
`source_id, source_sha256, page_number, printed_page_label, run_id, parser_name, parser_version, engine, model_revision, extraction_route, ocr_used, status, warnings, raw_output_ref`.

Block-level fields:
`block_id, source_id, page_number, block_order, bbox, coordinate_system, section_hint, content_type, raw_text, raw_markdown, raw_latex, asset_ids, parent_raw_ref, review_status`.

Allowed content types include heading, prose, formula, table, diagram/image, question, answer, worked_example and unknown. Parser classifications are proposals until checked for accepted use.

Retain only fields a tool really supplies; use null for unknown confidence, printed page or coordinates. Never populate a numerical confidence without a defined source/meaning. Bound boxes refer to the recorded page coordinate system/rotation; rendering crops must honor it.

Page statuses account for every page: extracted, accepted_empty, failed or quarantined. A page with a short formula is not automatically empty. Every asset keeps its PDF page/coordinates and meaning-review status.

Execution clarification: `ocr_used` is false for native PyMuPDF and null when a parser only reports batch-level OCR. MinerU's resolved `parser_parse_mode`, `ocr_observed_in_batch` and `ocr_observation_scope` retain the available evidence; a batch OCR log is not promoted to a per-page boolean.

## 4. Cleaned block and transformation log: Phase 05

Cleaned records keep `block_id, raw_block_id, source_id, page_number, cleaned_text, cleaned_markdown/latex where relevant, applied_rule_ids, content_hash, review_status, corpus_version`.

A transformation log record contains:
`run_id, transform_id, raw_block_id, source_id, page_number, before, after, rule_ids, reason, changed_or_removed, reviewer, review_status, evidence_ref`.

If text is unchanged, record a selected no-op evidence example rather than inventing a modification. Removed blocks must remain traceable. Ambiguous formulas go into quarantine. A human correction is a transformation with provenance, not an overwrite of parser-native output.

The rule register specifies conditions, exclusions and known limits. A regression check should use a meaningful case that could fail, such as a numeric line that is not a page number.

## 5. Concepts and hierarchy: Phase 07

Concept fields:
`concept_id, title, aliases, learning_objective, description, subject, grade, book_source_ids, chapter/section_refs, source_block_ids, evidence_refs, review_status, corpus_version`.

Hierarchy edges:
`parent_id, child_id, relation_type, source_refs, review_status`.

Hierarchy types such as contains/part_of are separate from prerequisite relations. Do not treat every concept in an earlier chapter as a prerequisite of every later one.

Alias normalization may connect terms but must preserve meaningful grade-specific differences. A concept definition inferred by an LLM must remain grounded in supplied passages and carry proposal/review provenance.

## 6. Questions and private answers: Phase 07

Learner-safe question fields:
`question_id, source_id, exercise_label, subquestion_label, group_id, prompt, options, asset_ids, concept_ids, assessed_skill_refs, page_number, printed_page_label, answer_available, requires_diagram, support_status, review_status`.

Backend-only answer fields:
`question_id, gold_answer, acceptable_forms, solution_steps, answer_source, derivation_method, evidence_refs, reviewer, review_status`.

`answer_source` distinguishes official/source-derived, team-derived and model-proposed answers. Missing answers remain unavailable. Synthetic variants are explicitly marked and do not inherit an official-answer claim.

Only approved supported questions with reviewed scoring information enter the M3 assessed-practice bank. A question needing an unreviewed diagram remains unsupported even if its prompt text extracted correctly.

Store learner-facing and private answer exports separately. Do not insert gold-answer fields into frontend payloads, open search hits or public evaluation traces. Keep separate worked examples safe for explanation rather than retrieving the active exercise solution.

## 7. Evidence chunks: Phase 07

Fields:
`chunk_id, content_hash, text, content_type, source_id, source_url, book_title, subject, grade, section_ref, page_start, page_end, printed_page_labels, block_ids, concept_ids, token_count, tokenizer_revision, review_status, corpus_version, retrieval_visibility`.

Use join tables/CSV links if preferred over repeated lists. A chunk can support multiple concepts. All page spans must refer to real contributing source blocks, not guessed chapter-wide ranges.

Starting token target is a proposal, approximately 300–400 BGE tokenizer tokens. Validate total encoded length including metadata and special tokens against the chosen model limit. Save long text as multiple meaningful chunks rather than silently truncating it.

`retrieval_visibility` distinguishes permitted explanatory evidence from private answer/solution material. Unknown or quarantined blocks are not automatically accepted evidence.

## 8. Prerequisite edges: Phase 08

Candidate/approved edge fields:
`edge_id, prerequisite_id, dependent_id, proposed_relation, evidence_block_ids, reason, proposal_method, judge_model_revision, prompt_version, model_confidence_optional, review_status, reviewer, review_date, decision_reason, corpus_version`.

Convention: prerequisite_id → dependent_id.

Keep candidate generation and final approval separate. A model confidence is recorded as its self-reported value if used, not presented as a calibrated probability. Evidence IDs must resolve to the supplied text.

Gold pair sets contain concept A/B, independently reviewed label/direction and source references. Separate development/test pair families; record candidate-universe limits when reporting recall. A graph with no cycles can still be educationally wrong, so cycle validation does not replace content review.

## 9. KT and diagnostic mappings: Phase 09

Skill mapping:
`concept_id/question_id, original_skill_id, checkpoint_skill_index, skill_name, checkpoint_id, vocabulary_hash, mapping_type, evidence, review_status, reviewer`.

Mapping type is exact / partial / unmapped. A checkpoint index is meaningful only with its exact vocabulary. Do not map all of science to a maths skill or reuse an index from another preprocessor.

Diagnostic labelbook:
`label_id, name, definition, included_error_pattern, exclusion_cases, concept_ids, external_source_id/version, provenance, terms, review_status`.

Diagnostic example:
`example_id, problem_group_id, concept_id, question, student_answer, student_working, correctness, diagnostic_label, needs_confirmation, provenance, split, review_status`.

External taxonomy records are not student-response examples. Generated examples need review and synthetic provenance. Unknown, arithmetic slip and correct alternative cases prevent a detector from interpreting every wrong answer as the same misconception.

Scope/guardrail support:
`example_id, problem_group_id, course_context, current_concept, pending_question, expected_answer_type, recent_context, message, intent_label, scope_label, proposed_route, provenance, review_status, split`.

Support data stays independent of the 161 held-out team scenarios. Group paraphrases/variants together. The guardrail classifier returns a proposed route; the backend controls allowed actions and whether an answer becomes a KT event.

## 10. Embedding and database manifests: Phase 10

Embedding manifest:
`embedding_release_id, corpus_version, embedding_model_id, model_revision, tokenizer_revision, vector_dimension, normalization, document_format, query_format, max_input_tokens, chunk_config_hash, record_count, dtype, artifact_paths, artifact_hashes, hardware, run_id`.

For the candidate BAAI/bge-small-en-v1.5, expected dimension is 384 and model sequence length is 512. Confirm against the pinned release. A change to model/dimension/text/configuration requires dependency-aware rebuilding; never mix embeddings from incompatible spaces.

Vectors must have finite values, correct dimensions and matching chunk IDs. Query formatting follows the chosen model documentation. Score thresholds need calibration on project development queries.

Proposed database entities:
sources, concepts, chunks, chunk_concepts, questions, private_answers, prerequisite_edges, concept_skill_map, concept_misconception_map and corpus_releases.

This is an entity plan, not an implemented SQL schema. Coordinate application migrations and naming with Sandeep. Content import must not drop/replace unrelated learner/session history. Use a transaction, source/version-scoped update and a verified target database.

## 11. Retrieval, evaluation and handoff: Phases 11–13

Search request contract:
course/subject, query, optional concept IDs, controller action, result limit and corpus version.

Search result contract:
chunk ID/text, matched concept IDs, source URL/title, physical PDF page span, printed labels, score/method and corpus version.

Error/uncertainty paths:
unknown concept, ambiguous concept, no accepted evidence, unsupported scope, source unavailable and internal retrieval failure. A nonempty vector result does not prove relevance.

Query annotation:
query_id, query_family_id, text/context, supported scope, relevant_chunk_ids, relevant_concept_ids, split, annotator and review status.

Metric report:
method/configuration, corpus/query manifest hashes, query count, per-group coverage, Recall@5/MRR, latency conditions, failures and run ID. Never invent comparative scores or reuse published numbers as project results.

Handoff manifest lists every artifact version/hash, required runtime and supported scope. The backend trace should identify the learner-state source (trained KT or labelled fallback), graph edges, retrieved evidence and output-check result. Sanitize real identifiers and private answers in publicly shared traces.

## 12. Report conventions and publication

Each phase README describes intended work. Each phase report records only actual completed work with evidence.

Use status Planned / In progress / Blocked by named dependency / Completed. A report can be incomplete without fabricating values. Missing runtime/count/accuracy is **Not measured**. Do not set completion simply because code was written.

Small manifests, labelled review decisions, report figures and summary metrics are candidates for version control. Bulk PDFs, parser outputs, model weights, vectors and database dumps use local/permitted artifact storage with hashes and instructions. The root .gitignore is a starting safeguard, not a legal/publication decision.

Public data release depends on source-specific terms, attribution and absence of private answers/learner data. Record available reproduction steps when redistribution is not permitted.



## Update 2 Nov (evening)

New record types (NCERT questions, private NCERT answers, worked examples, misconception catalogue) and their access rules are defined in [PLAN §13.2](PLAN.md#132-extract-once-then-split-into-four-record-types) and [§13.4](PLAN.md#134-misconceptions-datasets-not-hand-written-lists). Current field sets are in `07_concepts_questions_and_chunks/code/extract_ncert_questions.py` and `10_embeddings_and_database/code/load_ncert_questions.py`.
