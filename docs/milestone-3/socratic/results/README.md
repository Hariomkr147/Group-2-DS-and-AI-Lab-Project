# Results: Socratic response models

Zero-shot baselines on the candidate test subset (`../candidate/test.jsonl`, 200 conversations, 100 MathDial and 100 SocraTeach). The prompt is the conversation so far plus one added sentence: "Guide the student with one short question at a time. Never state the final answer." Models are loaded in 4-bit, decoding is greedy, and replies stop at 80 new tokens. Script: `../eval_baseline.py`.

## Files

| File | What it holds |
|---|---|
| `baseline_<name>.json` | `summary` (the metrics below) and `rows` (for each test turn: id, source, history, human reference, model reply, ROUGE-L) |
| `train_<name>.json` | Training and validation loss by step for a fine-tuning run (written by `../finetune_lora.py`) |
| `tuned_<name>.json` | Same format as the baseline file, for a fine-tuned model (`--adapter`) |

One test turn is picked per conversation (seeded, so every model sees the same 200 turns). Turns where the human tutor's reply gives away the final answer are skipped, and so is the very first message of a conversation.

## Metrics

| Metric | Meaning | How to read it |
|---|---|---|
| `rougeL` | Word overlap (longest common subsequence F-measure) between the model reply and the human tutor's reply | Higher means closer to the human wording. It does not measure whether a reply is good: a correct reply worded differently scores low. |
| `asks_question` | Share of replies that end with `?` | A Socratic tutor should mostly ask. Not asking is not always wrong (for example "Well done" after a correct answer). |
| `mean_words` vs `reference_mean_words` | Reply length against the human tutor's | Much longer means the model explains instead of probing. |

## Baseline results

| | Gemma 4 E4B | Phi-4-mini |
|---|---|---|
| ROUGE-L, all | 0.199 | 0.244 |
| ROUGE-L, MathDial | 0.138 | 0.157 |
| ROUGE-L, SocraTeach | 0.261 | 0.331 |
| Asks a question, all | 74% | 72% |
| Asks a question, MathDial | 75% | 60% |
| Asks a question, SocraTeach | 73% | 84% |
| Mean words (human tutor: 20.8) | 32.6 | 27.9 |

Gemma's numbers are from the printed run summary; its per-reply file is not in this folder yet.

## What the numbers say

- Phi-4-mini overlaps more with the human tutors, mostly on SocraTeach. It is also closer in length. Both models are wordier than the human tutor, which averages 20.8 words.
- MathDial scores are low for both. The human MathDial tutors write short replies (14.7 words on average), and the models write about twice that.
- Differences of a few points are within noise at n = 200, for example 72% against 74% on question rate. The ROUGE-L gap between the two models is larger and more reliable.

## Patterns seen in the Phi-4-mini replies

Counted from `baseline_phi4mini.json` with simple text rules (the rules are rough; treat the counts as estimates, not exact rates).

| Pattern | All | MathDial | SocraTeach |
|---|---|---|---|
| Reply does not end in `?` | 56/200 (28%) | 40/100 | 16/100 |
| ... of which cut off at the 80-token limit | 10/200 (5%) | 8/100 | 2/100 |
| ... of which a complete statement, not a question | 46/200 (23%) | 32/100 | 14/100 |
| Reply opens with praise or a confirmation ("Great", "Exactly", "Correct", ...) | 109/200 (55%) | 58/100 | 51/100 |
| Reply more than twice as long as the human tutor's | 70/200 (35%) | 51/100 | 19/100 |
| Test turn with no student message yet (conversation opening) | 51/200 (26%) | 23/100 | 28/100 |

- **Mostly complete statements, not cut-off text.** Truncation explains only a small part of the missing questions.
- **Praise and confirmation are common**, and in several cases the student was wrong. Examples: `MAWPS_train_2113_4` (student's 3 x 1.54 = 3.62 is confirmed; it is 4.62), `GSM8K_train_7061_2` (student's 800 is confirmed; it is 8,000), `MAWPS_train_2363_0` (2 + 6 = 7 is confirmed). The human tutors correct the student in these turns. This is not captured by any metric above.
- **Some replies give the answer or do the step for the student**, for example `GSM8K_train_7300_1` and `mathdial-train-220`.
- **Conversation openings:** in MathDial the human tutor often opens with "could you walk me through your solution?", and the model starts solving instead. ROUGE-L on MathDial openings is 0.089, against 0.177 on the later MathDial turns. SocraTeach openings are not affected (0.332 against 0.330).
- One reply (`mathdial-train-2057`) repeats a sentence until the token limit.

## Limits

- ROUGE-L measures wording, not tutoring quality. A reply that confirms a wrong answer can still score well.
- Answer leaks in model replies are not measured, because the final answers are not stored in the processed data. Only the human references that leak are skipped.
- One turn per conversation, 200 turns, one run (greedy decoding, no repeats), so there is no variance estimate.
- A small share of MathDial tutor messages contain text repeated twice, a leftover from the source data (0.7% of MathDial tutor messages in the candidate train split, 1.3% in the test split). References with this are scored as they are.
- The industry-benchmark comparison is not done here. The MathDial and SocraTeach papers use different metrics and splits, so they would be a rough reference only.
