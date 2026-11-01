# Data (Milestone 2): Kaggle dataset layout, splits and licences

Group 2, Data Science and AI Lab, IIT Madras BS. Hosted on Kaggle:
https://www.kaggle.com/datasets/sandeepnalla6125/group-2-ds-and-ai-lab-project-data

This is the layout of the Kaggle dataset. In the project repository the frozen learner-model files are in `docs/milestone-2/data/processed/assistments/frozen/` (made in Colab, so the scripts cannot recreate them exactly), and the rest is rebuilt by the scripts in `docs/milestone-2/data/scripts/` into `docs/milestone-2/data/`: the chat corpus and NCERT metadata in `processed/`, the course-pack specs and test scenarios in `generated/`.

```
Kaggle dataset/
├── assistments_dkt/          learner-model data (frozen set)
│   ├── dkt_data.npz                  arrays X_tr S_tr C_tr M_tr X_te S_te C_te M_te N   (82 skills, sequences of 200)
│   ├── dkt_processed_steps.csv       every step: split, user_id, chunk_id, step, skill_index, correct, x, skill_id_original
│   ├── skill_map.csv                 skill index -> original skill id
│   ├── SHA256.txt                    file hashes
│   └── test_dkt_data.py              prints shapes and statistics, checks the encoding
├── socratic_chat/            Socratic-model data (MathDial + SocraTeach, rebuilt from the original releases)
│   └── train.jsonl  val.jsonl  test.jsonl  stats.json
│         one conversation per line: {source, id, problem, messages[], tutor_acts[], tutor_leaks_answer[]}
├── splits/
│   └── dkt_validation.json           train sequence indices of 10% of the train students (seed 42)
├── ncert_metadata/           chapter list and counts only (NCERT text is not redistributed)
│   └── chapters.csv  stats.json
├── course_pack_specs/        AI-written, team-reviewed concepts, prerequisites and questions (no NCERT text)
│   └── specs.py  chapter_titles.csv
└── test_scenarios/           our own evaluation sets, never used for training
    └── backtracking.jsonl  misconceptions.jsonl  guardrails.jsonl  stats.json
```

## Splits
| Set | Train | Validation | Test | Split rule |
|---|---|---|---|---|
| ASSISTments (DKT) | 2,453 students (2,848 sequences, 183,648 answers) | 273 students (320 sequences, 21,770 answers) | 682 students (781 sequences, 50,642 answers) | by student, seed 42; validation cut from the train set |
| Chat corpus | 36,104 conversations (2,277 MathDial, 33,827 SocraTeach) | 943 (281 MathDial, 662 SocraTeach) | 965 (303 MathDial, 662 SocraTeach) | by problem across both sources, seed 42 |

Row numbers: `dkt_validation.json` lists the validation rows of `X_tr`/`S_tr`/`C_tr`/`M_tr`; the other train rows are the training set.

## Sources and licences
- ASSISTments 2009-2010 skill builder (Feng, Heffernan, Koedinger 2009): research use under the site's terms; cite the data page and paper.
- MathDial (Macina et al. 2023): CC BY-SA 4.0 (GitHub) / CC BY 4.0 (Hugging Face).
- SocraTeach Multi (`ulises-c/SocraTeach_Multi`): CC BY-NC 4.0.
- The bundle is for coursework use only; each part keeps its own source licence (share-alike for MathDial, non-commercial for SocraTeach, the ASSISTments site's terms).
- NCERT books: public but not ours to redistribute, so only metadata is included.
- Test scenarios: written by the team. Course-pack specs: written by an AI assistant and reviewed by the team.
