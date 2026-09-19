# Step-by-Step Implementation Walkthrough

**Nineteen stages, each with the eight items the project brief asks for: objective,
file to create, exact code, explanation, expected output, how to verify, common errors,
and what to do next.**

This is the record of how the repository was built, in the order it was built. The code
blocks are the code that is actually in the files - they are quoted so that a reader can
retype them, not so that they can be skipped. Nothing here assumes a result: every
"expected output" names the artefact that has to exist for the step to count as done, and
where a number is quoted it is the number this dataset produced.

Two conventions used throughout:

* Commands are PowerShell (Windows). On Linux/macOS replace `.venv\Scripts\activate` with
  `source .venv/bin/activate` and `\` with `/`.
* The raw file is opened read-only by design. No step in this walkthrough edits
  `data/raw/Air_quality_data.csv`.

---

## STEP 1 - Environment setup

**1. Objective.** Create the project skeleton and an isolated Python environment, so that
every later step runs on recorded versions instead of whatever happens to be installed.

**2. Folders to create.**

```
data/raw  data/processed  notebooks  src  visualizations  dashboard  report  tools
```

`visualizations/` is created per family (`eda/`, `correlation/`, `clustering/`,
`anomaly/`, `classification/`, `methodology/`) by `src/viz.py::path_for()`, not by hand.

**3. Exact code.**

```powershell
cd "c:\Users\DELL\OneDrive\Desktop\Air Quality"
mkdir data\raw, data\processed, notebooks, src, visualizations, dashboard, report, tools
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

`requirements.txt` pins a floor and records the verified version in a comment:

```
pandas>=2.2            # verified with 3.0.6
scikit-learn>=1.4      # verified with 1.9.1
scipy>=1.11            # verified with 1.17.1
matplotlib>=3.8        # verified with 3.11.2
nbformat>=5.9          # verified with 5.11.1
nbclient>=0.9          # verified with 0.11.0
python-docx>=1.1       # verified with 1.2.0
python-pptx>=1.0       # verified with 1.0.2
pywin32>=306; sys_platform == "win32"   # optional: PDF export of the report
```

**4. Explanation.** `python -m venv` writes a private interpreter so `pip install` cannot
touch the system Python. Activating it puts `.venv\Scripts` first on `PATH`, which is why
`python` and `pip` then refer to the project's own environment. The version floors are
deliberately not exact pins: the analysis code is written against public APIs, and a
`.venv`-local `pip freeze` is available if byte-identical reproduction is ever needed.

**5. Expected output.** A `.venv/` directory, and for every package an installed version
at or above the floor. Nothing else on the machine changes.

**6. How to verify.**

```powershell
python -c "import sys, pandas, sklearn, scipy, matplotlib; print(sys.version); print(pandas.__version__, sklearn.__version__, scipy.__version__, matplotlib.__version__)"
```

This project's run reported `3.11.9` and `3.0.6 / 1.9.1 / 1.17.1 / 3.11.2`, and the same
values are recorded automatically in `data/processed/results.json` under `environment`.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `python : The term 'python' is not recognized` | the venv is not activated | run `.venv\Scripts\activate`, or call `.\.venv\Scripts\python.exe` explicitly |
| `pip install` succeeds but `import sklearn` fails in Jupyter | the notebook kernel is a different interpreter | `python -m ipykernel install --user --name aqi --display-name "Python (AQI)"` from inside the venv, then select it |
| `Execution of script ... disabled because policy` (also seen: `ScriptBlock should only be specified...`) | PowerShell is blocking the venv activation script | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or activate with `. .\venv\Scripts\Activate.ps1` |
| `Microsoft Visual C++ 14.0 is required` during install | a source-only dependency | install the redistributable, or use a 64-bit Python 3.11 wheel set as pinned here |

**8. What to do next.** STEP 2 - put the dataset in `data/raw/`.

---

## STEP 2 - Download and place the dataset

**1. Objective.** Get the air-quality file into the project without modifying it, and make
the code tolerant of the two names this dataset is published under.

**2. File to create.** `data/raw/Air_quality_data.csv` (the supplied file;
`data/raw/city_day.csv` is also accepted).

**3. Exact code.**

```python
# src/config.py
RAW_CANDIDATES = ("Air_quality_data.csv", "city_day.csv")
RAW_FILE = next((RAW_DIR / n for n in RAW_CANDIDATES if (RAW_DIR / n).exists()),
                RAW_DIR / RAW_CANDIDATES[0])
```

**4. Explanation.** The project is pointed at a *candidate list*, not a single filename,
because the Kaggle schema this file follows is usually published as `city_day.csv`.
`RAW_FILE` resolves to whichever exists; if neither does it keeps the first name so that
the error message names a file the reader can create. Nothing reads the CSV through a
hard-coded path - `load_raw()` is the only entry point, which is what keeps the raw file
read-only in practice.

**5. Expected output.** A CSV of 18,265 data rows plus a header row, with 13 columns
including `City`, a date column, nine pollutant columns, `AQI` and `AQI_Bucket`.

**6. How to verify.**

```powershell
Get-Content data\raw\Air_quality_data.csv -TotalCount 1
(Get-Content data\raw\Air_quality_data.csv | Measure-Object -Line).Lines
```

Two lines of output: the header, and `18266` (18,265 records + header). The same check in
Python is `U.summary(U.load_raw())["rows"]`.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `FileNotFoundError: expected one of ... in data\raw` | the file landed elsewhere or kept a `.csv.txt` name | move/rename it to `data/raw/Air_quality_data.csv`; the message prints the directory contents to show what was found |
| Column names differ after download (`Stationity`, no `AQI_Bucket`) | a different variant of the schema | do **not** invent columns. Run notebook 01, read the printed columns, and extend `C.POLLUTANT_CANDIDATES` / `C.DATE_COL_CANDIDATES` so the code adapts to the real file |
| Excel saves a `.xlsx` copy | wrong format | keep the CSV; Excel is not in the pipeline |

**8. What to do next.** STEP 3 - inspect what is actually in the file before writing any
analysis.

---

## STEP 3 - Inspect the dataset (notebook 01)

**1. Objective.** Establish shape, columns, dtypes, missing values, duplicates, cities,
date range and cardinality, and produce a data dictionary - all from the real file.

**2. Files to create.** `src/data_utils.py`, `notebooks/01_data_understanding.ipynb`
(the notebook is generated by `tools/build_notebooks.py` so its code cannot drift from
`src/`).

**3. Exact code.**

