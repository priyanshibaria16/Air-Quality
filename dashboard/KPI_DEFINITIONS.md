# KPI documentation

Every number a viewer can see on the dashboard, with the measure that computes
it, the columns it reads, its unit and - most importantly - what it does **not**
mean. The measures themselves are in `dashboard/DAX_measures.dax`; the build
steps are in `dashboard/POWER_BI_BUILD_GUIDE.md`.

Rule applied throughout (brief §34): no official environmental threshold is
invented here. Where a threshold is used, its authority is named and the reader
is told to verify it against the source.

---

## 1. Headline KPIs (Page 1 - Executive Overview)

| KPI (card title) | Definition in words | DAX measure | Columns read | Unit | How to read it |
|---|---|---|---|---|---|
| Average AQI | Mean AQI of the rows selected by the current filters/slicers | `Avg AQI` | `FACT_AirQuality[AQI]` | index (0-500 as supplied) | An average of an index, not a concentration; compare across the same filter context only |
| Total Cities | Count of distinct city names in the current selection | `Cities Covered` | `FACT_AirQuality[City]` | count | 5 when nothing is filtered - the dataset covers 5 cities, not "all of India" |
| Total Observations | Number of city-day records in the current selection | `Observations` | fact table rows | count | One row = one city on one day, never a mixture |
| Average PM2.5 | Mean PM2.5 concentration in the current selection | `Avg PM2.5` | `FACT_AirQuality[PM2.5]` | µg/m³ (as supplied) | Reported with its unit; not compared to a limit unless the limit card is also read |
| Average PM10 | Mean PM10 concentration in the current selection | `Avg PM10` | `FACT_AirQuality[PM10]` | µg/m³ (as supplied) | Same as above |
| Anomaly Count | Rows the Isolation Forest flagged as unusual | `Anomaly Records` | `FACT_AirQuality[Anomaly]` (0/1) | count | Statistical unusualness only - see §5 |

Supporting context cards on the same page: `Median AQI`, `Min AQI`, `Max AQI`,
`StdDev AQI`, `Days Covered`, `Coverage Start`, `Coverage End`,
`Panel Completeness %`, `Severe or Very Poor Days`, `Severe or Very Poor Share %`,
`Good or Satisfactory Days`, `Good or Satisfactory Share %`.

---

## 2. Pollutant KPIs (Page 2 - Pollutant Intelligence)

| KPI | Definition | DAX measure | Unit |
|---|---|---|---|
| Average concentration, per pollutant | Mean of that pollutant over the visible rows | `Avg PM2.5`, `Avg PM10`, `Avg NO`, `Avg NO2`, `Avg NOx`, `Avg NH3`, `Avg CO`, `Avg SO2`, `Avg O3` | µg/m³, except CO (mg/m³ as supplied) |
| Fine Particle Fraction | `Avg PM2.5 / Avg PM10` - share of particulate mass that is the finer fraction | `Fine Particle Fraction` | ratio (dimensionless) |
| Days above PM2.5 limit | Rows whose PM2.5 exceeds the parameter value | `Days PM2.5 Above Limit` | count |
| % days above PM2.5 limit | That count over `Observations` | `Days PM2.5 Above Limit %` | % |
| Severe days | Rows with AQI above 400 (the "Severe" band of the AQI scale) | `Days AQI Above 400` | count |
| Bucket share | Rows in the slicer-selected AQI band over the visible total | `Records in Current Bucket`, `Share of Visible Total %` | count, % |

`Fine Particle Fraction` is descriptive. A high ratio is *consistent with*
combustion-dominated emissions and a low one with dust, but this dataset has no
source-reconciliation or speciation data, so the dashboard does not claim to
identify emission sources.

---

## 3. Thresholds actually used, and where they come from

