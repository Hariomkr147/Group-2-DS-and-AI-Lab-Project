# processed/chat

One chat corpus from `raw/socratic_chat/mathdial` and `raw/socratic_chat/socrateach`, built by `prep_chat.py`.

| File | What it holds |
|---|---|
| `train.jsonl`, `val.jsonl`, `test.jsonl` | One conversation per line: `source`, `id`, `problem`, `messages` (system, then alternating user and assistant), plus flags such as whether a tutor message leaks the final answer. |
| `stats.json` | Cleaning counts and split sizes. |

Splits are made by problem across both sources, so no problem appears in more than one split. Validation and test mix both sources.
