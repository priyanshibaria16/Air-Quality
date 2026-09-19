"""Integrity probe: is the supplied data consistent with real monitored air
quality, or with randomly generated values?

    python tools/probe_integrity.py

Checks performed
  1. Distribution shape of every numeric column (uniformity test).
  2. Pairwise |correlation| between pollutants and AQI.
  3. City-effect test (one-way ANOVA on AQI).
  4. Season/month effect test on AQI.
  5. Temporal autocorrelation (real daily pollution series are strongly
     autocorrelated; random series are not).
  6. Consistency of AQI_Bucket with the AQI numeric value.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config as C  # noqa: E402
import data_utils as U  # noqa: E402

df = U.load_raw()
df["_date"] = pd.to_datetime(df[C.date_column(df.columns)])
polls = C.pollutant_columns(df.columns)
num = polls + [C.AQI_COL]

print("=" * 72)
print("1. UNIFORMITY TEST (Kolmogorov-Smirnov vs uniform on [min, max])")
print("=" * 72)
for c in num:
    s = df[c].dropna()
    stat, p = stats.kstest((s - s.min()) / (s.max() - s.min()), "uniform")
    print(f"{c:>7}: KS p={p:>.4g}  skew={stats.skew(s):+.3f}  "
          f"kurt={stats.kurtosis(s):+.3f}  min={s.min():.2f} max={s.max():.2f}")

print("\n" + "=" * 72)
print("2. CORRELATION WITH AQI  and  MAX |PAIRWISE POLLUTANT CORRELATION|")
print("=" * 72)
corr = df[num].corr()
aqi_c = corr[C.AQI_COL].drop(C.AQI_COL).sort_values(key=abs, ascending=False)
print(aqi_c.round(4).to_string())
pc = corr.loc[polls, polls]
off = pc.where(~np.eye(len(polls), dtype=bool))
top = off.stack().abs().sort_values(ascending=False).head(5)
print("\nstrongest pollutant pairs:")
print(top.round(4).to_string())

print("\n" + "=" * 72)
print("3. CITY EFFECT ON AQI (one-way ANOVA)")
print("=" * 72)
groups = [g[C.AQI_COL].dropna().values for _, g in df.groupby(C.CITY_COL)]
F, p = stats.f_oneway(*groups)
print(f"F={F:.3f}  p={p:.4g}")
print(df.groupby(C.CITY_COL)[C.AQI_COL].agg(["mean", "median", "std"]).round(2).to_string())

print("\n" + "=" * 72)
print("4. MONTH / SEASON EFFECT ON AQI (Kruskal-Wallis)")
print("=" * 72)
mo = [g[C.AQI_COL].dropna().values for _, g in df.groupby(df._date.dt.month)]
H, p = stats.kruskal(*mo)
print(f"month: H={H:.3f} p={p:.4g}")
df["Season"] = df._date.dt.month.map(C.SEASON_MAP)
sg = [g[C.AQI_COL].dropna().values for _, g in df.groupby("Season")]
H, p = stats.kruskal(*sg)
print(f"season: H={H:.3f} p={p:.4g}")
print(df.groupby("Season")[C.AQI_COL].mean().round(2).to_string())
print("\nmonthly mean AQI:")
print(df.groupby(df._date.dt.month)[C.AQI_COL].mean().round(1).to_string())

print("\n" + "=" * 72)
print("5. LAG-1 AUTOCORRELATION PER CITY (real series >> 0, random ~= 0)")
print("=" * 72)
for city, g in df.sort_values("_date").groupby(C.CITY_COL):
    for col in (C.AQI_COL, "PM2.5"):
        v = g[col].dropna().values
        r = np.corrcoef(v[:-1], v[1:])[0, 1]
        print(f"{city:<10} {col:<6} lag1 r = {r:+.4f}")

print("\n" + "=" * 72)
print("6. AQI_BUCKET vs AQI CONSISTENCY (CPCB breakpoints)")
print("=" * 72)
BINS = [(0, 50, "Good"), (51, 100, "Satisfactory"), (101, 200, "Moderate"),
        (201, 300, "Poor"), (301, 400, "Very Poor"), (401, 500, "Severe")]


def expected(v):
    for lo, hi, lab in BINS:
        if lo <= v <= hi:
            return lab
    return "OutOfScale"


df["Expected_Bucket"] = df[C.AQI_COL].map(expected)
agree = (df["Expected_Bucket"] == df[C.TARGET_COL]).mean()
print(f"bucket matches CPCB breakpoints: {100*agree:.2f}% of rows")
print(pd.crosstab(df[C.AQI_COL].between(0, 500), df[C.TARGET_COL]).to_string())
print("\nAQI range per bucket:")
print(df.groupby(C.TARGET_COL)[C.AQI_COL].agg(["min", "max", "count"]).round(1).to_string())

print("\n" + "=" * 72)
print("7. VALUE GRANULARITY / ROUNDING SIGNATURE")
print("=" * 72)
for c in polls:
    s = df[c].dropna()
    decimals = s.astype(str).str.split(".").str[1].fillna("").str.len()
    print(f"{c:>7}: distinct={s.nunique():>6} of {len(s)} rows, "
          f"1-decimal share={100*(decimals == 1).mean():.1f}%")
