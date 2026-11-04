"""Export publisher-labelled distractors/explanations without inventing student data."""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, local_path, read_csv, run_record, sha256, write_jsonl

PHASE = ROOT / "09_skill_misconception_and_scope_mapping"


def split_for(group):
    return "calibration" if int(hashlib.sha256(group.encode()).hexdigest()[:8], 16) % 5 == 0 else "held_out_by_question"


def main():
    manifest_path = PHASE / "outputs/competition_dataset_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = [local_path(f["path"]) for d in manifest["datasets"] for f in d["files"].values()]
    with run_record("09_skill_misconception_and_scope_mapping", [manifest_path, *paths]) as run:
        examples = []
        for dataset in manifest["datasets"]:
            for file in dataset["files"].values():
                if sha256(local_path(file["path"])) != file["sha256"]:
                    raise ValueError("Original competition file changed")
            train = read_csv(local_path(dataset["files"]["train.csv"]["path"]))
            eedi = dataset["competition"].startswith("eedi-")
            mapping = {r["MisconceptionId"]: r["MisconceptionName"] for r in read_csv(local_path(dataset["files"]["misconception_mapping.csv"]["path"]))} if eedi else {}
            for row in train:
                group = dataset["competition"] + ":" + row["QuestionId"]
                common = dict(problem_group_id=group, source_question_id=row["QuestionId"], question=row["QuestionText"],
                              concept_id=None, split=split_for(group), source_dataset=dataset["competition"], dataset_release=dataset["dataset_release"],
                              review_status="publisher_label; not an independent Codex re-annotation", needs_confirmation=True,
                              persistent_misconception=False, source_file_sha256=dataset["files"]["train.csv"]["sha256"])
                if eedi:
                    for option in "ABCD":
                        raw_id = row["Misconception" + option + "Id"]
                        if option == row["CorrectAnswer"] or not raw_id:
                            continue
                        if not re.fullmatch(r"\d+(?:\.0+)?", raw_id):
                            raise ValueError("Original misconception ID is not an exact integer")
                        mid = raw_id.split(".", 1)[0]
                        if mid not in mapping:
                            raise ValueError("Gold distractor label has no original mapping")
                        examples.append(dict(**common, example_id="eedi:" + row["QuestionId"] + ":" + option,
                                             student_answer=row["Answer" + option + "Text"], student_working=None,
                                             correctness="publisher_incorrect_option", diagnostic_label="kaggle-eedi:" + mid,
                                             gold_original_misconception_id=mid, gold_misconception_text=mapping[mid],
                                             provenance="Publisher-labelled MCQ distractor; not an observed student response"))
                else:
                    examples.append(dict(**common, example_id="map:" + row["row_id"], student_answer=row["MC_Answer"],
                                         student_working=row["StudentExplanation"], correctness="selected_answer_correct" if row["Category"].startswith("True_") else "selected_answer_incorrect",
                                         diagnostic_label=row["Category"] + ":" + row["Misconception"], category=row["Category"],
                                         gold_misconception_text=None if row["Misconception"] == "NA" else row["Misconception"],
                                         provenance="Publisher-labelled original student explanation; no synthetic augmentation"))
        if len(examples) != len({e["example_id"] for e in examples}):
            raise ValueError("Duplicate original example identity")
        groups = {split: {e["problem_group_id"] for e in examples if e["split"] == split} for split in {e["split"] for e in examples}}
        if groups["calibration"] & groups["held_out_by_question"]:
            raise ValueError("Question family crossed the evaluation boundary")
        out = PHASE / "outputs"
        write_jsonl(out / "diagnostic_examples.jsonl", examples)
        result = dict(run_id=run["run_id"], examples=len(examples), source_counts=dict(Counter(e["source_dataset"] for e in examples)),
                      split_counts=dict(Counter(e["split"] for e in examples)), group_counts={k: len(v) for k, v in groups.items()},
                      group_overlap=0, synthetic_examples=0, team_161_scenarios_read=False, kt_mapping="deferred_by_user",
                      provenance="Original publisher data; Eedi distractors and MAP student explanations remain distinct", publication="Restricted local evaluation only",
                      warnings=["MAP has only 15 question groups despite 36,696 responses; row-random splits would leak problem context", "Kaggle misconception IDs and the 2026 Eedi graph IDs are distinct namespaces"])
        path = out / "diagnostic_dataset_summary.json"; path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([out / "diagnostic_examples.jsonl", path]); run["counts"] = result
        print(json.dumps(result))


if __name__ == "__main__":
    main()
