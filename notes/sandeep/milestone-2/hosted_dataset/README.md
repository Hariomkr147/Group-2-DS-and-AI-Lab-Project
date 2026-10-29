# Socratic AI Tutor: processed data (Milestone 2)

Group 2, Data Science and AI Lab, IIT Madras BS. Hosted on Google Drive:
https://drive.google.com/drive/folders/15vIRFghBsqfHjvHrIztgvVSUv2vP4tws

The learner-model data and the chat corpus were prepared by Hariom Pandey (Colab). The NCERT metadata, course-pack specs, test
scenarios and the validation splits were prepared by Sandeep Nalla.

```
hosted_dataset/
├── assistments_dkt/          learner-model data (Hariom Pandey)
│   ├── dkt_data.npz                  arrays X_tr S_tr C_tr M_tr X_te S_te C_te M_te N   (82 skills, sequences of 200)
│   ├── dkt_processed_steps.csv       every step: split, user_id, chunk_id, step, skill_index, correct, x, skill_id_original
│   ├── skill_map.csv                 skill index -> original skill id
│   ├── SHA256.txt                    file hashes
│   └── test_dkt_data.py              prints shapes and statistics, checks the encoding
├── socratic_chat/            Socratic-model data (Hariom Pandey)
│   └── socratic_tutor_combined.jsonl 37,413 conversations {source, messages[]}  (SocraTeach + MathDial train)
├── splits/                   validation splits derived from the two sets above (their files are not changed)
│   ├── dkt_validation.json           train sequence indices of 10% of the train students (seed 42)
│   └── chat_validation.json          line numbers of the MathDial conversations of 10% of the MathDial problems (seed 42)
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
| ASSISTments (DKT) | 2,453 students (2,848 sequences, 183,648 answers) | 273 students (320 sequences, 21,770 answers) | 682 students (781 sequences, 50,642 answers) | by student, seed 42; validation cut from his train set |
| Chat corpus | 37,198 conversations | 215 MathDial conversations (104 problems) | MathDial's own 599-dialogue test set, not in the file (download from Hugging Face) | validation by problem; SocraTeach stays in train |

Row numbers: `dkt_validation.json` lists the validation rows of `X_tr`/`S_tr`/`C_tr`/`M_tr`; the other train rows are the training set.

## Sources and licences
- ASSISTments 2009-2010 skill builder (Feng, Heffernan, Koedinger 2009): research use under the site's terms; cite the data page and paper.
- MathDial (Macina et al. 2023): CC BY-SA 4.0 (GitHub) / CC BY 4.0 (Hugging Face).
- SocraTeach Multi (`ulises-c/SocraTeach_Multi`): CC BY-NC 4.0.
- Because of the share-alike and non-commercial terms, the bundle is for coursework use only (CC BY-NC-SA 4.0).
- NCERT books: public but not ours to redistribute, so only metadata is included.
- Test scenarios and course-pack specs: written by the team.
