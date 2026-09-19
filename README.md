# Air Quality & Pollution Intelligence
### An Integrated Data Mining and Business Intelligence Dashboard

A daily air-quality panel of **18,265 observations** (5 Indian cities, 2015-2024) taken
through the complete analytics journey: understanding, cleaning, feature engineering,
exploratory and statistical analysis, correlation, **K-Means clustering**, **Isolation
Forest anomaly detection**, **four classifiers with an explicit leakage test**, a
**star-schema Power BI design with 67 DAX measures**, a 28-section academic report and a
17-slide presentation - all generated from one code base.

Every number in this README, the report, the slides and the dashboard comes from
`data/processed/results.json`, which the pipeline writes. Nothing here is typed in by
hand. Where the evidence is weak, the artefacts say so instead of claiming a finding.

---

## 1. Overview

Air-quality data mixes three different kinds of object in one table: measured pollutant
concentrations, an index (AQI) computed from them, and a category label (`AQI_Bucket`)
derived from that index. Treating all three as independent evidence is the most common
error in projects like this one. This project therefore treats the distinction as a
design constraint: AQI is excluded from every classifier, the leakage that including it
would cause is measured rather than asserted, and the derived target is checked against
the published CPCB band table before that table is used anywhere else (100 % agreement
with the labels in the file).

The deliverables are deliberately reproducible: `src/` holds the analysis once, nine
notebooks execute it and store their real outputs, notebook 09 exports the datasets the
dashboard consumes, and `tools/` builds the report and the deck *from* those artefacts.

**The honest headline.** The pipeline works; the supplied file does not behave like a
monitoring record. Pollutant columns are almost uncorrelated with each other and with
AQI, city/month/year differences are statistically indistinguishable, and AQI is
nonetheless reproducible from two columns at cross-validated R² = 0.9588 while rising
*non-monotonically* with concentration. That combination is the signature of a generated
file, so every conclusion is stated as a description of this file rather than as a fact
about Indian air.

## 2. Objectives

Main objective: *to develop an interactive Air Quality and Pollution Intelligence
Dashboard using data mining and business intelligence techniques to analyse pollution
patterns, identify relationships between pollutants, group observations by pollution
profile, detect unusual observations, predict AQI categories and communicate the
results.*

The ten questions the work has to answer:

| # | Question | Answered in |
|---|---|---|
| 1 | Which cities have higher average AQI? | report 16.2, 23; dashboard page 1 |
| 2 | How does AQI change over time? | report 16.3, 17.5; dashboard page 2 |
| 3 | Which pollutants are most strongly associated with AQI? | report 17.1-17.3; dashboard page 3 |
| 4 | How do pollutants correlate with each other? | report 17.4; dashboard page 3 |
| 5 | Are observations naturally grouped into pollution profiles? | report 18; dashboard page 4 |
| 6 | Which observations are unusual? | report 19; dashboard page 4 |
| 7 | Can AQI categories be predicted from pollutant measurements? | report 20-21; dashboard page 4 |
| 8 | Which months or seasons are dirtier? | report 16.4; dashboard page 2 |
| 9 | How do pollution profiles differ between cities? | report 18.3, 23; dashboard page 5 |
| 10 | What can be communicated through a BI dashboard? | report 22-24; `dashboard/` |

## 3. Dataset

| Property | Value |
|---|---|
| File | `data/raw/Air_quality_data.csv` (also accepts `city_day.csv`) |
| Shape | 18,265 rows x 13 columns - one row per city per day |
| Cities | Bangalore, Chennai, Delhi, Kolkata, Mumbai |
| Period | 2015-01-01 to 2024-12-31 - 3,653 dates x 5 cities = 18,265 rows, a complete balanced panel with no missing city-days |
| Pollutants | PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2, O3 (units as supplied) |
| Target | `AQI` (0-500 index) and `AQI_Bucket` (6 CPCB categories) |
| Missing values / duplicates | 0 / 0 |
| Expected but absent | Benzene, Toluene, Xylene; also station, source and weather columns |
| Provenance | **undocumented** - the file ships with no publisher, download date or collection method |

Class balance is severely skewed: Very Poor 5,501 (30.12 %), Severe 5,258 (28.79 %),
Moderate 4,258 (23.31 %), Poor 3,129 (17.13 %), Satisfactory 113 (0.62 %), Good 6
(0.03 %). Per-class scores for the two rarest classes are reported as indicative only.

## 4. Technologies

