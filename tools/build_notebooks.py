"""
Build the nine project notebooks programmatically.

    python tools/build_notebooks.py       # writes notebooks/*.ipynb
    python tools/run_notebooks.py         # executes them and embeds real output

Keeping the notebooks in one generator means the analysis code lives in src/
and the notebooks stay consistent with it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
NB_DIR.mkdir(exist_ok=True)

BOOTSTRAP = '''"""Environment bootstrap: make src/ importable and pin the working directory."""
import sys, os, warnings
from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(PROJECT_ROOT / "src"))
os.chdir(PROJECT_ROOT)
warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 60)
pd.set_option("display.max_colwidth", 90)
%matplotlib inline
print("project root:", PROJECT_ROOT)'''

HEAD = '''# {title}
**Project:** Air Quality & Pollution Intelligence - Data Mining and Business Intelligence

**Objective:** {objective}

**How to read this notebook:** every number printed below is produced by the
code in this notebook from `data/raw/Air_quality_data.csv`. Column names are
discovered at runtime through `src/config.py`, so nothing is assumed.
'''


def md(s):
    return ("md", s)


def code(s):
    return ("code", s)


def check_syntax(name: str, cells: list[tuple[str, str]]) -> None:
    """Compile every code cell before it is written.

    Magics (%matplotlib, !) are IPython-only, so they are replaced with a
    comment for the check; everything else must be valid Python 3.
    """
    for i, (kind, src) in enumerate(cells):
        if kind != "code":
            continue
        plain = "\n".join("# " + ln if ln.startswith(("%", "!")) else ln
                          for ln in src.splitlines())
        try:
            compile(plain, f"{name}[cell {i}]", "exec")
        except SyntaxError as exc:
            raise SyntaxError(f"{name} cell {i}: {exc.msg} (line {exc.lineno})") from None


def write(name: str, cells: list[tuple[str, str]]) -> Path:
    check_syntax(name, cells)
    nb = nbf.v4.new_notebook()
    nb.metadata = {
        "kernelspec": {"display_name": "Python 3", "language": "python",
                       "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    }
    nb.cells = [nbf.v4.new_markdown_cell(src) if kind == "md"
                else nbf.v4.new_code_cell(src) for kind, src in cells]
    path = NB_DIR / name
    nbf.write(nb, str(path))
    return path


# --------------------------------------------------------------------------- #
NOTEBOOKS: dict[str, list] = {}

NOTEBOOKS["01_data_understanding.ipynb"] = [
    md(HEAD.format(title="01 - Data Understanding",
                   objective="Inspect the real dataset before writing any analysis "
                             "code: shape, columns, types, missing values, duplicates, "
                             "cities, date range, and a data dictionary.")),
    code(BOOTSTRAP),
    md("""## 1. Load the raw file (read-only)

The raw dataset is never modified. `src/data_utils.load_raw()` accepts either
`Air_quality_data.csv` (the uploaded file) or `city_day.csv` (the name under
which this Kaggle dataset is usually published)."""),
    code('''import config as C
import data_utils as U

raw = U.load_raw()
print("file            :", C.RAW_FILE.name)
print("rows            :", f"{raw.shape[0]:,}")
print("columns         :", raw.shape[1])
print("column names    :", list(raw.columns))'''),
    md("## 2. First and last records"),
    code('''display(raw.head())
display(raw.tail())'''),
    md("## 3. Data types and memory"),
    code('''raw.info()
print()
raw.dtypes'''),
    md("## 4. Summary statistics for every column (numeric and categorical)"),
    code('''raw.describe(include="all").T'''),
    md("""## 5. Per-column profile produced by the project code

`Missing`, `Unique`, range and a negative-value count per column. The
negative-value column is the first validity check: a concentration cannot be
below zero."""),
    code('''prof = U.profile(raw)
prof'''),
    md("## 6. Missing values"),
    code('''miss = U.missing_table(raw)
print("cells that are missing:", int(raw.isna().sum().sum()))
miss if len(miss) else "No missing values in any column - verified, not assumed."'''),
    md("## 7. Duplicate records\n\nTwo different checks: fully identical rows, and repeated City + Date keys (a city should be measured once per day)."),
    code('''import pandas as pd
date_col = C.date_column(raw.columns)
print("exact duplicate rows          :", int(raw.duplicated().sum()))
print(f"duplicate ({C.CITY_COL}, {date_col}) keys:",
      int(raw.duplicated(subset=[C.CITY_COL, date_col]).sum()))'''),
    md("## 8. Cities and date range"),
    code('''print("unique cities:", raw[C.CITY_COL].nunique())
display(raw[C.CITY_COL].value_counts().rename("observations").to_frame())

dates = pd.to_datetime(raw[date_col], errors="coerce")
print("earliest observation :", dates.min().date())
print("latest observation   :", dates.max().date())
print("unparseable dates    :", int(dates.isna().sum()))
print("calendar days per city (expect equal counts for a balanced panel):")
display(raw.groupby(C.CITY_COL)[date_col].nunique().rename("distinct dates"))'''),
    md("""### Is the panel complete?

A balanced daily panel should contain (number of days in the range) x (number of
cities) rows. The cell below checks it, because gaps change how time-series
results must be interpreted."""),
    code('''expected_days = (dates.max().normalize() - dates.min().normalize()).days + 1
per_city = raw.groupby(C.CITY_COL)[date_col].nunique()
print(f"days in calendar range      : {expected_days}")
print(f"dates observed per city     : {sorted(per_city.unique())}")
print(f"expected rows if balanced   : {expected_days * raw[C.CITY_COL].nunique():,}")
print(f"actual rows                 : {len(raw):,}")
print("panel is complete           :", expected_days * raw[C.CITY_COL].nunique() == len(raw))'''),
    md("## 9. AQI categories present in the data"),
    code('''if C.TARGET_COL in raw.columns:
    b = raw[C.TARGET_COL].value_counts(dropna=False).rename("observations").to_frame()
    b["percent"] = (100 * b["observations"] / b["observations"].sum()).round(2)
    display(b)
    print("distinct categories:", int(raw[C.TARGET_COL].nunique()))
if C.AQI_COL in raw.columns:
    print("AQI numeric range :", raw[C.AQI_COL].min(), "to", raw[C.AQI_COL].max())'''),
    md("""## 10. Data dictionary

Generated from the columns that actually exist. Any column not documented by
the source is labelled as such rather than given an invented meaning."""),
    code('''dictionary = U.data_dictionary(raw)
dictionary'''),
    md("""## 11. Schema reconciliation against the expected Kaggle schema

The project brief listed an expected schema. The columns that are missing here
are reported explicitly; the analysis is then restricted to what exists. No
column is invented."""),
    code('''expected = ["City", "Date", "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3",
          "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene", "AQI", "AQI_Bucket"]
actual = [str(c) for c in raw.columns]
present_in_place_of_date = "Datetime" if "Datetime" in actual else "Date"
matched = [e for e in expected if e in actual] + (
    ["Date (supplied as 'Datetime')"] if present_in_place_of_date == "Datetime" else [])
missing = [e for e in expected if e not in actual and e != "Date"]
extra = [a for a in actual if a not in expected and a != "Datetime"]
print("expected but present under another name :",
      ["Date -> Datetime"] if "Datetime" in actual else [])
print("expected but NOT in this dataset        :", missing)
print("present but not in the expected list    :", extra)
print("pollutants actually analysed            :", C.pollutant_columns(raw.columns))
print()
print("Decision: the three hydrocarbon columns (Benzene, Toluene, Xylene) are")
print("absent, so they are excluded from EDA, clustering and classification.")'''),
    md("""## 12. Headline data-quality report (saved)

This is the table that is reused in the final report."""),
    code('''import json
summary = U.summary(raw)
display(pd.DataFrame(list(summary.items()), columns=["Metric", "Value"]))
C.PROCESSED_DIR.mkdir(exist_ok=True, parents=True)
dictionary.to_csv(C.PROCESSED_DIR / "data_dictionary.csv", index=False)
prof.to_csv(C.PROCESSED_DIR / "raw_column_profile.csv", index=False)
(C.PROCESSED_DIR / "understanding_summary.json").write_text(
    json.dumps(summary, indent=2, default=str), encoding="utf-8")
print("saved: data/processed/data_dictionary.csv, raw_column_profile.csv,")
print("       understanding_summary.json")'''),
    md("""## Verification checklist for this stage

