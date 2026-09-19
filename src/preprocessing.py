"""
Data cleaning: a documented, schema-agnostic cleaning pass.

Design rules enforced here
  * The raw file is never modified; everything operates on a copy.
  * Every step is logged (rows/values touched + justification) so the notebook
    can print an auditable "what was done and why" table.
  * Extreme values are FLAGGED, never silently deleted - a very high PM reading
    can be a genuine pollution episode (firecracker day, stubble burning, dust
    storm) rather than a recording error.
  * Physically impossible values (negative concentrations) are treated as
    recording errors, converted to missing, then imputed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C

UNKNOWN_LABEL = "Unknown"


class CleaningLog:
    """Collects one row per cleaning decision for the audit table."""

    def __init__(self) -> None:
        self._rows: list[dict] = []

    def add(self, step: str, action: str, touched: int | float | str = 0,
            justification: str = "") -> None:
        self._rows.append({"Step": len(self._rows) + 1, "Action Performed": step,
                           "Method / Rule": action,
                           "Rows / Values Affected": touched,
                           "Justification": justification})

    def to_frame(self) -> pd.DataFrame:
        return pd.DataFrame(
            self._rows,
            columns=["Step", "Action Performed", "Method / Rule",
                     "Rows / Values Affected", "Justification"])


# --------------------------------------------------------------------------- #
# Individual cleaning operations
# --------------------------------------------------------------------------- #
def parse_date(df: pd.DataFrame, log: CleaningLog) -> pd.Series:
    """Return a datetime Series parsed from whichever date column exists."""
    col = C.date_column(df.columns)
    if col is None:
        log.add("Date parsing", "skipped - no Date/Datetime column found", 0,
                "Nothing to parse, so time-based features stay unavailable.")
        return pd.Series(pd.NaT, index=df.index, name="Date")
    parsed = pd.to_datetime(df[col], errors="coerce")
    failed = int(parsed.isna().sum() - df[col].isna().sum())
    log.add("Date parsing", f"pd.to_datetime(errors='coerce') on '{col}'",
            max(failed, 0),
            "Explicit parsing so time features come from real calendar values "
            "instead of string slicing.")
    parsed.name = "Date"
    return parsed


def to_numeric(df: pd.DataFrame, cols: list[str], log: CleaningLog) -> pd.DataFrame:
    """Force the given columns to float, counting values that were not numeric."""
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        before = int(out[col].notna().sum())
        converted = pd.to_numeric(out[col], errors="coerce")
        lost = before - int(converted.notna().sum())
        if lost:
            log.add("Numeric coercion", f"'{col}' cast to float, non-numeric -> NaN",
                    lost,
                    "Text fragments inside a measurement column are unreadable "
                    "records, not measurements.")
        else:
            log.add("Numeric coercion check", f"'{col}' already fully numeric", 0,
                    "Verified rather than assumed; nothing had to be converted.")
        out[col] = converted
    return out


def flag_impossible(df: pd.DataFrame, cols: list[str], log: CleaningLog) -> pd.DataFrame:
    """Turn negative concentrations into missing values (physically impossible)."""
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        neg = int((out[col] < 0).sum())
        if neg:
            out.loc[out[col] < 0, col] = np.nan
        log.add("Impossible values", f"'{col}' < 0 set to NaN", neg,
                "A negative concentration cannot exist physically, so it is a "
                "recording error rather than an extreme pollution event.")
    return out


def impute_numeric(df: pd.DataFrame, cols: list[str], group_col: str | None,
                   log: CleaningLog) -> pd.DataFrame:
    """City-wise median imputation (global median fallback), with flag columns.

    Median is preferred to mean because pollutant distributions are skewed and
    the median is not dragged by extreme - possibly genuine - observations.
    Grouping by city respects the fact that each city has its own baseline.
    """
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        miss = int(out[col].isna().sum())
        if miss == 0:
            log.add("Missing values", f"'{col}' complete - no imputation needed", 0,
                    "Verified from the data; no values were fabricated.")
            continue
        if group_col and group_col in out.columns:
            filled = out.groupby(group_col)[col].transform(lambda s: s.fillna(s.median()))
            filled = filled.fillna(out[col].median())
            rule = f"median of the same {group_col} (global median fallback)"
        else:
            filled = out[col].fillna(out[col].median())
            rule = "global median"
        out[f"Imputed_{col}"] = out[col].isna().astype(int)
        out[col] = filled
        log.add("Missing values", f"'{col}' imputed with {rule}", miss,
                "Median keeps the imputed value inside the observed range and is "
                "robust to outliers; a flag column preserves which records were "
                "imputed so no result silently depends on invented data.")
    return out


def fill_categorical(df: pd.DataFrame, cols: list[str], log: CleaningLog,
                     mode_cols: list[str] | None = None) -> pd.DataFrame:
    """Missing categoricals become an explicit 'Unknown' band (never guessed)."""
    out = df.copy()
    mode_cols = mode_cols or []
    for col in cols:
        if col not in out.columns:
            continue
        miss = int(out[col].isna().sum())
        if miss == 0:
            log.add("Categorical values", f"'{col}' complete - nothing filled", 0,
                    "Verified from the data.")
            continue
        if col in mode_cols:
            out[col] = out[col].fillna(out[col].mode().iat[0])
            log.add("Categorical values", f"'{col}' filled with mode", miss,
                    "Only applied to labels with no meaningful 'missing' state.")
        else:
            out[col] = out[col].fillna(UNKNOWN_LABEL)
            log.add("Categorical values",
                    f"'{col}' filled with explicit '{UNKNOWN_LABEL}'", miss,
                    "An unknown band is honest; inventing a city or AQI category "
                    "would fabricate evidence.")
    return out


def flag_outliers_iqr(df: pd.DataFrame, cols: list[str], k: float = 1.5,
                      log: CleaningLog = None) -> pd.DataFrame:
    """Add <col>_Outlier flags using the IQR rule. Values are NOT modified."""
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            continue
        q1, q3 = out[col].quantile(0.25), out[col].quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - k * iqr, q3 + k * iqr
        flag = ((out[col] < lo) | (out[col] > hi)).astype(int)
        out[f"{col}_Outlier"] = flag
        if log is not None:
            log.add("Extreme values (flagged, kept)",
                    f"IQR rule on '{col}': bounds [{lo:.2f}, {hi:.2f}]",
                    int(flag.sum()),
                    "Retained because an extreme reading may be a real pollution "
                    "episode; deletion would erase exactly the events a BI "
                    "dashboard exists to surface.")
    return out


def remove_duplicates(df: pd.DataFrame, log: CleaningLog) -> pd.DataFrame:
    """Drop exact duplicate records and verify the City+Date key is unique."""
    exact = int(df.duplicated().sum())
    out = df.drop_duplicates().reset_index(drop=True)
    log.add("Duplicate removal", "drop_duplicates() on the full record", exact,
            "Exact copies are re-imported rows; keeping them would double-count "
            "observations in every average." if exact else
            "Checked for exact duplicates; none existed, so no rows were dropped.")
    date_col = C.date_column(df.columns)
    if C.CITY_COL in df.columns and date_col:
        key = [C.CITY_COL, date_col]
        dup_key = int(out.duplicated(subset=key).sum())
        log.add("Uniqueness check", f"duplicated(City, {date_col})", dup_key,
                "A city should appear once per day; repeats would mean two "
                "different monitoring records for the same day."
                if dup_key else
                "Verified: one record per city per day, so the panel is balanced.")
    return out


# --------------------------------------------------------------------------- #
# One-call pipeline
# --------------------------------------------------------------------------- #
def clean(df_raw: pd.DataFrame):
    """Run the full documented cleaning pipeline.

    Returns (cleaned_df, log_frame, before_summary, after_summary)
    """
    from data_utils import summary            # local import: avoids circular import

    log = CleaningLog()
    before_summary = summary(df_raw)

    # 1. duplicates ---------------------------------------------------------- #
    df = remove_duplicates(df_raw, log)

    # 2. types ---------------------------------------------------------------- #
    date_col = C.date_column(df.columns)
    pollutants = C.pollutant_columns(df.columns)
    measures = pollutants + ([C.AQI_COL] if C.AQI_COL in df.columns else [])
    df = to_numeric(df, measures, log)

    # 3. impossible values ---------------------------------------------------- #
    df = flag_impossible(df, pollutants, log)

    # 4. parsed date as a proper column --------------------------------------- #
    if date_col:
        df.insert(1, "Date", pd.to_datetime(df[date_col], errors="coerce"))
        if date_col != "Date":
            df = df.drop(columns=[date_col])
    else:
        df.insert(1, "Date", pd.NaT)

    # 5. categorical + numeric missing values --------------------------------- #
    cat_cols = [c for c in df.columns
                if not pd.api.types.is_numeric_dtype(df[c]) and c != "Date"]
    df = fill_categorical(df, cat_cols, log, mode_cols=[])
    df = impute_numeric(df, measures, C.CITY_COL if C.CITY_COL in df else None, log)

    # 6. ordered AQI category -------------------------------------------------- #
    if C.TARGET_COL in df.columns:
        order = [b for b in C.AQI_BUCKET_ORDER if b in set(df[C.TARGET_COL].unique())]
        df[C.TARGET_COL] = pd.Categorical(df[C.TARGET_COL], categories=order,
                                         ordered=True)
        log.add("Ordinal encoding",
                f"'{C.TARGET_COL}' cast to ordered category {order}", len(order),
                "AQI bands have a natural severity order, so models and charts "
                "sort them meaningfully instead of alphabetically.")

    # 7. extreme values: flagged, retained ------------------------------------ #
    df = flag_outliers_iqr(df, pollutants, log=log)

    after_summary = summary(df)
    return df, log.to_frame(), before_summary, after_summary
