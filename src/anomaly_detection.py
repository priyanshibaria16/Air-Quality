"""
Anomaly detection with Isolation Forest.

What the result means: an anomaly is a record whose combination of pollutant
values is statistically unusual with respect to the rest of the dataset. It is
NOT a diagnosis of why the air was unusual - attributing a cause would need
activity data (fireworks, stubble burning, traffic, industry) that this dataset
does not contain.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


def detect(df: pd.DataFrame, features: list[str],
           contamination: float = C.CONTAMINATION,
           random_state: int = C.RANDOM_STATE, n_estimators: int = 300):
    """Fit Isolation Forest and add Anomaly / Anomaly_Score / Anomaly_Label.

    Returns (frame, model, used_features, params).
    """
    used = [f for f in features if f in df.columns]
    if not used:
        raise ValueError("No anomaly features available in the dataset.")
    X = df[used].apply(pd.to_numeric, errors="coerce")
    keep = X.notna().all(axis=1)
    X = X[keep]

    model = IsolationForest(n_estimators=n_estimators, contamination=contamination,
                            random_state=random_state, n_jobs=-1)
    pred = model.fit_predict(X)                 # -1 anomaly, 1 normal
    score = model.score_samples(X)              # lower = more anomalous

    out = df.copy()
    out["Anomaly"] = np.nan
    out["Anomaly_Score"] = np.nan
    out.loc[X.index, "Anomaly"] = (pred == -1).astype(int)
    out.loc[X.index, "Anomaly_Score"] = np.round(score, 5)
    out["Anomaly_Label"] = np.where(out["Anomaly"].isna(), "Not evaluated",
                                    np.where(out["Anomaly"] == 1, "Anomaly", "Normal"))
    params = {"n_estimators": n_estimators, "contamination": contamination,
              "random_state": random_state, "features": used,
              "rows_evaluated": int(keep.sum())}
    return out, model, used, params


def summary(df: pd.DataFrame) -> dict:
    evaluated = df[df["Anomaly"].notna()]
    n = int(len(evaluated))
    k = int((evaluated["Anomaly"] == 1).sum())
    return {
        "Rows evaluated": n,
        "Anomalies detected": k,
        "Anomaly %": round(100 * k / n, 2) if n else None,
        "Configured contamination": C.CONTAMINATION,
        "Note": ("the detected share follows the contamination parameter; "
                 "it is an assumed sensitivity, not an independently observed "
                 "anomaly rate"),
    }


def by_city(df: pd.DataFrame, city_col: str = C.CITY_COL) -> pd.DataFrame:
    ev = df[df["Anomaly"].notna()]
    t = (ev.groupby(city_col, observed=True)
           .agg(Observations=("Anomaly", "size"), Anomalies=("Anomaly", "sum"))
           .assign(Anomaly_Pct=lambda x: (100 * x["Anomalies"] / x["Observations"]).round(2))
           .sort_values("Anomalies", ascending=False)
           .reset_index())
    return t


def by_period(df: pd.DataFrame, freq: str = "year") -> pd.DataFrame:
    """Anomaly counts per calendar bucket: 'year', 'month' or 'quarter'."""
    ev = df[df["Anomaly"].notna()].dropna(subset=["Date"]).copy()
    if ev.empty:
        return pd.DataFrame()
    d = pd.to_datetime(ev["Date"])
    if freq == "year":
        key = d.dt.year.astype(str)
    elif freq == "month":
        key = d.dt.strftime("%Y-%m")
    elif freq == "quarter":
        key = d.dt.year.astype(str) + "-Q" + d.dt.quarter.astype(str)
    else:
        raise ValueError("freq must be 'year', 'month' or 'quarter'")
    ev["Period"] = key.values
    t = (ev.groupby("Period", observed=True)
            .agg(Observations=("Anomaly", "size"), Anomalies=("Anomaly", "sum"))
            .assign(Anomaly_Pct=lambda x: (100 * x["Anomalies"] / x["Observations"]).round(2))
            .reset_index().sort_values("Period"))
    return t


def pollutant_comparison(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Mean value of each pollutant for normal vs anomalous records."""
    ev = df[df["Anomaly"].notna()].copy()
    used = [f for f in features if f in ev.columns]
    rows = []
    for f in used:
        normal = ev.loc[ev["Anomaly"] == 0, f]
        anom = ev.loc[ev["Anomaly"] == 1, f]
        diff = float(anom.mean() - normal.mean()) if len(anom) and len(normal) else np.nan
        rows.append({
            "Pollutant": f,
            "Normal_Mean": round(float(normal.mean()), 3) if len(normal) else None,
            "Anomaly_Mean": round(float(anom.mean()), 3) if len(anom) else None,
            "Difference": round(diff, 3),
            "Pct_Change": round(100 * diff / float(normal.mean()), 2)
            if len(normal) and normal.mean() else None,
            "Normal_Max": round(float(normal.max()), 3) if len(normal) else None,
            "Anomaly_Max": round(float(anom.max()), 3) if len(anom) else None,
        })
    return pd.DataFrame(rows)
