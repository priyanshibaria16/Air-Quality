"""Throwaway probe: settle the date-completeness question and read config constants."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import json  # noqa: E402
import pandas as pd  # noqa: E402

import config as C  # noqa: E402

r = json.loads((C.PROCESSED_DIR / "results.json").read_text(encoding="utf-8"))
ds = r["dataset"]
print("dataset date-related keys:")
for k, v in ds.items():
    if any(t in k.lower() for t in ("date", "day", "gap", "complete", "panel")):
        print("   ", k, "=", v)

raw = pd.read_csv(C.RAW_FILE)
print("\nRAW file:")
print("   Datetime non-null uniques:", raw["Datetime"].dropna().nunique())
print("   rows:", len(raw))
null = raw["Datetime"].isna().sum()
print("   null Datetimes:", null)
per_day = raw.groupby(raw["Datetime"].str.slice(0, 10)).size()
print("   days with != 5 rows:", (per_day != 5).sum())
print("   value counts of rows-per-day:", per_day.value_counts().to_dict())

cleaned = pd.read_csv(C.CLEANED_CSV)
cper = cleaned.groupby("Date").size()
print("\nCLEANED export:")
print("   distinct dates:", cleaned["Date"].nunique(), "| rows:", len(cleaned))
print("   days with != 5 rows:", (cper != 5).sum(), cper.value_counts().to_dict())
full = pd.date_range(cleaned["Date"].min(), cleaned["Date"].max())
present = set(pd.to_datetime(cleaned["Date"]).unique())
print("   calendar days in range:", len(full), "| absent:", len(set(full) - present))

print("\nconfig constants:")
for name in ("TEST_SIZE", "RANDOM_STATE", "K_RANGE", "CONTAMINATION", "N_ESTIMATORS",
             "CLUSTER_FEATURES", "MODEL_PARAMS"):
    if hasattr(C, name):
        print("   ", name, "=", getattr(C, name))
print("\nclassification keys:", list(r["classification"].keys()))
print("params:", json.dumps(r["classification"].get("params", {}), indent=1)[:500])
