# Milestone 4 · Full training of the Socratic tutor

**Group 2 · IIT Madras BS Data Science & AI Lab · 19 November 2026**

**Component owner** Hariom Kumar (23f2004225)  
**Companion notebook** [Qwen3.5-4B Unsloth training and verified run results](qwen35_unsloth_full.ipynb)

## 1. Training scope and success criteria

Milestone 3 screened Qwen3.5-4B, Gemma 4 E4B and Phi-4-mini on candidate dialogues. Milestone 4 carried forward Qwen3.5-4B, trained on the full eligible maths split, added NCERT/CBSE-aligned science Q&A, and raised the training context from 768 to 2,048 tokens. The final adapter completed one epoch in **3,073 optimizer steps**. This phase varied learning rate and weight decay while holding the architecture, adapter rank, batch size, seed and schedule family fixed. [Milestone 3 candidate report](../../milestone-3/model_finetune/report.md) · [Kaggle evaluation output](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation/output)

| Criterion set in the notebook | Observed outcome |
| --- | --- |
| Lower validation loss than the base model for each source | Met for MathDial, SocraTeach and science Q&A |
| Premature numeric answers in at most 3% of checkable maths replies | Met on this sample, with 0 of 54 flagged |
| At least 80% of reviewed student-facing science replies are factually grounded and elicit reasoning | Human scoring pending. The paired probes show a shift toward direct answers after tuning |

## 2. Data and preprocessing

Group 2's prepared maths release combines SocraTeach Multi and MathDial. The second release contains 1,500 curriculum Q&A records sourced from FoundryAI Labs. This run used the 900 records tagged science. They are single-turn questions with direct answers and lack the passage and chapter metadata needed for chapter-level isolation. [Prepared maths release](https://huggingface.co/datasets/IITM-2026T3-DSAI-GROUP2/socratic-tutoring-dataset) · [Curriculum subset](https://huggingface.co/datasets/IITM-2026T3-DSAI-GROUP2/preprocessed_tutor_ncrtinclude_data/blob/58b86defbec43a2c8d520ee1419b7425027f7d7e/manifest.json) · [Upstream curriculum Q&A](https://huggingface.co/datasets/FoundryAILabs/k12-indian-curriculum-4.9m)

| Source | Train before masking | Train used | Validation records | Reserved test records |
| --- | ---: | ---: | ---: | ---: |
| SocraTeach Multi | 22,574 | 22,574 | 2,682 | 0 |
| MathDial | 1,302 | 1,296 | 311 | 599 |
| Science Q&A | 708 | 708 | 95 | 97 |
| **Total** | **24,584** | **24,578** | **3,088** | **696** |

The training notebook used the pinned `train.jsonl.gz`, `val.jsonl.gz`, and `test.jsonl.gz` maths files. The maths release partitions by problem, caps train and validation at three dialogues per problem, and reserves the official MathDial test split. The notebook checks split overlap using dialogue IDs, problem IDs and normalized questions. It checks chapter and passage identifiers when present. The published science subset supports question-level checks. Chapter-level isolation requires chapter metadata for the future grounded dataset. The test records supplied split-check keys and stayed unused for model fitting, selection, and scoring.

Student turns and system instructions are context. The loss covers eligible maths tutor turns and their end-of-turn tokens, masking tutor turns flagged as telling or leaking the answer. Science Q&A uses a teacher answer-key prompt with the answer as the target. Tokenized records are cached in Parquet. When a dialogue exceeds 2,048 tokens, later windows repeat the problem prefix and up to 256 preceding dialogue tokens. The notebook masks repeated targets so that each eligible token contributes once.

Under the Milestone 4 template, 981 of 23,876 maths training dialogues exceeded 768 tokens and all fit within 2,048. Two maths validation dialogues exceeded 2,048. Six training and seven validation dialogues had zero eligible targets after masking. The final validation contains **3,082 scored windows**, including overlapping windows. This length audit uses the full Milestone 4 data mix and tokenizer template, which differ from the earlier candidate audit.