| Layer | Tools |
|---|---|
| Language / runtime | Python 3.11.9 (venv), Windows PowerShell |
| Data handling | pandas 3.0.6, NumPy 2.4.6, openpyxl |
| Statistics | SciPy 1.17.1 - Shapiro, Kolmogorov-Smirnov, ANOVA, Kruskal-Wallis, chi-square, linear trend |
| Machine learning | scikit-learn 1.9.1 - KMeans, IsolationForest, PCA, LogisticRegression, DecisionTree, RandomForest, HistGradientBoosting |
| Visualisation | matplotlib 3.11.2, seaborn |
| Notebooks | Jupyter / Notebook 7, executed headlessly with nbclient |
| Document generation | python-docx, python-pptx, XlsxWriter, pywin32 (Word exports the report to PDF and computes its fields) |
| Business intelligence | Microsoft Power BI Desktop, DAX, star schema |

## 5. Project Architecture

```
data/raw/Air_quality_data.csv
        |
        v  src/preprocessing.py      cleaning + 43 logged checks + band verification
        v  src/feature_engineering.py 24 catalogued features (calendar, ratios, index, lag/rolling)
        v  src/statistics_analysis.py descriptive stats, group tests, integrity probes
        v  src/clustering.py | anomaly_detection.py | classification.py
        v  src/reporting.py          summaries + insight list
        +-> data/processed/*.csv     11 primary exports (40-column fact table + dimensions)
        +-> visualizations/**/*.png  28 figures
        +-> data/processed/results.json   single source of every quoted number
        |
        +-> tools/build_report.py        -> report/*.docx + *.pdf   (28 sections, 66 pages)
        +-> tools/build_presentation.py  -> presentation/*.pptx     (17 slides)
        +-> dashboard/DAX_measures.dax + POWER_BI_BUILD_GUIDE.md   -> Power BI (.pbix built by the user)
```

Nine notebooks (`notebooks/01-09`) execute that route in order and store their outputs;
notebook 09 writes the exported datasets and the methodology diagram.

## 6. Data Mining Techniques

| Family | Technique | Settings used | Result on this data |
|---|---|---|---|
| Unsupervised | K-Means on 9 standardized pollutants | K swept 2-10, `random_state=42` | K = 2, silhouette **0.0838** (scored on a 6,000-row sample; weak separation, reported as weak); elbow rule suggested K = 4 - the disagreement is reported, not resolved silently |
| Unsupervised | PCA | 2 components, 22.9 % of variance | illustration only - never used for scoring |
| Outlier detection | Isolation Forest | 300 trees, contamination 0.05 | 914 flagged (5.00 %); the share follows the parameter, so it is an assumed sensitivity, not an observed anomaly rate |
| Supervised | Logistic Regression, Decision Tree, Random Forest, Hist Gradient Boosting | stratified 75/25 split (13,698 train / 4,567 test), 3-fold CV, no sampling, `class_weight='balanced'` | Random Forest best: 99.28 % accuracy, macro-F1 0.7765, CV 99.17 % vs a 30.11 % prior baseline |
| Leakage audit | same model with/without the derived column | AQI added back as a feature | +0.68 pp accuracy inflation; AQI excluded from every reported model |
| Significance testing | ANOVA, Kruskal-Wallis, chi-square, OLS trend | alpha = 0.05 | City p = 0.983, Month p = 0.861, Season p = 0.676, weekend p = 0.162, trend p = 0.900 - nothing is significant |
| Structure probe | greedy forward selection + monotonicity | DecisionTree CV R² | AQI recovered from PM2.5 + PM10 at R² = 0.9588, non-monotonic; linear R² only 0.0579 against tree R² 0.9969 |

## 7. Dashboard Pages

Designed as a star schema - `FACT_AirQuality` (40 columns, 18,265 rows) with
`DIM_Date` (3,653), `DIM_City` (5) and `DIM_Bucket` (6); model, cluster and insight
tables are deliberately left unrelated so they cannot filter the fact table.
**67 DAX measures** in `dashboard/DAX_measures.dax`; every KPI documented with its
definition, measure, unit and source column in `dashboard/KPI_DEFINITIONS.md`.

| # | Page | Purpose |
|---|---|---|
| 1 | Executive Overview | AQI KPIs, trend, city ranking, category share, gauge |
| 2 | Trend & Seasonality | monthly and yearly lines, season comparison, weekday/weekend, rolling average |
| 3 | Pollutant Relationship | heatmap, scatter with trend, pollutant selector, AQI-vs-pollutant correlation table |
| 4 | Anomaly & Clusters | cluster profiles, anomaly KPIs and timeline, model comparison table |
| 5 | City Comparison | city cards and ranking, per-city radar, excess-over-baseline table, insight list |

