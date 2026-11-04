"""Measure dataset-backed retrieval with explicit label namespaces and group splits."""
import hashlib
import json
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "10_embeddings_and_database/code"))
from pipeline import ROOT, local_path, read_jsonl, run_record, sha256, write_jsonl
from embed_chunks import QUERY_PREFIX, encode, load_encoder, validate_vectors, verify_model
from error_rules import candidate_errors

PHASE = ROOT / "09_skill_misconception_and_scope_mapping"


def normalized_text(text):
    return re.sub(r"\W+", " ", unicodedata.normalize("NFKC", text).casefold()).strip()


def select_cases(examples):
    selected, counters, seen = [], Counter(), set()
    for row in sorted(examples, key=lambda r: hashlib.sha256(r["example_id"].encode()).hexdigest()):
        eedi = row["source_dataset"].startswith("eedi-")
        if not eedi and row["gold_misconception_text"] is None:
            continue
        key = (row["source_dataset"], row["split"])
        family = row["problem_group_id"] if eedi else (row["problem_group_id"], row["gold_misconception_text"])
        if family in seen or counters[key] >= (200 if eedi else 100):
            continue
        seen.add(family); counters[key] += 1; selected.append(row)
    return selected


def main():
    import numpy as np
    examples_path = PHASE / "outputs/diagnostic_examples.jsonl"
    catalogue_path = PHASE / "outputs/misconceptions.jsonl"
    manifest_path = PHASE / "outputs/eedi_catalogue_manifest.json"
    with run_record("09_skill_misconception_and_scope_mapping", [examples_path, catalogue_path, manifest_path]) as run:
        examples, catalogue = read_jsonl(examples_path), read_jsonl(catalogue_path)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        vectors_path = local_path(manifest["vector_path"])
        if sha256(vectors_path) != manifest["vector_sha256"]:
            raise ValueError("Catalogue vector artifact changed")
        matrix = np.load(vectors_path, allow_pickle=False)
        ids = [r["misconception_id"] for r in catalogue]
        validate_vectors(matrix, ids)
        bridge = defaultdict(set)
        for row in catalogue:
            bridge[normalized_text(row["text"])].add(row["misconception_id"])
        cases = select_cases(examples)
        groups = {s: {r["problem_group_id"] for r in cases if r["split"] == s} for s in ["calibration", "held_out_by_question"]}
        if groups["calibration"] & groups["held_out_by_question"]:
            raise ValueError("Diagnostic question group crossed the frozen split")
        protocol = dict(examples_sha256=sha256(examples_path), catalogue_sha256=sha256(catalogue_path),
                        selected_example_ids=[c["example_id"] for c in cases],
                        sampling="Stable SHA256 order; one Eedi distractor per question, <=200 per split; one MAP response per question/label, <=100 per split",
                        query_format=QUERY_PREFIX + "Question: {original question}\nStudent answer: {original answer}\nStudent working: {original working if supplied}",
                        eedi_candidate_space="All 8,117 Eedi graph texts; gold IDs bridged only by exact normalized label text",
                        map_candidate_space="35 original MAP misconception labels; separate native-label baseline, not Eedi-ID accuracy",
                        top_k=5, tuning="None; no synthetic example or test-family tuning")
        eval_dir = PHASE / "evaluation"; eval_dir.mkdir(parents=True, exist_ok=True)
        protocol_path = eval_dir / "diagnostic_protocol.json"
        if protocol_path.exists() and json.loads(protocol_path.read_text(encoding="utf-8")) != protocol:
            raise ValueError("Diagnostic protocol changed; retain prior results before a new evaluation")
        protocol_path.write_text(json.dumps(protocol, indent=2) + "\n", encoding="utf-8")
        verify_model(); tokenizer, model = load_encoder()
        map_labels = sorted({r["gold_misconception_text"] for r in examples if r["source_dataset"].startswith("map-") and r["gold_misconception_text"]})
        map_vectors = encode(map_labels, tokenizer, model)
        queries, eligible, oversize = [], [], []
        for case in cases:
            text = QUERY_PREFIX + "Question: " + case["question"] + "\nStudent answer: " + case["student_answer"]
            if case["student_working"]:
                text += "\nStudent working: " + case["student_working"]
            if len(tokenizer.encode(text, add_special_tokens=True, truncation=False)) > 512:
                oversize.append(case["example_id"])
            else:
                queries.append(text); eligible.append(case)
        print("Encoding", len(queries), "original diagnostic cases", flush=True)
        start = time.perf_counter(); query_vectors = encode(queries, tokenizer, model)
        encode_seconds = time.perf_counter() - start
        validate_vectors(query_vectors, [r["example_id"] for r in eligible])
        results = []
        for case, vector in zip(eligible, query_vectors, strict=True):
            eedi = case["source_dataset"].startswith("eedi-")
            target = bridge.get(normalized_text(case["gold_misconception_text"]), set()) if eedi else {case["gold_misconception_text"]}
            candidate_ids, candidate_vectors = (ids, matrix) if eedi else (map_labels, map_vectors)
            scores = candidate_vectors @ vector
            ranked = [candidate_ids[i] for i in np.argsort(-scores, kind="stable")[:5]]
            rank = next((i + 1 for i, mid in enumerate(ranked) if mid in target), None)
            rules = candidate_errors(case["question"], case["student_answer"]) if eedi else []
            if any(not r["needs_confirmation"] or r["persistent"] for r in rules):
                raise ValueError("A numeric rule confirmed a misconception without working")
            results.append(dict(example_id=case["example_id"], source_dataset=case["source_dataset"], problem_group_id=case["problem_group_id"],
                                split=case["split"], candidate_namespace="Eedi graph original IDs" if eedi else "MAP original label names",
                                gold_bridge_available=bool(target), top5=ranked, gold_rank_at_5=rank,
                                rule_candidate_ids=[r["misconception_id"] for r in rules], working_available=bool(case["student_working"]),
                                diagnosis_status="retrieval_candidates_only; Qwen adjudication not measured"))
        metrics = []
        for dataset in sorted({r["source_dataset"] for r in results}):
            for split in ["calibration", "held_out_by_question"]:
                subset = [r for r in results if r["source_dataset"] == dataset and r["split"] == split]
                mapped = [r for r in subset if r["gold_bridge_available"]]
                metrics.append(dict(dataset=dataset, split=split, cases=len(subset), gold_namespace_coverage=len(mapped),
                                    recall_at_5_on_covered=sum(r["gold_rank_at_5"] is not None for r in mapped) / len(mapped) if mapped else None,
                                    mrr_at_5_on_covered=sum(1 / r["gold_rank_at_5"] if r["gold_rank_at_5"] else 0 for r in mapped) / len(mapped) if mapped else None,
                                    rule_candidate_cases=sum(bool(r["rule_candidate_ids"]) for r in subset)))
        out = PHASE / "outputs"
        write_jsonl(out / "diagnostic_retrieval_runs.jsonl", results)
        report = dict(run_id=run["run_id"], protocol_sha256=sha256(protocol_path), metrics=metrics, selected_cases=len(cases),
                      encoded_cases=len(results), oversize_cases_excluded=len(oversize), encode_seconds=encode_seconds,
                      wrong_confident_diagnosis_rate=None, qwen_adjudication_status="Not measured yet", rule_outputs_confirmed=0,
                      limits=["Eedi and MAP use different candidate spaces; their scores are not interchangeable", "Unbridged Eedi gold labels remain outside covered-label recall; coverage is reported", "Oversize full questions are excluded rather than truncated", "This is a bounded source-data baseline, not the private Kaggle hidden test", "Retrieval similarity is not a diagnosis probability"])
        path = out / "diagnostic_retrieval_metrics.json"; path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([protocol_path, out / "diagnostic_retrieval_runs.jsonl", path]); run["counts"] = report
        print(json.dumps(report))


if __name__ == "__main__":
    main()