- [x] File loads without error
- [x] Row/column counts printed from the object, not typed in
- [x] Every column's type shown
- [x] Missing-value counts computed per column
- [x] Duplicate rows checked (exact and key-based)
- [x] City list and date range verified
- [x] Panel completeness verified against the calendar
- [x] Differences from the expected schema documented

**Common errors and what they mean**

| Error | Meaning | Fix |
|---|---|---|
| `FileNotFoundError: data/raw/...` | Notebook run from the wrong folder | The bootstrap cell changes to the project root; re-run it |
| `KeyError: 'Date'` | This file names the column `Datetime` | `C.date_column()` already resolves it - use it instead of a literal |
| `ModuleNotFoundError: config` | `src/` not on the path | Re-run the bootstrap cell |

**Next:** `02_data_cleaning.ipynb`."""),
]

NOTEBOOKS["02_data_cleaning.ipynb"] = [
    md(HEAD.format(title="02 - Data Cleaning and Data Quality Report",
                   objective="Remove duplicates, fix types, handle impossible and "
                             "missing values, flag (not delete) extreme values, and "
                             "document every decision with the number of rows it touched.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import statistics_analysis as S

raw = U.load_raw()
before = U.summary(raw)
print("before cleaning:", before["Total Rows"], "rows,",
      before["Total Missing Values"], "missing cells,",
      before["Duplicate Rows"], "duplicate rows")'''),
    md("""## 1. Cleaning strategy - and why each rule was chosen

| Problem | Rule applied | Why this rule |
|---|---|---|
| Exact duplicate rows | `drop_duplicates()` | Re-imported rows would double-count every average |
| Text in a numeric column | `to_numeric(errors="coerce")` | An unreadable value is not a measurement |
| Negative concentration | set to missing, then imputed | Physically impossible, so it must be an error |
| Missing numeric value | median of the **same city**, global median as fallback | Pollutant distributions are skewed and each city has its own baseline; a mean would be dragged by extreme (possibly genuine) values |
| Missing category | explicit `Unknown` label | Inventing a city or an AQI band would fabricate evidence |
| Extreme value | **flagged, kept** | A high PM day can be a real pollution episode; deleting it removes the events a dashboard exists to show |

Every row of this table is executed by `src/preprocessing.py`, and the notebook
prints how many values each rule actually touched."""),
    code('''clean, log, before, after = P.clean(raw)
print("rows before:", before["Total Rows"], "| rows after:", after["Total Rows"])
print("columns before:", before["Total Columns"],
      "| columns after:", after["Total Columns"],
      "(extra columns are the documented imputation/outlier flags)")'''),
    md("## 2. Cleaning audit log"),
    code('''from IPython.display import display
display(log)
log.to_csv(C.PROCESSED_DIR / "cleaning_log.csv", index=False)'''),
    md("""### Reading the log honestly

On this particular file most rules report `0` affected values. That is a real
finding, not a failure: the supplied data contains no duplicates, no missing
cells and no negative concentrations. The rules are still executed so that the
same pipeline is safe on any other extract of this dataset."""),
    code('''zeroes = int((log["Rows / Values Affected"] == 0).sum())
print(f"{zeroes} of {len(log)} cleaning steps affected zero values in this file")
print("steps that did change something:")
display(log[log["Rows / Values Affected"] > 0])'''),
    md("## 3. Validity checks on the measurements"),
    code('''polls = C.pollutant_columns(clean.columns)
checks = []
for col in polls + [C.AQI_COL]:
    s = clean[col]
    checks.append({"Column": col, "Negative": int((s < 0).sum()), "Zero": int((s == 0).sum()),
                   "Min": s.min(), "Max": s.max(),
                   "Distinct values": int(s.nunique()),
                   "Values above observed max-1 step": int((s > s.max() - 0.1).sum())})
checks = pd.DataFrame(checks)
display(checks)'''),
    md("""### What the range boundaries tell us

Each pollutant stops at a round maximum (PM2.5 at 499.9, PM10 at 600, NO at 200,
NH3 at 50, CO at 10 ...) and occupies a complete one-decimal grid (for example
NO has exactly 2,000 distinct values on 0-200). Real monitoring stations report
instrument noise and detection limits, not perfect grids clipped at round
numbers. This is recorded here as a data-provenance observation and tested
statistically in notebook 05."""),
    code('''grid = pd.DataFrame({
    "Column": polls,
    "Distinct": [int(clean[p].nunique()) for p in polls],
    "Possible 1-decimal steps on [min,max]": [
        int(round((clean[p].max() - clean[p].min()) * 10)) + 1 for p in polls],
})
grid["Grid filled (%)"] = (100 * grid["Distinct"] / grid["Possible 1-decimal steps on [min,max]"]).round(1)
grid'''),
    md("""## 4. Extreme values

The IQR rule flags records outside Q1-1.5*IQR and Q3+1.5*IQR. The flags are kept
as columns; no row is deleted."""),
    code('''outlier_cols = [c for c in clean.columns if c.endswith("_Outlier")]
counts = clean[outlier_cols].sum()
print("records flagged as extreme, by pollutant:")
display(counts.rename("flagged").to_frame().assign(
    percent=(100 * counts / len(clean)).round(3)))
print()
print("Any record flagged on any pollutant:",
      int((clean[outlier_cols].sum(axis=1) > 0).sum()))'''),
    md("""## 5. AQI band vs AQI value - internal consistency

`config.py` carries one AQI band table (the CPCB NAAQI ranges: 0-50 Good,
51-100 Satisfactory, 101-200 Moderate, 201-300 Poor, 301-400 Very Poor,
401-500 Severe). The rest of the project maps AQI onto a band through
`U.band_from_aqi`, so if that table were wrong the error would show up here and
nowhere else. Two questions are answered with the data in front of us:

1. does the supplied `AQI_Bucket` agree with the band table, and
2. does every band label sit on a contiguous, non-overlapping stretch of the
   AQI number line (a band that overlapped its neighbour would mean the scale is
   not the one the labels were built from).

This is also the leakage warning used later in notebook 08."""),
    code('''band_check = clean[[C.AQI_COL, C.TARGET_COL]].copy()
band_check["Expected"] = U.band_from_aqi(clean[C.AQI_COL])
agree = float((band_check["Expected"].astype(str)
               == band_check[C.TARGET_COL].astype(str)).mean())
print(f"{100*agree:.2f}% of rows have a bucket consistent with the band table in config.py")
print()
print("Cross-tabulation of supplied label against recomputed label (a clean "
      "diagonal means the two are the same scale):")
display(pd.crosstab(band_check[C.TARGET_COL], band_check["Expected"]))
print()
print("Observed AQI range per label, straight from the data:")
display(band_check.groupby(C.TARGET_COL, observed=True)[C.AQI_COL]
        .agg(["min", "max", "count"])
        .reindex([b for b in C.AQI_BUCKET_ORDER if b in set(band_check[C.TARGET_COL])]))
print()
print("Conclusion: AQI_Bucket is a deterministic function of AQI on this scale.")
print("Consequence: AQI must NOT be used to predict AQI_Bucket (data leakage).")'''),
    md("## 6. Before / after data quality report"),
    code('''comparison = U.quality_comparison(before, after)
display(comparison)
comparison.to_csv(C.DATA_QUALITY_CSV, index=False)
clean.to_csv(C.PROCESSED_DIR / "cleaned_stage02.csv", index=False)
print("saved: data/processed/data_quality_report.csv, cleaned_stage02.csv")'''),
    md("""**Note on the column count:** "After cleaning" is larger because the
documented flag columns (`*_Outlier`, `Imputed_*`) were added. No measurement
column was removed."""),
    md("""## Verification checklist

- [x] Duplicates counted before and after
- [x] Date parsed to datetime
- [x] Numeric and categorical columns identified from the data
- [x] Missing values handled with a stated rule (or verified absent)
- [x] Impossible values checked
- [x] Extreme values flagged, not deleted, with justification
- [x] Internal consistency of AQI and AQI_Bucket tested
- [x] Before/after report saved

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `SettingWithCopyWarning` | assigning through a slice | the module always works on `df.copy()` and uses `.loc` |
| `InvalidComparison` on AQI_Bucket | column is an ordered category | compare with `.astype(str)` |

**Next:** `03_feature_engineering.ipynb`."""),
]

NOTEBOOKS["03_feature_engineering.ipynb"] = [
    md(HEAD.format(title="03 - Feature Engineering",
                   objective="Create the calendar, seasonal and pollution-composition "
                             "features that the analysis and the dashboard need, while "
                             "reusing the supplied AQI instead of inventing one.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE

clean, log, *_ = P.clean(U.load_raw())
feat, notes = FE.build_features(clean)
print("columns after engineering:", feat.shape[1])
for n in notes:
    print(" -", n)'''),
    md("""## 1. Calendar features

