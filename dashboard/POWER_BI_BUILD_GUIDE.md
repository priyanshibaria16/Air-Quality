# Power BI Build Guide
### Air Quality & Pollution Intelligence - interactive dashboard layer

This document is the complete, reproducible instruction set for the Business
Intelligence half of the project. It is written so that somebody who has never
seen this repository can rebuild the dashboard in about 60-90 minutes and end up
with exactly the numbers the Python notebooks produced.

| Item | Value |
|---|---|
| Tool | Microsoft Power BI Desktop (free, Windows) |
| Data inputs | CSV files in `data/processed/` only - no live API, no database |
| Fact table rows | 18,265 daily records (one per city per day) |
| Cities / period | 5 cities, 2015-01-01 to 2024-12-31 |
| Measure library | [`DAX_measures.dax`](DAX_measures.dax) - paste, do not retype |
| Pages | 5 (Executive Overview, Pollutant Intelligence, City Comparison, Data Mining Intelligence, Trends & Insights) |

> **Why no `.pbix` file is committed here.** A `.pbix` is a proprietary binary
> that can only be produced inside Power BI Desktop. Everything needed to
> reproduce it is in this folder: the exact tables, the exact relationships, the
> exact DAX and a page-by-page visual list. Building it is therefore a
> mechanical exercise, and the validation checklist in section 10 proves the
> result is the intended one.

---

## 1. What the dashboard has to answer

The brief is explicit that this is not "just a visualisation project", so each
page is tied to a decision a stakeholder would actually make:

| Page | Question it answers | Who asks it |
|---|---|---|
| 1. Executive Overview | How bad is the air, for how long, and is it getting worse? | Senior official / press |
| 2. Pollutant Intelligence | Which measured pollutant moves the index, and where does each one come from in the distribution? | Environment analyst |
| 3. City Comparison | Do cities differ beyond random variation? | Policy comparison, budget allocation |
| 4. Data Mining Intelligence | What did clustering, anomaly detection and classification actually produce, and how trustworthy is it? | Technical review / viva |
| 5. Trends & Insights | What time patterns exist, and what conclusions does the evidence support? | Planning cell |

Every page carries an **evidence note**. Where the dataset does not support a
conclusion, the page says so in words instead of showing a chart that implies
one. That requirement comes directly from the academic-integrity rules of the
brief and from the statistical tests in notebook 05.

---

## 2. Prerequisites

1. Windows 10/11 with Power BI Desktop installed (`Get-Data > Store > Power BI
   Desktop`, or the Microsoft installer).
2. The project already executed, so the artefacts exist:
   ```powershell
   .\.venv\Scripts\activate
   python tools/build_notebooks.py   # writes notebooks/*.ipynb
   python tools/run_notebooks.py     # executes them, writes data/processed/*.csv
   ```
3. If any file in `data/processed/` is missing, stop and re-run step 2. Never
   type values into Power Query to "fill in" a missing table.

---

## 3. Import the data (Get Data > Text/CSV)

For each file: **Home > Get Data > Text/CSV > Transform Data** (never
"Load" directly - the type detection needs correcting). Set the columns listed
below, rename the query to the model name, then **Close & Apply** at the end.

### 3.1 Model tables (part of the relationships)

| Query name (rename to this) | Source file | Key / grain | Type fixes that matter |
|---|---|---|---|
| `FACT_AirQuality` | `air_quality_cleaned.csv` | City + Date (one row per city-day) | `Date` = Date; `Is_Weekend` = Whole number; `Cluster` = Whole number; `AQI_Bucket`, `Anomaly_Label`, `Cluster_Description`, `Pollution_Index_Band` = Text; all pollutants and `AQI`, `Anomaly_Score`, `Pollution_Index`, ratios, percentiles, rolling values = Decimal |
| `DIM_Date` | `dim_date.csv` | `Date` (unique) | `Date` = Date; `Is_Weekend` = Whole number; rest Text/Whole number |
| `DIM_City` | `dim_city.csv` | `City` (unique) | `City` = Text; counts = Whole number; `Dominant_Cluster` = Whole number; dates = Date |
| `DIM_Bucket` | `dim_bucket.csv` | `AQI_Bucket` (unique) | `Sort_Order`, band and record columns = Whole number; `Colour` = Text |

### 3.2 Support tables (loaded, **not** related to the fact)

