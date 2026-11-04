> **Phase report snapshots.** Current release status is generated in [CURRENT_CHECKPOINT.md](../CURRENT_CHECKPOINT.md). Dated entries below are historical evidence, not a second current-status source.

<!-- pilot-hardening-2026-11-04 -->
## Current repair result — 4 November 2026

A fresh 300-group local Eedi test, with 200 calibration groups and no overlap with exposed test groups, improves native-label Recall@5 from 16% to 26% on the same task; top-1 remains 10%. The graph-ID baseline is separate (187/300 bridge coverage, 10.7% covered-label Recall@5). Broad diagnosis remains experimental. Runtime Qwen ID selection was removed. Six explicit wrong-method families can yield unconfirmed, non-persistent suggestions only after exact learner-equation checks; unsupported working abstains. No restricted competition rows were sent remotely in this evaluation.

See [Pilot repairs and decision](../PILOT_HARDENING.md) for evidence, measured limits and remaining gates. Earlier entries below are historical and superseded where they conflict.

---

<!-- eedi-guarded-runtime-2026-11-03 -->
## Guarded Eedi runtime — 3 November 2026

Implemented [diagnose_eedi.py](code/diagnose_eedi.py), a callable/CLI pipeline using the full pinned catalogue and BGE vectors, checked arithmetic candidate rules, optional live Qwen selection and strict candidate-ID/response validation. Input must be established as incorrect by the caller. With no working the pipeline asks for it and does not call the model; with working, remote transfer is disabled unless explicitly enabled per request. All selected IDs remain `candidate_needs_review`, never confirmed or persistent. Model/transport failures, unexpected response identity or format, and over-limit input fail closed. The remote model is the user's Socratic adapter; it is not a trained misconception classifier.

The local-only calibration smoke (`20261103T154125-20ec8145`) processed six Eedi distractors without working: all six returned `need_working`. Eight MAP examples with working returned `needs_review` / `remote_not_enabled`; no competition record was sent remotely in this run. These checks are not model accuracy measurements. MAP labels remain a separate namespace; accuracy and false confident diagnosis rates are not measured. The earlier explicitly requested Eedi model smoke did send eight competition cases to the user's Kaggle endpoint; subsequent competition checks respect the recorded local-only boundary.

At the user's explicit request, one **synthetic** example with the supplied learner name was used only as a transient live smoke and not added to any dataset or learner history. Without working the pipeline requested it. With supplied synthetic working the live endpoint returned Eedi candidate `19849`, consistent with the demonstrated fraction-addition method; the result remained unconfirmed and non-persistent. One constructed case cannot establish general diagnostic accuracy. Phase 09's 11 unit tests pass, including local HTTP transport, identity validation, whitelisting, no-working and remote opt-in guards. [Local-only smoke metrics](outputs/eedi_runtime_smoke_metrics.json); [usage and limits](EEDI_RUNTIME.md).

The current tutor backend has a separate numeric misconception detector and does **not** call this Eedi pipeline. It can return a label from a single wrong number; collecting working, avoiding unsupported diagnosis, and safely integrating the new flow remain necessary before learner-facing use.

---

<!-- qwen-eedi-calibration-smoke-2026-11-03 -->
## Live fine-tuned Qwen candidate-selection smoke — 3 November 2026

A live user-provided Qwen3.5 Socratic endpoint was tested on eight **calibration** Eedi Kaggle multiple-choice incorrect-option cases. These are publisher distractors, not observed individual student responses; no student working was supplied. Cases were deterministically selected to contain four where the exact normalized-text bridged gold was among the existing graph top five and four where it was absent; candidate order was deterministically shuffled. This 50/50 sample is deliberately balanced and not representative of retrieval recall or diagnosis prevalence. Neither publisher gold nor persistent student labels were sent in prompts. The model was instructed to output a candidate ID, NONE or NEED_WORKING; returned IDs are only suggestions and the endpoint does not confirm diagnoses.

Six requests completed; two failed with network exceptions (URLError and ConnectionResetError, with no confirmed inference result). All six completed responses conformed to the specified output format. One selected the dataset's bridged label, three selected a different candidate, and two abstained. Among the four completed cases with gold absent, two returned a candidate and two abstained; among two completed cases with gold present, one selected it and one selected another. A different label is measured against the publisher's label, not independent proof of the student's reasoning. The sample is too small and selected to estimate general accuracy. It does not justify confident diagnosis without working or override the plan's confirmation rule. No Eedi-specific training is claimed for the Socratic model.

The private per-case run, including original model outputs and candidate IDs, is retained under ignored Phase 09 logs. No API key or temporary URL is recorded. User-requested external inference was performed against their authenticated Kaggle endpoint; no real student explanations were sent. Held-out data and the 161 team scenarios were not used for this smoke test.

---

<!-- supplied-qwen-notebook-inspection-2026-11-03 -->
## Uploaded model role clarified — 3 November 2026

The user-supplied Qwen training notebook fine-tunes Socratic next-response generation on MathDial/SocraTeach, with no Eedi/MAP misconception labels. Its reported reply metrics are not diagnosis accuracy. An adapter-specific hosting notebook is in Phase 12; original Eedi retrieval metrics and unmeasured Qwen diagnosis status remain unchanged. The shared API default output length now matches its 96-token protocol; both prepared notebooks embed the current tested module. No GPU checkpoint or public endpoint was run here.