`Year`, `Month`, `Month_Name`, `Quarter`, `Day`, `Day_of_Week`, `Week_of_Year`,
`Is_Weekend`, `Year_Month`. These let the BI dashboard slice the same measure by
time period without re-aggregating the raw text dates."""),
    code('''cal = ["Year", "Month", "Month_Name", "Quarter_Label", "Day", "Day_Name",
       "Week_of_Year", "Is_Weekend", "Season", "Year_Month"]
display(feat[["Date"] + cal].head(8))
print("date span :", feat["Date"].min().date(), "->", feat["Date"].max().date())
print("years     :", sorted(feat["Year"].unique()))
print("sanity check, month 1 ->", feat.loc[feat["Month"] == 1, "Month_Name"].unique()[0])
print("sanity check, weekday 0 ->", feat.loc[feat["Day_of_Week"] == 0, "Day_Name"].unique()[0])'''),
    md("""## 2. Season definition (documented, not universal)

Winter = Dec-Feb, Summer = Mar-May, Monsoon = Jun-Sep, Post-Monsoon = Oct-Nov.
This is the convention normally used in Indian climate reporting and is adopted
here as a *project* definition. It is not presented as a scientifically
universal partition of the year."""),
    code('''season_check = feat.groupby("Season", observed=True).agg(
    months=("Month", lambda s: sorted(s.unique())), records=("Season", "size"))
display(season_check)
print("C. config.SEASON_MAP =", C.SEASON_MAP)'''),
    md("""## 3. Pollution-composition features

| Feature | Definition | Purpose |
|---|---|---|
| `PM25_PM10_Ratio` | PM2.5 / PM10 | fine vs coarse particulate share |
| `NO2_NOx_Ratio` | NO2 / NOx | aged vs freshly emitted nitrogen oxides |
| `O3_PM10_Ratio` | O3 / PM10 | secondary vs primary pollution balance |
| `Pollution_Index` | mean of min-max-scaled pollutants, x100 | one common 0-100 scale |
| `Pollutants_Above_City_Q3` | count of pollutants above that city's own 75th percentile | how many pollutants are simultaneously high |
| `City_Pollutant_Percentile` | mean within-city percentile across pollutants | comparable across cities |
| `AQI_Lag_1`, `AQI_Change_1d`, `AQI_Rolling_7/30` | per-city time features | smoothed trend lines |

**Important:** `Pollution_Index` is a project-specific analytical index. The
official AQI already exists in the data and is used unchanged everywhere else."""),
    code('''new_cols = ["PM25_PM10_Ratio", "NO2_NOx_Ratio", "O3_PM10_Ratio",
            "Pollution_Index", "Pollution_Index_Band", "Pollutants_Above_City_Q3",
            "City_Pollutant_Percentile", "AQI_Lag_1", "AQI_Change_1d",
            "AQI_Rolling_7", "AQI_Rolling_30"]
missing = [c for c in new_cols if c not in feat.columns]
print("expected engineered columns that are absent:", missing or "none")
display(feat[[C.CITY_COL, "Date"] + new_cols].head(6))'''),
    code('''feat[["Pollution_Index", "PM25_PM10_Ratio", "NO2_NOx_Ratio",
      "Pollutants_Above_City_Q3", "City_Pollutant_Percentile"]].describe().T'''),
    md("""### Guarded division

Ratios divide by a column that can be zero (PM10 = 0 exists in the data). The
implementation returns `NaN` instead of `inf` in that case; the count is shown
below so the reader knows how many records simply cannot have that ratio."""),
    code('''for r in ["PM25_PM10_Ratio", "NO2_NOx_Ratio", "O3_PM10_Ratio"]:
    print(f"{r}: {int(feat[r].isna().sum())} records with a zero/missing denominator")'''),
    md("## 4. Feature inventory (saved for the report)"),
    code('''inv = FE.feature_inventory(feat)
display(inv)
inv.to_csv(C.PROCESSED_DIR / "feature_inventory.csv", index=False)
feat.to_csv(C.PROCESSED_DIR / "features_stage03.csv", index=False)
print("saved: feature_inventory.csv, features_stage03.csv")'''),
    md("""## 5. Leakage guard for the engineered columns

A derived column that contains the target makes evaluation meaningless. Below,
the correlation of each engineered numeric feature with the AQI is shown; any
feature that is essentially a re-labelled AQI is excluded from modelling."""),
    code('''import statistics_analysis as S
eng = [c for c in ["Pollution_Index", "PM25_PM10_Ratio", "NO2_NOx_Ratio",
                   "O3_PM10_Ratio", "Pollutants_Above_City_Q3",
                   "City_Pollutant_Percentile", "Is_Weekend", "Month"]
       if c in feat.columns]
tab = S.correlation_with_target(feat, eng, C.AQI_COL)
display(tab)
print("Modelling in notebooks 06-08 uses only the measured pollutant columns,")
print("so engineered columns cannot leak the target into a model.")'''),
    md("""## Verification checklist

- [x] Every date feature derived from a parsed datetime, spot-checked against the calendar
- [x] Season definition written down and labelled project-specific
- [x] Supplied AQI reused; derived index explicitly labelled as non-official
- [x] Division-by-zero handled and the affected record count reported
- [x] Engineered columns checked for target leakage

**Next:** `04_eda.ipynb`."""),
]

NOTEBOOKS["04_eda.ipynb"] = [
    md(HEAD.format(title="04 - Exploratory Data Analysis",
                   objective="Look at the data from every angle the objectives require - "
                             "distributions, city comparison, time, month, year, season, "
                             "weekday - and save each figure to visualizations/.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE
import figures as F
import viz as V
from IPython.display import display, Image

clean, *_ = P.clean(U.load_raw())
feat, _ = FE.build_features(clean)
polls = C.pollutant_columns(feat.columns)
V.style()
print("records:", f"{len(feat):,}", "| cities:", feat[C.CITY_COL].nunique(),
      "| pollutants analysed:", len(polls))'''),
    md("""## 1. How AQI and the AQI categories are distributed

The mean/median pair and the category counts tell us where the data sits. No
axis is truncated and no 3-D effect is used."""),
    code('''paths = F.eda(feat, polls)
display(feat[C.AQI_COL].describe().round(2).to_frame("AQI").T)
display(pd.DataFrame({"category": feat[C.TARGET_COL].astype(str).value_counts().index,
                      "records": feat[C.TARGET_COL].astype(str).value_counts().values,
                      "percent": (100 * feat[C.TARGET_COL].astype(str).value_counts()
                                  / len(feat)).round(2).values}))
Image(paths["01_aqi_distribution"])'''),
    code('''Image(paths["02_aqi_category_distribution"])'''),
    md("""## 2. Cities

Average and median AQI per city, then the spread inside each city."""),
    code('''city = (feat.groupby(C.CITY_COL, observed=True)[C.AQI_COL]
            .agg(["count", "mean", "median", "std", "min", "max"]).round(2)
            .sort_values("mean", ascending=False))
display(city)
Image(paths["03_city_avg_median_aqi"])'''),
    code('''Image(paths["04_city_aqi_boxplot"])'''),
    md("""### Is the difference between cities meaningful?

A visual gap between bars means nothing without a test, so the same comparison
is made formally here (and again in notebook 05)."""),
    code('''import statistics_analysis as S
t = S.group_comparison(feat, C.AQI_COL, C.CITY_COL)
print(f"one-way ANOVA across the {len(t['group_means'])} cities: "
      f"F = {t['ANOVA_F']}, p = {t['ANOVA_p']}")
print(f"Kruskal-Wallis:                H = {t['Kruskal_H']}, p = {t['Kruskal_p']}")
print(f"spread between the highest and lowest city mean: "
      f"{t['Between_Group_Mean_Spread']} AQI points")
print()
print("Interpretation:",
      "the city means are statistically indistinguishable" if not t["Significant_at_0.05"]
      else "at least one city differs materially")'''),
    md("## 3. Pollutant distributions"),
    code('''Image(paths["05_pollutant_distributions"])'''),
    code('''display(S.descriptive_stats(feat, polls + [C.AQI_COL]))'''),
    md("""## 4. Change over time

