> **Historical notes.** This document describes earlier runs and is not current status. Read [CURRENT_CHECKPOINT.md](CURRENT_CHECKPOINT.md), generated from current release manifests. Earlier human-review/local-model instructions do not apply to the current app.

<!-- automatic-validation-2026-11-03 -->
> **Updated direction:** human review is not required. The historical review instructions below are superseded by [AUTOMATIC_VALIDATION.md](AUTOMATIC_VALIDATION.md); Codex and deterministic checks handle verification.

# Decide the misconception approach, review the pilot, and inspect storage

Updated 3 November 2026. These are handoff instructions, not new model-accuracy claims.

## Model identified from your uploaded training notebook

The supplied `qwen-finetuning (1).ipynb` trains a **Socratic next-response generator**, not an Eedi/MAP misconception classifier. Its sources are MathDial and SocraTeach; it has no misconception-ID label supervision. Use the tailored [Qwen3.5 adapter hosting notebook](12_socratic_model_feasibility/notebooks/host_qwen35_socratic_adapter.ipynb) for this model. The generic Phase 09 template remains available for a separate actual diagnostic model.

The saved outputs report the final adapter `final_lora_r16_lr0.0002`, 1,995 retained training dialogues and 100 development contexts. Mean reply length went from 56.39 to 20.25 words; question-mark rate from 52% to 59%; validation loss from 1.8238 to 1.072. The zero lexical leak flags do not establish answer safety. The evaluation contexts also informed model-setting selection, so these are development results, not an untouched final test. These numbers were read from notebook outputs and not rerun here. [Inspection record](12_socratic_model_feasibility/outputs/user_qwen_training_inspection.json).

