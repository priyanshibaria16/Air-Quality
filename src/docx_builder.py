"""
Reusable Word (.docx) builder for the project report.

Why a builder instead of writing the document by hand: every number, table and
figure in the report comes from code, so the report can be regenerated after any
re-run and cannot quietly fall out of step with the analysis.

What this module adds on top of python-docx:

* consistent A4 layout, fonts and margins;
* real Word fields - Table of Contents, List of Figures, List of Tables,
  auto-numbered `Figure N` / `Table N` captions (SEQ fields) and PAGE numbers -
  so the document behaves like a submitted report rather than a text dump;
* a `table()` helper that accepts a DataFrame directly;
* `convert_to_pdf()` which drives the installed Microsoft Word through COM to
  update every field and export a PDF (fields are only computed by Word itself).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C

BODY_FONT = "Times New Roman"
MONO_FONT = "Consolas"
ACCENT = RGBColor(0x1F, 0x4E, 0x79)


def _field(paragraph, instr: str, placeholder: str = ""):
    """Insert a Word field (e.g. PAGE, SEQ Figure) into a paragraph.

    The `placeholder` text is what Word shows until the field is updated; the
    .docx is opened in Word by convert_to_pdf(), which refreshes every field.
    """
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    code = OxmlElement("w:instrText")
    code.set(qn("xml:space"), "preserve")
    code.text = instr
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = placeholder
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for node in (begin, code, separate, text, end):
        run._r.append(node)
    return run


class DocxBuilder:
    """Small, explicit wrapper around a python-docx Document."""

    def __init__(self, header_text: str = "", footer_text: str = ""):
        self.doc = Document()
        self._configure_styles()
        self._configure_page(header_text, footer_text)
        self.fig_no = 0
        self.tab_no = 0

    # ------------------------------------------------------------------ setup
    def _configure_styles(self) -> None:
        normal = self.doc.styles["Normal"]
        normal.font.name = BODY_FONT
        normal.font.size = Pt(11)
        normal.element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.25

        for level, size in ((1, 16), (2, 13), (3, 11.5)):
            style = self.doc.styles[f"Heading {level}"]
            style.font.name = BODY_FONT
            style.font.size = Pt(size)
            style.font.bold = True
            style.font.color.rgb = ACCENT
            style.paragraph_format.space_before = Pt(14 if level == 1 else 10)
            style.paragraph_format.space_after = Pt(6)
            style.paragraph_format.keep_with_next = True

        caption = self.doc.styles["Caption"]
        caption.font.name = BODY_FONT
        caption.font.size = Pt(9.5)
        caption.font.bold = False
        caption.font.italic = True
        caption.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        caption.paragraph_format.space_before = Pt(3)
        caption.paragraph_format.space_after = Pt(10)
        caption.paragraph_format.keep_with_next = False

    def _configure_page(self, header_text: str, footer_text: str) -> None:
        for section in self.doc.sections:
            section.page_width, section.page_height = Cm(21.0), Cm(29.7)   # A4
            section.top_margin = Inches(1.0)
            section.bottom_margin = Inches(1.0)
            section.left_margin = Inches(1.1)
            section.right_margin = Inches(1.0)

            header_p = section.header.paragraphs[0]
            header_p.text = header_text
            header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            for run in header_p.runs:
                run.font.size = Pt(8.5)
                run.font.name = BODY_FONT
                run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

            footer_p = section.footer.paragraphs[0]
            footer_p.text = ""
            footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if footer_text:
                r = footer_p.add_run(footer_text + "     ")
                r.font.size = Pt(8.5)
                r.font.name = BODY_FONT
            r = footer_p.add_run("Page ")
            r.font.size = Pt(8.5)
            r.font.name = BODY_FONT
            page = _field(footer_p, "PAGE", "1")
            page.font.size = Pt(8.5)
            page.font.name = BODY_FONT
            of = footer_p.add_run(" of ")
            of.font.size = Pt(8.5)
            of.font.name = BODY_FONT
            nums = _field(footer_p, "NUMPAGES", "1")
            nums.font.size = Pt(8.5)
            nums.font.name = BODY_FONT

    # -------------------------------------------------------------- primitives
    def heading(self, text: str, level: int = 1) -> None:
        self.doc.add_heading(text, level=level)

    def para(self, text: str = "", style: str | None = None,
             align: str | None = None, size: float | None = None,
             bold: bool = False, italic: bool = False, mono: bool = False) -> "object":
        p = self.doc.add_paragraph(style=style)
        run = p.add_run(text)
        run.bold, run.italic = bold, italic
        run.font.name = MONO_FONT if mono else BODY_FONT
        if size:
            run.font.size = Pt(size)
        if align == "center":
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif align == "right":
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        elif align == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        return p

    def rich(self, parts: list[tuple[str, str]], align: str | None = None) -> None:
        """One paragraph from (text, marker) pairs; marker may contain b/i/mono."""
        p = self.doc.add_paragraph()
        for text, marker in parts:
            run = p.add_run(text)
            run.font.name = MONO_FONT if "mono" in marker else BODY_FONT
            run.bold = "b" in marker.split() or marker == "b"
            run.italic = "i" in marker.split() or marker == "i"
            if "small" in marker:
                run.font.size = Pt(9)
        if align == "justify":
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

    def bullets(self, items: list[str], style: str = "List Bullet") -> None:
        for item in items:
            self.doc.add_paragraph(item, style=style)

    def numbered(self, items: list[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Number")

    def steps(self, items: list[str], start: int = 1) -> None:
        """Explicitly numbered list with a hanging indent.

        Word's built-in List Number style shares one counter across the whole
        document, which silently continues numbering from the previous list. The
        report has many independent numbered lists (objectives, limitations,
        future scope), so the numbers are written here instead.
        """
        for offset, item in enumerate(items):
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.first_line_indent = Inches(-0.4)
            p.paragraph_format.space_after = Pt(4)
            run = p.add_run(f"{start + offset}.  ")
            run.bold = True
            run.font.name = BODY_FONT
            p.add_run(item).font.name = BODY_FONT

    def code(self, text: str) -> None:
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.3)
        p.paragraph_format.space_after = Pt(8)
        run = p.add_run(text)
        run.font.name = MONO_FONT
        run.font.size = Pt(8.5)
        _shade(p, "F2F2F2")

    def page_break(self) -> None:
        self.doc.add_page_break()

    def section_break(self) -> None:
        self.doc.add_section(WD_SECTION.NEW_PAGE)

    # ------------------------------------------------------------- structured
    def _caption(self, kind: str, text: str, above: bool = False) -> None:
        """`Figure N` / `Table N` caption with a live SEQ field for auto-number."""
        p = self.doc.add_paragraph(style="Caption")
        if kind == "Figure":
            self.fig_no += 1
        else:
            self.tab_no += 1
        p.add_run(f"{kind} ")
        _field(p, f"SEQ {kind} \\* ARABIC", str(self.fig_no if kind == "Figure"
                                                else self.tab_no))
        p.add_run(f": {text}")
        if above:
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(3)

    def table(self, data, caption: str | None = None, font_size: float = 8.5,
              max_rows: int | None = None, widths: list[float] | None = None,
              note: str | None = None) -> None:
        """Add a table from a DataFrame (or a list of header/row sequences)."""
        if caption:
            self._caption("Table", caption, above=True)
        if isinstance(data, pd.DataFrame):
            df = data
            if max_rows is not None and len(df) > max_rows:
                df = pd.concat([df.head(max_rows), df.tail(2)])
                truncated = True
            else:
                truncated = False
            headers = [str(c) for c in df.columns]
            rows = [[_cell(v) for v in record] for record in df.itertuples(index=False)]
        else:
            headers, rows = list(data[0]), [list(r) for r in data[1:]]
            truncated = False
            if max_rows is not None and len(rows) > max_rows:
                rows = rows[:max_rows]
                truncated = True

        t = self.doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = True if widths is None else False
        for i, text in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.text = ""
            run = cell.paragraphs[0].add_run(str(text))
            run.bold = True
            run.font.size = Pt(font_size)
            run.font.name = BODY_FONT
            _shade(cell, "DDE7F1")
        for record in rows:
            cells = t.add_row().cells
            for i, value in enumerate(record[:len(headers)]):
                cells[i].text = ""
                run = cells[i].paragraphs[0].add_run(str(value))
                run.font.size = Pt(font_size)
                run.font.name = BODY_FONT
                cells[i].paragraphs[0].paragraph_format.space_after = Pt(1)
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths[:len(row.cells)]):
                    row.cells[i].width = Inches(w)
        if truncated:
            self.para(f"Table shows the first {max_rows} rows only; the complete "
                      f"table is in the referenced CSV file.", size=8.5, italic=True)
        if note:
            self.para(note, size=8.5, italic=True)

    def figure(self, path, caption: str, width_in: float = 5.6) -> None:
        """Embed an image and give it an auto-numbered caption."""
        path = Path(path)
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        if path.exists():
            p.add_run().add_picture(str(path), width=Inches(width_in))
            self._caption("Figure", caption)
        else:                                  # never silently drop a figure
            self._caption("Figure", caption)
            self.para(f"[missing image: {path.name}]", size=9, italic=True,
                      align="center")

    def toc(self, instr: str, title: str | None = None) -> None:
        if title:
            self.para(title, bold=True, size=13)
        p = self.doc.add_paragraph()
        _field(p, instr, "Right-click and choose 'Update Field' (done "
                         "automatically when the PDF is built).")

    def save(self, path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path)
        return path


# ---------------------------------------------------------------- helpers
def _cell(value) -> str:
    """Cell text: short numbers stay numeric, everything else is stringified."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    if isinstance(value, float):
        return f"{value:,.4f}".rstrip("0").rstrip(".") if abs(value) < 1e6 \
            else f"{value:,.1f}"
    if isinstance(value, (int,)):
        return f"{value:,}"
    return str(value)


