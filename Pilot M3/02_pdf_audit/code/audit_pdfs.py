"""Inventory every physical page; probes and routes are provisional, not accepted extraction."""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, SCOPE, SOURCES, local_path, read_csv, run_record, write_csv
from validate_manifests import validate_scope, validate_sources

PHASE = ROOT / "02_pdf_audit"


def probe_page(page, source, number):
    text = page.get_text(sort=False)
    blocks = page.get_text("dict")["blocks"]
    spans = [s for b in blocks if b["type"] == 0 for line in b["lines"] for s in line["spans"]]
    images = sum(b["type"] == 1 for b in blocks)
    drawings = len(page.get_drawings())
    pua = sum(0xE000 <= ord(c) <= 0xF8FF for c in text)
    numeric_lines = sum(bool(re.fullmatch(r"\s*\d+\s*", line)) for line in text.splitlines())
    superscripts = sum(bool(s["flags"] & 1) for s in spans)
    operators = sum(c in "+−–×÷=<>%/" for c in text)
    if not text.strip():
        route = "scan/image-heavy" if images or drawings else "manual-review"
    elif pua:
        route = "manual-review"
    elif numeric_lines >= 4 or superscripts or operators >= 8:
        route = "layout/formula-heavy"
    elif images or drawings:
        route = "mixed"
    else:
        route = "native-text candidate"
    row = {"source_id": source["source_id"], "source_sha256": source["sha256"],
           "page_number": number, "printed_page_label": "", "status": "probed",
           "native_chars": len(text), "text_blocks": sum(b["type"] == 0 for b in blocks),
           "image_blocks": images, "drawing_paths": drawings, "numeric_lines": numeric_lines,
           "superscript_spans": superscripts, "operator_chars": operators,
           "private_use_chars": pua, "replacement_chars": text.count("\ufffd"),
           "route_candidate": route, "warnings": "heuristic flags; printed label not reviewed"}
    return row, {"source_id": source["source_id"], "source_sha256": source["sha256"],
                 "page_number": number, "raw_text": text,
                 "blocks": [{k: b[k] for k in ("number", "type", "bbox")} for b in blocks]}


def select_benchmark(pages, roles):
    chapters = [r for r in pages if roles[r["source_id"]] == "chapter" and r["status"] == "probed"]
    selected = {}
    for sid in dict.fromkeys(r["source_id"] for r in chapters):
        group = [r for r in chapters if r["source_id"] == sid]
        selected[(sid, 1)] = ["chapter opener; title and reading-order check"]
        for field, reason in (("numeric_lines", "stacked numeric lines / fraction-layout candidate"),
                              ("superscript_spans", "superscript or subscript candidate"),
                              ("drawing_paths", "vector diagram or table-layout candidate")):
            page = max(group, key=lambda r: r[field])
            if page[field]:
                selected.setdefault((sid, page["page_number"]), []).append(reason)
        page = min(group, key=lambda r: r["native_chars"])
        selected.setdefault((sid, page["page_number"]), []).append("sparsest native-text page; no dropping")
    return [{"source_id": sid, "page_number": number, "selection_reason": "; ".join(reasons),
             "selection_status": "pending visual stratification review", "printed_page_label": ""}
            for (sid, number), reasons in selected.items()]


def main():
    with run_record("02_pdf_audit", [SCOPE, SOURCES]) as run:
        scope = validate_scope(read_csv(SCOPE))
        sources = validate_sources(scope, read_csv(SOURCES))
        roles = {r["source_id"]: r["role"] for r in scope}
        pages, inventory, probes = [], [], []
        for source in sources:
            with pymupdf.open(local_path(source["local_path"])) as doc:
                inventory.append({**{k: source[k] for k in ("source_id", "subject", "grade", "edition", "bytes", "pdf_pages", "sha256")},
                                  "role": roles[source["source_id"]], "encrypted": doc.is_encrypted,
                                  "toc_entries": len(doc.get_toc()), "pdf_format": doc.metadata.get("format")})
                for number, page in enumerate(doc, 1):
                    try:
                        row, probe = probe_page(page, source, number)
                        probes.append(probe)
                    except Exception as exc:
                        row = {"source_id": source["source_id"], "source_sha256": source["sha256"],
                               "page_number": number, "status": "failed", "route_candidate": "manual-review",
                               "warnings": f"{type(exc).__name__}: {exc}"}
                        run["failures"].append(f"{source['source_id']} p{number}: {exc}")
                    pages.append(row)
        assert len(pages) == sum(int(s["pdf_pages"]) for s in sources), "Page accounting mismatch"
        assert len({(r['source_id'], r['page_number']) for r in pages}) == len(pages)
        output = PHASE / "outputs"
        write_csv(output / "pdf_inventory.csv", inventory, list(inventory[0]))
        fields = list(dict.fromkeys(k for row in pages for k in row))
        write_csv(output / "page_audit.csv", pages, fields)
        benchmark_path = output / "parser_benchmark_pages.csv"
        if benchmark_path.exists():
            benchmark = read_csv(benchmark_path)
            available = {(p["source_id"], p["page_number"]) for p in pages}
            for row in benchmark:
                row["page_number"] = int(row["page_number"])
                if (row["source_id"], row["page_number"]) not in available:
                    raise ValueError("Frozen parser development page disappeared")
        else:
            benchmark = select_benchmark(pages, roles)
        write_csv(output / "parser_benchmark_pages.csv", benchmark, list(benchmark[0]))
        probe_path = PHASE / f"evidence/probes/{run['run_id']}.jsonl"
        probe_path.parent.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in probes), encoding="utf-8")
        run["outputs"] = [output / name for name in ("pdf_inventory.csv", "page_audit.csv", "parser_benchmark_pages.csv")]
        run["outputs"].append(probe_path)
        by_id = {r["source_id"]: r for r in sources}
        render_dir = PHASE / "evidence/selected_page_renders"
        render_dir.mkdir(parents=True, exist_ok=True)
        for row in benchmark:
            with pymupdf.open(local_path(by_id[row["source_id"]]["local_path"])) as doc:
                path = render_dir / f"{row['source_id']}-p{row['page_number']:03}.png"
                doc[row["page_number"] - 1].get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25)).save(path)
                run["outputs"].append(path)
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
        chapter_sources = [s for s in sources if roles[s["source_id"]] == "chapter"]
        axes[0].bar([f"{s['subject']} {s['grade']}" for s in chapter_sources], [int(s["pdf_pages"]) for s in chapter_sources])
        axes[0].set(title="Initial sample: 4 of 43 chapters in four named books", ylabel="Physical chapter-PDF pages")
        axes[0].tick_params(axis="x", rotation=20)
        counts = Counter(r["route_candidate"] for r in pages)
        axes[1].barh(list(counts), list(counts.values()))
        axes[1].set(title=f"Heuristic routes; all {len(pages)} pages incl. prelims", xlabel="Physical pages; no fidelity claim")
        figure = PHASE / "figures/pdf_coverage.png"
        figure.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(figure, dpi=130)
        plt.close(fig)
        run["outputs"].append(figure)
        run["counts"] = {"sources": len(sources), "pages": len(pages), "benchmark_pages": len(benchmark), "routes": dict(counts)}
        print(json.dumps(run["counts"], indent=2))
        return 1 if run["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
