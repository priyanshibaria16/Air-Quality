"""
Loading, profiling and data-quality helpers.

Nothing in this module assumes a fixed schema: the columns reported are the
columns that are physically present in the CSV.
"""
from __future__ import annotations

import pandas as pd

try:  # allows `import src.data_utils` from a notebook run at project root
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


def load_raw(path=None) -> pd.DataFrame:
    """Load the raw dataset without touching/altering any value."""
    path = C.RAW_FILE if path is None else path
    if not pd.io.common.file_exists(str(path)):
        raise FileNotFoundError(
            f"Raw dataset not found at {path}. Expected one of {C.RAW_CANDIDATES}."
        )
    return pd.read_csv(path)


def profile(df: pd.DataFrame) -> pd.DataFrame:
    """Per-column profile: dtype, non-null, missing, % missing, unique, min/max.

    Numerical min/max and categorical cardinality are reported side by side so
    the same table is useful for any schema.
    """
    date_col = C.date_column(df.columns)
    rows = []
    for col in df.columns:
        s = df[col]
        numeric = pd.api.types.is_numeric_dtype(s)
        info = {
            "Column": col,
            "Dtype": str(s.dtype),
            "NonNull": int(s.notna().sum()),
            "Missing": int(s.isna().sum()),
            "Missing_Pct": round(100 * s.isna().mean(), 2),
            "Unique": int(s.nunique(dropna=True)),
        }
        if numeric:
            info["Min"] = round(float(s.min()), 3) if s.notna().any() else None
            info["Max"] = round(float(s.max()), 3) if s.notna().any() else None
            info["Mean"] = round(float(s.mean()), 3) if s.notna().any() else None
            info["Median"] = round(float(s.median()), 3) if s.notna().any() else None
        else:
            info["Min"] = info["Max"] = info["Mean"] = info["Median"] = None
        info["Negative_Values"] = int((s < 0).sum()) if numeric else 0
        rows.append(info)
    prof = pd.DataFrame(rows).astype(
        {"Min": "object", "Max": "object", "Mean": "object", "Median": "object"}
    )

    # Give the date column a parsed view of its range without mutating the input
    if date_col:
        parsed = pd.to_datetime(df[date_col], errors="coerce")
        if len(parsed.dropna()):
            prof.loc[prof["Column"] == date_col, "Min"] = str(parsed.min().date())
            prof.loc[prof["Column"] == date_col, "Max"] = str(parsed.max().date())
    return prof


def summary(df: pd.DataFrame) -> dict:
    """Headline statistics used by the data-quality report."""
    date_col = C.date_column(df.columns)
    pollutants = C.pollutant_columns(df.columns)
    numeric_cols = [c for c in df.select_dtypes("number").columns]
    # pandas >=3 stores text as a 'str' dtype, not 'object', so select by
    # exclusion instead of hard-coding "object".
    cat_cols = [c for c in df.columns if not pd.api.types.is_numeric_dtype(df[c])]
    parsed = pd.to_datetime(df[date_col], errors="coerce") if date_col else pd.Series(dtype="datetime64[ns]")
    return {
        "Total Rows": int(df.shape[0]),
        "Total Columns": int(df.shape[1]),
        "Duplicate Rows": int(df.duplicated().sum()),
        "Total Missing Values": int(df.isna().sum().sum()),
        "Columns With Missing": int((df.isna().sum() > 0).sum()),
        "Unique Cities": int(df[C.CITY_COL].nunique()) if C.CITY_COL in df else 0,
        "Date Column": date_col or "not found",
        "Date Start": str(parsed.min().date()) if len(parsed.dropna()) else "n/a",
        "Date End": str(parsed.max().date()) if len(parsed.dropna()) else "n/a",
        "Numerical Columns": len(numeric_cols),
        "Categorical Columns": len(cat_cols),
        "Pollutant Columns Detected": len(pollutants),
        "Pollutants": ", ".join(pollutants),
        "AQI Column Present": str(C.AQI_COL in df.columns),
        "AQI_Bucket Column Present": str(C.TARGET_COL in df.columns),
    }


