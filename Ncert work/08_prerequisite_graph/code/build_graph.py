"""Generate a tiny pair universe, apply explicit reviews and validate traversals."""
import hashlib
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, read_csv, read_jsonl, run_record, sha256, write_csv, write_jsonl

PHASE = ROOT / "08_prerequisite_graph"
CONCEPTS = ROOT / "07_concepts_questions_and_chunks/outputs/concepts.jsonl"
REVIEWS = PHASE / "outputs/edge_reviews.csv"


def prerequisites(edges, concept, depth=3):
    if not isinstance(depth, int) or not 0 <= depth <= 10:
        raise ValueError("Depth must be 0..10")
    visited, frontier, found = {concept}, [concept], []
    for level in range(1, depth + 1):
        next_level = sorted({e["prerequisite_id"] for e in edges if e["dependent_id"] in frontier} - visited)
        found.extend({"concept_id": k, "depth": level} for k in next_level)
        visited.update(next_level); frontier = next_level
    return found


def validate_graph(edges, concepts):
    pairs = set()
    for e in edges:
        a, b = e["prerequisite_id"], e["dependent_id"]
        if a not in concepts or b not in concepts or a == b or (a, b) in pairs or e["review_status"] != "approved":
            raise ValueError("Unknown/self/duplicate/unreviewed edge")
        pairs.add((a, b))
    remaining = set(concepts)
    while remaining:
        roots = {n for n in remaining if not any(b == n and a in remaining for a, b in pairs)}
        if not roots:
            raise ValueError("Prerequisite cycle")
        remaining -= roots


def reviewed(concepts):
    """Pilot concepts carry edge reviews; automatic section concepts get no prerequisite edges yet."""
    return [c for c in concepts if c.get("review_method") != "automatic_section_heading"]


def reviewed_fingerprint(concepts):
    """Edge reviews bind to what was reviewed: the pilot concept records, not the corpus version stamp."""
    records = sorted(({k: v for k, v in c.items() if k != "corpus_version"} for c in reviewed(concepts)), key=lambda c: c["concept_id"])
    return hashlib.sha256(json.dumps(records, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def candidates(concepts):
    output = []
    for a, b in itertools.combinations(reviewed(concepts), 2):
        a, b = sorted([a, b], key=lambda c: (c["grade"], c["concept_id"]))
        same_math = a["subject"] == b["subject"] == "mathematics"
        output.append(dict(edge_id="pair-" + hashlib.sha256((a["concept_id"] + "|" + b["concept_id"]).encode()).hexdigest()[:16],
                           concept_a=a["concept_id"], concept_b=b["concept_id"], proposed_relation="a_to_b" if same_math else "neither",
                           proposal_method="Grade-ordered mathematics candidate heuristic; not a semantic prerequisite assertion",
                           evidence_block_ids=sorted(set(a["source_block_ids"] + b["source_block_ids"])),
                           corpus_version=a["corpus_version"], review_status="pending"))
    return output


def main():
    inputs = [CONCEPTS] + ([REVIEWS] if REVIEWS.exists() else [])
    with run_record("08_prerequisite_graph", inputs) as run:
        concepts = read_jsonl(CONCEPTS)
        proposed = candidates(concepts)
        byid = {p["edge_id"]: p for p in proposed}
        reviews = read_csv(REVIEWS) if REVIEWS.exists() else []
        if len(reviews) != len({r["edge_id"] for r in reviews}):
            raise ValueError("Duplicate edge review")
        accepted = []
        for row in reviews:
            if row["edge_id"] not in byid or row["concepts_sha256"] != reviewed_fingerprint(concepts):
                raise ValueError("Review belongs to changed or unknown concepts")
            if row["review_method"] != "user_delegated_codex_ai_source_judgment" or not row["reason"] or row["reviewer"] != "Codex" or not row["review_date"]:
                raise ValueError("Missing authorized review evidence")
            pair = byid[row["edge_id"]]
            if row["decision"] in {"a_to_b", "b_to_a"}:
                a, b = pair["concept_a"], pair["concept_b"]
                if row["decision"] == "b_to_a":
                    a, b = b, a
                accepted.append(dict(edge_id=row["edge_id"], prerequisite_id=a, dependent_id=b, review_status="approved", reviewer=row["reviewer"],
                                     review_method=row["review_method"], review_date=row["review_date"], reason=row["reason"],
                                     evidence_block_ids=json.dumps(pair["evidence_block_ids"]), corpus_version=pair["corpus_version"]))
            elif row["decision"] not in {"neither", "related_only", "transitive_only"}:
                raise ValueError("Unrecognized pair decision")
        validate_graph(accepted, {c["concept_id"] for c in concepts})
        out = PHASE / "outputs"
        write_jsonl(out / "candidate_edges.jsonl", proposed)
        fields = "edge_id prerequisite_id dependent_id review_status reviewer review_method review_date reason evidence_block_ids corpus_version".split()
        write_csv(out / "approved_edges.csv", accepted, fields)
        metrics = dict(run_id=run["run_id"], concepts=len(concepts), candidate_pairs=len(proposed), reviewed_pairs=len(reviews), approved_edges=len(accepted),
                       cycles=0, direction="prerequisite -> dependent", independent_gold_precision=None, independent_gold_recall=None,
                       evaluation_limit="Same Codex AI reviewer assessed all pilot pairs; no independent gold or generalization claim",
                       prerequisite_trace=prerequisites(accepted, "percentages", 3))
        (out / "graph_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        run["outputs"].extend(out / p for p in ["candidate_edges.jsonl", "approved_edges.csv", "graph_metrics.json"])
        run["counts"] = metrics
        print(json.dumps(metrics))


if __name__ == "__main__":
    main()
