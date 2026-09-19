"""Hypothesis test: is AQI a deterministic function of the pollutant columns?

    python tools/probe_aqi_rule.py

Motivation: a random-forest regressor reconstructs AQI from the concentrations
with CV R^2 ~ 0.997 while linear regression reaches 0.058. That combination
suggests a "max of sub-indices" rule, which is how the CPCB AQI is computed:
the reported AQI equals the largest single-pollutant sub-index.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config as C  # noqa: E402
import data_utils as U  # noqa: E402

df = U.load_raw()
polls = C.pollutant_columns(df.columns)
aqi = df[C.AQI_COL].to_numpy(dtype="float64")

print("Hypothesis A: AQI = max over pollutants of a monotone sub-index")
best = None
for p in polls:
    s = df[p].to_numpy(dtype="float64")
    m = np.isfinite(s)
    order = np.argsort(s[m])
    a = aqi[m][order]
    mono = float((np.diff(a) >= -1e-9).mean())   # share of non-decreasing steps
    print(f"  {p:>7}: AQI non-decreasing in {p} for {100*mono:5.1f}% of consecutive steps")

# group-wise maximum check: AQI should equal the largest per-pollutant implied value
ratio = df[polls].apply(lambda s: s / s.max())
pred = 500 * ratio.max(axis=1)
r2 = 1 - np.sum((aqi - pred) ** 2) / np.sum((aqi - aqi.mean()) ** 2)
print(f"\n  naive 500*max(normalised pollutant): R^2 = {r2:.4f}")

# per-pollutant empirical sub-index curve learned from the data
from sklearn.ensemble import RandomForestRegressor  # noqa: E402
from sklearn.model_selection import KFold  # noqa: E402

X = df[polls].to_numpy(dtype="float64")
kf = KFold(3, shuffle=True, random_state=42)
oof = np.zeros(len(aqi))
for tr, te in kf.split(X):
    oof[te] = RandomForestRegressor(n_estimators=200, min_samples_leaf=2,
                                    n_jobs=-1, random_state=42).fit(X[tr], aqi[tr]).predict(X[te])
print(f"  random-forest CV R^2 = {1 - np.sum((aqi-oof)**2)/np.sum((aqi-aqi.mean())**2):.4f}, "
      f"MAE = {np.mean(np.abs(aqi-oof)):.3f} AQI points")

print("\nHypothesis B: AQI equals the sub-index of exactly one pollutant per row")
# For each pollutant fit AQI ~ f(p) alone; the true driver should reach R^2 ~ 1
for p in polls:
    s = df[[p]].to_numpy(dtype="float64")
    oof1 = np.zeros(len(aqi))
    for tr, te in KFold(3, shuffle=True, random_state=42).split(s):
        oof1[te] = RandomForestRegressor(n_estimators=120, min_samples_leaf=2,
                                         n_jobs=-1, random_state=42).fit(s[tr], aqi[tr]).predict(s[te])
    r = 1 - np.sum((aqi - oof1) ** 2) / np.sum((aqi - aqi.mean()) ** 2)
    print(f"  {p:>7} alone: R^2 = {r:7.4f}")

print("\nHypothesis C: which pollutant's single-pollutant curve does AQI follow?")
# argmax over per-pollutant predictions of the AQI implied curve
implied = {}
for p in polls:
    s = df[p].to_numpy(dtype="float64")
    o = np.argsort(s)
    implied[p] = np.interp(s, s[o], aqi[o])
imp = pd.DataFrame(implied)
winner = imp.idxmax(axis=1)
print(imp.corrwith(pd.Series(aqi, index=imp.index), method="spearman").round(3).to_string())
print("\nrows where max-implied value equals AQI within 0.6:",
      int((np.abs(imp.max(axis=1) - aqi) <= 0.6).sum()), "of", len(imp))
print("share by which pollutant attains that maximum:")
print((winner.value_counts(normalize=True) * 100).round(1).to_string())