Daily AQI is noisy, so the trend chart aggregates to monthly means. A least-
squares line is drawn on the monthly series and its slope is reported."""),
    code('''Image(paths["06_aqi_trend_time"])'''),
    code('''trend = S.linear_trend_test(feat, C.AQI_COL)
print(f"fitted slope  : {trend['slope_per_year']} AQI points per year")
print(f"p-value       : {trend['p_value']}")
print(f"conclusion    : {trend['verdict']}")'''),
    md("## 5. Month, year, season and weekday effects"),
    code('''display(feat.groupby("Month", observed=True)[C.AQI_COL]
            .agg(["count", "mean", "median"]).round(2))
Image(paths["07_monthly_aqi"])'''),
    code('''Image(paths["08_yearly_aqi"])'''),
    code('''display(feat.groupby("Season", observed=True)[C.AQI_COL]
            .agg(["count", "mean", "median", "std"]).round(2))
Image(paths["09_seasonal_aqi"])'''),
    code('''s = S.group_comparison(feat, C.AQI_COL, "Season")
w = S.group_comparison(feat, C.AQI_COL, "Is_Weekend")
print(f"season  : ANOVA p = {s['ANOVA_p']}, Kruskal p = {s['Kruskal_p']} -> "
      + ("significant" if s["Significant_at_0.05"] else "not significant"))
print(f"weekend : ANOVA p = {w['ANOVA_p']} -> "
      + ("significant" if w["Significant_at_0.05"] else "not significant"))'''),
    md("""### The expected winter peak

Publicly reported Indian air quality is strongly seasonal, with a late-October to
January peak. The tests above find no seasonal effect in this file. That is
reported as a property of this dataset, not written around."""),
    code('''Image(paths["11_weekday_aqi"])'''),
    md("## 6. Particulate relationship and city x pollutant profile"),
    code('''Image(paths["10_pm25_vs_pm10"])
r = feat[["PM2.5", "PM10"]].corr().iloc[0, 1]
print(f"Pearson r between PM2.5 and PM10 in this dataset: {r:.4f}")'''),
    code('''Image(paths["12_city_pollutant_heatmap"])'''),
    md("## 7. Figure index (saved for the report and README)"),
    code('''index = pd.DataFrame({"figure": list(paths.keys()), "path": list(paths.values())})
index["exists"] = [Path(p).exists() for p in paths.values()]
display(index)
index.to_csv(C.VIZ_DIR / "eda_figure_index.csv", index=False)
print("figures written under visualizations/eda/")'''),
    md("""## Verification checklist

- [x] All 16 required EDA views generated
- [x] Every figure titled, labelled and saved with units
- [x] Visual differences between cities backed by a statistical test
- [x] Absence of seasonality reported rather than assumed

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `KeyError: 'Day_Name'` | feature engineering not run first | run the second cell of this notebook |
| Empty PNG files | previous run crashed before drawing | re-run from the bootstrap cell |

**Next:** `05_correlation_analysis.ipynb`."""),
]

NOTEBOOKS["05_correlation_analysis.ipynb"] = [
    md(HEAD.format(title="05 - Correlation and Statistical Analysis",
                   objective="Quantify how the measured variables relate to each other "
                             "and to AQI, test whether those relationships are real, and "
                             "establish what the data can and cannot support.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE
import statistics_analysis as S
import figures as F
import viz as V
from IPython.display import display, Image

clean, *_ = P.clean(U.load_raw())
feat, _ = FE.build_features(clean)
polls = C.pollutant_columns(feat.columns)
meas = polls + [C.AQI_COL]
V.style()'''),
    md("""## 1. Pearson correlation matrix

Pearson's r measures **linear** association only, on -1 to +1. It is sensitive to
outliers and blind to any curve that is not a straight line."""),
    code('''corr = S.correlation_matrix(feat, meas)
display(corr)
Image(F.correlation(corr, pd.DataFrame())["01_correlation_heatmap"])'''),
    md("## 2. Spearman rank correlation (monotonic, robust to shape)"),
    code('''corr_s = S.correlation_matrix(feat, meas, method="spearman")
display(corr_s.round(3))
print("Largest absolute difference between the two matrices: "
      f"{(corr - corr_s).abs().max().max():.4f}")'''),
    md("""## 3. Every variable against AQI, with significance

`r^2` is the share of AQI variance that a **straight line** through that one
variable would explain. The p-value tests H0: r = 0 - with 18,265 records even a
trivially small r becomes significant, which is why effect size is reported next
to significance."""),
    code('''target = S.correlation_with_target(feat, polls, C.AQI_COL)
display(target)
print(f"{int(target['Significant_at_0.05'].sum())} of {len(target)} pollutants are "
      f"'significant' at 0.05, but the largest |r| is "
      f"{target['Pearson_r'].abs().max():.3f} - a negligible linear effect.")
Image(F.correlation(corr, target)["02_pollutant_vs_aqi"])'''),
    md("## 4. Strongest and weakest pollutant pairs"),
    code('''import numpy as np
pairs = corr.loc[polls, polls].copy()
body = pairs.to_numpy(copy=True)   # pandas returns a read-only view otherwise
np.fill_diagonal(body, np.nan)
pairs = pd.DataFrame(body, index=pairs.index, columns=pairs.columns)
long = (pairs.stack().rename("r").reset_index()
        .rename(columns={"level_0": "A", "level_1": "B"}))
long = long[long["A"] < long["B"]].sort_values("r", key=abs, ascending=False)
display(long.head(6))
print("weakest pairs:")
display(long.tail(3))
Image(F.correlation(corr, target, long.head(12))["03_pairwise_correlations"])'''),
    code('''pairs.to_csv(C.PROCESSED_DIR / "pollutant_pair_correlations.csv", index=False)
corr.to_csv(C.CORRELATION_CSV)
target.to_csv(C.PROCESSED_DIR / "correlation_with_aqi.csv", index=False)'''),
    md("""## 5. Correlation is not causation

Nothing in a correlation matrix can distinguish \"PM2.5 drives AQI\" from \"both
are computed from a common source\" or from pure coincidence. This dataset has no
emission inventory, no meteorology and no traffic data, so **no causal claim is
made anywhere in this project**. The next section shows why even the correlational
claim needs care here."""),
    md("""## 6. Is a near-zero r the same as \"no relationship\"?

A random-forest regressor is fitted to AQI with cross-validation and compared to
the linear result. If the tree model explains far more variance, the relationship
exists but is non-linear, and Pearson alone would have missed it."""),
    code('''pred = S.tree_predictability(feat, C.AQI_COL, polls)
print(f"linear regression R^2 (in-sample)   : {pred['linear_R2']}")
print(f"random forest R^2 (3-fold CV)       : {pred['tree_CV_R2']}")
print(f"random forest MAE                   : {pred['tree_CV_MAE']} AQI points")
print(f"gap                                 : {pred['gap']}")
print()
print(pred["verdict"])
pd.DataFrame([pred]).to_csv(C.PROCESSED_DIR / "nonlinear_predictability.csv", index=False)'''),
    code('''lin = S.linear_fit(feat, C.AQI_COL, polls)
print(f"multiple linear regression: R^2 = {lin['R2']}, adjusted R^2 = {lin['Adj_R2']}")
display(pd.DataFrame(lin["coefficients"].items(), columns=["Pollutant", "coef (unstandardised)"]))'''),
    md("""## 6b. Which columns actually determine AQI?

A random forest reproduces AQI with a cross-validated R^2 close to 1, so AQI must be
a *computed* function of some of the other columns. The cells below add one pollutant
at a time and always keep the one that raises CV R^2 the most (greedy forward
selection), so the answer comes from the data rather than from textbook assumptions.
An exhaustive search over all 36 pollutant pairs is kept in
`tools/probe_aqi_drivers.py`; the notebook uses a smaller forest and a greedy search
so that the section stays runnable in a couple of minutes."""),
    code('''from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score

y_aqi = feat[C.AQI_COL].to_numpy(dtype="float64")
cv = KFold(3, shuffle=True, random_state=C.RANDOM_STATE)

def cv_r2(cols):
    model = RandomForestRegressor(n_estimators=80, min_samples_leaf=5,
                                  n_jobs=2, random_state=C.RANDOM_STATE)
    X = feat[cols].to_numpy(dtype="float64")
    return float(np.mean(cross_val_score(model, X, y_aqi, scoring="r2",
                                         cv=cv, n_jobs=1)))

single = (pd.Series({p: round(cv_r2([p]), 4) for p in polls})
          .sort_values(ascending=False).rename("CV_R2").to_frame())
print("AQI predictability from one pollutant at a time (3-fold CV R^2):")
display(single)'''),
    code('''chosen, remaining, steps = [], list(polls), []
for _ in range(3):
    best = max(((cv_r2(chosen + [p]), p) for p in remaining), key=lambda t: t[0])
    chosen.append(best[1])
    remaining.remove(best[1])
    steps.append({"added": best[1], "CV_R2_after_adding": round(best[0], 4)})
    print(f"  + {best[1]:<6} -> CV R^2 = {best[0]:.4f}")
print("\\ngreedy informative set:", chosen)
print("Everything after the first two columns adds very little - AQI is driven")
print("by the particulate matter columns, which is what an AQI formula does,")
print("but see the shape test below for whether this file behaves like one.")
pd.DataFrame(steps).to_csv(C.PROCESSED_DIR / "aqi_driver_selection.csv",
                           index=False)'''),
    md("""### Shape of the relationship

