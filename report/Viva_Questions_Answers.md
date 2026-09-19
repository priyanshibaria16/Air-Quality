# Viva Preparation - Air Quality & Pollution Intelligence

**54 questions and answers, grouped by topic.** Every number in these answers was read
out of a file in this repository, not remembered. The line marked *Prove it* under each
answer names that file, so any claim can be checked in seconds while you are answering.

How to use this document:

1. Answer in your own words first; the wording below is a model, not a script.
2. If the panel asks something the project did **not** measure, say so. The last
   section lists those questions and the honest answer to each.
3. Re-generate the numbers after any re-run:
   `python tools/inspect_results.py <key>` prints any part of
   `data/processed/results.json` (for example `python tools/inspect_results.py
   classification/leakage`).

Environment the results were produced in: Python 3.11.9, pandas 3.0.6, NumPy 2.4.6,
scikit-learn 1.9.1, SciPy 1.17.1, matplotlib 3.11.2, `random_state = 42`.

---

## A. Dataset and data understanding

**Q1. What dataset did you use, and what does each row represent?**
One row is one city-day air-quality record: a city, a date, nine pollutant
concentrations, the Air Quality Index computed from them and the AQI category label.
The file is `data/raw/Air_quality_data.csv`, 18,265 rows and 13 columns, five cities,
from 2015-01-01 to 2024-12-31.
*Prove it:* `results.json` → `dataset`, or `notebooks/01_data_understanding.ipynb`.

**Q2. Which pollutants are in the file? Did you expect others?**
PM2.5, PM10, NO, NO2, NOx, NH3, CO, SO2 and O3. Benzene, Toluene and Xylene are absent -
they appear in the usual Kaggle version of this schema, so the difference is recorded
rather than assumed away.
*Prove it:* `dataset.detected_pollutants` and `dataset.columns_absent_vs_expected`.

**Q3. Did you assume the schema?**
No. `src/data_utils.py::load_raw()` accepts either `Air_quality_data.csv` or
`city_day.csv`, the date column is chosen from a list of candidates, and the pollutant
list is intersected with the columns that actually exist. Notebook 01 prints the real
columns before any analysis runs.
*Prove it:* `C.RAW_CANDIDATES`, `C.DATE_COL_CANDIDATES`, `C.pollutant_columns()`.

**Q4. What were the missing values and duplicates?**
Zero missing cells and zero exact duplicate rows on load, and no duplicated
(City, Date) pair - the panel is complete and balanced: 3,653 rows for each of the five
cities. Nothing was imputed, because there was nothing to impute.
*Prove it:* `dataset.missing_before`, `dataset.duplicates_before`; notebook 02 §1-§2.

**Q5. How do you know the file is trustworthy?**
I tested it. The nine concentration columns are each indistinguishable from a uniform
draw over a fixed range (Kolmogorov-Smirnov against uniform is not significant, e.g.
PM2.5 D = 0.0063, p = 0.461) while the normality test rejects hard (Shapiro-Wilk
p = 2.2e-37), excess kurtosis sits near -1.2, day-to-day autocorrelation is about 0.004
at lag 1, and city, month, season and year differences are all statistically
indistinguishable. Real monitoring data behaves the opposite way. The conclusion is
reported in the report (section 12.5) as a property of the file, and the mining results
are described as properties of this file rather than as findings about Indian air.
*Prove it:* `distribution_tests`, `autocorrelation`, `group_test_table`.

---

## B. Cleaning and preprocessing

**Q6. What is data cleaning, and what did you actually do?**
Making the types, ranges and identifiers of a dataset internally consistent while
recording every change. Here: read-only load, duplicate removal, date parsing, numeric
type verification per column, city-name normalisation, an impossible-value test
(negative concentrations), a range/flag test for extremes, and a uniqueness check on
(City, Date). Forty-three log entries, each with the number of values affected.
*Prove it:* `cleaning_log`, `data/processed/data_quality_report.csv`, notebook 02.

