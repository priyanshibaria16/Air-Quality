"""
Feature engineering: calendar attributes, seasons, derived pollution
indicators and rolling time-series context.

Honesty rules
  * The dataset already supplies an official-style AQI, so no AQI formula is
    re-invented. Any index created here is explicitly labelled as a
    project-specific analytical index.
  * Every helper checks that its input columns exist and simply skips (with a
    logged note) when they do not.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C

MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
             "Saturday", "Sunday"]


# --------------------------------------------------------------------------- #
# Calendar / temporal features
# --------------------------------------------------------------------------- #
def add_time_features(df: pd.DataFrame, date_col: str = "Date") -> pd.DataFrame:
    """Derive Year, Month, Month_Name, Quarter, Day, weekday and Season."""
    out = df.copy()
    if date_col not in out.columns or out[date_col].isna().all():
        for col in ["Year", "Month", "Month_Name", "Quarter", "Quarter_Label",
                    "Day", "Day_of_Week", "Day_Name", "Week_of_Year",
                    "Is_Weekend", "Season", "Year_Month"]:
            out[col] = np.nan
        return out

    d = pd.to_datetime(out[date_col], errors="coerce")
    out["Year"] = d.dt.year.astype("Int64")
    out["Month"] = d.dt.month.astype("Int64")
    out["Month_Name"] = d.dt.month.map(dict(enumerate(MONTH_NAMES, start=1))).astype("string")
    out["Quarter"] = d.dt.quarter.astype("Int64")
    out["Quarter_Label"] = "Q" + out["Quarter"].astype(str)
    out["Day"] = d.dt.day.astype("Int64")
    out["Day_of_Week"] = d.dt.dayofweek.astype("Int64")   # Monday = 0
    out["Day_Name"] = d.dt.dayofweek.map(dict(enumerate(DAY_NAMES))).astype("string")
    out["Week_of_Year"] = d.dt.isocalendar().week.astype("Int64")
    out["Is_Weekend"] = (out["Day_of_Week"] >= 5).astype(int)
    out["Year_Month"] = d.dt.strftime("%Y-%m").astype("string")

    # Indian meteorological convention documented in config.SEASON_MAP. This is
    # a reporting convention for this project, not a universal scientific
    # definition of season.
    out["Season"] = out["Month"].map(C.SEASON_MAP).astype("category")
    out["Season"] = out["Season"].cat.set_categories(C.SEASON_ORDER, ordered=True)
    return out


# --------------------------------------------------------------------------- #
# Derived pollution indicators
# --------------------------------------------------------------------------- #
def add_ratio_features(df: pd.DataFrame, log: list[str] | None = None) -> pd.DataFrame:
    """Concentration ratios that compare pollutant *composition*, not level."""
    out = df.copy()
    note = log if log is not None else []

    def ratio(name: str, num: str, den: str, scale: float = 1.0):
        if num in out.columns and den in out.columns:
            with np.errstate(divide="ignore", invalid="ignore"):
                out[name] = np.where(out[den] > 0, scale * out[num] / out[den], np.nan)
        else:
            note.append(f"{name} skipped: requires '{num}' and '{den}'")

    # Fine / coarse particulate split: a composition indicator, unit-free.
    ratio("PM25_PM10_Ratio", "PM2.5", "PM10")
    # Share of NO2 inside NOx (both supplied; treated as reported sub-terms).
    ratio("NO2_NOx_Ratio", "NO2", "NOx")
    # Relative dominance of secondary gas pollution vs primary particulates.
    if "O3" in out.columns and "PM10" in out.columns:
        out["O3_PM10_Ratio"] = np.where(out["PM10"] > 0, out["O3"] / out["PM10"], np.nan)
    else:
        note.append("O3_PM10_Ratio skipped: requires 'O3' and 'PM10'")
    return out


def add_pollution_index(df: pd.DataFrame, pollutants: list[str] | None = None,
                        log: list[str] | None = None) -> pd.DataFrame:
    """Add `Pollution_Index`: an equal-weight 0-100 project-specific index.

    Each available pollutant is min-max scaled onto [0, 1] using the observed
    range of this dataset, then averaged and rescaled to 0-100.

    This is NOT an official AQI. It exists only to let the dashboard compare
    records on a common 0-100 scale without claiming regulatory meaning.
    """
    out = df.copy()
    note = log if log is not None else []
    pollutants = pollutants or C.pollutant_columns(out.columns)
    pollutants = [p for p in pollutants if p in out.columns]
    if not pollutants:
        note.append("Pollution_Index skipped: no pollutant columns available")
        out["Pollution_Index"] = np.nan
        return out

    block = out[pollutants].astype("float64")
    lo, hi = block.min(), block.max()
    span = (hi - lo).replace(0, np.nan)
    scaled = (block - lo) / span
    out["Pollution_Index"] = (100 * scaled.mean(axis=1)).round(2)
    out["Pollution_Index_Band"] = pd.cut(
        out["Pollution_Index"],
        bins=[-0.01, 20, 40, 60, 80, 100],
        labels=["Very Low", "Low", "Medium", "High", "Very High"],
        ordered=True,
    )
    note.append(f"Pollution_Index built from {len(pollutants)} pollutants "
                f"({', '.join(pollutants)}); project-specific scale, not official AQI")
    return out


def add_elevated_counts(df: pd.DataFrame, pollutants: list[str] | None = None) -> pd.DataFrame:
    """How many pollutants sit in the top quartile of a city's own history."""
    out = df.copy()
    pollutants = [p for p in (pollutants or C.pollutant_columns(out.columns))
                  if p in out.columns]
    if not pollutants:
        out["Pollutants_Above_City_Q3"] = np.nan
        out["City_Pollutant_Percentile"] = np.nan
        return out

    group = out[C.CITY_COL] if C.CITY_COL in out.columns else pd.Series(0, index=out.index)
    counts = pd.Series(0, index=out.index, dtype="int64")
    ranks = pd.Series(0.0, index=out.index)
    for p in pollutants:
        q3 = out.groupby(group, observed=True)[p].transform(lambda s: s.quantile(0.75))
        counts = counts + (out[p] > q3).astype("int64")
        ranks = ranks + out.groupby(group, observed=True)[p].rank(pct=True)
    out["Pollutants_Above_City_Q3"] = counts
    # Mean within-city percentile across all available pollutants (0-100).
    out["City_Pollutant_Percentile"] = (100 * ranks / len(pollutants)).round(1)
    return out