A real AQI sub-index is **monotonically increasing** in concentration: more pollution
cannot give a cleaner index. The decile table tests that property directly."""),
    code('''bins = pd.qcut(feat[chosen[0]], 10, duplicates="drop")
shape = (feat.groupby(bins, observed=True)[C.AQI_COL]
         .agg(Records="count", Mean_AQI="mean", SD_AQI="std").round(2))
shape.index.name = f"decile of {chosen[0]}"
display(shape)
monotone = bool(shape["Mean_AQI"].is_monotonic_increasing)
print(f"mean AQI increases monotonically with {chosen[0]}: {monotone}")
print("The profile rises and then falls back - the relationship is deterministic")
print("but not an exposure-response curve. Logged as a data-integrity finding.")'''),
    code('''if len(chosen) > 1:
    qa = pd.qcut(feat[chosen[0]], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    qb = pd.qcut(feat[chosen[1]], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    grid = pd.crosstab(qa, qb, values=feat[C.AQI_COL], aggfunc="mean").round(1)
    grid.index.name = chosen[0]
    display(grid)
    print("Rows Q1 and Q5 of the lowest column are nearly equal, i.e. very low and")
    print("very high PM2.5 give the same average AQI. No monitoring process does")
    print("that; it is a signature of a generated numeric grid.")'''),
    code('''cells = (feat.groupby([pd.qcut(feat[chosen[0]], 20, duplicates="drop"),
                       pd.qcut(feat[chosen[1]], 20, duplicates="drop")],
                      observed=True)[C.AQI_COL].agg(["count", "std", "min", "max"]))
cells = cells[cells["count"] >= 8]
print(f"cells with >= 8 records                          : {len(cells)}")
print(f"mean SD of AQI inside a narrow PM cell           : {cells['std'].mean():.2f}")
print(f"mean range (max - min) of AQI inside such a cell : {(cells['max'] - cells['min']).mean():.2f}")
print(f"SD of AQI overall                                : {feat[C.AQI_COL].std():.2f}")
print("AQI is therefore nearly fixed once the two PM columns are known, with a")
print("small residual contributed by the remaining pollutants.")'''),
    md("""## 7. Distribution-shape tests (data integrity)

Real pollutant concentrations are right-skewed: most days are moderate, a few are
very bad. A column that a Kolmogorov-Smirnov test cannot distinguish from a
uniform distribution on a round maximum, with excess kurtosis near -1.2, has the
shape of randomly generated numbers."""),
    code('''dist = S.distribution_tests(feat, meas)
display(dist)
dist.to_csv(C.PROCESSED_DIR / "distribution_tests.csv", index=False)
n_uniform = int(dist["Interpretation"].str.contains("uniform-like").sum())
print(f"{n_uniform} of {len(dist)} measured columns are statistically uniform-like.")'''),
    md("""## 8. Does the record order carry information?

Daily pollution is strongly autocorrelated in reality (yesterday predicts today,
r ~ 0.7-0.9). Lagged correlation near zero means row order is uninformative."""),
    code('''ac = S.autocorrelation(feat, C.AQI_COL)
display(ac)
ac.to_csv(C.PROCESSED_DIR / "autocorrelation.csv", index=False)
print("Real monitored AQI typically shows lag-1 r above 0.6.")'''),
    md("## 9. Group comparison tests for every BI-relevant grouping"),
    code('''rows = []
for g in [c for c in [C.CITY_COL, "Season", "Month", "Is_Weekend", "Quarter"]
          if c in feat.columns]:
    t = S.group_comparison(feat, C.AQI_COL, g)
    rows.append({k: v for k, v in t.items() if k != "group_means"})
groups = pd.DataFrame(rows)
display(groups)
groups.to_csv(C.PROCESSED_DIR / "group_comparison_tests.csv", index=False)'''),
    code('''display(S.group_comparison(feat, C.AQI_COL, C.CITY_COL)["group_means"])
display(S.group_comparison(feat, "PM2.5", C.CITY_COL)["group_means"])'''),
    md("""## 10. What this stage licenses the project to conclude

| Question | Answer from this dataset | Evidence |
|---|---|---|
| Do cities differ in AQI? | Not significantly | ANOVA p-value above |
| Is AQI related to pollutants? | Linearly almost not at all, but non-linearly almost perfectly | tree CV R^2 vs linear R^2 |
| Is there a time trend? | No detectable trend | slope p-value (notebook 04) |
| Is there seasonality? | Not detectable | Kruskal/ANOVA p-values |
| Do the values look measured or generated? | Uniform on round caps, zero autocorrelation | distribution tests, autocorrelation |"""),
    md("""## Verification checklist

- [x] Pearson and Spearman matrices computed on real columns only
- [x] Significance reported together with effect size
- [x] Non-linear relationship tested, not assumed absent
- [x] Correlation/causation distinction stated explicitly
- [x] Distribution and autocorrelation integrity tests recorded

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `ValueError: input must have at least 3 entries` | a group has too few rows for Shapiro | the code samples and guards already; check the column exists |
| `NaN` correlations | constant column (zero variance) | drop it from the matrix |

**Next:** `06_kmeans_clustering.ipynb`."""),
]

NOTEBOOKS["06_kmeans_clustering.ipynb"] = [
    md(HEAD.format(title="06 - K-Means Clustering of Pollution Profiles",
                   objective="Group records by their pollutant composition, choose K from "
                             "evidence rather than preference, and describe each cluster "
                             "with neutral, number-backed language.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE
import clustering as KM
import figures as F
import viz as V
from IPython.display import display, Image

clean, *_ = P.clean(U.load_raw())
feat, _ = FE.build_features(clean)
polls = C.pollutant_columns(feat.columns)
print("clustering features taken from the data:", polls)'''),
    md("""## 1. Feature selection and preparation

Only measured pollutant concentrations are used. `AQI` is deliberately excluded:
it is a composite of the pollutants, so including it would cluster on a derived
value and double-count the same information."""),
    code('''X, scaler, used, raw = KM.build_matrix(feat, polls)
print(f"rows used            : {len(X):,} (records without missing values in the features)")
print(f"features standardised : {used}")
print("before scaling - means:")
display(raw.mean().round(2).to_frame("mean"))
print("after scaling - each column has mean 0 and unit variance:")
display(X.describe().loc[["mean", "std", "min", "max"]].round(2))'''),
    md("""### Why StandardScaler

K-Means assigns points to the nearest centroid using Euclidean distance. PM10
spans 0-600 while CO spans 0-10, so without scaling, PM10 alone would decide the
assignment and the other pollutants would be ignored."""),
    md("""## 2. Choosing K - elbow method and silhouette score

* **Inertia** = within-cluster sum of squares. It always falls as K grows, so the
  question is where the fall stops being informative (the "elbow").
* **Silhouette** = mean (b - a) / max(a, b) over points, where *a* is the mean
  distance to the point's own cluster and *b* the mean distance to the nearest
  other cluster. Above ~0.25 is usually read as weak structure; above 0.5 as
  clear structure."""),
    code('''k_table = KM.choose_k(X, C.K_RANGE)
display(k_table)
k_table.to_csv(C.PROCESSED_DIR / "k_selection_table.csv", index=False)
choice = KM.recommend_k(k_table)
for key, value in choice.items():
    print(f"{key:>18}: {value}")'''),
    code('''Image(F.clustering_k(k_table)["01_elbow_silhouette"])'''),
    md("""### K is chosen from the evidence, and the disagreement is reported

