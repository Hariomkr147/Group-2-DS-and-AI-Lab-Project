"""Run the whole data preparation, in order, and stop at the first failure.

    python docs/milestone-2/preprocessing/scripts/run_pipeline.py
    python docs/milestone-2/preprocessing/scripts/run_pipeline.py --skip-download --skip-ncert

Step                 Script                    Reads                          Writes (preprocessing/processed/)
 1 download          download.py               the internet                   raw/
 2 learner model     prep_dkt.py               raw/assistments_2009/sb.csv    dkt/
 3 chat corpus       prep_chat.py              raw/mathdial, raw/socrateach   chat/
 4 NCERT text        prep_ncert.py             raw/ncert                      ncert/
 5 chapter titles    build_chapter_titles.py   raw/ncert_toc                  ncert/chapters.csv
 6 course packs      build_course_packs.py     course_packs/specs.py + ncert  course_packs/
 7 test scenarios    build_scenarios.py        (hand-written lists)           ../test_scenarios/
 8 detector score    eval_misconception.py     scenarios + backend detector   misconception_eval.json
 9 figures           make_figures.py           everything above               ../../figures/
10 checks            check_data.py             everything above               (exit code)

The DKT arrays used for modelling are the frozen set in hosted_dataset/assistments_dkt; step 2 repeats the
recipe as a script. Its validation split is made by make_validation_splits.py.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = [("download", "download.py"), ("dkt", "prep_dkt.py"), ("chat", "prep_chat.py"), ("ncert", "prep_ncert.py"),
         ("titles", "build_chapter_titles.py"), ("packs", "build_course_packs.py"), ("scenarios", "build_scenarios.py"),
         ("detector", "eval_misconception.py"), ("figures", "make_figures.py"), ("checks", "check_data.py")]

if __name__ == "__main__":
    skipped = {a[7:] for a in sys.argv[1:] if a.startswith("--skip-")}
    if "ncert" in skipped:
        skipped |= {"titles", "packs"}
    for name, script in STEPS:
        if name in skipped:
            print(f"-- skip {name}")
            continue
        print(f"== {name}: {script}", flush=True)
        if subprocess.run([sys.executable, str(HERE / script)]).returncode:
            sys.exit(f"step '{name}' failed ({script})")
    print("pipeline finished")