---

<!-- model-human-db-handoff-2026-11-03 -->
## Model, review and database handoff — 3 November 2026

Prepared notebooks/host_finetuned_misconception_model.ipynb for a private, temporary Kaggle inference endpoint. Common HF causal/full-classifier/causal-LoRA loaders are included, with original label namespace, exact-prompt input, bounded context, Bearer authentication, one inference at a time and shutdown. Three endpoint tests pass on a real loopback HTTP server; all notebook cells compile and the embedded endpoint matches the tested source. The user checkpoint/base model, training format, label namespace and training-question exposure remain unconfirmed. No GPU checkpoint inference, public tunnel or new diagnostic accuracy was measured. A shared unseen-evaluation decision framework is in REVIEW_AND_MODEL_HANDOFF.md; proposed quality gates are not achieved results.

---

# Phase 09 execution report

Updated: 3 November 2026 (Asia/Kolkata). Owner: Hariom Kumar; execution: Codex.
Status: **Dataset acquisition, validation, catalogue embeddings and local loads completed; bounded retrieval evaluation completed; Qwen runtime diagnosis pending. KT mapping deferred by the user.**

The revised PLAN section 13.4 replaces the earlier six handwritten labels and 18 synthetic examples. They were moved to `_retired_codex_authored`; they are not active diagnostic data. No invented replacement questions, answers or student working were added.

The pinned **Eedi Misconceptions Graph v1.0** contains **8,117 original misconception IDs/texts, 2,258 constructs and 19,294 weighted links**. Text and identity consistency, construct foreign keys and per-misconception weight totals were checked. All 8,117 texts were embedded using pinned BGE-small-en-v1.5, CLS pooling, L2 normalization, 384 dimensions. Finite values, norms and ID alignment passed. These links are not prerequisite edges or learner probabilities.

Eedi attribution: “Eedi Misconceptions Graph v1.0” by Eedi, CC BY 4.0. Original texts and IDs are unchanged; CSV links were grouped into catalogue records. [Publisher](https://huggingface.co/datasets/Eedi/Eedi-Misconceptions-Graph). Dataset revision: `2ae0839debf73c0ce7dd6578d8ea8b99e7be8631`.

| Official competition file | Original records |
| --- | ---: |
| Eedi train questions | 1,869 |
| Eedi misconception mapping | 2,587 |
| MAP train explanations | 36,696 |
| Released sample test rows | 3 per competition |

The user authorized accepting both competition agreements under the signed-in account. Both acceptances were visibly confirmed, then the official ZIP downloads were used. ZIP file lists, total sizes, CRCs, CSV schemas and database counts passed. Data remains in ignored local storage and restricted `ncert_diag_eval.original_rows`; no CSVs or student explanations were published.

The Eedi data page and rules specify CC BY-NC 4.0 with competition restrictions. MAP's data page displays MIT, while its accepted competition-specific data-use rules specify CC BY-NC 4.0. Both signals are recorded; this project retains the competition data locally for non-commercial academic evaluation under the accepted restrictions, without redistribution.

Original labelled data was transformed into **41,066 diagnostic records**: **4,370 Eedi incorrect-option labels** and **36,696 MAP student explanations**. Eedi distractors are explicitly not represented as observed student responses. All original question groups stay together: **411 calibration groups / 1,473 held-out groups**, with zero overlap. MAP has only **15 unique questions**, so row-random splitting would leak context. The team's 161 scenarios were not read.

Five checked wrong-method rules cover fraction addition, fraction multiplication/division and percentage errors, referencing original Eedi IDs. Their output is always a candidate requiring working/confirmation; no single number establishes a persistent misconception. Checks include unreduced input fractions and the valid divide-by-10 method for 10%.

Evidence:
- [Catalogue manifest and hashes](outputs/eedi_catalogue_manifest.json), run `20261102T183405-52a22a04`.
- [Competition source manifests](outputs/competition_dataset_manifest.json), run `20261102T184035-342fbd3c`.
- [Diagnostic split summary](outputs/diagnostic_dataset_summary.json), run `20261102T185220-deac9616`.
- [Wrong-method rules](code/error_rules.py), [catalogue checks](code/test_eedi_catalogue.py), [ZIP/CSV checks](code/test_competition_datasets.py).

The two catalogue/archive boundary tests and rule self-checks passed. Actual database loads validate counts and original text/ID preservation. A frozen 439-case publisher-data retrieval baseline has now run (`20261102T190234-77f91e22`). Eedi test covered-label Recall@5 is **19.2% (24/125 bridged cases from 200 selected)** and MRR@5 is 0.086. MAP native-label test Recall@5 is **33.3% (9/27)** and MRR@5 is 0.1772; it uses a different label space and is not an Eedi-ID accuracy. Eedi calibration coverage is 128/200, Recall@5 0.140625; MAP calibration has 12 cases, Recall@5 0.08333. No cases exceeded the token limit. [Measured results](outputs/diagnostic_retrieval_metrics.json). Qwen selection, wrong-confident-diagnosis rate and science transfer remain unmeasured; retrieval similarity is not a diagnosis probability. Science misconception curation and concept filters remain deferred until extraction, as the revised plan requires.
