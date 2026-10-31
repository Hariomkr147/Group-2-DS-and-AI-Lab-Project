# Socratic AI Tutor: processed data (Milestone 2)

Group 2, Data Science and AI Lab, IIT Madras BS. Hosted on Google Drive:
https://drive.google.com/drive/folders/15vIRFghBsqfHjvHrIztgvVSUv2vP4tws

The same folder is `docs/milestone-2/hosted_dataset/` in the project repository. The scripts that make every file are in `docs/milestone-2/preprocessing/`.

```
hosted_dataset/
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
├── course_pack_specs/        hand-written concepts, prerequisites and questions (no NCERT text)
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
- Test scenarios and course-pack specs: written by the team.
