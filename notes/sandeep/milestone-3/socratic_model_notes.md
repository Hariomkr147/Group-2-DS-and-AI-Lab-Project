# Socratic Model - Project Notes

## 1. Models chosen for fine-tuning

| Model | Owner | Notes |
|---|---|---|
| Qwen3.5-4B | Hariom Pandey | Follows the Qwen3-4B plan from Milestone 1 |
| Gemma 4 E4B | Sandeep | "Effective" 4B, larger on disk (see section 5) |
| Phi-4-mini-instruct (3.8B) | Sandeep | Strong at math reasoning; may leak answers more, so check leakage |

Likely reasons (inferred, to confirm with teammate):
- All about 4B, so LoRA fits on a free Colab/Kaggle GPU.
- Three different families, so the comparison is fair.
- Open licences, and our own model stays the main brain (TA ruling).

Plan: run zero-shot baselines first, then fine-tune the best one or two. Add a smaller (1-2B) or an 8B model only if time allows.

## 2. LoRA

- Freeze the base model and train small low-rank matrices (A and B) added to selected layers.
- Trains about 0.1-1% of the parameters, so memory and time are low.
- Output is a small adapter (tens of MB) loaded on top of the base model.
- QLoRA = LoRA on a 4-bit base model (fits an 8B model on a free GPU).
- Settings: `r` (rank, 8/16/32), `lora_alpha`, `target_modules` (attention layers), `lora_dropout`.

## 3. Transfer learning

- Reuse a model pre-trained on a large general dataset and adapt it to a new task with a small dataset.
- Here: base model knows language and math; fine-tuning on MathDial and SocraTeach teaches the Socratic tutor behaviour.
- Works when the new task is close to what the model has seen. Weaker for harder topics (risk for IITM BS).

## 4. Datasets and licences

- MathDial: CC BY-SA 4.0 (GitHub) / CC BY 4.0 (Hugging Face). We follow the stricter one.
- SocraTeach Multi: CC BY-NC 4.0 (non-commercial; fine for coursework, say so in the report).
- Both are grade-school word problems, not NCERT or IITM BS content.
- Decision: no NCERT/IITM BS fine-tuning data. Socratic style comes from these datasets; subject content comes from the base model and retrieved course material in the prompt.
- Still needed: a small NCERT/IITM BS test set (30-50 scenarios) for evaluation only.

## 5. Why Gemma E4B is larger than Phi-4-mini

(From the Gemma 3n design; check the Gemma 4 E4B model card to confirm.)
- "E" = effective parameters. Large per-layer embedding tables are stored but cheap to compute, so stored size is bigger than 4B.
- Checkpoint also includes vision (maybe audio) encoders; Phi-4-mini is text only.
- Very large vocabulary (about 256k) means a bigger embedding table.
- Observed file sizes: Gemma 4 E4B about 16 GB, Phi-4-mini about 8 GB. At 2 bytes per parameter (16-bit) that is about 8B stored for Gemma and 3.8B for Phi-4-mini.
- Effect: bigger download, more GPU memory; compute per token is close to a 4B model.
- A free T4 has 16 GB, so Gemma in 16-bit will not fit for training. Use 4-bit QLoRA (about 5-6 GB). Phi-4-mini fits with plain LoRA. State which method each model used in the report.
- Report both effective and total parameters in the comparison table.

## 6. Existing tutor models (baselines / starting points)

Details are from search results; check licence and size on each page before citing.

| Model | Base | Link |
|---|---|---|
| MathDial-SFT-Qwen2.5-1.5B-Instruct | Qwen2.5 1.5B | https://featherless.ai/models/eth-nlped/MathDial-SFT-Qwen2.5-1.5B-Instruct |
| TutorRL-7B (Apache-2.0) | Qwen2.5-7B | https://huggingface.co/eth-nlped/TutorRL-7B |
| TutorRL-7B-think | Qwen2.5-7B | https://huggingface-proxy.pages.dev/eth-nlped/TutorRL-7B-think |
| SocraticLM (gated) | Qwen2.5-Math-7B (HF); ChatGLM3-6B (paper) | https://huggingface.co/CogBase-USTC/SocraticLM |
| qlm-math-tutor | Llama 3.1 8B + LoRA | https://huggingface.co/QuantumLearningMachines/qlm-math-tutor |
| Eduardo-27b (too large, cite only) | 27B | https://huggingface.co/eth-nlped/Eduardo-27b |
| SmolSocrates-360M (coding tutor, size reference) | 360M | https://huggingface.co/kushalicious/SmolSocrates-360M |

Papers: TutorRL https://arxiv.org/abs/2505.15607 ; SocraticLM https://neurips.cc/virtual/2024/poster/93477

Use: MathDial-SFT-1.5B and TutorRL-7B as published baselines on our 200-conversation test set. No small open tutor for NCERT was found.

## 7. Evaluation idea

Compare on leakage, ROUGE-L, question rate and the rubric:
1. Base model + Socratic prompt (no training)
2. Published tutor model
3. Our fine-tuned model
Use a strong model as judge for leakage and the rubric.
