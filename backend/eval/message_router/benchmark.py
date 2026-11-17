"""Compare three routers in fresh processes, including an imported FastAPI backend.

Run with benchmark dependencies only; this script does not start the app or connect to its databases.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import threading
import time

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))
from app.services import router_model

MODELS = {
    "minilm": ("sentence-transformers/all-MiniLM-L6-v2", "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"),
    "deberta": ("MoritzLaurer/deberta-v3-base-zeroshot-v2.0", "8e7e5af5983a0ddb1a5b45a38b129ab69e2258e8"),
}
INTENT_DESCRIPTIONS = {
    "answer_attempt": "The student attempts an answer or supplies working for the pending tutor question.",
    "doubt": "The student expresses confusion or asks why about the current lesson or a curriculum concept.",
    "hint_request": "The student asks for a clue or next step while wanting to solve the question themselves.",
    "explanation_request": "The student requests an explanation, rephrasing or example of an idea.",
    "topic_switch": "The student wants to leave the current lesson and study or discuss a different topic.",
    "answer_request": "The student wants the tutor to provide the final answer or complete solution.",
    "bypass_attempt": "The student instructs the tutor to override its rules or disclose private answers.",
    "other": "The student greets, thanks, acknowledges, or makes an unrelated request without changing an active lesson.",
    "clarification_reply": "The student answers the tutor's recent clarification about a class, subject or topic meaning.",
}
SCOPE_DESCRIPTIONS = {
    "supported": "The request is within the enabled NCERT subjects or clearly continues the active supported lesson.",
    "unsupported": "The request is outside the enabled subjects or concerns unrelated non-curriculum services.",
    "uncertain": "The context does not establish which curriculum topic, question or meaning the student refers to.",
}


def read_cases():
    raw = (HERE / "cases.json").read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def serialize(row, contexts):
    context = contexts[row["context"]]
    return router_model.format_context(
        row["message"], course=context["course"], subjects=context["supported"],
        concept=context["current_concept"], question=context["pending_question"],
        answer_type=context["expected_answer_type"], recent=context["recent_conversation"],
        grade=context.get("grade"),
    )


class LinearRouter:
    def __init__(self, kind):
        self.kind = kind
        self.heads = router_model.classifiers()
        self.artifact_bytes = 0
        self.model_revision = None
        if kind == "tfidf":
            self.encoder = router_model.tfidf_features()
            return
        # Avoid loading PyTorch alongside ONNX Runtime in this deployment candidate.
        os.environ["USE_TORCH"] = "0"
        import onnxruntime as ort
        from huggingface_hub import hf_hub_download
        from transformers import AutoTokenizer
        model, revision = MODELS["minilm"]
        self.model_revision = revision
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=revision)
        path = hf_hub_download(model, "onnx/model_quint8_avx2.onnx", revision=revision)
        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        self.encoder = ort.InferenceSession(path, sess_options=options, providers=["CPUExecutionProvider"])
        self.artifact_bytes = Path(path).stat().st_size

    def features(self, texts, *, fit=False):
        if self.kind == "tfidf":
            return self.encoder.fit_transform(texts) if fit else self.encoder.transform(texts)
        import numpy as np
        vectors = []
        for start in range(0, len(texts), 8):
            tokens = self.tokenizer(texts[start:start + 8], padding=True, truncation=True,
                                    max_length=256, return_tensors="np")
            inputs = {item.name: tokens[item.name].astype(np.int64) for item in self.encoder.get_inputs()}
            hidden = self.encoder.run(None, inputs)[0]
            mask = tokens["attention_mask"][..., None]
            pooled = (hidden * mask).sum(axis=1) / mask.sum(axis=1).clip(min=1)
            vectors.extend(pooled / np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-9))
        return np.asarray(vectors)

    def fit(self, rows, contexts):
        features = self.features([serialize(row, contexts) for row in rows], fit=True)
        for name, head in self.heads.items():
            head.fit(features, [row[name] for row in rows])
        import pickle
        payload = {"heads": self.heads}
        if self.kind == "tfidf":
            payload["encoder"] = self.encoder
        self.artifact_bytes += len(pickle.dumps(payload))

    def predict(self, premise):
        features = self.features([premise])
        result = {}
        for name, head in self.heads.items():
            probabilities = head.predict_proba(features)[0]
            best = int(probabilities.argmax())
            result[name] = str(head.classes_[best])
            result[name + "_score"] = float(probabilities[best])
        return result


class ZeroShotRouter:
    def __init__(self):
        import torch
        from huggingface_hub import HfApi, hf_hub_download
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        torch.set_num_threads(1)
        torch.set_num_interop_threads(1)
        model, revision = MODELS["deberta"]
        self.model_revision = revision or HfApi().model_info(model).sha
        self.tokenizer = AutoTokenizer.from_pretrained(model, revision=self.model_revision)
        self.encoder = AutoModelForSequenceClassification.from_pretrained(
            model, revision=self.model_revision, use_safetensors=True).eval()
        self.entailment_index = next(int(key) for key, label in self.encoder.config.id2label.items()
                                     if "entailment" in label.lower() and "not" not in label.lower())
        path = hf_hub_download(model, "model.safetensors", revision=self.model_revision)
        self.artifact_bytes = Path(path).stat().st_size

    def fit(self, rows, contexts):
        pass  # pretrained NLI model receives label descriptions, without fitting our examples

    def predict(self, premise):
        import torch
        result = {}
        for name, descriptions in (("intent", INTENT_DESCRIPTIONS), ("scope", SCOPE_DESCRIPTIONS)):
            hypotheses = list(descriptions.values())
            tokens = self.tokenizer([premise] * len(hypotheses), hypotheses, padding=True,
                                    truncation="only_first", max_length=384, return_tensors="pt")
            with torch.inference_mode():
                logits = self.encoder(**tokens).logits[:, self.entailment_index]
                probabilities = logits.softmax(dim=0)
            best = int(probabilities.argmax())
            result[name] = list(descriptions)[best]
            result[name + "_score"] = float(probabilities[best])
        return result


def accuracy(rows, field):
    return sum(row[field] == row["predicted_" + field] for row in rows) / len(rows) if rows else None


def write_report():
    output = HERE / "results"
    results = [json.loads((output / f"{kind}.json").read_text()) for kind in ("tfidf", "minilm", "deberta")]
    assert len({result["dataset_sha256"] for result in results}) == 1
    names = {"tfidf": "TF-IDF + logistic regression", "minilm": "MiniLM UINT8 + logistic regression",
             "deberta": "DeBERTa base zero-shot FP32"}
    lines = [
        "# Context-aware router benchmark",
        "",
        "Measured on a Windows laptop with an Intel i7-1260P, using one native inference thread. "
        "Each candidate ran in a separate process with the FastAPI backend imported. "
        "The app was not started and no database or hosted model calls were made.",
        "",
        "The dataset contains 132 training, 45 development and 104 held-out test cases. "
        "All examples and gold labels were authored by the assistant. They have no independent human review. "
        "The splits share six fixed context templates, so these are preliminary development results. "
        "The test set contains 79 supported, 16 uncertain and 9 unsupported examples; always predicting "
        "supported would achieve 76.0% scope accuracy.",
        "",
        "| Candidate | Intent accuracy | Intent macro-F1 | Scope accuracy | Joint accuracy | Median / p95 latency | Inference peak RSS | Whole-run peak RSS |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| {names[result['candidate']]} | {100 * result['intent_accuracy']:.1f}% | "
            f"{result['intent_macro_f1']:.3f} | {100 * result['scope_accuracy']:.1f}% | "
            f"{100 * result['joint_accuracy']:.1f}% | {result['latency_ms_p50']:.1f} / "
            f"{result['latency_ms_p95']:.1f} ms | "
            f"{result['sampled_inference_peak_backend_and_router_rss_mib']:.1f} MiB | "
            f"{result['sampled_peak_backend_and_router_rss_mib']:.1f} MiB |"
        )
    lines.extend([
        "",
        "Inference latency includes both intent and scope decisions. Joint accuracy requires both labels "
        "to match. Memory includes the imported backend and candidate libraries. It excludes HTTP serving, "
        "database activity, AKT and the Qwen retrieval encoder. The whole-run peak also includes model loading "
        "and fitting. A deployed model would normally be trained beforehand.",
        "",
        "TF-IDF and MiniLM trained two logistic-regression heads on the same 132 examples. MiniLM's encoder "
        "was frozen. DeBERTa used fixed natural-language labels with no task-specific fitting. "
        "The comparison measures these complete routing approaches, rather than equal training procedures.",
        "",
        "## Error and confidence checks",
        "",
        "| Candidate | Supported topic switches with both labels correct | Supported messages classified unsupported | Accepted test cases after development cutoff | Joint accuracy among accepted cases |",
        "|---|---:|---:|---:|---:|",
    ])
    predictions = {}
    for result in results:
        kind = result["candidate"]
        predictions[kind] = [json.loads(line) for line in (output / f"{kind}_predictions.jsonl").read_text(
            encoding="utf-8").splitlines()]
        hits, total = result["supported_switches_correct_intent_and_scope"]
        accepted_accuracy = result["test_accepted_joint_accuracy"]
        accepted_text = f"{100 * accepted_accuracy:.1f}%" if accepted_accuracy is not None else "No qualifying development cutoff"
        lines.append(
            f"| {names[kind]} | {hits}/{total} | {result['false_unsupported_redirects']} | "
            f"{result['test_accepted_count']}/{result['test_total_count']} | {accepted_text} |"
        )
    lines.extend(["", "The cutoff targets at least 90% joint accuracy on a minimum of ten development examples. "
                  "A missing qualifying cutoff means this procedure could not establish that target. "
                  "Confidence scores have different meanings across candidates.",
                  "", "## Intent recall by label", "",
                  "| Gold intent | TF-IDF | MiniLM | DeBERTa |",
                  "|---|---:|---:|---:|"])
    for label in INTENT_DESCRIPTIONS:
        values = [f"{100 * result['intent_report'][label]['recall']:.1f}%" for result in results]
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines.extend(["", "## Non-answer messages predicted as answer attempts", "",
                  "These are raw classifier errors. Feeding them directly into grading could penalize a "
                  "student for requesting help or changing topics. The benchmark does not apply confidence "
                  "abstention or backend validation to this count.", "",
                  "| Candidate | Non-answer messages classified as answer attempts |",
                  "|---|---:|"])
    dangerous = {}
    for kind, rows in predictions.items():
        dangerous[kind] = [row for row in rows if row["split"] == "test" and
                           row["intent"] != "answer_attempt" and row["predicted_intent"] == "answer_attempt"]
        lines.append(f"| {names[kind]} | {len(dangerous[kind])} |")
    for kind, rows in dangerous.items():
        if rows:
            lines.extend(["", f"**{names[kind]} example errors**", ""])
            for row in rows[:3]:
                lines.append(f"- {row['id']}: {row['message']} (gold intent: {row['intent']})")
    lines.extend([
                  "", "## Identical messages under different contexts", ""])
    test = [row for row in predictions["tfidf"] if row["split"] == "test"]
    counts = Counter(row["message"] for row in test)
    repeated = [row for row in test if counts[row["message"]] > 1]
    lines.extend(["| Context and message | Gold intent / scope | TF-IDF | MiniLM | DeBERTa |",
                  "|---|---|---|---|---|"])
    lookup = {kind: {row["id"]: row for row in rows} for kind, rows in predictions.items()}
    for row in repeated:
        columns = []
        for kind in ("tfidf", "minilm", "deberta"):
            prediction = lookup[kind][row["id"]]
            columns.append(prediction["predicted_intent"] + " / " + prediction["predicted_scope"])
        lines.append(f"| {row['context']} · {row['message']} | {row['intent']} / {row['scope']} | " +
                     " | ".join(columns) + " |")
    lines.extend(["", "## Limits and reproducibility", "",
                  "- These results use one authored English dataset and one run per candidate. "
                  "They do not establish quality across all NCERT chapters, Hindi/Hinglish or real student conversations.",
                  "- The DeBERTa result applies to the fixed label descriptions and context format tested. "
                  "No prompt search, supervised adaptation or model quantization was evaluated for that candidate.",
                  "- Render Free provides 512 MB RAM and 0.1 CPU. The laptop run does not reproduce that "
                  "Linux container or its CPU quota. Memory headroom and response time require deployment verification.",
                  "- No candidate was integrated into chat or deployed.",
                  "- See the adjacent README for the exact rerun command. The JSON summaries contain package versions, "
                  "model revisions, dataset hash, per-label reports and confusion matrices. Prediction JSONL files contain every scored case.",
                  "- [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)",
                  "- [DeBERTa model card](https://huggingface.co/MoritzLaurer/deberta-v3-base-zeroshot-v2.0)",
                  "- [Render compute limits](https://render.com/docs/compute-plans)",
                  ""])
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def worker(kind):
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    import psutil
    process = psutil.Process()
    # Import the real backend without startup, network calls or the user's database settings.
    os.environ.update(DATABASE_URL="sqlite://", NCERT_DATABASE_URL="", APP_ENV="development",
                      ADMIN_PASSWORD="benchmark-only-placeholder", SECRET_KEY="benchmark-only-placeholder")
    baseline_before = process.memory_info().rss
    import app.main  # noqa: F401
    baseline_app = process.memory_info().rss
    peaks = {"rss": baseline_app, "inference_rss": 0, "inference": False}
    stopped = threading.Event()

    def sample_memory():
        while not stopped.wait(0.01):
            current = process.memory_info().rss
            peaks["rss"] = max(peaks["rss"], current)
            if peaks["inference"]:
                peaks["inference_rss"] = max(peaks["inference_rss"], current)

    monitor = threading.Thread(target=sample_memory, daemon=True)
    monitor.start()
    data, digest = read_cases()
    train = [row for row in data["cases"] if row["split"] == "train"]
    contexts = data["contexts"]
    started = time.perf_counter()
    router = ZeroShotRouter() if kind == "deberta" else LinearRouter(kind)
    load_seconds = time.perf_counter() - started
    started = time.perf_counter()
    router.fit(train, contexts)
    fit_seconds = time.perf_counter() - started
    # Warm model execution independently of the scored test.
    router.predict(serialize(train[0], contexts))
    peaks["inference"] = True
    peaks["inference_rss"] = process.memory_info().rss
    rows = []
    for case in data["cases"]:
        if case["split"] == "train":
            continue
        started = time.perf_counter()
        predicted = router.predict(serialize(case, contexts))
        elapsed = (time.perf_counter() - started) * 1000
        rows.append({**case, **{"predicted_" + key: value for key, value in predicted.items()},
                     "latency_ms": elapsed})
        if len(rows) % 20 == 0:
            print(kind, len(rows), "cases scored", flush=True)
    peaks["rss"] = max(peaks["rss"], process.memory_info().rss)
    resident = process.memory_info().rss
    peaks["inference_rss"] = max(peaks["inference_rss"], resident)
    stopped.set()
    monitor.join()
    from sklearn.metrics import classification_report, confusion_matrix
    test = [row for row in rows if row["split"] == "test"]
    dev = [row for row in rows if row["split"] == "dev"]
    # Select a confidence cutoff using development examples only.
    thresholds = [index / 100 for index in range(0, 101)]
    qualified = []
    for threshold in thresholds:
        kept = [row for row in dev if min(row["predicted_intent_score"], row["predicted_scope_score"]) >= threshold]
        if len(kept) >= 10 and sum(row["intent"] == row["predicted_intent"] and
                                  row["scope"] == row["predicted_scope"] for row in kept) / len(kept) >= 0.9:
            qualified.append(threshold)
    threshold = min(qualified) if qualified else None
    kept_test = [] if threshold is None else [
        row for row in test if min(row["predicted_intent_score"], row["predicted_scope_score"]) >= threshold]
    intent_report = classification_report([row["intent"] for row in test], [row["predicted_intent"] for row in test],
                                          labels=list(INTENT_DESCRIPTIONS), zero_division=0, output_dict=True)
    scope_report = classification_report([row["scope"] for row in test], [row["predicted_scope"] for row in test],
                                         labels=list(SCOPE_DESCRIPTIONS), zero_division=0, output_dict=True)
    latencies = sorted(row["latency_ms"] for row in test)
    supported_switches = [row for row in test if row["intent"] == "topic_switch" and row["scope"] == "supported"]
    memory = process.memory_info()
    summary = {
        "candidate": kind, "dataset_sha256": digest, "model_revision": router.model_revision,
        "runtime": "ONNX Runtime UINT8 AVX2" if kind == "minilm" else "PyTorch FP32 CPU" if kind == "deberta" else "scikit-learn",
        "examples": dict(Counter(row["split"] for row in data["cases"])),
        "load_seconds_cached_files": load_seconds, "fit_seconds": fit_seconds,
        "artifact_bytes_excluding_tokenizer": router.artifact_bytes,
        "baseline_python_rss_mib": baseline_before / 2**20, "baseline_backend_rss_mib": baseline_app / 2**20,
        "resident_backend_and_router_rss_mib": resident / 2**20,
        "sampled_peak_backend_and_router_rss_mib": peaks["rss"] / 2**20,
        "sampled_inference_peak_backend_and_router_rss_mib": peaks["inference_rss"] / 2**20,
        "os_peak_working_set_mib": getattr(memory, "peak_wset", peaks["rss"]) / 2**20,
        "intent_accuracy": accuracy(test, "intent"), "scope_accuracy": accuracy(test, "scope"),
        "joint_accuracy": sum(row["intent"] == row["predicted_intent"] and row["scope"] == row["predicted_scope"]
                              for row in test) / len(test),
        "intent_macro_f1": intent_report["macro avg"]["f1-score"],
        "scope_macro_f1": scope_report["macro avg"]["f1-score"],
        "supported_switches_correct_intent_and_scope": [
            sum(row["predicted_intent"] == "topic_switch" and row["predicted_scope"] == "supported"
                for row in supported_switches), len(supported_switches)],
        "false_unsupported_redirects": sum(row["scope"] == "supported" and row["predicted_scope"] == "unsupported"
                                          for row in test),
        "latency_ms_p50": statistics.median(latencies),
        "latency_ms_p95": latencies[min(len(latencies) - 1, int(len(latencies) * .95))],
        "dev_selected_joint_confidence_threshold": threshold,
        "test_accepted_count": len(kept_test), "test_total_count": len(test),
        "test_accepted_joint_accuracy": (sum(row["intent"] == row["predicted_intent"] and
                                            row["scope"] == row["predicted_scope"] for row in kept_test) /
                                       len(kept_test)) if kept_test else None,
        "intent_report": intent_report, "scope_report": scope_report,
        "intent_confusion_matrix_labels": list(INTENT_DESCRIPTIONS),
        "intent_confusion_matrix": confusion_matrix(
            [row["intent"] for row in test], [row["predicted_intent"] for row in test],
            labels=list(INTENT_DESCRIPTIONS)).tolist(),
        "host": {"platform": platform.platform(), "python": platform.python_version(),
                 "logical_cpus": os.cpu_count(), "native_inference_threads": 1},
        "package_versions": {},
    }
    for package in ("numpy", "scikit-learn", "onnxruntime", "torch", "transformers", "psutil"):
        try:
            summary["package_versions"][package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            pass
    output = HERE / "results"
    output.mkdir(exist_ok=True)
    (output / f"{kind}.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / f"{kind}_predictions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in (
        "candidate", "intent_accuracy", "scope_accuracy", "intent_macro_f1", "latency_ms_p50",
        "resident_backend_and_router_rss_mib", "sampled_peak_backend_and_router_rss_mib")}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", choices=["tfidf", "minilm", "deberta"])
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
        return
    data, _ = read_cases()
    assert {row["intent"] for row in data["cases"]} == set(INTENT_DESCRIPTIONS)
    assert {row["scope"] for row in data["cases"]} == set(SCOPE_DESCRIPTIONS)
    for kind in ("tfidf", "minilm", "deberta"):
        subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", kind], check=True)
    write_report()


if __name__ == "__main__":
    main()
