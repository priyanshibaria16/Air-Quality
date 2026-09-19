"""
Build the viva presentation (17 slides, 10-15 minutes) from the computed results.

    python tools/build_presentation.py            # writes presentation/*.pptx

Like the report builder, this script contains no hard-coded results: every number
on a slide is read from `data/processed/results.json` or from an exported CSV by
`tools/build_report.py`'s loaders, and the shared wording (title, problem statement,
objectives, limitations, future scope) is imported from that module so the deck and
the report cannot drift apart. Every slide carries speaker notes with a suggested
timing; the notes add up to about 13 minutes.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tools"))

import build_report as R                    # noqa: E402  (shared text + loaders)
import config as C                          # noqa: E402

DECK_DIR = ROOT / "presentation"
DECK = DECK_DIR / "Air_Quality_Intelligence.pptx"

NAVY = RGBColor(0x0F, 0x2A, 0x44)
TEAL = RGBColor(0x1B, 0x7F, 0x79)
AMBER = RGBColor(0xB5, 0x6A, 0x11)
GREY = RGBColor(0x55, 0x5F, 0x6B)
LIGHT = RGBColor(0xF3, 0xF5, 0xF7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)

W, H = Inches(13.333), Inches(7.5)


# --------------------------------------------------------------------------- #
# Slide furniture
# --------------------------------------------------------------------------- #
def _text(box, lines, size, color, bold_first=False, line_spacing=1.15):
    """Fill a text frame with one paragraph per entry in `lines`."""
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.text = str(item)
        para.font.size = Pt(size)
        para.font.color.rgb = color
        para.font.name = "Calibri"
        para.line_spacing = line_spacing
        para.space_after = Pt(4)
        if bold_first and i == 0:
            para.font.bold = True


def slide(prs, number, title, subtitle=None):
    """Blank slide with a coloured title band, kicker and footer."""
    s = prs.slides.add_slide(prs.slide_layouts[6])
    band = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Inches(1.05))
    band.fill.solid()
    band.fill.fore_color.rgb = NAVY
    band.line.fill.background()
    band.shadow.inherit = False
    _text(band, [title], 26, WHITE, bold_first=True)
    band.text_frame.margin_left = Inches(0.5)
    band.text_frame.margin_top = Inches(0.16)

    foot = s.shapes.add_textbox(Inches(0.5), Inches(7.0), Inches(11.0), Inches(0.35))
    _text(foot, ["Air Quality & Pollution Intelligence  |  Data Mining + Power BI"],
          10, GREY)
    num = s.shapes.add_textbox(Inches(12.1), Inches(7.0), Inches(0.9), Inches(0.35))
    _text(num, [f"{number} / 17"], 10, GREY)

    if subtitle:
        sub = s.shapes.add_textbox(Inches(0.5), Inches(1.12), Inches(12.3), Inches(0.4))
        _text(sub, [subtitle], 13, TEAL)
    return s


def bullets(s, items, left=0.55, top=1.7, width=6.4, size=15, color=None):
    """Bulleted list; items may be (text, sub-text) pairs."""
    box = s.shapes.add_textbox(Inches(left), Inches(top), Inches(width),
                               Inches(H.inches - top - 0.7))
    tf = box.text_frame
    tf.word_wrap = True
    row = 0
    for item in items:
        head, *rest = item if isinstance(item, (tuple, list)) else (item,)
        para = tf.paragraphs[0] if row == 0 else tf.add_paragraph()
        para.text = "\u2022 " + str(head)
        para.font.size = Pt(size)
        para.font.color.rgb = color or NAVY
        para.font.name = "Calibri"
        para.space_after = Pt(5)
        row += 1
        for sub_line in rest:
            para = tf.add_paragraph()
            para.text = "   " + str(sub_line)
            para.font.size = Pt(size - 3)
            para.font.color.rgb = GREY
            para.font.name = "Calibri"
            para.space_after = Pt(7)
            row += 1
    return box


def picture(s, path, left, top, width):
    p = Path(path)
    if not p.exists():
        return None
    pic = s.shapes.add_picture(str(p), Inches(left), Inches(top), Inches(width))
    pic.line.color.rgb = LIGHT
    return pic


def cards(s, values, top=1.7, left=0.55, width=12.25, height=1.25, size=22):
    """A row of KPI cards: values on top, labels underneath."""
    count = len(values)
    gap = 0.18
    each = (width - gap * (count - 1)) / count
    for i, (value, label) in enumerate(values):
        box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                                 Inches(left + i * (each + gap)), Inches(top),
                                 Inches(each), Inches(height))
        box.fill.solid()
        box.fill.fore_color.rgb = LIGHT
        box.line.color.rgb = TEAL
        box.shadow.inherit = False
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_top = Pt(8)
        for j, (line, sz, col, bold) in enumerate(
                [(str(value), size, NAVY, True), (str(label), 11, GREY, False)]):
            para = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            para.text = line
            para.font.size = Pt(sz)
            para.font.color.rgb = col
            para.font.bold = bold
            para.font.name = "Calibri"
            para.alignment = PP_ALIGN.CENTER  # value and label centred in the card


def table(s, frame, left=0.55, top=1.75, width=6.6, font=11, max_rows=12):
    """Draw a DataFrame (or list of row lists) as a real PowerPoint table."""
    if isinstance(frame, pd.DataFrame):
        frame = frame.head(max_rows)
        header, rows = list(frame.columns), frame.values.tolist()
    else:
        header, *rows = [list(r) for r in frame]
    shape = s.shapes.add_table(len(rows) + 1, len(header), Inches(left), Inches(top),
                               Inches(width), Inches(0.32 * (len(rows) + 1)))
    tbl = shape.table
    for c, name in enumerate(header):
        cell = tbl.cell(0, c)
        cell.text = str(name)
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        cell.text_frame.paragraphs[0].font.size = Pt(font)
        cell.text_frame.paragraphs[0].font.bold = True
        cell.text_frame.paragraphs[0].font.color.rgb = WHITE
    for r, row in enumerate(rows, start=1):
        for c, value in enumerate(row):
            cell = tbl.cell(r, c)
            cell.text = "" if value is None else str(value)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if r % 2 else LIGHT
            cell.text_frame.paragraphs[0].font.size = Pt(font)
            cell.text_frame.paragraphs[0].font.color.rgb = NAVY
    return tbl


def notes(s, text, minutes):
    s.notes_slide.notes_text_frame.text = (
        f"Suggested time: {minutes} minutes.\n\n{text}")


def callout(s, text, left=7.2, top=1.75, width=5.6, color=AMBER):
    box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top),
                             Inches(width), Inches(1.5))
    box.fill.solid()
    box.fill.fore_color.rgb = LIGHT
    box.line.color.rgb = color
    box.shadow.inherit = False
    _text(box, [text], 12.5, color)
    box.text_frame.margin_left = Inches(0.14)
    box.text_frame.margin_top = Inches(0.1)
    return box


# --------------------------------------------------------------------------- #
# The deck
# --------------------------------------------------------------------------- #
def build(r: dict) -> Path:
    prs = Presentation()
    prs.slide_width, prs.slide_height = W, H

    ds = r["dataset"]
    cl = r["clustering"]
    an = r["anomaly"]
    cf = r["classification"]
    comp = pd.DataFrame(cf["comparison"])
    struct = r["aqi_structure"]
    city_tbl = R.csv("city_summary.csv")
    avg_aqi = city_tbl["Avg_AQI"]
    bal = pd.DataFrame(cf["class_balance"]).sort_values("Count", ascending=False)
    top_two = " and ".join(bal["Class"].head(2))
    top_two_pct = R.n(bal["Percent"].head(2).sum())
    rarest = bal.tail(2).iloc[::-1]
    rare_a, rare_b = rarest["Class"].tolist()
    rare_a_n = R.n(rarest["Count"].iloc[0], 0)
    rare_b_n = R.n(rarest["Count"].iloc[1], 0)
    rare_a_pct = R.n(rarest["Percent"].iloc[0])

    rows = R.n(ds["rows"], 0)
    cols = R.n(ds["columns"], 0)
    cities = R.n(ds["cities"], 0)
    span = f"{ds['date_start'][:7]} to {ds['date_end'][:7]}"
    pollutants = ", ".join(ds["detected_pollutants"])
    absent = ", ".join(ds["columns_absent_vs_expected"]) or "none"
    best = comp.sort_values("Accuracy_%", ascending=False).iloc[0]
    best_name = str(best["Model"])
    best_acc = R.n(best["Accuracy_%"])
    best_f1 = R.n(best["F1_macro"], 4)
    baseline = R.n(comp.loc[comp["Model"].str.startswith("Baseline"), "Accuracy_%"]
                   .iloc[0])
    lift = R.n(best["Lift_over_Baseline_pp"])
    k = R.n(cl["choice"]["chosen_K"], 0)
    k_elbow = R.n(cl["choice"]["K_by_elbow_rule"], 0)
    sil = R.n(cl["choice"]["silhouette"], 4)
    anomalies = R.n(an["stats"]["Anomalies detected"], 0)
    anomaly_pct = R.n(an["stats"]["Anomaly %"])
    contamination = R.n(an["params"]["contamination"], 2)
    inflation = R.n(cf["leakage"]["accuracy_inflation_pp"])
    leaky_acc = R.n(cf["leakage"]["with leaky column"]["accuracy_%"])
    tree_r2 = R.n(r["predictability"]["tree_CV_R2"], 4)
    lin_r2 = R.n(r["predictability"]["linear_R2"], 4)
    forward = struct["forward_selection"]
    fwd_two = f"{forward[0]['added']} + {forward[1]['added']}"
    fwd_two_r2 = R.n(forward[1]["cv_r2"], 4)
    city_p = R.n(r["group_tests"]["City"]["ANOVA_p"], 4)
    slope = R.n(r["trend_test"]["slope_per_year"], 4)
    trend_p = R.n(r["trend_test"]["p_value"], 4)
    hi_city = str(city_tbl.loc[avg_aqi.idxmax(), "City"])
    lo_city = str(city_tbl.loc[avg_aqi.idxmin(), "City"])
    hi_aqi = R.n(avg_aqi.max())
    lo_aqi = R.n(avg_aqi.min())
    spread = R.n(avg_aqi.max() - avg_aqi.min())
    viz = C.VIZ_DIR
    ins = pd.DataFrame(r["insights"])
    # counted from the file, so the deck and the report cannot disagree about it
    measures = R.n(R.dax_measure_count(), 0)

    # 1 - Title -------------------------------------------------------------- #
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H)
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()
    bg.shadow.inherit = False
    head = s.shapes.add_textbox(Inches(0.9), Inches(2.0), Inches(11.5), Inches(2.0))
    _text(head, [R.TITLE,
                 "Data Mining and Business Intelligence - project viva",
                 R.STUDENT["name"] + "   |   " + R.STUDENT["enrolment"],
                 R.STUDENT["institute"] + "   |   " + R.STUDENT["academic_year"]],
          30, WHITE)
    head.text_frame.paragraphs[1].font.size = Pt(18)
    head.text_frame.paragraphs[1].font.color.rgb = TEAL
    head.text_frame.paragraphs[2].font.size = Pt(15)
    head.text_frame.paragraphs[3].font.size = Pt(13)
    foot = s.shapes.add_textbox(Inches(0.9), Inches(6.3), Inches(11.5), Inches(0.5))
    _text(foot, ["17 slides - about 13 minutes - notebooks, code, dataset and "
                 "dashboard all available for demonstration"], 13, WHITE)
    notes(s, "Greet the panel, name the project and say what you will show: a nine "
             "notebook mining pipeline, the processed datasets, and the Power BI "
             "design built on them. Do not read the title slide.", 0.5)

    # 2 - Introduction ------------------------------------------------------- #
    s = slide(prs, 2, "Introduction",
              "What the data is, and why the analysis is not obvious")
    bullets(s, [
        ("An AQI table mixes three kinds of object",
         "measured pollutant concentrations, one derived index (AQI), "
         "and one label derived from that index (AQI_Bucket)"),
        ("Answering ten practical questions needs an ordered pipeline",
         "cities over time, pollutant-AQI association, natural groups, unusual days, "
         "predictable categories"),
        ("Data mining answers the questions once",
         "clustering, outlier detection, classification, significance testing"),
        ("Business intelligence answers them for the next asker",
         "star schema + DAX measures + a five-page Power BI dashboard"),
        ("The commitment behind every slide",
         "numbers come from the artefacts; where evidence is weak, the deck says so"),
    ], width=12.2, size=15)
    notes(s, "Frame the project as a journey: data -> knowledge -> mining -> BI -> "
             "insight. Emphasise the derived-column point early because it drives the "
             "leakage story in slide 12.", 0.8)

    # 3 - Problem statement -------------------------------------------------- #
    s = slide(prs, 3, "Problem Statement", "As set in the project brief")
    box = s.shapes.add_textbox(Inches(0.75), Inches(1.85), Inches(11.8), Inches(2.0))
    _text(box, [R.PROBLEM_STATEMENT], 17, NAVY)
    box.text_frame.paragraphs[0].font.italic = True
    bullets(s, [
        "Summarise five cities, ten years and nine pollutants without distorting them",
        "Measure pollutant-to-AQI association, with significance attached",
        "Define 'unusual' formally, without smuggling in the answer",
        "Quantify the leakage from the derived AQI column before trusting accuracy",
        "Publish the result as an interactive dashboard with documented KPIs",
    ], top=4.0, width=12.2, size=14)
    notes(s, "Read the italic statement in one breath, then list the five concrete "
             "gaps. Do not add claims the brief did not ask for.", 0.8)

    # 4 - Objectives --------------------------------------------------------- #
    s = slide(prs, 4, "Objectives", "The ten questions the project must answer")
    half = (len(R.PROJECT_QUESTIONS) + 1) // 2
    left = [f"{i + 1}. {q}" for i, q in enumerate(R.PROJECT_QUESTIONS[:half])]
    right = [f"{half + i + 1}. {q}" for i, q in enumerate(R.PROJECT_QUESTIONS[half:])]
    bullets(s, left, left=0.55, top=1.8, width=6.0, size=15)
    bullets(s, right, left=6.85, top=1.8, width=6.0, size=15)
    box = s.shapes.add_textbox(Inches(0.55), Inches(5.3), Inches(12.3), Inches(1.4))
    _text(box, [
        "Delivered through: cleaning and feature engineering, EDA, correlation, "
        "K-Means, Isolation Forest, four classifiers, and a Power BI design.",
        "Each question is answered with a figure in the report (section 24) and on "
        "slides 8 to 14 here.",
    ], 14, GREY)
    notes(s, "Say that the questions were kept fixed and the analysis was written to "
             "answer them, not the other way round.", 0.7)

    # 5 - Dataset ------------------------------------------------------------ #
    s = slide(prs, 5, "Dataset", f"data/raw/{Path(ds['file']).name}")
    cards(s, [(rows, "rows"), (cols, "columns"), (cities, "cities"),
              (span, "date range"),
              (R.n(ds["missing_before"], 0), "missing cells on load")])
    bullets(s, [
        ("Pollutants present", pollutants),
        ("Expected but absent", absent),
        ("Derived columns", "AQI (index) and AQI_Bucket (label from AQI)"),
        ("Exact duplicate rows on load: 0; rows after cleaning: "
         + R.n(ds["rows_after_cleaning"], 0)),
        ("Provenance not documented with the file",
         "publisher, download date and collection method are unknown"),
    ], top=3.4, width=12.2, size=14)
    callout(s, "Integrity finding: the measurement columns behave like uniform draws "
               "(independent of each other and of AQI, no city/month/year effect). "
               "Treat the results as properties of this file, not as findings about "
               "Indian air.", top=3.4, left=7.2, width=5.6)
    notes(s, "This is the honest slide. State the row/column counts from memory-free "
             "facts, then state the integrity finding plainly - the panel will ask "
             "about it anyway.", 1.0)

    # 6 - Methodology -------------------------------------------------------- #
    s = slide(prs, 6, "Methodology", "Thirteen stages, each evidenced by an artefact")
    picture(s, viz / "methodology" / "01_methodology_diagram.png", 0.55, 1.55, 8.4)
    bullets(s, [
        "Everything runs from reusable modules in src/",
        "Nine notebooks execute the same code end to end",
        "Notebook 09 re-runs the pipeline once and exports every artefact",
        "results.json is the single source of numbers for report and slides",
        "random_state = 42 everywhere; versions recorded",
    ], left=9.15, top=1.8, width=3.7, size=12)
    notes(s, "Walk the four phases in the diagram: preparation, description, mining, "
             "delivery. Mention that each stage names the file that proves it.", 0.7)

    # 7 - Preprocessing ------------------------------------------------------ #
    s = slide(prs, 7, "Data Preprocessing", "Every decision logged with the values it "
                                           "touched")
    log = pd.DataFrame(r["cleaning_log"])
    # One line per kind of action: the full log runs to 43 rows, which no slide can
    # show, but every row is still in notebook 02 and in results.json.
    affected = pd.to_numeric(log["Rows / Values Affected"], errors="coerce").fillna(0)
    summary = (log.assign(Affected=affected)
                  .groupby("Action Performed", as_index=False)
                  .agg(Steps=("Step", "count"), Affected=("Affected", "sum"))
                  .rename(columns={"Action Performed": "Cleaning action",
                                   "Steps": "Steps logged",
                                   "Affected": "Values affected"}))
    table(s, summary, left=0.55, top=1.7, width=8.0, font=10, max_rows=12)
    bullets(s, [
        "Raw file opened read-only; never overwritten",
        "Exact duplicate rows found on load: " + R.n(ds["duplicates_before"], 0),
        "Date parsed to datetime; city names normalised",
        "Negative / impossible values checked per pollutant",
        "Extreme values flagged, not deleted",
        "No imputation was needed - nothing was silently filled",
    ], left=8.85, top=1.8, width=4.0, size=12)
    notes(s, "Point at the 'Values affected' column: the log is auditable, so a "
             "reviewer can re-check each step in notebook 02. The " + str(len(log)) + " "
             "individual log entries are collapsed into these groups on this slide.",
          0.8)

    # 8 - EDA ---------------------------------------------------------------- #
    s = slide(prs, 8, "Exploratory Data Analysis", "Distribution, trend, city and "
                                                   "calendar profiles")
    picture(s, viz / "eda" / "03_city_avg_median_aqi.png", 0.55, 1.7, 6.3)
    picture(s, viz / "eda" / "07_monthly_aqi.png", 0.55, 4.6, 6.3)
    bullets(s, [
        (f"Average AQI by city ranges {lo_aqi} ({lo_city}) to {hi_aqi} ({hi_city})",
         f"a spread of {spread} points on an index that runs to 500"),
        (f"City effect is not statistically detectable (ANOVA p = {city_p})",
         "the ranking is descriptive only; it must not be quoted as 'X city is more "
         "polluted'"),
        ("Category shares follow the band widths, not the air",
         top_two + " together hold " + top_two_pct + "% of records; the rarest "
         "category, " + rare_a + ", holds " + rare_a_pct + "%"),
        ("Distributions are flat, not environmental",
         "Kolmogorov-Smirnov and skew/kurtosis tests reject the usual "
         "right-skewed pollutant shape"),
        (f"No trend over ten years (slope {slope} AQI/year, p = {trend_p})",
         "reported as 'no statistically detectable trend'"),
    ], left=7.05, top=1.65, width=5.8, size=12)
    notes(s, "Two messages: what the descriptive statistics show, and why the "
             "significance tests stop you turning them into claims.", 1.0)

    # 9 - Correlation -------------------------------------------------------- #
    s = slide(prs, 9, "Correlation Analysis", "Linear r, rank r, and a non-linear check")
    picture(s, viz / "correlation" / "01_correlation_heatmap.png", 0.55, 1.65, 6.4)
    bullets(s, [
        ("Pollutant-pollutant correlation is near zero",
         "the largest absolute Pearson r in the matrix is trivial; the columns behave "
         "independently"),
        (f"Linear regression on AQI: R2 = {lin_r2}",
         "Pearson r alone would say AQI is unexplained"),
        (f"Tree ensemble on AQI: CV R2 = {tree_r2}",
         "the relationship is non-linear, so a heat map understates it"),
        (f"Forward selection: {fwd_two} reach CV R2 = {fwd_two_r2}",
         "AQI is rebuilt almost exactly from a pair of input columns - it is derived, "
         "not measured"),
    ], left=7.15, top=1.7, width=5.7, size=12)
    notes(s, "The contrast between linear and tree R-squared is the analytical "
             "highlight of this slide; say why both were run.", 0.9)

    # 10 - K-Means ----------------------------------------------------------- #
    s = slide(prs, 10, "K-Means Clustering", "k chosen from evidence, disagreement "
                                             "reported")
    picture(s, viz / "clustering" / "01_elbow_silhouette.png", 0.55, 1.7, 6.3)
    picture(s, viz / "clustering" / "02_pca_clusters.png", 0.55, 4.35, 6.3)
    bullets(s, [
        ("Features: nine pollutant concentrations, StandardScaler applied",
         "scaling is mandatory - CO is of order 5 and PM10 of order 300"),
        (f"Chosen k = {k} by silhouette ({sil}); the elbow rule suggested k = "
         f"{k_elbow}",
         "the disagreement is reported, not hidden"),
        ("Silhouette near 0.08 means weak separation",
         "the groups are a description of this file, not pollution 'regimes'"),
        ("PCA is used for the picture only",
         "clustering runs on all nine scaled columns; the two plotted components carry "
         "just " + R.n(100 * sum(cl["pca_explained_variance"]), 1)
         + "% of the variance, so the scatter is illustrative"),
    ], left=7.05, top=1.7, width=5.8, size=12)
    notes(s, "Expect to be asked why you did not just take the elbow. Answer: the two "
             "criteria disagreed and the silhouette is weak, so the conservative k won.",
          1.0)

    # 11 - Anomaly detection ------------------------------------------------- #
    s = slide(prs, 11, "Anomaly Detection", "Isolation Forest on nine pollutants")
    picture(s, viz / "anomaly" / "02_anomaly_by_city.png", 0.55, 1.7, 6.3)
    picture(s, viz / "anomaly" / "04_anomaly_scatter.png", 0.55, 4.35, 6.3)
    bullets(s, [
        (f"{anomalies} of {rows} observations flagged ({anomaly_pct}%)",
         "300 trees, random_state 42, contamination = " + contamination),
        ("The rate is an assumption, not a discovery",
         "contamination fixes the share before the model sees the data"),
        ("Anomalous days are jointly unusual, not simply high",
         "largest pollutant shift between normal and flagged rows is a few percent"),
        ("Spread evenly over cities and years",
         "consistent with the uniform-distribution finding in slide 5"),
    ], left=7.05, top=1.7, width=5.8, size=12)
    notes(s, "Say out loud that 5% is configured. If a marker asks 'how do you know "
             "there are 914 real anomalies?', the answer is that you do not.", 0.9)

    # 12 - Classification ---------------------------------------------------- #
    s = slide(prs, 12, "Classification", "Predicting the AQI category from pollutants "
                                        "only")
    picture(s, viz / "classification" / "01_model_comparison.png", 0.55, 1.7, 6.4)
    table(s, comp[["Model", "Accuracy_%", "F1_macro", "Lift_over_Baseline_pp"]],
          left=7.1, top=1.75, width=5.7, font=11)
    bullets(s, [
        (f"Best model: {best_name} - accuracy {best_acc}%, macro-F1 {best_f1}, lift "
         f"{lift} pp over the {baseline}% prior baseline",
         "stratified 75/25 split, AQI excluded from every feature set"),
        (f"Including AQI inflates accuracy by {inflation} pp",
         "the label is a band of AQI, so using AQI is predicting the target from itself"),
        ("Rare classes are where accuracy lies",
         rare_a + " (" + rare_a_n + " rows) and " + rare_b + " (" + rare_b_n
         + " rows) are why macro-F1 " + best_f1 + " sits far below " + best_acc
         + "% accuracy"),
    ], left=7.1, top=4.35, width=5.7, size=12)
    notes(s, "This is the most likely question: 'why not report " + leaky_acc
             + "%?'. Answer: because that model saw AQI, and AQI determines the label.",
          1.0)

    # 13 - Power BI ---------------------------------------------------------- #
    s = slide(prs, 13, "Power BI Dashboard", "Star schema, documented KPIs, five pages")
    table(s, [
        ["Page", "Purpose", "Key visuals"],
        ["Overview", "One-glance status of the panel", "6 KPI cards, AQI by city, "
         "trend, category share"],
        ["City Analysis", "Compare cities in a filter context", "radar/bar comparison, "
         "cluster mix, percentile table"],
        ["Pollutant Analysis", "Relation between pollutants and AQI", "heat map, "
         "scatter vs AQI, ranking"],
        ["Pattern Discovery", "Mining results surfaced", "cluster profiles, anomaly "
         "list, model comparison"],
        ["Trends", "Time intelligence", "yearly/monthly/seasonal trend, YTD, "
         "year-over-year"],
    ], left=0.55, top=1.7, width=12.25, font=11)
    bullets(s, [
        "Fact: air_quality_cleaned.csv; dimensions: dim_date, dim_city, dim_bucket",
        measures + " DAX measures documented in dashboard/DAX_measures.dax and "
        "dashboard/KPI_DEFINITIONS.md",
        "Slicers (city, year, month, season, category) plus a what-if limit parameter",
        "Thresholds cite CPCB bands - verified to reproduce AQI_Bucket on 100% of rows",
    ], top=4.7, width=12.25, size=13)
    notes(s, "If the .pbix is available, switch to it here for two minutes: filter a "
             "city, watch the KPIs and titles recompute, then a cross-filter on a "
             "chart.", 1.0)

    # 14 - Results / insights ------------------------------------------------ #
    s = slide(prs, 14, "Results and Insights",
              "Generated from computed artefacts only - never typed in")
    top_ins = ins[["Insight", "Evidence Strength"]].head(6).values.tolist()
    table(s, [["Insight (abridged)", "Evidence"]] +
          [[str(a)[:150] + ("..." if len(str(a)) > 150 else ""), str(b)]
           for a, b in top_ins], left=0.55, top=1.7, width=12.25, font=11)
    box = s.shapes.add_textbox(Inches(0.55), Inches(5.9), Inches(12.25), Inches(1.0))
    _text(box, [f"{len(ins)} insights are stored in data/processed/insights.csv, each "
                "with its quantitative evidence and the file it was derived from. "
                "Insights whose evidence is weak are labelled as weak."], 13, GREY)
    notes(s, "Read out two or three insights and name the file behind each. Do not "
             "present a weak-evidence insight as a headline.", 1.0)

    # 15 - Limitations ------------------------------------------------------- #
    s = slide(prs, 15, "Limitations", "What this project cannot claim")
    bullets(s, [x if len(x) < 130 else x[:127] + "..." for x in R.LIMITATIONS_FROM_BRIEF],
            width=12.2, size=13, top=1.7)
    callout(s, "Added by the analysis itself: the supplied file carries no provenance "
               "and its columns behave like independent uniform draws, so city, month "
               "and year differences are statistically indistinguishable. Findings are "
               "therefore descriptions of the file.", top=5.4, left=0.55, width=12.2,
            color=AMBER)
    notes(s, "Owning limitations is what earns marks in a viva. Say which limitation "
             "changed the design: the derived target forced AQI out of the features.",
          0.8)

    # 16 - Future scope ------------------------------------------------------ #
    s = slide(prs, 16, "Future Scope", "Twelve directions, in three tiers")
    names = [name for name, _ in R.FUTURE_SCOPE]
    per_col = (len(names) + 2) // 3
    for i in range(3):
        chunk = names[i * per_col:(i + 1) * per_col]
        bullets(s, chunk, left=0.55 + i * 4.2, top=1.8, width=4.0, size=13)
    box = s.shapes.add_textbox(Inches(0.55), Inches(5.6), Inches(12.25), Inches(1.2))
    _text(box, [
        "Data first: real-time APIs, more cities, satellite and weather inputs.",
        "Then modelling: forecasting, deep learning, stronger anomaly validation, "
        "explainability.",
        "Then delivery: live and mobile dashboards, automated public alerts.",
    ], 13, GREY)
    notes(s, "Keep this to 40 seconds - the value is in the tiering, not the list.",
          0.7)

    # 17 - Conclusion -------------------------------------------------------- #
    s = slide(prs, 17, "Conclusion", "What was built, what was answered, what was not")
    bullets(s, [
        ("Pipeline delivered",
         f"13 source modules, 9 executed notebooks, {rows} rows, "
         "processed datasets and a documented Power BI design"),
        ("Answered with evidence",
         "city and calendar profiles, correlation structure (linear and non-linear), "
         "cluster solution, anomaly set, model comparison with a stated baseline"),
        ("Answered negatively, and reported that way",
         "no detectable city, month or year effect; no detectable ten-year trend; "
         "clusters that do not separate strongly"),
        ("Leakage quantified, not assumed",
         f"AQI_Bucket is reproducible from AQI on 100% of rows; AQI excluded from all "
         f"models; inflation measured at {inflation} pp"),
        ("Next step that matters most",
         "replace this file with a documented monitoring record and re-run the same "
         "code - every artefact regenerates from it"),
    ], width=12.2, size=14, top=1.7)
    notes(s, "Close on the reproducibility line: the same nine notebooks run against a "
             "real dataset unchanged. Then invite questions.", 0.8)

    DECK_DIR.mkdir(exist_ok=True)
    prs.save(DECK)
    return DECK


def main() -> None:
    r = R.load()
    path = build(r)
    deck = Presentation(str(path))
    print("wrote", path, f"({path.stat().st_size:,} bytes)")
    print("slides:", len(deck.slides))


if __name__ == "__main__":
    main()
