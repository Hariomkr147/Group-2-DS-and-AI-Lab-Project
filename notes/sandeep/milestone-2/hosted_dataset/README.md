# Socratic AI Tutor: processed data (Milestone 2)

Group 2, Data Science and AI Lab, IIT Madras BS. Upload this folder as a Kaggle dataset
(`kaggle datasets create -p .` after setting your username in `dataset-metadata.json`), then put the dataset link in
`docs/milestone-2/Milestone2_Report.md`.

Two prepared versions are included so models can be compared: **version A** (our scripts) and **version B** (Hariom Pandey, Colab).
Do not mix files from the two versions. See the report, Section 7.

```
hosted_dataset/
├── version_a_assistments/          learner-model data, version A
│   ├── train.jsonl  val.jsonl  test.jsonl    {user_id, skills[], correct[]}  one window of <=200 answers per line
│   ├── skill_map.csv                         skill index, original skill id, skill name (149 skills)
│   └── stats.json
├── version_b_assistments_dkt/      learner-model data, version B
│   ├── dkt_data.npz                          arrays X_tr S_tr C_tr M_tr X_te S_te C_te M_te N (82 skills)
│   ├── dkt_processed_steps.csv               every step with split, student, chunk, skill, correct, x
│   ├── skill_map.csv  SHA256.txt  test_dkt_data.py
├── mathdial/                       Socratic-model data, version A
│   ├── train.jsonl  val.jsonl  test.jsonl    one tutor reply per line (chat format) with act, keep, leaks_answer
│   └── stats.json
├── version_b_socratic_chat/
│   └── socratic_tutor_combined.jsonl         37,413 conversations {source, messages[]}  (SocraTeach + MathDial train)
├── ncert_metadata/                 chapter list and counts only (NCERT text is not redistributed)
│   ├── chapters.csv  stats.json
├── course_pack_specs/              hand-written concepts, prerequisites and questions (no NCERT text)
│   ├── specs.py  chapter_titles.csv
└── test_scenarios/                 our own evaluation sets, never used for training
    ├── backtracking.jsonl  misconceptions.jsonl  guardrails.jsonl  stats.json
```

## Splits
| Set | Train | Validation | Test | Split rule |
|---|---|---|---|---|
| ASSISTments A | 3,081 students | 385 | 386 | by student |
| ASSISTments B | 2,726 students | none | 682 | by student, seed 42 |
| MathDial A | 2,045 dialogues | 217 (by problem) | 599 (MathDial's own) | by problem |
| Chat corpus B | 37,413 conversations | none | none | MathDial test held out |

## Sources and licences
- ASSISTments 2009-2010 skill builder (Feng, Heffernan, Koedinger 2009): research use, cite the data page and paper.
- MathDial (Macina et al. 2023): CC BY-SA 4.0 (GitHub) / CC BY 4.0 (Hugging Face).
- SocraTeach Multi (`ulises-c/SocraTeach_Multi`): CC BY-NC 4.0.
- Because of the share-alike and non-commercial terms, this bundle is offered as **CC BY-NC-SA 4.0** for coursework use only.
- NCERT books: public but not ours to redistribute, so only metadata is included.
- Test scenarios and course-pack specs: written by the team.
