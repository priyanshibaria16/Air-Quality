"""Ad-hoc profiling of the raw dataset (run with any Python that has pandas).

    python tools/inspect_raw.py

Prints the facts the project is allowed to rely on: shape, dtypes, missing
values, duplicates, cities and date range. Nothing is written to disk.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config as C  # noqa: E402
import data_utils as U  # noqa: E402

df = U.load_raw()
print("FILE:", C.RAW_FILE)
print("SHAPE:", df.shape)
print("\nCOLUMNS:", list(df.columns))
print("\nDTYPES:\n", df.dtypes.to_string())
print("\nHEAD:\n", df.head().to_string())
print("\nTAIL:\n", df.tail().to_string())
print("\nMISSING:\n", U.missing_table(df).to_string())
print("\nEXACT DUPLICATE ROWS:", int(df.duplicated().sum()))
print("DUPLICATE (City, Date) PAIRS:",
      int(df.duplicated(subset=[c for c in [C.CITY_COL, C.date_column(df.columns)] if c]).sum()))
print("\nUNIQUE CITIES:", df[C.CITY_COL].nunique())
print(df[C.CITY_COL].value_counts().to_string())
dcol = C.date_column(df.columns)
dates = pd.to_datetime(df[dcol], errors="coerce")
print("\nDATE RANGE:", dates.min(), "->", dates.max(), "| unparseable:", int(dates.isna().sum()))
print("\nYEARS:\n", dates.dt.year.value_counts().sort_index().to_string())
print("\nAQI_BUCKET VALUES:\n", df[C.TARGET_COL].value_counts(dropna=False).to_string())
print("\nNEGATIVE / IMPOSSIBLE VALUES:")
for c in df.select_dtypes("number").columns:
    n = int((df[c] < 0).sum())
    z = int((df[c] == 0).sum())
    print(f"  {c}: negative={n}, zero={z}, min={df[c].min()}, max={df[c].max()}")
print("\nPOLLUTANTS DETECTED:", C.pollutant_columns(df.columns))
