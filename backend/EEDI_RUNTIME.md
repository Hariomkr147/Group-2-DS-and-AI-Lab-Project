# Eedi misconception detection developer handoff

The NCERT maths tutor uses Eedi labels to suggest where a learner may be stuck. After the tutor grades an answer as incorrect, it asks for a calculation step. The mock app can show an unconfirmed suggestion when the learner's equations reproduce one of six supported error patterns. Broader diagnosis is still a research task. [Current project checkpoint](../CURRENT_CHECKPOINT.md)

## What we built

| Source | How we used it |
| --- | --- |
| Eedi Misconceptions Graph v1.0 | Public catalogue of 8,117 original misconception IDs and descriptions, 2,258 learning constructs and 19,294 weighted links. We validated the links and embedded the catalogue with pinned BGE-small-en-v1.5, 384 dimensions. Attribute Eedi under CC BY 4.0. [Publisher dataset](https://huggingface.co/datasets/Eedi/Eedi-Misconceptions-Graph) · [Pinned manifest](outputs/eedi_catalogue_manifest.json) |
| Eedi Mining Misconceptions in Mathematics | 4,370 labelled incorrect multiple-choice options and a native vocabulary of 2,587 labels. These options are publisher-written distractors. [Dataset summary](outputs/diagnostic_dataset_summary.json) · [Publisher overview](https://www.eedi.com/data-and-competitions) |
| MAP | 36,696 student explanations across 15 distinct questions. This is the available starting point for research on actual learner working. Split by original question to keep related responses together. [Dataset summary](outputs/diagnostic_dataset_summary.json) |

Preserve the three label namespaces. The graph benchmark bridges Kaggle labels only through exact normalized label text. Use construct links as catalogue metadata and treat NCERT prerequisites and learner mastery as separate signals. Keep competition rows and student explanations in the authorized local evaluation environment. Follow the recorded handling rules when acquiring Kaggle data. [Competition manifest](outputs/competition_dataset_manifest.json)

## Current runtime

- [Mock server](../../mock-app/server.py) calls `EediDiagnostic.diagnose(question, answer, working, answer_is_incorrect=True)` after grading a wrong answer. The learner can submit working with the answer or on a following message while that question's wrong attempt is pending. The UI displays a matching candidate as a possible sticking point. [Mock UI](../../mock-app/static/app.js)
- [Diagnostic service](code/diagnose_eedi.py) returns `not_assessed` for unverified wrongness, `need_working` for missing working, and `insufficient_evidence` for unsupported, invalid or ambiguous working. A unique, catalogue-backed match returns `working_supported_candidate` with its original ID, method and evidence. Candidates have `confirmed: false` and `persistent: false`. Startup checks the pinned source hashes and the generated catalogue's contents and order.
- [Rule verifier](code/error_rules.py) checks exact rational arithmetic. The supported methods are adding fraction numerators and denominators separately (`19849`), flipping the second fraction during multiplication (`22666`), multiplying without taking the reciprocal during division (`23021`), multiplying by the raw percentage (`22482`), dividing by the raw percentage (`26916`), and attaching a percent sign to the ratio's decimal value (`14036`).
- The mock's diagnostic path uses local rules and catalogue lookups. Qwen generates Socratic replies. The earlier vector search and Qwen label selection are historical experiments. The main FastAPI backend has its own answer-only detector, so changes to the mock do not reach that tutor. [Historical runs](report.md) · [Main backend tutor](../../backend/app/services/tutor.py)

## What the benchmark showed

On 300 previously unused Eedi question groups, the native-label BGE baseline reached 16.0% Recall@5 and 6.3% top-1. Adding correct-answer and construct context plus BM25, selected on 200 calibration groups, raised those figures to 26.0% and 10.0%. The public graph comparison could map 187 of the 300 gold labels. It reached 10.7% Recall@5 on that covered subset. These figures measure ranking against publisher labels. Accuracy on real NCERT learner working, false suggestion rates and science transfer remain unmeasured. [Protocol](evaluation/diagnostic_improvement_protocol.json) · [Results](outputs/diagnostic_improvement_metrics.json)

## Run the local checks

From the repository root in PowerShell with the NCERT Python environment set up:

```powershell
$eediPython = (Resolve-Path 'Ncert work/.venv/Scripts/python.exe').Path
& $eediPython -m unittest discover -s 'Ncert work/09_skill_misconception_and_scope_mapping/code' -p 'test*.py'
'{"question":"What is 20% of 50?","answer":"1000","working":"50 * 20 = 1000","answer_is_incorrect":true}' |
  & $eediPython 'Ncert work/09_skill_misconception_and_scope_mapping/code/diagnose_eedi.py'
Push-Location 'mock-app'
& $eediPython -m unittest discover -p test_mock_app.py
Pop-Location
```

The synthetic CLI example should return `working_supported_candidate` for `22482`, with both confirmation and persistence false. A fresh checkout needs the ignored files listed in the public catalogue manifest and `outputs/misconceptions.jsonl` for the CLI. Restore the pinned sources under `datasets/eedi/<revision>/` and use the existing catalogue loader to regenerate the export. The loader also uses the local BGE model or validated vector cache and writes to the dedicated NCERT PostgreSQL database. The mock suite expects its local `data/private_questions.json` fixture, generated by `prepare_data.py` against the approved pilot release. [Pinned source files](https://huggingface.co/datasets/Eedi/Eedi-Misconceptions-Graph/tree/2ae0839debf73c0ce7dd6578d8ea8b99e7be8631) · [Catalogue loader](code/load_eedi_catalogue.py) · [Mock setup](../../mock-app/README.md)

## Where to pick up

1. **Fix fraction notation coverage.** The CLI accepts `1/2 + 1/3` with answer `2/5` and working `1 + 1 = 2` followed by `2 + 3 = 5`. The same example written with LaTeX `\frac` returns `insufficient_evidence`. Candidate matching normalizes LaTeX fractions, but the corroboration step extracts operands from the original prompt. Reuse the same normalization in both checks and add a regression test that preserves abstention for invalid or ambiguous working. [Rule verifier](code/error_rules.py) · [Verifier tests](code/test_working_verifier.py)
2. **Build a learner-working evaluation.** Reproduce the frozen Eedi ranking baseline with the authorized local files, then evaluate on grouped MAP or reviewed NCERT working. Include slips, valid alternative methods, unsupported topics and missing working. Report candidate precision, false suggestion rate and coverage alongside Recall@5. Keep the 161 team scenarios test-only and agree acceptance thresholds before opening a fresh test split. [Data preparation](code/prepare_diagnostic_examples.py) · [Ranking evaluator](code/evaluate_diagnostic_improvements.py)
3. **Integrate the evidence requirement in the main backend.** Once validated, pass the graded attempt and its working into the diagnostic flow. Test correct answers, missing working, and working submitted after a question switch. Keep candidate suggestions out of mastery updates and learner-profile labels. Science and the KT mapping need their own validated inputs. [Existing numeric detector](../../backend/app/services/misconception.py) · [Mock controller tests](../../mock-app/test_mock_app.py)