These describe analysis results rather than days. Leaving them un-related is a
deliberate modelling decision: relating a 5-row model table to an 18,265-row
fact would multiply rows and silently corrupt every average.

| Query name | Source file | Used on page |
|---|---|---|
| `MODEL_COMPARISON` | `model_comparison.csv` | 4 |
| `CLASSIFICATION_PER_CLASS` | `classification_per_class.csv` | 4 |
| `CLUSTER_PROFILE` | `cluster_profile.csv` | 4 |
| `K_SELECTION` | `k_selection_table.csv` | 4 |
| `CORRELATION_WITH_AQI` | `correlation_with_aqi.csv` | 2 |
| `ANOMALY_BY_CITY` | `anomaly_by_city.csv` | 4 |
| `INSIGHTS` | `insights.csv` | 1 and 5 |
| `DATA_QUALITY` | `data_quality_report.csv` | 1 (as a tooltip page) |

Right-click each of these in the Model view and choose **Configure table
display folders** if you want a tidier Fields pane. To keep them out of the
model entirely you may instead right-click > **Select related** later; but they
must stay loadable for visuals.

### 3.3 Do **not** import

* `data/raw/Air_quality_data.csv` - the raw file is the audit trail, the model
  consumes the cleaned one. Importing both invites double counting.
* `confusion_matrices.csv` (long/narrow, better shown as a static image from
  `visualizations/classification/`), `correlation_matrix.csv` (matrix layout -
  use the PNG or the long `correlation_with_aqi.csv` instead), and any
  `results.json`.

---

## 4. Star schema and relationships

```
                         DIM_Date          DIM_City          DIM_Bucket
                     (Date, 1:1 unique)  (City, 1:1 unique)  (AQI_Bucket, 1:1 unique)
                             |  1              |  1                 |  1
                             |                 |                    |
                             +-----------------+--------------------+
                                           \        |        /
                                            \       |       /
                                             v   *  v    * v
                                        FACT_AirQuality  (18,265 rows:
                                        City, Date, pollutants, AQI, AQI_Bucket,
                                        Cluster, Anomaly, engineered features)

   Unrelated (no line drawn): MODEL_COMPARISON, CLASSIFICATION_PER_CLASS,
   CLUSTER_PROFILE, K_SELECTION, CORRELATION_WITH_AQI, ANOMALY_BY_CITY,
   INSIGHTS, DATA_QUALITY
```

Create in **Model view > Manage relationships > New**:

| From (column) | To (column) | Cardinality | Cross-filter | Active | Why |
|---|---|---|---|---|---|
| `DIM_Date[Date]` | `FACT_AirQuality[Date]` | One to many | Single | Yes | Time slicer and all time intelligence |
| `DIM_City[City]` | `FACT_AirQuality[City]` | One to many | Single | Yes | City slicer; keeps city attributes in one place |
| `DIM_Bucket[AQI_Bucket]` | `FACT_AirQuality[AQI_Bucket]` | One to many | Both directions | Yes | Gives the category its severity sort order and colour; bi-directional so the bucket slicer can filter the fact while the fact can highlight the bucket |

Then:

1. Right-click `DIM_Date` > **Mark as date table** > `Date`. Without this,
   `TOTALYTD`, `SAMEPERIODLASTYEAR` and `DATESINPERIOD` fail or return blanks.
2. Select `FACT_AirQuality[AQI_Bucket]` > Column tools > **Sort by column** >
   `DIM_Bucket[Sort_Order]` is not directly available across tables, so do the
   sorting inside `DIM_Bucket`: select `DIM_Bucket[AQI_Bucket]` > Sort by column
   > `Sort_Order`. Categories then appear Severe -> Good everywhere.
3. Set **Storage mode = Import** for all tables (default). At 18,265 rows
   DirectQuery would only add latency.
4. `File > Options > Current File > Data load`: uncheck *Allow fast
   data loads* once, so type errors surface during development.

---

## 5. Create the `_Measures` table, the parameter and the selector

### 5.1 Empty measures table

Home > Enter Data > leave the grid empty > name it `_Measures`. Model the
library in [`DAX_measures.dax`](DAX_measures.dax) by creating each measure while
`_Measures` is selected (Modeling > New Measure). Keeping all measures in one
hidden table is the standard way to stop a fact table filling up with 60 icons.

### 5.2 What-if parameter: PM2.5 threshold

