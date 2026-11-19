"""Measure Windows process peak working set during one controlled local parser case."""
import ctypes
import importlib.metadata
import json
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "00_setup_and_scope/code"))
from pipeline import ROOT, SOURCES, local_path, read_csv, run_record


def peak_working_set(process_id=None):
    if sys.platform != "win32":
        raise RuntimeError("This measured counter is Windows-only")
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("faults", ctypes.c_ulong),
                    *[(name, ctypes.c_size_t) for name in ("peak_working_set", "working_set", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile")]]
    info = Counters()
    info.cb = ctypes.sizeof(info)
    query = ctypes.WinDLL("psapi", use_last_error=True).GetProcessMemoryInfo
    query.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    query.restype = ctypes.c_int
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.OpenProcess(0x0410, False, process_id) if process_id is not None else ctypes.c_void_p(-1)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not query(handle, ctypes.byref(info), info.cb):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        if process_id is not None:
            kernel.CloseHandle(handle)
    assert info.peak_working_set >= info.working_set > 0
    return info.peak_working_set


if __name__ == "__main__":
    with run_record("03_parser_benchmark", [SOURCES]) as run:
        source = next(s for s in read_csv(SOURCES) if "g8-" in s["source_id"] and s["chapter_title"] != "Prelims")
        folder = ROOT / "03_parser_benchmark/evidence/parser_outputs" / run["run_id"]
        folder.mkdir(parents=True)
        output = folder / "memory-case.zip"
        os.environ.update(MINERU_HOME=str(ROOT / ".mineru-state"), MINERU_MODEL_ONNX_DEVICE="cpu", MINERU_MODEL_SOURCE="local")
        baseline_peak = peak_working_set()
        sys.argv = ["mineru-kit", "parse", str(local_path(source["local_path"])), "--pages", "10", "--tier", "basic", "--ocr-mode", "auto", "--format", "zip", "-o", str(output)]
        succeeded = False
        try:
            from mineru.kit.main import main
            try:
                main()
            except SystemExit as exc:
                if exc.code not in (None, 0):
                    raise
            with zipfile.ZipFile(output) as bundle:
                middle = json.loads(bundle.read("middle_json.json"))
                assert [p["page_idx"] + 1 for p in middle["pages"]] == [10]
            succeeded = True
        finally:
            peak = peak_working_set()
            assert peak >= baseline_peak
            result = {"run_id": run["run_id"], "source_id": source["source_id"], "source_sha256": source["sha256"],
                      "page_number": 10, "mineru_version": importlib.metadata.version("mineru"), "engine": "ONNX CPU Basic",
                      "baseline_lifetime_peak_working_set_bytes": baseline_peak, "lifetime_peak_working_set_bytes": peak,
                      "scope": "Windows main process peak working set through parse/export; excludes descendant/render-worker processes",
                      "inference_succeeded": succeeded, "quality_status": "not scored"}
            path = ROOT / "03_parser_benchmark/outputs/parser_process_memory.json"
            path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            run["outputs"].extend([path, output])
            print(json.dumps(result, indent=2))
