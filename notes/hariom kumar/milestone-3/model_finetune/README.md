# Socratic tutor model fine-tuning (Milestone 3)

Hariom Kumar · Group 2, DS & AI Lab, IIT Madras BS · 5 November 2026

This folder holds the fine-tuning experiments for the tutor's **Socratic response model**: given a maths word problem and the conversation so far, write the next tutor turn as a short question or hint, without stating the final answer.

Four models were fine-tuned with LoRA on Kaggle T4 GPUs. Three of them share one protocol and can be compared directly. **Read [report.md](report.md) for the full method, results and comparison.**

| Model | Notebook | Output folder | Result |
|---|---|---|---|
| Qwen 3.5-4B | `qwen-finetuning.ipynb` | `Qwen_finetune_output/qwen35_socratic_final/` | **Selected.** ROUGE-L 0.331, 0 leaks |
| Gemma 4 E4B | `gemma-finetunning.ipynb` | `gemma_finetune_output/gemma4_e4b_socratic_final/` | ROUGE-L 0.319, 0 leaks |
| Phi-4-mini | `notes/sandeep/milestone-3/model_finetune/phi4mini-finetuning.ipynb` (Sandeep, same protocol) | Hugging Face: `IITM-2026T3-DSAI-GROUP2/Phi-4-mini-instruct-socratic-tutor` | ROUGE-L 0.294, 0 leaks |
| Qwen3-4B-Instruct-2507 (early trial) | `claudeaisocratic.ipynb` | Kaggle output only (`lora_adapter.zip`) | Different data and protocol; loss only, not ranked |

## Shared protocol (Qwen 3.5, Gemma, Phi)

| Step | Setting |
|---|---|
| Data | `candidate_train`: 1,000 SocraTeach + 1,000 MathDial dialogues; `candidate_val`: 100 + 100 (built in `../socratic_data_prep`) |
| Prompt | System prompt with the problem, the correct answer (for checking only) and, for MathDial, the student's first attempt |
| Training targets | Tutor turns only; turns that give away the answer, and MathDial "telling" turns, are context without loss |
| Baseline | Pretrained model in 4-bit NF4, no training |
| Grid search | 3 LoRA settings on the same 400 dialogues: r8 at 2e-4, r16 at 2e-4, r8 at 5e-5 |
| Selection rule | Lowest validation loss among settings that leak at most 2 points more than real tutors |
| Final model | Selected setting on all ~2,000 dialogues, 1 epoch |
| Evaluation | Same 100 validation contexts (50 per source), greedy decoding, ≤96 new tokens |
| Metrics | Leak rate, question rate, words per reply, ROUGE-L, BLEU, validation loss (within a model only) |

## Folder contents

| Path | What it is |
|---|---|
| `report.md` | Milestone 3 report: model selection and justification, baselines, candidate data, tuning, pipeline, results, comparison |
| `figures/model_comparison.png`, `figures/grid_search.png` | Comparison charts used in the report |
| `*_finetune_output/*/results.json` | All metrics: real tutors, baseline, grid, selected setting, final model, overall and per source |
| `*_finetune_output/*/generations_*.csv` | Every model reply beside the real tutor's reply, for reading side by side |
| `*_finetune_output/*/eval_contexts.csv` | The 100 evaluation contexts (identical across models) |
| `*_finetune_output/*/adapters/final_lora_r16_lr0.0002/` | Final LoRA adapter config (weights stay on Kaggle / Hugging Face) |
| `*_finetune_output/*/figures/results.png` | Per-model training curves and metrics |
| `*_finetune_output/*/run_cache.json` | Resume cache written by the notebook |

## Re-run on Kaggle

1. Accelerator **GPU T4 x2** (one GPU is used), Internet **on**.
2. Attach the dataset with `candidate_train.jsonl.gz` and `candidate_val.jsonl.gz` (https://www.kaggle.com/datasets/hariomkr/socratic-test-db).
3. **Save Version → Save & Run All (Commit).** A run that stops can resume: attach its output folder as input and commit again.

Training the final model takes about 49 min (Phi-4-mini), 62 min (Gemma) and 80 min (Qwen 3.5) on one T4.

## Host the selected Qwen model

Use [hosting-qwen.ipynb](../model_hosting/hosting-qwen.ipynb) to load the published model automatically and generate a temporary API URL and key. Follow the [Colab and Kaggle hosting setup guide](../model_hosting/README.md) for setup, API examples, troubleshooting, and stopping the endpoint. Hosting uses an interactive session rather than the background training workflow above.

## Licence

SocraTeach is CC BY-NC 4.0 and MathDial is CC BY 4.0, so all adapters are for non-commercial use. Base models: Qwen 3.5 (Apache 2.0), Phi-4-mini (MIT), Gemma 4 (Gemma terms of use).
