# NCERT extraction and RAG corpus preparation (2026-11-06)

**Contributor:** Hariom Kumar  
**Context:** Multi-stage extraction of 130 NCERT Mathematics and Science chapter PDFs (Classes 6 to 10) into structured passages with pgvector embeddings in Supabase.

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex (GPT-6)
- **Purpose of Use:** Data pipeline artifact organization, Kaggle CLI output synchronization, source link manifest generation, and routing evaluation script execution.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I designed and executed the 6-stage extraction pipeline on dual-T4 GPUs on Kaggle. The AI was used interactively for file management and helper script generation. I inspected all generated scripts, validated parsed page outputs across both subjects, and verified database schemas and pgvector embeddings.

## 2. My Contribution and Independent Engineering

I designed and executed the end-to-end NCERT processing pipeline across six stages on Kaggle GPU instances:
1. Inventory and audit: Built the catalogue of all 130 official NCERT chapter PDFs across Classes 6 to 10 for Mathematics and Science (3,066 physical pages), calculating SHA-256 hashes for reproducibility.
2. Document parsing: Chose MinerU over basic PDF text extractors to properly preserve equations, chemical formulas, tables, and multi-column layout geometry. Ran dual-GPU parsing on Kaggle (T4 x 2), extracting page Markdown, structured JSON, formulas, and visual figures.
3. Passage preparation: Chunked the parsed text into 7,221 candidate passages, preserving LaTeX math delimiters ($...$ and $$...$$), stripping OCR header/footer noise, and filtering out empty pages.
4. Embedding generation: Chose `Qwen/Qwen3-Embedding-0.6B` and generated 1,024-dimensional normalized embeddings on GPU for all 7,221 passages using mean pooling.
5. Database loading: Designed the PostgreSQL schema using the pgvector extension under the `ncert_research` schema and loaded frozen release `9aea0ce28990f86074b2d813`.
6. Routing benchmark: Formulated the topic routing evaluation to measure retrieval accuracy across grade and subject boundaries.

I directed the AI to handle mechanical repository management: retrieving executed notebook exports from Kaggle, downloading output artifacts, replacing local PDF binaries with an indexed source link manifest, and running the evaluation check on notebook 06.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Artifact organization | `Write a Python automation script using Kaggle CLI to pull outputs from my 6 dual-T4 extraction notebooks, verify SHA-256 hashes of the 130 textbook PDFs against our inventory manifest, and organize the JSON, markdown, and embedding artifacts into stage directories under Ncert Extraction Notebook/output/.` | Script to download executed notebook versions with cell outputs via Kaggle API and verify file integrity. | Verified output hashes, organized files into stage folders under `Ncert Extraction Notebook/output/`. |
| Repository weight | `We cannot commit 3,066 pages of raw PDF binaries into git. Write an automated manifest generator that extracts chapter title, class, and physical page counts from our stage 01 inventory, maps them to official NCERT portal URLs with '#page=X' deep links, and generates a lightweight README.md index table.` | Generated manifest extractor linking PDF titles to official URLs with physical page fragments. | Formatted `manifest.json` with direct physical page counts and created README links, keeping repository size lightweight. |
| Chunking and filtering | `Review stage 03 passage chunking logic: ensure formulas marked with LaTeX delimiters ($...$ and $$...$$) and multi-row tables are not split across chunks. Add regex cleaning to strip OCR page headers, footers, and blank pages, targeting roughly 7,000 clean passages.` | Drafted chunking and sanitization routine with delimiter-aware boundaries. | Audited chunk boundaries across sample physics and chemistry chapters; confirmed 7,221 clean passages generated. |
| Vector schema design | `Draft PostgreSQL migration for Supabase pgvector under the schema 'ncert_research'. Define table 'passages' with columns (id, class_num, subject, chapter_title, page_num, content, embedding vector(1024), metadata jsonb). Include an HNSW index on embedding using cosine distance operator '<=>' and insert frozen release identifier '9aea0ce28990f86074b2d813'.` | Drafted SQL DDL with HNSW index configuration and metadata structure. | Verified database schema in Supabase; confirmed successful ingestion of release `9aea0ce28990f86074b2d813`. |
| Routing evaluation | `Run notebook 06 routing evaluation script on saved outputs. Test 20 curriculum queries across Classes 6 to 10 Maths and Science plus 10 out-of-domain adversarial queries. Calculate top-1 accuracy, top-5 accuracy, and off-topic rejection rate based on cosine distance thresholds.` | Ran evaluation script over candidate passages and embeddings, reporting retrieval rank metrics. | Audited output metrics: confirmed 16/20 top-1 accuracy, 20/20 top-5 accuracy, and 10/10 off-topic rejections. |

## 4. Reasoning I Can Substantiate in Review

- Why MinerU instead of PyPDF or pdfplumber: NCERT Science and Maths textbooks use multi-column layouts, complex chemical formulas, and mathematical notation. Basic text dumpers mangle column order and drop formula structures, whereas MinerU extracts reading order, formulas, and visual figures into separate assets.
- Choice of Qwen3-Embedding-0.6B: Provides strong multilingual and technical comprehension within a compact parameter size, outputting 1,024-dimensional dense vectors suitable for fast cosine distance matching in pgvector.
- Release hashing and immutability: Using release hash `9aea0ce28990f86074b2d813` guarantees that the vector embeddings in Supabase match the exact frozen passage text in git, preventing retrieval drift.
- Link-based storage: Keeping raw PDF files in the git repository would bloat git history by gigabytes; linking official NCERT URLs with physical page fragments (`#page=X`) keeps the repo lightweight while providing reproducible verification.

## 5. Validation Record

- Checked all 130 textbook PDFs against recorded SHA-256 hashes.
- Verified 3,066 parsed pages (3,047 content pages and 19 blank pages) with zero parser errors.
- Verified 7,221 candidate passages match their corresponding 1,024-dimensional embedding vectors.
- Confirmed database release `9aea0ce28990f86074b2d813` loaded cleanly in Supabase.
- Verified notebook 06 routing results: 16/20 top-1 accuracy, 20/20 top-5 accuracy, and 100% off-topic rejection.

## 6. Team Accountability Declaration

- All AI-assisted code, scripts, and documentation incorporated into this stage have been reviewed and appropriately validated by me.
- Project decisions, experimental results, and conclusions are supported by my independent reasoning and empirical evidence.
- I understand all contributions and can explain and defend the relevant work independently during review and assessment.

**References:** `Ncert Extraction Notebook/README.md`, `Ncert Extraction Notebook/output/`, `Ncert Extraction Notebook/06_route_query.ipynb`, `Ncert work/03_parser_benchmark/modern_benchmark/REPORT.md`.
