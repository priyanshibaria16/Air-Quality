"""
End-to-end analysis pipeline: raw data -> cleaned -> features -> statistics ->
correlation -> clustering -> anomalies -> classification -> BI summaries.

Run it directly to regenerate every artefact and the machine-readable
results.json that the report and slides are generated from:

    python run_pipeline.py

Nothing in this module prints a number that was not computed from the CSV.
"""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import anomaly_detection as AD          # noqa: E402
import classification as CL             # noqa: E402
import clustering as KM                 # noqa: E402
import config as C                      # noqa: E402
import data_utils as U                  # noqa: E402
import feature_engineering as FE        # noqa: E402
import preprocessing as P               # noqa: E402
import reporting as R                   # noqa: E402
import statistics_analysis as S         # noqa: E402

RESULTS_JSON = C.PROCESSED_DIR / "results.json"


def _jsonable(o):
    if isinstance(o, (dict,)):
        return {k: _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (pd.DataFrame,)):
        return json.loads(o.to_json(orient="records", date_format="iso"))
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o) if np.isfinite(o) else None
    if isinstance(o, float) and not np.isfinite(o):
        return None
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return o.isoformat()
    if isinstance(o, Path):
        return str(o)
    return o


def run(verbose: bool = True) -> dict:
    t0 = datetime.now()
    log = (lambda *a: print(*a)) if verbose else (lambda *a: None)

    # -------------------------------------------------------------- 1. load #
    raw = U.load_raw()
    profile_raw = U.profile(raw)
    dictionary = U.data_dictionary(raw)
    before = U.summary(raw)
    pollutants = C.pollutant_columns(raw.columns)
    date_col = C.date_column(raw.columns)
    log(f"[1/9] loaded {raw.shape[0]:,} rows x {raw.shape[1]} cols from {C.RAW_FILE.name}")

    # ------------------------------------------------------------ 2. clean #
    df, clean_log, before, after = P.clean(raw)
    missing_before = U.missing_table(raw)
    comparison = U.quality_comparison(before, after)
    comparison.to_csv(C.DATA_QUALITY_CSV, index=False)
    clean_log.to_csv(C.PROCESSED_DIR / "cleaning_log.csv", index=False)
    dictionary.to_csv(C.PROCESSED_DIR / "data_dictionary.csv", index=False)
    profile_raw.to_csv(C.PROCESSED_DIR / "raw_column_profile.csv", index=False)
    log(f"[2/9] cleaning: {int(before['Total Rows']) - int(after['Total Rows'])} rows removed, "
        f"{after['Total Missing Values']} missing values remain")

    # --------------------------------------------------- 3. feature engineering #
    feat, fe_notes = FE.build_features(df)
    fe_inventory = FE.feature_inventory(feat)
    log(f"[3/9] feature engineering: {feat.shape[1]} columns")

    # ------------------------------------------------------- 4. statistics #
    measures = pollutants + ([C.AQI_COL] if C.AQI_COL in feat.columns else [])
    desc = S.descriptive_stats(feat, measures)
    dist = S.distribution_tests(feat, measures)
    groups = {g: S.group_comparison(feat, C.AQI_COL, g) for g in
              ("City", "Season", "Month", "Is_Weekend") if g in feat.columns}
    group_table = pd.DataFrame([{k: v for k, v in g.items() if k != "group_means"}
                                for g in groups.values()])
    autocorr = S.autocorrelation(feat, C.AQI_COL)
    trend = S.linear_trend_test(feat, C.AQI_COL)
    fit = S.linear_fit(feat, C.AQI_COL, pollutants)
    predictability = S.tree_predictability(feat, C.AQI_COL, pollutants)
    desc.to_csv(C.PROCESSED_DIR / "descriptive_statistics.csv", index=False)
    dist.to_csv(C.PROCESSED_DIR / "distribution_tests.csv", index=False)
    group_table.to_csv(C.PROCESSED_DIR / "group_comparison_tests.csv", index=False)
    log("[4/9] statistical + integrity tests done")

    # ------------------------------------------------------- 5. correlation #
    corr = S.correlation_matrix(feat, measures)
    corr_spearman = S.correlation_matrix(feat, measures, method="spearman")
    corr_target = S.correlation_with_target(feat, measures, C.AQI_COL)
    corr.to_csv(C.CORRELATION_CSV)
    corr_target.to_csv(C.PROCESSED_DIR / "correlation_with_aqi.csv", index=False)
    log(f"[5/9] correlation: strongest partner of AQI is "
        f"{corr_target.iloc[0]['Variable']} (r={corr_target.iloc[0]['Pearson_r']})")

    # Which columns actually determine AQI, and is that dependence monotone?
    structure = S.aqi_structure(feat, C.AQI_COL, pollutants)
    if "error" not in structure:
        rows = [{"stage": "single column", "pollutant": k, "cv_r2_for_AQI": v}
                for k, v in structure["single_column_cv_r2"].items()]
        rows += [{"stage": f"forward selection step {i + 1}",
                  "pollutant": s["added"], "cv_r2_for_AQI": s["cv_r2"]}
                 for i, s in enumerate(structure["forward_selection"])]
        (pd.DataFrame(rows)
         .sort_values(["stage", "cv_r2_for_AQI"], ascending=[True, False])
         .to_csv(C.PROCESSED_DIR / "aqi_structure_probe.csv", index=False))
        log(f"          AQI structure: {structure['verdict']}")

    # --------------------------------------------------------- 6. clustering #
    k_table = KM.choose_k(KM.build_matrix(feat, pollutants)[0], C.K_RANGE)
    k_choice = KM.recommend_k(k_table)
    feat, kmodel, kscaler, kused, centroids_z, centroids_raw = KM.fit(
        feat, pollutants, k_choice["chosen_K"])
    metrics = pollutants + ([C.AQI_COL] if C.AQI_COL in feat.columns else [])
    cprofile = KM.cluster_profile(feat, metrics)
    cdesc = KM.describe_clusters(cprofile, metrics)
    # Carry the neutral cluster wording onto the profile and onto every record, so
    # the dashboard can label a cluster point without a second lookup table.
    label_map = dict(zip(cdesc["Cluster"], cdesc["Neutral_Description"]))
    cprofile["Cluster_Description"] = cprofile["Cluster"].map(label_map)
    feat["Cluster_Description"] = feat["Cluster"].map(label_map)
    Xc = KM.build_matrix(feat, pollutants)[0]
    pcs = KM.pca_projection(Xc)
    feat = feat.merge(pcs, left_index=True, right_index=True)
    k_table.to_csv(C.PROCESSED_DIR / "k_selection_table.csv", index=False)
    cprofile.to_csv(C.CLUSTER_PROFILE_CSV, index=False)
    centroids_raw.to_csv(C.PROCESSED_DIR / "cluster_centroids_original_units.csv", index=False)
    log(f"[6/9] K-Means: K={k_choice['chosen_K']}, silhouette={k_choice['silhouette']}")

    # ------------------------------------------------------------ 7. anomaly #
    feat, iforest, aused, aparams = AD.detect(feat, pollutants)
    a_stats = AD.summary(feat)
    a_city = AD.by_city(feat)
    a_year = AD.by_period(feat, "year")
    a_poll = AD.pollutant_comparison(feat, pollutants)
    a_city.to_csv(C.PROCESSED_DIR / "anomaly_by_city.csv", index=False)
    a_poll.to_csv(C.PROCESSED_DIR / "anomaly_pollutant_comparison.csv", index=False)
    log(f"[7/9] Isolation Forest: {a_stats['Anomalies detected']} anomalies "
        f"({a_stats['Anomaly %']}%)")

    # ------------------------------------------------------ 8. classification #
    target = C.TARGET_COL
    cls_df = CL.drop_non_informative(feat, target)
    balance = CL.class_balance(cls_df, target)
    leakage = CL.leakage_check(cls_df, pollutants, target)
    comp, reports, matrices, split_info, pred_frame, y_test, X_test = CL.train_and_evaluate(
        cls_df, pollutants, target, cv_folds=3)
    per_class = pd.concat([CL.report_to_frame(n, r) for n, r in reports.items()],
                          ignore_index=True)
    conf = pd.concat([CL.confusion_to_frame(m, sorted(split_info["classes"]), n)
                      for n, m in matrices.items()], ignore_index=True)
    imp_model, imp_features = CL.fit_reference_model(cls_df, pollutants, target)
    imp = CL.feature_importance(imp_model, imp_features)
    comp.to_csv(C.MODEL_COMPARISON_CSV, index=False)
    per_class.to_csv(C.PROCESSED_DIR / "classification_per_class.csv", index=False)
    conf.to_csv(C.PROCESSED_DIR / "confusion_matrices.csv", index=False)
    balance.to_csv(C.PROCESSED_DIR / "class_balance.csv", index=False)
    Path(C.PROCESSED_DIR / "leakage_check.json").write_text(
        json.dumps(_jsonable(leakage), indent=2), encoding="utf-8")
    log(f"[8/9] classification: best macro-F1 "
        f"{comp.iloc[0]['Model']}={comp.iloc[0]['F1_macro']}")

    # ----------------------------------------------- 9. BI exports & insights #
    city_sum = R.city_summary(feat)
    monthly = R.monthly_summary(feat)
    yearly = R.yearly_summary(feat)
    seasonal = R.seasonal_summary(feat)
    buckets = R.bucket_distribution(feat)
    city_bucket = R.city_bucket_matrix(feat)
    dim_date = R.build_dim_date(feat)
    dim_bucket = R.build_dim_bucket(feat)
    dim_city = R.build_dim_city(feat)

    keep = ([C.CITY_COL, "Date", "Year", "Month", "Month_Name", "Quarter_Label", "Day",
             "Day_Name", "Season", "Is_Weekend", "Week_of_Year", "Year_Month"] + pollutants +
            [C.AQI_COL, target, "Pollution_Index", "Pollution_Index_Band",
             "PM25_PM10_Ratio", "NO2_NOx_Ratio", "Pollutants_Above_City_Q3",
             "City_Pollutant_Percentile", "AQI_Rolling_7", "AQI_Rolling_30",
             "AQI_Change_1d", "Cluster", "PC1", "PC2", "Anomaly", "Anomaly_Label",
             "Anomaly_Score", "Cluster_Description"])
    final = feat[[c for c in keep if c in feat.columns]].copy()
    # A record is an extreme episode when any IQR-flagged concentration column is
    # flagged - taken from the flags created in the cleaning stage, never re-derived.
    episode_flags = [c for c in feat.columns if c.endswith("_Outlier")]
    final["Is_Extreme_PM_Episode"] = (
        (feat[episode_flags] > 0).any(axis=1).astype(int)
        if episode_flags else 0)
    log(f"          extreme-episode flag set on "
        f"{int(final['Is_Extreme_PM_Episode'].sum()):,} records "
        f"({100 * final['Is_Extreme_PM_Episode'].mean():.2f}%)")

    final.to_csv(C.CLEANED_CSV, index=False)
    city_sum.to_csv(C.CITY_SUMMARY_CSV, index=False)
    monthly.to_csv(C.MONTHLY_SUMMARY_CSV, index=False)
    yearly.to_csv(C.PROCESSED_DIR / "yearly_summary.csv", index=False)
    seasonal.to_csv(C.PROCESSED_DIR / "seasonal_summary.csv", index=False)
    buckets.to_csv(C.PROCESSED_DIR / "aqi_bucket_distribution.csv", index=False)
    city_bucket.to_csv(C.PROCESSED_DIR / "city_bucket_matrix.csv", index=False)
    dim_date.to_csv(C.PROCESSED_DIR / "dim_date.csv", index=False)
    dim_bucket.to_csv(C.DIM_BUCKET_CSV, index=False)
    dim_city.to_csv(C.DIM_CITY_CSV, index=False)

    cluster_cols = [c for c in [C.CITY_COL, "Date", "Year", "Season"] + pollutants +
                    [C.AQI_COL, target, "Cluster", "Cluster_Description", "PC1", "PC2"]
                    if c in feat.columns]
    feat[cluster_cols].to_csv(C.CLUSTER_RESULTS_CSV, index=False)
    anom_cols = [c for c in [C.CITY_COL, "Date", "Year", "Month", "Season"] + pollutants +
                 [C.AQI_COL, target, "Anomaly", "Anomaly_Label", "Anomaly_Score", "Cluster"]
                 if c in feat.columns]
    feat[anom_cols].to_csv(C.ANOMALY_RESULTS_CSV, index=False)
    pred_frame.to_csv(C.CLASSIFICATION_CSV, index=False)

    insights = R.insights_from_results(
        before=before, after=after, city=city_sum, monthly=monthly,
        corr_target=corr_target, cluster_choice=k_choice, cluster_profile=cprofile,
        anomaly_stats=a_stats, anomaly_by_city=a_city, model_table=comp,
        leakage=leakage, distribution=dist,
        group_tests={k: v for k, v in groups.items()}, trend=trend,
        predictability=predictability, aqi_structure=structure)
    insights.to_csv(C.INSIGHTS_CSV, index=False)

    results = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runtime_seconds": round((datetime.now() - t0).total_seconds(), 1),
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__, "numpy": np.__version__,
            "sklearn": __import__("sklearn").__version__,
            "scipy": __import__("scipy").__version__,
            "matplotlib": __import__("matplotlib").__version__,
            "random_state": C.RANDOM_STATE,
        },
        "dataset": {
            "file": str(C.RAW_FILE), "rows": before["Total Rows"],
            "columns": before["Total Columns"], "cities": before["Unique Cities"],
            "date_start": before["Date Start"], "date_end": before["Date End"],
            "detected_pollutants": pollutants,
            "columns_absent_vs_expected": [p for p in C.POLLUTANT_CANDIDATES
                                           if p not in pollutants],
            "missing_before": before["Total Missing Values"],
            "duplicates_before": before["Duplicate Rows"],
            "rows_after_cleaning": after["Total Rows"],
        },
        "cleaning_log": clean_log,
        "quality_comparison": comparison,
        "data_dictionary": dictionary,
        "raw_column_profile": profile_raw,
        "feature_notes": fe_notes, "feature_inventory": fe_inventory,
        "descriptive_statistics": desc, "distribution_tests": dist,
        "group_tests": {k: {kk: vv for kk, vv in v.items() if kk != "group_means"}
                        for k, v in groups.items()},
        "group_test_table": group_table,
        "group_means": {k: v["group_means"] for k, v in groups.items()},
        "autocorrelation": autocorr, "trend_test": trend, "linear_fit": fit,
        "predictability": predictability,
        "aqi_structure": structure,
        "correlation_matrix": corr, "correlation_spearman": corr_spearman,
        "correlation_with_aqi": corr_target,
        "clustering": {"k_table": k_table, "choice": k_choice, "profile": cprofile,
                       "descriptions": cdesc, "centroids_original_units": centroids_raw,
                       "features_used": kused,
                       "pca_explained_variance": pcs.attrs.get("explained_variance_ratio"),
                       "pca_components": pcs.attrs.get("components")},
        "anomaly": {"stats": a_stats, "by_city": a_city, "by_year": a_year,
                    "pollutant_comparison": a_poll, "params": aparams},
        "classification": {"class_balance": balance, "leakage": leakage,
                           "comparison": comp, "per_class": per_class,
                           "confusion": conf, "split_info": split_info,
                           "feature_importance": imp},
        "summaries": {"city": city_sum, "monthly": monthly, "yearly": yearly,
                      "seasonal": seasonal, "buckets": buckets,
                      "city_bucket": city_bucket},
        "dimensions": {"dim_date": dim_date, "dim_bucket": dim_bucket,
                       "dim_city": dim_city},
        "insights": insights,
        "exports": {"cleaned": str(C.CLEANED_CSV), "city_summary": str(C.CITY_SUMMARY_CSV),
                    "monthly_summary": str(C.MONTHLY_SUMMARY_CSV),
                    "cluster_results": str(C.CLUSTER_RESULTS_CSV),
                    "anomaly_results": str(C.ANOMALY_RESULTS_CSV),
                    "classification_results": str(C.CLASSIFICATION_CSV),
                    "model_comparison": str(C.MODEL_COMPARISON_CSV),
                    "dim_date": str(C.DIM_DATE_CSV),
                    "dim_bucket": str(C.DIM_BUCKET_CSV),
                    "dim_city": str(C.DIM_CITY_CSV),
                    "insights": str(C.INSIGHTS_CSV)},
    }
    RESULTS_JSON.write_text(json.dumps(_jsonable(results), indent=2), encoding="utf-8")
    log(f"[9/9] exported {len(list(C.PROCESSED_DIR.glob('*.csv')))} CSVs "
        f"+ results.json ({results['runtime_seconds']}s)")
    return results


if __name__ == "__main__":
    run()
