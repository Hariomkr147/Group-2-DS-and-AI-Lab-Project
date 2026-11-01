# processed/assistments

Two versions of the learner-model (DKT) data.

- `frozen/`: the set the team models on. Made in the first Colab notebook from the 303,260-row file (82 skills); not recreated by any script. `dkt_validation.json` (made by `make_validation_splits.py`) lists its validation rows.
- `rebuilt/`: made from `raw/assistments` by `prep_dkt.py` (525,534 rows, 123 skills). Files:

| File | What it holds |
|---|---|
| `rebuilt/dkt_data.npz` | Arrays `X, S, C, M` for train (`_tr`) and test (`_te`), shape (sequences, 200), plus `N`, the number of skills. `x = skill + N x correct`; `M` marks real (not padded) steps. Students are split whole, never across train and test. |
| `rebuilt/skill_map.csv` | Skill index to the original skill id. |
| `rebuilt/stats.json` | Row counts after each cleaning step, split sizes, correct rate, validation counts. |

The rebuild repeats the recipe; its counts differ from the frozen set because the input file is different.
