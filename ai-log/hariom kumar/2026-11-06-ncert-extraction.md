# NCERT extraction and RAG corpus preparation (2026-11-06)

**Contributor:** Hariom Kumar  
**Context:** Multi-stage extraction of 130 NCERT Mathematics and Science chapter PDFs (Classes 6 to 10) into structured passages with pgvector embeddings in Supabase.

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex
- **Purpose of Use:** Data pipeline artifact organization, script boilerplate for downloading executed Kaggle outputs, source link manifest generation, and routing evaluation script execution.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I designed and executed the 6-stage pipeline on Kaggle GPU instances. The AI was used interactively for file management and helper script generation. I inspected all generated scripts, validated parsed page outputs, and manually checked the database schema and pgvector embeddings.

## 2. My Contribution and Independent Engineering

I designed and executed the end-to-end NCERT processing pipeline across six stages on Kaggle GPU instances:
1. Inventory and audit: Built the catalogue of all 130 official NCERT chapter PDFs across Classes 6 to 10 for Mathematics and Science (3,066 physical pages).
2. Document parsing: Chose MinerU over basic PDF text extractors to properly preserve equations, tables, and layout geometry. Ran dual-GPU parsing on Kaggle (T4 x 2), extracting page Markdown, structured JSON, equations, and images.
3. Passage preparation: Chunked the parsed text into 7,221 clean candidate passages, removing OCR artifacts and filtering out empty pages.
4. Embedding generation: Chose `Qwen/Qwen3-Embedding-0.6B` and generated 1,024-dimensional normalized embeddings on GPU for all 7,221 passages.
5. Database loading: Designed the PostgreSQL schema using the pgvector extension under the `ncert_research` schema and loaded release `9aea0ce28990f86074b2d813`.
6. Routing benchmark: Formulated the topic routing evaluation to measure retrieval accuracy across grade and subject boundaries.

I used the AI as an assistant for mechanical repository management: retrieving executed notebook exports from Kaggle, downloading output artifacts, replacing local PDF binaries with an indexed source link manifest, and running the evaluation check on notebook 06.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Artifact organization | `pull my executed ncert extraction notebooks from kaggle and organise the outputs` | Script to download executed notebook versions with cell outputs via Kaggle API. | Verified output hashes, organized files into stage folders under `Ncert Extraction Notebook/output/`. |
| Repository weight | `replace the heavy pdfs with links to official ncert site in a readme` | Generated manifest extractor linking PDF titles to official URLs. | Formatted `manifest.json` with direct physical page counts and created README links, keeping repository size lightweight. |
| Routing evaluation | `run notebook 06 routing evaluation on the saved outputs and summarize the accuracy` | Ran evaluation script over candidate passages and embeddings. | Audited output metrics: confirmed 16/20 top-1 accuracy, 20/20 top-5 accuracy, and 10/10 off-topic rejections. |

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

**References:** `Ncert Extraction Notebook/README.md`, `Ncert Extraction Notebook/output/`, `Ncert Extraction Notebook/06_route_query.ipynb`.