def missing_table(df: pd.DataFrame) -> pd.DataFrame:
    """Columns ranked by missing-value percentage (only columns with gaps)."""
    t = pd.DataFrame({
        "Column": df.columns,
        "Missing": df.isna().sum().values,
    })
    t["Missing_Pct"] = (100 * t["Missing"] / max(len(df), 1)).round(2)
    t = t[t["Missing"] > 0].sort_values("Missing_Pct", ascending=False)
    return t.reset_index(drop=True)


def aqi_band_table() -> pd.DataFrame:
    """The AQI band table from `config.py` as a DataFrame (worst band first).

    Centralising this keeps every check, dimension table and figure reading the
    same scale instead of each one re-typing breakpoint numbers.
    """
    return pd.DataFrame([{"AQI_Bucket": label, "Lower": lo, "Upper": hi}
                         for label, lo, hi in C.AQI_BUCKET_BANDS])


def band_from_aqi(values) -> pd.Series:
    """Map AQI numbers onto band labels using `config.AQI_BUCKET_BANDS`.

    The interval edges are derived from the table itself and made continuous, so
    the only thing this function can get wrong is the table - and notebook 02
    tests that table against the labels the dataset already carries.
    """
    bands = sorted(C.AQI_BUCKET_BANDS, key=lambda b: b[1])      # lowest band first
    labels = [label for label, _, _ in bands]                   # ascending severity
    edges = [bands[0][1]] + [hi + 1 for _, _, hi in bands]      # 0, 51, 101, ...
    s = pd.to_numeric(pd.Series(values), errors="coerce")
    return pd.cut(s, bins=edges, labels=labels, right=False).astype("string")


def quality_comparison(before: dict, after: dict) -> pd.DataFrame:
    """Side-by-side 'Before Cleaning vs After Cleaning' metric table."""
    keys = ["Total Rows", "Total Columns", "Duplicate Rows", "Total Missing Values",
            "Columns With Missing", "Unique Cities", "Date Start", "Date End",
            "Numerical Columns", "Categorical Columns"]
    rows = [{"Metric": k,
             "Before Cleaning": before.get(k),
             "After Cleaning": after.get(k)} for k in keys]
    return pd.DataFrame(rows)


def data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    """Human-readable dictionary generated from the *actual* columns."""
    descriptions = {
        "City": "Name of the monitored Indian city",
        "Datetime": "Observation date (daily record)",
        "Date": "Observation date (daily record)",
        "PM2.5": "Fine particulate matter ≤ 2.5 µm concentration",
        "PM10": "Inhalable particulate matter ≤ 10 µm concentration",
        "NO": "Nitric oxide concentration",
        "NO2": "Nitrogen dioxide concentration",
        "NOx": "Total nitrogen oxides concentration",
        "NH3": "Ammonia concentration",
        "CO": "Carbon monoxide concentration",
        "SO2": "Sulphur dioxide concentration",
        "O3": "Ozone concentration",
        "Benzene": "Benzene concentration",
        "Toluene": "Toluene concentration",
        "Xylene": "Xylene concentration",
        "AQI": "Air Quality Index as supplied by the dataset",
        "AQI_Bucket": "Categorical AQI band derived from AQI by the data owner",
    }
    prof = profile(df).set_index("Column")
    rows = []
    for col in df.columns:
        p = prof.loc[col]
        kind = "Numeric" if pd.api.types.is_numeric_dtype(df[col]) else "Categorical"
        if C.date_column(df.columns) == col:
            kind = "Date (text in raw file)"
        rows.append({
            "Column": col,
            "Type": kind,
            "Description": descriptions.get(col, "Not documented in source dataset"),
            "Missing Values": int(p["Missing"]),
            "Missing %": p["Missing_Pct"],
            "Unique": int(p["Unique"]),
        })
    return pd.DataFrame(rows)