```python
import config as C
import data_utils as U

raw = U.load_raw()                 # never edited in place
print("shape:", raw.shape)
display(U.profile(raw))            # dtype, non-null, unique, min/max per column
print("cities :", sorted(raw[C.CITY_COL].unique()))
display(U.missing_table(raw))      # per-column null count and %
display(U.data_dictionary(raw))    # name, type, description, unit, role
```

and the profile function it calls:

```python
# src/data_utils.py
def profile(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for col in df.columns:
        s = df[col]
        numeric = pd.to_numeric(s, errors="coerce")
        rows.append({"Column": col, "Dtype": str(s.dtype),
                     "Non-Null": int(s.notna().sum()),
                     "Null %": round(100 * s.isna().mean(), 2),
                     "Unique": int(s.nunique(dropna=True)),
                     "Min": numeric.min(), "Max": numeric.max()})
    return pd.DataFrame(rows)
```

**4. Explanation.** `pd.to_numeric(..., errors="coerce")` is used so that a text value in
a numeric column shows up as a coercion gap rather than an exception - that is how a
"96" stored as `"96 µg/m³"` would be detected. `Unique` per column is the check that turns
"13 columns" into "13 columns, of which 2 are identifiers, 9 measurements, 1 derived index
and 1 derived label", which is the classification the whole project then hangs on.

**5. Expected output.** `(18265, 13)`; five cities (Bangalore, Chennai, Delhi, Kolkata,
Mumbai); 0 nulls; 0 exact duplicates; `AQI` in 37.7-500.0; nine pollutants each bounded by
a suspiciously round maximum (PM10 to 600.0, CO to 10.0).

**6. How to verify.** Open `notebooks/01_data_understanding.ipynb` and check that the
cells have stored outputs (`[11]:` style prompts, not `[ ]:`), or re-run headless:

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 01
.\.venv\Scripts\python.exe tools\show_outputs.py notebooks\01_data_understanding.ipynb
```

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `KeyError: 'Date'` | this file names the column `Datetime` | already handled: `C.date_column()` picks from `DATE_COL_CANDIDATES`; do not add a fake `Date` column |
| Dtype is `object` for a numeric column | thousands separators or units inside the text | `P.to_numeric()` coerces and logs how many values failed; investigate before imputing |
| `[ ]` prompts in the notebook | cells were never executed | run STEP 3's verification command; a notebook without outputs is not a result |

**8. What to do next.** STEP 4 - cleaning, now that the real schema is documented.

---

## STEP 4 - Data cleaning (notebook 02)

**1. Objective.** Make the table internally consistent - types, duplicates, identifiers,
impossible values, extremes - and log every decision with the number of values it touched.

**2. Files to create.** `src/preprocessing.py`, `notebooks/02_data_cleaning.ipynb`, and on
run: `data/processed/air_quality_cleaned.csv`, `data_quality_report.csv`,
`cleaning_log.csv`, plus the AQI band verification.

**3. Exact code.**

```python
import config as C
import data_utils as U
import preprocessing as P

raw = U.load_raw()
cleaned, log, before, after = P.clean(raw)     # (frame, log, before, after)
display(log)                                   # Step | Action | Rows/Values | Why
display(U.quality_comparison(before, after))
```

The band-consistency test that caught a real defect:

```python
import data_utils as U
band_check = clean[[C.AQI_COL, C.TARGET_COL]].copy()
band_check["Expected"] = U.band_from_aqi(clean[C.AQI_COL])
agree = float((band_check["Expected"].astype(str)
               == band_check[C.TARGET_COL].astype(str)).mean())
print(f"{100*agree:.2f}% of rows have a bucket consistent with the band table")
```

**4. Explanation.** `CleaningLog` is a list-append recorder: each function in
`preprocessing.py` takes the log and writes what it did, so the report is produced by the
code path rather than typed afterwards. `flag_impossible()` tests `value < 0` for
concentrations; `flag_outliers_iqr()` writes boolean columns instead of dropping rows, so
an extreme day stays available to notebook 07. `band_from_aqi()` maps AQI onto a category
through the single band table in `src/config.py` - the whole project uses that one
function, so a wrong boundary fails in one place and visibly.

**5. Expected output.** 43 log rows; 0 duplicates removed; 0 values imputed (no gaps
existed); the crosstab of supplied against recomputed `AQI_Bucket` is a clean diagonal and
`agree == 1.0`. Before the band table was corrected, this same test printed **76.07%** -
which is the point of having it.

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 02
.\.venv\Scripts\python.exe tools\show_outputs.py notebooks\02_data_cleaning.ipynb
```

Then confirm the diagonal directly: the "observed range per label" table must show each
band inside its own CPCB limits (Satisfactory 51-100, Moderate 101-200).

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| Agreement around 76% with Moderate/Satisfactory swapped in the observed ranges | the band table does not match the scale the labels were built on | correct `C.AQI_BUCKET_BANDS` and re-run 02 *and* everything downstream; never patch the labels row by row |
| `SettingWithCopyWarning` | assigning through a slice | `P.clean()` works on an explicit `.copy()` of the raw frame |
| `Date` becomes `1970-01-01` | an int/epoch column parsed as a date | `parse_date()` uses `errors="coerce"` and logs unparseable counts |
| `ValueError: IQR flagging needs numeric columns` | a measure column stayed `object` | fix the coercion first; do not skip the flag step |

**8. What to do next.** STEP 5 - feature engineering on the cleaned frame.

---

## STEP 5 - Feature engineering (notebook 03)

**1. Objective.** Create the derived columns that make the project's questions expressible
- calendar, season, ratios, rolling means, per-city percentiles - while reusing the
supplied AQI instead of inventing a new one.

**2. Files to create.** `src/feature_engineering.py`, `notebooks/03_feature_engineering.ipynb`.

**3. Exact code.**

```python
import feature_engineering as FE

feat, notes = FE.build_features(cleaned)
display(FE.feature_inventory(feat))
for note in notes:
    print("-", note)
```

The guarded division that the "no invented values" rule depends on:

```python
# src/feature_engineering.py
def ratio(name: str, num: str, den: str, scale: float = 1.0):
    if num in out.columns and den in out.columns:
        with np.errstate(divide="ignore", invalid="ignore"):
            out[name] = np.where(out[den] > 0, scale * out[num] / out[den], np.nan)
    else:
        note.append(f"{name} skipped: requires '{num}' and '{den}'")
```

**4. Explanation.** `add_time_features()` derives Year, Month, Month_Name, Season, Day,
Weekday and Is_Weekend from the parsed date - Power BI's time intelligence needs these as
columns, not as formulas. `add_ratio_features()` builds PM2.5/PM10, NO2/NOx and O3/PM10 with a `denominator > 0`
guard, so a zero denominator yields a blank rather than `inf`.
`add_rolling_features()` groups by city before applying the window, because a rolling mean
across city boundaries would mix stations. `add_pollution_index()` and
`add_elevated_counts()` express composition without touching the supplied AQI.

