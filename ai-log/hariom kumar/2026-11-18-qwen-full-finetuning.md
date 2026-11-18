# Qwen full finetuning (2026-11-18)

## Prompts
1. Assess the two tutoring datasets against the TA's science and context feedback and build the full-data Milestone 4 Unsloth Qwen3.5 notebook.
2. Check whether the notebook can run on Kaggle and which inputs must be attached.
3. Confirm science dataset sufficiency, required Kaggle uploads, and expected runtime for Save & Run All.
4. Deliver the final mixed maths and science notebook and reduce repeated work while preserving the full training recipe.
5. Launch the mixed notebook on Kaggle unattended with a 12-hour limit.

## Links
- https://huggingface.co/datasets/IITM-2026T3-DSAI-GROUP2/socratic-tutoring-dataset
- https://huggingface.co/datasets/IITM-2026T3-DSAI-GROUP2/preprocessed_tutor_ncrtinclude_data
- https://huggingface.co/datasets/FoundryAILabs/k12-indian-curriculum-4.9m
- https://unsloth.ai/docs/models/qwen3.5/fine-tune
- https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements
- https://www.kaggle.com/docs/notebooks
- https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4
- Milestone 4 brief, M3 Qwen notebook and report, existing M4 Qwen helpers, NCERT extraction README.

## Tools and packages
- Codex (GPT-6), PowerShell, Python, Hugging Face Hub, Transformers, pandas and nbformat. The notebook uses Unsloth, PyTorch, PEFT and bitsandbytes on GPU.

## What the AI did
- Created `notes/hariom kumar/milestone-4/model_finetune/qwen35_unsloth_full.ipynb`.
- Read the mixed JSONL splits and matched the original maths files byte-for-byte to the pinned Hub release. Counted 900 single-exchange science examples and 294 original maths test questions in the mixed training set.
- Validated notebook structure and code syntax. Encoded every original maths training and validation dialogue on CPU with the pinned tokenizer and checked target preservation. Exercised science seed export, split checks, and the optional mixed-input path with a small fixture.
- Checked the notebook's Kaggle requirements and confirmed that the default maths run downloads its datasets from Hugging Face. The mixed run needs the reviewed science splits attached separately.
- Added an eight-hour Kaggle training budget and previous-output restore setting. Tested the checkpoint stop, output copy and Trainer resume with a tiny CPU model.
- Estimated single-T4 training time from the Milestone 3 run rather than treating it as a measured runtime for Unsloth.
- Rechecked the current HF revisions. Changed the default to full maths plus science QA under an explicit teacher answer-key prompt. Added paired science tutoring probes. The reviewed-dialogue input remains available.
- Reused the frozen backbone across fresh adapters, added cached Parquet windows and a measured fit ETA. Ran the combined data pipeline on CPU, checked every eligible science target, restored the cache, and checked adapter reset after an optimizer update in a tiny model.
- Submitted private Kaggle version 1 with internet enabled, a T4 accelerator and a 43,200-second limit. Set training to checkpoint after 11 hours 45 minutes. The Kaggle API confirmed RUNNING.

## Notes
- The mixed run is underway. Training completion, adapter quality and the TA's multi-turn science target remain outstanding. Test partitions are reserved.
