"""
Check the generated report instead of trusting that it "looks fine".

    python tools/verify_report.py            # structure + section list
    python tools/verify_report.py --pdf      # also count PDF pages

Reads the .docx back with python-docx and reports: the numbered top-level headings
in order, whether Word computed the table of contents and list of figures (a field
that was never updated leaves no 'toc 1' paragraphs), how many captions/tables/
inline images exist, and the word count of the abstract. It also greps the whole
document for placeholder text that must not be submitted.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import docx  # noqa: E402

import config as C  # noqa: E402

DOCX = C.REPORT_DIR / "Air_Quality_Intelligence_Report.docx"
PDF = C.REPORT_DIR / "Air_Quality_Intelligence_Report.pdf"

# The 28 numbered sections the brief prescribes. Sections 1-8 are front matter
# (title page, certificate, declaration, acknowledgement, abstract and the three
# contents lists), which carries a name rather than a number in an Indian
# university report format, so they are checked by title below.
REQUIRED_SECTIONS = {9: "Introduction", 10: "Problem Statement", 11: "Objectives",
                     12: "Dataset", 13: "Technology", 14: "Methodology",
                     15: "Preprocessing", 16: "Exploratory", 17: "Correlation",
                     18: "K-Means", 19: "Anomaly", 20: "Classification",
                     21: "Model Evaluation", 22: "Power BI", 23: "Results",
                     24: "Findings", 25: "Limitations", 26: "Future Scope",
                     27: "Conclusion", 28: "References"}

REQUIRED_FRONT_MATTER = ("Certificate", "Declaration", "Acknowledgement", "Abstract",
                         "Table of Contents", "List of Figures", "List of Tables")

PLACEHOLDER_PATTERNS = (r"To be calculated", r"TODO", r"FIXME", r"\bn/a\b")

# The front matter is written before the student's details exist, so these are
# reported as a checklist to complete rather than as defects.
IDENTITY_PATTERNS = (r"<STUDENT", r"<ENROLMENT", r"<\w+ NAME>", r"<\w+ UNIVERSITY>",
                     r"<YYYY-YYYY>", r"<DD MONTH YYYY>", r"<CITY>")


def main() -> int:
    if not DOCX.exists():
        print("MISSING", DOCX, "- run tools/build_report.py first")
        return 1
    d = docx.Document(str(DOCX))
    paras = d.paragraphs

    h1 = [p.text.strip() for p in paras if p.style.name == "Heading 1"]
    numbered = [t for t in h1 if re.match(r"^\d+\.", t)]
    print(f"paragraphs: {len(paras):,}   tables: {len(d.tables)}   "
          f"inline images: {len(d.inline_shapes)}")
    print(f"heading-1 entries: {len(h1)}  (numbered sections: {len(numbered)})")
    print("Headings  :", ", ".join(numbered) or "NONE - section numbering is broken")

    problems = []
    for num, expected in REQUIRED_SECTIONS.items():
        hit = [t for t in numbered if t.startswith(f"{num}.")]
        if not hit:
            problems.append(f"section {num} ({expected}) is missing")
        elif expected.lower() not in hit[0].lower():
            problems.append(f"section {num} is titled {hit[0]!r}, expected to contain "
                            f"{expected!r}")

    for name in REQUIRED_FRONT_MATTER:
        if name not in h1:
            problems.append(f"front-matter heading {name!r} is missing")

    toc = [p.text.strip() for p in paras if p.style.name.startswith("toc")]
    figs = [p.text.strip() for p in paras if p.style.name.startswith("table of figures")]
    print(f"TOC entries computed by Word : {len(toc)}")
    print(f"List-of-figures entries      : {len(figs)}")
    if not toc:
        problems.append("the table of contents was never computed (no 'toc' paragraphs) "
                        "- open the .docx in Word and press Ctrl+A, F9, or export with "
                        "tools/build_report.py which drives Word to update fields")
    if toc:
        print("first TOC lines:", " | ".join(toc[:3]))
    if figs:
        print("first figure line:", figs[0])

    captions = [p.text.strip() for p in paras if p.style.name == "Caption"]
    figures = sum(1 for c in captions if c.startswith("Figure"))
    tables_cap = sum(1 for c in captions if c.startswith("Table"))
    print(f"SEQ captions: {len(captions)} (Figures {figures}, Tables {tables_cap})")
    if figures != len(d.inline_shapes):
        problems.append(f"{figures} figure captions but {len(d.inline_shapes)} embedded "
                        "images - a figure is missing its caption or its picture")
    if tables_cap != len(d.tables):
        problems.append(f"{tables_cap} table captions but {len(d.tables)} tables - one "
                        "table has no caption")

    # The abstract is the body text under its own heading, up to the next heading.
    words = None
    texts = [p for p in range(len(paras)) if paras[p].style.name == "Heading 1"]
    for i, start in enumerate(texts):
        if paras[start].text.strip() != "Abstract":
            continue
        stop = texts[i + 1] if i + 1 < len(texts) else len(paras)
        body_text = " ".join(p.text.strip() for p in paras[start + 1:stop]
                             if p.text.strip() and not p.text.startswith("Keywords")
                             and "Abstract length" not in p.text)
        words = len(body_text.split())
        print("abstract words:", words)
        break
    if words is None:
        problems.append("abstract section could not be located for the word count")
    elif not 200 <= words <= 300:
        problems.append(f"abstract is {words} words; the brief asks for 200-300")

    for pattern in PLACEHOLDER_PATTERNS:
        found = [p.text.strip()[:90] for p in paras if re.search(pattern, p.text)]
        if found:
            print(f"forbidden text {pattern!r}: {len(found)} occurrence(s)")
            for f in found[:3]:
                print("   ", f)
            if pattern == r"\bn/a\b":
                problems.append("a value printed as 'n/a' - the artefact behind it did "
                                "not exist when the report was built")
            else:
                problems.append(f"{pattern!r} text is present in the report")

    body = "\n".join(p.text for p in paras)
    to_fill = sorted({m for pattern in IDENTITY_PATTERNS
                      for m in re.findall(pattern + r"[^\n]*", body)})
    if to_fill:
        print("front matter still to complete by hand:")
        for m in to_fill:
            print("   ", m[:80])

    if "--pdf" in sys.argv:
        if not PDF.exists():
            problems.append("PDF was not written (Word conversion failed or --no-pdf)")
        else:
            print(f"pdf: {PDF.stat().st_size:,} bytes")
            # Word writes the final page count into the document properties when it
            # repaginates, which is more reliable than parsing the PDF object stream.
            import zipfile

            with zipfile.ZipFile(DOCX) as archive:
                app = archive.read("docProps/app.xml").decode("utf-8", "ignore")
            found = re.search(r"<Pages>(\d+)</Pages>", app)
            if found:
                print(f"paginated by Word: {found.group(1)} pages "
                      "(docProps/app.xml, written at export time)")
            else:
                problems.append("the document reports no page count - Word may not have "
                                "repaginated it; open it in Word and press Ctrl+A, F9")

    print()
    if problems:
        print("PROBLEMS:")
        for p in problems:
            print("  -", p)
        return 1
    print("report structure verified: every required numbered section is present, "
          "fields were computed, and no forbidden placeholder text remains.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
