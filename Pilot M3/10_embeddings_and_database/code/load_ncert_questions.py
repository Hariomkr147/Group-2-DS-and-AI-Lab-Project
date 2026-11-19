"""Load NCERT's own questions, worked examples and answer-key solutions into separate tables.

Independent of the frozen pilot corpus_version: the question bank is keyed by source_id and
fully replaced on each load (one transaction). Answers go to the private schema only.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load_database import connect
from pipeline import ROOT, SOURCES, read_csv, run_record, sha256

CONTENT = Path(__file__).resolve().parents[2] / "07_concepts_questions_and_chunks/outputs"
DDL = """
CREATE SCHEMA IF NOT EXISTS ncert_content;
CREATE SCHEMA IF NOT EXISTS ncert_private;
CREATE TABLE IF NOT EXISTS ncert_content.ncert_questions (
    question_id text PRIMARY KEY, source_id text NOT NULL, kind text NOT NULL,
    provenance text NOT NULL CHECK (provenance IN ('ncert_extracted', 'ncert_solution_pages')),
    answer_available boolean NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS ncert_content.ncert_worked_examples (
    example_id text PRIMARY KEY, source_id text NOT NULL, payload jsonb NOT NULL);
CREATE TABLE IF NOT EXISTS ncert_private.ncert_answers (
    question_id text PRIMARY KEY REFERENCES ncert_content.ncert_questions ON DELETE CASCADE,
    provenance text NOT NULL CHECK (provenance = 'ncert_solution_pages'), payload jsonb NOT NULL);
REVOKE ALL ON ncert_private.ncert_answers FROM PUBLIC;
"""
PRIVATE = {"answer", "solution", "gold_answer", "acceptable_forms", "solution_steps"}


def read(name):
    return [json.loads(l) for l in open(CONTENT / name, encoding="utf-8")]


def load_bank():
    questions, examples = read("ncert_questions.jsonl"), read("ncert_worked_examples.jsonl")
    answers = [a for a in read("ncert_answers_private.jsonl") if a["question_id"] and a["answer"]]
    ids = {q["question_id"] for q in questions}
    if len(ids) != len(questions) or not {a["question_id"] for a in answers} <= ids:
        raise ValueError("Duplicate question id or answer without a question")
    if len({a["question_id"] for a in answers}) != len(answers):
        raise ValueError("More than one NCERT answer linked to a question")
    if any(PRIVATE & q.keys() for q in questions):
        raise ValueError("Answer text in learner-visible question payload")
    source_ids = sorted(s["source_id"] for s in read_csv(SOURCES))
    if any(q["source_id"] not in source_ids or not q["source_block_ids"] or q["page_start"] is None for q in questions):
        raise ValueError("Question lacks a current physical source reference")
    with connect() as db:
        db.execute(DDL)
        db.execute("DELETE FROM ncert_content.ncert_worked_examples WHERE source_id=ANY(%s)", (source_ids,))
        db.execute("DELETE FROM ncert_content.ncert_questions WHERE source_id=ANY(%s)", (source_ids,))
        from psycopg.types.json import Jsonb
        for q in questions:
            db.execute("INSERT INTO ncert_content.ncert_questions VALUES (%s,%s,%s,%s,%s,%s)",
                       (q["question_id"], q["source_id"], q["kind"], q["provenance"], q["answer_available"], Jsonb(q)))
        for e in examples:
            db.execute("INSERT INTO ncert_content.ncert_worked_examples VALUES (%s,%s,%s)", (e["example_id"], e["source_id"], Jsonb(e)))
        for a in answers:
            db.execute("INSERT INTO ncert_private.ncert_answers VALUES (%s,%s,%s)", (a["question_id"], a["provenance"], Jsonb(a)))
        got = {t: db.execute(f"SELECT count(*) FROM {t} WHERE source_id=ANY(%s)", (source_ids,)).fetchone()[0]
               for t in ["ncert_content.ncert_questions", "ncert_content.ncert_worked_examples"]}
        got["ncert_private.ncert_answers"] = db.execute("SELECT count(*) FROM ncert_private.ncert_answers a JOIN ncert_content.ncert_questions q USING(question_id) WHERE q.source_id=ANY(%s)", (source_ids,)).fetchone()[0]
        assert got == {"ncert_content.ncert_questions": len(questions), "ncert_content.ncert_worked_examples": len(examples),
                       "ncert_private.ncert_answers": len(answers)}, got
        db.execute("CREATE OR REPLACE VIEW ncert_content.approved_ncert_questions AS SELECT q.* FROM ncert_content.ncert_questions q JOIN ncert_private.ncert_answers a USING(question_id) WHERE q.payload->>'review_status'='approved' AND a.payload->>'review_status'='approved' AND q.payload->>'scoring_eligible'='true' AND a.payload->>'scoring_eligible'='true'")
        db.commit()
    print(json.dumps(got, indent=1))
    return got


def main():
    inputs = [SOURCES, *[CONTENT / p for p in ["ncert_questions.jsonl", "ncert_worked_examples.jsonl", "ncert_answers_private.jsonl", "ncert_bank_manifest.json"]]]
    with run_record("10_embeddings_and_database", inputs) as run:
        manifest = json.loads(inputs[-1].read_text(encoding="utf-8"))
        for path in inputs[1:-1]:
            if manifest["artifact_hashes"][path.relative_to(ROOT).as_posix()] != sha256(path):
                raise ValueError("Source question bank changed after validation")
        counts = load_bank()
        out = ROOT / "10_embeddings_and_database/outputs/ncert_database_counts.json"
        out.write_text(json.dumps(dict(run_id=run["run_id"], counts=counts, bank_manifest_sha256=sha256(inputs[-1]),
                                       replacement_scope="Current manifest source IDs only; transaction verified before commit",
                                       scoring_gate="Only source-reviewed approved question/answer pairs may be assessed"), indent=2) + "\n", encoding="utf-8")
        run["outputs"].append(out); run["counts"] = counts


if __name__ == "__main__":
    main()
