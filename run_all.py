"""Re-run the whole pipeline from the frozen raw CSV: python run_all.py"""
import runpy
import sys
import time
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
STEPS = ["01_audit_raw.py", "02_clean.py", "03_split.py", "04_tables.py", "05_eda.py", "06_tests.py"]

if __name__ == "__main__":
    for step in STEPS:
        t0 = time.time()
        print(f"\n===== {step} =====", flush=True)
        sys.argv = [str(SRC / step)]
        runpy.run_path(str(SRC / step), run_name="__main__")
        print(f"----- {step} done in {time.time() - t0:.0f}s", flush=True)