| Threshold | Value used | Authority | Status |
|---|---|---|---|
| AQI category bands | 0-50 Good, 51-100 Satisfactory, 101-200 Moderate, 201-300 Poor, 301-400 Very Poor, 401-500 Severe | Central Pollution Control Board (CPCB), National Air Quality Index, Technical Report, CPCB, New Delhi, 2014 | **Verified against this dataset**: notebook 02 §5 recomputes `AQI_Bucket` from `AQI` with these breakpoints and reports 100 % agreement with the supplied labels |
| PM2.5 24-hour limit (default of the `PM25 Limit` what-if parameter) | 60 µg/m³ | India's National Ambient Air Quality Standards for PM2.5 (24-hour value for residential and other areas), CPCB | **User-adjustable and to be re-verified before quoting**: the parameter exists so the number is visible on the page rather than hidden in a visual. This project does not perform a compliance assessment - the dataset has no monitoring-station, averaging-time or instrument metadata, which a compliance statement requires |
| "Severe days" cut | AQI > 400 | Top band of the same CPCB scale | Same as the band row above |

No other limit appears anywhere in the model. In particular the dashboard does
**not** use WHO air-quality guideline values, because none were verified from a
primary source as part of this work; adding them means adding a documented
reference and a second parameter, not editing a label.

---

## 4. Comparison and trend KPIs (Pages 3 and 5)

| KPI | Definition | DAX measure | Note |
|---|---|---|---|
| Variance vs Overall AQI | Selected city's `Avg AQI` minus the all-city `Avg AQI` under the same date filter | `Variance vs Overall AQI`, `Avg AQI All Cities` | Uses `REMOVEFILTERS` on City for the reference value, so the comparison is against the whole period, not the city itself |
| YoY AQI Change | `Avg AQI` minus the same measure for the previous year | `Avg AQI Previous Year`, `YoY AQI Change`, `YoY AQI Change %` | `SAMEPERIODLASTYEAR`; needs a marked date table |
| 30-day moving average | Mean AQI over the 30 days ending on the current date | `Avg AQI 30-Day Moving Average` | `DATESINPERIOD` |
| Year to date | Mean AQI from 1 January of the selected year | `Avg AQI Year to Date` | `TOTALYTD` |
| Trend direction | Text: rising / falling / broadly flat | `AQI Trend Direction` | Compares the moving average with the period average; it is a label, not a significance test |
| Worst / Best city, City rank, Worst month | Ranking helpers | `Worst City By Avg AQI`, `Best City By Avg AQI`, `City Rank By Avg AQI`, `Worst Month By Avg AQI` | `RANKX` over `ALLSELECTED` |
| Is Above Average ? | Yes/No flag for conditional formatting | `Is Above Average ?` | Drives colour rules only |

Honesty note carried on Page 5 of the dashboard: differences between cities and
between months in this dataset are **not** statistically significant (one-way
ANOVA on AQI: city p = 0.983, month p = 0.826; OLS yearly trend slope
+0.037 index-points/year, p = 0.900 - `data/processed/results.json`). The
rankings above therefore describe the sample, and must not be presented as
evidence that one city is genuinely dirtier than another.

---

## 5. Data-mining KPIs (Page 4 - Data Mining Intelligence)