**5. Expected output.** 24 columns in the feature inventory (13 from the file, 11 derived);
rolling and lag columns blank only at the start of each city's window; no new column
introduced into the model feature list without a note explaining why.

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 03
```

then check the blank audit at the end of notebook 09 §7: the columns allowed to contain
blanks are exactly the documented derived ones
(`PM25_PM10_Ratio`, `NO2_NOx_Ratio`, `O3_PM10_Ratio`, `AQI_Rolling_7`, `AQI_Rolling_30`,
`AQI_Change_1d`, `Cluster_Description`, `City_Pollutant_Percentile`).

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `KeyError: 'Month'` in a later notebook | the feature step was skipped or the frame was re-read from disk | notebooks are independent processes: run `03` before `04`, or re-read the exported CSV |
| `inf` in a ratio column | the guard was bypassed by writing `a / b` directly | use `C.safe_div`; `replace(0, np.nan)` is the only correct form here |
| Rolling means wrong for the first rows of each city | window applied across the whole sorted frame | group by `City` first (`groupby(...).rolling(...)`) |
| A derived column silently disappears from `results.json` | it was never added to `feature_inventory()`'s view | keep the inventory and the export list in `pipeline.py` in step with the new column |

**8. What to do next.** STEP 6 - descriptive EDA, which needs these columns to exist.

---

## STEP 6 - Exploratory data analysis (notebook 04)

**1. Objective.** Describe the data visually and numerically: AQI distribution, category
shares, city comparison, time trends, monthly/seasonal/weekday profiles, pollutant
distributions - each figure with title, axis labels and units.

**2. Files to create.** `src/viz.py`, `src/figures.py`,
`notebooks/04_eda.ipynb`, and `visualizations/eda/01_...12_*.png`.

**3. Exact code.**

```python
import figures as F
from IPython.display import Image

paths = F.eda(feat, pollutants)                 # writes and returns 12 PNGs
Image(paths["03_city_avg_median_aqi"])
```

Every figure goes through the same style and save path:

```python
# src/viz.py
def savefig(fig, name, subdir=None, ...):
    ...
def unit(col: str) -> str: ...                   # "µg/m³" or "mg/m³" from config
```

**4. Explanation.** `figures.eda()` is one function per figure family so that notebooks
only orchestrate: the same code runs inside `src/pipeline.py`, which is why the PNGs and
the exported tables cannot disagree. `viz.style()` sets font sizes, removes top/right
spines, and forbids 3D; `viz.unit()` pulls the unit from `C.UNIT_LABELS` so an axis can
never be labelled with a unit the column does not use.

**5. Expected output.** Twelve PNGs in `visualizations/eda/`, and printed tables for
descriptive statistics. The two most informative: `03_city_avg_median_aqi.png` (bars that
look identical) and `01_aqi_distribution.png` (flat, not right-skewed).

**6. How to verify.**

```powershell
(Get-ChildItem visualizations\eda\*.png).Count      # 12
.\.venv\Scripts\python.exe tools\run_notebooks.py 04
```

Open one PNG and check: title present, both axes labelled with units, no 3D, no
truncated tick labels.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `ValueError: I/O operation on closed file` from seaborn/matplotlib | a figure was saved then re-used after `plt.close()` | each helper builds its own figure and closes it; do not cache `Axes` across calls |
| Blank PNGs | figure saved before content was drawn | save inside the same function that draws (`viz.savefig`) |
| Tick labels unreadable at 12,000+ characters | too many categories on an axis | aggregate first (month names, not dates) or rotate/shorten in `viz.label_axes` |
| `TypeError: 'Line2D' object is not subscriptable` on a boxplot | matplotlib 3.11 returns artists, not the old tuple form | index the artists via `ax.patches`/`ax.lines`, not the removed boxplot return contract |

**8. What to do next.** STEP 7 - correlation and statistical structure.

---

## STEP 7 - Correlation analysis and statistical testing (notebook 05)

**1. Objective.** Measure association between pollutants and with AQI - linearly, by rank,
and non-linearly - and attach significance to the group differences EDA only displayed.

**2. Files to create.** `src/statistics_analysis.py`, `notebooks/05_correlation_analysis.ipynb`,
plus `correlation_matrix.csv`, `correlation_with_aqi.csv`,
`group_comparison_tests.csv`, `distribution_tests.csv`, `aqi_structure_probe.csv`.

**3. Exact code.**

```python
import statistics_analysis as S

corr   = S.correlation_matrix(feat, measures)                      # Pearson + p-values
spear  = S.correlation_matrix(feat, measures, method="spearman")
target = S.correlation_with_target(feat, measures, C.AQI_COL)
dist   = S.distribution_tests(feat, measures)                      # Shapiro + KS-vs-uniform
groups = {g: S.group_comparison(feat, C.AQI_COL, g)
          for g in ("City", "Month", "Season", "Is_Weekend")}
fit    = S.linear_fit(feat, C.AQI_COL, measures)                   # R2, adj R2, RMSE
pred   = S.tree_predictability(feat, C.AQI_COL, measures)          # CV R2 of a tree ensemble
struct = S.aqi_structure(feat, C.AQI_COL, measures)                # forward selection
```

**4. Explanation.** Pearson alone would have produced the wrong story here: the matrix is
near zero, yet a gradient-boosted tree predicts AQI with CV R2 = 0.9969 where linear
regression manages 0.0579. `tree_predictability()` exists because of that gap, and
`aqi_structure()` (single-column CV R2, then greedy forward selection) exists to ask
*which* columns carry it. `group_comparison()` reports ANOVA **and** Kruskal-Wallis,
because normality is rejected for every measured column, so the parametric test's
assumption is not satisfied. `distribution_tests()` adds KS-against-uniform plus skew and
excess kurtosis, which is how the flat shape was quantified rather than eyeballed.

**5. Expected output.** Largest absolute Pearson r between pollutants is negligible;
AQI's own r with each pollutant is small; linear R2 0.0579; tree CV R2 0.9969 (MAE 1.21);
forward selection PM2.5 (0.4935) then +PM10 (0.9588) then +O3 (0.9862); ANOVA p = 0.983
(City), 0.861 (Month), 0.676 (Season), 0.162 (weekend); trend slope 0.0366/year,
p = 0.9001.

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 05
.\.venv\Scripts\python.exe tools\inspect_results.py predictability
.\.venv\Scripts\python.exe tools\inspect_results.py aqi_structure/forward_selection
```

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `ConvergenceWarning` / long runtime in the probe | tree ensembles with `n_jobs` across a big frame | the probe uses a modest fixed forest on a sample; keep `random_state` pinned |
| "No significant correlation, therefore AQI is random" | over-reading a linear measure | report the linear *and* tree result together; that contrast is the finding |
| ANOVA quoted as proof of equality | a non-significant p is not proof of no difference | phrase as "no statistically detectable difference", as the report does |
| `LinAlgError: SVD did not converge` in a correlation | a constant column after filtering | drop zero-variance columns before calling `corr()` |