Modeling > **New parameter > Numeric range** >
Name `PM25 Limit`, Minimum `0`, Maximum `300`, Increment `5`, Default `60`,
Agents off. This creates the table `'PM25 Limit'` with the column
`[PM25 Limit]` that `PM25 Limit Value` in the measure library reads.

> Default rationale: 60 ug/m3 is the 24-hour PM2.5 value in India's National
> Ambient Air Quality Standards for residential other-than-dedicated zones.
> Confirm against the current standard before publishing; the parameter exists
> precisely so this number is visible and editable instead of hidden inside a
> visual filter.

### 5.3 Measure selector (disconnected)

Home > Enter Data > paste:

| Measure |
|---|
| AQI |
| PM2.5 |
| PM10 |
| NO2 |
| CO |
| SO2 |
| O3 |
| Anomaly Rate % |

Name the query `Measure Selector`. It is **not** related to anything;
`Selected Metric Value` reads it via `SELECTEDVALUE`. Put its field in a
single-select dropdown slicer on page 2.

---

## 6. Page 1 - Executive Overview

Layout: 16-column grid, four KPI cards across the top, headline chart in the
middle band, evidence strip at the bottom.

| # | Visual | Fields / wells | Settings and interactions |
|---|---|---|---|
| 1.1 | Card | `[_Measures].[Observations]` | Format: whole number, thousands separator |
| 1.2 | Card | `Avg AQI` | Conditional background colour from `Is Above Average ?` |
| 1.3 | Card | `Severe or Very Poor Share %` | Percent, 1 decimal |
| 1.4 | Card | `YoY AQI Change %` | With the icon `AQI Trend Direction` overlaid |
| 1.5 | Slicer (vertical list) | `DIM_City[City]` | Selection type: Multi-item with **Select all**; cross-filter on |
| 1.6 | Slicer (between) | `DIM_Date[Date]` | Set `Type = Between`, default = whole range |
| 1.7 | Slicer (dropdown) | `DIM_Bucket[AQI_Bucket]` | Single or multi select |
| 1.8 | Line chart | Axis `DIM_Date[Date]` (or `[Year_Month_Label]`), Value `Avg AQI` | Turn **Analytics > Trend line = Off** and add a note: the fitted slope in notebook 05 is not statistically significant, so the line is for reading level, not direction |
| 1.9 | Donut | Legend `AQI_Bucket`, Values `Observations`, Detail label `Share of Visible Total %` | Colours from `DIM_Bucket[Colour]` (see 9.2) |
| 1.10 | Multi-row card | Fields `Cities Covered`, `Days Covered`, `Coverage Start`, `Coverage End`, `Panel Completeness %` | Header off |
| 1.11 | Text box | `Page 1 Title Context` (Insert > New visual > Numeric range, or use a Measure card) | Font 16, semibold |
| 1.12 | Table | `INSIGHTS[Category]`, `INSIGHTS[Insight]`, `INSIGHTS[Evidence Strength]` | Filter to `Evidence Strength = measured` for the headline strip; add the full table to page 5 |

**Page-level note (text box, required):** *"Averages here are descriptive. The
dataset shows no statistically significant difference between cities and no
significant time trend (notebook 05), so this page reports levels, not
improvements."*

---

## 7. Page 2 - Pollutant Intelligence

| # | Visual | Fields | Notes |
|---|---|---|---|
| 2.1 | Slicer | `Measure Selector[Measure]` | Single select, drives 2.2 and 2.3 |
| 2.2 | Line chart | Axis `DIM_Date[Year_Month_Label]`, Value `Selected Metric Value` | Sort X by `DIM_Date[Year]`, `DIM_Date[Month]` |
| 2.3 | Small-multiple bar | Axis `DIM_City[City]`, Value `Selected Metric Value` | Keeps the city comparison honest for any pollutant |
| 2.4 | Bar chart | Y `CORRELATION_WITH_AQI[Variable]`, Values `Pearson_r` | Data labels 3 decimals; add error note from 2.7 |
| 2.5 | Scatter | X `PM10`, Y `PM2.5`, Details `Date`, Legend `Anomaly_Label` | Sample or use `Anomaly` filter - 18,265 points render slowly on a laptop |
| 2.6 | Histogram (column) | X = `FACT_AirQuality[AQI]` binned (Create bin: 50 bins), Y = `Observations` | Shows the flat distribution that notebook 05 documents |
| 2.7 | Text box | static | *"Pearson r for every pollutant is below 0.23 in absolute value, yet a cross-validated random forest reproduces AQI with R^2 ~ 0.99. The association is strong and non-linear; a correlation bar chart alone would understate it. Correlation is not causation and no causal claim is made."* |
| 2.8 | KPI card | `Days PM2.5 Above Limit` with trend axis `DIM_Date[Year]` | Responds to the `PM25 Limit` parameter |

