# akt checkpoint swap (2026-11-19)

## Prompts
1. Read Mrityunjay's notes on the new AKT files, then make his checkpoint the default.

## Links
- notes/Mrityunjay Chakraborty (notebook, best_weights.pt, Ncert Pack README)

## Tools and packages
- Claude Code (Sonnet 5.5), torch, pytest

## What the AI did
- Read his notebook: it merges multi-skill rows into one step per attempt; the older notebook did not, so its 0.843 AUC is probably inflated (not re-run).
- Checked his weights load strictly into `akt_net.py`; replaced `backend/models/akt` weights, skill map (header `mapped_index`) and added `model_info.json`. Loader now reads the bare state dict and updates the checksums. Backend suite: 81 passed.

## Notes
- Test AUC is 0.779 (old: 0.843). His mapping suggestions are unreviewed and not used. Still opt-in via `KT_MODEL=akt`.
