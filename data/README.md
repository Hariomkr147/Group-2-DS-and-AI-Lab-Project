# Data

Scripts that download and prepare the three datasets. Raw files and bulky outputs are not committed; run the scripts to rebuild them.

```bash
python -m venv data/.venv
data/.venv/Scripts/pip install -r data/requirements.txt      # Linux/Mac: data/.venv/bin/pip
data/.venv/Scripts/python data/scripts/download.py            # raw files -> data/raw/
data/.venv/Scripts/python data/scripts/prep_assistments.py
data/.venv/Scripts/python data/scripts/prep_mathdial.py
data/.venv/Scripts/python data/scripts/prep_ncert.py
data/.venv/Scripts/python data/scripts/check_data.py          # sanity checks
```

| Dataset | Used for | Output in `data/processed/` |
|---|---|---|
| ASSISTments 2009-2010 (corrected) | Train and test the learner model (DKT) | `assistments/`: `train/val/test.jsonl` (one window of up to 200 answers per line), `skill_map.csv`, `stats.json` |
| MathDial | Fine-tune the Socratic model | `mathdial/`: `train/val/test.jsonl` (one tutor reply per line, chat format), `stats.json` |
| NCERT Maths and Science, classes 6-10 | Course pack (study material for search) | `ncert/`: `chunks.jsonl`, `chapters.csv`, `stats.json` |

Details, choices and limits are in `docs/milestone-2/Milestone2_Report.md`.
