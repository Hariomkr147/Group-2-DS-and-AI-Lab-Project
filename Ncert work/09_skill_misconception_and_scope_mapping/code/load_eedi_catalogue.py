"""Load the original pinned Eedi catalogue, validate links, and embed its texts."""
import csv
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "10_embeddings_and_database/code"))
from pipeline import ROOT, read_csv, run_record, sha256, write_jsonl
from embed_chunks import REVISION, encode, load_encoder, validate_vectors, verify_model
from load_database import connect

PHASE = ROOT / "09_skill_misconception_and_scope_mapping"
DATA_REVISION = "2ae0839debf73c0ce7dd6578d8ea8b99e7be8631"
DATA = PHASE / "datasets/eedi" / DATA_REVISION
ATTRIBUTION = "Eedi Misconceptions Graph v1.0 by Eedi, licensed under CC BY 4.0. CSV links grouped into original-ID catalogue records; texts unchanged."


def catalogue(constructs, edges):
    by_construct = {r["ConstructId"]: r for r in constructs}
    if len(by_construct) != len(constructs):
        raise ValueError("Duplicate construct identity")
    misconceptions, weights, links = {}, defaultdict(float), set()
    for row in edges:
        mid, cid, text = row["MisconceptionId"], row["ConstructId"], row["MisconceptionName"]
        weight = float(row["PercentageMisconceptionExistsInThisConstruct"])
        if not mid.isdigit() or cid not in by_construct or not text.strip() or not 0 <= weight <= 100 or (mid, cid) in links:
            raise ValueError("Invalid original-ID link, weight or text")
        links.add((mid, cid)); weights[mid] += weight
        if mid in misconceptions and misconceptions[mid]["text"] != text:
            raise ValueError("Conflicting text for the same original misconception ID")
        entry = misconceptions.setdefault(mid, dict(misconception_id=mid, source="Eedi Misconceptions Graph v1.0", text=text, construct_ids=[],
                                                    licence="CC-BY-4.0", dataset_revision=DATA_REVISION, attribution=ATTRIBUTION,
                                                    provenance="publisher_dataset; original text and IDs"))
        entry["construct_ids"].append(cid)
    if any(abs(w - 100) > .1 for w in weights.values()):
        raise ValueError("Publisher edge weights do not sum to approximately 100 per misconception")
    for entry in misconceptions.values():
        entry["construct_ids"].sort(key=int)
    return sorted(misconceptions.values(), key=lambda r: int(r["misconception_id"]))


def main():
    import numpy as np
    from psycopg.types.json import Jsonb
    files = [DATA / p for p in ["data/construct-map.csv", "data/misconception-map.csv", "LICENSE", "README.md"]]
    with run_record("09_skill_misconception_and_scope_mapping", files) as run:
        constructs, edges = read_csv(files[0]), read_csv(files[1])
        rows = catalogue(constructs, edges)
        if (len(rows), len(constructs), len(edges)) != (8117, 2258, 19294):
            raise ValueError("Pinned dataset counts differ from publisher v1.0")
        release = "eedi-" + DATA_REVISION[:16]
        ids = [r["misconception_id"] for r in rows]
        folder = PHASE / "vectors" / release; folder.mkdir(parents=True, exist_ok=True)
        vector_path, receipt = folder / "vectors.npy", folder / "receipt.json"
        expected = dict(dataset_revision=DATA_REVISION, model_revision=REVISION, source_sha256=sha256(files[1]), document_format="original misconception text; no prefix", pooling="CLS L2")
        start = time.perf_counter()
        if receipt.exists():
            saved = json.loads(receipt.read_text(encoding="utf-8"))
            if saved["request"] != expected or saved["vector_sha256"] != sha256(vector_path):
                raise ValueError("Changed catalogue embedding cache")
            vectors = np.load(vector_path, allow_pickle=False)
            reused = True
        else:
            verify_model()
            tokenizer, model = load_encoder()
            vectors = encode([r["text"] for r in rows], tokenizer, model)
            validate_vectors(vectors, ids)
            np.save(vector_path, vectors, allow_pickle=False)
            receipt.write_text(json.dumps(dict(request=expected, vector_sha256=sha256(vector_path)), indent=2) + "\n", encoding="utf-8")
            reused = False
        validate_vectors(vectors, ids)
        encode_seconds = time.perf_counter() - start
        with connect() as db:
            db.execute("CREATE SCHEMA IF NOT EXISTS ncert_diag")
            db.execute("CREATE TABLE IF NOT EXISTS ncert_diag.constructs (dataset_release text, construct_id text, payload jsonb NOT NULL, PRIMARY KEY(dataset_release,construct_id))")
            db.execute("CREATE TABLE IF NOT EXISTS ncert_diag.misconceptions (dataset_release text, misconception_id text, source text NOT NULL, text text NOT NULL, construct_ids text[] NOT NULL, licence text NOT NULL, payload jsonb NOT NULL, embedding vector(384) NOT NULL, PRIMARY KEY(dataset_release,misconception_id))")
            with db.cursor() as cur:
                cur.executemany("INSERT INTO ncert_diag.constructs VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", [(release, r["ConstructId"], Jsonb(r)) for r in constructs])
                cur.executemany("INSERT INTO ncert_diag.misconceptions VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector) ON CONFLICT DO NOTHING",
                                [(release, r["misconception_id"], r["source"], r["text"], r["construct_ids"], r["licence"], Jsonb(r), json.dumps(v.tolist(), allow_nan=False)) for r, v in zip(rows, vectors, strict=True)])
            count = db.execute("SELECT count(*) FROM ncert_diag.misconceptions WHERE dataset_release=%s", (release,)).fetchone()[0]
            stored = db.execute("SELECT misconception_id,text,construct_ids FROM ncert_diag.misconceptions WHERE dataset_release=%s", (release,)).fetchall()
            by_id = {r["misconception_id"]: r for r in rows}
            if count != len(rows) or any(text != by_id[mid]["text"] or cids != by_id[mid]["construct_ids"] for mid, text, cids in stored):
                raise ValueError("Stored original IDs/text/links differ from pinned dataset")
        out = PHASE / "outputs"
        write_jsonl(out / "misconceptions.jsonl", rows)
        manifest = dict(run_id=run["run_id"], dataset_release_id=release, dataset_revision=DATA_REVISION,
                        source_url="https://huggingface.co/datasets/Eedi/Eedi-Misconceptions-Graph", licence="CC-BY-4.0", attribution=ATTRIBUTION,
                        misconception_count=len(rows), construct_count=len(constructs), edge_count=len(edges),
                        input_sha256={p.relative_to(ROOT).as_posix(): sha256(p) for p in files}, model_revision=REVISION, vector_dimension=384,
                        vector_sha256=sha256(vector_path), vector_path=vector_path.relative_to(ROOT).as_posix(), embeddings_reused=reused,
                        load_and_encode_seconds=encode_seconds, original_text_preserved=True, synthetic_student_examples=0,
                        tables=["ncert_diag.misconceptions", "ncert_diag.constructs"],
                        limits=["Catalogue links are not prerequisite edges or per-student probabilities", "No NCERT-to-construct filter applied", "Kaggle evaluation access is separate; catalogue is not labelled student-response data", "Mixed workload timings, not an isolated throughput benchmark"])
        path = out / "eedi_catalogue_manifest.json"; path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([out / "misconceptions.jsonl", path, vector_path, receipt]); run["counts"] = {k: manifest[k] for k in ["misconception_count", "construct_count", "edge_count", "vector_dimension"]}
        print(json.dumps(run["counts"]))


if __name__ == "__main__":
    main()
