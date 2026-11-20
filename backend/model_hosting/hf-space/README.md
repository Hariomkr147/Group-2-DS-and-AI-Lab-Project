---
title: Qwen Socratic Tutor
emoji: 🎓
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.32.0
app_file: app.py
short_description: Fine-tuned Qwen that tutors with questions, not answers
python_version: "3.12"
startup_duration_timeout: 30m
models:
  - IITM-2026T3-DSAI-GROUP2/qwen3-4b-ai-tutor-lora-latest
  - Qwen/Qwen3-4B-Instruct-2507
---

# Qwen Socratic Tutor

Demo of the [fine-tuned Socratic tutor](https://huggingface.co/IITM-2026T3-DSAI-GROUP2/qwen3-4b-ai-tutor-lora-latest)
built by Group 2 for the Data Science and AI Lab project, IIT Madras BS programme.

Enter a problem and its correct answer, then chat as the learner. The tutor replies with one guiding question
or hint at a time and should not state the final answer.

- The default test adapter uses `Qwen/Qwen3-4B-Instruct-2507`. Set `QWEN_ADAPTER_ID` and `QWEN_ADAPTER_REVISION` in Space settings to switch checkpoints. The base model comes from the adapter metadata.
- Runs on ZeroGPU in bf16. Replies are limited to 192 new tokens and use greedy decoding.
- The Gradio endpoint `/predict` returns a plain reply. `/predict_grounded` returns the reply and the status fields used by NCERT chat.

This is a research demo. Replies can be wrong and are not approved for use with real learners.
