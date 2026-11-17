"""Fit the packaged TF-IDF router and select confidence cutoffs using the development split."""
import json
from hashlib import sha256
from pathlib import Path
import sys

import joblib
import sklearn

from benchmark import LinearRouter, read_cases, router_model, serialize

ARTIFACT = Path(router_model.__file__).with_name("message_router.joblib")
RUNTIME_CASES = Path(__file__).with_name("runtime_cases.json")


def cutoff(rows, decision):
    # shortcut: held-out examples share a small set of lesson contexts, recalibrate on reviewed conversations.
    for percent in range(50, 101):
        threshold = percent / 100
        accepted = [row for row, predictions in rows if predictions[decision][1] >= threshold]
        if len(accepted) >= 8:
            correct = sum(row[decision] == predictions[decision][0] for row, predictions in rows
                          if predictions[decision][1] >= threshold)
            if correct / len(accepted) >= 0.90:
                return threshold
    return 1.01


def main():
    data, digest = read_cases()
    runtime_raw = RUNTIME_CASES.read_bytes()
    runtime = json.loads(runtime_raw)
    cases = data["cases"] + runtime["cases"]
    contexts = {**data["contexts"], **runtime["contexts"]}
    train_dev = {row["message"].casefold() for row in cases if row["split"] != "test"}
    assert all(row["message"].casefold() not in train_dev for row in cases if row["split"] == "test")
    model = LinearRouter("tfidf")
    model.fit([row for row in cases if row["split"] == "train"], contexts)
    dev = [(row, router_model.predict(model.encoder, model.heads, serialize(row, contexts)))
           for row in cases if row["split"] == "dev"]
    thresholds = {name: cutoff(dev, name) for name in model.heads}
    bundle = {"version": router_model.ARTIFACT_VERSION, "dataset_sha256": digest,
              "runtime_cases_sha256": sha256(runtime_raw).hexdigest(),
              "sklearn_version": sklearn.__version__, "encoder": model.encoder, "heads": model.heads,
              "thresholds": thresholds}
    target = ARTIFACT.with_suffix(".tmp")
    joblib.dump(bundle, target, compress=3)
    target.replace(ARTIFACT)
    test = [(row, router_model.predict(model.encoder, model.heads, serialize(row, contexts)))
            for row in runtime["cases"] if row["split"] == "test"]
    test_metrics = {}
    for label in ("answer_attempt", "topic_switch"):
        items = [prediction for row, prediction in test if row["intent"] == label]
        test_metrics[label + "_recall"] = [sum(prediction["intent"][0] == label for prediction in items), len(items)]
    test_metrics["raw_non_answers_predicted_as_answers"] = sum(
        row["intent"] != "answer_attempt" and prediction["intent"][0] == "answer_attempt" for row, prediction in test)
    test_metrics["raw_supported_predicted_as_unsupported"] = sum(
        row["scope"] == "supported" and prediction["scope"][0] == "unsupported" for row, prediction in test)
    test_metrics["abstentions"] = sum(
        any(prediction[name][1] < thresholds[name] for name in thresholds) for row, prediction in test)
    print(json.dumps({"dataset_sha256": digest, "thresholds": thresholds,
                      "bytes": ARTIFACT.stat().st_size, "unseen_context_tests": len(test), **test_metrics}), file=sys.stdout)


if __name__ == "__main__":
    main()
