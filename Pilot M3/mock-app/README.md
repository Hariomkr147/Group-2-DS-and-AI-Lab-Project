# NCERT mock tutor

An isolated FastAPI app using the existing Socratic Tutor layout, frozen NCERT passages, a hosted fine-tuned Qwen model, the supplied trained AKT weights and SQLite learner history. It references the existing `Ncert work` artifacts. Current content counts and verification status are in [CURRENT_CHECKPOINT.md](../Ncert%20work/CURRENT_CHECKPOINT.md).

## Start

Run `./start.ps1` in PowerShell from this folder, then open http://127.0.0.1:8765. It uses `Ncert work/.venv`, validates/prepares the seven source checkpoints, and loads the pinned NCERT embedding encoder. PostgreSQL is not needed to run this app.

Keep the hosted model runtime/tunnel running for explanations, hints and discussion. Its key stays in the ignored `Ncert work/.env`. If its temporary URL expires, enter the new URL in the app's reconnection form. Health and model identity checks must pass before the URL is saved. The app never launches a local generative model.

Connection settings are cached until a successful reconnection or app restart. Restart the app after changing the key in `.env`. Hints use the same `/api/sessions/{sid}/messages` endpoint as other chat actions, with `intent: "hint"`.

## Lesson flow

- Choose a topic. Explain concept teaches from NCERT evidence and the hosted model; Try a question starts a source-backed checkpoint.
- Hints provide three increasing levels of guidance. Send discusses working; Check answer submits a final answer. Explanation, hint, off-topic and answer-request messages do not count as assessment attempts.
- Correct answers advance through the connected seven-question maths pool. Prerequisite backtracking returns to the original question after recovery. After all seven, Try a question starts a labelled review round and preserves history. Science/section topics without a checked checkpoint are teaching-only.
- Eedi suggestions use six checked wrong-method families and direct lookup of the publisher's original label text. Explicit learner equations must support the suggestion. Other working selects no ID. Suggestions remain unconfirmed and non-persistent; general misconception diagnosis is experimental. The app does not load/search Eedi vectors or call Qwen as an ID classifier. Research retrieval remains in the offline pipeline.
- Knowledge tracing uses the supplied `akt_best.pt.zip` checkpoint, saved unchanged as `mock-app/models/akt/akt_best.pt`. It is a PyTorch checkpoint despite its `.zip` filename. AKT has 123 skills, 15,922 training questions, 128-dimensional embeddings, eight attention heads, and one block. The app uses up to 199 past mapped answers plus the next question, matching the 200-step training window. Fraction multiplication maps to index 42, fraction division to 38, and percentages to Percents at 75; other topics use practice estimates. The supplied AKT skill map matches every index and original skill ID in the earlier named export.
- NCERT questions have no matching ASSISTments question IDs, so AKT uses its zero-difficulty padding entry for them; it does not borrow a training question's learned difficulty. This curriculum bridge is not validated transfer. Earlier DKT exports remain in `models/dkt` and `models/dkt-demo-baseline`. Restart the app to load AKT; learner history is preserved.

NCERT retrieval uses a topic filter and local BGE cosine ranking. Raw PDFs, keys and unrelated candidate content are not served as public files. The seven private checkpoints must pass source/key gates. A ratio-conversion checkpoint uses ratio-as-fraction evidence, rather than a share-of-total example.

Failed model actions preserve progress and can be retried with the same request ID. Replies are screened for direct answer leakage, invalid protocol output and truncation. The lexical leakage guard is not proof of semantic safety. Inputs sent for teaching are processed by the configured external model endpoint; competition evaluation records stay local.

## Checks

Using `../Ncert work/.venv/Scripts/python.exe` from this folder:

- `-m unittest discover -p test_mock_app.py`: controller, model-error and API-boundary tests.
- `check_offline.py`: actual artifacts, evidence, source questions, review continuation and guarded suggestions, using ephemeral history and zero response-model calls.
- `check_live.py`: later hosted-model teaching/hint test; run only when the endpoint is available.

[Verification](VERIFICATION.md) · [Release report](../Ncert%20work/PILOT_REPORT.md) · [Archived workflows](../Ncert%20work/_archive/README.md).