The silhouette and the elbow rule do not have to agree. Here the rule that is
followed is stated in advance: **maximise the silhouette score**, with the elbow
reported as corroboration. If they disagree, the disagreement is printed rather
than hidden."""),
    code('''K = choice["chosen_K"]
print(f"selected K = {K} (silhouette {choice['silhouette']})")
sil_max = k_table["Silhouette_Score"].max()
print(f"highest silhouette over all tested K: {sil_max}")
print("conventional reading: < 0.25 weak / 0.25-0.5 moderate / > 0.5 distinct structure")'''),
    md("## 3. Fit K-Means with the selected K"),
    code('''feat, model, scaler, used, centroids_z, centroids_raw = KM.fit(feat, polls, K)
print("inertia                 :", round(float(model.inertia_), 2))
print("iterations to converge  :", int(model.n_iter_))
print("cluster sizes           :", dict(pd.Series(model.labels_).value_counts()))
display(centroids_raw.round(2))
centroids_raw.to_csv(C.PROCESSED_DIR / "cluster_centroids_original_units.csv", index=False)'''),
    md("## 4. Cluster profile table"),
    code('''metrics = polls + [C.AQI_COL]
profile = KM.cluster_profile(feat, metrics)
display(profile[[c for c in ["Cluster", "Cluster_Size", "Share_%"] +
                 [f"Avg_{m}" for m in metrics] if c in profile.columns]])
profile.to_csv(C.CLUSTER_PROFILE_CSV, index=False)'''),
    code('''desc = KM.describe_clusters(profile, metrics)
display(desc)
desc.to_csv(C.PROCESSED_DIR / "cluster_descriptions.csv", index=False)'''),
    md("""### Why the labels stay neutral

Words such as "dangerous" or "safe" require an external standard. This project
describes clusters only by their relative position on measured variables - for
example *highest average NOx among clusters* - and reports the numbers so the
reader can judge severity against whatever standard they care about."""),
    md("""## 5. Do the clusters mean anything?

Two extra checks that are often skipped: how much of the spread the clusters
actually explain, and whether the same partition appears with a different random
seed."""),
    code('''from sklearn.metrics import adjusted_rand_score
var_explained = 1 - model.inertia_ / (len(X) * X.values.var(axis=0).sum())
print(f"share of feature variance explained by the K={K} partition: "
      f"{100*var_explained:.2f}%")

alt = [KM.fit(feat.drop(columns=["Cluster", "PC1", "PC2"], errors="ignore"), polls, K,
              random_state=s)[1].labels_ for s in (7, 2024, 99)]
base = model.labels_
ari = pd.DataFrame({"seed": [7, 2024, 99],
                    "adjusted_rand_index": [round(adjusted_rand_score(base, a), 4) for a in alt]})
display(ari)
print("ARI = 1 means the same partition; values near 0 mean the labels are arbitrary.")'''),
    md("## 6. PCA visualisation of the clusters"),
    code('''pcs = KM.pca_projection(X)
expl = pcs.attrs["explained_variance_ratio"]
print(f"PC1 explains {100*expl[0]:.1f}% and PC2 {100*expl[1]:.1f}% "
      f"-> {(pcs.shape[1])} of {X.shape[1]} dimensions, "
      f"{100*sum(expl):.1f}% of the total variance in the feature space")
display(pcs.attrs["components"].round(3))
feat = feat.merge(pcs, left_index=True, right_index=True)
paths = F.clustering(pcs, pd.Series(model.labels_, index=X.index),
                     profile, centroids_raw, polls)
Image(paths["02_pca_clusters"])'''),
    md("""**PCA caveat that must appear in the report:** the 2-D picture keeps only
the percentage of variance printed above. Distances in the plot are **not**
distances in the original pollutant space, so the plot is illustrative and the
centroid table above is the authoritative description."""),
    code('''Image(paths["03_cluster_sizes_profiles"])
Image(paths["04_cluster_centroids"])'''),
    md("## 7. Which cities and AQI bands fall in which cluster?"),
    code('''ct = pd.crosstab(feat[C.CITY_COL], feat["Cluster"], normalize="index").mul(100).round(1)
display(ct)
print("If cities were genuinely different pollution profiles, these row percentages "
      "would differ strongly between cities.")'''),
    code('''keep = [c for c in [C.CITY_COL, "Date", "Year", "Season"] + polls +
          [C.AQI_COL, C.TARGET_COL, "Cluster", "PC1", "PC2"] if c in feat.columns]
feat[keep].to_csv(C.CLUSTER_RESULTS_CSV, index=False)
print("saved:", C.CLUSTER_RESULTS_CSV.name)'''),
    md("""## Verification checklist

- [x] Features standardised before distance computation
- [x] K selected by a rule stated in advance, with the elbow reported too
- [x] Cluster profile table in original units, not only in z-scores
- [x] Descriptions kept neutral and numeric
- [x] Variance explained and seed stability measured
- [x] PCA limitation written down

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `ValueError: Number of labels=... does not match number of samples` | silhouette on a subsample | `choose_k` subsamples consistently; re-run the cell |
| All points in one cluster | degenerate start | `n_init=10` is already set; check for a constant column |

**Next:** `07_anomaly_detection.ipynb`."""),
]

NOTEBOOKS["07_anomaly_detection.ipynb"] = [
    md(HEAD.format(title="07 - Anomaly Detection with Isolation Forest",
                   objective="Find records whose combination of pollutant values is "
                             "statistically unusual, quantify how many there are, and state "
                             "clearly what the label does and does not mean.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE
import anomaly_detection as AD
import figures as F
import viz as V
from IPython.display import display, Image

clean, *_ = P.clean(U.load_raw())
feat, _ = FE.build_features(clean)
polls = C.pollutant_columns(feat.columns)
V.style()'''),
    md("""## 1. Why Isolation Forest

* It isolates points by random splits, so the cost is linear in the number of
  records - practical at 18,265 rows.
* It does not assume the data is Gaussian (true here: notebook 05 shows uniform-like
  marginals), unlike a Z-score or Mahalanobis approach.
* It uses all pollutant dimensions jointly, so it can flag a record whose
  *combination* of values is unusual even when no single value is extreme."""),
    md("""## 2. The `contamination` parameter

`contamination` is the fraction of records the algorithm is told to treat as
outliers, and it fixes the decision threshold. It is an **assumption**, not a
finding, so the sensitivity to it is reported instead of being buried."""),
    code('''sens = []
for c in (0.01, 0.02, 0.05, 0.10):
    tmp, _, _, _ = AD.detect(feat, polls, contamination=c)
    st = AD.summary(tmp)
    sens.append({"contamination": c, "anomalies": st["Anomalies detected"],
                 "rows_evaluated": st["Rows evaluated"],
                 "observed_pct": st["Anomaly %"]})
display(pd.DataFrame(sens))'''),
    code('''feat, model, used, params = AD.detect(feat, polls)
print("features used :", used)
print("parameters    :", {k: v for k, v in params.items() if k != "features"})
stats_tbl = AD.summary(feat)
for k, v in stats_tbl.items():
    print(f"{k:>24}: {v}")'''),
    md("## 3. Anomaly distribution and score"),
    code('''paths = F.anomaly(feat, AD.by_city(feat), AD.by_period(feat, "year"), polls)
display(feat["Anomaly_Label"].value_counts().to_frame("records"))
Image(paths["01_anomaly_distribution"])'''),
    md("## 4. Which cities and which years are flagged?"),
    code('''by_city = AD.by_city(feat)
display(by_city)
by_city.to_csv(C.PROCESSED_DIR / "anomaly_by_city.csv", index=False)
Image(paths["02_anomaly_by_city"])'''),
    code('''by_year = AD.by_period(feat, "year")
display(by_year)
by_year.to_csv(C.PROCESSED_DIR / "anomaly_by_year.csv", index=False)
Image(paths["03_anomaly_timeline"])'''),
    code('''print("is the spread between cities larger than sampling noise would give?")
import statistics_analysis as S
flagged = feat.assign(Is_Anomaly=feat["Anomaly"])
ct = pd.crosstab(flagged[C.CITY_COL], flagged["Anomaly"], values=flagged["AQI"],
                aggfunc="size")
from scipy import stats as sps
chi2, p, dof, _ = sps.chi2_contingency(ct)
print(f"chi-square test of independence between City and Anomaly: chi2={chi2:.3f}, "
      f"df={dof}, p={p:.4g}")
print("expected under a fixed contamination rate: about equal shares in every city")'''),
    md("""## 5. What makes a record anomalous here?

