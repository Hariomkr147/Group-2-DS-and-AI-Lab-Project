---
title: Qwen3.5-4B Socratic Tutor
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
  - IITM-2026T3-DSAI-GROUP2/qwen3.5-4b-socratic-tutor
  - Qwen/Qwen3.5-4B
---

# Qwen3.5-4B Socratic Tutor

Demo of the [fine-tuned Socratic tutor](https://huggingface.co/IITM-2026T3-DSAI-GROUP2/qwen3.5-4b-socratic-tutor)
built by Group 2 for the Data Science and AI Lab project, IIT Madras BS programme.

Enter a problem and its correct answer, then chat as the learner. The tutor replies with one guiding question
or hint at a time and should not state the final answer.

- Base model `Qwen/Qwen3.5-4B` with the team's LoRA adapter, both at pinned revisions.
- Runs on ZeroGPU in bf16. Replies are limited to 96 new tokens and use greedy decoding.
- The API endpoint `/predict` takes a system prompt and one message and returns the reply.

This is a research demo. Replies can be wrong and are not approved for use with real learners.