The full epoch used natural source frequencies, about **91.8% SocraTeach, 5.3% MathDial, and 2.9% science Q&A** by training records. The pilot and monitoring sets were source-balanced, and final results are broken out by source. The final fit used neither source weighting nor oversampling. Source imbalance remains relevant when interpreting the science and MathDial results.

## 3. Architecture and training configuration

The text backbone has 32 decoder layers at hidden size 2,560. It alternates 24 Gated DeltaNet linear-attention layers with eight gated full-attention layers, with feed-forward blocks and built-in RMS normalization. It predicts a distribution over 248,320 tokens. This text run froze the 4-bit base and vision tower. LoRA updated language attention and MLP projections. The Kaggle run reported **32,464,896 trainable weights** out of **4,571,730,432 loaded parameters**, about **0.71%**, including the loaded vision components in the denominator. [Qwen3.5-4B model card](https://huggingface.co/unsloth/Qwen3.5-4B) · [Initial Kaggle run](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4)

| Setting | Final value |
| --- | --- |
| Model and tokenizer | `unsloth/Qwen3.5-4B` at `3764fa359b9082ea5a1e4a5e3ac3aaf6e9671636` |
| Maths dataset revision | `6edd4d26866b857ac86c29d1a6aac37074389edf` |
| Curriculum Q&A revision | `58b86defbec43a2c8d520ee1419b7425027f7d7e` |
| Objective | Masked causal cross-entropy over eligible assistant tokens, with equal target-token weights and label `-100` for masked tokens |
| Adapter | LoRA rank 16, alpha 16, dropout 0, no trainable bias |
| Optimizer | 8-bit AdamW with betas 0.9 and 0.999, epsilon 1e-8, weight decay 0.01 |
| Learning rate and schedule | 0.0002, 5% warm-up rounded up to 154 steps, then cosine decay |
| Gradient clipping | Global norm capped at 1.0 |
| Batch and duration | One dialogue window per microbatch, eight accumulation steps, effective batch size eight, one epoch |
| Hardware and precision | One active Tesla T4 GPU, 4-bit frozen weights, FP32 fallback, Unsloth gradient checkpointing |
| Logging and checkpoint selection | Log every 10 steps and at the end. Evaluate and checkpoint every 250 steps and at the end. Keep the checkpoint with the lowest monitoring validation loss |
| Reproducibility | Seed 42, Unsloth 2026.11.6, Transformers 5.17.0, PyTorch 2.11.0+cu130, PEFT 0.21.2 |

For eligible next-token positions $E$, the objective is $-\sum_{t \in E}\log p_\theta(x_t \mid x_{<t}) / |E|$. The validation logs record masked loss, and the report gives perplexity as its exponential. Generation diagnostics use ROUGE-L, counts of question marks and empty replies, and a premature numeric-answer check where a reference number can be tested.

## 4. Hyperparameter search

The grid used 600 fixed pilot dialogues (200 per source), 48 monitoring dialogues per source, and 75 optimizer steps per trial. Every trial started from the same adapter initialization and a fresh optimizer and scheduler. All logged pilot losses and gradient norms were finite.

| Learning rate | Weight decay | Best monitoring loss ↓ |
| ---: | ---: | ---: |
| 0.00005 | 0.00 | 1.2594 |
| 0.00005 | 0.01 | 1.2599 |
| 0.00020 | 0.00 | 1.1864 |
| **0.00020** | **0.01** | **1.1828** |

With zero weight decay, the higher learning rate improved monitoring loss by 0.0730. At the higher rate, adding 0.01 weight decay improved loss by another 0.0036. At the lower rate, the same decay increased loss by 0.0005. The result supported the selected setting on this pilot. The small decay effect was measured with one seed. The notebook embeds the sweep plot. [Verified run figures](qwen35_unsloth_full.ipynb) · [Kaggle sweep output](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation/output)

## 5. Stability and convergence

| Signal | Observation |
| --- | --- |
| Logged training loss | 1.4326 at step 10 and 0.9158 at step 3,073. Each value averages its own recent training batches |
| Monitoring validation loss | 1.2989 at step 250, 1.2684 at 1,000, 1.2382 at 2,000 and 1.2268 at 3,073 |
| Gradient norms | All 308 logged values were finite. Median 1.0339, maximum 2.2967, and 167 values above the 1.0 clipping threshold before clipping |
| Checkpoint recovery | The first Kaggle session paused at step 2,380. The continuation restored the optimizer, scheduler and RNG state and finished at step 3,073 |

Monitoring loss decreased at every scheduled evaluation in the saved history and flattened near the end. The last training log was about 0.311 below the last monitoring loss. This gap compares a recent training batch average with a fixed validation subset. It is an observed diagnostic rather than an estimate of a technique's causal effect. Weight decay and learning rate were varied. Clipping, warm-up, normalization, and checkpointing were fixed. No domain augmentation or dynamic loss scaling was used in the reported fit. The notebook includes the full training-loss, validation-loss and gradient curves. [Learning curves and training history](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation/output)

## 6. Evaluation and observed tutor behaviour

The base and tuned conditions used identical validation windows. The base condition disabled adapter contributions on the same quantized backbone. ROUGE-L is the mean over 40 generation prompts per source.

| Source | Scored windows | Base loss ↓ | Tuned loss ↓ | Base perplexity ↓ | Tuned perplexity ↓ | Base ROUGE-L ↑ | Tuned ROUGE-L ↑ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| MathDial | 305 | 2.9447 | **1.7196** | 19.01 | **5.58** | 0.1956 | **0.2348** |
| Science Q&A | 95 | 1.5086 | **1.0517** | 4.52 | **2.86** | 0.2237 | **0.3394** |
| SocraTeach | 2,682 | 1.4564 | **0.8193** | 4.29 | **2.27** | 0.3288 | **0.4287** |

**Maths example.** A student had already worked out that candidate A received 20 votes and candidate B received 30. The tuned tutor acknowledged the calculation and asked for the candidates' combined votes, leaving that step to the student. Across both maths sources, the numeric check flagged one base reply and zero tuned replies among the same 54 checkable prompts. The check covers prematurely stated exact numbers.

**Science failure example.** Asked how tightening a guitar string affects pitch, the base prompted the student to reason about vibration. The tuned model directly explained the effect and gave the final answer. On the same 40 student-facing science prompts, 38 base replies and seven tuned replies contained a question mark. This count is a screening signal. Correctness, well-timed hints and answer leakage still require human scoring. The lower science loss above evaluates teacher answer keys, while these probes use the Socratic tutoring instruction.

**Sanity checks.** All six source-and-model validation losses were finite. The stored output contains 240 comparison transcripts and 80 science probe replies, with no empty replies in either set. [Validation CSV and paired outputs](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation/output)

### Comparison with earlier and published results

| Reference | Reported result | Evaluation protocol |
| --- | --- | --- |
| Milestone 3 candidate Qwen3.5-4B | MathDial ROUGE-L 0.244 and overall ROUGE-L 0.331 | 100 candidate validation contexts, 50 per maths source. [Candidate report](../../milestone-3/model_finetune/report.md) |
| Amrityunjay's Qwen3.5-4B | Validation perplexity 2.6093 and test perplexity 2.5956 | Own 512-token-filtered prompt-completion splits, with balanced maths dialogue sampling. [Peer Kaggle notebook](https://www.kaggle.com/code/amrityunjay/qwen-3-5-finetuning) |
| MathDial published Flan-T5-780M | 30% Success@5 and under 1% Telling@5 | Interactive student simulation over up to five tutor turns. [MathDial paper, Figure 5](https://aclanthology.org/2023.findings-emnlp.372.pdf) |

The reported values use different examples, scoring protocols or metrics. The same-window base-to-tuned comparison above supports the Milestone 4 loss claims. A common unseen benchmark and a shared tutoring rubric are needed to rank the fine-tuned adapters.

## 7. Artifacts and reproduction

The Kaggle working directory was `/kaggle/working/qwen35-m4/mixed-hf-qa-v2/`. Paths in this table are relative to that directory.

| Artifact | Path and source |
| --- | --- |
| Final adapter and tokenizer | `full/adapter/`, including `adapter_model.safetensors` and `adapter_config.json`. [Kaggle continuation output](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-resume/output) |
| Resumable training state | `full/checkpoint-3073/`, including adapter weights, optimizer and scheduler states, RNG state and `trainer_state.json`. [Kaggle continuation output](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-resume/output) |
| Configuration and run history | `run_config.json`, `data_revisions.json`, `requirements_runtime.txt`, `sweep.csv`, `sweep.png`, `full/history.json`, `full/summary.json` and per-run `training_args.json`. [Kaggle training logs](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-resume/log) |
| Validation and qualitative outputs | `validation.csv`, `transcripts.csv`, `science_tutor_probes.csv` and `learning_curves.png`. [Completed Kaggle evaluation](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation/output) |
| Reproducible code | [Final Jupyter notebook](qwen35_unsloth_full.ipynb) |

To reproduce the mixed-Q&A run, import the notebook into Kaggle, enable Internet, select a T4 GPU and run with `SCIENCE_DIR = None`. If the session pauses, attach its Notebook Output and set `RESUME_FROM` to the mounted `qwen35-m4/mixed-hf-qa-v2` directory. Keep the pinned model, tokenizer, data and GPU settings. The validation cell demonstrates loading the saved adapter and running inference with the pinned tokenizer. A separately verified single-command inference entry point remains outstanding.

Training completed before the first evaluation attempt raised a Transformers error when creating a Trainer around the bare quantized base. The corrected evaluation attached the saved adapter and disabled its contribution for the baseline. That evaluation completed using the same trained weights. [Completed recovery run](https://www.kaggle.com/code/hariom1407/qwen35-mixed-socratic-tutor-m4-evaluation)

## 8. Findings and Milestone 5 priorities

1. **Keep the long-context pipeline.** The measured 2,048-token limit retained all eligible training dialogues. For comparisons, include long conversational prompts and record when earlier context changes the tutor response.
2. **Address the science tutoring regression.** Build the TA's proposed 3,000–5,000 reviewed multi-turn science dialogues using cited NCERT passages and student misconceptions. Group by chapter and passage before splitting. Replace or ablate the answer-key Q&A targets and compare both adapters under the same student-facing prompt.
3. **Evaluate teaching behaviour directly.** Blind-review responses for factual grounding, useful next-step guidance and premature answers. Record denominators and agreement. Evaluate the final candidates on a common held-out benchmark after freezing selection.
4. **Isolate stability effects and complete reproducibility.** Compare clipping and warm-up with controlled runs at the selected learning rate, repeat the pilot across seeds if resources allow, and verify one-command inference from the final artifact.

## 9. Team review and submission

This report covers Hariom Kumar's Qwen training and evaluation component. The team-wide contribution log should record each member's Milestone 4 work. The submission also requires the PDF slides, code and model artifacts, and individual sign-offs. The rows below are for each member to complete after reviewing the report and code.

| Team member | Roll number | Review date | Signature or initials |
| --- | --- | --- | --- |
| Sandeep Nalla | 21f1006125 | Pending | Pending |
| Hariom Kumar | 23f2004225 | Pending | Pending |
| Hariom Pandey | 21f3002112 | Pending | Pending |
| Mrityunjay Chakraborty | 21f3001385 | Pending | Pending |

## Appendix · AI use and verification

Codex (GPT-6) assisted with the notebook, data and context audits, Kaggle submission and resume, diagnosis of the evaluation failure, comparison with the peer notebook, and this report draft. The AI logs contain shortened prompts and checks. Report figures and metrics were checked against the saved Kaggle CSVs, run configuration, and Trainer history. The adapter bytes were checked against the final checkpoint. Team review, the science tutoring rubric scores, and individual accountability confirmations remain pending. [Training and dataset AI log](../../../../ai-log/hariom%20kumar/2026-11-18-qwen-full-finetuning.md) · [Kaggle recovery AI log](../../../../ai-log/hariom%20kumar/2026-11-19-kaggle-time-limit.md) · [Course AI-use guidance](../../../../docs/ai-policy.md)