## 8. Installation

```powershell
# 1. get the code
git clone <your-fork-url>
cd "Air Quality"

# 2. isolated environment (Python 3.11+ recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`pywin32` is optional and Windows-only: it lets `tools/build_report.py` drive Microsoft
Word to compute the table of contents and export the PDF. Without it the `.docx` is still
written; open it in Word and press `Ctrl+A`, `F9` to paginate.

**Power BI Desktop** is a separate free download (<https://powerbi.microsoft.com>). It is
needed only to render the dashboard; nothing in Python depends on it.

## 9. How to Run

```powershell
python tools\inspect_raw.py                 # what is actually in the file
python src\pipeline.py                      # full analysis -> data/processed/ + results.json

python tools\build_notebooks.py             # generate the 9 notebooks
python tools\run_notebooks.py               # execute them headlessly, storing real outputs
python tools\run_notebooks.py 07 08 09 --timeout 5400   # re-run a subset

python tools\build_report.py                # report .docx + .pdf from results.json
python tools\verify_report.py --pdf         # read the .docx back and check its structure
python tools\build_presentation.py          # 17-slide deck from the same results
python tools\verify_presentation.py         # check slide order, notes and timings
```

To build the dashboard: create the three dimension tables and the fact table from
`data/processed/*.csv` (the `_Measures` table too), paste
`dashboard/DAX_measures.dax`, then follow `dashboard/POWER_BI_BUILD_GUIDE.md` step by
step - it names every field, visual, format string and interaction for all five pages.

Useful checks already wired into the notebooks:

```python
from sklearn.tree import DecisionTreeRegressor
tree = DecisionTreeRegressor(max_depth=6, random_state=42).fit(X_pollutants, aqi)
# tree CV R2 = 0.9969 vs linear R2 = 0.0579 -> the relationship is not linear
```

## 10. Results

| Metric | Value | Artefact |
|---|---|---|
| Rows removed by cleaning | 0 (no duplicates, no missing values) | `data_quality_report.csv` |
| Cleaning checks logged | 43 | `cleaning_log.csv` |
| AQI band table vs stored labels | 100 % agreement | notebook 02 |
| Columns: raw / cleaned / exported fact table | 13 / 22 / 40 | `data_quality_report.csv`, `air_quality_cleaned.csv` |
| Clusters | K = 2, sizes 9,112 and 9,153, silhouette 0.0838 | `cluster_profile.csv` |
| Anomalies | 914 (5.00 %) at contamination 0.05 | `anomaly_results.csv` |
| Best classifier | Random Forest, 99.28 % accuracy, macro-F1 0.7765 | `model_comparison.csv` |
| Baseline and lift | 30.11 % prior baseline, +69.17 pp | `model_comparison.csv` |
| Leakage inflation from AQI | +0.68 pp (99.96 % with, 99.28 % without) | `leakage_check.json` |
| Strongest pollutant-AQI correlation | PM10, r = 0.2296 (weak); 3 of 9 significant | `correlation_with_aqi.csv` |
| City / month / trend significance | p = 0.983 / 0.861 / 0.900 - none | `group_comparison_tests.csv` |
| AQI reconstruction from PM2.5 + PM10 | CV R² = 0.9588, non-monotonic | `aqi_structure_probe.csv` |
| Insights generated | 20 (17 `measured`, 3 `interpretation`) | `insights.csv` |
| Report / deck | 28 sections, 66 pages, 45 tables, 28 figures / 17 slides, ~14 min | `report/`, `presentation/` |

Read the two rows with the smallest numbers first: a "99 % accurate" classifier whose
target is a deterministic band of one column, and a strongest correlation of r = 0.23,
together say the interesting result here is the *structure of the file*, not the air.

## 11. Project Structure

```
Air Quality/
├── data/
│   ├── raw/Air_quality_data.csv          input, never modified in place
│   └── processed/                        43 CSVs: fact table, dimensions, every result table,
│                                         results.json (the single source of quoted numbers)
├── notebooks/                            01 understanding ... 09 export, executed with outputs stored
├── src/                                  13 reusable modules - no notebook-to-notebook copying
│   ├── config.py                         paths, schema, AQI bands, model parameters
│   ├── data_utils.py                     loading, profiling, band table, band_from_aqi()
│   ├── preprocessing.py                  cleaning; every rule logs its effect
│   ├── feature_engineering.py            calendar, ratios, Pollution_Index, lag/rolling
│   ├── statistics_analysis.py            descriptive + significance + integrity tests
│   ├── clustering.py                     standardize, K selection, silhouette, PCA
│   ├── anomaly_detection.py              Isolation Forest + grouped comparisons
│   ├── classification.py                 models, CV, confusion, metrics, leakage test
│   ├── reporting.py                        summaries and evidence-backed insight rows
│   ├── figures.py / viz.py               all 28 charts, units on every axis
│   ├── pipeline.py                       runs the whole route, writes results.json
│   └── docx_builder.py                   headings, captions, SEQ fields, TOC, Word->PDF
├── visualizations/                       eda(12) correlation(3) clustering(4) anomaly(4)
│                                          classification(4) methodology(1)
├── dashboard/                            DAX_measures.dax (67) POWER_BI_BUILD_GUIDE.md
│                                          KPI_DEFINITIONS.md
├── report/                               28-section .docx + .pdf, Implementation_Walkthrough.md
│                                          (STEP 1-19), Viva_Questions_Answers.md (54 Q&A)
├── presentation/Air_Quality_Intelligence.pptx   17 slides with speaker notes and timings
├── tools/                                14 scripts: build, run, verify, probe, smoke-test
├── requirements.txt                        versioned, with the tested versions annotated
└── .gitignore
```

## 12. Screenshots

The 28 generated charts in `visualizations/` are the project's figure set and are
embedded in the report; open these four first:

| Figure | What it shows |
|---|---|
| `visualizations/eda/01_aqi_distribution.png` | AQI is flat across its range, not right-skewed as real air-quality data would be |
| `visualizations/correlation/01_correlation_heatmap.png` | the pollutant block carries almost no shared variance |
| `visualizations/clustering/01_elbow_silhouette.png` | elbow and silhouette disagree, and the silhouette is weak |
| `visualizations/classification/02_confusion_matrices.png` | the near-diagonal error pattern a deterministic band produces, on the leakage-free nine-pollutant feature set |
| `visualizations/methodology/01_methodology_diagram.png` | the 13-stage route with the artefact that evidences each stage |

Dashboard screenshots are taken after the five pages are built in Power BI Desktop
(the `.pbix` is not committed here: Power BI Desktop was not available in the environment
this project was built in, so the dashboard is delivered as a fully specified build -
data, DAX, guide and KPI documentation).

## 13. Future Scope

Data first: real-time CPCB/OpenAQ ingestion, more cities and station-level rows,
satellite aerosol, and the meteorological variables that explain day-to-day
concentration. Then modelling: forecasting on a genuinely autocorrelated series,
sequence models, anomaly detection validated against known episode records instead of a
chosen contamination rate, and SHAP-based explanations. Then delivery: live and mobile
Power BI with scheduled refresh, automated public alerts, and geospatial visuals once
coordinates exist. Replacing this file with a documented monitoring record is the first
item on the list, because every conclusion here is bounded by it - the same code runs
against real data unchanged.

## 14. Authors

| Role | Name |
|---|---|
| Student | `<STUDENT NAME>` (`<ENROLMENT / ROLL NUMBER>`) |
| Programme | `<B.Tech / M.Sc. PROGRAMME, e.g. Computer Science & Engineering>` |
| Institute | `<INSTITUTION NAME>`, `<DEPARTMENT NAME>` |
| Project guide | `<PROJECT GUIDE NAME AND DESIGNATION>` |
| Academic year | `<YYYY-YYYY>` |

Fill the same placeholders in `tools/build_report.py` (`STUDENT = {...}`) and
`tools/build_presentation.py` (`STUDENT = {...}`) and re-run the two builders, so the
report, the deck and this README agree. No real names were invented for this project.

## 15. Notes on academic integrity

- Results are computed, never transcribed: `tools/verify_report.py` fails the build if any
  number is missing and the placeholder text `n/a` reaches the document.
- The dataset's provenance is undocumented and its statistical properties are consistent
  with a synthetic panel; this is stated in the abstract, the limitations section, the
  slides and the dashboard rather than being dropped.
- Negative results are reported as negative: no detectable city, month or year effect, no
  ten-year trend, no strong clustering.
- Figures are flat 2-D charts with units and sample sizes on every axis; no 3-D effects,
  no truncated axes, no colour without meaning.
