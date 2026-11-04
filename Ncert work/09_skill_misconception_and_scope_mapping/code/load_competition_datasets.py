"""Validate official user-authorized Kaggle ZIPs and load original CSV rows locally."""
import csv
import io
import json
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "10_embeddings_and_database/code"))
from pipeline import ROOT, run_record, sha256
from load_database import connect

PHASE = ROOT / "09_skill_misconception_and_scope_mapping"
COMPETITIONS = {
    "eedi-mining-misconceptions-in-mathematics": {"train.csv", "test.csv", "sample_submission.csv", "misconception_mapping.csv"},
    "map-charting-student-math-misunderstandings": {"train.csv", "test.csv", "sample_submission.csv"},
}


def validate_archive(path, expected):
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) != len(expected) or {m.filename for m in members} != expected or sum(m.file_size for m in members) > 100_000_000:
            raise ValueError("Unexpected competition archive files/size")
        if any(PurePosixPath(m.filename).name != m.filename or m.flag_bits & 1 for m in members) or archive.testzip() is not None:
            raise ValueError("Unsafe, encrypted or corrupt dataset ZIP")
        result = {}
        for member in members:
            payload = archive.read(member)
            reader = csv.DictReader(io.StringIO(payload.decode("utf-8-sig")))
            rows = list(reader)
            if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)) or not rows or any(None in r for r in rows):
                raise ValueError("Invalid CSV header/row alignment")
            result[member.filename] = dict(bytes=payload, fields=reader.fieldnames, rows=rows)
        return result


def main():
    from psycopg.types.json import Jsonb
    original = {name: Path.home() / "Downloads" / (name + ".zip") for name in COMPETITIONS}
    inputs = []
    for name, path in original.items():
        digest = sha256(path)
        target = PHASE / "datasets/kaggle" / name / digest[:16] / "original.zip"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256(target) != digest:
            raise ValueError("Changed retained official archive")
        if not target.exists():
            shutil.copy2(path, target)
        inputs.append(target)
    with run_record("09_skill_misconception_and_scope_mapping", inputs) as run:
        reports = []
        with connect() as db:
            db.execute("CREATE SCHEMA IF NOT EXISTS ncert_diag_eval")
            db.execute("REVOKE ALL ON SCHEMA ncert_diag_eval FROM PUBLIC")
            db.execute("CREATE TABLE IF NOT EXISTS ncert_diag_eval.original_rows (dataset_release text, filename text, row_number integer, payload jsonb NOT NULL, PRIMARY KEY(dataset_release,filename,row_number))")
            db.execute("REVOKE ALL ON ncert_diag_eval.original_rows FROM PUBLIC")
            for name, path in zip(COMPETITIONS, inputs, strict=True):
                files = validate_archive(path, COMPETITIONS[name])
                required = {"QuestionId", "QuestionText", "CorrectAnswer", "AnswerAText", "MisconceptionAId"} if name.startswith("eedi-") else {"QuestionId", "QuestionText", "StudentExplanation", "Category", "Misconception"}
                if not required <= set(files["train.csv"]["fields"]):
                    raise ValueError("Official training schema differs from documented dataset")
                release = name + "-" + sha256(path)[:16]
                stats = {}
                for filename, file in files.items():
                    target = path.parent / filename
                    if target.exists() and target.read_bytes() != file["bytes"]:
                        raise ValueError("Refusing to overwrite changed original CSV")
                    if not target.exists():
                        target.write_bytes(file["bytes"])
                    with db.cursor() as cur:
                        cur.executemany("INSERT INTO ncert_diag_eval.original_rows VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                                        [(release, filename, n, Jsonb(row)) for n, row in enumerate(file["rows"], 1)])
                    count = db.execute("SELECT count(*) FROM ncert_diag_eval.original_rows WHERE dataset_release=%s AND filename=%s", (release, filename)).fetchone()[0]
                    if count != len(file["rows"]):
                        raise ValueError("Competition DB counts differ from original CSV")
                    stats[filename] = dict(rows=count, columns=file["fields"], sha256=sha256(target), path=target.relative_to(ROOT).as_posix())
                reports.append(dict(competition=name, dataset_release=release, source_url=f"https://www.kaggle.com/competitions/{name}/data",
                                    archive_sha256=sha256(path), files=stats, access="Authorized rules acceptance in signed-in browser; official Download as zip",
                                    terms="Non-commercial academic evaluation; restrict access to accepted participants; no redistribution",
                                    licence_display="CC BY-NC 4.0" if name.startswith("eedi-") else "Data tab displays MIT; accepted competition-specific data rules specify CC BY-NC 4.0; retain locally under competition restrictions"))
        out = PHASE / "outputs/competition_dataset_manifest.json"
        manifest = dict(run_id=run["run_id"], datasets=reports, original_rows_preserved=True, invented_examples=0,
                        publication="Summary metadata only; competition CSVs/archives/private rows stay ignored and local", table="ncert_diag_eval.original_rows")
        out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        run["outputs"].append(out); run["counts"] = {r["competition"]: {f: v["rows"] for f, v in r["files"].items()} for r in reports}
        print(json.dumps(run["counts"]))


if __name__ == "__main__":
    main()
