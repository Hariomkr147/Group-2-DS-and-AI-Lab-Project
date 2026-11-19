"""Reproducibly verify stored embeddings, their inputs, and database alignment."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '00_setup_and_scope/code'))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / '09_skill_misconception_and_scope_mapping/code'))
from pipeline import ROOT, local_path, read_csv, read_jsonl, run_record, sha256
from embed_chunks import encode, load_encoder, validate_vectors, verify_model
from load_database import connect
from load_eedi_catalogue import catalogue


def verify_database_rows(ids, texts, vectors, rows):
    if len(rows) != len(ids) or len({r[0] for r in rows}) != len(rows):
        raise ValueError('Database count or IDs differ')
    saved = {r[0]: (r[1], np.asarray(json.loads(r[2]), dtype=np.float32)) for r in rows}
    for identifier, text, vector in zip(ids, texts, vectors, strict=True):
        if identifier not in saved or saved[identifier][0] != text or not np.allclose(saved[identifier][1], vector, rtol=0, atol=1e-6):
            raise ValueError('Database identity, text or vector differs')


def main():
    phase = ROOT / '10_embeddings_and_database'
    embedding_path = phase / 'outputs/embedding_manifest.json'
    eedi_path = ROOT / '09_skill_misconception_and_scope_mapping/outputs/eedi_catalogue_manifest.json'
    content_path = ROOT / '07_concepts_questions_and_chunks/outputs/content_manifest.json'
    with run_record('10_embeddings_and_database', [embedding_path, eedi_path, content_path]) as run:
        embedding, eedi, content = [json.loads(p.read_text(encoding='utf-8')) for p in (embedding_path, eedi_path, content_path)]
        chunk_path = local_path(content['accepted_chunk_path'])
        if sha256(chunk_path) != embedding['chunks_sha256'] or sha256(chunk_path) != content['artifact_hashes'][content['accepted_chunk_path']]:
            raise ValueError('Accepted chunk input hash mismatch')
        chunks = read_jsonl(chunk_path)
        if any(c['review_status'] != 'approved' or c['retrieval_visibility'] != 'evidence' or c['corpus_version'] != content['corpus_version'] for c in chunks):
            raise ValueError('Unapproved/private/mismatched chunks')
        for relative, expected in eedi['input_sha256'].items():
            if sha256(local_path(relative)) != expected:
                raise ValueError('Pinned Eedi source mismatch')
        source = local_path(next(p for p in eedi['input_sha256'] if p.endswith('data/misconception-map.csv')))
        constructs = local_path(next(p for p in eedi['input_sha256'] if p.endswith('data/construct-map.csv')))
        graph = catalogue(read_csv(constructs), read_csv(source))
        if graph != read_jsonl(ROOT / '09_skill_misconception_and_scope_mapping/outputs/misconceptions.jsonl'):
            raise ValueError('Eedi text or row ordering differs from pinned source')
        chunk_vectors_path, graph_vectors_path = local_path(embedding['vector_path']), local_path(eedi['vector_path'])
        ids_path = local_path(embedding['chunk_ids_path'])
        if any(sha256(p) != expected for p, expected in [(chunk_vectors_path, embedding['vector_sha256']),
               (graph_vectors_path, eedi['vector_sha256']), (ids_path, embedding['chunk_ids_sha256'])]):
            raise ValueError('Vector or identity file hash mismatch')
        ids = [c['chunk_id'] for c in chunks]
        if [row['chunk_id'] for row in read_jsonl(ids_path)] != ids:
            raise ValueError('Chunk order differs from embedding row order')
        graph_ids = [r['misconception_id'] for r in graph]
        chunk_vectors, graph_vectors = np.load(chunk_vectors_path, allow_pickle=False), np.load(graph_vectors_path, allow_pickle=False)
        validate_vectors(chunk_vectors, ids); validate_vectors(graph_vectors, graph_ids)
        verify_model()
        tokenizer, model = load_encoder()
        recomputed = encode([c['text'] for c in chunks], tokenizer, model)
        if not np.allclose(recomputed, chunk_vectors, rtol=0, atol=1e-5):
            raise ValueError('Recomputed NCERT vectors differ')
        sample = sorted(range(len(graph)), key=lambda i: hashlib.sha256(graph_ids[i].encode()).hexdigest())[:20]
        reproduced_graph = encode([graph[i]['text'] for i in sample], tokenizer, model)
        if not np.allclose(reproduced_graph, graph_vectors[sample], rtol=0, atol=1e-5):
            raise ValueError('Recomputed Eedi sample differs')
        with connect() as db:
            db.execute('SET TRANSACTION READ ONLY')
            rows = db.execute('SELECT chunk_id,text,embedding::text FROM ncert_content.chunks WHERE corpus_version=%s', (content['corpus_version'],)).fetchall()
            verify_database_rows(ids, [c['text'] for c in chunks], chunk_vectors, rows)
            graph_rows = db.execute('SELECT misconception_id,text,embedding::text FROM ncert_diag.misconceptions WHERE dataset_release=%s', (eedi['dataset_release_id'],)).fetchall()
            verify_database_rows(graph_ids, [r['text'] for r in graph], graph_vectors, graph_rows)
        summary = dict(run_id=run['run_id'], status='passed', corpus_version=content['corpus_version'],
                       ncert_vectors_checked=len(ids), eedi_vectors_checked=len(graph_ids), dimensions=384,
                       ncert_vectors_recomputed=len(ids), eedi_vectors_recomputed=len(sample),
                       sample_method='20 lowest SHA256(misconception_id), deterministic',
                       checks=['input/model/vector hashes', 'source IDs and row order', 'finite L2-normalized vectors',
                               'recomputed vector agreement', 'all database IDs, text and vectors agree'],
                       limitations=['No individual vector needs visual review', 'Passing integrity checks does not prove source transcription or retrieval relevance',
                                    'The Eedi recomputation is a sample; all stored Eedi vectors are checked against their file and database'])
        path = phase / 'outputs/automatic_embedding_audit.json'
        path.write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        run['outputs'].append(path); run['counts'] = summary
        print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