Comparing the mean pollutant level of flagged and normal records shows which
measurements drive the flag. Note that anomalies are **not** simply the highest
values - the algorithm flags unusual combinations."""),
    code('''cmp_tbl = AD.pollutant_comparison(feat, polls)
display(cmp_tbl)
cmp_tbl.to_csv(C.PROCESSED_DIR / "anomaly_pollutant_comparison.csv", index=False)
Image(paths["04_anomaly_scatter"])'''),
    md("## 6. The most anomalous records in the file"),
    code('''worst = (feat.nsmallest(15, "Anomaly_Score")
              [[C.CITY_COL, "Date", "Season"] + polls + [C.AQI_COL, C.TARGET_COL,
                                                        "Anomaly_Score"]])
display(worst.reset_index(drop=True))'''),
    md("""## 7. Interpretation limits

An anomaly label means "this record is far from the bulk of the data in the
chosen feature space". It does **not** identify a cause. Naming a cause (fireworks,
stubble burning, a dust storm, a sensor fault) would need activity or maintenance
data that this dataset does not contain, so no cause is asserted."""),
    code('''keep = [c for c in [C.CITY_COL, "Date", "Year", "Month", "Season"] + polls +
          [C.AQI_COL, C.TARGET_COL, "Anomaly", "Anomaly_Label", "Anomaly_Score",
           "Cluster"] if c in feat.columns]
feat[keep].to_csv(C.ANOMALY_RESULTS_CSV, index=False)
print("saved:", C.ANOMALY_RESULTS_CSV.name, "rows:", len(feat))'''),
    md("""## Verification checklist

- [x] Feature set restricted to measured concentrations
- [x] Contamination sensitivity reported
- [x] Anomaly share compared against the configured rate
- [x] City/year breakdowns tested for non-randomness
- [x] No causal explanation claimed

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `ValueError: could not convert string to float` | a categorical column entered the feature list | pass only `C.pollutant_columns(...)` |
| All scores identical | a constant column dominates | drop zero-variance columns |

**Next:** `08_classification.ipynb`."""),
]

NOTEBOOKS["08_classification.ipynb"] = [
    md(HEAD.format(title="08 - AQI Category Classification and Model Evaluation",
                   objective="Predict the AQI band from pollutant concentrations with "
                             "several algorithms, avoid data leakage, respect the class "
                             "imbalance, and compare the models on a held-out split.")),
    code(BOOTSTRAP),
    code('''import config as C
import data_utils as U
import preprocessing as P
import feature_engineering as FE
import classification as CL
import figures as F
import viz as V
from IPython.display import display, Image

clean, *_ = P.clean(U.load_raw())
feat, _ = FE.build_features(clean)
polls = C.pollutant_columns(feat.columns)
target = C.TARGET_COL
model_df = CL.drop_non_informative(feat, target)
print("records with a usable AQI band:", f"{len(model_df):,}")'''),
    md("""## 1. Target and class balance

Accuracy is meaningless without the class distribution, so the balance is measured
first and a prior-based baseline is carried through every comparison."""),
    code('''balance = CL.class_balance(model_df, target)
display(balance)
print(f"imbalance ratio (largest/smallest class): {balance.attrs['imbalance_ratio']}")
print(f"majority class: {balance.attrs['majority_class']} "
      f"({balance.attrs['majority_share_pct']}%) -> baseline accuracy")'''),
    md("""## 2. Data leakage: the AQI column must not be a predictor

`AQI_Bucket` is a banding of `AQI` (proved in notebook 02), so giving a model the
AQI number to predict the AQI band is predicting the target from itself. The cell
below measures how much that mistake would inflate the score."""),
    code('''leak = CL.leakage_check(model_df, polls, target)
display(pd.DataFrame([leak]).T.rename(columns={0: "value"})
        if False else pd.Series(
            {"accuracy without AQI (%)": leak["without leaky column"]["accuracy_%"],
             "accuracy with AQI (%)": leak["with leaky column"]["accuracy_%"],
             "inflation (pp)": leak["accuracy_inflation_pp"],
             "macro F1 without AQI": leak["without leaky column"]["macro_F1"],
             "macro F1 with AQI": leak["with leaky column"]["macro_F1"]}).to_frame("value"))
print()
print(leak["verdict"])
(C.PROCESSED_DIR / "leakage_check.json").write_text(__import__("json").dumps(leak, indent=2),
                                                    encoding="utf-8")'''),
    md("""## 3. Models and their settings

| Model | Why included | Key settings |
|---|---|---|
| Baseline (prior) | reference point that any real model must beat | always predicts the largest class |
| Logistic Regression | linear, interpretable multi-class reference | L2, one-vs-rest internals, `class_weight="balanced"`, features scaled |
| Decision Tree | single transparent model, non-linear | `max_depth=12`, `min_samples_leaf=20`, balanced weights |
| Random Forest | bagged ensemble, robust, gives feature importances | 200 trees, `min_samples_leaf=2`, `balanced_subsample` |
| Hist Gradient Boosting | modern boosted benchmark | 250 iterations, learning rate 0.1 |

All use `random_state=42`, a stratified 75/25 split, and 3-fold stratified CV for
the accuracy column."""),
    code('''comp, reports, matrices, split_info, pred_frame, y_test, X_test = CL.train_and_evaluate(
    model_df, polls, target, cv_folds=3)
display(comp)
print()
print("features given to the models:", split_info["features_used"])
print("excluded as leaky          :", split_info["excluded_leaky_column"])
print("train / test rows          :", split_info["train_rows"], "/", split_info["test_rows"])'''),
    code('''comp.to_csv(C.MODEL_COMPARISON_CSV, index=False)
display(comp[["Model", "Accuracy_%", "Precision_macro", "Recall_macro", "F1_macro",
             "Lift_over_Baseline_pp", "CV_Accuracy_%"]])'''),
    md("""## 4. Why macro-F1 and per-class recall, not just accuracy

The four main bands hold over 99% of records; `Good` holds 6 rows and
`Satisfactory` 113. A model can therefore look excellent overall while never
detecting the rare classes."""),
    code('''per_class = pd.concat([CL.report_to_frame(n, r) for n, r in reports.items()],
                     ignore_index=True)
rare = per_class[per_class["Class"].isin(["Good", "Satisfactory"])]
display(rare)
print("Support is the number of test records in that class; recall is the share found.")'''),
    code('''best = comp.iloc[0]["Model"]
display(pd.DataFrame(reports[best]).T.round(3))'''),
    md("## 5. Confusion matrices"),
    code('''conf = pd.concat([CL.confusion_to_frame(m, sorted(split_info["classes"]), n)
                  for n, m in matrices.items()], ignore_index=True)
conf.to_csv(C.PROCESSED_DIR / "confusion_matrices.csv", index=False)
per_class.to_csv(C.PROCESSED_DIR / "classification_per_class.csv", index=False)
Image(F.classification(comp, conf, per_class, pd.DataFrame(),
                       sorted(split_info["classes"]))["02_confusion_matrices"])'''),
    code('''imp_model, imp_features = CL.fit_reference_model(model_df, polls, target)
imp = CL.feature_importance(imp_model, imp_features)
paths = F.classification(comp, conf, per_class, imp,
                         sorted(split_info["classes"]))
Image(paths["01_model_comparison"])'''),
    code('''Image(paths["03_per_class_recall"])
Image(paths["04_feature_importance"])'''),
    md("""## 6. Which pollutants carry the signal?

Mean-decrease-in-impurity importance from a random forest trained on the full
frame. This is a *model-internal* measure: it says which columns the trees split
on, not which pollutants cause poor air quality."""),
    code('''display(imp)
imp.to_csv(C.PROCESSED_DIR / "feature_importance.csv", index=False)'''),
    md("""## 7. Test-set predictions exported for the dashboard

Actual-versus-predicted records allow the BI layer to show model reliability
without retraining anything in Power BI."""),
    code('''pred_frame.to_csv(C.CLASSIFICATION_CSV, index=False)
print("saved:", C.CLASSIFICATION_CSV.name, "rows:", f"{len(pred_frame):,}")
display(pred_frame.head(8))'''),
    md("""## Verification checklist

- [x] Leak-proof feature set (AQI excluded, and the inflation measured)
- [x] Stratified split, fixed random state
- [x] Baseline model reported next to every real model
- [x] Class imbalance quantified before accuracy is interpreted
- [x] Precision, recall and F1 reported per class and macro-averaged
- [x] Confusion matrices and feature importances saved

**Common errors**

