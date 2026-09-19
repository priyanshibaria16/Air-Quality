"""Which pollutant columns actually determine AQI in this file?

    python tools/probe_aqi_drivers.py

A random forest reconstructs AQI almost perfectly (CV R^2 ~ 0.997), so AQI must
be a deterministic function of some columns. This script finds the smallest
informative subset and inspects the shape of that function, so the report can
state which relationships are real in the data instead of assuming the usual
textbook ones.
"""
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import KFold, cross_val_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config as C  # noqa: E402
import data_utils as U  # noqa: E402

df = U.load_raw()
polls = C.pollutant_columns(df.columns)
y = df[C.AQI_COL].to_numpy(dtype="float64")
kf = KFold(3, shuffle=True, random_state=42)
report: dict = {"pollutants": polls, "n_rows": int(len(df))}


def cv_r2(cols):
    X = df[cols].to_numpy(dtype="float64")
    m = RandomForestRegressor(n_estimators=120, min_samples_leaf=2, n_jobs=-1,
                              random_state=42)
    return float(np.mean(cross_val_score(m, X, y, scoring="r2", cv=kf, n_jobs=1)))


print("single-column predictability of AQI (CV R^2):")
single = {p: round(cv_r2([p]), 4) for p in polls}
for p, r2 in single.items():
    print(f"  {p:>7}: {r2:+.4f}")
report["single_column_r2"] = single

print("\npairs (top 8):")
scores = sorted(((cv_r2(list(c)), c) for c in combinations(polls, 2)), reverse=True)
for r2, c in scores[:8]:
    print(f"  {' + '.join(c):<18}: {r2:+.4f}")
report["best_pairs"] = [{"columns": list(c), "cv_r2": round(r2, 4)}
                        for r2, c in scores[:8]]

print("\ncumulative greedy forward selection:")
chosen, remaining = [], list(polls)
forward = []
for step in range(5):
    best = max(((cv_r2(chosen + [p]), p) for p in remaining), key=lambda t: t[0])
    print(f"  + {best[1]:<7} -> R^2 = {best[0]:.4f}")
    forward.append({"added": best[1], "cv_r2": round(best[0], 4)})
    chosen.append(best[1])
    remaining.remove(best[1])
report["forward_selection"] = forward
report["informative_set"] = chosen
print(f"\nsmallest informative set found: {chosen}")
sub = df[chosen].join(df[[C.AQI_COL]])
print("\nshape of the relationship (deciles of the first chosen column):")
first = chosen[0]
sub["_bin"] = pd.qcut(sub[first], 10, duplicates="drop")
deciles = (sub.groupby("_bin", observed=True)[C.AQI_COL]
           .agg(["count", "mean", "std"]).round(2))
print(deciles.to_string())
report["deciles_of_first_column"] = {
    str(i): {"count": int(r["count"]), "aqi_mean": float(r["mean"]),
             "aqi_std": float(r["std"])} for i, r in deciles.iterrows()}
report["monotonic_in_first_column"] = bool(
    deciles["mean"].is_monotonic_increasing)
if len(chosen) > 1:
    print("\nAQI mean by quintile of the two chosen columns:")
    a = pd.qcut(sub[chosen[0]], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    b = pd.qcut(sub[chosen[1]], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    grid = pd.crosstab(a, b, values=sub[C.AQI_COL], aggfunc="mean").round(1)
    print(grid.to_string())
    report["quintile_grid_aqi_mean"] = {
        f"{chosen[0]}={i},{chosen[1]}={j}": float(v)
        for (i, j), v in grid.stack().items()}

print("\nDecisive test - 'AQI is the larger of two sub-indices':")
print("If AQI = max(subindex(PM2.5), subindex(PM10)), then holding one pollutant")
print("near its minimum must make AQI a pure function of the other.")
for fixed, other in (("PM2.5", "PM10"), ("PM10", "PM2.5")):
    low = df[df[fixed] <= df[fixed].quantile(0.05)]
    if len(low) < 100:
        continue
    oof = np.zeros(len(low))
    Xl = low[[other]].to_numpy(dtype="float64")
    yl = low[C.AQI_COL].to_numpy(dtype="float64")
    for tr, te in KFold(3, shuffle=True, random_state=42).split(Xl):
        oof[te] = RandomForestRegressor(n_estimators=150, min_samples_leaf=2,
                                        n_jobs=-1, random_state=42).fit(
            Xl[tr], yl[tr]).predict(Xl[te])
    r2 = 1 - np.sum((yl - oof) ** 2) / np.sum((yl - yl.mean()) ** 2)
    print(f"  rows with {fixed} in the lowest 5% (n={len(low):,}): "
          f"AQI vs {other} alone -> CV R^2 = {r2:.4f}")
    report.setdefault("hold-one-low", {})[fixed] = {
        "n_rows": int(len(low)), "other": other, "cv_r2": round(float(r2), 4)}

print("\nSpread of AQI inside cells where BOTH PM values are almost identical")
print("(a deterministic rule implies a spread close to zero):")
cell = df.assign(k25=(df["PM2.5"] // 10) * 10, k10=(df["PM10"] // 10) * 10)
sheet = (cell.groupby(["k25", "k10"])[C.AQI_COL].agg(["count", "min", "max", "std"])
         .query("count >= 8"))
print(f"  cells tested: {len(sheet)}")
print(f"  mean within-cell range (max-min): {(sheet['max'] - sheet['min']).mean():.2f} AQI points")
print(f"  mean within-cell SD             : {sheet['std'].mean():.2f} AQI points")
print(f"  overall AQI SD                  : {df[C.AQI_COL].std():.2f} AQI points")
report["within_pm_cell"] = {
    "cells_tested": int(len(sheet)),
    "mean_range": round(float((sheet["max"] - sheet["min"]).mean()), 2),
    "mean_sd": round(float(sheet["std"].mean()), 2),
    "overall_sd": round(float(df[C.AQI_COL].std()), 2),
}

out_json = C.PROCESSED_DIR / "aqi_driver_probe.json"
out_json.parent.mkdir(parents=True, exist_ok=True)
out_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(f"\nsaved: {out_json}")