def _shade(element, hex_fill: str) -> None:
    """Apply a background fill to a paragraph or a table cell."""
    pr = element._p.get_or_add_pPr() if hasattr(element, "_p") \
        else element._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    pr.append(shd)


def convert_to_pdf(docx_path, pdf_path=None, timeout: int = 240) -> Path:
    """Open the .docx in Microsoft Word, update every field, export a PDF.

    Word is the only program that can compute a Table of Contents, so this step
    cannot be done with python-docx alone. Falls back to the plain .docx if Word
    or pywin32 is unavailable - the caller decides whether that is acceptable.
    """
    docx_path = Path(docx_path)
    pdf_path = Path(pdf_path) if pdf_path else docx_path.with_suffix(".pdf")
    import pythoncom                      # noqa: F401 - imported here so the
    import win32com.client                # module still works without pywin32
    from win32com.client import constants  # noqa: F401

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        d = word.Documents.Open(str(docx_path), ReadOnly=False, AddToRecentFiles=False)
        d.Repaginate()
        for i in range(1, d.TablesOfContents.Count + 1):
            d.TablesOfContents.Item(i).Update()
        d.Fields.Update()                 # page numbers / SEQ need a 2nd pass
        d.Repaginate()
        for i in range(1, d.TablesOfContents.Count + 1):
            d.TablesOfContents.Item(i).Update()
        d.Save()
        d.ExportAsFixedFormat(OutputFileName=str(pdf_path), ExportFormat=17)
        d.Close(SaveChanges=0)
    finally:
        word.Quit()
        pythoncom.CoUninitialize()
    return pdf_path


def count_words(text: str) -> int:
    """Whitespace word count - used to keep the abstract inside 200-300 words."""
    return len(text.split())
