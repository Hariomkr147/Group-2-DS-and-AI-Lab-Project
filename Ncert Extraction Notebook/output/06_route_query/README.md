# Automatic NCERT query routing

Kaggle version **7** completed on **17 November 2026** using a GPU T4 ×2 runtime. The run used content preparation **version 4** and embeddings **version 2**. [Executed notebook](../../06_route_query.ipynb) · [Run log](ncert-class-6-10-topic-route.log) · [Results JSON](routing_results.json)

## How routing works

The notebook verifies the hashes and passage ID alignment of the saved inputs. It embeds the learner's question with the pinned Qwen3-Embedding-0.6B model and compares it with **6,207 eligible passages** out of 7,221. It skips answer headings, passages flagged for answer leakage, and short fragments. The best-scoring passage for each chapter determines that chapter's rank. The router returns up to five distinct chapters with headings and source pages when the best match scores at least **0.60**.

## Saved run results

| Check | Result |
| --- | --- |
| Expected chapter ranked first | 16 of 20 |
| Expected chapter in the top five | 20 of 20 |
| Off-topic questions rejected | 10 of 10 |

For “How do I compare tenths and hundredths?”, the top result was **Class 7 Mathematics, Chapter 3, A Peek Beyond the Point**, on physical PDF page 44 with a similarity score of **0.7603**. The results JSON includes the full example shortlist and the per-question benchmark results.

This rerun used the existing small benchmark. The score cutoff needs validation on fresh learner questions before deployment. Routing remains a notebook feature, and the suggested passages retain candidate review status.

## Try another question on Kaggle

Open the notebook with GPU and Internet enabled. Attach the private [content preparation outputs](../03_prepare_content/ncert_prepared/) and [embedding outputs](../04_embed_gpu/ncert_embeddings/) as matching inputs. Run the setup and router cells, then edit the question in the last cell.
