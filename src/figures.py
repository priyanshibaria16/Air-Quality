"""
All figures used by the notebooks, the report and the dashboard documentation.

Every plot carries a title, axis labels and units, is saved under
visualizations/<category>/ and its path is returned, so nothing has to be
re-drawn by hand and every image in the report is reproducible.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

try:
    from . import config as C
    from . import viz as V
except ImportError:  # pragma: no cover
    import config as C
    import viz as V


def _new(figsize=(9, 5)):
    V.style()
    fig, ax = plt.subplots(figsize=figsize)
    return fig, ax


# --------------------------------------------------------------------------- #
# EDA
# --------------------------------------------------------------------------- #
def eda(feat: pd.DataFrame, pollutants: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    aqi = C.AQI_COL

    # 1. AQI distribution
    fig, ax = _new()
    ax.hist(feat[aqi].dropna(), bins=40, color="#1f77b4", edgecolor="white")
    mean, med = feat[aqi].mean(), feat[aqi].median()
    ax.axvline(mean, color="red", ls="--", label=f"mean = {mean:.1f}")
    ax.axvline(med, color="darkorange", ls="--", label=f"median = {med:.1f}")
    V.label_axes(ax, "Distribution of AQI across all observations",
                 f"Air Quality Index ({V.unit(aqi)})", "Number of daily records",
                 legend=True)
    out["01_aqi_distribution"] = str(V.savefig(fig, "01_aqi_distribution.png", "eda"))

    # 2. AQI category distribution
    if C.TARGET_COL in feat.columns:
        d = feat[C.TARGET_COL].astype(str).value_counts()
        order = [b for b in C.AQI_BUCKET_ORDER if b in d.index] + \
                [b for b in d.index if b not in C.AQI_BUCKET_ORDER]
        d = d.reindex(order)
        fig, ax = _new()
        bars = ax.bar(d.index, d.values, color=[V.AQI_COLORS.get(b, "#607d8b") for b in d.index])
        ax.bar_label(bars, fmt="{:,}", padding=2)
        V.label_axes(ax, "Observations per AQI category", "AQI category",
                     "Number of daily records")
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
        out["02_aqi_category_distribution"] = str(V.savefig(
            fig, "02_aqi_category_distribution.png", "eda"))

    # 3/4. city-wise average and median AQI
    if C.CITY_COL in feat.columns:
        g = feat.groupby(C.CITY_COL, observed=True)[aqi].agg(["mean", "median", "std"])
        fig, ax = _new()
        x = np.arange(len(g))
        ax.bar(x - 0.2, g["mean"], width=0.4, label="mean", color="#1f77b4")
        ax.bar(x + 0.2, g["median"], width=0.4, label="median", color="#2ca02c")
        ax.errorbar(x - 0.2, g["mean"], yerr=g["std"], fmt="none", ecolor="black",
                    capsize=3, label="mean +/- 1 SD")
        ax.set_xticks(x, g.index)
        V.label_axes(ax, f"Average vs median {aqi} by city", "City",
                     f"{aqi} ({V.unit(aqi)})", legend=True)
        out["03_city_avg_median_aqi"] = str(V.savefig(
            fig, "03_city_avg_median_aqi.png", "eda"))

        fig, ax = _new()
        data = [feat.loc[feat[C.CITY_COL] == c, aqi].dropna().values for c in g.index]
        bp = ax.boxplot(data, tick_labels=list(g.index), showfliers=False)
        for box, color in zip(bp["boxes"], V.PALETTE):
            # matplotlib < 3.11 returns a Patch for the box, >= 3.11 a Line2D
            # whose rectangle is drawn as a marker - support both.
            if hasattr(box, "set_facecolor"):
                box.set_facecolor(color)
                box.set_alpha(0.5)
            else:
                box.set_markerfacecolor(color)
                box.set_markeredgecolor(color)
                if hasattr(box, "set_markeralpha"):
                    box.set_markeralpha(0.5)
        V.label_axes(ax, "AQI spread within each city (box plot, outliers hidden)",
                     "City", f"{aqi} ({V.unit(aqi)})")
        out["04_city_aqi_boxplot"] = str(V.savefig(fig, "04_city_aqi_boxplot.png", "eda"))

    # 5-10. pollutant distributions
    n = len(pollutants)
    cols = 3
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.3 * cols, 3.2 * rows))
    axes = np.atleast_1d(axes).ravel()
    for i, p in enumerate(pollutants):
        axes[i].hist(feat[p].dropna(), bins=35, color="#9467bd", edgecolor="white")
        axes[i].set_title(f"{p} distribution", fontsize=10)
        axes[i].set_xlabel(V.unit(p))
        axes[i].set_ylabel("records")
    for j in range(i + 1, len(axes)):
        axes[j].axis("off")
    fig.suptitle("Pollutant concentration distributions", fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    out["05_pollutant_distributions"] = str(V.savefig(
        fig, "05_pollutant_distributions.png", "eda"))

    # 11. AQI over time (monthly aggregation keeps it readable)
    if "Date" in feat.columns:
        s = (feat.dropna(subset=["Date"])
                .groupby(feat["Date"].dt.to_period("M").astype(str), observed=True)[aqi]
                .mean())
        idx = pd.to_datetime(s.index)
        fig, ax = _new(figsize=(11, 4.5))
        ax.plot(idx, s.values, color="#1f77b4", lw=1.1, label="monthly mean AQI")
        V.trend_line(ax, idx.astype("int64") / 10 ** 9, s.values)
        V.label_axes(ax, "AQI over time (monthly average, all cities)",
                     "Year", f"{aqi} ({V.unit(aqi)})", legend=True)
        out["06_aqi_trend_time"] = str(V.savefig(fig, "06_aqi_trend_time.png", "eda"))

    # 12. monthly
    if "Month" in feat.columns:
        m = feat.groupby("Month", observed=True)[aqi].mean()
        names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
                 "Oct", "Nov", "Dec"]
        fig, ax = _new()
        ax.bar([names[int(k) - 1] for k in m.index], m.values, color="#ff7f0e")
        ax.axhline(feat[aqi].mean(), color="black", ls="--", lw=1,
                   label=f"overall mean = {feat[aqi].mean():.1f}")
        V.label_axes(ax, "Average AQI by month", "Month",
                     f"mean {aqi} ({V.unit(aqi)})", legend=True)
        out["07_monthly_aqi"] = str(V.savefig(fig, "07_monthly_aqi.png", "eda"))

    # 13. yearly
    if "Year" in feat.columns:
        yy = feat.groupby("Year", observed=True)[aqi].agg(["mean", "std"])
        fig, ax = _new()
        ax.errorbar(yy.index.astype(str), yy["mean"], yerr=yy["std"], marker="o",
                    lw=2, capsize=4, color="#2ca02c")
        V.label_axes(ax, "Average AQI by year (error bars = SD across records)",
                     "Year", f"mean {aqi} ({V.unit(aqi)})")
        out["08_yearly_aqi"] = str(V.savefig(fig, "08_yearly_aqi.png", "eda"))

    # 14. seasonal
    if "Season" in feat.columns:
        s = feat.groupby("Season", observed=True)[aqi].mean()
        fig, ax = _new()
        ax.bar(s.index.astype(str), s.values, color="#17becf")
        V.label_axes(ax, "Average AQI by season (project season definition)",
                     "Season", f"mean {aqi} ({V.unit(aqi)})")
        out["09_seasonal_aqi"] = str(V.savefig(fig, "09_seasonal_aqi.png", "eda"))

    # 15. PM2.5 vs PM10 scatter with trend
    if {"PM2.5", "PM10"}.issubset(feat.columns):
        samp = feat.sample(min(4000, len(feat)), random_state=C.RANDOM_STATE)
        fig, ax = _new()
        ax.scatter(samp["PM10"], samp["PM2.5"], s=8, alpha=0.4, color="#d62728")
        V.trend_line(ax, samp["PM10"], samp["PM2.5"])
        V.label_axes(ax, "PM2.5 against PM10 (random 4,000 records)",
                     f"PM10 ({V.unit('PM10')})", f"PM2.5 ({V.unit('PM2.5')})",
                     legend=True)
        out["10_pm25_vs_pm10"] = str(V.savefig(fig, "10_pm25_vs_pm10.png", "eda"))

    # 16. weekday / weekend comparison
    if "Day_Name" in feat.columns:
        order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                 "Saturday", "Sunday"]
        dw = feat.groupby("Day_Name", observed=True)[aqi].mean().reindex(order)
        fig, ax = _new()
        colors = ["#8c564b" if d in ("Saturday", "Sunday") else "#1f77b4"
                  for d in dw.index]
        ax.bar(dw.index, dw.values, color=colors)
        ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#1f77b4"),
                           plt.Rectangle((0, 0), 1, 1, color="#8c564b")],
                  labels=["weekday", "weekend"], loc="best")
        V.label_axes(ax, "Average AQI by day of week", "Day",
                     f"mean {aqi} ({V.unit(aqi)})")
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")
        out["11_weekday_aqi"] = str(V.savefig(fig, "11_weekday_aqi.png", "eda"))

    # 17. city x pollutant heat profile
    if C.CITY_COL in feat.columns and pollutants:
        prof = feat.groupby(C.CITY_COL, observed=True)[pollutants].mean()
        fig, ax = _new(figsize=(10, 4.5))
        im = ax.imshow(prof.values, aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(prof.columns)), prof.columns, rotation=30, ha="right")
        ax.set_yticks(range(len(prof.index)), prof.index)
        for i in range(prof.shape[0]):
            for j in range(prof.shape[1]):
                ax.text(j, i, f"{prof.values[i, j]:.0f}", ha="center", va="center",
                        color="white", fontsize=8)
        fig.colorbar(im, ax=ax, label="mean concentration (mixed units)")
        V.label_axes(ax, "City x pollutant mean profile", "Pollutant", "City")
        out["12_city_pollutant_heatmap"] = str(V.savefig(
            fig, "12_city_pollutant_heatmap.png", "eda"))
    return out


# --------------------------------------------------------------------------- #
# Correlation
# --------------------------------------------------------------------------- #
def correlation(corr: pd.DataFrame, corr_target: pd.DataFrame,
                rank_pairs: pd.DataFrame | None = None) -> dict[str, str]:
    out: dict[str, str] = {}
    V.style()
    fig, ax = plt.subplots(figsize=(max(7, 0.62 * len(corr) + 3),
                                    max(6, 0.55 * len(corr) + 2.5)))
    im = ax.imshow(corr.values, vmin=-1, vmax=1, cmap="coolwarm")
    ax.set_xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(corr.index)), corr.index)
    for i in range(corr.shape[0]):
        for j in range(corr.shape[1]):
            ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center",
                    fontsize=8, color="black" if abs(corr.values[i, j]) < 0.6 else "white")
    fig.colorbar(im, ax=ax, label="Pearson r")
    ax.set_title("Pearson correlation matrix of measured variables",
                 fontweight="bold")
    out["01_correlation_heatmap"] = str(V.savefig(fig, "01_correlation_heatmap.png",
                                                  "correlation"))

    if len(corr_target):
        d = corr_target.sort_values("Pearson_r")
        fig, ax = _new(figsize=(8, 0.42 * len(d) + 2))
        colors = ["#d62728" if r > 0 else "#1f77b4" for r in d["Pearson_r"]]
        ax.barh(d["Variable"], d["Pearson_r"], color=colors)
        ax.axvline(0, color="black", lw=1)
        for y, (r, p) in enumerate(zip(d["Pearson_r"], d["Pearson_p"])):
            ax.text(r, y, f"  r={r:+.3f} (p={p:.2g})", va="center", fontsize=8)
        V.label_axes(ax, "Linear association of each variable with AQI",
                     "Pearson r", "Variable")
        ax.set_xlim(-1.05, 1.35)
        out["02_pollutant_vs_aqi"] = str(V.savefig(
            fig, "02_pollutant_vs_aqi.png", "correlation"))

    if rank_pairs is not None and len(rank_pairs):
        fig, ax = _new(figsize=(9, 0.35 * len(rank_pairs) + 2))
        d = rank_pairs.sort_values("r")
        ax.barh([f"{a} - {b}" for a, b in zip(d["A"], d["B"])], d["r"], color="#9467bd")
        V.label_axes(ax, "Strongest pairwise pollutant correlations",
                     "Pearson r", "Variable pair")
        out["03_pairwise_correlations"] = str(V.savefig(
            fig, "03_pairwise_correlations.png", "correlation"))
    return out


# --------------------------------------------------------------------------- #
# Clustering
# --------------------------------------------------------------------------- #
def clustering_k(k_table: pd.DataFrame) -> dict[str, str]:
    """Elbow + silhouette panel - the evidence used to choose K."""
    V.style()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.6))
    a1.plot(k_table["K"], k_table["Inertia"], marker="o", lw=2, color="#1f77b4")
    a1.set_title("Elbow method: inertia vs K")
    a1.set_xlabel("Number of clusters K")
    a1.set_ylabel("Inertia (within-cluster sum of squares)")
    a2.plot(k_table["K"], k_table["Silhouette_Score"], marker="s", lw=2, color="#ff7f0e")
    a2.axhline(0.25, color="red", ls="--", lw=1, label="0.25 = weak-structure threshold")
    a2.set_title("Silhouette score vs K")
    a2.set_xlabel("Number of clusters K")
    a2.set_ylabel("Silhouette score")
    a2.legend()
    fig.tight_layout()
    return {"01_elbow_silhouette": str(V.savefig(fig, "01_elbow_silhouette.png",
                                                 "clustering"))}


def clustering(pcs: pd.DataFrame, labels: pd.Series, profile: pd.DataFrame,
               centroids_raw: pd.DataFrame, pollutants: list[str]) -> dict[str, str]:
    """PCA projection, cluster sizes, pollutant profiles and centroid heatmap."""
    out: dict[str, str] = {}
    V.style()
    fig, ax = _new(figsize=(9, 6))
    frame = pcs.copy()
    frame["Cluster"] = pd.Series(labels, index=frame.index).values
    for cid, g in frame.groupby("Cluster"):
        ax.scatter(g["PC1"], g["PC2"], s=10, alpha=0.55, label=f"Cluster {int(cid)}")
    expl = pcs.attrs.get("explained_variance_ratio", [None, None])
    V.label_axes(ax, "K-Means clusters projected to 2-D with PCA",
                 f"PC1 (explains {100*(expl[0] or 0):.1f}% of variance)",
                 f"PC2 (explains {100*(expl[1] or 0):.1f}% of variance)", legend=True)
    out["02_pca_clusters"] = str(V.savefig(fig, "02_pca_clusters.png", "clustering"))

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4))
    a1.bar(profile["Cluster"].astype(str), profile["Cluster_Size"], color="#2ca02c")
    a1.set_title("Cluster sizes")
    a1.set_xlabel("Cluster ID")
    a1.set_ylabel("Number of records")
    cols = [c for c in pollutants if f"Avg_{c}" in profile.columns]
    x = np.arange(len(cols))
    for i, (_, r) in enumerate(profile.iterrows()):
        a2.plot(x, [r[f"Avg_{c}"] for c in cols], marker="o", label=f"Cluster {int(r['Cluster'])}")
    a2.set_title("Average pollutant level per cluster")
    a2.set_xticks(x, cols, rotation=30, ha="right")
    a2.set_ylabel("mean concentration (mixed units)")
    a2.legend()
    fig.tight_layout()
    out["03_cluster_sizes_profiles"] = str(V.savefig(
        fig, "03_cluster_sizes_profiles.png", "clustering"))

    fig, ax = _new(figsize=(10, 4.6))
    body = centroids_raw.set_index("Cluster")[pollutants]
    norm = body.div(body.max(axis=0), axis=1)
    im = ax.imshow(norm.T.values, aspect="auto", cmap="YlGnBu", vmin=0, vmax=1)
    ax.set_yticks(range(len(norm.columns)), norm.columns, rotation=30, ha="right")
    ax.set_xticks(range(len(norm.index)), [f"Cluster {int(c)}" for c in norm.index])
    for i in range(norm.shape[1]):          # pollutants (rows of the transposed image)
        for j in range(norm.shape[0]):      # clusters (columns of the image)
            ax.text(j, i, f"{body.values[j, i]:.0f}", ha="center", va="center",
                    fontsize=8, color="black" if norm.values[j, i] < 0.6 else "white")
    fig.colorbar(im, ax=ax, label="share of the highest cluster mean")
    V.label_axes(ax, "Cluster centroids in original units (labels = mean concentration)",
                 "Cluster", "Pollutant")
    out["04_cluster_centroids"] = str(V.savefig(fig, "04_cluster_centroids.png",
                                                "clustering"))
    return out


# --------------------------------------------------------------------------- #
# Anomaly detection
# --------------------------------------------------------------------------- #
def anomaly(feat: pd.DataFrame, by_city: pd.DataFrame, by_year: pd.DataFrame,
            pollutants: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    V.style()
    ev = feat[feat["Anomaly"].notna()]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.4))
    cnt = ev["Anomaly_Label"].value_counts()
    a1.bar(cnt.index.astype(str), cnt.values, color=["#2ca02c", "#d62728"][:len(cnt)])
    a1.bar_label(a1.containers[0], fmt="{:,}")
    a1.set_title("Normal vs anomalous records")
    a1.set_ylabel("Number of records")
    a2.hist(ev["Anomaly_Score"], bins=50, color="#1f77b4")
    thr = ev.loc[ev["Anomaly"] == 1, "Anomaly_Score"].max()
    a2.axvline(thr, color="red", ls="--", label=f"decision boundary = {thr:.3f}")
    a2.set_title("Distribution of Isolation Forest scores")
    a2.set_xlabel("score_samples() (lower = more anomalous)")
    a2.set_ylabel("records")
    a2.legend()
    fig.tight_layout()
    out["01_anomaly_distribution"] = str(V.savefig(fig, "01_anomaly_distribution.png",
                                                   "anomaly"))

    if C.CITY_COL in by_city.columns:
        fig, ax = _new()
        ax.bar(by_city[C.CITY_COL].astype(str), by_city["Anomaly_Pct"], color="#ff7f0e")
        ax.axhline(100 * C.CONTAMINATION, color="black", ls="--",
                   label=f"configured contamination = {100*C.CONTAMINATION:.0f}%")
        V.label_axes(ax, "Share of records flagged anomalous, by city", "City",
                     "% of that city's records flagged", legend=True)
        out["02_anomaly_by_city"] = str(V.savefig(fig, "02_anomaly_by_city.png", "anomaly"))

    if len(by_year):
        fig, ax = _new(figsize=(10, 4.2))
        ax.plot(by_year["Period"], by_year["Anomaly_Pct"], marker="o", lw=2,
                color="#9467bd")
        V.label_axes(ax, "Anomaly rate over time", "Year", "% of records flagged")
        out["03_anomaly_timeline"] = str(V.savefig(fig, "03_anomaly_timeline.png",
                                                   "anomaly"))

    samp = ev.sample(min(3000, len(ev)), random_state=C.RANDOM_STATE)
    if {"PM2.5", "PM10"}.issubset(samp.columns):
        fig, ax = _new()
        for lab, c in [("Normal", "#2ca02c"), ("Anomaly", "#d62728")]:
            g = samp[samp["Anomaly_Label"] == lab]
            ax.scatter(g["PM10"], g["PM2.5"], s=10, alpha=0.5, color=c, label=lab)
        V.label_axes(ax, "Anomalies in the PM10 / PM2.5 plane (sample)",
                     f"PM10 ({V.unit('PM10')})", f"PM2.5 ({V.unit('PM2.5')})",
                     legend=True)
        out["04_anomaly_scatter"] = str(V.savefig(fig, "04_anomaly_scatter.png", "anomaly"))
    return out


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #
def classification(comp: pd.DataFrame, conf: pd.DataFrame, per_class: pd.DataFrame,
                   importance: pd.DataFrame, classes: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    V.style()
    fig, ax = _new(figsize=(10, 4.8))
    d = comp.sort_values("Accuracy_%")
    x = np.arange(len(d))
    ax.bar(x - 0.2, d["Accuracy_%"], width=0.4, label="Accuracy %", color="#1f77b4")
    ax.bar(x + 0.2, 100 * d["F1_macro"], width=0.4, label="macro F1 x 100",
           color="#ff7f0e")
    ax.set_xticks(x, d["Model"], rotation=18, ha="right")
    for i, v in zip(x - 0.2, d["Accuracy_%"]):
        ax.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=8)
    V.label_axes(ax, "Model comparison on the held-out test split", "Model",
                 "Score (%)", legend=True)
    ax.set_ylim(0, 112)
    out["01_model_comparison"] = str(V.savefig(fig, "01_model_comparison.png",
                                              "classification"))

    models = [m for m in conf["Model"].unique() if not str(m).startswith("Baseline")]
    show = models[:4]
    fig, axes = plt.subplots(1, len(show), figsize=(4.2 * len(show), 3.9),
                             squeeze=False)
    labels = sorted(conf["Actual"].unique())
    for ax, name in zip(axes[0], show):
        m = (conf[conf["Model"] == name]
               .pivot(index="Actual", columns="Predicted", values="Count")
               .reindex(index=labels, columns=labels).fillna(0))
        im = ax.imshow(np.log1p(m.values), cmap="Blues")
        ax.set_xticks(range(len(labels)), labels, rotation=45, ha="right", fontsize=7)
        ax.set_yticks(range(len(labels)), labels, fontsize=7)
        ax.set_title(name, fontsize=10, fontweight="bold")
        for i in range(len(labels)):
            for j in range(len(labels)):
                if m.values[i, j] > 0:
                    ax.text(j, i, f"{int(m.values[i, j])}", ha="center", va="center",
                            fontsize=6,
                            color="white" if np.log1p(m.values[i, j]) > 3 else "black")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
    fig.colorbar(im, ax=axes, shrink=0.7, label="log(1+count)")
    fig.suptitle("Confusion matrices (log-scaled counts)", fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    out["02_confusion_matrices"] = str(V.savefig(fig, "02_confusion_matrices.png",
                                                 "classification"))

    pc = per_class[~per_class["Class"].isin(["accuracy", "macro avg", "weighted avg"])]
    if len(pc):
        fig, ax = _new(figsize=(11, 4.6))
        mods = [m for m in pc["Model"].unique() if not m.startswith("Baseline")]
        width = 0.8 / max(len(mods), 1)
        for k, m in enumerate(mods):
            d = pc[pc["Model"] == m].set_index("Class").reindex(labels)
            ax.bar(np.arange(len(labels)) + k * width, d["Recall"], width=width, label=m)
        ax.set_xticks(np.arange(len(labels)) + width, labels, rotation=20, ha="right")
        V.label_axes(ax, "Per-class recall: how well each AQI band is detected",
                     "AQI category", "Recall", legend=True)
        out["03_per_class_recall"] = str(V.savefig(fig, "03_per_class_recall.png",
                                                   "classification"))

    if len(importance):
        fig, ax = _new(figsize=(8, 4.4))
        d = importance.sort_values("Importance")
        ax.barh(d["Feature"], d["Importance"], color="#2ca02c")
        V.label_axes(ax, "Random Forest feature importance (mean decrease in impurity)",
                     "Importance", "Pollutant")
        out["04_feature_importance"] = str(V.savefig(fig, "04_feature_importance.png",
                                                     "classification"))
    return out


# --------------------------------------------------------------------------- #
# Project framework (no data needed - it documents the method itself)
# --------------------------------------------------------------------------- #
# Each stage carries the artefact or decision it produces, so the diagram doubles
# as a map from method to the file that evidences it.
METHODOLOGY_STAGES = [
    ("Dataset",                       "data/raw/Air_quality_data.csv, read once, never edited", "prep"),
    ("Data Understanding",             "shape, dtypes, missing values, distributions", "prep"),
    ("Data Cleaning",                  "air_quality_cleaned.csv + cleaning_log.csv", "prep"),
    ("Feature Engineering",            "ratios, rolling means, calendar and season fields", "prep"),
    ("EDA",                             "distributions, city / time / season profiles", "describe"),
    ("Correlation Analysis",            "correlation_matrix.csv, significance tests", "describe"),
    ("K-Means",                         "k chosen by elbow + silhouette; cluster_profile.csv", "mine"),
    ("Anomaly Detection",               "Isolation Forest; anomaly_results.csv", "mine"),
    ("Classification",                  "AQI band from pollutants; leakage test included", "mine"),
    ("Model Evaluation",                "model_comparison.csv, confusion matrices", "mine"),
    ("Processed Dataset",               "fact table + DIM_Date / DIM_City / DIM_Bucket", "bi"),
    ("Power BI",                         "star schema, DAX measures, 5 dashboard pages", "bi"),
    ("Insights",                         "insights.csv - each row tied to its evidence", "bi"),
]

METHODOLOGY_PHASES = {
    "prep":     ("Understanding & preparation", "#DCE6F1", "#2F5597"),
    "describe": ("Description & association",   "#E2EFDA", "#548235"),
    "mine":     ("Data mining",                 "#FCE4D6", "#C55A11"),
    "bi":       ("Delivery & decision support", "#EAE1F2", "#7030A0"),
}


def methodology_diagram(title: str = "Project methodology: data to insight",
                        subdir: str = "methodology") -> str:
    """Draw the 13-stage methodology chain (one column, arrows, phase brackets).

    Flat by design: no 3-D, no colour without meaning, and every stage names the
    artefact that proves it was carried out.
    """
    stages = METHODOLOGY_STAGES
    n = len(stages)
    step = 1.0
    box_w, box_h = 6.2, 0.62
    x_box = 5.6                                   # centre of the stage boxes
    x_bracket = 1.15
    fig, ax = _new(figsize=(8.6, 1.02 * n))
    ax.set_axis_off()
    ax.set_xlim(0, 11)
    ax.set_ylim(0, n * step)
    ax.grid(False)

    top = n * step - 0.35
    for i, (name, detail, phase) in enumerate(stages):
        y = top - i * step
        face, edge = METHODOLOGY_PHASES[phase][1], METHODOLOGY_PHASES[phase][2]
        ax.add_patch(FancyBboxPatch((x_box - box_w / 2, y - box_h / 2), box_w, box_h,
                                    boxstyle="round,pad=0,rounding_size=0.10",
                                    linewidth=1.1, edgecolor=edge, facecolor=face))
        ax.text(x_box, y + 0.11, f"{i + 1}. {name}", ha="center", va="center",
                fontsize=10.5, fontweight="bold", color="#1a1a1a")
        ax.text(x_box, y - 0.15, detail, ha="center", va="center",
                fontsize=7.6, style="italic", color="#333333")
        if i < n - 1:
            ax.annotate("", xy=(x_box, y - box_h / 2 - 0.30),
                        xytext=(x_box, y - box_h / 2 - 0.06),
                        arrowprops=dict(arrowstyle="-|>,head_width=0.16,head_length=0.30",
                                        lw=1.3, color="#555555"))

    # one bracket per contiguous phase, labelled vertically on the left
    for phase, (label, _face, edge) in METHODOLOGY_PHASES.items():
        idx = [i for i, s in enumerate(stages) if s[2] == phase]
        if not idx:
            continue
        y_hi = top - min(idx) * step + box_h / 2
        y_lo = top - max(idx) * step - box_h / 2
        ax.plot([x_bracket, x_bracket], [y_lo, y_hi], lw=5, color=edge,
                solid_capstyle="round")
        ax.text(x_bracket - 0.28, (y_hi + y_lo) / 2, label, rotation=90,
                ha="center", va="center", fontsize=9.5, fontweight="bold", color=edge)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
    fig.text(0.5, 0.012, "Stages 1-4 notebooks 01-03 - 5-6 notebook 04-05 - 7-10 notebooks "
                         "06-08 - 11 notebook 09 - 12-13 dashboard/ and insights.csv",
             ha="center", fontsize=7.6, color="#555555")
    fig.subplots_adjust(left=0.06, right=0.99, top=0.97, bottom=0.035)
    return str(V.savefig(fig, "01_methodology_diagram.png", subdir))
