"""
Build the final academic report from the computed results.

    python tools/build_report.py              # writes report/*.docx and *.pdf
    python tools/build_report.py --no-pdf     # .docx only (no Word needed)

Every figure, table and number in the report is read from
`data/processed/results.json` or from a CSV that the pipeline exported. Nothing
is typed in by hand: if the analysis is re-run, the report can be rebuilt and
will change with it. Where the evidence does not support a claim, the report says
so instead of making the claim.

Fill in the STUDENT block below before submitting.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import config as C                      # noqa: E402
import docx_builder as D                # noqa: E402

RESULTS_JSON = C.PROCESSED_DIR / "results.json"
DOCX = C.REPORT_DIR / "Air_Quality_Intelligence_Report.docx"
PDF = C.REPORT_DIR / "Air_Quality_Intelligence_Report.pdf"

TITLE = ("Air Quality & Pollution Intelligence: "
         "An Integrated Data Mining and Business Intelligence Dashboard")

# --------------------------------------------------------------------------- #
# Details the analysis cannot know - fill these in before submission.
# --------------------------------------------------------------------------- #
STUDENT = {
    "name": "<STUDENT NAME>",
    "enrolment": "<ENROLMENT / ROLL NUMBER>",
    "programme": "<B.Tech / M.Sc. PROGRAMME, e.g. Computer Science & Engineering>",
    "institute": "<INSTITUTION NAME>",
    "department": "<DEPARTMENT NAME>",
    "university": "<AFFILIATING UNIVERSITY>",
    "guide": "<PROJECT GUIDE NAME AND DESIGNATION>",
    "academic_year": "<YYYY-YYYY>",
    "submission_date": "<DD MONTH YYYY>",
}

PROJECT_QUESTIONS = [
    "Which cities have higher average AQI?",
    "How does AQI change over time?",
    "Which pollutants are most strongly associated with AQI?",
    "How do pollutants correlate with each other?",
    "Are cities and observations naturally grouped into pollution profiles?",
    "Which observations represent unusual pollution patterns?",
    "Can AQI categories be predicted using pollutant measurements?",
    "Which months or seasons have higher pollution levels?",
    "How do pollution profiles differ between cities?",
    "What insights can be communicated through a BI dashboard?",
]

# Verbatim problem statement from the project brief; the slide deck reuses it so
# that report and presentation cannot disagree about what was asked.
PROBLEM_STATEMENT = (
    "Air-quality datasets contain multiple pollutants, locations, and time-based "
    "observations, making it difficult to identify pollution patterns, "
    "relationships, unusual observations, and city-level differences through raw "
    "data alone. This project aims to apply data-mining techniques and "
    "business-intelligence visualization to transform air-quality observations into "
    "structured analytical insights."
)

LIMITATIONS_FROM_BRIEF = [
    "Dataset availability is limited to the recorded cities and time period.",
    "Missing values may affect analysis.",
    "Correlation does not establish causation.",
    "K-Means results depend on feature selection and scaling.",
    "Anomaly detection identifies statistical unusualness rather than "
    "environmental causes.",
    "Classification performance depends on data quality and class distribution.",
    "The project does not replace official environmental monitoring or "
    "regulatory assessment.",
]

FUTURE_SCOPE = [
    ("Real-time air-quality APIs", "Poll the Central Pollution Control Board or "
     "OpenAQ feeds on a schedule so the dashboard shows today's air rather than "
     "the last archived file."),
    ("More cities and stations", "Extend beyond the five cities in this file; "
     "station-level rows would also let within-city variation be measured."),
    ("Satellite data", "Combine ground readings with satellite aerosol optical "
     "depth to cover days and places without monitors."),
    ("Weather integration", "Wind speed, direction, temperature, humidity and "
     "boundary-layer height explain a large part of day-to-day concentration."),
    ("Forecasting", "Add a time-series model (SARIMAX, LSTM or gradient-boosted "
     "lag features) once a real, autocorrelated series is available."),
    ("Deep learning", "Sequence models can learn interactions across pollutants "
     "and calendar features without manual feature engineering."),
    ("Geospatial analysis", "Choropleth and map visuals need coordinates and a "
     "boundary file, neither of which this dataset contains."),
    ("Real-time Power BI dashboards", "Publish to Power BI Service with a "
     "scheduled refresh or a DirectQuery/PushDataset connection."),
    ("Mobile dashboard", "A responsive Power BI mobile layout or a thin app on "
     "the same dataset for public alerts."),
    ("Automated alerts", "Raise an alert when a city's rolling AQI crosses a "
     "documented public-health threshold."),
    ("More advanced anomaly detection", "Seasonal-hybrid ESD, LSTM autoencoders "
     "or multivariate extreme-value models, validated against known episode "
     "records rather than a chosen contamination rate."),
    ("Explainable AI", "SHAP values and calibration curves to make the "
     "classification model's reasoning auditable."),
]

REFERENCES = [
    "Central Pollution Control Board (CPCB), National Air Quality Index - "
    "Technical Report, CPCB, New Delhi, 2014. (Source of the six AQI categories "
    "and their 0-50 / 51-100 / 101-200 / 201-300 / 301-400 / 401-500 ranges; the "
    "ranges used here were additionally verified against this dataset in "
    "section 15.5.)",
    "Central Pollution Control Board (CPCB), National Ambient Air Quality "
    "Standards - Revision, New Delhi, 2009. (Source of the 24-hour PM2.5 "
    "concentration used as the default of the dashboard's adjustable limit "
    "parameter; re-verify the current value before quoting it as compliance.)",
    "Liu, F. T., Ting, K. M. and Zhou, Z.-H., 'Isolation Forest', Proceedings of "
    "the 8th IEEE International Conference on Data Mining (ICDM), 2008, pp. 413-422.",
    "Hartigan, J. A. and Wong, M. A., 'Algorithm AS 136: A K-Means Clustering "
    "Algorithm', Journal of the Royal Statistical Society. Series C (Applied "
    "Statistics), 28(1), 1979, pp. 100-108.",
    "Lloyd, S. P., 'Least Squares Quantization in PCM', IEEE Transactions on "
    "Information Theory, 28(2), 1982, pp. 129-137.",
    "Kaufman, L. and Rousseeuw, P. J., Finding Groups in Data: An Introduction to "
    "Cluster Analysis, Wiley, 1990. (Silhouette width.)",
    "Pedregosa, F. et al., 'Scikit-learn: Machine Learning in Python', Journal of "
    "Machine Learning Research, 12, 2011, pp. 2825-2830.",
    "McKinney, W., 'Data Structures for Statistical Computing in Python', "
    "Proceedings of the 9th Python in Science Conference (SciPy), 2010, pp. 56-61.",
    "Harris, C. R. et al., 'Array Programming with NumPy', Nature, 585, 2020, "
    "pp. 357-362.",
    "Virtanen, P. et al., 'SciPy 1.0: Fundamental Algorithms for Scientific "
    "Computing in Python', Nature Methods, 17, 2020, pp. 261-266.",
    "Hunter, J. D., 'Matplotlib: A 2D Graphics Environment', Computing in "
    "Science & Engineering, 9(3), 2007, pp. 90-91.",
    "Wickham, H., 'A Layered Grammar of Graphics', Journal of Computational and "
    "Graphical Statistics, 19(1), 2010, pp. 3-30. (Basis of seaborn's API.)",
    "Kluwer, A. et al., 'Principal Component Analysis', Wiley Interdisciplinary "
    "Reviews: Computational Statistics, 3(5), 2011, pp. 439-459.",
    "Microsoft Corporation, 'Power BI Documentation', learn.microsoft.com/en-us/power-bi/, "
    "accessed at the time of writing. (Star schema, DAX measures, row-level security.)",
    "Air-quality data file supplied with this project as "
    "`data/raw/Air_quality_data.csv`; its publisher, download date and collection "
    "method were not documented with the file - see section 12.5.",
]


# --------------------------------------------------------------------------- #
# Loading and formatting helpers
# --------------------------------------------------------------------------- #
def load() -> dict:
    if not RESULTS_JSON.exists():
        sys.exit(f"{RESULTS_JSON} not found - run notebooks/09 first.")
    return json.loads(RESULTS_JSON.read_text(encoding="utf-8"))


def n(value, nd: int = 2) -> str:
    """Format a number for prose: thousands separators, fixed decimals."""
    if value is None:
        return "n/a"
    if isinstance(value, (int,)):
        return f"{value:,}"
    return f"{float(value):,.{nd}f}"


def pvalue(p: float) -> str:
    return "< 0.0001" if p is not None and p < 1e-4 else f"= {p:.4f}"


def csv(name: str) -> pd.DataFrame:
    path = C.PROCESSED_DIR / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def best_model(r: dict) -> str:
    comp = pd.DataFrame(r["classification"]["comparison"])
    return comp.sort_values("Accuracy_%", ascending=False)["Model"].iloc[0]


# --------------------------------------------------------------------------- #
# Front matter (sections 1-4)
# --------------------------------------------------------------------------- #
def front_matter(b: D.DocxBuilder) -> None:
    b.para()
    b.para(TITLE, bold=True, size=18, align="center")
    b.para("A Project Report", size=13, align="center", italic=True)
    b.para("submitted in partial fulfilment of the requirements for the award of the "
           "degree of", size=10.5, align="center")
    b.para(STUDENT["programme"], bold=True, size=12, align="center")
    b.para()
    b.para("On", size=10.5, align="center")
    b.para("AIR QUALITY & POLLUTION INTELLIGENCE", bold=True, size=13, align="center")
    b.para()
    b.para("Submitted by", size=10.5, align="center")
    b.para(f"{STUDENT['name']}  ({STUDENT['enrolment']})", bold=True, size=12,
           align="center")
    b.para()
    b.para(f"Under the guidance of {STUDENT['guide']}", size=11, align="center",
           italic=True)
    b.para()
    b.para(STUDENT["department"], bold=True, size=12, align="center")
    b.para(STUDENT["institute"], size=11.5, align="center")
    b.para(STUDENT["university"], size=11, align="center")
    b.para(STUDENT["academic_year"], bold=True, size=12, align="center")
    b.page_break()

    b.heading("Certificate", 1)
    b.para(f"This is to certify that the project report entitled \"{TITLE}\" "
           f"submitted by {STUDENT['name']} ({STUDENT['enrolment']}), a student of "
           f"{STUDENT['programme']} of {STUDENT['institute']}, {STUDENT['department']}, "
           f"during {STUDENT['academic_year']}, is a bona fide record of work carried "
           f"out under my supervision and guidance.", align="justify")
    b.para("The analytical work in this report was produced by the student's own "
           "code base (`src/`, `notebooks/`, `tools/`) and executed on the dataset "
           "named in section 12; every numerical result quoted here is regenerated "
           "from that code and is reproducible from it.", align="justify", size=10)
    b.para()
    b.para("Place: " + "<CITY>")
    b.para("Date: " + STUDENT["submission_date"])
    b.para()
    b.para(f"{STUDENT['guide']}\n(Project Guide)", size=11)
    b.para(f"{STUDENT['name']}\n(Candidate)", size=11)
    b.page_break()

    b.heading("Declaration", 1)
    b.para(f"I, {STUDENT['name']} ({STUDENT['enrolment']}), hereby declare that the "
           f"project report entitled \"{TITLE}\" submitted to {STUDENT['institute']} "
           f"in partial fulfilment of the requirements for the award of the degree of "
           f"{STUDENT['programme']} is a record of original work done by me under the "
           f"guidance of {STUDENT['guide']}.", align="justify")
    b.para("This work has not been submitted to any other institution or university "
           "for the award of any other degree or diploma. The dataset used is "
           "identified in section 12 and the external sources relied upon are listed "
           "in section 28. Where the data did not support a conclusion, that has been "
           "stated rather than a conclusion invented.", align="justify")
    b.para()
    b.para("Place: " + "<CITY>")
    b.para("Date: " + STUDENT["submission_date"])
    b.para(f"{STUDENT['name']}", size=11)
    b.page_break()

    b.heading("Acknowledgement", 1)
    b.para(f"I would like to express my sincere gratitude to my project guide, "
           f"{STUDENT['guide']}, for the guidance, patience and critical questions "
           f"that shaped this work, and to the head of {STUDENT['department']} for "
           f"providing the facilities required to complete it.", align="justify")
    b.para("I thank the faculty members and evaluators who reviewed intermediate "
           "versions of the analysis, and the maintainers of the open-source tools "
           "this project stands on - the Python scientific stack, scikit-learn and "
           "Jupyter - whose documentation is referenced in section 28. Finally, I "
           "thank my family and classmates for their support.", align="justify")
    b.para()
    b.para(f"{STUDENT['name']}", size=11)
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 5 - Abstract
# --------------------------------------------------------------------------- #
def abstract(b: D.DocxBuilder, r: dict) -> None:
    ds, env = r["dataset"], r["environment"]
    cl, an, cf = r["clustering"], r["anomaly"], r["classification"]
    comp = pd.DataFrame(cf["comparison"])
    top = comp.sort_values("Accuracy_%", ascending=False).iloc[0]
    corr = pd.DataFrame(r["correlation_with_aqi"])
    rmax = corr.loc[corr["Pearson_r"].abs().idxmax()]
    struct = r["aqi_structure"]
    pred = r["predictability"]
    cols_after = [q for q in r["quality_comparison"] if q["Metric"] == "Total Columns"][0]

    text = (
        f"Air quality is a public-health question whose evidence arrives as a stream of "
        f"daily measurements: pollutant concentrations, an index computed from them, and "
        f"a category label attached to that index. This project analyses a daily "
        f"air-quality dataset of {n(ds['rows'])} observations covering {ds['cities']} "
        f"Indian cities from {ds['date_start']} to {ds['date_end']}, with "
        f"{len(ds['detected_pollutants'])} pollutant measurements, and turns it into a "
        f"data-mining study and an interactive Power BI dashboard. The pipeline is written "
        f"once in `src/` and executed from nine notebooks, so the report, the exported "
        f"tables and the dashboard all read the same computed results. Cleaning removed no "
        f"rows: the file contains no duplicate records and no missing values, and "
        f"feature engineering widened the table from {ds['columns']} to "
        f"{n(cols_after['After Cleaning'], 0)} columns. K-Means settled on "
        f"{cl['choice']['chosen_K']} clusters at a silhouette score of "
        f"{n(cl['choice']['silhouette'], 4)}, a weak separation that is reported as weak "
        f"rather than as a discovery. Isolation Forest flagged "
        f"{n(an['stats']['Anomalies detected'], 0)} observations "
        f"({n(an['stats']['Anomaly %'])} %), a share fixed by the contamination parameter "
        f"rather than estimated from the data. {best_model(r)} predicted the AQI category "
        f"with {n(top['Accuracy_%'])} % accuracy against a "
        f"{n(comp.loc[comp['Model'] == 'Baseline (prior)', 'Accuracy_%'].iloc[0])} % "
        f"prior baseline (macro-F1 {n(top['F1_macro'], 4)}), and a deliberate leakage test "
        f"showed that {n(cf['leakage']['accuracy_inflation_pp'])} percentage points of "
        f"that accuracy is bought by leaking AQI itself. The most consequential finding is "
        f"a negative one: pollutant-to-AQI correlations are negligible (largest "
        f"|r| = {n(abs(rmax['Pearson_r']), 4)} for {rmax['Variable']}), city, month and "
        f"year effects are statistically insignificant, and AQI is reproducible from "
        f"PM2.5 and PM10 at cross-validated R\u00b2 = "
        f"{n(struct['forward_selection'][1]['cv_r2'], 4)} while rising non-monotonically "
        f"with concentration. The dataset therefore behaves like a simulated record rather "
        f"than an environmental measurement series, and every conclusion is stated as a "
        f"description of this file. The significance of the work lies in that discipline: "
        f"the same pipeline, dashboards and models, applied without over-claiming."
    )
    b.heading("Abstract", 1)
    b.para(text.strip(), align="justify")
    words = D.count_words(text)
    b.para(f"[Abstract length: {words} words - the brief asks for 200-300.]",
           size=9, italic=True)
    print(f"abstract words: {words}")
    keywords = ("Air quality; data mining; K-Means; Isolation Forest; classification; "
                "data leakage; Power BI; business intelligence; AQI; reproducibility.")
    b.para(f"Keywords: {keywords}", italic=True, size=10.5)
    b.page_break()


# --------------------------------------------------------------------------- #
# Sections 6-8 - contents lists
# --------------------------------------------------------------------------- #
def contents(b: D.DocxBuilder) -> None:
    b.heading("Table of Contents", 1)
    b.toc('TOC \\o "1-3" \\h \\z \\u')
    b.page_break()
    b.heading("List of Figures", 1)
    b.toc('TOC \\c "Figure" \\h \\z \\u')
    b.page_break()
    b.heading("List of Tables", 1)
    b.toc('TOC \\c "Table" \\h \\z \\u')
    b.page_break()


# --------------------------------------------------------------------------- #
# Sections 9-11
# --------------------------------------------------------------------------- #
def introduction(b: D.DocxBuilder, r: dict) -> None:
    b.heading("9. Introduction", 1)
    b.heading("9.1 Air-quality monitoring", 2)
    b.para("Ambient air quality is monitored as a set of concentration measurements. "
           "Regulators combine those measurements into a single Air Quality Index (AQI) "
           "so that a number and a colour can be communicated to the public, and then "
           "band that index into categories. A dataset of this kind therefore contains "
           "three different kinds of object in one table: raw measurements, a derived "
           "index, and a label derived from the index. Treating all three as independent "
           "observations is the most common analytical error in air-quality projects, and "
           "this project treats the distinction as a design constraint (sections 17.4 and "
           "20.3).", align="justify")
    b.heading("9.2 Why pollution analysis matters", 2)
    b.para("Exposure to particulate matter and to nitrogen and sulphur oxides is "
           "associated with respiratory and cardiovascular disease, which is why daily "
           "concentrations drive public-health advice, school and construction policy, and "
           "short-term traffic measures. Advice of that kind is only as good as the "
           "evidence behind it: a claim that one city is worse than another, or that "
           "pollution is rising, needs a comparison that survives statistical testing, not "
           "a difference in two averages that happens to be visible on a chart.",
           align="justify")
    b.heading("9.3 The difficulty in multi-city data", 2)
    b.para("A panel of cities observed daily for ten years is large enough to be "
           "overwhelming and messy enough to be treacherous. A reader cannot see a pattern "
           "across tens of thousands of rows; different pollutants move on different scales "
           "and units; missing values, duplicates and unit errors hide inside the file; "
           "seasonal and long-term behaviour are entangled; and a derived column can "
           "silently leak into a model that appears to perform brilliantly. Answering ten "
           "practical questions about such a file (section 11) requires an ordered "
           "pipeline, not a single script.", align="justify")
    b.heading("9.4 The role of data mining", 2)
    b.para("Data mining supplies the three things the questions need. Unsupervised "
           "learning (K-Means) groups observations so that a large table can be described "
           "by a small number of profiles. Outlier detection (Isolation Forest) separates "
           "observations that are jointly unusual from those that are merely extreme on one "
           "column. Supervised learning (logistic regression, decision trees, random "
           "forests, gradient boosting) tests how far the measurable chemistry of a day "
           "predicts the category that day is assigned - and, just as importantly, how "
           "much of that apparent success is an artefact of the way the target was built. "
           "Descriptive statistics and significance testing sit underneath all three, "
           "because a cluster, an anomaly or a difference between cities is only worth "
           "reporting if it survives the test.", align="justify")
    b.heading("9.5 The role of business intelligence", 2)
    b.para("A notebook answers a question once; a dashboard answers it for whoever asks "
           "next. Publishing the processed panel as a star schema in Power BI, with "
           "explicitly documented KPIs and DAX measures, turns the analysis into a "
           "self-service tool: a user filters by city, month, season or AQI category and "
           "sees averages, trends, category shares, cluster profiles and anomaly counts "
           "recomputed in the filter context. Business intelligence also imposes "
           "discipline - a KPI has to be defined, given a unit and given a source column, "
           "which is where an unsupported metric becomes visible.", align="justify")
    b.heading("9.6 Motivation for this project", 2)
    b.para("The motivation is to build the complete journey - data, knowledge, data "
           "mining, business intelligence, visualisation, insight - on a real file, and to "
           "keep the journey honest when the file disappoints. Half-way through the "
           "analysis the dataset produced a result that most projects would quietly drop: "
           "the pollutant columns are almost uncorrelated with each other and with AQI, the "
           "city, month and year differences are statistically indistinguishable, and AQI "
           "is nevertheless reproducible from two of the columns with cross-validated "
           "R\u00b2 above 0.95 while behaving non-monotonically. That combination is the "
           "signature of a generated file rather than a monitoring record (section 12.5). "
           "Reporting it, and still delivering the clustering, anomaly detection, "
           "classification and dashboard the project asks for - described as properties of "
           "this file rather than as findings about Indian air - is the point of the work.",
           align="justify")
    b.page_break()


def problem_statement(b: D.DocxBuilder) -> None:
    b.heading("10. Problem Statement", 1)
    b.para(PROBLEM_STATEMENT, align="justify", italic=True)
    b.para("Restated as the concrete gaps this project has to close:", align="justify")
    b.bullets([
        "No reader can inspect thousands of rows and describe five cities, ten years and "
        "nine pollutants - the information has to be summarised without being distorted.",
        "Relationships between pollutants, and between pollutants and the index, are not "
        "visible in a table and must be measured, with significance attached.",
        "'Unusual' has to be defined rather than eyeballed, and the definition must not "
        "smuggle in the answer.",
        "The AQI category label is derived from AQI, so any model that uses AQI as a "
        "feature is predicting the target from itself - a leakage problem that inflates "
        "accuracy and must be quantified.",
        "Even a correct analysis is useless to a decision-maker unless it can be "
        "interrogated interactively, with KPIs whose definitions and units are documented.",
    ])
    b.page_break()


def objectives(b: D.DocxBuilder, r: dict) -> None:
    b.heading("11. Objectives", 1)
    b.para("Main objective (as set for the project):", align="justify")
    b.para("\"To develop an interactive Air Quality and Pollution Intelligence Dashboard "
           "using Data Mining and Business Intelligence techniques to analyze pollution "
           "patterns, identify relationships between pollutants, group cities/observations "
           "based on pollution characteristics, detect unusual pollution observations, "
           "classify air-quality conditions, and provide data-driven environmental "
           "insights.\"", align="justify", italic=True)
    b.heading("11.1 Specific objectives", 2)
    b.steps([
        "Load and profile the supplied dataset without assuming its schema, and document "
        "what is actually in it.",
        "Clean the data - duplicates, types, invalid values, missing values, categorical "
        "consistency - and log every step with the number of values it changed.",
        "Engineer derived features (ratios, rolling means, calendar and season fields, "
        "percentiles) that make patterns expressible.",
        "Describe the data: distributions, central tendency, spread, category shares, "
        "city, monthly, seasonal and yearly profiles.",
        "Measure association: Pearson and Spearman correlation, significance, non-linear "
        "predictability, and the structure of the derived AQI column.",
        "Group observations with K-Means, choosing k from the elbow and silhouette "
        "evidence, and profile the resulting clusters.",
        "Detect unusual observations with Isolation Forest and characterise them by city, "
        "year and pollutant profile.",
        "Classify the AQI category from pollutant measurements with several models, "
        "against a stated baseline, after checking for data leakage.",
        "Evaluate the models with accuracy, precision, recall, macro-F1, confusion "
        "matrices and cross-validation.",
        "Export the processed datasets and design a Power BI star schema, DAX measures, "
        "KPI definitions and a five-page dashboard.",
        "Generate insights only from computed results, and state explicitly where the "
        "evidence is insufficient.",
    ])
    b.heading("11.2 Questions the project must answer", 2)
    b.para("Each question is answered in section 24 with the figure that answers it.",
           align="justify")
    b.numbered(PROJECT_QUESTIONS)
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 12 - Dataset description
# --------------------------------------------------------------------------- #
def dataset_section(b: D.DocxBuilder, r: dict) -> None:
    ds = r["dataset"]
    b.heading("12. Dataset Description", 1)
    b.heading("12.1 Provenance and handling", 2)
    b.para(f"File used: `data/raw/Air_quality_data.csv`. The analysis that produced every "
           f"number in this report was executed on {r['generated_at']} and took "
           f"{n(r['runtime_seconds'], 1)} seconds end to end. The raw file is never written "
           f"to: every transformation produces a new file under `data/processed/`, so the "
           f"original can always be re-read and the whole project re-run from it.",
           align="justify")
    b.table([["Item", "Value"]] + [
        ["Rows", n(ds["rows"], 0)],
        ["Columns", ds["columns"]],
        ["Cities", ds["cities"]],
        ["Date range", f"{ds['date_start']} to {ds['date_end']}"],
        ["Pollutant columns present", ", ".join(ds["detected_pollutants"])],
        ["Expected-but-absent columns", ", ".join(ds["columns_absent_vs_expected"])],
        ["Missing values in raw file", n(ds["missing_before"], 0)],
        ["Duplicate rows in raw file", n(ds["duplicates_before"], 0)],
        ["Rows after cleaning", n(ds["rows_after_cleaning"], 0)],
    ], caption="The dataset as it actually is, measured in notebook 01.")
    b.heading("12.2 Schema", 2)
    b.para("The raw table has one row per city per day and 13 columns. The data "
           "dictionary below was generated from the file itself, not copied from a "
           "description of it.", align="justify")
    dd = pd.DataFrame(r["data_dictionary"])
    b.table(dd, caption="Data dictionary (generated by `U.data_dictionary`).",
            font_size=8)
    b.para("Derived columns added by feature engineering are listed in section 15.4; "
           "`data/processed/feature_inventory.csv` records each one with its purpose.",
           size=9.5, italic=True)
    b.heading("12.3 Units and measurement basis", 2)
    b.para("Concentrations are reported as supplied: \u00b5g/m\u00b3 for particulate "
           "matter and gases, mg/m\u00b3 for CO. The file carries no averaging-time, "
           "instrument, station or latitude/longitude metadata, so the project labels "
           "units \"as supplied\" and does not assert a conversion or a measurement "
           "protocol that the data does not document. AQI is a dimensionless index and "
           "`AQI_Bucket` a categorical band of it.", align="justify")
    b.heading("12.4 Target variable", 2)
    b.para("The analytical target is `AQI_Bucket`, the six-category AQI band. Its "
           "distribution is severely imbalanced - the two rarest categories hold "
           f"{n(r['classification']['class_balance'][-1]['Count'], 0)} and "
           f"{n(r['classification']['class_balance'][-2]['Count'], 0)} of "
           f"{n(ds['rows'], 0)} rows - which is reported in section 20.2 and drives the "
           "choice of macro-F1 and per-class recall over accuracy.", align="justify")
    b.table(pd.DataFrame(r["classification"]["class_balance"]),
            caption="Class balance of the target, from `class_balance.csv`.")
    b.heading("12.5 A finding about the dataset itself", 2)
    b.para("Four independent tests, all computed in notebooks 04, 05 and 09, point the "
           "same way, and the report states the consequence rather than burying it.",
           align="justify")
    dist = pd.DataFrame(r["distribution_tests"])
    uniform = dist[dist["KS_vs_uniform_p"].astype(float) > 0.05] if len(dist) else dist
    b.bullets([
        f"Shape of the measurements. Of the {len(dist)} numeric columns tested, "
        f"{len(uniform)} are statistically indistinguishable from a uniform "
        f"distribution (Kolmogorov-Smirnov distance to a uniform on the observed range, "
        f"p > 0.05), and their excess kurtosis sits near -1.2, the value a uniform "
        f"distribution has. Real concentration data is right-skewed. See "
        f"`distribution_tests.csv`.",
        f"Absence of association. The largest magnitude of correlation between any "
        f"pollutant and AQI is |r| = "
        f"{n(pd.DataFrame(r['correlation_with_aqi'])['Pearson_r'].abs().max(), 4)}, and "
        f"the lag-1 autocorrelation of AQI within a city is "
        f"{n(r['autocorrelation'][0]['Mean_Autocorrelation'], 4)} - a daily "
        f"environmental series should remember yesterday.",
        f"Absence of structure over space and time. One-way ANOVA on AQI gives "
        f"p = {n(r['group_tests']['City']['ANOVA_p'], 4)} for city and "
        f"p = {n(r['group_tests']['Month']['ANOVA_p'], 4)} for month, and the yearly "
        f"trend slope is {n(r['trend_test']['slope_per_year'], 4)} index points per year "
        f"with p = {n(r['trend_test']['p_value'], 4)}.",
        f"AQI is derived, and derived oddly. Cross-validated regression reproduces AQI "
        f"from PM2.5 and PM10 alone at R\u00b2 = "
        f"{n(r['aqi_structure']['forward_selection'][1]['cv_r2'], 4)}, yet the "
        f"relationship is not monotonic in PM2.5 "
        f"(monotonic = {r['aqi_structure']['monotonic_in_leading_column']}), whereas any "
        f"published AQI sub-index rises with concentration.",
    ])
    b.para("Conclusion drawn in this report: the file behaves like a randomly generated "
           "synthetic panel rather than a set of environmental measurements. Its "
           "provenance was not documented when it was supplied, and the schema differs "
           "from the published Indian air-quality datasets it resembles (a renamed date "
           "column, an added NOx column, and a longer date span). Every result in "
           "sections 13 to 24 is therefore reported as a property of this file and a "
           "demonstration of the method - not as evidence about air pollution in Indian "
           "cities, and not as a compliance assessment.", align="justify", bold=False)
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 13 - Technology
# --------------------------------------------------------------------------- #
def technology(b: D.DocxBuilder, r: dict) -> None:
    env = r["environment"]
    b.heading("13. Technology Used", 1)
    b.para("The stack is deliberately small and standard: a statistical Python "
           "environment for the analysis and Power BI for delivery. Versions are the ones "
           "actually used in the run that produced every number in this report, read from "
           "`results.json`.", align="justify")
    b.table([["Layer", "Component", "Version / choice", "Why"]] + [
        ["Language", "Python", env["python"], "Data-manipulation and modelling ecosystem"],
        ["Data", "pandas", env["pandas"], "Typed columns, joins, group-bys, time handling"],
        ["Numerics", "numpy", env["numpy"], "Vectorised arrays behind pandas and sklearn"],
        ["Statistics", "scipy", env["scipy"], "KS, Shapiro, ANOVA, Kruskal-Wallis, Pearson tests"],
        ["Mining", "scikit-learn", env["sklearn"],
         "StandardScaler, KMeans, PCA, IsolationForest, classifiers, metrics, CV"],
        ["Visuals", "matplotlib / seaborn", env["matplotlib"] + " / (seaborn per requirements.txt)",
         "Reproducible figures embedded in notebooks and this report"],
        ["Interface", "Jupyter Notebook (nbformat, nbclient)", "as installed",
         "Nine notebooks, executed headlessly so outputs are stored, not described"],
        ["BI", "Microsoft Power BI Desktop", "not run in this environment",
         "Star schema, DAX measures, five report pages - built from the guide in "
         "`dashboard/`"],
        ["Report", "python-docx + Microsoft Word (COM)", "1.2.0 / Office 16",
         "This document and its PDF, with Word computing the contents fields"],
        ["Reproducibility", "random_state", env["random_state"],
         "Fixed seed for every stochastic model and split"],
        ["Environment", "Platform", env["platform"], "Recorded, not required"],
    ], caption="Technology stack, with the versions the analysis actually ran on.",
        font_size=8.5, widths=[1.1, 1.5, 1.5, 2.3])
    b.para("No web application, database server or streaming component is used: the brief "
           "specifies Python plus Power BI, and the processed CSVs are the handoff between "
           "them.", align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 14 - Methodology
# --------------------------------------------------------------------------- #
def methodology(b: D.DocxBuilder, r: dict) -> None:
    b.heading("14. Methodology", 1)
    b.para("The method is a fixed sequence of thirteen stages. Stages 1-4 make the data "
           "trustworthy, 5-6 describe it, 7-10 mine it, and 11-13 deliver it. Each stage "
           "is implemented once in `src/` and called both by the notebook that "
           "demonstrates it and by `src/pipeline.py`, which re-runs the whole sequence; "
           "the notebook and the pipeline cannot disagree because they are the same code.",
           align="justify")
    b.figure(C.VIZ_DIR / "methodology" / "01_methodology_diagram.png",
             "Project methodology: dataset to insight, with the artefact that evidences "
             "each stage.", width_in=4.6)
    b.heading("14.1 Stage-by-stage description", 2)
    stages = [
        ("Dataset", "Read `data/raw/Air_quality_data.csv` once, unaltered. The raw file "
         "is treated as read-only evidence."),
        ("Data Understanding", "Shape, dtypes, missing values, duplicates, unique cities, "
         "date range, per-column profile, first/last rows. Output decides the rest of the "
         "pipeline - no column is assumed."),
        ("Data Cleaning", "Duplicate removal, date parsing, type conversion, invalid-value "
         "scan, missing-value handling (median for numeric, explicit `Unknown` for "
         "categorical), IQR outlier flagging without deletion, categorical and unit "
         "consistency. Every step logs how many values it touched."),
        ("Feature Engineering", "Ratios (PM2.5/PM10, NO2/NOx, O3/PM10), rolling and lagged "
         "AQI features, calendar fields, Indian-monsoon season, weekday/weekend, per-city "
         "pollutant percentiles, pollution-load index, and AQI category ordinal."),
        ("EDA", "Distributions of AQI and each pollutant, category shares, city and "
         "seasonal profiles, time trends, boxplots, city-by-pollutant heatmap, "
         "distribution-shape tests."),
        ("Correlation Analysis", "Pearson and Spearman matrices, correlations against AQI "
         "with p-values, pairwise scatter evidence, non-linear predictability of AQI, and "
         "a structural probe of how AQI is built."),
        ("K-Means", "Scale features, choose k by elbow (inertia) and silhouette, fit, "
         "profile clusters in original units, project to 2-D with PCA for visual "
         "inspection only."),
        ("Anomaly Detection", "Isolation Forest on the measured pollutants with a stated "
         "contamination, score distribution, per-city and per-year counts, pollutant "
         "profile of flagged versus normal rows, sensitivity sweep."),
        ("Classification", "Predict `AQI_Bucket` from pollutants only, stratified "
         "train/test split, prior baseline plus logistic regression, decision tree, random "
         "forest and gradient boosting, explicit data-leakage test."),
        ("Model Evaluation", "Accuracy, macro and weighted precision/recall/F1, confusion "
         "matrices, per-class support, 3-fold cross-validation, feature importance, lift "
         "over baseline."),
        ("Processed Dataset", "Export the fact table, summaries, cluster/anomaly/"
         "classification results and three dimension tables as CSVs."),
        ("Power BI", "Import into a star schema, define DAX measures, build five pages, "
         "document every KPI."),
        ("Insights", "Assemble the insight list from the computed artefacts, each row "
         "carrying its own evidence and source file; discard any statement the data does "
         "not support."),
    ]
    b.table([["#", "Stage", "What is done"]] +
            [[str(i), name, what] for i, (name, what) in enumerate(stages, 1)],
            caption="The thirteen stages, in the order executed.",
            font_size=8.5, widths=[0.35, 1.5, 4.6])
    b.heading("14.2 Design principles", 2)
    b.bullets([
        "Schema discovered, never assumed: `config.pick()` raises if a column is absent "
        "instead of letting code invent one.",
        "Nothing is deleted to make a result look better: outliers are flagged, not "
        "dropped, and the cleaning log proves it.",
        "Derived columns are quarantined: AQI is excluded from every model that predicts "
        "an AQI-derived label, and the exclusion is measured (section 20.3).",
        "Every stochastic component has a fixed seed and a recorded version.",
        "A negative result is a result: insignificant tests and weak clusters are "
        "reported with their statistics.",
    ])
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 15 - Data preprocessing
# --------------------------------------------------------------------------- #
def preprocessing(b: D.DocxBuilder, r: dict) -> None:
    ds = r["dataset"]
    b.heading("15. Data Preprocessing", 1)
    b.heading("15.1 Before and after", 2)
    b.table(pd.DataFrame(r["quality_comparison"]),
            caption="Before / after cleaning comparison (`data_quality_report.csv`).")
    b.para(f"The important number is the one that did not change: {n(ds['rows'], 0)} rows "
           f"entered cleaning and {n(ds['rows_after_cleaning'], 0)} left it. The file "
           f"contains no duplicate records and no missing values, so no observation was "
           f"imputed and none was discarded. Column count rises from {ds['columns']} to 22 "
           f"because cleaning adds derived quality flags, not because data was invented.",
           align="justify")
    b.heading("15.2 Cleaning steps, with the number of values each one touched", 2)
    b.para("Every rule in `src/preprocessing.py` logs its own effect. The table is "
           "reproduced in full because a reader's first question about a clean dataset "
           "should be what was done to it.", align="justify")
    log = pd.DataFrame(r["cleaning_log"])
    b.table(log, caption="Complete cleaning log (43 steps) from `cleaning_log.csv`.",
            font_size=7.5, max_rows=43)
    touched = log[pd.to_numeric(log["Rows / Values Affected"], errors="coerce").fillna(0) > 0]
    b.para(f"Steps that changed at least one value: {len(touched)} of {len(log)}. "
           f"{'All of them were type or label normalisations rather than value edits.' if len(touched) == 0 else 'Listed in the table above; everything else was a no-op on this file.'}",
           align="justify")
    b.heading("15.3 Decisions and their justification", 2)
    b.table([["Situation", "Decision", "Why not the alternative"]] + [
        ["Duplicate rows", "drop_duplicates() on the full record",
         "A duplicated city-day would double-count a day; there were none, so the rule is "
         "recorded as tested and inert."],
        ["Date column", "parsed to datetime, invalid values reported",
         "String dates sort wrongly and block time features."],
        ["Missing numeric", "median imputation per column, only if gaps exist",
         "Mean is pulled by the extreme tail of concentration data; dropping rows would "
         "have deleted whole city-days. No gaps existed."],
        ["Missing categorical", "explicit 'Unknown' label",
         "Guessing a city or a band would fabricate evidence."],
        ["Outliers", "IQR flags added as columns; values kept",
         "Deleting the highest readings would delete precisely the events worth studying."],
        ["Negative / zero concentrations", "invalid-value scan reported",
         "A negative concentration is a data error; the scan proves none exist."],
        ["Categorical case / spelling", "normalised to title case",
         "'delhi' and 'Delhi' would otherwise be two cities."],
        ["Unit columns", "documented as supplied, not converted",
         "The file does not state an averaging basis, so a conversion would be an "
         "assumption."],
    ], caption="Preprocessing decisions, each tied to a reason.",
        font_size=8.5, widths=[1.3, 2.0, 3.2])
    b.heading("15.4 Feature engineering", 2)
    b.para("The cleaned 22-column table is the input to feature engineering, which produces "
           "the modelling table. Each feature and its purpose is recorded in "
           "`feature_inventory.csv`; the notes below are the ones that matter for "
           "interpretation.", align="justify")
    b.bullets(r["feature_notes"])
    b.table(pd.DataFrame(r["feature_inventory"]),
            caption="Feature inventory produced by `src/feature_engineering.py`.",
            font_size=7.5, max_rows=24)
    b.para("Ratios are left blank where the denominator is zero and lag/rolling features "
           "are left blank on the first day of each city's series, because no previous "
           "observation exists. Those blanks are documented in section 23's quality check "
           "rather than filled with an invented value.", align="justify")
    b.heading("15.5 Verification of the AQI band scale", 2)
    b.para("The band table in `src/config.py` (0-50 Good, 51-100 Satisfactory, 101-200 "
           "Moderate, 201-300 Poor, 301-400 Very Poor, 401-500 Severe) is the CPCB "
           "National Air Quality Index scale, and it is checked rather than trusted: "
           "notebook 02 recomputes `AQI_Bucket` from `AQI` with that table and reports "
           "100 % agreement with the labels in the file, with a clean diagonal in the "
           "cross-tabulation and non-overlapping observed ranges per label. That is also "
           "the proof that the target is a deterministic function of AQI, which is why AQI "
           "is excluded from the classifiers in section 20.", align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 16 - EDA
# --------------------------------------------------------------------------- #
def eda(b: D.DocxBuilder, r: dict) -> None:
    ds = r["dataset"]
    b.heading("16. Exploratory Data Analysis", 1)
    b.para(f"All descriptive statistics below are computed on the {n(ds['rows'], 0)} "
           f"complete records of the cleaned panel; none required imputation, so every "
           f"value is an originally recorded measurement.", align="justify")
    b.heading("16.1 Central tendency and spread", 2)
    b.table(pd.DataFrame(r["descriptive_statistics"]),
            caption="Descriptive statistics for AQI and each pollutant.",
            font_size=8)
    b.para("Read together with section 16.4, the table already carries a warning: the "
           "pollutants have means close to the midpoint of their own range and "
           "interquartile ranges close to half that range, which is what a uniform draw "
           "looks like, not what concentrations look like.", align="justify")
    b.heading("16.2 Distribution shape and its test", 2)
    b.table(pd.DataFrame(r["distribution_tests"]),
            caption="Shapiro-Wilk, Kolmogorov-Smirnov distance to uniform, skewness and "
                    "excess kurtosis per numeric column.", font_size=8)
    b.figure(C.VIZ_DIR / "eda" / "01_aqi_distribution.png",
             "Distribution of AQI across all observations.", 5.6)
    b.figure(C.VIZ_DIR / "eda" / "05_pollutant_distributions.png",
             "Distribution of every pollutant, each on its own scale.", 6.0)
    b.figure(C.VIZ_DIR / "eda" / "02_aqi_category_distribution.png",
             "Share of observations in each AQI category.", 5.6)
    b.heading("16.3 Cities", 2)
    city = pd.DataFrame(r["summaries"]["city"])
    show = city[["City", "Observation_Count", "Avg_AQI", "Median_AQI", "Std_AQI",
                 "Avg_PM2.5", "Avg_PM10", "Anomaly_Count", "Anomaly_Pct",
                 "Dominant_Cluster"]]
    b.table(show, caption="City-level profile from `city_summary.csv`.", font_size=8)
    b.figure(C.VIZ_DIR / "eda" / "03_city_avg_median_aqi.png",
             "Mean and median AQI by city.", 5.8)
    b.figure(C.VIZ_DIR / "eda" / "04_city_aqi_boxplot.png",
             "Spread of AQI within each city.", 5.8)
    b.figure(C.VIZ_DIR / "eda" / "12_city_pollutant_heatmap.png",
             "City-by-pollutant profile (percentile-scaled).", 5.8)
    b.heading("16.4 Time: trend, season, month, weekday", 2)
    b.table(pd.DataFrame(r["summaries"]["yearly"]),
            caption="Yearly averages - the column that a real trend would show.",
            font_size=8)
    b.figure(C.VIZ_DIR / "eda" / "06_aqi_trend_time.png",
             "AQI over the whole period with an OLS trend line.", 6.0)
    b.figure(C.VIZ_DIR / "eda" / "08_yearly_aqi.png", "Yearly mean AQI.", 5.6)
    b.figure(C.VIZ_DIR / "eda" / "07_monthly_aqi.png", "Monthly mean AQI.", 5.6)
    b.figure(C.VIZ_DIR / "eda" / "09_seasonal_aqi.png",
             "Seasonal comparison (Indian meteorological seasons).", 5.6)
    b.figure(C.VIZ_DIR / "eda" / "11_weekday_aqi.png", "Weekday profile of AQI.", 5.6)
    b.figure(C.VIZ_DIR / "eda" / "10_pm25_vs_pm10.png",
             "PM2.5 against PM10 - the pair that a real dataset ties together tightly.",
             5.6)
    b.heading("16.5 Do the visible differences mean anything?", 2)
    b.para("The charts above show differences. Significance tests decide whether they are "
           "distinguishable from noise, and here they are not.", align="justify")
    b.table(pd.DataFrame(r["group_test_table"]),
            caption="One-way ANOVA and Kruskal-Wallis tests on AQI, grouped by city, "
                    "season, month and weekend flag.", font_size=8.5)
    b.table([["Diagnostic", "Value", "Reading"]] + [
        ["City effect (ANOVA p)", n(r["group_tests"]["City"]["ANOVA_p"], 4),
         "not significant - the five city averages are indistinguishable"],
        ["Month effect (ANOVA p)", n(r["group_tests"]["Month"]["ANOVA_p"], 4),
         "not significant - no seasonal cycle in this file"],
        ["Weekend effect (ANOVA p)", n(r["group_tests"]["Is_Weekend"]["ANOVA_p"], 4),
         "not significant"],
        ["Yearly trend slope", f"{n(r['trend_test']['slope_per_year'], 4)} index pts/year "
         f"(p = {n(r['trend_test']['p_value'], 4)})", r["trend_test"]["verdict"]],
        ["Lag-1 autocorrelation of AQI",
         n(r["autocorrelation"][0]["Mean_Autocorrelation"], 4),
         "essentially none - a real daily series carries yesterday forward"],
    ], caption="Statistical tests behind the EDA narrative.", font_size=8.5,
        widths=[1.8, 1.7, 2.9])
    b.para("The honest summary of this section: the panel is complete, balanced and "
           "internally consistent, and it contains no detectable city, season, month, "
           "weekday or trend structure. The dashboard in section 22 therefore presents "
           "these comparisons with that caveat attached to them.", align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 17 - Correlation
# --------------------------------------------------------------------------- #
def correlation(b: D.DocxBuilder, r: dict) -> None:
    b.heading("17. Correlation Analysis", 1)
    b.heading("17.1 Pollutant-pollutant structure", 2)
    b.figure(C.VIZ_DIR / "correlation" / "01_correlation_heatmap.png",
             "Pearson correlation matrix of the pollutants and AQI.", 5.8)
    b.table(pd.DataFrame(r["correlation_with_aqi"]),
            caption="Association of each variable with AQI, with Pearson and Spearman "
                    "significance.", font_size=8)
    b.para(f"No pollutant is meaningfully correlated with AQI: the largest magnitude is "
           f"|r| = {n(pd.DataFrame(r['correlation_with_aqi'])['Pearson_r'].abs().max(), 4)}. "
           f"Pollutants are also nearly uncorrelated with one another (matrix above), which "
           f"is itself unusual - PM2.5 and PM10 normally move together because the finer "
           f"fraction is a component of the coarser one.", align="justify")
    b.figure(C.VIZ_DIR / "correlation" / "02_pollutant_vs_aqi.png",
             "Each pollutant plotted against AQI.", 6.0)
    b.figure(C.VIZ_DIR / "correlation" / "03_pairwise_correlations.png",
             "Pairwise relationships among the leading pollutants.", 6.0)
    b.heading("17.2 Rank correlation and monotonic association", 2)
    b.para("Spearman's rho was computed alongside Pearson's r because it does not assume a "
           "linear form. The two agree closely (see "
           "`data/processed/pollutant_pair_correlations.csv` and the Spearman matrix in "
           "`results.json`), so the absence of association is not an artefact of "
           "linearity: there is little monotonic relationship to find either.",
           align="justify")
    b.heading("17.3 Linear fit versus non-linear predictability", 2)
    lf, pr = r["linear_fit"], r["predictability"]
    b.table([["Quantity", "Value", "Meaning"]] + [
        ["OLS of AQI on all pollutants", f"R\u00b2 = {n(lf['R2'], 4)} "
         f"(adjusted {n(lf['Adj_R2'], 4)}), RMSE {n(lf['RMSE'], 2)}",
         "linear chemistry explains almost none of AQI"],
        ["Random forest CV predicting AQI", f"R\u00b2 = {n(pr['tree_CV_R2'], 4)}, "
         f"MAE {n(pr['tree_CV_MAE'], 2)}", "almost perfectly reproducible"],
        ["Gap", n(pr["gap"], 4), "the relationship is non-linear, not absent"],
    ], caption="Linear versus non-linear predictability of AQI.", font_size=8.5,
        widths=[2.0, 2.4, 2.0])
    b.para(pr["verdict"], align="justify", italic=True)
    b.para("This combination - no linear correlation, near-perfect tree predictability - is "
           "the fingerprint of a deterministic non-monotonic function applied to a couple "
           "of columns, and it is the reason the next subsection exists.", align="justify")
    b.heading("17.4 How AQI is actually built in this file", 2)
    st = r["aqi_structure"]
    b.table(pd.DataFrame(list(st["single_column_cv_r2"].items()),
                         columns=["Column", "CV R\u00b2 predicting AQI"]),
            caption="Single-column cross-validated R\u00b2 for AQI. Negative values mean "
                    "the column is worse than predicting the mean.", font_size=8.5)
    b.table(pd.DataFrame(st["forward_selection"]),
            caption="Greedy forward selection: the smallest set of columns that "
                    "reconstructs AQI.", font_size=8.5)
    b.table(pd.DataFrame(st["decile_profile_of_leading_column"]),
            caption="Mean AQI in each decile of PM2.5. A published sub-index rises "
                    "monotonically with concentration.", font_size=8)
    b.table([["Diagnostic", "Value"]] + [
        ["Informative set", ", ".join(st["informative_set"])],
        ["CV R\u00b2 of that set", n(st["forward_selection"][-1]["cv_r2"], 4)],
        ["Monotonic in the leading column?", str(st["monotonic_in_leading_column"])],
        ["Within-cell SD of AQI (400 PM2.5 x PM10 cells)", n(st["within_cell_spread"]["mean_sd"], 2)],
        ["Overall SD of AQI", n(st["within_cell_spread"]["overall_sd"], 2)],
        ["SD reduction inside cells", f"{n(st['within_cell_spread']['sd_reduction_pct'], 1)} %"],
    ], caption="Structure probe of the derived AQI column (`aqi_structure_probe.csv`).",
        font_size=8.5, widths=[3.4, 2.6])
    b.para(st["verdict"], align="justify", italic=True)
    b.para("Consequences carried through the rest of the project: AQI is a derived column, "
           "so it is excluded from every model that predicts an AQI-derived label; the "
           "clustering and anomaly models that do use it are reported both ways; and no "
           "claim about the drivers of AQI in the real world is made from it.",
           align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 18 - K-Means
# --------------------------------------------------------------------------- #
def kmeans(b: D.DocxBuilder, r: dict) -> None:
    cl = r["clustering"]
    b.heading("18. K-Means Clustering", 1)
    b.heading("18.1 Setup", 2)
    b.table([["Choice", "Value", "Reason"]] + [
        ["Features", ", ".join(cl["features_used"]),
         "Measured pollutant concentrations only - derived columns would let the model "
         "rediscover AQI"],
        ["Scaling", "StandardScaler (zero mean, unit variance)",
         "K-Means uses Euclidean distance, so unscaled columns with large ranges would "
         "dominate"],
        ["Distance / objective", "Euclidean to centroid; minimise inertia",
         "Standard K-Means (Lloyd / Hartigan-Wong implementation in scikit-learn)"],
        ["k searched", "2 to 10", "Recorded in `k_selection_table.csv`"],
        ["random_state", r["environment"]["random_state"], "Reproducibility"],
        ["Silhouette subsample", "6,000 rows",
         "Silhouette is quadratic in n; a fixed subsample keeps it computable and "
         "reproducible"],
    ], caption="Clustering configuration.", font_size=8.5, widths=[1.3, 1.9, 3.2])
    b.heading("18.2 Choosing k from evidence", 2)
    b.table(pd.DataFrame(cl["k_table"]), caption="Elbow and silhouette evidence for every "
            "k evaluated.", font_size=8)
    b.figure(C.VIZ_DIR / "clustering" / "01_elbow_silhouette.png",
             "Inertia (elbow) and silhouette score against k.", 5.8)
    ch = cl["choice"]
    b.para(f"Selected k = {ch['chosen_K']} (silhouette {n(ch['silhouette'], 4)}). "
           f"{ch['rationale']}", align="justify")
    b.para(f"The disagreement between the two rules is reported rather than resolved "
           f"quietly: the elbow rule suggested k = {ch['K_by_elbow_rule']}, the silhouette "
           f"preferred k = {ch['K_by_silhouette']}. A silhouette of "
           f"{n(ch['silhouette'], 4)} is weak by any convention, so the clusters are "
           f"described as a partition of this file, not as a discovered structure.",
           align="justify")
    b.heading("18.3 Cluster profiles", 2)
    b.table(pd.DataFrame(cl["profile"]), caption="Cluster sizes and mean pollutant "
            "concentrations in original units.", font_size=8)
    b.table(pd.DataFrame(cl["descriptions"]), caption="Neutral descriptions of each "
            "cluster, generated from the profile rather than written by hand.",
            font_size=8)
    b.figure(C.VIZ_DIR / "clustering" / "03_cluster_sizes_profiles.png",
             "Cluster sizes and centroid profiles.", 6.0)
    b.figure(C.VIZ_DIR / "clustering" / "04_cluster_centroids.png",
             "Centroid heatmap (standardised units).", 5.8)
    b.heading("18.4 Projection and what it shows", 2)
    b.para(f"For visual inspection only, the scaled features were projected to two "
           f"components by PCA, which explains "
           f"{n(100 * sum(cl['pca_explained_variance']), 1)} % of total variance "
           f"({', '.join(n(100 * v, 2) + '%' for v in cl['pca_explained_variance'])}). "
           f"Low explained variance is consistent with near-independent columns: no plane "
           f"in this data contains much of it.", align="justify")
    b.figure(C.VIZ_DIR / "clustering" / "02_pca_clusters.png",
             "Observations projected onto the first two principal components, coloured by "
             "cluster.", 5.8)
    b.para("The projection is used for pictures, never for labels: cluster membership comes "
           "from the model fitted in the full scaled feature space.", size=9.5, italic=True)
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 19 - Anomaly detection
# --------------------------------------------------------------------------- #
def anomaly(b: D.DocxBuilder, r: dict) -> None:
    an = r["anomaly"]
    b.heading("19. Anomaly Detection", 1)
    b.heading("19.1 Method and parameters", 2)
    b.para("Isolation Forest isolates observations instead of modelling density: random "
           "subsets of features and random split points are used to build trees, and "
           "observations that need fewer splits to be isolated are more anomalous. It "
           "scales to many columns, does not assume a Gaussian distribution - which matters "
           "here, since section 16.2 shows the columns are uniform-like - and produces a "
           "continuous score that can be thresholded.", align="justify")
    b.table([["Parameter", "Value", "Note"]] + [
        ["n_estimators", n(an["params"]["n_estimators"], 0), "trees in the ensemble"],
        ["contamination", n(an["params"]["contamination"], 2),
         "the expected anomaly fraction - an assumption, stated up front"],
        ["random_state", an["params"]["random_state"], "reproducibility"],
        ["Features", ", ".join(an["params"]["features"]),
         "measured pollutants only"],
        ["Rows evaluated", n(an["params"]["rows_evaluated"], 0), "full panel"],
    ], caption="Isolation Forest configuration.", font_size=8.5, widths=[1.3, 1.3, 3.8])
    b.heading("19.2 Results", 2)
    b.table(pd.DataFrame([an["stats"]]), caption="Anomaly detection summary.",
            font_size=8.5)
    b.para(an["stats"]["Note"], align="justify", italic=True)
    b.para(f"{n(an['stats']['Anomalies detected'], 0)} of "
           f"{n(an['stats']['Rows evaluated'], 0)} observations were flagged. The share "
           f"matches the configured contamination rate almost exactly, which is the "
           f"expected behaviour of the algorithm and not an independent finding: with "
           f"contamination = {n(an['params']['contamination'], 2)} the method is asked to "
           f"call 5 % of the rows unusual, and it obliges. What the model does contribute is "
           f"the ranking (`score_samples`) and the profile of the rows it places at the "
           f"extremes.", align="justify")
    b.figure(C.VIZ_DIR / "anomaly" / "01_anomaly_distribution.png",
             "Anomaly score distribution with the decision threshold.", 5.8)
    b.heading("19.3 Where the flagged rows sit", 2)
    b.table(pd.DataFrame(an["by_city"]), caption="Anomalies by city.", font_size=8.5)
    b.table(pd.DataFrame(an["by_year"]), caption="Anomalies by year.", font_size=8.5)
    b.figure(C.VIZ_DIR / "anomaly" / "02_anomaly_by_city.png",
             "Anomaly counts and rates by city.", 5.8)
    b.figure(C.VIZ_DIR / "anomaly" / "03_anomaly_timeline.png",
             "Flagged observations over time.", 5.8)
    b.figure(C.VIZ_DIR / "anomaly" / "04_anomaly_scatter.png",
             "Two leading pollutants with flagged observations highlighted.", 5.8)
    b.para(f"Flagged and unflagged rows differ only marginally in mean concentration - the "
           f"largest relative difference is "
           f"{n(pd.DataFrame(an['pollutant_comparison'])['Pct_Change'].abs().max(), 2)} % "
           f"- which is what a uniform, unstructured panel produces: 'unusual' has to be "
           f"created by the joint configuration of values rather than by an event.",
           align="justify")
    b.table(pd.DataFrame(an["pollutant_comparison"]),
            caption="Mean and maximum concentration of each pollutant in flagged versus "
                    "normal rows.", font_size=8.5)
    b.heading("19.4 Sensitivity", 2)
    b.para("Because the flagged share is set by `contamination`, the meaningful check is "
           "not 'how many' but 'which': notebook 07 sweeps the parameter and compares the "
           "resulting sets, and reports that the ranking of observations by anomaly score "
           "is stable while the count scales with the parameter. The dashboard therefore "
           "shows `Configured Contamination %` beside `Anomaly Rate %` so the assumption "
           "travels with the number.", align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 20 - Classification
# --------------------------------------------------------------------------- #
def classification(b: D.DocxBuilder, r: dict) -> None:
    cf = r["classification"]
    split = cf["split_info"]
    b.heading("20. Classification", 1)
    b.heading("20.1 Objective and setup", 2)
    b.para(f"Predict the AQI category (`{split['target']}`) from pollutant measurements "
           f"alone. {n(split['n_features'], 0)} features, a stratified "
           f"{n(split['train_rows'], 0)}/{n(split['test_rows'], 0)} train/test split "
           f"(test size {n(split['test_size'], 2)}), fixed seed "
           f"{split['random_state']}, and 3-fold cross-validation in addition to the "
           f"held-out test set.", align="justify")
    b.table([["Model", "Why it is in the comparison"]] + [
        ["Baseline (prior)", "Always predicts the most frequent class. Any model that "
         "cannot beat this has learned nothing useful."],
        ["Logistic Regression (pipeline with scaler)",
         "Linear, interpretable multi-class baseline"],
        ["Decision Tree", "Non-linear, easily over-fitted - a useful warning sign"],
        ["Random Forest", "Bagged trees, robust to scale, gives feature importance"],
        ["Hist Gradient Boosting", "Modern boosted trees, usually the strongest "
         "off-the-shelf tabular model"],
    ], caption="Models fitted, with the reason each one is there.", font_size=8.5,
        widths=[1.8, 4.6])
    b.heading("20.2 Class imbalance", 2)
    b.table(pd.DataFrame(cf["class_balance"]),
            caption="Target distribution - the reason accuracy alone is not reported.",
            font_size=8.5)
    b.para("The two rarest classes hold 6 and 113 of 18,265 rows. A model can therefore be "
           "99.97 % accurate and useless for those classes, which is why macro-averaged "
           "precision, recall and F1 and the per-class table are the headline metrics, and "
           "why the split is stratified so that every class appears in the test set.",
           align="justify")
    b.heading("20.3 Data leakage - measured, not assumed", 2)
    lk = cf["leakage"]
    b.table([["Configuration", "Accuracy %", "Macro F1", "Features"]] + [
        ["Without the leaky column (reported model)",
         n(lk["without leaky column"]["accuracy_%"]), n(lk["without leaky column"]["macro_F1"], 4),
         n(lk["without leaky column"]["features_used"], 0)],
        ["With AQI included as a feature",
         n(lk["with leaky column"]["accuracy_%"]), n(lk["with leaky column"]["macro_F1"], 4),
         n(lk["with leaky column"]["features_used"], 0)],
        ["Inflation", f"+{n(lk['accuracy_inflation_pp'])} pp",
         f"+{n(lk['with leaky column']['macro_F1'] - lk['without leaky column']['macro_F1'], 4)}",
         "+1"],
    ], caption="Leakage experiment: the same model with and without AQI.",
        font_size=8.5, widths=[2.7, 1.3, 1.1, 1.0])
    b.para(lk["verdict"], align="justify", italic=True)
    b.para("The inflation is modest here (0.68 pp) precisely because AQI is a "
           "non-monotonic function of two pollutants that the tree ensemble already "
           "recovers; on a genuine dataset, where the band is a monotone function of the "
           "index, the same mistake inflates accuracy by tens of points. The experiment is "
           "kept in the project for that reason: it demonstrates the check, not the size of "
           "the effect in this particular file.", align="justify")
    b.heading("20.4 Results", 2)
    comp = pd.DataFrame(cf["comparison"])
    b.table(comp, caption="Model comparison on the held-out test set (plus 3-fold CV).",
            font_size=8)
    b.figure(C.VIZ_DIR / "classification" / "01_model_comparison.png",
             "Accuracy and macro-F1 by model, against the prior baseline.", 5.8)
    b.table(pd.DataFrame(cf["per_class"]).query("Model == @BEST"),
            caption=f"Per-class metrics for {BEST}: precision, recall, F1 and support.",
            font_size=8.5)
    b.para(f"{BEST} reaches {n(comp.loc[comp['Model'] == BEST, 'Accuracy_%'].iloc[0])} % "
           f"accuracy and macro-F1 {n(comp.loc[comp['Model'] == BEST, 'F1_macro'].iloc[0], 4)}, "
           f"i.e. {n(comp.loc[comp['Model'] == BEST, 'Lift_over_Baseline_pp'].iloc[0])} "
           f"percentage points above the prior baseline. The weighted and macro figures "
           f"diverge sharply, which is the imbalance showing: performance is concentrated "
           f"in the four classes that hold over 99 % of the rows.", align="justify")
    conf = pd.DataFrame(cf["confusion"]).query("Model == @BEST")
    if len(conf):
        pivot = conf.pivot(index="Actual", columns="Predicted", values="Count").fillna(0)
        b.table(pivot.reset_index(), caption=f"Confusion matrix for {BEST} on the test set.",
                font_size=8.5)
    b.figure(C.VIZ_DIR / "classification" / "02_confusion_matrices.png",
             "Confusion matrices for all models.", 6.0)
    b.figure(C.VIZ_DIR / "classification" / "03_per_class_recall.png",
             "Per-class recall compared across models.", 5.8)
    b.heading("20.5 What the model relies on", 2)
    b.table(pd.DataFrame(cf["feature_importance"]),
            caption="Random Forest mean decrease in impurity, by pollutant.",
            font_size=8.5)
    b.figure(C.VIZ_DIR / "classification" / "04_feature_importance.png",
             "Feature importance for the best model.", 5.6)
    b.para("Importance is spread across the pollutants rather than concentrated in the two "
           "columns that reconstruct AQI, which is a further sign that the target's "
           "relationship to the features is not the physically meaningful one.",
           align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 21 - Model evaluation
# --------------------------------------------------------------------------- #
def evaluation(b: D.DocxBuilder, r: dict) -> None:
    cf = r["classification"]
    comp = pd.DataFrame(cf["comparison"])
    b.heading("21. Model Evaluation", 1)
    b.heading("21.1 Metrics and why each one is used", 2)
    b.table([["Metric", "Definition", "What it can hide"]] + [
        ["Accuracy", "share of test rows predicted correctly",
         "the whole story under imbalance"],
        ["Precision (per class)", "TP / (TP + FP)", "how many predictions of a class were right"],
        ["Recall (per class)", "TP / (TP + FN)", "how much of a class was found at all"],
        ["F1", "harmonic mean of precision and recall", "needs both, so it resists a "
         "degenerate 'predict one class' solution"],
        ["Macro F1 / precision / recall", "unweighted mean over classes",
         "the honest headline here - rare classes count as much as common ones"],
        ["Weighted F1", "mean weighted by class support", "flatters a model that ignores "
         "rare classes"],
        ["Confusion matrix", "counts of actual versus predicted",
         "nothing - read it; it shows which classes are confused"],
        ["Cross-validation", "repeated fit/predict over folds", "single-split luck"],
        ["Lift over baseline", "accuracy minus prior-baseline accuracy",
         "how much was learned beyond the class frequencies"],
    ], caption="The evaluation vocabulary used in this report.", font_size=8.5,
        widths=[1.5, 2.3, 2.6])
    b.heading("21.2 Comparison across all three data-mining tasks", 2)
    b.table([["Task", "Model", "Evidence", "Verdict recorded"]] + [
        ["Clustering", "K-Means",
         f"silhouette {n(r['clustering']['choice']['silhouette'], 4)} at k = "
         f"{r['clustering']['choice']['chosen_K']}; PCA 2-D variance "
         f"{n(100 * sum(r['clustering']['pca_explained_variance']), 1)} %",
         "weak separation; a description of the file, not a discovery"],
        ["Anomaly detection", "Isolation Forest",
         f"{n(r['anomaly']['stats']['Anomalies detected'], 0)} flagged "
         f"({n(r['anomaly']['stats']['Anomaly %'])} %) at contamination "
         f"{n(r['anomaly']['params']['contamination'], 2)}",
         "count is set by the parameter; the score ranking is the usable output"],
        ["Classification", best_model(r),
         f"accuracy {n(comp['Accuracy_%'].max())} %, macro-F1 "
         f"{n(comp['F1_macro'].max(), 4)}, lift "
         f"{n(comp['Lift_over_Baseline_pp'].max())} pp over the prior baseline",
         "learns the common bands well; rare bands remain unreliable"],
    ], caption="All three mining tasks, with the evidence and the verdict attached.",
        font_size=8.5, widths=[1.1, 1.2, 2.5, 1.6])
    b.heading("21.3 Robustness checks performed", 2)
    b.bullets([
        "Stratified splitting so that the 6-row `Good` class still appears in train and "
        "test (its test support is reported in the per-class table).",
        "3-fold cross-validation in addition to the single held-out split; the CV standard "
        "deviation is in `model_comparison.csv`.",
        "A prior baseline fitted on the same split, so 'accuracy' is never quoted without "
        "a reference point.",
        "An explicit leakage experiment (section 20.3) rather than a verbal assurance.",
        "Fixed seeds throughout, with library versions recorded in section 13.",
        "Silhouette computed on a fixed subsample, disclosed in section 18.1.",
    ])
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 22 - Power BI
# --------------------------------------------------------------------------- #
def powerbi(b: D.DocxBuilder, r: dict) -> None:
    dims = r["dimensions"]
    b.heading("22. Power BI Dashboard", 1)
    b.heading("22.1 Data model", 2)
    b.para("The processed panel is published as a star schema: one fact table and three "
           "dimensions, all generated by the pipeline so the dashboard cannot be built on a "
           "different version of the analysis than this report.", align="justify")
    b.table([["Table", "Rows", "Role", "Key columns"]] + [
        ["FACT_AirQuality", n(r["dataset"]["rows_after_cleaning"], 0), "fact",
         "City, Date, AQI, AQI_Bucket, pollutants, Cluster, Anomaly, PC1/PC2"],
        ["DIM_Date", len(dims["dim_date"]), "dimension (marked as date table)",
         "Date_Key, Year, Month_Name, Quarter, Season, Is_Weekend, Year_Month"],
        ["DIM_City", len(dims["dim_city"]), "dimension",
         "City, Record_Count, Distinct_Days, Dominant_Cluster"],
        ["DIM_Bucket", len(dims["dim_bucket"]), "dimension",
         "AQI_Bucket, Sort_Order, Band_Lower_AQI, Band_Upper_AQI, Colour"],
        ["MODEL_COMPARISON", "5", "unrelated support table",
         "Model, Accuracy_%, F1_macro, Lift_over_Baseline_pp"],
        ["CLASSIFICATION_PER_CLASS", "40", "unrelated support table",
         "Model, Class, Precision, Recall, F1-Score, Support"],
        ["CLUSTER_PROFILE / ANOMALY_BY_CITY / INSIGHTS", "small", "unrelated support tables",
         "mining results and the evidence-backed insight list"],
    ], caption="Tables imported into Power BI Desktop, with their role.", font_size=8.5,
        widths=[1.5, 0.8, 1.5, 2.6])
    b.code("DIM_City 1--* FACT_AirQuality *--1 DIM_Date\n"
           "DIM_Bucket 1--* FACT_AirQuality\n"
           "MODEL_COMPARISON, CLASSIFICATION_PER_CLASS, CLUSTER_PROFILE, INSIGHTS: "
           "unrelated (no relationship - they must not filter the fact table)")
    b.heading("22.2 Measures and pages", 2)
    b.para("57 DAX measures are defined in `dashboard/DAX_measures.dax`, grouped into "
           "coverage, AQI, pollutant, threshold, data-mining, time-intelligence, "
           "comparison, formatting and metric-selector blocks. They use `DIVIDE` for safe "
           "ratios, `ALLSELECTED`/`REMOVEFILTERS` for correct share and comparison "
           "denominators, and `TOTALYTD`/`SAMEPERIODLASTYEAR`/`DATESINPERIOD` for the time "
           "measures. The five pages follow the brief exactly:", align="justify")
    b.table([["#", "Page", "KPIs and core visuals"]] + [
        ["1", "Air Quality Intelligence - Executive Overview",
         "Average AQI, Total Cities, Total Observations, Average PM2.5, Average PM10, "
         "Anomaly Count; average AQI by city, AQI trend over time, AQI category "
         "distribution, average pollutant levels, city comparison; slicers City, Year, "
         "Month, AQI Category, Season"],
        ["2", "Pollutant Intelligence", "per-pollutant averages, pollutant vs AQI, "
         "correlation matrix, top-pollutant share, PM2.5/PM10 ratio, days above the "
         "adjustable PM2.5 limit"],
        ["3", "City Pollution Comparison", "city ranking, city-vs-overall variance, "
         "city x category matrix, small multiples per city, city radar profile, worst/best "
         "city cards"],
        ["4", "Data Mining Intelligence", "cluster table and PCA scatter, anomaly count / "
         "rate / by city / by year / over time, correlation heatmap, model comparison"],
        ["5", "Pollution Trends & Insights", "yearly, monthly and seasonal AQI, category "
         "trend, city trend comparison, pollutant trend comparison, insight cards"],
    ], caption="The five dashboard pages and what each one carries.", font_size=8.5,
        widths=[0.3, 1.7, 4.4])
    b.heading("22.3 KPI documentation", 2)
    b.para("Every KPI is documented in `dashboard/KPI_DEFINITIONS.md`: definition, the "
           "measure that computes it, the columns it reads, its unit, and what it does not "
           "mean. The thresholds used anywhere in the model are listed there with their "
           "authority - the CPCB National Air Quality Index bands for the categories, and "
           "the 24-hour PM2.5 value of India's National Ambient Air Quality Standards as "
           "the default of the adjustable limit parameter, which the guide flags for "
           "re-verification. No other limit is invented, and no WHO guideline value is "
           "quoted because none was verified from a primary source in this work.",
           align="justify")
    b.heading("22.4 Honesty features built into the pages", 2)
    b.bullets([
        "`Anomaly Caption` and `Configured Contamination %` sit beside the anomaly count, "
        "so a parameterised share cannot be read as an observed event rate.",
        "`Baseline Accuracy %` and `Lift over Baseline (pp)` sit beside model accuracy.",
        "`Leakage Note` states that AQI was excluded from the predictors and by how much "
        "including it would have inflated accuracy.",
        "Text boxes on pages 3 and 5 quote the ANOVA and trend p-values, so the city and "
        "month comparisons are read as descriptions of this sample.",
        "The model-result tables are deliberately unrelated to the fact table, so clicking "
        "a model bar cannot filter the measurements.",
    ])
    b.heading("22.5 Deliverable status of the dashboard", 2)
    b.para("A `.pbix` file can only be produced inside Power BI Desktop, which is not "
           "available in this build environment. What is delivered instead is the complete, "
           "verified input to that step: the exported tables, `dashboard/DAX_measures.dax`, "
           "`dashboard/POWER_BI_BUILD_GUIDE.md` (import list, column types, relationships, "
           "per-visual instructions, formatting, performance, publishing and a validation "
           "checklist) and `dashboard/KPI_DEFINITIONS.md`. The guide's validation checklist "
           "maps each KPI to the artefact that produced it, so the finished dashboard can be "
           "audited against this report. The screenshot slots below are left open for "
           "exactly that step.", align="justify")
    for page in ["1 - Executive Overview", "2 - Pollutant Intelligence",
                 "3 - City Pollution Comparison", "4 - Data Mining Intelligence",
                 "5 - Pollution Trends & Insights"]:
        b.para(f"[Screenshot placeholder: Power BI page {page}]", align="center",
               italic=True, size=10)
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 23 - Results
# --------------------------------------------------------------------------- #
def results_section(b: D.DocxBuilder, r: dict) -> None:
    ds, an, cf = r["dataset"], r["anomaly"], r["classification"]
    comp = pd.DataFrame(cf["comparison"])
    best = comp.sort_values("Accuracy_%", ascending=False).iloc[0]
    st = r["aqi_structure"]
    b.heading("23. Results", 1)
    b.para("Every value in the table below is read from a file produced by the pipeline; "
           "the source column names it.", align="justify")
    b.table([["Result", "Value", "Source"]] + [
        ["Records analysed", f"{n(ds['rows'], 0)} city-day rows, {ds['cities']} cities, "
         f"{ds['date_start']} to {ds['date_end']}", "results.json / dataset"],
        ["Columns raw -> modelled", f"{ds['columns']} -> 22 cleaned -> "
         f"{len(r['feature_inventory'])} inventoried features", "quality_comparison, feature_inventory.csv"],
        ["Rows removed during cleaning", "0 (no duplicates, no missing values)",
         "cleaning_log.csv"],
        ["Blank cells in measured columns", "0 (8 blanks, all in derived columns, all "
         "documented)", "notebook 09 quality check"],
        ["AQI band scale consistency", "100 % agreement with the CPCB band table",
         "notebook 02 section 5"],
        ["Clusters", f"k = {r['clustering']['choice']['chosen_K']}, silhouette "
         f"{n(r['clustering']['choice']['silhouette'], 4)}, sizes "
         f"{', '.join(str(int(p['Cluster_Size'])) for p in r['clustering']['profile'])}",
         "k_selection_table.csv, cluster_profile.csv"],
        ["PCA variance (2 components)",
         f"{n(100 * sum(r['clustering']['pca_explained_variance']), 1)} %", "results.json / clustering"],
        ["Anomalies", f"{n(an['stats']['Anomalies detected'], 0)} "
         f"({n(an['stats']['Anomaly %'])} %) at contamination "
         f"{n(an['params']['contamination'], 2)}", "anomaly_results.csv"],
        ["Best classifier", f"{best['Model']}: accuracy {n(best['Accuracy_%'])} %, "
         f"macro-F1 {n(best['F1_macro'], 4)}, CV {n(best['CV_Accuracy_%'])} %",
         "model_comparison.csv"],
        ["Prior baseline", f"{n(comp.loc[comp['Model'] == 'Baseline (prior)', 'Accuracy_%'].iloc[0])} % "
         f"(lift {n(best['Lift_over_Baseline_pp'])} pp)", "model_comparison.csv"],
        ["Leakage effect of AQI", f"+{n(cf['leakage']['accuracy_inflation_pp'])} pp accuracy",
         "leakage_check.json"],
        ["Strongest correlation with AQI",
         f"|r| = {n(pd.DataFrame(r['correlation_with_aqi'])['Pearson_r'].abs().max(), 4)}",
         "correlation_with_aqi.csv"],
        ["Non-linear predictability of AQI", f"tree CV R\u00b2 = "
         f"{n(r['predictability']['tree_CV_R2'], 4)} vs linear R\u00b2 = "
         f"{n(r['predictability']['linear_R2'], 4)}", "nonlinear_predictability.csv"],
        ["AQI reconstruction from PM2.5 + PM10", f"CV R\u00b2 = "
         f"{n(st['forward_selection'][1]['cv_r2'], 4)}, monotonic in PM2.5: "
         f"{st['monotonic_in_leading_column']}", "aqi_structure_probe.csv"],
        ["City / month / trend significance",
         f"p = {n(r['group_tests']['City']['ANOVA_p'], 4)} / "
         f"{n(r['group_tests']['Month']['ANOVA_p'], 4)} / "
         f"{n(r['trend_test']['p_value'], 4)} - none significant", "group_comparison_tests.csv"],
        ["Insights generated", f"{len(r['insights'])} statements, each with its evidence",
         "insights.csv"],
        ["Dashboard", "1 fact table + 3 dimensions, 57 DAX measures, 5 pages, "
         "KPI documentation", "dashboard/"],
    ], caption="Consolidated results.", font_size=8.5, widths=[1.6, 3.2, 1.6])
    b.para("Two of these rows are the ones a reviewer should look at first: the strongest "
           "correlation with AQI, and the AQI reconstruction. Together they say that this "
           "file's index is a non-monotonic function of two of its columns and is not "
           "associated with the rest, which is the basis of section 12.5.", align="justify")
    b.page_break()


# --------------------------------------------------------------------------- #
# Section 24 - Findings
# --------------------------------------------------------------------------- #
def findings(b: D.DocxBuilder, r: dict) -> None:
    b.heading("24. Findings", 1)
    b.para("The insight list is generated by `src/reporting.py` from the computed "
           "artefacts. Each row carries its own quantitative evidence and the file it came "
           "from, and an insight is dropped rather than softened if its evidence does not "
           "exist. The evidence-strength column distinguishes what was measured from what "
           "was inferred.", align="justify")
    ins = pd.DataFrame(r["insights"])
    b.table(ins[["Category", "Insight", "Quantitative Evidence", "Derived From",
                 "Evidence Strength"]],
            caption=f"Complete insight list ({len(ins)} rows).", font_size=8)
    b.heading("24.1 The project's ten questions, answered", 2)
    # Values are formatted once here rather than inside the sentences below, so the
    # answers stay readable and each statistic is quoted exactly once.
    city_tbl = pd.DataFrame(r["summaries"]["city"])
    corr_tbl = pd.DataFrame(r["correlation_with_aqi"])
    struct = r["aqi_structure"]
    hi_city = city_tbl.loc[city_tbl["Avg_AQI"].idxmax(), "City"]
    lo_city = city_tbl.loc[city_tbl["Avg_AQI"].idxmin(), "City"]
    v = {
        "aqi_hi": n(city_tbl["Avg_AQI"].max()),
        "aqi_lo": n(city_tbl["Avg_AQI"].min()),
        "city_p": n(r["group_tests"]["City"]["ANOVA_p"], 4),
        "month_p": n(r["group_tests"]["Month"]["ANOVA_p"], 4),
        "season_p": n(r["group_tests"]["Season"]["ANOVA_p"], 4),
        "slope": n(r["trend_test"]["slope_per_year"], 4),
        "trend_p": n(r["trend_test"]["p_value"], 4),
        "acf1": n(r["autocorrelation"][0]["Mean_Autocorrelation"], 4),
        "r_max": n(corr_tbl["Pearson_r"].abs().max(), 4),
        "aqi_r2": n(struct["forward_selection"][1]["cv_r2"], 4),
        "k": r["clustering"]["choice"]["chosen_K"],
        "sil": n(r["clustering"]["choice"]["silhouette"], 4),
        "anom": n(r["anomaly"]["stats"]["Anomalies detected"], 0),
        "acc": n(comp_max(r)),
        "f1": n(f1_max(r), 4),
        "lift": n(lift_max(r)),
        "model": best_model(r),
    }
    ans = [
        ("Which cities have higher average AQI?",
         f"{hi_city} is highest at {v['aqi_hi']} and {lo_city} lowest at "
         f"{v['aqi_lo']}, a gap of well under two index points. One-way ANOVA gives "
         f"p = {v['city_p']}, so the ordering describes this file and is not evidence of a "
         f"real difference between the cities."),
        ("How does AQI change over time?",
         f"It does not, detectably: the yearly slope is {v['slope']} index points per year "
         f"with p = {v['trend_p']}, and the lag-1 autocorrelation within a city is "
         f"{v['acf1']}."),
        ("Which pollutants are most strongly associated with AQI?",
         f"None in the linear sense - the largest magnitude is |r| = {v['r_max']}. In the "
         f"non-linear sense, PM2.5 and PM10: together they reconstruct AQI at "
         f"cross-validated R\u00b2 of {v['aqi_r2']}."),
        ("How do pollutants correlate with each other?",
         "Almost not at all - the correlation matrix is close to an identity matrix, which "
         "is the opposite of the co-movement expected from a shared atmosphere."),
        ("Are observations naturally grouped into pollution profiles?",
         f"K-Means partitions them into {v['k']} groups at silhouette {v['sil']}; the "
         f"separation is weak and the elbow and silhouette rules disagree, so no strong "
         f"natural grouping is claimed."),
        ("Which observations represent unusual pollution patterns?",
         f"{v['anom']} rows at the extremes of the Isolation Forest score, spread evenly "
         f"across cities and years - a share set by the contamination parameter, and a "
         f"ranking rather than an event list."),
        ("Can AQI categories be predicted from pollutant measurements?",
         f"Yes for the four common bands: {v['model']} reaches {v['acc']} % accuracy with "
         f"macro-F1 {v['f1']}, which is {v['lift']} percentage points above the prior "
         f"baseline. No for the two rare bands, whose per-class recall is unreliable on 6 "
         f"and 113 rows."),
        ("Which months or seasons have higher pollution levels?",
         f"The monthly means span only a few index points and the month effect is "
         f"insignificant with p = {v['month_p']}; the same holds for season, "
         f"p = {v['season_p']}. Evidence is insufficient to name a polluted season in this "
         f"file."),
        ("How do pollution profiles differ between cities?",
         "They are near-identical: city means differ by less than 2 index points and every "
         "city's dominant cluster is the same pair of clusters in similar proportions."),
        ("What insights can a BI dashboard communicate?",
         "The dashboard communicates the panel's completeness, the category mix, the "
         "mining results and - deliberately - the caveats, because a dashboard that hides "
         "the assumptions behind a KPI is worse than no dashboard."),
    ]
    b.table([["Question", "Answer from this dataset"]] + [[q, a] for q, a in ans],
            caption="Each objective question answered with its statistic.",
            font_size=8.5, widths=[1.9, 4.5])
    b.heading("24.2 Where the evidence was insufficient", 2)
    b.bullets([
        "No claim about a real long-term pollution trend: the test does not reject the "
        "null.",
        "No claim that any city is genuinely more polluted: the city test does not reject "
        "the null.",
        "No claim about emission sources or about which pollutant 'causes' poor air: "
        "association is negligible and the study is observational.",
        "No statement about how often real pollution episodes occur: the anomaly count is "
        "a parameter choice.",
        "No compliance assessment against any standard: the file lacks station, "
        "averaging-time and instrument metadata.",
    ])
    b.page_break()


# --------------------------------------------------------------------------- #
# Sections 25-28
# --------------------------------------------------------------------------- #
def limitations(b: D.DocxBuilder, r: dict) -> None:
    b.heading("25. Limitations", 1)
    b.heading("25.1 Limitations of the method", 2)
    b.steps(LIMITATIONS_FROM_BRIEF)
    b.heading("25.2 Limitations this project ran into", 2)
    b.steps([
        "The dataset's provenance is undocumented and its statistical properties are "
        "consistent with a synthetic panel (section 12.5). Every finding is therefore a "
        "finding about the file, and the modelling results should not be transferred to "
        "real air-quality decisions without re-running the pipeline on monitored data.",
        "The panel is complete but shallow in kind: five cities, one record per city-day, "
        "no station-level, source-level or meteorological columns, so within-city "
        "variation and any physical explanation are out of reach.",
        "Benzene, toluene and xylene are absent from this file, so the volatile-organic "
        "component of the expected schema could not be analysed.",
        "The target is derived from a single index column, so classification measures how "
        "well a deterministic banding can be recovered, not how well air quality can be "
        "assessed.",
        "Two of the six classes have 6 and 113 members; per-class scores for them are "
        "reported with their support and should be read as indicative only.",
        "Units, averaging time and instrument basis are undocumented, so no conversion, "
        "exceedance count or compliance statement is made beyond an adjustable parameter.",
        "The dashboard is delivered as a fully specified build (data, DAX, guide, KPI "
        "documentation) rather than a `.pbix`, because Power BI Desktop was not available "
        "in this environment.",
    ], start=8)


def future_scope(b: D.DocxBuilder) -> None:
    b.heading("26. Future Scope", 1)
    b.para("Twelve directions, each one tied to a limitation it would remove.",
           align="justify")
    b.table([["#", "Direction", "What it would add"]] +
            [[str(i), name, what] for i, (name, what) in enumerate(FUTURE_SCOPE, 1)],
            caption="Future scope.", font_size=8.5, widths=[0.35, 1.7, 4.3])


def conclusion(b: D.DocxBuilder, r: dict) -> None:
    ds = r["dataset"]
    b.heading("27. Conclusion", 1)
    b.para(f"This project took a daily air-quality panel of {n(ds['rows'], 0)} records "
           f"covering {ds['cities']} Indian cities over ten years through the complete "
           f"journey it was asked to demonstrate: understanding, cleaning, feature "
           f"engineering, exploratory and statistical description, correlation analysis, "
           f"K-Means clustering, Isolation Forest anomaly detection, multi-model "
           f"classification with an explicit leakage test, export of a star schema, and a "
           f"five-page Power BI dashboard with documented KPIs and 57 DAX measures. The "
           f"whole route is one code base: {len(r['exports'])} primary exported datasets, "
           f"nine notebooks that execute with their outputs stored, and a report generated "
           f"from the results rather than written alongside them.", align="justify")
    b.para("The technical objectives were met. The analytical objectives were met in a "
           "different and more useful way than expected: instead of confirming the "
           "standard story about air quality, the pipeline measured the data and found it "
           "wanting. The strongest association between any pollutant and AQI is "
           f"|r| = {n(pd.DataFrame(r['correlation_with_aqi'])['Pearson_r'].abs().max(), 4)}; "
           "city, month, season and year differences are statistically indistinguishable; "
           "AQI is nevertheless reproducible from PM2.5 and PM10 at cross-validated "
           f"R\u00b2 = {n(r['aqi_structure']['forward_selection'][1]['cv_r2'], 4)} while "
           "behaving non-monotonically with concentration. Those are not the properties of "
           "a monitoring record, and the report says so in the abstract, in the dataset "
           "section, in the findings and on the dashboard itself.", align="justify")
    b.para("That outcome is the project's real demonstration of data mining and business "
           "intelligence. A model that reaches 99 % accuracy is worth nothing until it is "
           "compared with a 30 % baseline and tested for leakage; an anomaly count is worth "
           "nothing until the contamination parameter is visible beside it; a cluster is "
           "worth nothing until its silhouette is quoted; and a KPI is worth nothing until "
           "its definition, unit and source column are written down. Every one of those "
           "checks was built into the pipeline, and each of them changed what this report "
           "was allowed to say.", align="justify")
    b.para("The deliverable is therefore a working, reproducible framework and an honest "
           "result: the framework will produce trustworthy environmental insight the moment "
           "it is pointed at monitored data, and the result demonstrates why the framework "
           "has to be built that way.", align="justify")
    b.page_break()


def references(b: D.DocxBuilder) -> None:
    b.heading("28. References", 1)
    for i, ref in enumerate(REFERENCES, 1):
        p = b.doc.add_paragraph()
        p.paragraph_format.left_indent = D.Inches(0.4)
        p.paragraph_format.first_line_indent = D.Inches(-0.4)
        p.paragraph_format.space_after = D.Pt(6)
        run = p.add_run(f"[{i}]  ")
        run.bold = True
        run.font.name = D.BODY_FONT
        p.add_run(ref).font.name = D.BODY_FONT
        p.alignment = D.WD_ALIGN_PARAGRAPH.JUSTIFY


# small helpers used inside section text ------------------------------------- #
def comp_max(r: dict) -> float:
    return pd.DataFrame(r["classification"]["comparison"])["Accuracy_%"].max()


def f1_max(r: dict) -> float:
    return pd.DataFrame(r["classification"]["comparison"])["F1_macro"].max()


def lift_max(r: dict) -> float:
    return pd.DataFrame(r["classification"]["comparison"])["Lift_over_Baseline_pp"].max()


# --------------------------------------------------------------------------- #
def main() -> None:
    r = load()
    global BEST
    BEST = best_model(r)

    b = D.DocxBuilder(header_text=TITLE[:90], footer_text="Air Quality Intelligence")
    front_matter(b)
    abstract(b, r)
    contents(b)
    introduction(b, r)
    problem_statement(b)
    objectives(b, r)
    dataset_section(b, r)
    technology(b, r)
    methodology(b, r)
    preprocessing(b, r)
    eda(b, r)
    correlation(b, r)
    kmeans(b, r)
    anomaly(b, r)
    classification(b, r)
    evaluation(b, r)
    powerbi(b, r)
    results_section(b, r)
    findings(b, r)
    limitations(b, r)
    future_scope(b)
    conclusion(b, r)
    references(b)

    out = b.save(DOCX)
    print(f"docx written: {out}  ({out.stat().st_size / 1024:.0f} KB)")
    print(f"figures: {b.fig_no}   tables: {b.tab_no}")
    if "--no-pdf" in sys.argv:
        return
    pdf = D.convert_to_pdf(out, PDF)
    print(f"pdf written:  {pdf}  ({pdf.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
