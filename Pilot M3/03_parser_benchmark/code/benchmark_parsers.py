"""Run native PyMuPDF and local MinerU Basic on identical original PDF pages."""
import json
import os
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, SCOPE, SOURCES, local_path, read_csv, run_record, sha256, write_csv
from validate_manifests import validate_scope, validate_sources

PHASE = ROOT / "03_parser_benchmark"
SELECTION = ROOT / "02_pdf_audit/outputs/parser_benchmark_pages.csv"
CLI = ROOT / ".mineru-venv" / ("Scripts/mineru-kit.exe" if os.name == "nt" else "bin/mineru-kit")


def page_groups(selection, sources):
    by_id = {r["source_id"]: r for r in sources}
    groups = {}
    for row in selection:
        sid, number = row["source_id"], int(row["page_number"])
        if sid not in by_id or number < 1 or number > int(by_id[sid]["pdf_pages"]):
            raise ValueError(f"Invalid benchmark page: {sid} p{number}")
        if number in groups.setdefault(sid, []):
            raise ValueError(f"Duplicate benchmark page: {sid} p{number}")
        groups[sid].append(number)
    if not groups:
        raise ValueError("Empty benchmark selection")
    return {sid: sorted(numbers) for sid, numbers in groups.items()}


def verify_page_set(middle, expected):
    actual = [p["page_idx"] + 1 for p in middle["pages"]]
    if actual != sorted(expected):
        raise ValueError(f"MinerU page identity mismatch: {actual} != {sorted(expected)}")


def command_log(command, env, log_path, timeout):
    with log_path.open("w", encoding="utf-8") as stream:
        stream.write(subprocess.list2cmdline(list(map(str, command))) + "\n")
        stream.flush()
        result = subprocess.run(list(map(str, command)), env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"Command exited {result.returncode}; see {log_path.relative_to(ROOT)}")


def main():
    with run_record("03_parser_benchmark", [SCOPE, SOURCES, SELECTION]) as run:
        sources = validate_sources(validate_scope(read_csv(SCOPE)), read_csv(SOURCES))
        by_id = {s["source_id"]: s for s in sources}
        groups = page_groups(read_csv(SELECTION), sources)
        artifacts = PHASE / "evidence/parser_outputs" / run["run_id"]
        artifacts.mkdir(parents=True)
        rows, raw = [], []
        fields = "run_id source_id source_sha256 page_numbers parser_name parser_version engine ocr_mode_requested ocr_used status elapsed_seconds timing_scope peak_ram_bytes raw_output_ref review_status error".split()
        for sid, numbers in groups.items():
            started = time.perf_counter()
            path = artifacts / f"{sid}-pymupdf.jsonl"
            with pymupdf.open(local_path(by_id[sid]["local_path"])) as doc:
                for number in numbers:
                    page = doc[number - 1]
                    raw.append({"source_id": sid, "source_sha256": by_id[sid]["sha256"],
                                "page_number": number, "printed_page_label": None,
                                "raw_text": page.get_text(sort=False),
                                "blocks": page.get_text("blocks"), "review_status": "pending"})
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in raw if r["source_id"] == sid), encoding="utf-8")
            rows.append(dict(zip(fields, [run["run_id"], sid, by_id[sid]["sha256"], ";".join(map(str, numbers)),
                                         "PyMuPDF", pymupdf.__version__, "native CPU", "none", False,
                                         "completed", round(time.perf_counter() - started, 6),
                                         "source open + selected pages + output write; in-process", "",
                                         path.relative_to(ROOT).as_posix(), "pending", ""])))
            run["outputs"].append(path)
        comparison = PHASE / "outputs/parser_comparison.csv"
        write_csv(comparison, rows, fields)
        run["outputs"].append(comparison)
        env = {**os.environ, "MINERU_HOME": str(ROOT / ".mineru-state"),
               "MINERU_MODEL_ONNX_DEVICE": "cpu", "MINERU_MODEL_SOURCE": "huggingface"}
        setup_log = artifacts / "mineru-model-setup.log"
        run["outputs"].append(setup_log)
        try:
            if not CLI.is_file():
                raise RuntimeError("Install pinned MinerU in the documented separate environment first")
            command_log([CLI, "models", "download", "--tier", "basic", "--source", "huggingface"], env, setup_log, 1800)
            verify_log = artifacts / "mineru-model-verification.log"
            run["outputs"].append(verify_log)
            command_log([CLI, "models", "verify", "--tier", "basic"], env, verify_log, 60)
            weights = ROOT / ".mineru-state/models"
            model_manifest = PHASE / "outputs/mineru_model_files.json"
            model_manifest.write_text(json.dumps({"mineru_version": "4.1.3", "tier": "basic",
                "engine": "ONNX CPU", "upstream_revision": None,
                "files": {p.relative_to(weights).as_posix(): sha256(p)
                          for p in weights.rglob("*") if p.is_file() and ".cache" not in p.parts}}, indent=2) + "\n", encoding="utf-8")
            run["outputs"].append(model_manifest)
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            run["failures"].append(f"MinerU setup: {exc}")
            for sid, numbers in groups.items():
                rows.append({"run_id": run["run_id"], "source_id": sid,
                             "source_sha256": by_id[sid]["sha256"], "page_numbers": ";".join(map(str, numbers)),
                             "parser_name": "MinerU", "parser_version": "4.1.3", "engine": "ONNX CPU",
                             "ocr_mode_requested": "auto", "ocr_used": "unknown; not run", "status": "not_run_setup_failed",
                             "review_status": "pending", "error": str(exc)})
            write_csv(comparison, rows, fields)
            return 1
        for sid, numbers in groups.items():
            output = artifacts / f"{sid}-mineru.zip"
            log = artifacts / f"{sid}-mineru.log"
            started = time.perf_counter()
            row = {"run_id": run["run_id"], "source_id": sid, "source_sha256": by_id[sid]["sha256"],
                   "page_numbers": ";".join(map(str, numbers)), "parser_name": "MinerU", "parser_version": "4.1.3",
                   "engine": "ONNX CPU Basic", "ocr_mode_requested": "auto", "ocr_used": "inspect native metadata; not inferred",
                   "status": "completed", "timing_scope": "CLI startup + source batch parse + zip export; models cached",
                   "peak_ram_bytes": "", "raw_output_ref": output.relative_to(ROOT).as_posix(),
                   "review_status": "pending", "error": ""}
            try:
                command_log([CLI, "parse", local_path(by_id[sid]["local_path"]), "--pages", ",".join(map(str, numbers)),
                             "--tier", "basic", "--ocr-mode", "auto", "--format", "zip", "-o", output], env, log, 1800)
                with zipfile.ZipFile(output) as bundle:
                    middle = json.loads(bundle.read("middle_json.json"))
                verify_page_set(middle, numbers)
            except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError, zipfile.BadZipFile) as exc:
                row.update(status="failed", error=str(exc))
                run["failures"].append(f"{sid}: {exc}")
            row["elapsed_seconds"] = round(time.perf_counter() - started, 6)
            rows.append(row)
            write_csv(comparison, rows, fields)
            run["outputs"].extend([output, log])
            print(f"{sid}: MinerU {row['status']} ({row['elapsed_seconds']} s)", flush=True)
        return 1 if run["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
