"""
Look inside data/processed/results.json without opening it in an editor.

    python tools/inspect_results.py                 # top-level keys and sizes
    python tools/inspect_results.py clustering      # one subtree, pretty printed
    python tools/inspect_results.py insights        # the insight list, numbered
    python tools/inspect_results.py trend_test/slope_per_year

The report and slide builders read their numbers from this file; this script is
how a human checks that a quoted figure really is in there.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data" / "processed" / "results.json"


def size_of(value) -> str:
    if isinstance(value, dict):
        return f"dict({len(value)} keys)"
    if isinstance(value, list):
        return f"list({len(value)} items)"
    text = str(value)
    return text if len(text) <= 90 else text[:87] + "..."


def main() -> None:
    if not RESULTS.exists():
        sys.exit(f"missing {RESULTS} - run notebook 09 first")
    results = json.loads(RESULTS.read_text(encoding="utf-8"))

    if len(sys.argv) < 2:
        for key, value in results.items():
            print(f"{key:26}{size_of(value)}")
        return

    node = results
    for part in sys.argv[1].strip("/").split("/"):
        if isinstance(node, list):
            node = node[int(part)]
        elif isinstance(node, dict) and part in node:
            node = node[part]
        else:
            sys.exit(f"no such key: {part} (available: {list(node)[:20]})")

    if isinstance(node, list) and node and isinstance(node[0], dict):
        headers = list(node[0])
        print(" | ".join(headers))
        for row in node:
            print(" | ".join(str(row.get(h, ""))[:60] for h in headers))
    else:
        print(json.dumps(node, indent=2, default=str))


if __name__ == "__main__":
    main()
