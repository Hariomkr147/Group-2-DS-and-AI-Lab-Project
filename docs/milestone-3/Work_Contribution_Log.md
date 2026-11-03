# Work Contribution Log: Milestone 3

**Project:** Socratic AI Tutor: guiding a learner to the answer through probing questions
**Team:** Group 2, Data Science and AI Lab, IIT Madras BS

## Team

| Name | Roll number | Primary role |
|---|---|---|
| Sandeep Nalla | 21f1006125 | Backend developer |
| Hariom Kumar | 23f2004225 | Build the RAG (search) agent |
| Hariom Pandey | 21f3002112 | Build the fine-tuned models |
| Mrityunjay Chakraborty | 21f3001385 | Frontend developer |

These are primary roles only. They are not fixed: as the project needs, members contribute to other parts as well.

## Work split for this milestone

| Area | Owner | Models compared |
|---|---|---|
| Knowledge tracing (DKT) and Qwen Socratic model | Hariom Pandey | DKT; Qwen3.5-4B |
| Knowledge tracing (BKT, AKT) and backtracking / misconception detection | Mrityunjay Chakraborty | BKT, AKT; LLM call as the misconception detector |
| Socratic response model | Sandeep Nalla | Gemma 4 E4B, Phi-4-mini-instruct, other models if time allows |
| Search (RAG) and NCERT embeddings | Hariom Kumar | Embedding models and vector stores |

## Contributions

Each member fills in their own row before sign-off. Entries below are what is recorded so far.

| Name | Work done |
|---|---|
| Sandeep Nalla | Built the candidate subset for Socratic-model experiments (2,000 train, 150 validation and 200 test conversations, seeded, no problem shared across splits, MathDial and SocraTeach both kept) and its statistics; wrote the zero-shot baseline evaluation script (ROUGE-L, question rate, reply length, per source); *to fill in: baseline results for Gemma 4 E4B and Phi-4-mini-instruct, LoRA tuning runs, comparison plots, report sections for the Socratic models* |
| Hariom Kumar | *to fill in* |
| Hariom Pandey | *to fill in* |
| Mrityunjay Chakraborty | *to fill in* |

## Sign-off

By signing, each member confirms that this log is accurate and that they have reviewed the report and presentation.

| Name | Roll number | Signature | Date |
|---|---|---|---|
| Sandeep Nalla | 21f1006125 | | |
| Hariom Kumar | 23f2004225 | | |
| Hariom Pandey | 21f3002112 | | |
| Mrityunjay Chakraborty | 21f3001385 | | |
