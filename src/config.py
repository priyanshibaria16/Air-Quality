"""
Central configuration for the Air Quality & Pollution Intelligence project.

Every notebook and script imports paths and constants from here so that no
absolute file path is ever hard-coded inside analysis code.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

# --------------------------------------------------------------------------- #
# Paths (all resolved relative to the project root, i.e. the folder that
# contains this src/ package)
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
SRC_DIR = PROJECT_ROOT / "src"
VIZ_DIR = PROJECT_ROOT / "visualizations"
DASHBOARD_DIR = PROJECT_ROOT / "dashboard"
REPORT_DIR = PROJECT_ROOT / "report"

# The uploaded file is named Air_quality_data.csv. The Kaggle dataset it comes
# from is usually published as city_day.csv, so both names are accepted.
RAW_CANDIDATES = ("Air_quality_data.csv", "city_day.csv")
RAW_FILE = next((RAW_DIR / n for n in RAW_CANDIDATES if (RAW_DIR / n).exists()),
                RAW_DIR / RAW_CANDIDATES[0])

for _d in (PROCESSED_DIR, VIZ_DIR, DASHBOARD_DIR, REPORT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Output datasets ------------------------------------------------------------- #
CLEANED_CSV = PROCESSED_DIR / "air_quality_cleaned.csv"
CITY_SUMMARY_CSV = PROCESSED_DIR / "city_summary.csv"
MONTHLY_SUMMARY_CSV = PROCESSED_DIR / "monthly_summary.csv"
CLUSTER_RESULTS_CSV = PROCESSED_DIR / "cluster_results.csv"
CLUSTER_PROFILE_CSV = PROCESSED_DIR / "cluster_profile.csv"
ANOMALY_RESULTS_CSV = PROCESSED_DIR / "anomaly_results.csv"
CLASSIFICATION_CSV = PROCESSED_DIR / "classification_results.csv"
MODEL_COMPARISON_CSV = PROCESSED_DIR / "model_comparison.csv"
CORRELATION_CSV = PROCESSED_DIR / "correlation_matrix.csv"
DATA_QUALITY_CSV = PROCESSED_DIR / "data_quality_report.csv"
INSIGHTS_CSV = PROCESSED_DIR / "insights.csv"
DIM_DATE_CSV = PROCESSED_DIR / "dim_date.csv"
DIM_BUCKET_CSV = PROCESSED_DIR / "dim_bucket.csv"
DIM_CITY_CSV = PROCESSED_DIR / "dim_city.csv"

# --------------------------------------------------------------------------- #
# Column contract - filled/validated at runtime, never assumed
# --------------------------------------------------------------------------- #
CITY_COL = "City"
DATE_COL_CANDIDATES = ("Datetime", "Date")
TARGET_COL = "AQI_Bucket"
AQI_COL = "AQI"

POLLUTANT_CANDIDATES = [
    "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3", "CO", "SO2", "O3",
    "Benzene", "Toluene", "Xylene",
]

# Indian meteorological season definition used throughout the project.
# This is a project-specific convention (commonly used for Indian climate
# reporting); it is NOT a universal scientific definition.
SEASON_MAP = {
    1: "Winter", 2: "Winter", 3: "Winter",
    4: "Summer", 5: "Summer", 6: "Summer",
    7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Post-Monsoon", 11: "Post-Monsoon", 12: "Post-Monsoon",
}
SEASON_ORDER = ["Winter", "Summer", "Monsoon", "Post-Monsoon"]

# Display order for AQI categories, worst first (CPCB-style labels as they
# appear in the dataset).
AQI_BUCKET_ORDER = [
    "Severe", "Very Poor", "Poor", "Moderate", "Satisfactory", "Good", "Unknown",
]

# AQI category bands, worst first. These are the CPCB NAAQI ranges that the
# labels in this file use: Central Pollution Control Board, National Air
# Quality Index (Technical Report), CPCB, New Delhi, 2014 - six categories,
# 0-50 Good, 51-100 Satisfactory, 101-200 Moderate, 201-300 Poor,
# 301-400 Very Poor, 401-500 Severe.
# The boundaries are NOT assumed: notebook 02 recomputes AQI_Bucket from AQI
# with this table and reports the agreement with the supplied labels, so the
# scale is verified against the data itself rather than taken on trust. Because
# the labels are a pure function of AQI, AQI_Bucket is treated as a derived
# column and is never used as a predictor of (or alongside) AQI.
AQI_BUCKET_BANDS = [
    ("Severe", 401, 500),
    ("Very Poor", 301, 400),
    ("Poor", 201, 300),
    ("Moderate", 101, 200),
    ("Satisfactory", 51, 100),
    ("Good", 0, 50),
]

# Hex colours used by both the matplotlib figures and the Power BI guide, so the
# dashboard and the report never disagree about what "Severe" looks like. These
# are the project's own severity ramp (green -> yellow -> orange -> red ->
# maroon) chosen so that colour order matches band order; they are not presented
# as the official CPCB colour codes.
AQI_COLORS = {
    "Good": "#00E400",
    "Satisfactory": "#8BC34A",
    "Moderate": "#FFFF00",
    "Poor": "#FF9800",
    "Very Poor": "#F44336",
    "Severe": "#7E0023",
    "Unknown": "#9E9E9E",
}

# --------------------------------------------------------------------------- #
# Reproducibility
# --------------------------------------------------------------------------- #
RANDOM_STATE = 42
TEST_SIZE = 0.25
K_RANGE = range(2, 11)
CONTAMINATION = 0.05          # Isolation Forest expected anomaly fraction
FIG_DPI = 130

# Unit assumptions: particulate matter and gases in µg/m³, CO in mg/m³ is the
# convention of the source dataset. Units are reported as "µg/m³ (as supplied)"
# to avoid asserting a conversion the raw data does not document.
UNIT_LABELS = {
    "PM2.5": "µg/m³", "PM10": "µg/m³", "NO": "µg/m³", "NO2": "µg/m³",
    "NOx": "µg/m³", "NH3": "µg/m³", "CO": "mg/m³", "SO2": "µg/m³",
    "O3": "µg/m³", "Benzene": "µg/m³", "Toluene": "µg/m³", "Xylene": "µg/m³",
    "AQI": "index",
}


def pick(columns, name: str, required: bool = True):
    """Return the column actually present in *columns* that matches *name*.

    Prevents the code from ever assuming a column exists: if the requested
    column is absent the function either raises a clear error or returns None.
    """
    columns = list(columns)
    if name in columns:
        return name
    # tolerate cosmetic differences such as 'PM2.5 ' or 'pm2.5'
    lookup = {str(c).strip().lower(): c for c in columns}
    match = lookup.get(name.strip().lower())
    if match is None and required:
        raise KeyError(
            f"Column {name!r} is not in the dataset. Available columns: {columns}"
        )
    return match


def pollutant_columns(columns) -> list[str]:
    """Pollutant columns that genuinely exist in the supplied dataset."""
    present = {str(c).strip(): c for c in columns}
    return [present[p] for p in POLLUTANT_CANDIDATES if p in present]


def date_column(columns):
    for cand in DATE_COL_CANDIDATES:
        if cand in list(columns):
            return cand
    return None


def safe_div(numerator, denominator):
    """Division that yields NaN instead of raising on zero/NaN."""
    with np.errstate(divide="ignore", invalid="ignore"):
        return numerator / denominator
