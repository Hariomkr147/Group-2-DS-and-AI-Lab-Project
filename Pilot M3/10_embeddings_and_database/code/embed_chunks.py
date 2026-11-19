"""Encode exact accepted evidence with pinned BGE CLS pooling on CPU."""
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "07_concepts_questions_and_chunks/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "03_parser_benchmark/code"))
from pipeline import ROOT, local_path, read_jsonl, run_record, sha256, write_jsonl
from build_content_pack import ACCEPTED_CHUNKS, MODEL_DIR, MODEL_ID, REVISION
from measure_parser_memory import peak_working_set

PHASE = ROOT / "10_embeddings_and_database"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def validate_vectors(vectors, ids):
    import numpy as np
    if vectors.shape != (len(ids), 384) or len(ids) != len(set(ids)) or not np.isfinite(vectors).all():
        raise ValueError("Vector dimensions, identity alignment or finite values failed")
    if not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-5):
        raise ValueError("Vectors must be nonzero and L2 normalized")


def load_encoder():
    import torch
    from transformers import AutoModel, AutoTokenizer
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False)
    model = AutoModel.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False, attn_implementation="eager").eval()
    return tokenizer, model


def encode(texts, tokenizer, model):
    import numpy as np
    import torch
    if not texts:
        return np.empty((0, 384), dtype="float32")
    lengths = [len(tokenizer.encode(t, add_special_tokens=True, truncation=False)) for t in texts]
    if max(lengths) > 512 or any(not t.strip() for t in texts):
        raise ValueError("Empty or oversize input; refusing embedding truncation")
    vectors = []
    for offset in range(0, len(texts), 4):
        batch = tokenizer(texts[offset:offset + 4], padding=True, truncation=False, return_tensors="pt")
        with torch.inference_mode():
            cls = model(**batch).last_hidden_state[:, 0]
            cls = torch.nn.functional.normalize(cls, p=2, dim=1)
        vectors.append(cls.cpu().numpy().astype("float32"))
    return np.concatenate(vectors)


def verify_model():
    metadata = json.loads((PHASE / "outputs/bge_pinned_metadata.json").read_text(encoding="utf-8"))
    if metadata["sha"] != REVISION:
        raise ValueError("Model metadata revision mismatch")
    hashes = {}
    for name in ["model.safetensors", "config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt"]:
        item = next(f for f in metadata["siblings"] if f["rfilename"] == name)
        path = MODEL_DIR / name
        digest = sha256(path)
        if "lfs" in item:
            if digest != item["lfs"]["sha256"] or path.stat().st_size != item["lfs"]["size"]:
                raise ValueError("Pinned LFS model bytes differ")
        else:
            data = path.read_bytes()
            if hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != item["blobId"]:
                raise ValueError("Pinned tokenizer/config Git blob differs")
        hashes[name] = digest
    return hashes


def main():
    content_path = ROOT / "07_concepts_questions_and_chunks/outputs/content_manifest.json"
    chunks_path = ACCEPTED_CHUNKS
    metadata = PHASE / "outputs/bge_pinned_metadata.json"
    with run_record("10_embeddings_and_database", [content_path, chunks_path, metadata, MODEL_DIR / "model.safetensors"]) as run:
        import numpy as np
        content = json.loads(content_path.read_text(encoding="utf-8"))
        if content["artifact_hashes"][chunks_path.relative_to(ROOT).as_posix()] != sha256(chunks_path):
            raise ValueError("Accepted chunks changed")
        hashes = verify_model()
        chunks = read_jsonl(chunks_path)
        if any(c["review_status"] != "approved" or c["retrieval_visibility"] != "evidence" or c["corpus_version"] != content["corpus_version"] for c in chunks):
            raise ValueError("Unapproved/private/incompatible embedding input")
        start = time.perf_counter()
        tokenizer, model = load_encoder()
        load_seconds = time.perf_counter() - start
        start = time.perf_counter()
        vectors = encode([c["text"] for c in chunks], tokenizer, model)
        seconds = time.perf_counter() - start
        ids = [c["chunk_id"] for c in chunks]
        validate_vectors(vectors, ids)
        release_id = "bge-" + hashlib.sha256((sha256(chunks_path) + REVISION + hashes["model.safetensors"] + "cls-l2-float32-exact-text").encode()).hexdigest()[:16]
        folder = PHASE / "vectors" / release_id
        folder.mkdir(parents=True, exist_ok=True)
        vector_path = folder / "vectors.npy"
        if vector_path.exists():
            old = np.load(vector_path, allow_pickle=False)
            if not np.array_equal(old, vectors):
                raise ValueError("Frozen embedding bytes changed; require a new embedding configuration/release")
        else:
            np.save(vector_path, vectors, allow_pickle=False)
        ids_path = folder / "chunk_ids.jsonl"
        write_jsonl(ids_path, [{"chunk_id": i} for i in ids])
        manifest = dict(embedding_release_id=release_id, corpus_version=content["corpus_version"], embedding_model_id=MODEL_ID,
                        model_revision=REVISION, tokenizer_revision=REVISION, model_file_hashes=hashes, vector_dimension=384,
                        normalization="L2", pooling="CLS last_hidden_state[:,0]", document_format="exact chunk text, no prefix",
                        query_format=QUERY_PREFIX + "{query}", max_input_tokens=512, record_count=len(ids), dtype="float32",
                        chunk_config_hash=sha256(content_path), chunks_sha256=sha256(chunks_path), vector_path=vector_path.relative_to(ROOT).as_posix(),
                        chunk_ids_path=ids_path.relative_to(ROOT).as_posix(), vector_sha256=sha256(vector_path), chunk_ids_sha256=sha256(ids_path),
                        hardware="Intel i7-1260P CPU; two Torch threads", load_seconds=load_seconds, encode_seconds=seconds,
                        chunks_per_second=len(ids) / seconds, controller_peak_working_set_bytes=peak_working_set(),
                        measurement_limit="Mixed workload with a separate response-model benchmark; not isolated latency", run_id=run["run_id"])
        out = PHASE / "outputs/embedding_manifest.json"
        out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend([out, vector_path, ids_path]); run["counts"] = {k: manifest[k] for k in ["record_count", "vector_dimension", "load_seconds", "encode_seconds", "controller_peak_working_set_bytes"]}
        print(json.dumps(run["counts"]))


if __name__ == "__main__":
    main()
