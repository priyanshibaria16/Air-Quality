"""Smoke test: run load -> clean -> features -> statistics on the real data.

    python tools/smoke_test.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import config as C          # noqa: E402
import data_utils as U      # noqa: E402
import preprocessing as P   # noqa: E402
import feature_engineering as FE  # noqa: E402
import statistics_analysis as S   # noqa: E402

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 50)

raw = U.load_raw()
clean, log, before, after = P.clean(raw)
print("CLEANING LOG\n", log.to_string(max_colwidth=60), "\n")
print("QUALITY COMPARISON\n", U.quality_comparison(before, after).to_string(), "\n")
print("SHAPE after cleaning:", clean.shape)
print("\nDTYPES\n", clean.dtypes.to_string())

feat, notes = FE.build_features(clean)
print("\nFEATURE NOTES\n")
for n in notes:
    print(" -", n)
print("\nFEATURE INVENTORY\n", FE.feature_inventory(feat).to_string())
print("\nSAMPLE\n", feat.head(3).T.to_string())

polls = C.pollutant_columns(feat.columns)
meas = polls + [C.AQI_COL]
print("\nDESCRIPTIVES\n", S.descriptive_stats(feat, meas).to_string())
print("\nDISTRIBUTION TESTS\n", S.distribution_tests(feat, meas).to_string())
print("\nCITY COMPARISON\n", {k: v for k, v in S.group_comparison(feat, C.AQI_COL, "City").items()
                             if k != "group_means"})
print(S.group_comparison(feat, C.AQI_COL, "City")["group_means"])
print("\nSEASON COMPARISON\n", {k: v for k, v in S.group_comparison(feat, C.AQI_COL, "Season").items()
                               if k != "group_means"})
print("\nAUTOCORRELATION\n", S.autocorrelation(feat, C.AQI_COL).to_string())
print("\nCORR WITH AQI\n", S.correlation_with_target(feat, polls, C.AQI_COL).to_string())
print("\nTREND TEST\n", S.linear_trend_test(feat, C.AQI_COL))
print("\nLINEAR FIT\n", S.linear_fit(feat, C.AQI_COL, polls))
print("\nALL MODULES OK")