def add_rolling_features(df: pd.DataFrame, col: str = C.AQI_COL,
                         windows: tuple[int, ...] = (7, 30),
                         group_col: str = C.CITY_COL) -> pd.DataFrame:
    """Per-city lag / rolling-mean context, used for dashboard trend lines."""
    out = df.copy()
    if col not in out.columns:
        return out
    key = group_col if group_col in out.columns else None
    if key:
        out = out.sort_values([key, "Date"]) if "Date" in out.columns else out.sort_values(key)
        g = out.groupby(key, observed=True)[col]
    else:
        g = out[col].groupby(pd.Series(0, index=out.index))
    out[f"{col}_Lag_1"] = g.shift(1)
    out[f"{col}_Change_1d"] = g.diff(1)
    for w in windows:
        out[f"{col}_Rolling_{w}"] = g.transform(
            lambda s, w=w: s.rolling(w, min_periods=1).mean())
        out[f"{col}_RollingStd_{w}"] = g.transform(
            lambda s, w=w: s.rolling(w, min_periods=2).std())
    return out


# --------------------------------------------------------------------------- #
# One-call pipeline
# --------------------------------------------------------------------------- #
def build_features(df: pd.DataFrame, with_rolling: bool = True):
    """Apply every engineering step. Returns (feature_frame, notes_list)."""
    notes: list[str] = []
    out = add_time_features(df)
    notes.append("Calendar features added: Year, Month, Month_Name, Quarter, Day, "
                 "Day_of_Week, Week_of_Year, Is_Weekend, Year_Month")
    notes.append("Season added using the Indian meteorological convention "
                 "Winter=12-2, Summer=3-5, Monsoon=6-9, Post-Monsoon=10-11 "
                 "(project-specific, not a universal scientific definition)")
    out = add_ratio_features(out, log=notes)
    out = add_pollution_index(out, log=notes)
    out = add_elevated_counts(out)
    if with_rolling:
        out = add_rolling_features(out)
        notes.append("Per-city lag/rolling features added for trend readability")
    return out, notes


def feature_inventory(df: pd.DataFrame) -> pd.DataFrame:
    """Describe the engineered columns for the report."""
    engineered = ["Year", "Month", "Month_Name", "Quarter", "Quarter_Label", "Day",
                  "Day_of_Week", "Day_Name", "Week_of_Year", "Is_Weekend", "Season",
                  "Year_Month", "PM25_PM10_Ratio", "NO2_NOx_Ratio", "O3_PM10_Ratio",
                  "Pollution_Index", "Pollution_Index_Band",
                  "Pollutants_Above_City_Q3", "City_Pollutant_Percentile",
                  f"{C.AQI_COL}_Lag_1", f"{C.AQI_COL}_Change_1d",
                  f"{C.AQI_COL}_Rolling_7", f"{C.AQI_COL}_Rolling_30",
                  f"{C.AQI_COL}_RollingStd_7"]
    purposes = {
        "Year": "yearly trend comparison",
        "Month": "monthly seasonality",
        "Season": "seasonal aggregation",
        "Is_Weekend": "weekday vs weekend behaviour",
        "PM25_PM10_Ratio": "fine vs coarse particulate composition",
        "NO2_NOx_Ratio": "share of freshly emitted NO2 in NOx",
        "Pollution_Index": "common 0-100 scale across pollutants (project index)",
        "Pollutants_Above_City_Q3": "how many pollutants are simultaneously high",
        f"{C.AQI_COL}_Rolling_7": "smoothed trend for dashboards",
    }
    rows = [{"Feature": c, "Present": c in df.columns,
             "Dtype": str(df[c].dtype) if c in df.columns else "-",
             "Purpose": purposes.get(c, "supporting BI attribute")}
            for c in engineered]
    return pd.DataFrame(rows)