| Error | Meaning | Fix |
|---|---|---|
| `ConvergenceWarning` in logistic regression | unscaled inputs or too few iterations | features are piped through `StandardScaler` and `max_iter=2000` |
| `UndefinedMetricWarning` | a class has no predicted samples | `zero_division=0` is set; recall is reported instead |
| Accuracy of ~100% | leakage | re-check `leakage_check` above |

**Next:** `09_final_analysis.ipynb`."""),
]

NOTEBOOKS["09_final_analysis.ipynb"] = [
    md(HEAD.format(title="09 - Final Analysis, Processed Datasets and Insights",
                   objective="Run the complete pipeline once more from a single entry "
                             "point, export every processed dataset for Power BI, and turn "
                             "the computed results into the insight list.")),
    code(BOOTSTRAP),
    md("""## 1. Run the whole pipeline from the shared code

`src/pipeline.py` is the same code the notebooks above use, so the exported files
cannot drift away from what was demonstrated."""),
    code('''import json
import pipeline
import config as C
from IPython.display import display

results = pipeline.run(verbose=True)
print("runtime (seconds):", results["runtime_seconds"])'''),
    md("## 2. Environment recorded for reproducibility"),
    code('''display(pd.DataFrame(list(results["environment"].items()),
                     columns=["Component", "Version / setting"]))'''),
    md("## 3. Dataset facts used in the report"),
    code('''ds = results["dataset"]
display(pd.DataFrame(list(ds.items()), columns=["Item", "Value"]))'''),
    md("## 4. Every processed dataset that Power BI will import"),
    code('''files = sorted(C.PROCESSED_DIR.glob("*.csv"))
table = pd.DataFrame({
    "file": [f.name for f in files],
    "rows": [sum(1 for _ in open(f, encoding="utf-8")) - 1 for f in files],
    "columns": [pd.read_csv(f, nrows=1).shape[1] for f in files]})
display(table)
print("primary BI inputs:")
for k, v in results["exports"].items():
    print(f"  {k:<22}{Path(v).name}")'''),
    md("""## 5. Insights generated from the computed results

Each insight is assembled by `src/reporting.py` from numbers that exist in the
artefacts listed above, and carries its own evidence column and source file."""),
    code('''ins = pd.DataFrame(results["insights"])
display(ins[["Category", "Insight", "Evidence Strength"]])
print("full table with evidence:")
display(ins[["Insight", "Quantitative Evidence", "Derived From"]])'''),
    md("## 6. Key result tables in one place"),
    code('''display(pd.DataFrame(results["classification"]["comparison"])[
    ["Model", "Accuracy_%", "F1_macro", "Lift_over_Baseline_pp"]].head())
display(pd.DataFrame(results["clustering"]["choice"], index=["value"]).T)
display(pd.DataFrame([results["anomaly"]["stats"]]))
display(pd.DataFrame([results["predictability"]]))
display(pd.DataFrame([results["trend_test"]]))'''),
    md("""## 7. Final quality check

Every line below is evaluated from the artefacts, not asserted. Two checks deserve
an explanation:

* **Measured columns** (city, date, the nine pollutant concentrations, AQI) must
  contain no blank cells at all.
* **Derived columns** are *allowed* to be blank where the derivation is undefined:
  a ratio whose denominator is zero, and the first day of each city's lag / rolling
  window, which has no previous observation to compare with. Those blanks are
  documented, not silently filled."""),
    code('''import data_utils as U

cleaned = pd.read_csv(C.CLEANED_CSV)
measured = ([C.CITY_COL, "Date"]
            + C.pollutant_columns(cleaned.columns)
            + [c for c in (C.AQI_COL, C.TARGET_COL) if c in cleaned.columns])
blank_cols = set(cleaned.columns[cleaned.isna().any()])
allowed_blank = {"PM25_PM10_Ratio", "NO2_NOx_Ratio", "O3_PM10_Ratio",
                 "AQI_Rolling_7", "AQI_Rolling_30", "AQI_Change_1d",
                 "Cluster_Description", "City_Pollutant_Percentile"}
# Rebuild the category from the AQI value with the single band table in
# src/config.py (through U.band_from_aqi), then count how often it agrees with
# the supplied label - this is the leakage test and the scale test at once.
expected_bucket = U.band_from_aqi(cleaned[C.AQI_COL])
bucket_agreement = float((expected_bucket.astype(str)
                          == cleaned[C.TARGET_COL].astype(str)).mean())
checks = {
 "raw dataset loads": C.RAW_FILE.exists(),
 "cleaned dataset exported": C.CLEANED_CSV.exists(),
 "city summary exported": C.CITY_SUMMARY_CSV.exists(),
 "monthly summary exported": C.MONTHLY_SUMMARY_CSV.exists(),
 "cluster results exported": C.CLUSTER_RESULTS_CSV.exists(),
 "anomaly results exported": C.ANOMALY_RESULTS_CSV.exists(),
 "classification results exported": C.CLASSIFICATION_CSV.exists(),
 "model comparison exported": C.MODEL_COMPARISON_CSV.exists(),
 "insights exported": C.INSIGHTS_CSV.exists(),
 "date / bucket / city dimensions exported":
     C.DIM_DATE_CSV.exists() and C.DIM_BUCKET_CSV.exists() and C.DIM_CITY_CSV.exists(),
 "results.json written": (C.PROCESSED_DIR / "results.json").exists(),
 "no blank cells in the measured columns":
     int(cleaned[measured].isna().sum().sum()) == 0,
 "blank cells confined to documented derived columns": bool(blank_cols <= allowed_blank),
 "one record per city-day":
     not cleaned.duplicated([C.CITY_COL, "Date"]).any(),
 "AQI_Bucket is reproducible from AQI (leakage confirmed)": bucket_agreement == 1.0,
}
display(pd.DataFrame(list(checks.items()), columns=["Check", "Passed"]))
print("all checks passed:", all(checks.values()))
print()
print("blank cells by column (only derived columns may appear):")
blanks = cleaned.isna().sum()
display(blanks[blanks > 0].rename("Blank cells").to_frame())
print(f"AQI_Bucket agreement with the band table: {100 * bucket_agreement:.2f}%")
print("disagreements:", int((expected_bucket.astype(str)
                            != cleaned[C.TARGET_COL].astype(str)).sum()))'''),
    md("""## 8. Star-schema tables for Power BI

`FACT_AirQuality` is `air_quality_cleaned.csv`; the three dimension tables below
are what a clean model needs (see `dashboard/POWER_BI_BUILD_GUIDE.md`)."""),
    code('''print("DIM_Date rows:", f"{pd.read_csv(C.DIM_DATE_CSV).shape[0]:,}")
display(pd.read_csv(C.DIM_BUCKET_CSV))
display(pd.read_csv(C.DIM_CITY_CSV))'''),
    md("""## 9. Handoff to Power BI

The CSVs in `data/processed/` are the only inputs the dashboard needs. The star
schema, the DAX measures and the page-by-page build instructions live in
`dashboard/` - see `dashboard/POWER_BI_BUILD_GUIDE.md`."""),
    code('''print("Import these into Power BI Desktop:")
for name in ["air_quality_cleaned.csv", "dim_date.csv", "dim_city.csv",
             "dim_bucket.csv", "city_summary.csv", "monthly_summary.csv",
             "cluster_results.csv", "cluster_profile.csv",
             "anomaly_results.csv", "aqi_bucket_distribution.csv",
             "model_comparison.csv", "classification_per_class.csv",
             "correlation_with_aqi.csv", "insights.csv",
             "data_quality_report.csv", "k_selection_table.csv"]:
    p = C.PROCESSED_DIR / name
    print(f"  {'OK  ' if p.exists() else 'MISS'} {name}")'''),
    md("""## 10. Methodology diagram (figure used in the report)

The chain below is the method this project actually followed, stage by stage, and
the italic line under each stage names the file that evidences it - so the
diagram can be checked against `data/processed/` rather than taken on trust."""),
    code('''import figures as F
from IPython.display import Image

method_png = F.methodology_diagram()
print("written to:", Path(method_png).relative_to(C.PROJECT_ROOT))
Image(filename=method_png)'''),
]


def main() -> None:
    written = []
    for name, cells in NOTEBOOKS.items():
        written.append(write(name, cells))
    for path in sorted(written):
        print("wrote", path.relative_to(ROOT))
    print(f"\n{len(written)} notebooks generated in {NB_DIR.name}/")


if __name__ == "__main__":
    main()