---

## 8. Page 3 - City Comparison

| # | Visual | Fields | Notes |
|---|---|---|---|
| 3.1 | Bar chart | Y `DIM_City[City]`, Value `Avg AQI`, Data colour by `Is Above Average ?` | Sort descending |
| 3.2 | Decomposition tree | Explain by `DIM_City[City]`, `DIM_Date[Season]`, `DIM_Date[Month_Name]`; Explain value `Avg AQI` | Shows the (small) contribution of each split |
| 3.3 | Matrix | Rows `DIM_City[City]`, Columns `DIM_Bucket[AQI_Bucket]`, Values `Observations` | Cell maximum = 100 % of row; turn on stepped background |
| 3.4 | Radar (chart store: *Radar/Dot Plot by xViz* or use a spider alternative; if no custom visual is allowed, substitute a clustered bar) | Dimension `pollutant`, Value `Avg <pollutant>` normalised | One series per city |
| 3.5 | Box plot (chart store) or clustered column | `DIM_City[City]`, `AQI` distribution | Quartile fields; the Python equivalent is `visualizations/eda/04_city_aqi_boxplot.png` |
| 3.6 | Table with drill-through | `City`, `Avg AQI`, `Median AQI`, `StdDev AQI`, `Severe or Very Poor Share %`, `Anomaly Rate %`, `City Rank By Avg AQI` | From `city_summary.csv` equivalents computed live so slicers apply |
| 3.7 | Text box | static | *"ANOVA on AQI across cities: F ~ 0.10, p ~ 0.98; Kruskal-Wallis agrees (notebook 05). With p far above 0.05 the correct reading of any visual difference here is 'not distinguishable from sampling variation', and the project therefore does not rank the cities as better or worse."* |

Drill-through target: create a hidden **Day Detail** page with `Date`,
all pollutant fields, `AQI`, `AQI_Bucket`, `Anomaly_Label` and
`Anomaly_Score` in a table, and set **Drill-through = DIM_City[City]**. Right
clicking a city then answers "which days made that number?".

---

## 9. Page 4 - Data Mining Intelligence

This page is what separates the project from a reporting dashboard: it exposes
the models, their settings and their weaknesses.

| # | Visual | Fields | Notes |
|---|---|---|---|
| 4.1 | Table | `K_SELECTION[K]`, `Inertia`, `Silhouette_Score` | Conditional data bar on silhouette |
| 4.2 | Line + column combo | X `K`, Column `Inertia`, Line `Silhouette_Score` | Mirror of `visualizations/clustering/01_elbow_silhouette.png` |
| 4.3 | Scatter | X `FACT_AirQuality[PC1]`, Y `PC2`, Legend `Cluster`, Tooltip `Cluster_Description` | Add a note: the two components together hold only ~23 % of the variance, so this projection is illustrative, not conclusive |
| 4.4 | Bar | X `CLUSTER_PROFILE[Cluster]`, Y `Cluster_Size`, tooltip `Share_%` | |
| 4.5 | Ribbon or clustered bar | `CLUSTER_PROFILE` Avg_* fields per cluster | Shows the profile differences are small |
| 4.6 | Funnel or bar | X `ANOMALY_BY_CITY[City]`, Y `Anomaly_Pct` | Reference line at 5 % = configured contamination (Analytics tab) |
| 4.7 | Card + text | `Anomaly Records`, `Anomaly Rate %`, `Anomaly Caption` | States the count depends on the configured contamination, not on a diagnosis |
| 4.8 | Table | `MODEL_COMPARISON` all columns | Baseline row must be visible - accuracy without the baseline is not a result |
| 4.9 | Bar with slider | X `CLASSIFICATION_PER_CLASS[Class]`, Y `Per-Class Recall`, legend `Model` | Filter out `macro avg` / `weighted avg` rows with a visual-level filter |
| 4.10 | Image | `visualizations/classification/02_confusion_matrices.png` | A true heatmap of the confusion matrix is not a native Power BI visual |
| 4.11 | Text box (required) | static | *"Accuracy near 99 % is explained by leakage, not skill: AQI_Bucket is a deterministic function of AQI (verified in notebook 02), and AQI is itself reconstructible from PM2.5 and PM10 (notebook 05). AQI is therefore excluded from the classifier, and macro-F1 0.78 is the honest headline number. No causal statement is made anywhere."* |

