"""Validate and transactionally load an immutable release into the NCERT-owned DB."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "07_concepts_questions_and_chunks/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "08_prerequisite_graph/code"))
from pipeline import ROOT, SOURCES, local_path, read_csv, read_jsonl, run_record, sha256
from build_content_pack import ACCEPTED_CHUNKS, PRIVATE_FIELDS
from build_graph import validate_graph
from embed_chunks import validate_vectors
from setup_local_database import CONNECTION, DATA, PORT

PHASE = ROOT / "10_embeddings_and_database"
CONTENT = ROOT / "07_concepts_questions_and_chunks/outputs"
TABLES = ["ncert_content.sources", "ncert_content.concepts", "ncert_content.chunks", "ncert_content.chunk_concepts",
          "ncert_content.questions", "ncert_private.answers", "ncert_content.prerequisite_edges"]


def connect():
    import psycopg
    config = json.loads(CONNECTION.read_text(encoding="utf-8"))
    if config["host"] != "127.0.0.1" or config["port"] != PORT or config["dbname"] != "ncert_pilot":
        raise ValueError("Database must be the dedicated NCERT pilot target")
    db = psycopg.connect(**config, connect_timeout=5)
    with db.cursor() as cur:
        cur.execute("SHOW data_directory")
        if Path(cur.fetchone()[0]).resolve() != DATA.resolve():
            db.close()
            raise ValueError("Connected cluster is outside NCERT-owned directory")
    db.commit()
    return db


def counts(db, version):
    from psycopg import sql
    return {table: db.execute(sql.SQL("SELECT count(*) FROM {} WHERE corpus_version=%s").format(sql.Identifier(*table.split("."))),
                             (version,)).fetchone()[0] for table in TABLES}


def load(db, version, fingerprint, manifest, sources, concepts, chunks, questions, answers, edges, vectors):
    from psycopg.types.json import Jsonb
    with db.transaction():
        existing = db.execute("SELECT fingerprint FROM ncert_content.releases WHERE corpus_version=%s", (version,)).fetchone()
        if existing:
            if existing[0] != fingerprint:
                raise ValueError("Refusing replacement of a frozen corpus version")
            return counts(db, version)
        db.execute("INSERT INTO ncert_content.releases VALUES (%s,%s,%s)", (version, fingerprint, Jsonb(manifest)))
        for s in sources:
            db.execute("INSERT INTO ncert_content.sources VALUES (%s,%s,%s)", (version, s["source_id"], Jsonb(s)))
        for c in concepts:
            db.execute("INSERT INTO ncert_content.concepts VALUES (%s,%s,%s)", (version, c["concept_id"], Jsonb(c)))
        for c, vector in zip(chunks, vectors, strict=True):
            value = json.dumps(vector.tolist(), allow_nan=False)
            db.execute("INSERT INTO ncert_content.chunks VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)",
                       (version, c["chunk_id"], c["source_id"], c["text"], c["page_start"], c["page_end"], Jsonb(c), value))
            for concept in c["concept_ids"]:
                db.execute("INSERT INTO ncert_content.chunk_concepts VALUES (%s,%s,%s)", (version, c["chunk_id"], concept))
        for q in questions:
            if PRIVATE_FIELDS & q.keys():
                raise ValueError("Private key in learner-safe question payload")
            db.execute("INSERT INTO ncert_content.questions VALUES (%s,%s,%s)", (version, q["question_id"], Jsonb(q)))
        for a in answers:
            db.execute("INSERT INTO ncert_private.answers VALUES (%s,%s,%s)", (version, a["question_id"], Jsonb(a)))
        for e in edges:
            db.execute("INSERT INTO ncert_content.prerequisite_edges VALUES (%s,%s,%s,%s)",
                       (version, e["prerequisite_id"], e["dependent_id"], Jsonb(e)))
        return counts(db, version)


def main():
    import numpy as np
    import psycopg
    manifest_path = CONTENT / "content_manifest.json"
    embedding_path = PHASE / "outputs/embedding_manifest.json"
    graph_path = ROOT / "08_prerequisite_graph/outputs/approved_edges.csv"
    schema_path = PHASE / "code/schema.sql"
    with run_record("10_embeddings_and_database", [manifest_path, embedding_path, graph_path, schema_path, SOURCES]) as run:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        embedding = json.loads(embedding_path.read_text(encoding="utf-8"))
        for path, digest in manifest["artifact_hashes"].items():
            if sha256(local_path(path)) != digest:
                raise ValueError("Accepted content artifact changed")
        vectors_path, ids_path = local_path(embedding["vector_path"]), local_path(embedding["chunk_ids_path"])
        if sha256(vectors_path) != embedding["vector_sha256"] or sha256(ids_path) != embedding["chunk_ids_sha256"]:
            raise ValueError("Frozen vector or identity artifacts changed")
        concepts = read_jsonl(CONTENT / "concepts.jsonl")
        chunks = read_jsonl(ACCEPTED_CHUNKS)
        questions, answers = [read_jsonl(CONTENT / p) for p in ["questions.jsonl", "answers_private.jsonl"]]
        version = manifest["corpus_version"]
        edges, sources = read_csv(graph_path), read_csv(SOURCES)
        if embedding["corpus_version"] != version or any(e["corpus_version"] != version for e in edges):
            raise ValueError("Incompatible graph/embedding release")
        validate_graph(edges, {c["concept_id"] for c in concepts})
        ids = [r["chunk_id"] for r in read_jsonl(ids_path)]
        if ids != [c["chunk_id"] for c in chunks] or sha256(ACCEPTED_CHUNKS) != embedding["chunks_sha256"]:
            raise ValueError("Chunk/vector order or text hash differs")
        vectors = np.load(vectors_path, allow_pickle=False)
        validate_vectors(vectors, ids)
        fingerprint = hashlib.sha256((sha256(manifest_path) + embedding["vector_sha256"] + sha256(graph_path) + sha256(SOURCES)).encode()).hexdigest()
        with connect() as db:
            db.execute(schema_path.read_text(encoding="utf-8")); db.commit()
            start = time.perf_counter()
            first = load(db, version, fingerprint, manifest, sources, concepts, chunks, questions, answers, edges, vectors)
            seconds = time.perf_counter() - start
            second = load(db, version, fingerprint, manifest, sources, concepts, chunks, questions, answers, edges, vectors)
            assert first == second
            expected = dict(zip(TABLES, [len(sources), len(concepts), len(chunks), sum(len(c["concept_ids"]) for c in chunks), len(questions), len(answers), len(edges)]))
            if first != expected:
                raise ValueError("Database counts differ from accepted artifacts")
            db.commit()
            probe = version + "-rollback-probe"
            try:
                with db.transaction():
                    from psycopg.types.json import Jsonb
                    db.execute("INSERT INTO ncert_content.releases VALUES (%s,%s,%s)", (probe, "probe", Jsonb({})))
                    db.execute("INSERT INTO ncert_content.chunk_concepts VALUES (%s,%s,%s)", (probe, "missing_chunk", "missing_concept"))
            except psycopg.errors.ForeignKeyViolation:
                pass
            else:
                raise AssertionError("Invalid foreign key was accepted")
            assert db.execute("SELECT count(*) FROM ncert_content.releases WHERE corpus_version=%s", (probe,)).fetchone()[0] == 0
            try:
                load(db, version, "changed-fingerprint", manifest, sources, concepts, chunks, questions, answers, edges, vectors)
            except ValueError:
                pass
            else:
                raise AssertionError("Changed frozen release was accepted")
            assert counts(db, version) == first
            dimensions = db.execute("SELECT DISTINCT vector_dims(embedding) FROM ncert_content.chunks WHERE corpus_version=%s", (version,)).fetchall()
            assert dimensions == [(384,)]
            learner_payloads = db.execute("SELECT payload FROM ncert_content.learner_questions WHERE corpus_version=%s", (version,)).fetchall()
            assert all(not PRIVATE_FIELDS & row[0].keys() for row in learner_payloads)
            vector_version = db.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()[0]
        result = dict(run_id=run["run_id"], corpus_version=version, counts=first, load_seconds=seconds, pgvector_version=vector_version,
                      repeated_load_same_counts=True, failed_load_rolled_back=True, frozen_version_replacement_rejected=True,
                      vector_dimension=384, learner_export_private_fields=0, skill_mapping="deferred_by_user",
                      database="ncert_pilot", schema="ncert_content + ncert_private", search="pgvector exact cosine over this release; no ANN index needed at pilot size")
        out = PHASE / "outputs/database_counts.json"
        out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        run["outputs"].append(out); run["counts"] = result
        print(json.dumps(result))


if __name__ == "__main__":
    main()
