# Tutor response diagnosis (2026-11-19)

## Prompts
1. Find why the tutor asks questions or refers to the textbook when the student asks for an explanation or hint.
2. Check who contributed the tutoring code responsible for those replies.

## Links
- Screenshot supplied in the chat.

## Tools and packages
- Codex (GPT-6), Python, unittest.mock.

## What the AI did
- Traced the three screenshot turns and reproduced the hint routing and question-only response checks with local mocks.
- Checked Git attribution for the original tutor and the NCERT-specific reply and routing code.

## Notes
- Application code was unchanged. Production traces and retrieval scores were not checked.