---

## 10. Page 5 - Trends & Insights

| # | Visual | Fields | Notes |
|---|---|---|---|
| 5.1 | Line chart | Axis `DIM_Date[Date]`, Value `Avg AQI`, Secondary values `Avg AQI 30-Day Moving Average` | The moving average smooths noise; the notebook reports no significant trend |
| 5.2 | Column | Axis `DIM_Date[Month_Name]` (sorted by `Month`), Value `Avg AQI` | Note: month effect p ~ 0.83 - differences are noise |
| 5.3 | Column | Axis `DIM_Date[Day_Name]` (sorted by `Day_of_Week`), Value `Avg AQI`, legend `Is_Weekend` | |
| 5.4 | Small multiples | Legend `DIM_Date[Season]`, X `DIM_Date[Month_Name]`, Value `Avg AQI` | |
| 5.5 | Table | `INSIGHTS` full, with `Quantitative Evidence`, `Derived From`, `Evidence Strength` | Wrap text, header on; this is the auditable conclusion list |
| 5.6 | Smart narrative (Insert > Smart Narrative) | Source `city_summary` (support table) | Auto-generated sentences; keep it, it demonstrates BI competence, but verify every sentence it writes |
| 5.7 | Bookmark navigator | Bookmarks: `Whole period`, `Last 3 years`, `Severe only` | View > Bookmarks > Add, then Insert > Button > Bookmarks navigator |
| 5.8 | Text box | static | Limitations block: uniform-looking distributions, no autocorrelation, no city or season effect, derived AQI, single-source data |

Optional **tooltip page** (1-page tiny report page, Page information > Tooltip =
On) carrying `Avg AQI`, `Median AQI`, `Anomaly Rate %` and `Observations`; set
`DATA_QUALITY` values (`Before Cleaning` / `After Cleaning`) here so hovering any
visual shows how clean the underlying data is.

---

## 11. Formatting standards (apply to every page)

### 11.1 AQI category colours

Use the exact hex codes exported in `dim_bucket.csv` (column `Colour`), which
come from `src/config.py::AQI_COLORS` and are the same colours the matplotlib
figures use:

| Category | Hex |
|---|---|
| Good | `#00E400` |
| Satisfactory | `#8BC34A` |
| Moderate | `#FFFF00` |
| Poor | `#FF9800` |
| Very Poor | `#F44336` |
| Severe | `#7E0023` |
| Unknown | `#9E9E9E` |

These are the project's own severity ramp (green → yellow → orange → red →
maroon), chosen so that colour order matches band order. They are **not**
presented as the official CPCB colour codes; if an official palette is required,
replace the `Colour` column in `src/config.py::AQI_COLORS` with values taken from
the CPCB source and regenerate.

The band boundaries behind the category names are in `dim_bucket.csv`
(`Band_Lower_AQI`, `Band_Upper_AQI`) and match the CPCB NAAQI ranges (0-50 Good,
51-100 Satisfactory, 101-200 Moderate, 201-300 Poor, 301-400 Very Poor,
401-500 Severe). Notebook 02 §5 recomputes `AQI_Bucket` from `AQI` with that
single table and reports 100 % agreement with the supplied labels, so the scale
is verified against the data rather than assumed.

Format > object properties > **Colour conditions** > Field value, or manually per
legend entry in the legend's **(i) > Colours** list. Manual legend colours are
fragile across refresh; a field-value colour rule on a `DIM_Bucket[Colour]`-backed
column is preferred.

### 11.2 Number formats

* AQI and concentrations: 1 decimal, unit in the axis title
* Percent measures: 1 decimal, and the measure name must end in `%`
* Counts: thousands separator, 0 decimals
* p-values: scientific (2 significant digits) - they are read as magnitudes, not as decimals

### 11.3 Non-negotiables

1. Every visual has a title that names the aggregate ("Average AQI", never "AQI").
2. Every chart with a time axis states the grain (daily / monthly average).
3. Every page has an evidence note in a text box, not in a footnote nobody opens.
4. No visual may display a per-city comparison without the significance statement
   from page 3 present on the same page.
5. No dual-axis chart, no pie with more than 6 slices, no 3-D anything.

