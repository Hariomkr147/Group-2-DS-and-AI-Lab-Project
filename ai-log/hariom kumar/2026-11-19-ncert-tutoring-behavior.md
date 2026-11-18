# NCERT tutoring behavior (2026-11-19)

## Prompts
1. Make the NCERT tutor explain concepts, ask follow-up questions, and guide students through problems without giving the exact answer.

## Links
- Screenshot and Class 6 Maths “2.1 Point” lesson from the chat.

## Tools and packages
- Codex (GPT-6), pytest, Playwright, Vite, Supabase, and the hosted Qwen tutor.

## What the AI did
- Added separate prompts for explanations, hints, problem guidance, and reviewing student work. Updated follow-up routing and chat labels.
- Tested the reported Point lesson, the hint button, arithmetic result suppression, and feedback on a wrong step. Ran a smoke check with the approved Point passage and the hosted model.

## Notes
- Simple arithmetic checks use the existing evaluator. Open-ended textbook exercises rely on the model prompt and output checks. Render deployment was not part of this run.