| KPI | Definition | DAX measure | Assumption to disclose |
|---|---|---|---|
| Clusters In Use | Number of distinct cluster labels present | `Clusters In Use` | k = 2, chosen by silhouette (0.084) after the elbow; the score is low, so the split is weak and is described as a description, not a discovery |
| Records in Current Cluster | Rows carrying the selected cluster label | `Records in Current Cluster` | - |
| Most Common Cluster | Modal cluster label in the current selection | `Most Common Cluster` | Text; changes with filters |
| Anomaly Records | Rows flagged `Anomaly = 1` by Isolation Forest | `Anomaly Records` | 914 rows = 5.00 % of 18,265 |
| Anomaly Rate % | `Anomaly Records / Observations` | `Anomaly Rate %` | Will sit near the configured contamination rate by construction |
| Configured Contamination % | The `contamination` value used at training time, exported as a column | `Configured Contamination %` | 0.05 - a modelling choice, **not** an estimate of how often real pollution events occur |
| Extreme PM Episodes | Rows flagged as an extreme episode on any pollutant (per-pollutant outlier indicators) | `Extreme PM Episodes` | IQR-based flag, computed in Python, not by DAX |
| Extreme PM Episode Rate % | That count over `Observations` | `Extreme PM Episode Rate %` | Same |
| Best Model Accuracy % | Highest test accuracy among the imported model rows | `Best Model Accuracy %` | From `MODEL_COMPARISON[Accuracy_%]` |
| Best Model Macro F1 | Highest macro-averaged F1 | `Best Model Macro F1` | 0.777 for the best model - accuracy alone overstates performance because the classes are imbalanced |
| Baseline Accuracy % | Most-frequent-class (prior) baseline | `Baseline Accuracy %` | 30.11 %; every model must be read against this, not against 0 % |
| Lift over Baseline (pp) | Best accuracy minus baseline accuracy | `Lift over Baseline (pp)` | +69.17 pp |
| Per-Class Recall / Precision / F1 | Metrics for the class on the axis/slicer | `Per-Class Recall`, `Per-Class Precision`, `Per-Class F1` | From `CLASSIFICATION_PER_CLASS`; the rare classes (`Good`: 6 rows, `Satisfactory`: 113 rows) have unstable scores |
| Test Records in Class | Number of held-out rows behind a per-class score | `Test Records in Class` | Read this before quoting any per-class figure |

`Anomaly Caption` and `Leakage Note` are text measures placed next to the
relevant visuals so the caveat travels with the number: an anomaly here means
"statistically unusual given the other pollutants", and the classifier's AQI
input was deliberately removed because `AQI_Bucket` is a deterministic banding of
`AQI` (predicting the target from itself).

---

## 6. Interactivity contract (brief §33)

| Requirement | How it is met |
|---|---|
| Slicers affect charts | `City`, `Year`, `Month_Name`, `AQI_Bucket`, `Season` slicers are page-level and bound to the dimension tables, so they filter `FACT_AirQuality` through the relationships |
| Charts cross-filter each other | Default single-select cross-filtering is left on between the fact-backed visuals; the model-result tables (`MODEL_COMPARISON`, `CLASSIFICATION_PER_CLASS`) are unrelated and are set to **None** so they cannot filter the fact table |
| Tooltips are useful | Each visual's tooltip field list carries the pollutant value, its unit and the record count behind the mark |
| Titles update where appropriate | Visual titles reference measures (`Page 1 Title Context`, `Selected Metric Value`, `Selected Metric Unit`) so the title states the active selection |
| Units shown | Every concentration measure is formatted with its unit; `Selected Metric Unit` supplies the unit for the metric-selector visual |
| No misleading axes | Column charts start at zero; ratio and index measures are labelled as dimensionless; no truncated axes |
| No 3-D | All visuals are 2-D (bar, line, area, matrix, card, scatter) |
| Readable | Category colours come from `DIM_Bucket[Colour]` with `Sort_Order` controlling legend order, so severity order is preserved everywhere |

---

## 7. Numbers a viewer should never see quoted without their context

| Figure | Value in this dataset | Required companion statement |
|---|---|---|
| Anomaly Rate % | 5.00 % | "…by construction: the Isolation Forest was configured to flag 5 %" |
| Best Model Accuracy % | 99.28 % | "…with macro-F1 0.777 on imbalanced classes, and +0.68 pp of that accuracy is data leakage from keeping AQI as a feature" |
| City ranking | Mumbai first on average AQI | "The five city averages span 316.62-318.19 index points and the difference is not statistically significant (one-way ANOVA p = 0.983)" |
| Worst month | from `Worst Month By Avg AQI` | "Month effect not significant (p = 0.826)" |
| Fine Particle Fraction | ratio | "Descriptive only; the dataset cannot identify emission sources" |
| Days above PM2.5 limit | depends on parameter | "Parameter default 60 µg/m³ from India's NAAQS 24-hour standard; this is not a compliance assessment" |
