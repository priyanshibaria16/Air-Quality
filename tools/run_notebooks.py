"""
Execute the project notebooks and store their real outputs inside the .ipynb.

    python tools/run_notebooks.py                  # all notebooks, in order
    python tools/run_notebooks.py 01 04            # only those starting 01 / 04
    python tools/run_notebooks.py --timeout 1800   # per-cell timeout in seconds

Execution is done with nbclient, so the saved notebooks contain the same
numbers the console run produced - nothing is typed in by hand. A failing cell
stops that notebook (the traceback is printed) but the remaining notebooks are
still attempted, so one problem does not hide the rest.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"


def run_one(path: Path, timeout: int) -> tuple[bool, float, str]:
    start = time.time()
    nb = nbformat.read(str(path), as_version=4)
    # Keep the CPU BLAS pool small: nested parallelism (a parallel forest inside
    # parallel cross-validation) can exhaust memory.
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    client = NotebookClient(nb, timeout=timeout, kernel_name="python3",
                            resources={"metadata": {"path": str(ROOT)}})
    try:
        client.execute()
    except CellExecutionError as exc:
        nbformat.write(nb, str(path))
        return False, time.time() - start, str(exc)
    nbformat.write(nb, str(path))
    return True, time.time() - start, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("selectors", nargs="*",
                    help="only notebooks whose filename starts with one of these")
    ap.add_argument("--timeout", type=int, default=1200)
    args = ap.parse_args()

    notebooks = sorted(NB_DIR.glob("*.ipynb"))
    if args.selectors:
        notebooks = [n for n in notebooks
                     if any(n.name.startswith(s) for s in args.selectors)]
    if not notebooks:
        print("no notebooks matched - run tools/build_notebooks.py first")
        return 1

    failures = []
    for nb in notebooks:
        print(f"executing {nb.name} ...", flush=True)
        ok, secs, err = run_one(nb, args.timeout)
        print(f"  {'done  ' if ok else 'FAILED'} {nb.name}  ({secs:.1f}s)", flush=True)
        if not ok:
            failures.append((nb.name, err))
            print("  " + "\n  ".join(err.strip().splitlines()[-25:]), flush=True)

    print(f"\n{len(notebooks) - len(failures)}/{len(notebooks)} notebooks executed "
          "with outputs stored.")
    for name, _ in failures:
        print("  failed:", name)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
