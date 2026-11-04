"""Retain native outputs and build a draft canonical extraction, resumable by input/config hashes."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "03_parser_benchmark/code"))
from pipeline import ROOT, SCOPE, SOURCES, local_path, read_csv, read_jsonl, run_record, sha256, write_csv, write_jsonl
from validate_manifests import validate_scope, validate_sources
from benchmark_parsers import CLI, verify_page_set
from hybrid_route_test import native_features, subject_route

PHASE = ROOT / "04_extract_text_and_ocr"
POLICY = ROOT / "03_parser_benchmark/outputs/working_parser_policy.json"
DISPOSITIONS = ROOT / "02_pdf_audit/outputs/source_page_dispositions.csv"
BENCHMARK = ROOT / "03_parser_benchmark/outputs/parser_comparison.csv"
MODEL_FILES = ROOT / "03_parser_benchmark/outputs/mineru_model_files.json"
ROUTER = ROOT / "03_parser_benchmark/code/hybrid_route_test.py"
ADAPTER = sha256(Path(__file__))[:12]
TYPES = {"text": "prose", "equation": "formula", "table": "table", "image": "diagram/image",
         "doc_title": "heading", "paragraph_title": "heading", "header": "heading",
         "footer": "heading", "page_number": "heading"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def leaves(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (list, dict)):
                yield from leaves(child)
    elif isinstance(value, list):
        for child in value:
            yield from leaves(child)


def safe_member(name):
    member = PurePosixPath(name)
    if "\\" in name or member.is_absolute() or ":" in name or ".." in member.parts or member.parts[:1] != ("images",):
        raise ValueError(f"Unsafe parser asset path: {name}")
    return member


def normalize_page(source, number, raw, parser, raw_ref, raw_hash, disposition, policy, run_id, ocr_observed_in_batch=None, parse_mode=None, routing=None):
    sid = source["source_id"]
    role = disposition["proposed_content_role"]
    routing = routing or {"target": subject_route(sid, {}, role), "features": {}, "reason": "Subject/content-role policy"}
    fallback = parser == "PyMuPDF" and routing["target"] == "mineru"
    page = {"source_id": sid, "source_sha256": source["sha256"], "page_number": number,
            "printed_page_label": None, "run_id": run_id, "parser_name": parser,
            "parser_version": policy["mineru_version"] if parser == "MinerU" else pymupdf.__version__,
            "engine": "ONNX CPU Basic" if parser == "MinerU" else "native CPU",
            "model_revision": policy["model_revision"] if parser == "MinerU" else None,
            "extraction_route": "mineru-basic" if parser == "MinerU" else "native-fallback" if fallback else "native-science" if role == "chapter_content" else "native-excluded",
            "planned_route": routing["target"], "route_reason": routing["reason"], "native_features": routing["features"],
            "ocr_used": None if parser == "MinerU" else False,
            "ocr_observed_in_batch": ocr_observed_in_batch if parser == "MinerU" else False,
            "parser_parse_mode": parse_mode if parser == "MinerU" else "native",
            "ocr_observation_scope": "MinerU exposes batch mode/logs, not per-page OCR invocation" if parser == "MinerU" else "Native PyMuPDF; no OCR",
            "status": "quarantined" if fallback else "extracted",
            "warnings": ["Draft: source/meaning review pending", "Printed labels are not inferred from parser page-number guesses"],
            "raw_output_ref": raw_ref, "raw_output_sha256": raw_hash, "content_role": role,
            "retrieval_visibility": "private" if role == "private_answer" else "not_accepted",
            "review_status": "quarantined" if fallback else "pending", "confidence": None,
            "corpus_version": None, "policy_id": policy["policy_id"], "adapter_revision": ADAPTER}
    if fallback:
        page["warnings"].append("Selected math/layout route unavailable; native fallback is not accepted evidence")
    blocks = []
    for order, block in enumerate(raw["blocks"]):
        if parser == "MinerU":
            kind = block["type"]
            content = block.get("content", "")
            nodes = list(leaves(block))
            text = content if isinstance(content, str) else "".join(n.get("content", "") for n in leaves(content)
                      if n.get("type") in {"text", "equation_inline", "code_inline"} and isinstance(n.get("content"), str))
            formulas = [n["content"] for n in nodes if n.get("type") in {"equation", "equation_inline"} and isinstance(n.get("content"), str)]
            html = next((n["content"] for n in nodes if n.get("type") == "table_body" and isinstance(n.get("content"), str)), None)
            bbox = block.get("bbox")
            coordinates = "MinerU normalized 0..1 page frame; dimensions in native docvortex_layout metadata"
            assets = sorted({n["image_path"] for n in nodes if n.get("image_path")})
        else:
            kind = "text" if block["type"] == 0 else "image"
            text = "\n".join("".join(s["text"] for s in line["spans"]) for line in block.get("lines", []))
            formulas, html, assets = [], None, [block["asset_path"]] if block.get("asset_path") else []
            bbox = block.get("bbox")
            coordinates = "PyMuPDF unrotated page points; native page dimensions/rotation retained"
        blocks.append({"block_id": f"{sid}:p{number:03}:{raw_hash[:12]}:{ADAPTER}:b{order:03}",
                       "source_id": sid, "source_sha256": source["sha256"], "page_number": number,
                       "block_order": order, "bbox": bbox, "coordinate_system": coordinates,
                       "section_hint": None, "content_type": "answer" if role == "private_answer" else TYPES.get(kind, "unknown"),
                       "native_content_type": kind, "raw_text": text, "raw_markdown": None,
                       "raw_latex": block.get("content") if parser == "MinerU" and kind == "equation" else None,
                       "inline_formulas": formulas, "raw_html": html, "asset_ids": assets,
                       "parent_raw_ref": raw_ref, "raw_output_sha256": raw_hash, "review_status": page["review_status"],
                       "content_role": role, "retrieval_visibility": page["retrieval_visibility"],
                       "confidence": None, "corpus_version": None, "adapter_revision": ADAPTER})
    return page, blocks


def native_source(source, run, policy, dispositions):
    key = digest({"source": source["sha256"], "parser": pymupdf.__version__, "format": "native-dict-features-and-page-visual-v2",
                  "router_sha256": sha256(ROUTER), "page_roles": [dispositions[(source["source_id"], n)]["proposed_content_role"] for n in range(1, int(source["pdf_pages"]) + 1)]})
    folder = PHASE / "native_outputs" / f"native-{key}"
    path, receipt = folder / "pages.jsonl", folder / "receipt.json"
    if receipt.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved["sha256"] != sha256(path):
            raise ValueError("Changed native cache; inspect before recovery")
        run["native_sources_reused"] += 1
        return read_jsonl(path), path
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    with pymupdf.open(local_path(source["local_path"])) as doc:
        for number, page in enumerate(doc, 1):
            try:
                data = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
                _, features = native_features(page)
                if source["subject"] == "science" and dispositions[(source["source_id"], number)]["proposed_content_role"] == "chapter_content" and (features["drawings"] or features["images"]):
                    image = PHASE / "assets" / f"native-{key}" / f"p{number:03}.png"
                    image.parent.mkdir(parents=True, exist_ok=True)
                    page.get_pixmap(matrix=pymupdf.Matrix(1.4, 1.4)).save(image)
                    data["blocks"].append({"type": 1, "bbox": list(page.rect), "asset_path": image.relative_to(ROOT).as_posix(),
                                           "asset_sha256": sha256(image), "asset_scope": "Full-page original render; diagram interpretation unreviewed"})
                rows.append({"page_number": number, "rotation": page.rotation, "raw_text": page.get_text(sort=False), "native_features": features, **data})
            except Exception as exc:
                rows.append({"page_number": number, "blocks": [], "error": f"{type(exc).__name__}: {exc}"})
    write_jsonl(path, rows)
    receipt.write_text(json.dumps({"source_sha256": source["sha256"], "sha256": sha256(path)}, indent=2), encoding="utf-8")
    run["outputs"].extend([path, receipt])
    return rows, path


def cached_mineru(sources, policy, run):
    cached = {}
    for row in read_csv(BENCHMARK):
        if row["parser_name"] != "MinerU" or row["status"] != "completed":
            continue
        source = sources[row["source_id"]]
        if row["source_sha256"] != source["sha256"] or row["parser_version"] != policy["mineru_version"]:
            raise ValueError("Benchmark cache identity differs from selected source/parser")
        path = local_path(row["raw_output_ref"])
        # Match the original run's recorded archive hash before copying cache bytes.
        records = [json.loads(line) for line in (ROOT / "03_parser_benchmark/logs/run_manifest.jsonl").read_text(encoding="utf-8").splitlines()]
        original = next(r for r in records if r["run_id"] == row["run_id"] and r["event"] == "finished")
        recorded = {key.replace("\\", "/"): value for key, value in original["output_hashes"].items()}
        expected = recorded[path.relative_to(ROOT).as_posix()]
        if sha256(path) != expected:
            raise ValueError("Changed benchmark archive")
        with zipfile.ZipFile(path) as bundle:
            middle = json.loads(bundle.read("middle_json.json"))
        verify_page_set(middle, [int(n) for n in row["page_numbers"].split(";")])
        target = PHASE / "native_outputs" / "benchmark-cache" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and sha256(target) != expected:
            raise ValueError("Changed retained benchmark cache")
        if not target.exists():
            shutil.copyfile(path, target)
        log_path = path.with_suffix(".log")
        text = log_path.read_text(encoding="utf-8", errors="replace")
        for page in middle["pages"]:
            cached[(source["source_id"], page["page_idx"] + 1)] = (page, target, middle, "OCR-rec" in text or "OCR-det" in text)
        run["outputs"].append(target)
    return cached


def main():
    with run_record("04_extract_text_and_ocr", [SCOPE, SOURCES, POLICY, DISPOSITIONS, MODEL_FILES, BENCHMARK, ROUTER]) as run:
        policy = json.loads(POLICY.read_text(encoding="utf-8"))
        sources = validate_sources(validate_scope(read_csv(SCOPE)), read_csv(SOURCES))
        by_id = {s["source_id"]: s for s in sources}
        dispositions = {(r["source_id"], int(r["page_number"])): r for r in read_csv(DISPOSITIONS)}
        expected = {(s["source_id"], n) for s in sources for n in range(1, int(s["pdf_pages"]) + 1)}
        if set(dispositions) != expected or len(read_csv(DISPOSITIONS)) != len(expected):
            raise ValueError("Page dispositions must cover every physical page exactly once")
        for key, disposition in dispositions.items():
            if disposition["source_sha256"] != by_id[key[0]]["sha256"]:
                raise ValueError("Disposition belongs to different PDF bytes")
        run.update(native_sources_reused=0, mineru_pages_reused=0, mineru_pages_new=0)
        native = {}
        for source in sources:
            rows, path = native_source(source, run, policy, dispositions)
            for page in rows:
                native[(source["source_id"], page["page_number"])] = (page, path)
        routes = {}
        for key, (page, _) in native.items():
            features = page.get("native_features", {})
            role = dispositions[key]["proposed_content_role"]
            target = subject_route(key[0], features, role)
            routes[key] = {"target": target, "features": features,
                           "reason": f"role={role}; subject={by_id[key[0]]['subject']}; tables={features.get('tables', 0)}; table_caption={features.get('table_caption', 0)}; number_only_lines={features.get('num_lines', 0)}; notation={features.get('notation', 0)}"}
        model_files = json.loads(MODEL_FILES.read_text(encoding="utf-8"))["files"]
        for name, expected_hash in model_files.items():
            model_root = ROOT / ".mineru-state/models"
            model_path = (model_root / name).resolve()
            if not model_path.is_relative_to(model_root) or sha256(model_path) != expected_hash:
                raise ValueError(f"Changed selected model file: {name}")
        python = CLI.with_name("python.exe" if os.name == "nt" else "python")
        installed = subprocess.check_output([str(python), "-c", "import importlib.metadata; print(importlib.metadata.version('mineru'))"], text=True).strip()
        if installed != policy["mineru_version"] or pymupdf.__version__ != policy["native_parser_version"]:
            raise ValueError("Selected parser version differs from installed environment")
        cached = cached_mineru(by_id, policy, run)
        for receipt in sorted((PHASE / "native_outputs").glob("mineru-*/receipt.json")):
            saved = json.loads(receipt.read_text(encoding="utf-8"))
            request = saved["request"]
            sid = next((sid for sid, source in by_id.items() if source["sha256"] == request["source_sha256"]), None)
            if sid is None or request["parser"] != installed or request["model_manifest_sha256"] != sha256(MODEL_FILES) or request["tier"] != "basic" or request["ocr_mode"] != "auto":
                continue
            archive = receipt.with_name("result.zip")
            if sha256(archive) != saved["sha256"]:
                raise ValueError("Changed retained MinerU page cache")
            with zipfile.ZipFile(archive) as bundle:
                middle = json.loads(bundle.read("middle_json.json"))
            verify_page_set(middle, request["pages"])
            log_text = local_path(saved["log_ref"]).read_text(encoding="utf-8", errors="replace")
            for page in middle["pages"]:
                cached.setdefault((sid, page["page_idx"] + 1), (page, archive, middle, "OCR-rec" in log_text or "OCR-det" in log_text))
        env = {**os.environ, "MINERU_HOME": str(ROOT / ".mineru-state"), "MINERU_MODEL_ONNX_DEVICE": "cpu", "MINERU_MODEL_SOURCE": "local"}
        batch_rows, failure_rows = [], []
        for source in sources:
            sid = source["source_id"]
            wanted = [n for n in range(1, int(source["pdf_pages"]) + 1) if routes[(sid, n)]["target"] == "mineru"]
            missing = [n for n in wanted if (sid, n) not in cached]
            run["mineru_pages_reused"] += len(wanted) - len(missing)
            for offset in range(0, len(missing), policy["batch_pages"]):
                numbers = missing[offset:offset + policy["batch_pages"]]
                request = {"source_sha256": source["sha256"], "pages": numbers, "parser": installed,
                           "tier": "basic", "engine": "ONNX CPU", "ocr_mode": "auto", "model_manifest_sha256": sha256(MODEL_FILES)}
                folder = PHASE / "native_outputs" / f"mineru-{digest(request)}"
                folder.mkdir(parents=True, exist_ok=True)
                output, receipt = folder / "result.zip", folder / "receipt.json"
                log = folder / f"{run['run_id']}.log"
                started, reused = time.perf_counter(), False
                try:
                    if receipt.exists():
                        saved = json.loads(receipt.read_text(encoding="utf-8"))
                        if saved["request"] != request or saved["sha256"] != sha256(output):
                            raise ValueError("Changed batch cache; inspect before recovery")
                        reused, log = True, local_path(saved["log_ref"])
                    else:
                        target = folder / f"{run['run_id']}.zip"
                        command = [str(python), "-c", "from mineru.kit.main import main; main()", "parse", str(local_path(source["local_path"])), "--pages", ",".join(map(str, numbers)),
                                   "--tier", "basic", "--ocr-mode", "auto", "--format", "zip", "-o", str(target)]
                        with log.open("w", encoding="utf-8") as stream:
                            stream.write(subprocess.list2cmdline(command) + "\n")
                            stream.flush()
                            result = subprocess.run(command, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
                        if result.returncode:
                            raise RuntimeError(f"MinerU exit {result.returncode}")
                        with zipfile.ZipFile(target) as bundle:
                            verify_page_set(json.loads(bundle.read("middle_json.json")), numbers)
                        os.replace(target, output)
                        receipt.write_text(json.dumps({"request": request, "sha256": sha256(output), "log_ref": log.relative_to(ROOT).as_posix()}, indent=2), encoding="utf-8")
                    with zipfile.ZipFile(output) as bundle:
                        middle = json.loads(bundle.read("middle_json.json"))
                    verify_page_set(middle, numbers)
                    text = log.read_text(encoding="utf-8", errors="replace")
                    for page in middle["pages"]:
                        cached[(sid, page["page_idx"] + 1)] = (page, output, middle, "OCR-rec" in text or "OCR-det" in text)
                    run["mineru_pages_reused" if reused else "mineru_pages_new"] += len(numbers)
                    batch_rows.append({"source_id": sid, "page_numbers": ";".join(map(str, numbers)), "status": "reused" if reused else "completed",
                                       "seconds": round(time.perf_counter() - started, 3), "raw_output_ref": output.relative_to(ROOT).as_posix()})
                    run["outputs"].extend([output, receipt, log])
                except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
                    for number in numbers:
                        failure_rows.append({"run_id": run["run_id"], "source_id": sid, "page_number": number, "error": str(exc), "disposition": "native fallback quarantined", "log_ref": log.relative_to(ROOT).as_posix()})
                    run["failures"].append(f"{sid} {numbers}: {exc}")
                print(f"{sid} pages {numbers}: {'reused' if reused else 'batch finished'}", flush=True)
                write_csv(PHASE / "outputs/parser_batches.csv", batch_rows, ["source_id", "page_numbers", "status", "seconds", "raw_output_ref"])
        pages, blocks, assets = [], [], {}
        for source in sources:
            for number in range(1, int(source["pdf_pages"]) + 1):
                key = (source["source_id"], number)
                use_mineru = routes[key]["target"] == "mineru" and key in cached
                if use_mineru:
                    raw, path, middle, ocr_used = cached[key]
                    parser = "MinerU"
                else:
                    raw, path = native[key]
                    parser, ocr_used = "PyMuPDF", False
                raw_hash = sha256(path)
                mode = middle.get("extensions", {}).get("mineru", {}).get("parse_mode") if use_mineru else "native"
                page, page_blocks = normalize_page(source, number, raw, parser, path.relative_to(ROOT).as_posix(), raw_hash, dispositions[key], policy, run["run_id"], ocr_used, mode, routes[key])
                if raw.get("error"):
                    page.update(status="failed", review_status="quarantined")
                    page["warnings"].append(raw["error"])
                    run["failures"].append(f"{key}: {raw['error']}")
                if use_mineru:
                    prefix = raw_hash[:16]
                    with zipfile.ZipFile(path) as bundle:
                        for block in page_blocks:
                            references = []
                            for name in block["asset_ids"]:
                                member = safe_member(name)
                                target = PHASE / "assets" / prefix / Path(*member.parts)
                                target.parent.mkdir(parents=True, exist_ok=True)
                                payload = bundle.read(name)
                                if target.exists() and sha256(target) != hashlib.sha256(payload).hexdigest():
                                    raise ValueError("Changed asset file")
                                if not target.exists():
                                    target.write_bytes(payload)
                                asset_id = f"{prefix}:{name}"
                                references.append(asset_id)
                                assets[asset_id] = {"asset_id": asset_id, "source_id": source["source_id"], "source_sha256": source["sha256"],
                                                    "page_number": number, "block_id": block["block_id"], "bbox": json.dumps(block["bbox"]),
                                                    "coordinate_system": block["coordinate_system"], "local_path": target.relative_to(ROOT).as_posix(),
                                                    "sha256": sha256(target), "meaning_review_status": "pending", "asset_scope": "parent block; tight asset coordinates retained in native JSON"}
                            block["asset_ids"] = references
                else:
                    for block in page_blocks:
                        references = []
                        for name in block["asset_ids"]:
                            target = local_path(name)
                            if not target.is_relative_to(PHASE / "assets"):
                                raise ValueError("Native visual asset outside the designated asset root")
                            aid = f"{raw_hash[:16]}:{target.name}"
                            references.append(aid)
                            original = raw["blocks"][block["block_order"]]
                            if sha256(target) != original["asset_sha256"]:
                                raise ValueError("Changed native visual asset")
                            assets[aid] = {"asset_id": aid, "source_id": source["source_id"], "source_sha256": source["sha256"], "page_number": number,
                                           "block_id": block["block_id"], "bbox": json.dumps(block["bbox"]), "coordinate_system": block["coordinate_system"],
                                           "local_path": name, "sha256": sha256(target), "meaning_review_status": "pending", "asset_scope": original["asset_scope"]}
                        block["asset_ids"] = references
                pages.append(page)
                blocks.extend(page_blocks)
        output = PHASE / "outputs"
        if (output / "pages.jsonl").exists() and any(p["review_status"] == "approved" for p in read_jsonl(output / "pages.jsonl")):
            raise ValueError("Refusing to replace an approved extraction; select a new release path")
        write_jsonl(output / "pages.jsonl", pages)
        write_jsonl(output / "blocks.jsonl", blocks)
        write_jsonl(output / run["run_id"] / "pages.jsonl", pages)
        write_jsonl(output / run["run_id"] / "blocks.jsonl", blocks)
        asset_fields = "asset_id source_id source_sha256 page_number block_id bbox coordinate_system local_path sha256 meaning_review_status asset_scope".split()
        write_csv(output / "assets_manifest.csv", list(assets.values()), asset_fields)
        write_csv(output / "extraction_failures.csv", failure_rows, ["run_id", "source_id", "page_number", "error", "disposition", "log_ref"])
        write_csv(output / "page_accounting.csv", [{k: p[k] for k in ("source_id", "source_sha256", "page_number", "status", "parser_name", "extraction_route", "content_role", "retrieval_visibility")} for p in pages],
                  ["source_id", "source_sha256", "page_number", "status", "parser_name", "extraction_route", "content_role", "retrieval_visibility"])
        run["outputs"].extend(output / name for name in ("pages.jsonl", "blocks.jsonl", "assets_manifest.csv", "extraction_failures.csv", "page_accounting.csv", "parser_batches.csv"))
        run["outputs"].extend(output / run["run_id"] / name for name in ("pages.jsonl", "blocks.jsonl"))
        run["counts"] = {"pages": len(pages), "blocks": len(blocks), "assets": len(assets)}
        from validate_extraction import validate_extraction
        validate_extraction(sources, pages, blocks, list(assets.values()))
        print(json.dumps({**run["counts"], "mineru_pages_new": run["mineru_pages_new"], "mineru_pages_reused": run["mineru_pages_reused"]}), flush=True)
        return 1 if run["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
