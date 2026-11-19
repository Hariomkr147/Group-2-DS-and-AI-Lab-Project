# Model and chapter integration (2026-11-19)

## Prompts
1. Connect the new fine-tuned model to the app and check the endpoint and old token.
2. Show chapter names in the chapter selector.

## Links
- https://huggingface.co/IITM-2026T3-DSAI-GROUP2/NCERT-AI-Tutor-Qwen3.5-4B
- https://huggingface.co/spaces/21f1006125/Qwen-3-test
- https://huggingface.co/docs/transformers/en/model_doc/qwen3_5

## Tools and packages
- Codex, Hugging Face Spaces, Transformers, PEFT, Supabase, pytest, and Playwright.

## What the AI did
- Updated the model loader and deployed the pinned adapter to the existing Space. Confirmed Render already points there and tested the grounded API with the existing read token.
- Added chapter titles based on the indexed PDF inventory and the project concept list. Verified 130 live catalogue rows, 88 backend tests, and four browser tests.

## Notes
- The chapter selector changes are local and require the team’s usual GitHub and Render release. Credentials omitted.
