"""
Print the stored text output of an executed notebook (debug helper).

    python tools/show_outputs.py notebooks/01_data_understanding.ipynb
    python tools/show_outputs.py notebooks/01_data_understanding.ipynb --cells 5-9

Tables rendered as HTML are shown as their text/plain fallback, so this stays
readable in a console.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat

ROOT = Path(__file__).resolve().parents[1]


def parse_cells(spec: str) -> list[int] | None:
    if not spec:
        return None
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("notebook")
    ap.add_argument("--cells", default="", help="1-based cell numbers, e.g. 3 or 5-9")
    ap.add_argument("--limit", type=int, default=4000, help="chars per output block")
    args = ap.parse_args()

    nb = nbformat.read(str(Path(args.notebook).resolve()), as_version=4)
    wanted = parse_cells(args.cells)
    shown = 0
    for i, cell in enumerate(nb.cells, start=1):
        if cell.cell_type != "code":
            continue
        if wanted and i not in wanted:
            continue
        shown += 1
        print(f"\n{'=' * 78}\nCODE CELL {i}\n{'-' * 78}")
        print(cell.source)
        for out in cell.get("outputs", []):
            kind = out.get("output_type")
            if kind == "stream":
                text = out.get("text", "")
            elif kind in ("execute_result", "display_data"):
                text = out.get("data", {}).get("text/plain", "")
            elif kind == "error":
                text = "\n".join(out.get("traceback", []))
            else:
                text = f"<{kind}>"
            text = text if isinstance(text, str) else "\n".join(text)
            print(f"--- {kind} ---")
            print(text[:args.limit] + ("\n...[truncated]" if len(text) > args.limit else ""))
    if not shown:
        print("no code cells matched")
    return 0


if __name__ == "__main__":
    sys.exit(main())
