"""
Statistical analysis: descriptive statistics, distribution-shape tests,
group comparisons and correlation significance.

This module is what keeps the project honest: it reports whether an apparent
pattern is actually supported by the data, and it is used to test whether the
supplied values behave like real monitored measurements.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


# --------------------------------------------------------------------------- #
# Descriptive statistics
# --------------------------------------------------------------------------- #
def descriptive_stats(df: pd.DataFrame, cols: list[str] | None = None) -> pd.DataFrame:
    """Count, central tendency, spread, shape and coefficient of variation."""
    cols = cols or list(df.select_dtypes("number").columns)
    rows = []
    for col in cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.empty:
            continue
        q1, q3 = s.quantile(0.25), s.quantile(0.75)
        rows.append({
            "Variable": col,
            "Count": int(s.size),
            "Mean": round(float(s.mean()), 3),
            "Std": round(float(s.std()), 3),
            "Min": round(float(s.min()), 3),
            "Q1": round(float(q1), 3),
            "Median": round(float(s.median()), 3),
            "Q3": round(float(q3), 3),
            "Max": round(float(s.max()), 3),
            "IQR": round(float(q3 - q1), 3),
            "Skewness": round(float(stats.skew(s)), 3),
            "Kurtosis(excess)": round(float(stats.kurtosis(s)), 3),
            "CV_%": round(100 * float(s.std() / s.mean()), 2) if s.mean() else None,
        })
    return pd.DataFrame(rows)


def distribution_tests(df: pd.DataFrame, cols: list[str] | None = None,
                       sample: int = 5000, seed: int = C.RANDOM_STATE) -> pd.DataFrame:
    """Test each numeric column against (a) normal and (b) uniform shapes.

    Real pollutant concentrations are typically right-skewed (roughly
    log-normal). A column that is statistically indistinguishable from a
    uniform distribution on a round maximum is a strong indicator of
    simulated or randomly generated values, and that has to be stated.
    """
    cols = cols or list(df.select_dtypes("number").columns)
    rng = np.random.default_rng(seed)
    rows = []
    for col in cols:
        s = pd.to_numeric(df[col], errors="coerce").dropna()
        if s.nunique() < 3 or s.size < 10:
            continue
        sub = s.sample(min(int(s.size), sample), random_state=seed) if s.size > sample else s
        sw_stat, sw_p = stats.shapiro(sub)
        lo, hi = float(s.min()), float(s.max())
        span = (hi - lo) or 1.0
        ks_stat, ks_p = stats.kstest((s - lo) / span, "uniform")
        skew, kurt = float(stats.skew(s)), float(stats.kurtosis(s))
        verdict = []
        verdict.append("not normal" if sw_p < 0.05 else "normal-like")
        verdict.append("uniform-like" if ks_p >= 0.05 else "not uniform")
        verdict.append("right-skewed" if skew > 0.5 else
                       ("flat/uniform shape (kurtosis ~ -1.2)" if abs(kurt + 1.2) < 0.15
                        else "symmetric"))
        rows.append({
            "Variable": col, "Shapiro_W": round(float(sw_stat), 4),
            "Shapiro_p": float(f"{sw_p:.3g}"),
            "KS_vs_uniform_D": round(float(ks_stat), 4),
            "KS_vs_uniform_p": float(f"{ks_p:.3g}"),
            "Skewness": round(skew, 3), "Excess_Kurtosis": round(kurt, 3),
            "Observed_Range": f"{lo:g} to {hi:g}",
            "Interpretation": "; ".join(verdict),
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Group comparisons
# --------------------------------------------------------------------------- #
def group_comparison(df: pd.DataFrame, value: str, by: str) -> dict:
    """One-way ANOVA + Kruskal-Wallis for a numeric value across a grouping."""
    groups = [g[value].dropna().values for _, g in df.groupby(by, observed=True)
              if g[value].notna().sum() > 1]
    if len(groups) < 2:
        return {"grouping": by, "error": "fewer than two usable groups"}
    f_stat, f_p = stats.f_oneway(*groups)
    h_stat, h_p = stats.kruskal(*groups)
    means = df.groupby(by, observed=True)[value].agg(["count", "mean", "std"]).round(3)
    spread = float(means["mean"].max() - means["mean"].min())
    return {
        "grouping": by, "value": value,
        "ANOVA_F": round(float(f_stat), 4), "ANOVA_p": float(f"{f_p:.4g}"),
        "Kruskal_H": round(float(h_stat), 4), "Kruskal_p": float(f"{h_p:.4g}"),
        "Between_Group_Mean_Spread": round(spread, 3),
        "Significant_at_0.05": bool(min(f_p, h_p) < 0.05),
        "group_means": means,
    }


def autocorrelation(df: pd.DataFrame, col: str, lags: tuple[int, ...] = (1, 2, 3, 7, 30),
                    group: str = C.CITY_COL) -> pd.DataFrame:
    """Lagged self-correlation of a series.

    Genuine daily air-quality series are strongly autocorrelated (yesterday's
    pollution predicts today's). Values near zero indicate the ordering of
    rows carries no information, i.e. the series behaves like random draws.
    """
    out = []
    groups = (df.groupby(group, observed=True) if group in df.columns
              else [("all", df)])
    for lag in lags:
        vals = []
        for _, g in groups:
            s = g.sort_values("Date")[col].dropna() if "Date" in g.columns else g[col].dropna()
            if s.size > lag + 10:
                vals.append(np.corrcoef(s.values[:-lag], s.values[lag:])[0, 1])
        out.append({"Lag": lag, "Mean_Autocorrelation": round(float(np.mean(vals)), 4),
                    "n_series": len(vals)})
    return pd.DataFrame(out)


# --------------------------------------------------------------------------- #
# Correlation
# --------------------------------------------------------------------------- #
def correlation_matrix(df: pd.DataFrame, cols: list[str],
                       method: str = "pearson") -> pd.DataFrame:
    return df[cols].corr(method=method).round(4)


def correlation_with_target(df: pd.DataFrame, cols: list[str], target: str) -> pd.DataFrame:
    """Pearson + Spearman + p-value + n for every variable against the target."""
    rows = []
    for col in cols:
        if col == target or col not in df.columns:
            continue
        pair = df[[col, target]].apply(pd.to_numeric, errors="coerce").dropna()
        if pair.shape[0] < 5:
            continue
        pr, pp = stats.pearsonr(pair[col], pair[target])
        sr, sp = stats.spearmanr(pair[col], pair[target])

        def strength(r):
            a = abs(r)
            return ("negligible" if a < 0.1 else "weak" if a < 0.3 else
                    "moderate" if a < 0.5 else "strong" if a < 0.7 else "very strong")
        rows.append({
            "Variable": col, "n": int(pair.shape[0]),
            "Pearson_r": round(float(pr), 4), "Pearson_p": float(f"{pp:.3g}"),
            "Spearman_rho": round(float(sr), 4), "Spearman_p": float(f"{sp:.3g}"),
            "r^2": round(float(pr) ** 2, 4),
            "Strength": strength(pr), "Direction": "positive" if pr > 0 else "negative",
            "Significant_at_0.05": bool(pp < 0.05),
        })
    return (pd.DataFrame(rows)
            .sort_values("Pearson_r", key=lambda s: s.abs(), ascending=False)
            .reset_index(drop=True))


def linear_fit(df: pd.DataFrame, y: str, x_cols: list[str]) -> dict:
    """Multiple linear regression via numpy least squares (no extra dependency)."""
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    data = df[[y] + x_cols].apply(pd.to_numeric, errors="coerce").dropna()
    if data.empty:
        return {"error": "no usable rows"}
    model = LinearRegression().fit(data[x_cols], data[y])
    pred = model.predict(data[x_cols])
    resid = data[y].values - pred
    n, k = data.shape[0], len(x_cols)
    r2 = r2_score(data[y], pred)
    adj = 1 - (1 - r2) * (n - 1) / (n - k - 1)
    return {
        "n": int(n), "predictors": x_cols, "target": y,
        "R2": round(float(r2), 4), "Adj_R2": round(float(adj), 4),
        "RMSE": round(float(np.sqrt(np.mean(resid ** 2))), 4),
        "coefficients": {c: round(float(v), 4) for c, v in zip(x_cols, model.coef_)},
        "intercept": round(float(model.intercept_), 4),
    }


def tree_predictability(df: pd.DataFrame, target: str, features: list[str],
                        folds: int = 3,
                        random_state: int = C.RANDOM_STATE) -> dict:
    """Cross-validated predictability of a target under a non-linear learner.

    Compared against the linear R^2 this answers an important methodological
    question: if a tree ensemble predicts far better than linear regression,
    the relationship exists but is non-linear, so a Pearson correlation matrix
    alone would have missed it.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.metrics import mean_absolute_error, r2_score
    from sklearn.model_selection import KFold

    cols = [c for c in features + [target] if c in df.columns]
    data = df[cols].apply(pd.to_numeric, errors="coerce").dropna()
    if data.shape[0] < 50:
        return {"error": "not enough complete rows"}
    X, y = data[[c for c in cols if c != target]], data[target]
    kf = KFold(n_splits=folds, shuffle=True, random_state=random_state)
    pred = np.zeros(len(y))
    for tr, te in kf.split(X):
        m = RandomForestRegressor(n_estimators=150, min_samples_leaf=2,
                                  n_jobs=2, random_state=random_state).fit(
            X.iloc[tr], y.iloc[tr])
        pred[te] = m.predict(X.iloc[te])
    lin = linear_fit(df, target, list(X.columns))
    r2 = float(r2_score(y, pred))
    return {
        "target": target, "n": int(len(y)),
        "features": list(X.columns),
        "tree_CV_R2": round(r2, 4),
        "tree_CV_MAE": round(float(mean_absolute_error(y, pred)), 4),
        "linear_R2": lin.get("R2"),
        "gap": round(r2 - float(lin.get("R2") or 0), 4),
        "verdict": ("the relationship is largely NON-LINEAR: a tree ensemble "
                    "explains far more than linear regression / Pearson r, so a "
                    "correlation matrix alone would understate it"
                    if r2 - float(lin.get("R2") or 0) > 0.2 else
                    "linear and non-linear predictability are comparable"),
    }


def aqi_structure(df: pd.DataFrame, target: str, features: list[str],
                  folds: int = 3, steps: int = 3,
                  n_estimators: int = 60,
                  random_state: int = C.RANDOM_STATE) -> dict:
    """Find which columns determine a derived target and describe the shape.

    If a tree ensemble reproduces the target almost exactly, the target is a
    computed function of some columns rather than an independent measurement.
    This function answers three questions with evidence:

    1. how well each single column predicts the target (cross-validated R^2),
    2. the smallest useful set of columns, by greedy forward selection, and
    3. the *shape* of the relationship - a real AQI sub-index must rise
       monotonically with concentration, and a deterministic rule leaves almost
       no spread of the target inside narrow cells of its drivers.
    """
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import KFold, cross_val_score

    cols = [c for c in features if c in df.columns]
    data = df[cols + [target]].apply(pd.to_numeric, errors="coerce").dropna()
    if data.shape[0] < 200 or not cols:
        return {"error": "not enough complete rows for a structure probe"}

    kf = KFold(n_splits=folds, shuffle=True, random_state=random_state)

    def cv_r2(sub):
        model = RandomForestRegressor(n_estimators=n_estimators,
                                      min_samples_leaf=5,
                                      n_jobs=2, random_state=random_state)
        return float(np.mean(cross_val_score(
            model, data[sub], data[target], scoring="r2", cv=kf, n_jobs=1)))

    single = {p: round(cv_r2([p]), 4) for p in cols}

    chosen, remaining, path = [], list(cols), []
    for _ in range(min(steps, len(cols))):
        score, best = max(((cv_r2(chosen + [p]), p) for p in remaining),
                          key=lambda t: t[0])
        chosen.append(best)
        remaining.remove(best)
        path.append({"added": best, "cv_r2": round(score, 4)})

    out: dict = {"target": target, "n": int(len(data)),
                 "single_column_cv_r2": single,
                 "forward_selection": path, "informative_set": chosen}

    lead = chosen[0]
    deciles = (data.groupby(pd.qcut(data[lead], 10, duplicates="drop"),
                            observed=True)[target]
               .agg(Records="count", Mean="mean", SD="std").round(2))
    out["decile_profile_of_leading_column"] = [
        {"bin": str(i), "records": int(r["Records"]),
         "mean_target": float(r["Mean"]), "sd_target": float(r["SD"])}
        for i, r in deciles.iterrows()]
    out["monotonic_in_leading_column"] = bool(
        deciles["Mean"].is_monotonic_increasing)

    if len(chosen) > 1:
        cells = (data.groupby([pd.qcut(data[chosen[0]], 20, duplicates="drop"),
                               pd.qcut(data[chosen[1]], 20, duplicates="drop")],
                              observed=True)[target]
                 .agg(["count", "std", "min", "max"]))
        cells = cells[cells["count"] >= 8]
        if len(cells):
            overall = float(data[target].std())
            within = float(cells["std"].mean())
            out["within_cell_spread"] = {
                "cells": int(len(cells)),
                "mean_sd": round(within, 2),
                "mean_range": round(float((cells["max"] - cells["min"]).mean()), 2),
                "overall_sd": round(overall, 2),
                "sd_reduction_pct": round(100 * (1 - within / overall), 1),
            }

    last = path[-1]["cv_r2"] if path else None
    monotone = out.get("monotonic_in_leading_column")
    if last is not None and last > 0.9:
        verdict = (f"{target} is reproducible from "
                   f"{'+'.join(chosen)} at CV R^2={last} - it is a derived "
                   f"column, not an independent measurement")
        if monotone is False:
            verdict += (", and its dependence on the leading column is "
                        "non-monotonic, which a physical sub-index cannot be")
    else:
        verdict = (f"{target} is not closely reproduced by the measured "
                   f"columns (best greedy CV R^2={last})")
    out["verdict"] = verdict
    return out


def linear_trend_test(df: pd.DataFrame, col: str, date_col: str = "Date") -> dict:
    """OLS slope of the series against time, with its significance test.

    A rank-based Mann-Kendall test would be the usual non-parametric choice;
    the OLS slope of scipy.linregress is used here because it needs no extra
    dependency and the sample size (thousands of points) makes the slope test
    statistic reliable.
    """
    d = df[[date_col, col]].dropna()
    if d.shape[0] < 30:
        return {"error": "series too short"}
    x = (pd.to_datetime(d[date_col]) - pd.to_datetime(d[date_col]).min()).dt.days.values
    y = pd.to_numeric(d[col], errors="coerce").values
    res = stats.linregress(x, y)
    return {
        "series": col, "n": int(len(d)),
        "slope_per_year": round(float(res.slope * 365.25), 4),
        "p_value": float(f"{res.pvalue:.4g}"),
        "r": round(float(res.rvalue), 4),
        "significant": bool(res.pvalue < 0.05),
        "verdict": ("statistically detectable trend" if res.pvalue < 0.05
                    else "no statistically detectable trend"),
    }