**8. What to do next.** STEP 8 - unsupervised grouping.

---

## STEP 8 - K-Means clustering (notebook 06)

**1. Objective.** Group observations by pollutant profile, choose k from evidence, and
describe the clusters without pretending they are more real than the silhouette says.

**2. Files to create.** `src/clustering.py`, `notebooks/06_kmeans_clustering.ipynb`, plus
`k_selection_table.csv`, `cluster_results.csv`, `cluster_profile.csv`,
`cluster_centroids_original_units.csv`.

**3. Exact code.**

```python
import clustering as KM

X = KM.build_matrix(feat, pollutants)[0]            # scaled design matrix
k_table = KM.choose_k(X, C.K_RANGE)                 # inertia + silhouette, k = 2..10
choice = KM.recommend_k(k_table)                    # documented, incl. disagreement
feat, kmodel, kscaler, used, centroids_z, centroids_raw = KM.fit(
    feat, pollutants, choice["chosen_K"])
metrics = pollutants + [C.AQI_COL]
profile = KM.cluster_profile(feat, metrics)
described = KM.describe_clusters(profile, metrics)  # neutral wording per cluster
pcs = KM.pca_projection(X)                          # for the plot only
```

**4. Explanation.** `build_matrix()` scales before distance is ever computed - with CO near
5 and PM10 near 300, unscaled Euclidean distance is a PM10-only measure. `choose_k()`
computes inertia on the full panel and silhouette on a fixed 6,000-row sample (silhouette
is O(n²) and the sample size is recorded in the table's `Evaluated_On` column).
`recommend_k()` applies the "first k where inertia improvement < 5%" elbow rule *and* the
silhouette maximum, and if they disagree it says so in `rationale` rather than picking
quietly. `pca_projection()` is used only to draw; the labels come from all nine columns.

**5. Expected output.** `k_table` for k = 2..10; silhouette maximum at k = 2 with 0.0838
while the elbow rule suggests 4; the two-cluster solution chosen, with a profile table whose
clusters differ mainly in overall level, and a PCA plot whose two components carry 22.90%
of variance.

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 06
Get-Content data\processed\k_selection_table.csv
```

Check that `Clusters_Used == K` for the chosen k (no empty cluster), and that the notebook
text states the silhouette value it used.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `ValueError: Number of labels=0 does not match number of samples` | silhouette on a single-cluster result | `choose_k()` records `Clusters_Used`; filter before scoring |
| Clusters map 1:1 onto one pollutant | no scaling | use `build_matrix()` instead of the raw frame |
| Different cluster labels on every run | `random_state` missing | `C.RANDOM_STATE = 42` is passed to `KMeans` |
| Cluster 0 in one run is cluster 1 in another | K-Means label permutation - labels carry no order | always describe clusters by their profile table, never by number |

**8. What to do next.** STEP 9 - anomaly detection on the same scaled matrix.

---

## STEP 9 - Anomaly detection (notebook 07)

**1. Objective.** Find jointly unusual observations with Isolation Forest and characterise
them by city, period and pollutant profile - stating that the rate is an assumption.

**2. Files to create.** `src/anomaly_detection.py`, `notebooks/07_anomaly_detection.ipynb`,
plus `anomaly_results.csv`, `anomaly_by_city.csv`, `anomaly_pollutant_comparison.csv`.

**3. Exact code.**

```python
import anomaly_detection as AD

feat, model, used, params = AD.detect(feat, pollutants)   # contamination=0.05
display(AD.summary(feat))                                  # count, %, Note
display(AD.by_city(feat))
display(AD.by_period(feat, "year"))
display(AD.pollutant_comparison(feat, pollutants))
```

**4. Explanation.** `detect()` fits `IsolationForest(n_estimators=300,
contamination=C.CONTAMINATION, random_state=42)` on the nine pollutant columns and writes
`Anomaly` (bool), `Anomaly_Score` and `Anomaly_Pctile`. The score is the model's own
relative ranking, so a percentile makes it readable without implying a probability.
`summary()` returns a `Note` field that says plainly that the detected share follows the
contamination parameter - the sentence the viva will ask for, written into the data.

**5. Expected output.** 914 flagged rows of 18,265 (5.00%); per-city counts 168-200
(4.60%-5.47%); per-year rates 3.67%-5.92%; largest mean shift between normal and flagged
rows 14.57% (NO).

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 07
.\.venv\Scripts\python.exe tools\inspect_results.py anomaly/stats
.\.venv\Scripts\python.exe tools\inspect_results.py anomaly/params
```

Also confirm the sensitivity table exists (contamination 0.01, 0.02, 0.05, 0.10) - it is
the direct demonstration that the count is a threshold, not a discovery.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| "5% of the city's days are anomalous events" | restating the parameter as a finding | the anomaly rate is configured; describe what the flagged days look like instead |
| A cell times out during the sensitivity loop | four more forest fits on the full panel under memory pressure | raise `--timeout` (e.g. `tools/run_notebooks.py 07 --timeout 5400`) or close other processes; do not delete the sensitivity cell |
| `ValueError: Input contains NaN` | a pollutant column has gaps after feature engineering | fit on the measured columns only, as `detect()` does |
| Scores all near zero | contamination mismatch or untrained model | check `params` in `results.json`; the model must be fitted on the same frame that is scored |

**8. What to do next.** STEP 10 - classification, with AQI excluded.

---

## STEP 10 - Classification (notebook 08)

**1. Objective.** Predict the AQI category from pollutant measurements only, against a
stated baseline, after measuring what the leaked column would have contributed.

**2. Files to create.** `src/classification.py`, `notebooks/08_classification.ipynb`, plus
`model_comparison.csv`, `class_balance.csv`, `classification_per_class.csv`,
`confusion_matrices.csv`, `feature_importance.csv`, `leakage_check.json`,
`classification_results.csv`.

**3. Exact code.**

```python
import classification as CL

cls_df  = CL.drop_non_informative(feat, target)          # target kept, identifiers dropped
balance = CL.class_balance(cls_df, target)                # the imbalance, stated first
leakage = CL.leakage_check(cls_df, pollutants, target)    # AQI in / AQI out, measured
comp, reports, matrices, split_info, pred_frame, y_test, X_test = CL.train_and_evaluate(
    cls_df, pollutants, target, cv_folds=3)               # AQI excluded from features
imp_model, imp_features = CL.fit_reference_model(cls_df, pollutants, target)
imp = CL.feature_importance(imp_model, imp_features)
```

`build_models()` returns the five contenders:

```python
{"Baseline (prior)": DummyClassifier(strategy="prior"),
 "Logistic Regression": Pipeline([("scaler", StandardScaler()),
                                  ("clf", LogisticRegression(max_iter=2000, ...))]),
 "Decision Tree": DecisionTreeClassifier(...),
 "Random Forest": RandomForestClassifier(...),
 "Hist Gradient Boosting": HistGradientBoostingClassifier(...)}
```

**4. Explanation.** The order of those calls is the point. `class_balance()` runs first so
accuracy is interpreted afterwards; `leakage_check()` fits the same model twice - once with
AQI, once without - and stores the difference, so the exclusion is justified by a measured
number rather than by assertion. `train_and_evaluate()` uses a stratified 75/25 split with
`random_state = 42`, adds 3-fold CV, and appends the lift over the prior baseline.
Macro-averaged precision/recall/F1 are reported per model *and* per class, because the four
main bands hold over 99% of records.

**5. Expected output.** Baseline (prior) accuracy 30.11%; random forest best at 99.28%
accuracy, macro-F1 0.7765, lift 69.17 points, CV accuracy 99.17% (sd 0.17); logistic
regression 31.55%; leakage experiment 99.28% -> 99.96% (inflation 0.68 points, macro-F1
0.7355 -> 0.8276).

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 08
Get-Content data\processed\model_comparison.csv
.\.venv\Scripts\python.exe tools\inspect_results.py classification/leakage
```

Confirm `split_info.excluded_leaky_column == "AQI"` and that the comparison table contains
the baseline row.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| Accuracy close to 100% with macro-F1 close to accuracy | leakage - AQI or a bucket of it is in `X` | re-check `drop_non_informative()` and the feature list printed in `split_info["features_used"]` |
| `ConvergenceWarning` in logistic regression | unscaled inputs or too few iterations | the model is inside a `StandardScaler` pipeline with `max_iter=2000` |
| `UndefinedMetricWarning` for a class | no predicted samples for that class | `zero_division=0` is set; report per-class recall alongside, as notebook 08 does |
| Rare classes always mispredicted (Good has 6 rows) | genuine data limit, not a bug | state it; do not resample silently to make the table look better |

**8. What to do next.** STEP 11 - export everything Power BI needs.

---

## STEP 11 - Export the processed datasets (notebook 09)

**1. Objective.** Produce every file the dashboard consumes, from the same code the
notebooks demonstrated, and record the results as machine-readable JSON.

**2. Files to create.** `src/pipeline.py`, `src/reporting.py` (summaries and dimensions),
`notebooks/09_final_analysis.ipynb`, and the ~35 CSVs in `data/processed/` including
`air_quality_cleaned.csv`, `dim_date.csv`, `dim_city.csv`, `dim_bucket.csv`,
`city_summary.csv`, `monthly_summary.csv`, `results.json`.

**3. Exact code.**

```python
import pipeline

results = pipeline.run(verbose=True)      # steps 1-9 of this walkthrough, once
print("runtime (seconds):", results["runtime_seconds"])
```

Inside `run()`, the BI-facing tables:

```python
final.to_csv(C.CLEANED_CSV, index=False)                      # FACT_AirQuality
dim_date.to_csv(C.PROCESSED_DIR / "dim_date.csv", index=False)
dim_bucket.to_csv(C.DIM_BUCKET_CSV, index=False)
dim_city.to_csv(C.DIM_CITY_CSV, index=False)
feat[cluster_cols].to_csv(C.CLUSTER_RESULTS_CSV, index=False)
feat[anom_cols].to_csv(C.ANOMALY_RESULTS_CSV, index=False)
pred_frame.to_csv(C.CLASSIFICATION_CSV, index=False)
```

**4. Explanation.** Notebook 09 does not re-implement the analysis: it calls
`pipeline.run()`, the same module the earlier notebooks use cell by cell, so the exported
files cannot drift from what was demonstrated. The dimension tables exist because a star
schema needs them (`dim_date` for time intelligence, `dim_bucket` for the band order and
colour ramp, `dim_city` for city attributes). `results.json` is the contract with the
document builders: the report and the slides read every number from it.

**5. Expected output.** The full `data/processed/` directory, `results.json` with 30
top-level keys, and notebook 09 §7's quality table with every check `True` - including
"AQI_Bucket is reproducible from AQI (leakage confirmed)" and
"AQI_Bucket agreement with the band table: 100.00%".

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\run_notebooks.py 09
.\.venv\Scripts\python.exe tools\show_outputs.py notebooks\09_final_analysis.ipynb
(Get-ChildItem data\processed\*.csv).Count
```

The last line of notebook 09 §7 must read `all checks passed: True`. If any row is
`False`, fix that artefact before touching the report or the slides.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `NameError: name 'U' is not defined` in a regenerated notebook | a cell uses a module the notebook's bootstrap does not import | add the import to that cell (`import data_utils as U`) and regenerate: `python tools/build_notebooks.py` |
| A cell times out (`nbclient.exceptions.CellTimeoutError`) | the machine is out of memory and paging, not an infinite loop | free memory and re-run with a larger allowance: `tools/run_notebooks.py 09 --timeout 5400`; do not delete the cell |
| A CSV has an unexpected column count | an earlier notebook was not re-run after a code change | re-run the whole set: `tools/run_notebooks.py` |
| `results.json` older than the CSVs | the pipeline was run, then a notebook overwrote some files | re-run notebook 09 last, always |

**8. What to do next.** STEP 12 - load the exported files into Power BI.

---

## STEP 12 - Power BI: load the data and build the model

**1. Objective.** Turn the exported CSVs into a star schema with documented measures - the
step that converts analysis into a tool someone else can use.

**2. Files to create.** `dashboard/Air_Quality_Intelligence.pbix` (built by hand in Power
BI Desktop; it cannot be generated from Python), guided by
`dashboard/POWER_BI_BUILD_GUIDE.md` and `dashboard/DAX_measures.dax`.

**3. Exact code.** In Power BI Desktop: *Get data > Text/CSV* for
`data/processed/air_quality_cleaned.csv` (rename to `FACT_AirQuality`), `dim_date.csv`,
`dim_city.csv`, `dim_bucket.csv`, `city_summary.csv`, `monthly_summary.csv`,
`cluster_results.csv`, `cluster_profile.csv`, `anomaly_results.csv`,
`model_comparison.csv`, `classification_results.csv`, `insights.csv`. Then, in
*Model view*:

```
FACT_AirQuality[Date]   -*→ dim_date[DateKey]        (single, active)
FACT_AirQuality[City]   -*→ dim_city[City]           (single, active)
FACT_AirQuality[AQI_Bucket] -*→ dim_bucket[AQI_Bucket] (single, active)
```

and *Transform data* sets `Date` to Date type, `AQI_Bucket` to a categorical whose
sort order follows `Band_Order`, and hides the technical columns
(`PM25_PM10_Ratio` and friends are kept for tooltips, not for the field list).

**4. Explanation.** One fact table at city-day grain, three conformed dimensions: that is
what lets a single slicer filter every visual. The model-result tables are deliberately
**unrelated** to the fact table - `cluster_results.csv` is at observation grain and
`model_comparison.csv` is at model grain, and relating them to the fact table would either
ambiguous-filter or silently multiply counts. They are used as plain tables on the Pattern
Discovery page.

**5. Expected output.** A `.pbix` whose model view shows three active 1-to-many
relationships, no bi-directional filters on the fact table, and 0 errors on load. Row
count of `FACT_AirQuality` equals 18,265.

**6. How to verify.** *Transform data standard > FACT_AirQuality* shows 18,265 rows;
hovering a relationship shows "Many to one, Single cardinality, Cross filter direction
Single". Then run one measure in a card: `Avg AQI` should equal the value in
`data/processed/city_summary.csv`'s overall mean when no slicer is active.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `Cannot show value of type Date` / no date hierarchy | the Date column stayed as text | set Data Type = Date in Power Query, and mark `dim_date` as a date table (`Table tools > Mark as date table`) |
| AQI categories sort alphabetically | categorical column default | sort `AQI_Bucket` by the `Band_Order` column in `dim_bucket` |
| A total that doubles after adding a relationship | two paths filter the same table | keep single-direction filters; leave model tables unrelated |
| "We can't convert to a number" on load | locale decimal separator | set the file's origin locale in Power Query, do not text-patch the CSV |

**8. What to do next.** STEP 13 - pages, visuals and DAX.

---

## STEP 13 - Dashboard design: five pages and the DAX layer

**1. Objective.** Build the five pages the brief specifies, with KPIs defined in DAX, and
make the interaction contract visible to the user.

**2. Files to create.** The report pages inside the `.pbix`, plus the measure table built
by pasting `dashboard/DAX_measures.dax` (*Modeling > New measure*, one at a time).

**3. Exact code.** The three idioms the measures rely on:

```dax
Avg_AQI := DIVIDE ( SELECTEDVALUE ( ... ), ... )          -- never divides by zero
AQI_Share_Pct :=
    DIVIDE (
        COUNTROWS ( FILTER ( FACT_AirQuality, ... ) ),
        COUNTROWS ( ALLSELECTED ( FACT_AirQuality ) )     -- respects slicers, not rows
    )
Avg_AQI_YTD := TOTALYTD ( [Avg_AQI_Abs], dim_date[DateKey] )
Avg_AQI_YoY_Pct := DIVIDE ( [Avg_AQI] - [Avg_AQI_PY], [Avg_AQI_PY] )
```

where the previous-year measure is

```dax
Avg_AQI_PY := CALCULATE ( [Avg_AQI], SAMEPERIODLASTYEAR ( dim_date[DateKey] ) )
```

Pages: **Overview** (6 KPI cards + AQI by city, trend over time, category distribution,
average pollutant levels, city comparison), **City Analysis**, **Pollutant Analysis**,
**Pattern Discovery** (clusters, anomalies, model comparison), **Trends** (yearly, monthly,
seasonal, category trend, city trend comparison, pollutant trend comparison).

**4. Explanation.** `DIVIDE` is used everywhere because a slicer combination can legitimately
produce an empty selection, and a blank is honest where `#DIV/0!` is not. `ALLSELECTED`
makes "share of the current selection" work under a slicer without hard-coding the filter.
`TOTALYTD` / `SAMEPERIODLASTYEAR` need a real marked date table - which is why `dim_date`
exists rather than the fact's own Date column. A what-if parameter supplies the adjustable
limit so the threshold is a user input, documented at 60 µg/m³ (CPCB 24-hour PM2.5,
flagged for re-verification).

**5. Expected output.** Five pages, 6 KPI cards on page 1, a slicer pane (City, Year,
Month, Season, AQI Category) on every page, and dynamic titles such as
`"AQI trend - " & SELECTEDVALUE ( dim_city[City], "All cities" )`.

**6. How to verify.** Follow the interaction checklist in
`dashboard/POWER_BI_BUILD_GUIDE.md` §7: pick one city and confirm every visual on the page
changes; click a bar in *Average AQI by City* and confirm the other visuals cross-filter;
hover a KPI and read a tooltip with a unit; check no axis starts at a non-zero baseline
where that would exaggerate a difference. Each KPI's meaning is checked against
`dashboard/KPI_DEFINITIONS.md`.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| A slicer changes some visuals but not others | *Format > Edit interactions* left at defaults after a visual was replaced | re-set interactions (filter, not highlight) for the slicer on every visual |
| KPI cards show the same number for every city | measure built on `ALL()` where `ALLSELECTED()` was meant | replace `ALL` with `ALLSELECTED` (or plain `SELECTEDVALUE` context) |
| `TOTALYTD` returns blank | no marked date table, or the relationship is inactive | mark `dim_date` as a date table and activate the 1-to-many relationship |
| A stacked bar of AQI categories in alphabetical order | bucket sort order not applied | sort by `Band_Order` from `dim_bucket` |

**8. What to do next.** STEP 14 - insights, which the dashboard displays and the report
quotes.

---

## STEP 14 - Insight generation

**1. Objective.** Produce the insight list from computed artefacts only, each row carrying
its own evidence, source file and strength label.

**2. Files to create.** `src/reporting.py::insights_from_results()`,
`data/processed/insights.csv`.

**3. Exact code.**

```python
insights = R.insights_from_results(
    before=before, after=after, city=city_sum, monthly=monthly,
    corr_target=corr_target, cluster_choice=k_choice, cluster_profile=cprofile,
    anomaly_stats=a_stats, anomaly_by_city=a_city, model_table=comp,
    leakage=leakage, distribution=dist, group_tests=groups, trend=trend,
    predictability=predictability, aqi_structure=structure)
insights.to_csv(C.INSIGHTS_CSV, index=False)
```

**4. Explanation.** The function takes *frames and dicts*, never raw constants, and each
sentence is built with an f-string around those values - so an insight cannot survive a
change of data without changing its own text. `Evidence Strength` is one of two labels, and
the rule is mechanical: **`measured`** when the sentence's number can be read straight out
of an artefact (a summary table, a test result, a model comparison), and **`interpretation`**
when the sentence is a judgement drawn *from* several measured results rather than a reading
of one - "the file behaves like a simulation" is the example. A weak structure is therefore
never dressed up: the 0.08 silhouette produces a `measured` row that says the separation is
weak, not a headline. `Derived From` names the CSV or JSON key, which is what makes the
dashboard's insight table auditable.

**5. Expected output.** 20 rows with columns
`Insight | Category | Quantitative Evidence | Derived From | Evidence Strength`, 17 labelled
`measured` and 3 labelled `interpretation`, including the leakage insight ("AQI_Bucket is
reproducible from AQI on 100% of rows"), the non-linear predictability insight, the "no
statistically detectable trend" insight, and the dataset-integrity insight.

**6. How to verify.**

```powershell
Import-Csv data\processed\insights.csv | Group-Object "Evidence Strength" | Select-Object Name,Count
Import-Csv data\processed\insights.csv | Where-Object { $_."Evidence Strength" -eq "interpretation" } |
    Select-Object Insight, "Quantitative Evidence"
```

Pick one `measured` row and open the file named in `Derived From` to see the number.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| An insight quotes a number that is not in any artefact | it was typed rather than assembled | delete the literal and pass the value in as a parameter |
| Two insights contradict each other | they were written at different times | re-run the pipeline; both now come from one `results.json` |
| Every insight is `measured` | the judgement rows were mislabelled to look harder | anything that reasons across results must be labelled `interpretation` |

**8. What to do next.** STEP 15 - the written report.

---

## STEP 15 - Final academic report

**1. Objective.** Produce the 28-section report as Word and PDF, with every figure, table
and number read from the computed artefacts.

**2. Files to create.** `src/docx_builder.py`, `tools/build_report.py`,
`report/Air_Quality_Intelligence.docx`, `report/Air_Quality_Intelligence.pdf`.

**3. Exact code.**

```powershell
.\.venv\Scripts\python.exe tools\build_report.py            # docx + PDF via Word
.\.venv\Scripts\python.exe tools\build_report.py --no-pdf   # docx only
```

Sections come from the same helper that reads the JSON:

```python
r = load()                     # data/processed/results.json
n(r["clustering"]["choice"]["silhouette"], 4)
b.table(pd.DataFrame(r["classification"]["comparison"]), caption="...")
b.figure(viz / "clustering" / "01_elbow_silhouette.png", "Elbow and silhouette evidence")
```

**4. Explanation.** `DocxBuilder` writes real Word fields (not typed text) for the table of
contents, the list of figures/tables, `SEQ` caption numbering and `PAGE`/`NUMPAGES`, so the
page numbers in the contents are Word's own. `convert_to_pdf()` drives Word through COM: it
repaginates, updates every `TablesOfContents`, updates fields, repaginates again, then
exports `wdFormatPDF (17)` - which is why the PDF's contents matches the printed pages
instead of the pre-repagination guess. `report/` also holds the viva document and this
walkthrough.

**5. Expected output.** A document with the 28 numbered sections in the brief's order, a
generated abstract whose word count is printed at build time (target 200-300), embedded
figures with numbered captions, the methodology diagram, and a PDF whose TOC entries point
at the right pages.

**6. How to verify.** The build prints the abstract word count and the output paths. Then
read the generated files back:

```powershell
.\.venv\Scripts\python.exe - <<'PY'
import docx
d = docx.Document("report/Air_Quality_Intelligence.docx")
print("paragraphs:", len(d.paragraphs), "tables:", len(d.tables))
print([p.style.name for p in d.paragraphs if p.style.name.startswith("toc")][:5])
PY
```

`toc 1` / `table of figures` styles prove the fields were computed by Word, not typed.
Spot-check three quoted numbers against `tools/inspect_results.py`.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `COMError` / "Word could not open the file" during PDF export | Word is not installed or is busy with a dialog | use `--no-pdf` and export manually, or close the open Word instance and retry |
| PDF page numbers in the contents are wrong | fields were updated before repagination | `convert_to_pdf()` already does Repaginate -> update -> Repaginate -> update; do not shorten that sequence |
| A number in the text disagrees with the table below it | one of them was typed by hand | both must come from `results.json`; re-run `build_report.py` |
| Abstract outside 200-300 words after a code change | the abstract is generated from results, so it moves | adjust the sentence templates in `abstract()`, not the resulting prose |

**8. What to do next.** STEP 16 - the README.

---

## STEP 16 - README

**1. Objective.** Write the repository's front page so a stranger can reproduce the
project without reading the code first.

**2. File to create.** `README.md` at the project root.

**3. Exact code.** Markdown with the sections the brief lists, in order: Project Title,
Overview, Objectives, Dataset, Technologies, Project Architecture, Data Mining Techniques,
Dashboard Pages, Installation, How to Run, Results, Project Structure, Screenshots, Future
Scope, Authors. The runnable part is the important part:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python tools\build_notebooks.py        # (re)generate the nine notebooks
python tools\run_notebooks.py          # execute them and store real outputs
python tools\build_report.py           # report .docx + .pdf
python tools\build_presentation.py     # 17-slide .pptx
```

**4. Explanation.** The README documents the *tool chain* rather than pasting results: the
one-command rebuild is the reproducibility claim, and the numbers live in `results.json`,
the report and the dashboard. Every result quoted in it is the value in the current
artefacts, with the file named beside it.

**5. Expected output.** A README that renders on GitHub with a directory tree, a table of
the notebooks, the five dashboard pages, and a "what this dataset does not support"
paragraph.

**6. How to verify.** Read the *How to Run* commands and execute them in order on a clean
checkout - the whole project must rebuild from those lines alone. Preview the Markdown
(a tree block that is not fenced will break the page).

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| Commands work only inside `notebooks/` | the notebooks resolve the root themselves, the shell does not | README commands are written from the project root; say so |
| Screenshots section empty | the `.pbix` is built by hand in Power BI | mark it as "capture after building the dashboard" rather than leaving a broken image link |
| Version numbers in README differ from `results.json` | hand-copied | quote them from `environment` in `results.json` |

**8. What to do next.** STEP 17 - put it on GitHub.

---

## STEP 17 - GitHub

**1. Objective.** Publish the project with the environment excluded and the outputs kept.

**2. Files to create.** `.gitignore` (already present), and the remote repository.

**3. Exact code.**

```powershell
git init
git add .
git commit -m "Initial project setup"
git branch -M main
git remote add origin YOUR_GITHUB_URL
git push -u origin main
```

`.gitignore` excludes `.venv/`, `__pycache__/`, `*.py[cod]`, `.ipynb_checkpoints/`, `.env`,
transient logs (`*.log`, `notebook_run.log`), Office lock files (`~$*`) and local pip
freeze files. It does **not** exclude `data/raw/` (the file is small and required for
reproduction) or the executed notebooks (they carry the real outputs).

**4. Explanation.** Committing the executed notebooks is a deliberate choice for an academic
submission: a reviewer sees the numbers without running anything. Committing the raw CSV is
what makes the claim checkable. Everything regenerable - `__pycache__`, virtual
environments, Word lock files, run logs - is ignored, because a committed artefact that can
drift from its source is a future inconsistency.

**5. Expected output.** A repository whose first commit contains `data/`, `notebooks/`,
`src/`, `tools/`, `visualizations/`, `dashboard/`, `report/`, `requirements.txt`,
`README.md`, `.gitignore` - and no `.venv`.

**6. How to verify.**

```powershell
git status --short
git ls-files | Measure-Object -Line
git ls-files | Select-String "\.venv|__pycache__|\.env$"   # must print nothing
```

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `git push` rejects with a large-file error | a big CSV or `.pbix` exceeded the limit | keep data files under the limit (this project's raw CSV is ~2 MB); use Git LFS if the dataset grows, and never delete the data to make the push work |
| `.venv` got committed anyway | it was added before `.gitignore` existed | `git rm -r --cached .venv` then commit; `--cached` keeps the local files |
| `remote origin already exists` | the remote was set before | `git remote set-url origin YOUR_GITHUB_URL` |
| Notebooks show as modified after every open | Jupyter rewrites metadata on save | re-run `tools/build_notebooks.py` + `tools/run_notebooks.py` so stored outputs are the executed ones |

**8. What to do next.** STEP 18 - the presentation.

---

## STEP 18 - Presentation

**1. Objective.** Build a 17-slide deck for a 10-15 minute viva, whose numbers come from
the same artefacts as the report.

**2. Files to create.** `tools/build_presentation.py`,
`presentation/Air_Quality_Intelligence.pptx`.

**3. Exact code.**

```powershell
.\.venv\Scripts\python.exe tools\build_presentation.py
```

Slides follow the brief's list exactly: Title, Introduction, Problem Statement, Objectives,
Dataset, Methodology, Data Preprocessing, EDA, Correlation Analysis, K-Means, Anomaly
Detection, Classification, Power BI Dashboard, Results/Insights, Limitations, Future Scope,
Conclusion.

**4. Explanation.** The deck imports its shared wording from `tools/build_report.py`
(`TITLE`, `PROBLEM_STATEMENT`, `PROJECT_QUESTIONS`, `LIMITATIONS_FROM_BRIEF`,
`FUTURE_SCOPE`) so the slides and the report cannot disagree about what was asked. Every
figure on a slide is either a real PNG from `visualizations/` or a value read from
`results.json`; the DAX measure count is counted from `DAX_measures.dax` rather than
remembered. Each slide carries speaker notes with a suggested timing; the timings total
about 13 minutes.

**5. Expected output.** A `.pptx` reporting `slides: 17`, with no placeholder text except
the student-detail fields in `STUDENT` (which are the report's own placeholders, filled
once for both documents).

**6. How to verify.**

```powershell
.\.venv\Scripts\python.exe tools\build_presentation.py
```

then open the deck, press F5, and check that each slide's notes are present and that the
numbers on slides 8, 10, 11 and 12 match `results.json` / `model_comparison.csv`.

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| `PackageNotFoundError` reading the deck | the file was saved while PowerPoint held a lock | close PowerPoint and rebuild |
| A picture is missing from a slide | that figure was never generated (a notebook did not run) | re-run the notebook that owns the figure family; do not delete the slide entry |
| Text overflows its box | too many bullets for the frame | shorten the sentence in the builder; never fix it by hiding the evidence |
| Slide numbers differ from the brief's list | a slide was added or reordered | the brief's 17 titles are the contract; keep them |

**8. What to do next.** STEP 19 - viva preparation.

---

## STEP 19 - Viva preparation

**1. Objective.** Be able to answer, and prove, any question about the project - including
the ones this dataset does not answer.

**2. File to create.** `report/Viva_Questions_Answers.md`.

**3. Exact code.** Rehearsal loop, per topic:

```powershell
.\.venv\Scripts\python.exe tools\inspect_results.py clustering/choice
.\.venv\Scripts\python.exe tools\inspect_results.py classification/leakage
.\.venv\Scripts\python.exe tools\inspect_results.py anomaly/stats
.\.venv\Scripts\python.exe tools\inspect_results.py trend_test
```

**4. Explanation.** 54 questions cover the topic list in the brief (dataset, preprocessing,
missing values, outliers, feature engineering, correlation, Pearson, K-Means, centroids,
elbow, silhouette, StandardScaler, PCA, Isolation Forest, anomaly detection,
classification, train/test split, data leakage, confusion matrix, precision, recall,
F1-score, Power BI, KPI, slicer, dashboard, BI, data mining, limitations, future scope).
Each answer ends with a *Prove it* line naming the artefact, so preparation doubles as
verification: if the file no longer says what the answer says, the answer is wrong and
gets edited.

**5. Expected output.** Answers that survive the follow-up question - "how do you know?" -
with a file and a number rather than a justification.

**6. How to verify.** Say each answer out loud in under 30 seconds, then open the named
artefact and confirm the figure. Anything that fails either test is rewritten. The last
question in the document is the one to be ready for: *"what would you do differently?"*

**7. Common errors.**

| Error | Meaning | Fix |
|---|---|---|
| Quoting the leaky accuracy (99.96%) as the result | it is the number that proves leakage, not the model | quote 99.28% with its macro-F1 and the 69.17-point lift over the baseline |
| Saying "5% of days are anomalous" | restating `contamination` as a finding | say the rate was configured, and describe the flagged days |
| Claiming Delhi is the most polluted city | not supported: city ANOVA p = 0.983 | give the ranking *and* the p-value, as `KPI_DEFINITIONS.md` requires |
| "Correlation is 0.99" | the Pearson matrix is near zero; the 0.9969 is a tree R2 | separate linear association from non-linear predictability |

**8. What to do next.** Final quality check: re-run `tools/run_notebooks.py`, confirm
notebook 09 §7 prints `all checks passed: True`, rebuild report and deck from the fresh
artefacts, and walk the brief's section 54 checklist item by item against the repository.
