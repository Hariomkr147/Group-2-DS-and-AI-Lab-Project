# Context-aware message router benchmark

Compare TF-IDF with logistic regression, frozen MiniLM embeddings with logistic regression, and DeBERTa base zero-shot NLI. The benchmark runs independently of production chat.

## Run

From the repository root, with uv installed, run:

```powershell
uv run --no-project --isolated --python 3.13 --with-requirements backend/eval/message_router/requirements.txt python backend/eval/message_router/benchmark.py
```

The first run downloads pinned model files. Results are written under `results/`, with separate intent and scope predictions for every development and test case. Model loading times use locally cached files and exclude downloads.

`cases.json` is the frozen dataset. `build_cases.py` records the authored utterance pools and split assignments. Running that builder asserts there are no duplicate context/message pairs or identical messages crossing splits. Examples with identical messages under different contexts stay within the test split.

## Protocol

- 132 training, 45 development and 104 test examples. All are AI-authored synthetic examples. Independent human review and real learner evaluation remain necessary.
- Nine intent labels and three curriculum scope labels. The two decisions are scored separately and jointly.
- TF-IDF and MiniLM fit two class-balanced logistic-regression heads on the same training examples. MiniLM's encoder stays frozen. DeBERTa receives fixed label descriptions and uses no task-specific training examples.
- MiniLM uses the publisher's UINT8 AVX2 ONNX artifact, mean pooling and L2 normalization. DeBERTa uses PyTorch FP32 on CPU.
- Each candidate runs in a fresh process, imports the real FastAPI application without executing startup, then loads its model. Database settings are overridden before import. No learner data, hosted inference or database queries are used.
- Native numerical threads are limited to one. After a warm-up, the benchmark measures one example at a time. Request latency includes encoding, classification and both output decisions.
- A 10 ms sampler measures process resident memory during loading, fitting and prediction, plus a separate prediction-phase peak. The imported backend and model libraries are included. The process does not serve HTTP requests, load AKT or run the Qwen retrieval encoder.
- Raw accuracy and macro-F1 are reported for all test examples. Confidence cutoff selection uses development examples only, targeting 90% joint accuracy with at least ten accepted development cases. Test acceptance coverage and accuracy are reported separately.
- The data is small and shares a limited set of lesson contexts across splits. Numbers are preliminary development measurements and can overestimate generalization.
- Windows laptop memory and timing do not reproduce Render's Linux container, shared CPU allocation or 512 MB limit. Compare memory cautiously and verify the chosen candidate on the deployment environment before integration.

## Results

The original comparison in [REPORT.md](REPORT.md) uses the frozen benchmark data. The packaged runtime artifact trains on the benchmark training split and the additional training examples in `runtime_cases.json`. The exporter uses development examples only to pick separate confidence cutoffs and prints raw results for the added held-out contexts.

On the 16 added synthetic test cases, the raw classifier found 4 of 4 topic switches and 0 of 2 answer attempts. It labeled four supported messages unsupported and marked 12 cases below a confidence cutoff for at least one decision. These figures describe the classifier alone. The API applies independent assessment and curriculum checks.

A local Windows smoke test with the locked Python 3.12 dependencies exercised course-pack chat through the FastAPI API. The first message took 11.3 seconds with model loading, the next took 23 ms, and peak process memory was 175 MiB. It used a temporary SQLite database and template replies. Render measurements remain pending.

[Read the completed benchmark report](REPORT.md) for the comparison, individual intent recall, context pairs and errors that could send help requests into grading. The report also records limitations of the fixed zero-shot label descriptions.

## References

- [MiniLM model and optimized artifacts](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [DeBERTa zero-shot classifier](https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0)
- [Render compute limits](https://render.com/docs/compute-plans)
