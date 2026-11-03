# Qwen3.5-4B Socratic tutor: baseline and fine-tuning (Milestone 3)

`qwen35_socratic_baseline_finetune.ipynb` scores the pretrained Qwen3.5-4B (4-bit) as a tutor,
runs a small LoRA grid search, trains the best setting on the candidate set and scores it again
on the same 200 validation contexts.

## Run on Kaggle

1. Create a Kaggle dataset from `notes/hariom kumar/milestone-3/socratic_data_prep/processed/`. It needs `candidate_train.jsonl.gz` and `candidate_val.jsonl.gz`.
2. Create a notebook and upload `qwen35_socratic_baseline_finetune.ipynb`. In the settings, set Accelerator to GPU T4 and switch Internet on.
3. Add the dataset as an input. The notebook finds `candidate_train.jsonl.gz` under `/kaggle/input/` by itself.
4. Run all cells. Results go to `/kaggle/working/qwen35_socratic_ft/`: `results.json`, the `generations_*.csv` files, `figures/` and `lora_adapter/`. Download that folder before the session ends.

## What it measures

Leak rate, question rate, ROUGE-L, BLEU, reply length and masked validation loss. The same numbers
for the real tutors on the same contexts are included as a reference.

## Before you rely on it

- The code was run end to end on CPU with `SMOKE_TEST = True`, which uses a tiny random Qwen3.5 model.
  The prompt rendering matches the official chat template. The loss mask was checked on 1,744
  candidate dialogues with no mismatch.
- The GPU parts have not run yet: 4-bit loading, fp16 numerics on the T4, the flash-linear-attention kernels and the training speed.
- Training speed on a T4 is unknown. Check `train_minutes` after the first grid setting and shrink `GRID` or `GRID_TRAIN` if needed.
- Unsloth's Qwen3.5 guide advises against 4-bit QLoRA for this model family. The notebook therefore also baselines the fp16 model, so the cost of 4-bit is measured.
