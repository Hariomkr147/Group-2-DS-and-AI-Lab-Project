# Eedi candidate pipeline

The callable pipeline is `code/diagnose_eedi.py`. It searches the full pinned 8,117-entry Eedi graph with the existing BGE vectors, then adds any matching checked arithmetic-rule IDs. It validates original dataset and vector hashes and refuses changed catalogue identities. The model may select only an ID in this returned set, `NONE`, or `NEED_WORKING`; malformed, truncated, unexpected-model or unavailable-service outputs fail closed.

Call `EediDiagnostic().diagnose(question, answer, working, answer_is_incorrect=True)` only after a trusted scoring step establishes that the answer is incorrect. The result includes original Eedi candidate IDs/texts and a status. With no working it returns `need_working` without calling the model. With working it defaults to `needs_review` because remote transfer is disabled. To send a particular authorized question, answer and working to the user's hosted Kaggle model through Cloudflare, explicitly pass `allow_remote=True`. The temporary URL is held in ignored `.remote_model_connection.json`; the key remains in ignored `Ncert work/.env`.

Example of the expected input structure, using placeholders rather than a student example:

```json
{"question": "<source question>", "answer": "<incorrect answer>", "working": "<actual learner working>", "answer_is_incorrect": true, "allow_remote": false}
```

To run once from the `Ncert work` directory, save an authorized input as a local JSON file and use:

```powershell
Get-Content -Raw -LiteralPath 'input.json' | & '.\.venv\Scripts\python.exe' '09_skill_misconception_and_scope_mapping/code/diagnose_eedi.py'
```

`candidate_needs_review` is **not a confirmed or persistent diagnosis**. `none_fits`, `need_working`, `needs_review` and `not_assessed` carry no selected misconception. No response should be used as a learner-facing diagnosis or a knowledge-tracing update until the selection and evidence are independently validated. The existing tutor backend currently uses a separate numeric detector and is **not connected** to this pipeline; it can return labels from a single number. Integration needs session-level working collection and a separate safety review.

The Eedi Kaggle and MAP competition files have a recorded local-only evaluation boundary. Do not set `allow_remote=True` for those records. Public Eedi graph catalogue text is CC BY 4.0; attribute Eedi. The earlier eight-case smoke sent Eedi competition question/option text to the user's hosted Kaggle endpoint; the new runtime smoke keeps all competition records local.

`code/evaluate_runtime_smoke.py` performs a small calibration check without remote model calls: six Eedi distractors without working and eight MAP incorrect answers with working. MAP labels are in a separate namespace and are not automatically mapped to Eedi graph IDs. This test verifies routing and safeguards; it cannot measure model accuracy or false confident diagnoses. The previously measured full-catalogue Eedi retrieval baseline remains 19.2% top-five recall among the 125 label-bridged held-out cases; no independent improvement is claimed.