**Q7. How did you handle missing values, and why not impute?**
There were none in the measured columns, so no imputation was applied. For derived
columns, blanks are *expected* where the maths is undefined - a ratio whose denominator
is zero, or the first day of a rolling window - and notebook 09 verifies that blanks
appear only in that documented set of derived columns.
*Prove it:* notebook 09 §7, "blank cells by column".

**Q8. What do you do if a value is negative in a concentration column?**
Treat it as an invalid measurement, not as an outlier: it cannot be rescaled into
plausibility. The check is run per column and its count is logged; if any appeared, they
would be set to missing and then handled by the documented rule for that column.
*Prove it:* notebook 02 §4, `preprocessing.py`.

**Q9. Did you delete outliers?**
No. Extreme values are flagged with boolean columns and left in the data, because in
air quality an extreme value is often the event worth studying. Deleting them would also
make the anomaly analysis in notebook 07 impossible to interpret.
*Prove it:* `outlier_cols` flag columns in notebook 02 §4; `anomaly_results.csv`.

**Q10. What is the difference between an outlier and an anomaly in your project?**
An outlier flag is univariate - "this one column is far out". An anomaly is
multivariate - Isolation Forest asks whether the whole nine-pollutant vector is unusual
relative to the joint distribution. A day can be unremarkable on every single column and
still be jointly unusual.
*Prove it:* notebook 02 §4 versus notebook 07 §2.

**Q11. Which cleaning step mattered most, and why?**
The one that changed a reported number from wrong to right: the AQI band table in
`src/config.py` had Moderate and Satisfactory swapped. Rebuilding `AQI_Bucket` from AQI
with that table agreed with the supplied label on only 76.07% of rows. After verifying
the boundaries against the raw data and the CPCB ranges, the agreement is 100%, and the
band table is now the single source used by every part of the project.
*Prove it:* notebook 02 §5 (crosstab and per-label ranges), notebook 09 §7.

---

## C. Feature engineering

**Q12. What features did you create, and why?**
Calendar features (Year, Month, Month_Name, Season, Day, Weekday, Is_Weekend),
compositional ratios (PM2.5/PM10, NO2/NOx, O3/PM10), rolling and lag features
(AQI_Rolling_7, AQI_Rolling_30, AQI_Change_1d), per-city percentiles and a cluster
description. Each exists to make a question expressible: seasonality needs a season
column, "how dirty is this day for this city" needs a within-city percentile.
*Prove it:* `feature_inventory`, `feature_notes`, notebook 03.

**Q13. Why are ratios computed with a guard, and what do you do about zero denominators?**
Because a ratio with a zero denominator is undefined, not infinite. The guard writes a
blank instead of a spurious number, and the blank is documented as an expected gap.
Filling it with zero would invent a physical claim.
*Prove it:* `feature_engineering.py`; the blank-cell audit in notebook 09 §7.

**Q14. Why did you not recompute AQI yourself?**
The file already carries AQI, and the project's questions are about the supplied index.
Recomputing it would silently substitute my formula for the publisher's. Instead I test
it: `AQI_Bucket` is reproducible from AQI on 100% of rows, and AQI itself is rebuilt to
cross-validated R2 = 0.9588 from PM2.5 and PM10 alone. That is the leakage evidence used
in notebook 08.
*Prove it:* `aqi_structure.forward_selection`; notebook 02 §5.

---

## D. Exploratory data analysis and statistical testing

**Q15. What is EDA, and what did it show here?**
Describing a dataset's distributions, spread, relationships and oddities before modelling.
Here: AQI values sit mainly in the Poor-to-Severe bands, average AQI by city spans only
1.57 points (Mumbai 318.19, Chennai 316.62) on a 0-500 index, monthly and
seasonal profiles are visually flat, and every pollutant distribution is flat-topped
rather than right-skewed.
*Prove it:* `visualizations/eda/*.png`, `descriptive_statistics`, `city_summary.csv`.

