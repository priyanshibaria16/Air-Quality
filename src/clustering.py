"""
K-Means clustering of pollution profiles: feature matrix construction,
scaling, evidence-based choice of K, cluster profiling and PCA projection.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


def build_matrix(df: pd.DataFrame, features: list[str]):
    """Return (X_scaled, scaler, used_features, raw_matrix) for real columns only."""
    used = [f for f in features if f in df.columns]
    if not used:
        raise ValueError("None of the requested clustering features exist in the data.")
    raw = df[used].apply(pd.to_numeric, errors="coerce").dropna()
    scaler = StandardScaler()
    scaled = scaler.fit_transform(raw)
    return pd.DataFrame(scaled, index=raw.index, columns=used), scaler, used, raw


def choose_k(X: pd.DataFrame, k_range=range(2, 11),
             random_state: int = C.RANDOM_STATE, sample: int = 6000) -> pd.DataFrame:
    """Elbow (inertia) + silhouette table. K is chosen from this evidence.

    Silhouette is computed on a fixed random subsample for tractability on
    large frames; the sample size is reported so the number is reproducible.
    """
    rng = np.random.default_rng(random_state)
    idx = (rng.choice(len(X), size=min(sample, len(X)), replace=False)
           if len(X) > sample else np.arange(len(X)))
    Xs = X.iloc[idx]
    rows = []
    for k in k_range:
        model = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X)
        labels = model.predict(Xs)
        sil = silhouette_score(Xs, labels) if len(set(labels)) > 1 else np.nan
        rows.append({"K": k, "Inertia": round(float(model.inertia_), 2),
                     "Silhouette_Score": round(float(sil), 4),
                     "Clusters_Used": int(len(set(labels))),
                     "Evaluated_On": f"{len(Xs)} rows (silhouette), {len(X)} rows (inertia)"})
    return pd.DataFrame(rows)


def recommend_k(table: pd.DataFrame, elbow_shrink: float = 0.05) -> dict:
    """Pick K by best silhouette, with the elbow point reported as corroboration.

    The elbow is defined as the first K after which the relative reduction in
    inertia falls below `elbow_shrink` - a stated, reproducible rule rather
    than a visual guess.
    """
    t = table.sort_values("K")
    best = t.loc[t["Silhouette_Score"].idxmax()]
    inert = t["Inertia"].values
    drops = np.abs(np.diff(inert) / inert[:-1])
    elbow_k = None
    for i, d in enumerate(drops):
        if d < elbow_shrink:
            elbow_k = int(t["K"].values[i + 1])
            break
    return {
        "K_by_silhouette": int(best["K"]),
        "silhouette": float(best["Silhouette_Score"]),
        "K_by_elbow_rule": elbow_k,
        "elbow_rule": f"first K where inertia improvement < {elbow_shrink:.0%}",
        "chosen_K": int(best["K"]),
        "rationale": ("chosen to maximise silhouette separation, corroborated by "
                      "the elbow rule" if elbow_k in (None, int(best["K"])) else
                      "silhouette preferred; the elbow rule suggested a different K, "
                      "which is reported as a disagreement rather than hidden"),
    }


def fit(df: pd.DataFrame, features: list[str], k: int,
        random_state: int = C.RANDOM_STATE):
    """Standardise, fit K-Means and attach Cluster to the original frame."""
    X, scaler, used, raw = build_matrix(df, features)
    model = KMeans(n_clusters=k, n_init=10, random_state=random_state).fit(X)
    out = df.loc[raw.index].copy()
    out["Cluster"] = model.labels_
    centers = pd.DataFrame(model.cluster_centers_, columns=[f"z_{c}" for c in used])
    centers["Cluster"] = centers.index
    # centroids expressed back in original units for readable reporting
    inv = scaler.inverse_transform(model.cluster_centers_)
    original = pd.DataFrame(inv, columns=used)
    original.insert(0, "Cluster", original.index)
    return out, model, scaler, used, centers, original


def cluster_profile(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Size plus average of each metric per cluster (neutral, numeric evidence)."""
    metrics = [m for m in metrics if m in df.columns]
    prof = (df.groupby("Cluster", observed=True)
              .agg(**{"Cluster_Size": (metrics[0], "size"),
                      **{f"Avg_{m}": (m, "mean") for m in metrics},
                      **{f"Median_{m}": (m, "median") for m in metrics}})
              .round(3)
              .reset_index())
    prof["Share_%"] = (100 * prof["Cluster_Size"] / prof["Cluster_Size"].sum()).round(2)
    return prof


def describe_clusters(profile: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    """Assign a neutral label from the data: highest/lowest on the key metric.

    Labels describe relative position only. No cluster is called 'good' or
    'dangerous' - that would require an external standard the project does
    not assert.
    """
    metrics = [m for m in metrics if f"Avg_{m}" in profile.columns]
    rows = []
    for _, r in profile.iterrows():
        rank_txt = ", ".join(
            f"{m}: rank {int((profile[f'Avg_{m}'] > r[f'Avg_{m}']).sum() + 1)}"
            for m in metrics[:4])
        rows.append({"Cluster": int(r["Cluster"]),
                     "Size": int(r["Cluster_Size"]),
                     "Relative_Position (1 = highest)": rank_txt,
                     "Neutral_Description": _describe_row(r, profile, metrics)})
    return pd.DataFrame(rows)


def _describe_row(r, profile, metrics) -> str:
    if not metrics:
        return "no metrics available"
    key = metrics[0]
    vals = profile[f"Avg_{key}"]
    if r[f"Avg_{key}"] == vals.max():
        return f"highest average {key} among clusters"
    if r[f"Avg_{key}"] == vals.min():
        return f"lowest average {key} among clusters"
    return f"intermediate average {key} among clusters"


def pca_projection(X: pd.DataFrame, n_comp: int = 2,
                   random_state: int = C.RANDOM_STATE) -> pd.DataFrame:
    """2-D PCA view of the standardised features, with explained variance.

    PCA only visualises; the coordinates discard the variance that is not in
    the first components, which is reported alongside the projection.
    """
    pca = PCA(n_components=n_comp, random_state=random_state)
    coords = pca.fit_transform(X)
    out = pd.DataFrame(coords, columns=[f"PC{i+1}" for i in range(n_comp)], index=X.index)
    out.attrs["explained_variance_ratio"] = [round(float(v), 4)
                                             for v in pca.explained_variance_ratio_]
    out.attrs["components"] = pd.DataFrame(pca.components_, columns=X.columns,
                                           index=[f"PC{i+1}" for i in range(n_comp)])
    return out
