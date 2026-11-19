# akt wiring (2026-11-18)

## Prompts
1. Pasted a list: prerequisites, misconception, AKT/DKT wiring, skill mapping wiring. "I need to work on these."
2. Chose AKT/DKT wiring as the first item.

## Links
- mock-app/README.md and mock-app/kt.py (pilot AKT), docs/milestone-3/KT_model (checkpoint, skill map)

## Tools and packages
- Claude Code (Sonnet 5.5), torch 2.11 from the backend venv, pytest

## What the AI did
- Rezipped the unpacked checkpoint to `backend/models/akt/akt_best.pt`, copied `skill_map.csv`, added `concept_skill_map.json` (indices 38, 42, 75 taken from the mock README and checked against the skill map).
- New `app/services/akt_net.py` (copied architecture), `app/services/akt.py` (checksum-checked loader, `predict`), `readiness` in `learner_model.py` uses AKT when `KT_MODEL=akt`, otherwise the old smoothed accuracy.
- New `tests/test_akt.py`. Backend suite: 81 passed. Updated README and `.env.example`.

## Notes
- Off by default. Only `percentages` and two NCERT fraction ids are mapped; the other three items (prerequisites, misconception, skill mapping) are not started.
- Weights were not run on real learner data; the WEAK threshold (0.6) was tuned for smoothed accuracy and may need review.
- Torch is not in `requirements.txt`, so Render falls back unless the `rag` extra is installed.
- Nothing committed.
