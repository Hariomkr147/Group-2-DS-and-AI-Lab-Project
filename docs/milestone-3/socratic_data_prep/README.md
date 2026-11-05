# Tutoring dialogue data prep (Milestone 3)

`socratic_dialogue_prep.ipynb` reads the raw SocraTeach_Multi and MathDial files in `raw/` and
produces cleaned, annotated, problem-level splits in `processed/` with plots in `figures/`.
It only reads local files and needs pandas, matplotlib and scipy.

**Hosted processed dataset (Kaggle):** https://www.kaggle.com/datasets/hariomkr/socratic
**Candidate dataset(kaggle):** https://www.kaggle.com/datasets/hariomkr/socratic-test-db/data


| Folder | Contents |
| --- | --- |
| `raw/` | Gzipped JSON Lines exports of the pinned HuggingFace revisions. `python download_raw.py` recreates them if they are missing (needs the `datasets` package). |
| `processed/` | `train`, `val`, `test`, `candidate_train` and `candidate_val` as `.jsonl.gz`, plus `split_problem_ids.json` and `stats.json` |
| `figures/` | Raw overview, train distributions, candidate subset against full train, split-overlap matrix |

| Split | Dialogues | Problems |
| --- | ---: | ---: |
| train | 23,876 (22,574 SocraTeach, 1,302 MathDial) | 8,661 |
| val | 2,993 (2,682 SocraTeach, 311 MathDial) | 1,032 |
| test (MathDial official test) | 599 | 394 |
| candidate_train | 2,000 (1,000 SocraTeach, 1,000 MathDial) | |
| candidate_val | 200 (100 per source) | |

Splits are by problem, and no problem appears in two splits. Every problem in the MathDial test
set is removed from train and validation in both sources. Train and validation keep at most 3
dialogues per problem from each source, so SocraTeach repeats never push out MathDial dialogues.

The candidate subset (1,000 + 1,000 train, 100 + 100 validation, stratified by length) is the
shared experiment set for the Gemma and Qwen comparison.

Compared with `notes/hariom pandey/milestone-2/socratic_tutor_combined.jsonl` (left unchanged), the
records keep the problem text, reference answer and solution for SocraTeach. They also carry a
problem ID, MathDial teacher moves and an answer-leak flag on tutor turns.

Licences: SocraTeach_Multi CC BY-NC 4.0, MathDial CC BY 4.0.