---

## 12. Performance, refresh and publishing

* **Size.** 18,265 rows x ~35 columns compresses to a few MB; the whole file
  opens in seconds. No aggregation tables are needed. If a future version adds
  hourly data, add an aggregate table at city-month grain and keep the fact for
  drill-through.
* **Scatter charts** over the full fact are the only slow visual: use the
  `Anomaly` slicer or `Preview` visual-level filter, or a `Filter > Top N` rule.
* **Refresh.** CSV files on a local disk cannot be refreshed by the Power BI
  service. Supported options, in order of simplicity:
  1. Put `data/processed/*.csv` on OneDrive/SharePoint and use **Get Data >
     SharePoint folder**; schedule refresh in the service - the Python pipeline
     writes in place, so refresh picks up new content automatically.
  2. Publish to a workspace with an **On-premises data gateway** pointing at the
     project folder (works unchanged).
  3. Manual: re-run the notebooks, then **Refresh** in Desktop. Fine for a
     college submission.
* **Publish**: Home > Publish > a workspace named
  `Air Quality Intelligence`. Enable the dataset's **Quick insights** and
  **Auto page navigation** so the reviewer can explore without instructions.
* **Row-level security**: not required for this dataset (it contains no personal
  data). If a future version restricts city access, add a table
  `CityAccess(UserID, City)` and `DIM_City` > Manage roles with
  `[City] = USERPRINCIPALNAME()`-style DAX.

---

## 13. Validation checklist (dashboard vs notebooks)

Build the dashboard, then confirm each figure in Power BI against the artefact
that produced it. Do not accept "looks about right".

| Check | Expected source | Tolerance |
|---|---|---|
| `Observations` on an unfiltered page 1 | `data_quality_report.csv > After Cleaning > Total Rows` | exact |
| `Cities Covered` | same table, `Unique Cities` | exact |
| `Panel Completeness %` = 1 | notebook 01 panel-completeness cell | exact |
| Donut slice counts | `aqi_bucket_distribution.csv` | exact |
| `Anomaly Records` | `anomaly_results.csv` sum of `Anomaly` | exact |
| `Clusters In Use` | `cluster_profile.csv` row count | exact |
| Page 4 table values | `model_comparison.csv` | exact |
| Page 2 correlation bars | `correlation_with_aqi.csv` | exact |
| `Coverage Start` / `End` | `city_summary.csv` min/max of `First_Observation`, `Last_Observation` | exact |

If a value differs, the usual causes are: a slicer left on **All except** a few
members, a support table accidentally related to the fact, or `Is_Weekend`
imported as Text (so it filters nothing).

---

## 14. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `A function 'TOTALYTD' has been used in a measure that requires a date table` | `DIM_Date` not marked | Model view > right-click `DIM_Date` > Mark as date table |
| Time axis shows years only, or dates out of order | `Date` imported as Text | Power Query > change type to Date |
| Blank visuals when `DIM_Bucket` is used as a slicer | relationship inactive or wrong direction | Re-create `DIM_Bucket[AQI_Bucket] -> FACT_AirQuality[AQI_Bucket]` |
| `PM25 Limit Value` returns 60 although the slider moved | parameter table renamed | The parameter must be called `'PM25 Limit'` with column `[PM25 Limit]` |
| Percentages add to more than 100 % | `ALL()` used where `ALLSELECTED()` was intended | Use the supplied `Share of Visible Total %` |
| Average AQI changes when a slicer is added unexpectedly | bi-directional filter leaking from `DIM_Bucket` | Set `DIM_Bucket -> FACT` cross-filter direction to Single where a numeric average is used, or use `REMOVEFILTERS` in the measure |
| Very slow page render | scatter over the full fact + tooltips on every point | Add a visual-level filter, or use `Cluster`/`Anomaly` to limit points |
| "column 'PM2.5' was not found" | the file's header row was skipped or renamed on import | Re-import with **First row as header = true**; do not rename columns |

---

## 15. What to submit for this part of the project

1. The `.pbix` built from this guide (file name:
   `Air_Quality_Intelligence.pbix`).
2. This folder as-is: `POWER_BI_BUILD_GUIDE.md`, `DAX_measures.dax`.
3. Screenshots of all five pages saved as `dashboard/screenshots/page1.png` ...
   `page5.png`, referenced from the final report.
4. The CSVs in `data/processed/` (they are the dashboard's data dictionary).