Attach the saved training output containing `qwen35_socratic_final/adapters/final_lora_r16_lr0.0002` as a private Kaggle input. The tailored host selects that exact adapter, fetches base/tokenizer revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`, uses NF4/double-quant/fp16 and the original no-thinking chat format, and caps generation at 96 tokens. The tokenizer was not saved by the training script, so loading it from the pinned base is required. No training cells from the supplied file were executed or changed.

This model can now be evaluated for source-grounded hint generation. Using it to select misconception IDs would be a separate, unvalidated task; the weak Eedi retrieval finding remains unchanged. No adapter weights were provided in the attached notebook, so GPU loading and real inference are still pending.

## The decision we can make now

Keep Eedi as the attributed mathematics misconception catalogue. The weak baseline is a finding about our current BGE matching method, not a reason to discard the catalogue. Do not enable automatic diagnoses from the current 19.2% covered-label top-five result. Science needs separate evidence.

Your fine-tuned model may replace the retrieval step, rank candidates better, or classify directly. Which role fits depends on its actual architecture, training input and output labels. A MAP classifier's labels must not silently become Eedi graph IDs. Use the model's original label namespace for its first evaluation; test graph-ID alignment separately.

Before choosing the method, we still need:

1. Your checkpoint path, base checkpoint, full-model/adapter/classifier type, exact training prompt/tokenization, original label mapping and training run identity.
2. Training/validation question IDs and the data used for fine-tuning. Our existing question split is **not independently held out** if your model trained on those questions. Freeze a genuinely unseen split before comparing methods. Do not tune on the team's 161 scenarios.
3. Compare the current baseline and your model on the same unseen question families and label space. Include actual wrong responses with working, correct responses, insufficient working and out-of-scope cases. Report label-alignment coverage separately. The previous MAP retrieval baseline did not evaluate correct/no-misconception rejection.
4. If the model supplies candidates, measure top-five recall; if it diagnoses directly, measure final precision and coverage. Also measure false diagnoses on correct/unsupported answers, abstention, invalid labels and latency. Selecting from five weak candidates cannot recover a missing label unless another candidate source supplies it.
5. Keep numeric rules as candidate evidence, not proof. Confirm using the learner's working; persistence requires repeated evidence across attempts. The five arithmetic rules had no matches in the bounded publisher baseline, so their wider coverage is not demonstrated.

Suggested **development gates**, to agree before the next evaluation: top-five recall at least 80% if using a shortlist; at least 95% precision among accepted diagnoses; and at least 50% coverage among in-scope, sufficiently explained cases. These are proposed project targets, not established standards or achieved results. Always report sample size and uncertainty. Passing a small sample does not establish deployment readiness.

If the model improves retrieval but diagnosis precision fails, retain the candidates internally and ask for working. If it passes on genuinely unseen cases, proceed with a bounded tutor integration. If it fails, change the matching method or use an explanation/probing fallback; do not manufacture a confident label. Concept filtering remains deferred until full extraction under PLAN 13.5.

## Host the fine-tuned model

For your supplied Socratic model use [host_qwen35_socratic_adapter.ipynb](12_socratic_model_feasibility/notebooks/host_qwen35_socratic_adapter.ipynb) and its matching instructions. The following generic steps describe the separate [diagnostic hosting template](09_skill_misconception_and_scope_mapping/notebooks/host_finetuned_misconception_model.ipynb). Both use the same authenticated transport; the default output limit is now 96 tokens. The Socratic host also rejects larger output limits to preserve its declared protocol.

1. Import it into a **private Kaggle notebook**. Attach the checkpoint and, for LoRA, its exact base checkpoint/tokenizer. Enable GPU and Internet.
2. Fill the configuration cell. Supported template loaders: HF causal LM, causal-LM LoRA, or full HF sequence classifier. GGUF, custom rerankers, encoder-only retrieval models and classifier adapters need their matching loader instead. The exact model remains unconfirmed.
3. Add a fresh random endpoint-only key of at least 32 characters in Kaggle Secrets as `TUTOR_API_KEY`. Never use your Kaggle account key or a Hugging Face token as this service key. The notebook can also ask for a hidden key.
4. Run through the tunnel cell. It checks local and public authenticated health, and checks that an unauthenticated request receives HTTP 401. Share the temporary HTTPS **URL**, not just the Kaggle notebook URL.
5. Copy [.remote_model_connection.example.json](09_skill_misconception_and_scope_mapping/.remote_model_connection.example.json) to `09_skill_misconception_and_scope_mapping/.remote_model_connection.json`. Fill the URL and temporary endpoint key **locally**. The real file is ignored; do not paste long-lived credentials in chat or commit the filled file. Then tell Codex the endpoint is ready and provide the training-format/label details.
6. Keep the Kaggle session running during testing; run its stop cell afterwards and rotate/delete the temporary key. Temporary tunnels and notebook sessions are not permanent hosting.

All routes require Bearer authentication. `/metadata` states model identity and label namespace; `/predict` accepts the exact training-formatted `prompt`, or chat `messages` for an appropriate causal chat model. It rejects oversized context rather than silently clipping. Raw generations and classifier probabilities are **not** approved diagnoses. Outputs still require parsing, candidate-ID checks and the independent evaluation above. No competition examples or student text are packaged in this notebook.

Local verification so far: every notebook code cell compiles; the exact embedded endpoint module passes live loopback HTTP/auth/request tests without a GPU. Your checkpoint load, GPU memory fit, public tunnel and model inference have **not** been executed here.

References: [Kaggle session/input settings](https://www.kaggle.com/docs/notebooks), [Transformers chat formatting](https://huggingface.co/docs/transformers/main/chat_templating), [PEFT loading](https://huggingface.co/docs/peft/package_reference/auto_class), [temporary Cloudflare tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

## Human review: where to start and how

Open [human_review/review_packet.html](human_review/review_packet.html) in your browser and [human_review/review_decisions.csv](human_review/review_decisions.csv) in Excel. Both are generated private files on this PC. The HTML contains official private answer-key excerpts; keep it local. It works without uploading anything to a review service. Local PDF links may be blocked by some viewers; use the accompanying official PDF link or open the PDF manually.

The queue has 241 records: 12 accepted retrieval chunks, 119 question records, 91 block checks, four whole quality pages and 15 prerequisite pairs. You do **not** need to finish all of these to give the first useful review.

Recommended first pass:

1. **The 12 accepted chunks.** Open each source PDF at the displayed physical page. Check that the extracted meaning, fractions, operators, exponents, units and tables agree. This checks the material currently used by retrieval. It previously received Codex AI checks, not independent human approval.
2. **A small fixed math question set with official keys.** Review the question wording, instructions, all subparts, required diagrams and source page. Expand the owner-only answer section; open its separate PDF page and confirm the exercise/question number and exact printed answer. Include both Grade 7 multiplication and division. Never derive a missing key or silently correct an ambiguous printed answer. Missing-key items stay unscored.
3. **The four quality pages.** Compare the whole original page with its extracted blocks, looking for missing material as well as incorrect material. Their physical PDF page numbers are Grade 6 math 36, Grade 7 math 25, Grade 8 math 13 and Grade 7 science 16. These are extraction/source checks, not a request to solve the exercises. Do not claim CER or semantic accuracy from a simple tick.
4. **The 15 graph pairs, later.** Judge whether learning A is needed to learn B, rather than merely related. Explain direction, redundancy or neither in notes. The three-edge pilot is already sufficient for its bounded demo.

In the CSV leave identifiers and hashes unchanged. Fill only:

- `decision`: `approve`, `reject`, `needs_fix` or `unsure`.
- `reviewer`: your name; `review_date`: actual review date.
- `notes`: exact mismatch, PDF physical page and correction/reference. For graph pairs include the actual relationship/direction. For a question with no official key, use `unsure` and note any prompt-only check; do not approve it for scoring.

Use `approve` only after opening and comparing the PDF. Keep `unsure` when a symbol, diagram or answer link is ambiguous. Physical page is the viewer counter: it can differ from the printed textbook page. Text is shown literally, including LaTeX/table markup; compare its intended notation to the PDF.

Save the CSV, then tell Codex its path. **Nothing is automatically approved:** these are review submissions. Decisions must be checked against the saved source/record/answer hashes, translated to the relevant block/item/graph review records, and released with a new version. A chunk approval alone does not approve all other blocks on its page. Question review ingestion is not implemented yet. Do not edit generated source JSONL files or overwrite Codex reviewer names to simulate human checks.

Existing detailed queues remain at `06_eda_and_quality/outputs/quality_annotations.csv`, `06_eda_and_quality/outputs/block_reviews.csv`, `03_parser_benchmark/outputs/reference_reviews.csv` and `08_prerequisite_graph/outputs/edge_reviews.csv`. Prefer the new packet/decision CSV for your first pass. The packet builder refuses to overwrite an existing decision queue.

## Where the database is and how to view it

This is **local PostgreSQL 18 with pgvector**, not a remote/cloud database. The existing dedicated cluster was started and checked on 3 November 2026. It is separate from the machine's default PostgreSQL port 5432.

| pgAdmin connection field | Value |
| --- | --- |
| Host | `127.0.0.1` |
| Port | `54329` |
| Maintenance database | `ncert_pilot` |
| Username | `ncert` |
| Password | Copy only the password value from the ignored local `10_embeddings_and_database/.database_connection.json` file; do not share it |

Open **pgAdmin 4** from Windows Start. Right-click Servers → Register → Server. Give it a name such as `NCERT pilot`, enter the connection above, and save. Expand Databases → ncert_pilot → Schemas → the schema → Tables. Right-click a table → View/Edit Data → First 100 Rows. Treat this as inspection; do not edit frozen rows.

For easier inspection, open [inspect_database.sql](10_embeddings_and_database/inspect_database.sql) in pgAdmin's Query Tool and run it. Its transaction is read-only. It shows current-release chunks, source questions, owner-only official answers and Eedi entries. The tables with plain text are easier to inspect than the physical database files.

| Schema/table | Stored information |
| --- | --- |
| `ncert_content.chunks` | Accepted explanation text, source pages, metadata and 384-dimensional vectors |
| `ncert_content.ncert_questions` | 119 source question payloads, including pending status |
| `ncert_content.ncert_worked_examples` | 14 NCERT worked examples |
| `ncert_private.ncert_answers` | 86 linked official answer payloads; backend scoring/review only |
| `ncert_content.concepts`, `prerequisite_edges`, `releases` | Concepts, reviewed edges and version identities |
| `ncert_diag.misconceptions` | 8,117 original Eedi entries and their vectors |
| `ncert_diag.constructs` | 2,258 Eedi learning constructs |
| `ncert_diag_eval.original_rows` | 41,170 retained original CSV rows across competition files, including maps/samples; not 41,170 student explanations |

There are **three historical chunk releases**, 12 chunks each: 36 stored rows. The current release is `ncert-pilot-fd981363bc7f493a`, with **12** chunks. Filter by this release; do not mix versions or treat old rows as current content. All source-bank questions currently remain pending item review. Database ownership access lets you view private answers; learner endpoints must not expose them.

If the server is stopped, from the `Ncert work` directory run:

```powershell
& '.\.venv\Scripts\python.exe' '10_embeddings_and_database/code/setup_local_database.py'
```

The helper validates the existing NCERT-owned cluster. Its physical files are under `10_embeddings_and_database/postgres/data/`; do not open, edit or move those files to inspect rows. Credentials are in the ignored `.database_connection.json`, not in reports.

## Where text and embeddings are stored on disk

All paths below are relative to `C:\Users\Hario\Documents\Group-2-DS-and-AI-Lab-Project\Ncert work`.

| Stage | Location | Meaning |
| --- | --- | --- |
| Original PDFs | `01_download_pdfs/pdfs/` | Unchanged official source copies |
| Sources and PDF locations | `01_download_pdfs/manifests/sources.csv` | IDs, URLs, hashes and exact PDF paths |
| Native PyMuPDF probes | `04_extract_text_and_ocr/native_outputs/` | Per-source native output/cache |
| Canonical extracted text | `04_extract_text_and_ocr/outputs/blocks.jsonl` | All 3,090 raw block records; not all approved |
| Page records and routes | `04_extract_text_and_ocr/outputs/pages.jsonl` | 203 physical pages with parser/role/lineage |
| Images | `04_extract_text_and_ocr/assets/` | Preserved figures/page renders; no image-understanding claim |
| Cleaned text | `05_clean_and_preprocess/outputs/clean_blocks.jsonl` | All cleaned records and quarantine/removal status |
| Explanation candidates | `07_concepts_questions_and_chunks/outputs/chunks.jsonl` | 984 candidates, including pending/quarantined material |
| Current retrieval text | `07_concepts_questions_and_chunks/outputs/accepted_chunks.jsonl` | Only the 12 current approved mapped chunks |
| Source question bank | `07_concepts_questions_and_chunks/outputs/ncert_questions.jsonl` | Questions; no private answer text |
| Private answer extraction | `07_concepts_questions_and_chunks/outputs/ncert_answers_private.jsonl` | All 297 extracted key items, including unmatched whole-book Grade 8 entries; only 86 are linked and loaded |
| NCERT vector array | `10_embeddings_and_database/vectors/bge-7f120cc70b23ca1f/vectors.npy` | 12 × 384 float32 vectors |
| NCERT vector row IDs | Same folder, `chunk_ids.jsonl` | Maps array row to chunk ID; do not reorder separately |
| NCERT embedding provenance | `10_embeddings_and_database/outputs/embedding_manifest.json` | Model revision, hashes, dimensions and timings |
| Eedi vector array | `09_skill_misconception_and_scope_mapping/vectors/eedi-2ae0839debf73c0c/vectors.npy` | 8,117 × 384 float32 vectors |
| Eedi records/row order | `09_skill_misconception_and_scope_mapping/outputs/misconceptions.jsonl` | Original IDs/texts aligned with the vector array |
| Eedi embedding provenance | `09_skill_misconception_and_scope_mapping/outputs/eedi_catalogue_manifest.json` | Pinned data/model identities and vector hash |

Both text and vectors also exist together in PostgreSQL for accepted chunks and Eedi entries. `.npy` files are binary arrays, not text to open in Notepad; use Python/NumPy or inspect the database's `embedding` column. The larger raw/clean text sets remain on disk; they are not all loaded into retrieval. JSONL has one JSON object per line, so VS Code or the local review packet is more convenient than Excel for reading it.
