# Qwen model fine-tuning and evaluation (2026-11-19)

**Contributor:** Hariom Kumar  
**Context:** Milestone 4 Unsloth Qwen3.5-4B Socratic fine-tuning on Kaggle GPU across mixed Mathematics and Science datasets, checkpoint management, and quantitative evaluation.

## 1. AI Tools Utilized

- **Tool Name:** Antigravity and Codex (GPT-6)
- **Purpose of Use:** Unsloth training script configuration, Kaggle CLI execution and checkpoint recovery, evaluation script creation, and metric aggregation.
- **Shared Chat Link / Conversation File:** Local CLI interaction logs.
- **Contribution and Validation:** I designed the fine-tuning recipe, curated and balanced the mixed Maths (MathDial) and Science (SocraTeach / Science QA) datasets, engineered the Kaggle 12-hour checkpoint and resume workflow, and evaluated the model on 40 paired science probes and 240 validation dialogues. I verified all loss curves, checkpoint integrity, and generated report artifacts.

## 2. My Contribution and Independent Engineering

I designed and directed the fine-tuning and evaluation workflow for our Milestone 4 Socratic tutor:
1. Dataset preparation and curation: Combined mathematical dialogue datasets (MathDial with 294 test questions) and curriculum science questions (FoundryAILabs / IITM preprocessed with 900 single-exchange examples and SocraTeach) to address TA feedback and prevent catastrophic forgetting of scientific concepts.
2. Socratic prompting architecture: Formulated teacher prompts enforcing explicit answer-key grounding, requiring the model to guide students through progressive hints rather than providing direct answers.
3. Training configuration: Configured Unsloth Qwen3.5-4B with 4-bit base quantization and LoRA adapters (rank r=16, alpha=32, target modules: q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj, down_proj).
4. Cloud timeout engineering: Engineered a reliable checkpoint and resume workflow on Kaggle GPU instances to handle the 12-hour execution limit. Configured training to save full adapter, optimizer, scheduler, and RNG state at 11 hours 45 minutes (step 2,380 of 3,073) and resumed execution to complete all 3,073 steps.
5. Systematic evaluation and reporting: Evaluated validation loss across all three data splits (MathDial: 1.7196, Science QA: 1.0517, SocraTeach: 0.8193), evaluated 40 paired science tutoring probes (80 outputs comparing base vs fine-tuned model behavior), and authored the Milestone 4 report in `notes/hariom kumar/milestone-4/model_finetune/report.md`.

## 3. Significant Prompts and Responses

| Problem Addressed | Prompt (as typed) | Relevant AI Response | Action Taken |
|---|---|---|---|
| Dataset mixing and pipeline | `Configure an Unsloth fine-tuning notebook for Qwen3.5-4B on Kaggle T4 GPU. We need to train LoRA adapters (r=16, alpha=32) on a mixed dataset: MathDial mathematical dialogues and Indian curriculum science QA (FoundryAILabs / IITM preprocessed) under an explicit teacher answer-key prompt to ensure both maths and science tutoring capabilities.` | Drafted data loading, tokenization pipeline, and chat template formatting with teacher answer-key prompts. | Verified byte-level token encoding, confirmed 900 science examples and 294 maths test questions integrated cleanly into training splits. |
| Kaggle session timeout | `Kaggle has a strict 12-hour session timeout. Configure our Hugging Face Trainer to monitor elapsed execution time and trigger a clean checkpoint save at 11 hours 45 minutes, preserving LoRA adapter weights, optimizer state, scheduler, and RNG state to allow seamless continuation in a resumed session.` | Added time-based callback in training loop saving full state dictionary and stopping before hard platform eviction. | Validated checkpoint saving on a dry-run fixture; scheduled production run on Kaggle GPU. |
| Continuation run | `Version 1 completed step 2,380 of 3,073 before the 11h45m checkpoint. Prepare the continuation notebook configuration to restore optimizer and scheduler states from the checkpoint output, complete the remaining 693 training steps, and verify that the learning rate schedule continues smoothly.` | Configured resume script setting checkpoint path in Trainer.train(resume_from_checkpoint=...) and preserving output directories. | Submitted continuation notebook to Kaggle; confirmed run completed all 3,073 steps with smooth loss convergence. |
| Evaluation pipeline | `At evaluation setup, raw quantized base comparison threw an error. Fix the evaluation pipeline to load the base backbone and disable LoRA adapter contributions during baseline inference, generating side-by-side transcripts for 240 validation dialogues and 40 paired science tutoring probes.` | Updated evaluation script to toggle adapter activation via model.disable_adapters() during baseline runs, avoiding duplicate model reloading. | Generated 240 validation transcripts and 80 paired science probe outputs for comparative analysis. |
| Metrics and reporting | `Aggregate validation loss metrics across MathDial, Science QA, and SocraTeach splits. Generate learning curve plots comparing training loss against validation loss, count Socratic inquiry markers (question mark frequency) across the 40 paired science probes, and draft the Milestone 4 report in notes/hariom kumar/milestone-4/model_finetune/report.md.` | Aggregated validation metrics, generated matplotlib loss curve figures, and drafted structured Markdown report. | Embedded verified metrics (MathDial: 1.7196, Science QA: 1.0517, SocraTeach: 0.8193) and plots into final report. |

## 4. Reasoning I Can Substantiate in Review

- Mixed curriculum fine-tuning: Fine-tuning exclusively on MathDial causes catastrophic forgetting of scientific reasoning and physical terminology. Mixing Science QA with MathDial maintains domain balance across Classes 6 to 10 curricula.
- LoRA parameter efficiency: Training full 4B parameters requires multiple enterprise GPUs. LoRA adapters with rank 16 and alpha 32 on all linear projections allow high-quality adaptation on a single Kaggle T4 GPU while keeping final adapter weights under 100MB.
- Socratic behavior via prompt formatting: Enforcing an explicit answer-key format in the prompt prevents the model from hallucinating false mathematical calculations while training it to offer progressive hints rather than direct answers.
- Resumable training design: Kaggle timeouts corrupt model files if interrupted mid-epoch. A timed checkpoint at 11h45m guarantees clean state persistence and reproducible resumption.

## 5. Validation Record

- Completed all 3,073 training steps across initial run (step 2,380) and continuation run.
- Verified tuned validation loss across splits: 1.7196 on MathDial, 1.0517 on Science QA, 0.8193 on SocraTeach.
- Evaluated 80 science tutor probe outputs (40 base vs 40 fine-tuned) demonstrating consistent Socratic inquiry.
- Verified notebook execution and output artifacts in `notes/hariom kumar/milestone-4/model_finetune/qwen35_unsloth_full.ipynb` and `notes/hariom kumar/milestone-4/model_finetune/report.md`.

## 6. Team Accountability Declaration

- All AI-assisted code, models, and test cases incorporated into this stage have been reviewed and appropriately validated by me.
- Architectural decisions, benchmark methodologies, model choices, and edge-case guards are supported by my independent reasoning and experimental verification.
- I understand all contributions and can explain, justify, debug, and defend the fine-tuning methodology and evaluation results independently during review and assessment.

**References:** `notes/hariom kumar/milestone-4/model_finetune/qwen35_unsloth_full.ipynb`, `notes/hariom kumar/milestone-4/model_finetune/report.md`, Kaggle notebook `qwen35-mixed-socratic-tutor-m4`.