**Q16. Which city has the highest average AQI? Can you claim it is the most polluted?**
Mumbai has the highest average (318.185) and Delhi is third (317.725), but the claim
stops at "highest in this file": one-way ANOVA on AQI by city gives p = 0.983
(Kruskal-Wallis p = 0.981), so the differences are not statistically detectable. The
dashboard shows the ranking, and `dashboard/KPI_DEFINITIONS.md` states the context that
must accompany it.
*Prove it:* `city_summary.csv`, `group_tests.City`.

**Q17. Why report a non-parametric test next to ANOVA?**
ANOVA assumes approximately normal group residuals. Since normality is rejected for every
pollutant and for AQI, Kruskal-Wallis is the test that does not need that assumption;
both are reported and both agree here.
*Prove it:* `group_tests`, `distribution_tests`.

**Q18. Is pollution increasing over the ten years?**
Not detectably. Ordinary least squares of AQI on time gives a slope of 0.0366 index
points per year with p = 0.9001 and r = 0.0009. The verdict recorded in the results is
"no statistically detectable trend", and the report states that rather than describing a
seasonal cycle as a long-term rise.
*Prove it:* `trend_test`, notebook 05.

---

## E. Correlation and predictability

**Q19. What is Pearson correlation, and what were its limits here?**
Pearson r measures the strength of a *linear* relationship between two continuous
variables, is symmetric, and says nothing about cause. Here it also says very little
about prediction, which is why I did not stop at it.
*Prove it:* `correlation_matrix`, `correlation_with_aqi`.

**Q20. What did the correlation analysis find between pollutants and AQI?**
Almost nothing linear: the pollutant-pollutant matrix is close to zero everywhere, and
multiple linear regression of AQI on all nine pollutants gives R2 = 0.0579
(adjusted 0.0574, RMSE 110.5).
*Prove it:* `linear_fit`, `correlation_with_aqi`, `visualizations/correlation/01_*.png`.

**Q21. Then how can AQI be reproducible from pollutants?**
Because the relationship is non-linear. A gradient-boosted tree predicts AQI from the
same nine columns with cross-validated R2 = 0.9969 and MAE 1.21 index points, against a
linear R2 of 0.0579 - a gap of 0.939. Greedy forward selection reaches 0.9588 with
PM2.5 + PM10 and 0.9862 after adding O3.
*Prove it:* `predictability`, `aqi_structure.forward_selection`, notebook 05 §6.

