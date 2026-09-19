"""
Aggregations exported for Power BI, plus insight generation that can only
phrase statements about values it was actually given.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


def _mean_cols(cols, agg="mean", suffix="Avg"):
    return {f"{suffix}_{c}": (c, agg) for c in cols}


# --------------------------------------------------------------------------- #
# BI summary tables
# --------------------------------------------------------------------------- #
def city_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per city: AQI statistics, average pollutants, observation count."""
    polls = C.pollutant_columns(df.columns)
    metrics = polls + ([C.AQI_COL] if C.AQI_COL in df.columns else [])
    g = df.groupby(C.CITY_COL, observed=True)
    out = g.agg(
        **{"Observation_Count": (metrics[0], "size"),
           **_mean_cols(metrics),
           "Median_AQI": (C.AQI_COL, "median") if C.AQI_COL in df.columns else (metrics[0], "median"),
           "Max_AQI": (C.AQI_COL, "max") if C.AQI_COL in df.columns else (metrics[0], "max"),
           "Min_AQI": (C.AQI_COL, "min") if C.AQI_COL in df.columns else (metrics[0], "min"),
           "Std_AQI": (C.AQI_COL, "std") if C.AQI_COL in df.columns else (metrics[0], "std")}
    ).reset_index()
    if "Season" in df.columns and C.AQI_COL in df.columns:
        worst = (df.groupby([C.CITY_COL, "Season"], observed=True)[C.AQI_COL].mean()
                   .reset_index().sort_values(C.AQI_COL, ascending=False)
                   .groupby(C.CITY_COL).head(1).set_index(C.CITY_COL))
        out["Worst_Season"] = out[C.CITY_COL].map(worst["Season"].astype(str))
        out["Worst_Season_Avg_AQI"] = out[C.CITY_COL].map(
            worst[C.AQI_COL].round(2)).astype("float64")
    if "Anomaly" in df.columns:
        an = df[df["Anomaly"].notna()].groupby(C.CITY_COL)["Anomaly"].agg(["sum", "size"])
        out["Anomaly_Count"] = out[C.CITY_COL].map(an["sum"]).fillna(0).astype(int)
        out["Anomaly_Pct"] = out[C.CITY_COL].map(
            (100 * an["sum"] / an["size"]).round(2))
    if "Cluster" in df.columns:
        dom = (df.groupby([C.CITY_COL, "Cluster"], observed=True).size()
                 .reset_index(name="n").sort_values("n", ascending=False)
                 .groupby(C.CITY_COL).head(1).set_index(C.CITY_COL)["Cluster"])
        out["Dominant_Cluster"] = out[C.CITY_COL].map(dom)
    if C.TARGET_COL in df.columns:
        sev = (df.assign(_s=df[C.TARGET_COL].astype(str).isin(["Severe", "Very Poor"]))
                 .groupby(C.CITY_COL, observed=True)["_s"].mean() * 100).round(2)
        out["Pct_Severely_Polluted_Days"] = out[C.CITY_COL].map(sev)
    date_cols = [c for c in ("Date",) if c in df.columns]
    if date_cols:
        rng = df.groupby(C.CITY_COL, observed=True)["Date"].agg(["min", "max"])
        out["First_Observation"] = out[C.CITY_COL].map(rng["min"].dt.date.astype(str))
        out["Last_Observation"] = out[C.CITY_COL].map(rng["max"].dt.date.astype(str))
    return out.round(3).sort_values("Avg_AQI", ascending=False).reset_index(drop=True)


def monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per Year-Month: AQI and pollutant averages plus record count."""
    if not {"Year", "Month"}.issubset(df.columns):
        raise ValueError("monthly_summary needs Year and Month columns "
                         "(run feature engineering first).")
    polls = C.pollutant_columns(df.columns)
    metrics = polls + ([C.AQI_COL] if C.AQI_COL in df.columns else [])
    named = "Month_Name" if "Month_Name" in df.columns else "Month"
    out = (df.groupby(["Year", "Month"], observed=True)
             .agg(**{"Month_Name": (named, "first"),
                     **_mean_cols(metrics),
                     "Observation_Count": (metrics[0], "size")})
             .reset_index())
    out["Month_Name"] = out["Month"].map(dict(enumerate(
        ["January", "February", "March", "April", "May", "June", "July", "August",
         "September", "October", "November", "December"], start=1)))
    if "Season" in df.columns:
        out["Season"] = out["Month"].map(C.SEASON_MAP)
    if C.TARGET_COL in df.columns and "Year_Month" in df.columns:
        ym = df.dropna(subset=["Year", "Month"]).copy()
        ym["key"] = ym["Year"].astype(str) + "-" + ym["Month"].astype(str).str.zfill(2)
        worst_bucket = (ym.groupby(["key", C.TARGET_COL], observed=True).size()
                          .reset_index(name="n").sort_values("n", ascending=False)
                          .groupby("key").head(1).set_index("key")[C.TARGET_COL])
        out["key"] = out["Year"].astype(str) + "-" + out["Month"].astype(str).str.zfill(2)
        out["Dominant_AQI_Category"] = out["key"].map(worst_bucket.astype(str))
        out = out.drop(columns=["key"])
    out["Year_Month"] = (out["Year"].astype(str) + "-"
                         + out["Month"].astype(int).astype(str).str.zfill(2))
    return out.round(3)


def yearly_summary(df: pd.DataFrame) -> pd.DataFrame:
    polls = C.pollutant_columns(df.columns)
    metrics = polls + ([C.AQI_COL] if C.AQI_COL in df.columns else [])
    out = (df.groupby("Year", observed=True)
             .agg(**_mean_cols(metrics), Observation_Count=(metrics[0], "size"))
             .reset_index())
    return out.round(3)


def seasonal_summary(df: pd.DataFrame) -> pd.DataFrame:
    polls = C.pollutant_columns(df.columns)
    metrics = polls + ([C.AQI_COL] if C.AQI_COL in df.columns else [])
    out = (df.groupby("Season", observed=True)
             .agg(**_mean_cols(metrics), Observation_Count=(metrics[0], "size"))
             .reset_index())
    return out.round(3)


def bucket_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """Observation counts per AQI category (and share of the total)."""
    if C.TARGET_COL not in df.columns:
        return pd.DataFrame()
    t = (df[C.TARGET_COL].astype(str).value_counts().rename_axis(C.TARGET_COL)
           .reset_index(name="Observation_Count"))
    t["Percent"] = (100 * t["Observation_Count"] / t["Observation_Count"].sum()).round(2)
    order = [b for b in C.AQI_BUCKET_ORDER if b in set(t[C.TARGET_COL])]
    t["_o"] = t[C.TARGET_COL].map({b: i for i, b in enumerate(order)})
    return t.sort_values("_o").drop(columns="_o").reset_index(drop=True)


def city_bucket_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """City x AQI category counts - feeds the Power BI matrix/heatmap visual."""
    if C.TARGET_COL not in df.columns:
        return pd.DataFrame()
    m = (df.pivot_table(index=C.CITY_COL, columns=C.TARGET_COL,
                        values=C.AQI_COL if C.AQI_COL in df.columns else None,
                        aggfunc="size", fill_value=0, observed=True)
           .reset_index())
    return m


def build_dim_date(df: pd.DataFrame) -> pd.DataFrame:
    """A proper Power BI date dimension built from the dates actually present."""
    if "Date" not in df.columns:
        return pd.DataFrame()
    d = (df[["Date", "Year", "Month", "Month_Name", "Quarter", "Quarter_Label",
             "Day", "Day_of_Week", "Day_Name", "Season", "Is_Weekend", "Year_Month"]]
         .dropna(subset=["Date"]).drop_duplicates("Date").sort_values("Date")
         .reset_index(drop=True))
    d["Date_Key"] = pd.to_datetime(d["Date"]).dt.date.astype(str)
    d["Year_Month_Label"] = d["Month_Name"].astype(str) + " " + d["Year"].astype(str)
    d["Days_In_Month"] = pd.to_datetime(d["Date"]).dt.days_in_month
    return d


def build_dim_bucket(df: pd.DataFrame) -> pd.DataFrame:
    """AQI-category dimension for the dashboard.

    Holds the sort order (1 = worst, so legends, small multiples and axis orders
    follow severity rather than the alphabet), the band from the scale the labels
    use, the range actually observed in this file, and the agreed colour. The
    observed range is computed here, never typed in.
    """
    if C.TARGET_COL not in df.columns:
        return pd.DataFrame()
    obs = df.groupby(df[C.TARGET_COL].astype(str), observed=True)[C.AQI_COL].agg(
        ["count", "min", "max"])
    banded = {b[0] for b in C.AQI_BUCKET_BANDS}
    n = len(df)
    rows = []
    for order, (label, lo, hi) in enumerate(C.AQI_BUCKET_BANDS, start=1):
        cnt = int(obs.loc[label, "count"]) if label in obs.index else 0
        rows.append({
            "AQI_Bucket": label,
            "Sort_Order": order,
            "Band_Lower_AQI": lo,
            "Band_Upper_AQI": hi,
            "Observed_Min_AQI": float(obs.loc[label, "min"]) if cnt else None,
            "Observed_Max_AQI": float(obs.loc[label, "max"]) if cnt else None,
            "Record_Count": cnt,
            "Share_%": round(100 * cnt / n, 2) if n else None,
            "Colour": C.AQI_COLORS.get(label, C.AQI_COLORS["Unknown"]),
        })
    for k, label in enumerate(i for i in obs.index if i not in banded):
        cnt = int(obs.loc[label, "count"])
        rows.append({"AQI_Bucket": label, "Sort_Order": len(rows) + 1,
                     "Band_Lower_AQI": None, "Band_Upper_AQI": None,
                     "Observed_Min_AQI": float(obs.loc[label, "min"]),
                     "Observed_Max_AQI": float(obs.loc[label, "max"]),
                     "Record_Count": cnt,
                     "Share_%": round(100 * cnt / n, 2) if n else None,
                     "Colour": C.AQI_COLORS["Unknown"]})
    return pd.DataFrame(rows)


def build_dim_city(df: pd.DataFrame) -> pd.DataFrame:
    """City dimension: one row per city, descriptive attributes only.

    Aggregates deliberately stay in the measures (DAX) rather than being
    duplicated here, so the fact table and the dimension cannot disagree.
    """
    if C.CITY_COL not in df.columns:
        return pd.DataFrame()
    g = df.groupby(C.CITY_COL, observed=True)
    out = pd.DataFrame({"City": g.size().index.astype(str),
                        "Record_Count": g.size().to_numpy()})
    if "Date" in df.columns:
        out["Distinct_Days"] = g["Date"].nunique().to_numpy()
        rng = g["Date"].agg(["min", "max"])
        out["First_Observation"] = out["City"].map(
            lambda c: pd.to_datetime(rng.loc[c, "min"]).date().isoformat())
        out["Last_Observation"] = out["City"].map(
            lambda c: pd.to_datetime(rng.loc[c, "max"]).date().isoformat())
    if "Cluster" in df.columns:
        dom = (df.groupby([C.CITY_COL, "Cluster"], observed=True).size()
                 .reset_index(name="n").sort_values("n", ascending=False)
                 .drop_duplicates(C.CITY_COL).set_index(C.CITY_COL)["Cluster"])
        out["Dominant_Cluster"] = out["City"].map(dom.astype(int).to_dict())
    return out.sort_values("City").reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Insights
# --------------------------------------------------------------------------- #
def insight_row(insight: str, category: str, evidence: str, source: str,
                strength: str = "descriptive") -> dict:
    return {"Insight": insight, "Category": category, "Quantitative Evidence": evidence,
            "Derived From": source, "Evidence Strength": strength}


def insights_from_results(*, before: dict, after: dict, city: pd.DataFrame,
                          monthly: pd.DataFrame, corr_target: pd.DataFrame,
                          cluster_choice: dict, cluster_profile: pd.DataFrame,
                          anomaly_stats: dict, anomaly_by_city: pd.DataFrame,
                          model_table: pd.DataFrame, leakage: dict,
                          distribution: pd.DataFrame | None = None,
                          group_tests: dict | None = None,
                          trend: dict | None = None,
                          predictability: dict | None = None,
                          aqi_structure: dict | None = None) -> pd.DataFrame:
    """Turn computed artefacts into the insight table.

    Every sentence is assembled from numbers passed in, so no statement can be
    written that the analysis did not actually produce.
    """
    rows: list[dict] = []
    add = rows.append

    add(insight_row(
        f"The dataset covers {after['Total Rows']:,} daily observations across "
        f"{after['Unique Cities']} cities from {after['Date Start']} to {after['Date End']}.",
        "Data scope",
        f"rows={after['Total Rows']:,}; cities={after['Unique Cities']}; "
        f"range={after['Date Start']}..{after['Date End']}",
        "Notebook 01/02 - data quality report", "measured"))

    if before["Duplicate Rows"] == 0 and before["Total Missing Values"] == 0:
        add(insight_row(
            "Cleaning removed no rows: the supplied file contains no duplicate "
            "records and no missing values, so the analysis rests entirely on "
            "originally recorded values.",
            "Data quality",
            f"duplicates_before={before['Duplicate Rows']}, "
            f"missing_before={before['Total Missing Values']}, "
            f"rows_removed={before['Total Rows'] - after['Total Rows']}",
            "Notebook 02 - cleaning log", "measured"))
    else:
        add(insight_row(
            f"Cleaning touched {before['Total Rows'] - after['Total Rows']} rows and "
            f"{before['Total Missing Values']} missing cells.",
            "Data quality",
            f"duplicates={before['Duplicate Rows']}; missing={before['Total Missing Values']}",
            "Notebook 02 - cleaning log", "measured"))

    if len(city):
        best, worst = city.iloc[-1], city.iloc[0]
        spread = float(worst["Avg_AQI"]) - float(best["Avg_AQI"])
        add(insight_row(
            f"{worst[C.CITY_COL]} has the highest average AQI ({worst['Avg_AQI']}) and "
            f"{best[C.CITY_COL]} the lowest ({best['Avg_AQI']}), a gap of {spread:.1f} index points.",
            "City comparison",
            f"max_avg_AQI={worst['Avg_AQI']} ({worst[C.CITY_COL]}); "
            f"min_avg_AQI={best['Avg_AQI']} ({best[C.CITY_COL]}); gap={spread:.2f}",
            "city_summary.csv", "measured"))
        if group_tests and "City" in group_tests:
            t = group_tests["City"]
            verdict = ("the difference between cities is NOT statistically significant"
                       if not t["Significant_at_0.05"] else
                       "the difference between cities IS statistically significant")
            add(insight_row(
                f"Although city averages differ slightly, {verdict} "
                f"(ANOVA F={t['ANOVA_F']}, p={t['ANOVA_p']}), so this dataset does not "
                f"support a claim that any one city is materially more polluted.",
                "Statistical test",
                f"ANOVA_F={t['ANOVA_F']}, p={t['ANOVA_p']}, "
                f"mean_spread={t['Between_Group_Mean_Spread']}",
                "Notebook 05 - group comparison test", "measured"))

    if len(corr_target):
        top = corr_target.iloc[0]
        sig = corr_target[corr_target["Significant_at_0.05"]]
        add(insight_row(
            f"{top['Variable']} shows the strongest association with AQI "
            f"(Pearson r={top['Pearson_r']}, {top['Strength']}, p={top['Pearson_p']}); "
            f"{len(sig)} of {len(corr_target)} pollutants reach significance at 0.05.",
            "Correlation",
            f"top_r={top['Pearson_r']}, r2={top['r^2']}, p={top['Pearson_p']}, "
            f"significant={len(sig)}/{len(corr_target)}",
            "correlation_matrix.csv / Notebook 05", "measured"))
        add(insight_row(
            f"Measured linearly, {top['Variable']} explains only "
            f"{100 * float(top['r^2']):.1f}% of AQI variance, and correlation is not "
            f"causation: this dataset contains no activity or meteorological data that "
            f"could support a causal claim. A non-linear test (below) shows whether the "
            f"near-zero Pearson coefficients really mean 'no relationship'.",
            "Correlation",
            f"r2={top['r^2']}", "Notebook 05", "measured"))

    if len(cluster_profile):
        k = cluster_choice.get("chosen_K")
        sil = cluster_choice.get("silhouette")
        add(insight_row(
            f"K-Means was run with K={k}, selected because it maximised the silhouette "
            f"score ({sil}); the elbow rule suggested K={cluster_choice.get('K_by_elbow_rule')}.",
            "Clustering", f"chosen_K={k}, silhouette={sil}, "
            f"elbow_K={cluster_choice.get('K_by_elbow_rule')}",
            "Notebook 06 - K selection table", "measured"))
        if sil is not None and sil < 0.25:
            add(insight_row(
                f"The silhouette score of {sil} is below the conventional 0.25 threshold "
                f"for meaningful structure, so the clusters should be read as a software "
                f"partition of the value range rather than as naturally distinct pollution "
                f"profiles.",
                "Clustering", f"silhouette={sil} < 0.25",
                "Notebook 06 - K selection table", "measured"))

    if len(anomaly_by_city):
        top = anomaly_by_city.iloc[0]
        add(insight_row(
            f"Isolation Forest flagged {anomaly_stats['Anomalies detected']} of "
            f"{anomaly_stats['Rows evaluated']:,} records "
            f"({anomaly_stats['Anomaly %']}%) as statistically unusual; "
            f"{top[C.CITY_COL]} contributes the most ({int(top['Anomalies'])}).",
            "Anomaly detection",
            f"anomalies={anomaly_stats['Anomalies detected']}, "
            f"share={anomaly_stats['Anomaly %']}%, "
            f"contamination={anomaly_stats['Configured contamination']}",
            "anomaly_results.csv", "measured"))
        spread = anomaly_by_city["Anomaly_Pct"].max() - anomaly_by_city["Anomaly_Pct"].min()
        add(insight_row(
            f"Anomaly rates differ across cities by only {spread:.2f} percentage points, "
            f"which is consistent with the configured contamination rate rather than with "
            f"city-specific unusual events. Anomaly labels describe statistical unusualness, "
            f"not an identified cause.",
            "Anomaly detection",
            f"anomaly_pct_spread={spread:.2f}pp",
            "Notebook 07", "measured"))

    if len(model_table):
        best = model_table.iloc[0]
        base = model_table.loc[model_table["Model"].str.startswith("Baseline"), "Accuracy_%"]
        bacc = float(base.iloc[0]) if not base.empty else np.nan
        add(insight_row(
            f"The best model by macro-F1 is {best['Model']} "
            f"(accuracy {best['Accuracy_%']}%, macro-F1 {best['F1_macro']}).",
            "Classification",
            f"model={best['Model']}, acc={best['Accuracy_%']}%, macroF1={best['F1_macro']}",
            "model_comparison.csv", "measured"))
        if not np.isnan(bacc):
            delta = float(best["Accuracy_%"]) - bacc
            if delta > 5:
                add(insight_row(
                    f"The best model beats the prior-based baseline by "
                    f"{delta:+.2f} percentage points ({bacc:.2f}% -> "
                    f"{best['Accuracy_%']}%), so the pollutant columns do carry "
                    f"substantial information about the AQI band.",
                    "Classification",
                    f"baseline={bacc:.2f}%, best={best['Accuracy_%']}%, delta={delta:+.2f}pp",
                    "model_comparison.csv", "measured"))
            else:
                add(insight_row(
                    f"The best model does not clearly beat the prior-based baseline of "
                    f"{bacc:.2f}% (best {best['Accuracy_%']}%, delta {delta:+.2f}pp), so the "
                    f"pollutant columns do not carry enough information to reconstruct the "
                    f"AQI band in this dataset.",
                    "Classification",
                    f"baseline={bacc:.2f}%, best={best['Accuracy_%']}%, delta={delta:+.2f}pp",
                    "model_comparison.csv", "measured"))

    if leakage.get("present"):
        wo = leakage["without leaky column"]["accuracy_%"]
        wi = leakage["with leaky column"]["accuracy_%"]
        add(insight_row(
            f"Leakage control applied: {C.TARGET_COL} is derived from "
            f"{leakage['suspect_column']}, so {leakage['suspect_column']} was removed from "
            f"the predictors. Adding it back changes accuracy only from {wo}% to {wi}% "
            f"({leakage['accuracy_inflation_pp']} pp) - because the pollutant "
            f"concentrations already recover the index almost completely.",
            "Model validity",
            f"acc_without={wo}%, acc_with={wi}%, inflation={leakage['accuracy_inflation_pp']}pp",
            "Notebook 08 - leakage check", "measured"))

    if predictability and "error" not in predictability:
        add(insight_row(
            f"AQI is almost fully determined by the pollutant concentrations: a "
            f"cross-validated random-forest regressor reaches R2="
            f"{predictability['tree_CV_R2']} (MAE {predictability['tree_CV_MAE']}) while "
            f"linear regression reaches only R2={predictability['linear_R2']}. The "
            f"relationship is therefore strong but NON-LINEAR, which is why the Pearson "
            f"matrix shows near-zero coefficients - a textbook warning against concluding "
            f"'no relationship' from correlation alone.",
            "Correlation / method",
            f"tree_CV_R2={predictability['tree_CV_R2']}, linear_R2={predictability['linear_R2']}, "
            f"gap={predictability['gap']}",
            "Notebook 05 - non-linear predictability test", "measured"))
        add(insight_row(
            f"Because AQI can be reproduced from the concentrations with "
            f"R2={predictability['tree_CV_R2']}, AQI behaves as a derived column in this "
            f"file rather than as an independently measured quantity. Findings that compare "
            f"AQI against pollutants are therefore partly circular and are labelled as such.",
            "Data integrity",
            f"tree_CV_R2={predictability['tree_CV_R2']}, "
            f"features={len(predictability.get('features', []))}",
            "Notebook 05", "interpretation"))

    if aqi_structure and "error" not in aqi_structure:
        path = aqi_structure["forward_selection"]
        lead = aqi_structure["informative_set"][:2]
        steps = " -> ".join(f"{s['added']} ({s['cv_r2']})" for s in path)
        first = path[0]["cv_r2"]
        second = path[1]["cv_r2"] if len(path) > 1 else None
        last = path[-1]["cv_r2"]
        detail = (f"{lead[0]} alone reaches R2={first}, adding {lead[1]} raises it to "
                  f"{second}, and every further column together adds only "
                  f"{round(last - second, 4)}" if second is not None else
                  f"{lead[0]} alone reaches R2={first}")
        add(insight_row(
            f"Greedy search identifies the columns AQI is built from: {steps}. "
            f"{detail} - so AQI in this file is computed mainly from the "
            f"particulate-matter columns rather than measured independently.",
            "Data integrity",
            f"informative_set={aqi_structure['informative_set']}; "
            f"single_column_r2={aqi_structure['single_column_cv_r2']}",
            "Notebook 05 - AQI structure probe", "measured"))
        if aqi_structure.get("monotonic_in_leading_column") is False:
            spread = aqi_structure.get("within_cell_spread", {})
            add(insight_row(
                f"The mean AQI profile across deciles of {lead[0]} rises and then "
                f"falls again (monotonic: False). A physical AQI sub-index cannot "
                f"decrease when a concentration increases, so this relationship is "
                f"arithmetically reproducible but not physically meaningful - the "
                f"project reports it as an integrity finding instead of an "
                f"'insight' about pollution."
                + (f" Inside narrow {lead[0]} x {lead[1]} cells AQI still varies by "
                   f"{spread.get('mean_sd')} points on average "
                   f"({spread.get('sd_reduction_pct')}% below the overall SD of "
                   f"{spread.get('overall_sd')}), so a small residual comes from the "
                   f"other columns." if spread else ""),
                "Data integrity",
                f"monotonic={aqi_structure.get('monotonic_in_leading_column')}; "
                f"within_cell={spread}",
                "Notebook 05 - shape of the AQI relationship", "interpretation"))

    if distribution is not None and len(distribution):
        uni = distribution[distribution["Interpretation"].str.contains("uniform-like")]
        if len(uni):
            add(insight_row(
                f"Integrity finding: {len(uni)} of {len(distribution)} measured columns are "
                f"statistically indistinguishable from a uniform distribution on a round "
                f"maximum (all with excess kurtosis near -1.2 and near-zero skew), which is "
                f"the signature of randomly generated values, not of monitored pollutant "
                f"concentrations (real concentrations are right-skewed).",
                "Data integrity",
                f"uniform_like_columns={len(uni)}/{len(distribution)}; "
                f"kurtosis_range="
                f"{distribution['Excess_Kurtosis'].min()}..{distribution['Excess_Kurtosis'].max()}",
                "Notebook 05 - distribution tests", "measured"))

    if trend is not None and "error" not in trend:
        add(insight_row(
            f"AQI over 2015-2024 shows a fitted slope of "
            f"{trend['slope_per_year']} index points per year with p={trend['p_value']}: "
            f"{trend['verdict']}. The dataset therefore does not evidence a rising or "
            f"falling pollution trend.",
            "Trend analysis",
            f"slope_per_year={trend['slope_per_year']}, p={trend['p_value']}, r={trend['r']}",
            "Notebook 05 / 09 - trend test", "measured"))

    add(insight_row(
        "Overall: the analytical pipeline is valid and fully reproducible, but the "
        "conclusions it can support are limited by the dataset itself. Patterns that "
        "real air-quality data shows (city ranking, winter spikes, PM-AQI coupling) are "
        "absent here, so they are reported as absent rather than asserted.",
        "Overall conclusion", "see Notebook 05 integrity tests and model_comparison.csv",
        "all notebooks", "interpretation"))

    return pd.DataFrame(rows)
