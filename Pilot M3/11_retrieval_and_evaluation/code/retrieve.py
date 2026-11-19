"""Small, source-linked retrieval interface over the accepted PostgreSQL release."""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "10_embeddings_and_database/code"))
from pipeline import ROOT, read_jsonl
from embed_chunks import QUERY_PREFIX, encode, load_encoder, verify_model
from load_database import connect


def tokens(text):
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25(query, documents, k1=1.2, b=0.75):
    terms = [tokens(text) for text in documents]
    lengths = [len(t) for t in terms]
    average = sum(lengths) / len(lengths) if lengths else 1
    counts = [Counter(t) for t in terms]
    scores = [0.0] * len(terms)
    for word in set(tokens(query)):
        frequency = sum(word in c for c in counts)
        idf = math.log(1 + (len(terms) - frequency + 0.5) / (frequency + 0.5))
        for index, count in enumerate(counts):
            tf = count[word]
            if tf:
                scores[index] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * lengths[index] / average))
    return scores


def reciprocal_rank_fusion(rankings):
    scores = Counter()
    for ranking in rankings:
        for rank, (identifier, _) in enumerate(ranking, 1):
            scores[identifier] += 1 / (60 + rank)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


def resolve(dense, chunks, threshold, margin):
    scores = {}
    for identifier, score in dense:
        for cid in chunks[identifier]["concept_ids"]:
            scores[cid] = max(scores.get(cid, -1), score)
    ranked = sorted(scores.items(), key=lambda p: (-p[1], p[0]))
    if not ranked:
        return dict(status="no_evidence", concept_id=None, candidates=[])
    difference = ranked[0][1] - ranked[1][1] if len(ranked) > 1 else 1
    status = "unsupported" if ranked[0][1] < threshold else "clarify" if difference < margin else "resolved"
    return dict(status=status, concept_id=ranked[0][0] if status == "resolved" else None,
                candidates=[{"concept_id": k, "similarity": v} for k, v in ranked[:2]], score_margin=difference,
                score_meaning="cosine similarity, not probability")


class Retriever:
    def __init__(self):
        manifest = json.loads((ROOT / "07_concepts_questions_and_chunks/outputs/content_manifest.json").read_text(encoding="utf-8"))
        self.version = manifest["corpus_version"]
        self.db = connect()
        self.chunks = {r[0]["chunk_id"]: r[0] for r in self.db.execute(
            "SELECT payload FROM ncert_content.chunks WHERE corpus_version=%s ORDER BY chunk_id", (self.version,)).fetchall()}
        self.concepts = {r[0]["concept_id"]: r[0] for r in self.db.execute(
            "SELECT payload FROM ncert_content.concepts WHERE corpus_version=%s", (self.version,)).fetchall()}
        if len(self.chunks) != manifest["chunks"] or any(c["review_status"] != "approved" or c["retrieval_visibility"] != "evidence" for c in self.chunks.values()):
            self.db.close()
            raise ValueError("Loaded evidence differs from the accepted release")
        verify_model()
        self.tokenizer, self.model = load_encoder()

    def close(self):
        self.db.close()

    def query_vector(self, query):
        if not query.strip():
            raise ValueError("Query must not be empty")
        return encode([QUERY_PREFIX + query], self.tokenizer, self.model)[0]

    def rank(self, query, vector, subject=None, concept_ids=None):
        if subject not in {None, "mathematics", "science"} or (concept_ids and not set(concept_ids) <= self.concepts.keys()):
            raise ValueError("Unknown subject or concept filter")
        selected = [c for c in self.chunks.values() if (not subject or c["subject"] == subject)
                    and (not concept_ids or set(c["concept_ids"]) & set(concept_ids))]
        ids = [c["chunk_id"] for c in selected]
        dense = self.db.execute("SELECT chunk_id, 1-(embedding <=> %s::vector) AS similarity FROM ncert_content.chunks "
                                "WHERE corpus_version=%s AND chunk_id=ANY(%s) ORDER BY similarity DESC,chunk_id",
                                (json.dumps(vector.tolist(), allow_nan=False), self.version, ids)).fetchall() if ids else []
        scores = bm25(query, [c["text"] for c in selected])
        sparse = sorted(((c["chunk_id"], s) for c, s in zip(selected, scores) if s > 0), key=lambda p: (-p[1], p[0]))
        return {"BM25": sparse, "BGE_cosine": dense, "RRF_BM25_BGE": reciprocal_rank_fusion([sparse, dense])}

    def search(self, query, subject=None, concept_ids=None, k=5):
        if not isinstance(k, int) or not 1 <= k <= 5:
            raise ValueError("k must be 1..5")
        policy = json.loads((ROOT / "11_retrieval_and_evaluation/outputs/resolution_policy.json").read_text(encoding="utf-8"))
        if policy["corpus_version"] != self.version:
            raise ValueError("Routing policy belongs to another corpus")
        if policy.get('automatic_routing_enabled') is False and (not concept_ids or len(set(concept_ids))!=1):
            return dict(corpus_version=self.version,resolution=dict(status='choose_topic',concept_id=None,
                reason='Automatic topic routing did not pass validation; select one pilot topic'),hits=[])
        vector = self.query_vector(query)
        ranks = self.rank(query, vector, subject, concept_ids)
        resolution = (dict(status='resolved',concept_id=concept_ids[0],selection='explicit_user_topic')
                      if policy.get('automatic_routing_enabled') is False else
                      resolve(ranks["BGE_cosine"], self.chunks, policy["threshold"], policy["margin"]))
        hits = [{**self.chunks[i], "score": score, "ranking_method": "RRF_BM25_BGE"} for i, score in ranks["RRF_BM25_BGE"][:k]] if resolution["status"] == "resolved" else []
        return dict(corpus_version=self.version, resolution=resolution, hits=hits)

