"""Smoke test for src/docx_builder.py - builds a tiny document outside the project.

    python tools/smoke_docx.py            # writes <temp>/aqi_smoke.docx
    python tools/smoke_docx.py --pdf      # also drive Word to make the PDF

The output goes to the system temp directory on purpose: a test artefact must not
appear next to the real report in report/.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd  # noqa: E402

import docx_builder as D  # noqa: E402

b = D.DocxBuilder("Air Quality Intelligence", "Project report")
b.heading("1. Test", 1)
b.para("Hello world, justified body text.", align="justify")
b.rich([("PM2.5 ", "b"), ("mean = ", ""), ("250.6", "i")])
b.bullets(["first", "second"])
b.numbered(["alpha", "beta"])
b.code("print('hello')")
b.table(pd.DataFrame({"A": [1.5, 2.25], "B": ["p", "q"]}), caption="Smoke test table")
b.figure(ROOT / "visualizations/methodology/01_methodology_diagram.png",
         "Smoke figure", width_in=3.0)
b.toc('TOC \\o "1-3" \\h \\z \\u', "Contents")
b.toc('TOC \\c "Figure" \\h \\z \\u', "List of Figures")
out = b.save(Path(tempfile.gettempdir()) / "aqi_smoke.docx")
print("wrote", out, out.stat().st_size, "bytes")
print("words:", D.count_words("one two three"))

if "--pdf" in sys.argv:
    print("wrote", D.convert_to_pdf(out))
