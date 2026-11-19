# Context-aware router benchmark

Measured on a Windows laptop with an Intel i7-1260P, using one native inference thread. Each candidate ran in a separate process with the FastAPI backend imported. The app was not started and no database or hosted model calls were made.

The dataset contains 132 training, 45 development and 104 held-out test cases. All examples and gold labels were authored by the assistant. They have no independent human review. The splits share six fixed context templates, so these are preliminary development results. The test set contains 79 supported, 16 uncertain and 9 unsupported examples; always predicting supported would achieve 76.0% scope accuracy.

| Candidate | Intent accuracy | Intent macro-F1 | Scope accuracy | Joint accuracy | Median / p95 latency | Inference peak RSS | Whole-run peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF + logistic regression | 78.8% | 0.784 | 93.3% | 74.0% | 3.4 / 4.8 ms | 167.5 MiB | 176.5 MiB |
| MiniLM UINT8 + logistic regression | 70.2% | 0.689 | 89.4% | 65.4% | 34.5 / 132.2 ms | 267.1 MiB | 267.1 MiB |
| DeBERTa base zero-shot FP32 | 48.1% | 0.394 | 47.1% | 25.0% | 4751.1 / 10089.8 ms | 1337.0 MiB | 1558.5 MiB |

Inference latency includes both intent and scope decisions. Joint accuracy requires both labels to match. Memory includes the imported backend and candidate libraries. It excludes HTTP serving, database activity, AKT and the Qwen retrieval encoder. The whole-run peak also includes model loading and fitting. A deployed model would normally be trained beforehand.

TF-IDF and MiniLM trained two logistic-regression heads on the same 132 examples. MiniLM's encoder was frozen. DeBERTa used fixed natural-language labels with no task-specific fitting. The comparison measures these complete routing approaches, rather than equal training procedures.

## Error and confidence checks

| Candidate | Supported topic switches with both labels correct | Supported messages classified unsupported | Accepted test cases after development cutoff | Joint accuracy among accepted cases |
|---|---:|---:|---:|---:|
| TF-IDF + logistic regression | 8/9 | 0 | 24/104 | 91.7% |
| MiniLM UINT8 + logistic regression | 5/9 | 7 | 0/104 | No qualifying development cutoff |
| DeBERTa base zero-shot FP32 | 2/9 | 1 | 0/104 | No qualifying development cutoff |

The cutoff targets at least 90% joint accuracy on a minimum of ten development examples. A missing qualifying cutoff means this procedure could not establish that target. Confidence scores have different meanings across candidates.

## Intent recall by label

| Gold intent | TF-IDF | MiniLM | DeBERTa |
|---|---:|---:|---:|
| answer_attempt | 72.7% | 81.8% | 81.8% |
| doubt | 42.9% | 42.9% | 100.0% |
| hint_request | 50.0% | 30.0% | 0.0% |
| explanation_request | 92.3% | 46.2% | 84.6% |
| topic_switch | 85.7% | 71.4% | 35.7% |
| answer_request | 90.0% | 80.0% | 10.0% |
| bypass_attempt | 80.0% | 90.0% | 50.0% |
| other | 100.0% | 100.0% | 41.7% |
| clarification_reply | 100.0% | 100.0% | 0.0% |

## Non-answer messages predicted as answer attempts

These are raw classifier errors. Feeding them directly into grading could penalize a student for requesting help or changing topics. The benchmark does not apply confidence abstention or backend validation to this count.

| Candidate | Non-answer messages classified as answer attempts |
|---|---:|
| TF-IDF + logistic regression | 6 |
| MiniLM UINT8 + logistic regression | 4 |
| DeBERTa base zero-shot FP32 | 18 |

**TF-IDF + logistic regression example errors**

- router-043: I'm having trouble with this idea. (gold intent: doubt)
- router-044: How can two pieces still have the same denominator? (gold intent: doubt)
- router-046: This is the bit I'm stuck at. (gold intent: doubt)

**MiniLM UINT8 + logistic regression example errors**

- router-047: What if the pieces aren't equal? (gold intent: doubt)
- router-048: I didn't follow your last sentence. (gold intent: doubt)
- router-068: Nudge me a bit, please. (gold intent: hint_request)

**DeBERTa base zero-shot FP32 example errors**

- router-066: Please point me toward the next move. (gold intent: hint_request)
- router-067: Could you help me get unstuck with a hint? (gold intent: hint_request)
- router-069: Just tell me which part to check. (gold intent: hint_request)

## Identical messages under different contexts

| Context and message | Gold intent / scope | TF-IDF | MiniLM | DeBERTa |
|---|---|---|---|---|
| fractions · 10 | answer_attempt / supported | answer_attempt / supported | answer_attempt / supported | answer_attempt / uncertain |
| fractions · I don't understand why that works. | doubt / supported | doubt / supported | doubt / supported | doubt / supported |
| fractions · Can you explain that? | explanation_request / supported | explanation_request / supported | explanation_request / supported | explanation_request / supported |
| none · 10 | other / uncertain | other / uncertain | other / uncertain | doubt / uncertain |
| none · Can you explain that? | explanation_request / uncertain | explanation_request / uncertain | other / uncertain | doubt / uncertain |
| none · I don't understand why that works. | doubt / uncertain | doubt / uncertain | other / uncertain | doubt / uncertain |
| science · Can you explain that? | explanation_request / supported | explanation_request / supported | topic_switch / unsupported | explanation_request / uncertain |
| fractions · Can we learn photosynthesis now? | topic_switch / supported | topic_switch / supported | topic_switch / unsupported | answer_attempt / uncertain |
| maths_only · Can we learn photosynthesis now? | topic_switch / unsupported | topic_switch / unsupported | topic_switch / unsupported | doubt / uncertain |

## Limits and reproducibility

- These results use one authored English dataset and one run per candidate. They do not establish quality across all NCERT chapters, Hindi/Hinglish or real student conversations.
- The DeBERTa result applies to the fixed label descriptions and context format tested. No prompt search, supervised adaptation or model quantization was evaluated for that candidate.
- Render Free provides 512 MB RAM and 0.1 CPU. The laptop run does not reproduce that Linux container or its CPU quota. Memory headroom and response time require deployment verification.
- No candidate was integrated into chat or deployed.
- See the adjacent README for the exact rerun command. The JSON summaries contain package versions, model revisions, dataset hash, per-label reports and confusion matrices. Prediction JSONL files contain every scored case.
- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [DeBERTa model card](https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0)
- [Render compute limits](https://render.com/docs/compute-plans)
