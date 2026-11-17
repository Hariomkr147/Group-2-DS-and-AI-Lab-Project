# NCERT Classes 6–10 extraction

This folder contains the six executed Kaggle notebooks and saved outputs for the English-medium NCERT Mathematics and Science extraction. Start with the [index of 130 official chapter PDFs](output/01_inventory_and_eda/README.md), grouped by class and subject. The [inventory manifest](output/01_inventory_and_eda/ncert_inventory/manifest.json) records the source URLs, book codes, physical page counts, and file hashes used in the run.

## Notebooks and outputs

Each notebook includes its saved cell outputs. Its corresponding folder in [output](output/) contains the Kaggle execution log and any files saved by that stage.

| Notebook | Kaggle version | Saved outputs |
| --- | ---: | --- |
| [01 Inventory and EDA](01_inventory_and_eda.ipynb) | 4 | [Inventory folder](output/01_inventory_and_eda/) with the official PDF links, manifest, and gap report |
| [02 GPU parsing](02_parse_gpu.ipynb) | 3 | [MinerU outputs](output/02_parse_gpu/ncert_parsed/) with page Markdown, structured JSON, images, and worker logs. [Parse summary](output/02_parse_gpu/ncert_parsed/summary.json) |
| [03 Content preparation](03_prepare_content.ipynb) | 4 | [Candidate passages](output/03_prepare_content/ncert_prepared/candidate_passages.jsonl), [page audit](output/03_prepare_content/ncert_prepared/page_audit.jsonl), and [EDA report](output/03_prepare_content/ncert_prepared/eda_report.json) |
| [04 Embeddings](04_embed_gpu.ipynb) | 2 | [Candidate vectors](output/04_embed_gpu/ncert_embeddings/candidate_vectors.npz) and [embedding manifest](output/04_embed_gpu/ncert_embeddings/embedding_manifest.json). The archive aligns vectors with passage IDs. |
| [05 Supabase load](05_load_supabase.ipynb) | 5 | [Database schema](output/05_load_supabase/ncert_schema.sql) and [load log](output/05_load_supabase/ncert-class-6-10-supabase-load.log) |
| [06 Query routing](06_route_query.ipynb) | 7 | [Routing README](output/06_route_query/README.md), [results JSON](output/06_route_query/routing_results.json), and [run log](output/06_route_query/ncert-class-6-10-topic-route.log) |

## Verified results

- The corrected inventory covers **130 PDFs and 3,066 physical pages**. The parse produced **3,047 nonempty pages and 19 empty pages**, with zero reported page errors. The parser download contains **21,779 files**.
- Preparation produced **7,221 candidate passages**. The pinned `Qwen/Qwen3-Embedding-0.6B` model produced one **1,024-dimensional vector** per passage. The downloaded vector and passage files matched the recorded hashes, and their passage ID order matched.
- The saved Supabase log records candidate release `9aea0ce28990f86074b2d813` with **7,221 passages** in the `ncert_research` schema. A live database dump is unavailable in this package.

The passages are research candidates. Review flagged maths notation, tables, figures, and OCR fragments against the linked PDFs before approving them as teaching evidence. Stages 01–05 use the saved Kaggle runs. Stage 06 was rerun on 17 November 2026 using the saved preparation and embedding outputs.