**Q22. What does that combination - near-zero pairwise correlation but near-perfect
predictability - tell you?**
That AQI is a deterministic function of a few columns with a non-additive form (a
maximum-of-sub-indices structure, as CPCB's index is), not a linear co-movement. It is
also the diagnostic that a generated file was left in place of a monitoring record, and
it is why I test predictability and not only correlation.
*Prove it:* `predictability.verdict`, `tools/probe_aqi_rule.py`.

---

## F. K-Means clustering

**Q23. Explain K-Means in your own words.**
It partitions rows into k groups by alternating two steps: assign each row to its
nearest centroid, then move each centroid to the mean of its assigned rows, until the
assignments stop changing. It minimises within-cluster sum of squares (inertia), so it
finds round, similarly sized blobs and needs scaled inputs.
*Prove it:* `src/clustering.py`, notebook 06.

**Q24. How did you choose k?**
I ran k = 2..10 and recorded both inertia and silhouette. The elbow rule (first k where
the inertia improvement falls below 5%) suggested 4; the silhouette maximum was at 2 with
0.0838. I took k = 2 because with a weak silhouette the extra clusters would not be
defensible, and I reported the disagreement instead of choosing the story I liked.
*Prove it:* `clustering.k_table`, `clustering.choice`,
`visualizations/clustering/01_elbow_silhouette.png`.

**Q25. What is the silhouette score, and what does 0.0838 mean?**
For each row, (b - a) / max(a, b), where a is the mean distance to its own cluster and b
the mean distance to the nearest other cluster; the score is the average. +1 is tight and
well separated, 0 means the row sits between clusters, negative means it is probably in
the wrong cluster. 0.0838 means the structure is weak: clusters exist because K-Means
always returns some, not because the data demanded two.
*Prove it:* `clustering.choice.silhouette`, notebook 06 §4.

**Q26. What are centroids, and were any cluster empty?**
The mean vector of each cluster, in scaled feature space. The k-selection table records
Clusters_Used at every k, so empty clusters would be visible; at k = 2 both were used.
*Prove it:* `k_selection_table.csv`, `clustering.k_table`.

**Q27. What did the clusters mean here?**
They split the panel on overall concentration level: the profile table shows one cluster
with means around the upper half of each pollutant's range and one around the lower half,
which is exactly what a uniform, independent generator produces when you force k = 2.
Sizes and mean pollutant levels are in `cluster_profile.csv`; each observation's label is
in `cluster_results.csv` for the dashboard.
*Prove it:* `clustering.profile`, `clustering.descriptions`.

**Q28. What happens if you cluster without scaling?**
PM10 (values up to 600) dominates the squared distance and CO (up to 10) contributes
almost nothing, so the clusters are effectively one-variable splits. Scaling puts every
pollutant on equal footing; that is why the pipeline pipes `StandardScaler` before
`KMeans`.
*Prove it:* notebook 06 §1-§2.

---

## G. Scaling and PCA

**Q29. What does StandardScaler do, and why before K-Means and logistic regression?**
It replaces each column with (x - mean) / standard deviation, giving zero mean and unit
variance. Distance-based and gradient-based methods are sensitive to the original units;
trees are not, which is why the tree models are used unscaled.
*Prove it:* `src/clustering.py`, `src/classification.py`.

**Q30. Did you use PCA? Should you have clustered on the principal components?**
PCA is used only to draw the scatter plot. The two leading components explain 22.90% of
variance, so a plot in that plane is a poor summary and clustering on it would throw away
most of the information. All modelling used the nine scaled columns; PCA also has no
supervision, so it cannot know what makes air "bad".
*Prove it:* `clustering.pca_explained_variance`, `visualizations/clustering/02_pca_clusters.png`.

**Q31. If PCA were applied before fitting a model on training data, what is the rule?**
Fit it on the training split only and transform test data with the fitted components -
otherwise test-set variance leaks into the feature space. I avoided the issue by not
using PCA as a modelling step.
*Prove it:* `notebooks/08_classification.ipynb` §1 (leakage discipline).

---

## H. Isolation Forest and anomaly detection

**Q32. How does Isolation Forest work?**
It builds many random trees, each splitting on a random feature and a random value. An
unusual point is separated from the rest in fewer splits, so the mean path length is
short; the score is derived from that average path length relative to its expectation.
It is a randomised method, so `random_state = 42` is pinned.
*Prove it:* `anomaly.params`, `src/anomaly_detection.py`, notebook 07.

**Q33. How many anomalies did you find, and is that a real rate?**
914 of 18,265 observations (5.00%). The share is not a discovery: `contamination = 0.05`
tells the algorithm what fraction to flag. The honest statement is "at a 5% assumed
sensitivity, these are the 914 jointly most unusual days".
*Prove it:* `anomaly.stats` (including its Note field), `anomaly_results.csv`.

**Q34. What did the anomalies look like?**
They are spread almost evenly across cities (168-200 per city, 4.60%-5.47%) and across
years (3.67%-5.92%), and the flagged-versus-normal pollutant means differ by at most
about 14.6% (NO), with no single pollutant dominating. That is what joint unusualness
looks like in data whose columns are independent.
*Prove it:* `anomaly.by_city`, `anomaly.by_year`, `anomaly.pollutant_comparison`.

**Q35. Why Isolation Forest and not a Z-score?**
A per-column Z-score finds univariate extremes and misses multivariate combinations; with
nine correlated-or-not columns it also needs a threshold per column. Isolation Forest
scores the whole vector at once and scales to high dimensions without distance
explosions. For completeness the cleaning step keeps univariate flags as well.
*Prove it:* notebook 07 §1.

---

## I. Classification, leakage and metrics

**Q36. What did you classify, with what, and on what split?**
`AQI_Bucket` (six classes) from the nine pollutant concentrations only, using a prior
baseline, logistic regression in a `StandardScaler` pipeline, decision tree, random forest
and histogram gradient boosting; a stratified 75/25 split (13,698 train / 4,567 test)
with `random_state = 42` and three-fold cross-validation.
*Prove it:* `classification.split_info`, `model_comparison.csv`.

**Q37. What were the results?**
Random forest was best on the leak-proof feature set: accuracy 99.28%, macro-F1 0.7765,
lift 69.17 percentage points over the 30.11% majority-prior baseline; cross-validated
accuracy 99.17% (sd 0.17), so the result is not a lucky split. Logistic regression
reached only 31.55%, barely above the baseline.
*Prove it:* `model_comparison.csv`, `visualizations/classification/01_model_comparison.png`.

**Q38. Define data leakage, and show the version in your project.**
Leakage is a feature that carries the answer through a route the real prediction
situation would not have. `AQI_Bucket` is a band of `AQI`, so AQI *is* the target.
Including it raises accuracy from 99.28% to 99.96%, an inflation of 0.68 points, and
macro-F1 from 0.7355 to 0.8276. AQI is therefore excluded from every reported model, and
the experiment is shown rather than hidden.
*Prove it:* `classification.leakage`, notebook 08 §2.

**Q39. Why is accuracy a bad headline metric here?**
Because the classes are extremely imbalanced: Satisfactory has 113 rows (0.62%) and Good
has 6 (0.03%). A model that never predicts Good is right 99.97% of the time. Macro-F1 and
per-class recall expose that; accuracy hides it.
*Prove it:* `classification.class_balance`, `classification.per_class`.

**Q40. Explain precision, recall, F1 and the confusion matrix.**
Precision = predicted positives that were correct (TP/(TP+FP)); recall = real positives
found (TP/(TP+FN)); F1 is their harmonic mean, so a class needs both to score. The
confusion matrix lays out actual against predicted per class, from which per-class
precision, recall and F1 are computed; macro-F1 averages the class F1s equally, weighted
F1 averages them by support.
*Prove it:* `confusion_matrices.csv`, `visualizations/classification/02_*.png`,
`03_per_class_recall.png`.

**Q41. Which feature carried the classification signal?**
The importance ranking from a reference random forest is dominated by PM10 and PM2.5,
with a long tail - consistent with the forward-selection result on AQI, since the label
is derived from it.
*Prove it:* `feature_importance.csv`,
`visualizations/classification/04_feature_importance.png`.

**Q42. Why stratified splitting, and what else would you consider for imbalance?**
Stratification keeps the class proportions in both splits, so the 113 Satisfactory rows
do not vanish from the test set. Beyond that, `class_weight="balanced"` and resampling
(SMOTE) are the usual options; I report the imbalance and use metrics that cannot be
flattered by it instead of silently resampling.
*Prove it:* `classification.split_info.stratified`, notebook 08 §1.

---

## J. Power BI and business intelligence

**Q43. What is the difference between data mining and business intelligence here?**
Data mining answers a fixed question set by fitting models and testing structure; BI
makes the *processed result* interactive so an untrained user can ask their own
question. The notebooks discover, the dashboard disseminates - and it only disseminates
what was computed, because it imports exported CSVs and cannot reach Python.

**Q44. Describe your data model.**
A star schema: `FACT_AirQuality` (= `air_quality_cleaned.csv`) with three dimensions -
`DIM_Date`, `DIM_City`, `DIM_BUCKET`. Model outputs (`cluster_results`,
`anomaly_results`, `model_comparison`, `classification_results`) are deliberately
**not** related to the fact table, because they are summaries at a different grain and a
wrong relationship would silently double-count measures.
*Prove it:* `dashboard/POWER_BI_BUILD_GUIDE.md` §2-§4.

**Q45. What KPIs did you build?**
Average AQI, total observations, total cities, average PM2.5 and PM10, anomaly count,
plus severity share, days above the adjustable limit, year-to-date and year-over-year
measures, per-city ranks and a category share. Each has a DAX definition, its source
column, its unit and an explicit statement of what it does *not* mean.
*Prove it:* `dashboard/KPI_DEFINITIONS.md`, `dashboard/DAX_measures.dax`.

**Q46. What is a slicer, and what do yours do?**
A slicer is a visual filter - here City, Year, Month, Season and AQI category - that
applies its filter context to every visual on the page. Cross-filtering between visuals
is what lets a user click "Delhi" and "Monsoon" and see the whole page recompute.
*Prove it:* `dashboard/POWER_BI_BUILD_GUIDE.md` §7 (interaction contract).

**Q47. Why do your measures use DIVIDE and ALLSELECTED?**
`DIVIDE` returns blank instead of raising on a zero denominator, which matters for ratios
over an empty filter selection. `ALLSELECTED` keeps the measure responsive to the user's
slicers while ignoring the local row context of a visual, which is what a share-of-total
or a cross-filtered reference line needs.
*Prove it:* any measure in `DAX_measures.dax`, e.g. the category-share measures.

**Q48. What is the what-if parameter for?**
The regulatory limit is not a fact of this dataset. A what-if parameter (default 60
µg/m³, the CPCB 24-hour PM2.5 standard) lets the user move the threshold and see
"days above limit" recompute, instead of baking one number into the model. The default's
provenance, and the instruction to re-verify it before quoting compliance, are documented.
*Prove it:* `dashboard/KPI_DEFINITIONS.md` §3.

**Q49. Which five pages does the dashboard have?**
Overview (KPIs and the six headline visuals), City Analysis, Pollutant Analysis,
Pattern Discovery (clusters, anomalies, model comparison), and Trends (yearly, monthly,
seasonal, YTD and year-over-year).
*Prove it:* `dashboard/POWER_BI_BUILD_GUIDE.md` §5-§6.

---

## K. Data mining concepts, limitations and future scope

**Q50. Which data-mining techniques did you use, and why those three families?**
Descriptive statistics with significance testing (so a difference is only claimed if it
survives a test), unsupervised clustering (to summarise 18,265 rows as profiles), outlier
detection (to find jointly unusual days without a target), and supervised classification
(to measure how predictable the category is from chemistry alone). Each family maps onto
a different one of the project's ten questions.

**Q51. What are the project's main limitations?**
The seven stated in the brief - limited cities and period, missing values, correlation is
not causation, K-Means depends on features and scaling, anomaly detection measures
statistical unusualness not environmental cause, classification depends on data quality
and class distribution, and the project does not replace official monitoring - plus seven
more that the analysis itself produced, the most important being the file's undocumented
provenance and its uniform, independent columns.
*Prove it:* report section 25; the three `insights.csv` rows labelled `interpretation` rather
than `measured`.

**Q52. What would you add next?**
Twelve items in three tiers: data (real-time CPCB/OpenAQ feeds, more cities and stations,
satellite aerosol, weather variables), modelling (forecasting once a genuinely
autocorrelated series exists, sequence models, validated anomaly detection, SHAP
explanations) and delivery (live and mobile Power BI, automated public alerts, geospatial
visuals that need coordinates this file lacks).
*Prove it:* report section 26.

**Q53. What did you change your mind about during the project?**
The band-table bug (Q11) and the non-linear AQI result (Q21-Q22). The first made me stop
trusting a convenient "100% consistent" claim and start verifying it; the second made me
add a tree-based predictability probe to the correlation notebook, because the Pearson
matrix alone would have produced the wrong conclusion that AQI is unexplainable.

**Q54. What can this project *not* answer, and what is your answer when asked?**
It cannot rank Indian cities by true pollution, cannot forecast, cannot attribute any
 pollutant source, and cannot certify regulatory compliance. The answer in those cases is:
"the evidence in this dataset is insufficient, and here is the test that shows why" -
the significance tests in `group_tests`, the trend test, and the integrity finding in
report section 12.5.
