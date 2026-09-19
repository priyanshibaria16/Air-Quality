"""
AQI-category classification, with explicit leakage and imbalance handling.

Two rules shape this module:
  1. AQI_Bucket is derived from AQI by the data owner, so AQI can never be a
     predictor of AQI_Bucket. `leakage_check` quantifies what happens if that
     rule is broken, which is the point of the exercise.
  2. Accuracy alone is meaningless on an imbalanced target, so a prior-based
     DummyClassifier baseline is always reported next to the real models.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (classification_report, confusion_matrix,
                             f1_score, precision_score, recall_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


# --------------------------------------------------------------------------- #
# Target hygiene
# --------------------------------------------------------------------------- #
def class_balance(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Counts, share and imbalance ratio of every class present in the data."""
    vc = df[target].value_counts().sort_values(ascending=False)
    t = pd.DataFrame({"Class": vc.index.astype(str), "Count": vc.values})
    t["Percent"] = (100 * t["Count"] / t["Count"].sum()).round(2)
    t["Rank"] = range(1, len(t) + 1)
    ratio = t["Count"].max() / t["Count"].min()
    t.attrs["imbalance_ratio"] = round(float(ratio), 1)
    t.attrs["majority_class"] = str(t.iloc[0]["Class"])
    t.attrs["majority_share_pct"] = float(t.iloc[0]["Percent"])
    t.attrs["baseline_accuracy_pct"] = float(t.iloc[0]["Percent"])
    return t


def drop_non_informative(df: pd.DataFrame, target: str) -> pd.DataFrame:
    """Remove records whose AQI band is unknown/unlabelled."""
    keep = df[target].notna() & (df[target].astype(str).str.strip() != "")
    return df[keep].copy()


def leakage_check(df: pd.DataFrame, features: list[str], target: str,
                  suspect: str = C.AQI_COL) -> dict:
    """Compare model accuracy with and without a suspect (leaky) column."""
    if suspect not in df.columns:
        return {"suspect_column": suspect, "present": False}
    from sklearn.ensemble import RandomForestClassifier
    res = {"suspect_column": suspect, "present": True, "target": target}
    for label, cols in (("without leaky column", features),
                        ("with leaky column", features + [suspect])):
        d = df[[c for c in cols] + [target]].dropna()
        X, y = d[cols], d[target]
        Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=C.TEST_SIZE,
                                              random_state=C.RANDOM_STATE, stratify=y)
        m = RandomForestClassifier(n_estimators=150, random_state=C.RANDOM_STATE,
                                   n_jobs=-1).fit(Xtr, ytr)
        res[label] = {"accuracy_%": round(100 * m.score(Xte, yte), 2),
                      "macro_F1": round(f1_score(yte, m.predict(Xte), average="macro"), 4),
                      "features_used": len(cols)}
    a = res["without leaky column"]["accuracy_%"]
    b = res["with leaky column"]["accuracy_%"]
    res["accuracy_inflation_pp"] = round(b - a, 2)
    res["verdict"] = (f"including {suspect} inflates accuracy by "
                      f"{b - a:.2f} percentage points, so {suspect} is excluded "
                      f"from all reported models")
    return res


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
def build_models(random_state: int = C.RANDOM_STATE) -> dict:
    """Baseline + linear + tree + ensemble learners, all reproducible.

    Logistic Regression is wrapped in a Pipeline with StandardScaler because
    its optimisation is scale-sensitive; tree models are not.
    """
    return {
        "Baseline (prior)": DummyClassifier(strategy="prior"),
        "Logistic Regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                       random_state=random_state))]),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=12, min_samples_leaf=20, class_weight="balanced",
            random_state=random_state),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=None, min_samples_leaf=2,
            class_weight="balanced_subsample", n_jobs=2,
            random_state=random_state),
        "Hist Gradient Boosting": HistGradientBoostingClassifier(
            max_iter=250, learning_rate=0.1, random_state=random_state),
    }


def train_and_evaluate(df: pd.DataFrame, features: list[str], target: str,
                       test_size: float = C.TEST_SIZE,
                       random_state: int = C.RANDOM_STATE,
                       cv_folds: int = 0):
    """Train every model on a stratified split and score it honestly.

    Returns (comparison_table, reports, matrices, split_info, X_test_frame,
    y_test, predictions_frame).
    """
    used = [f for f in features if f in df.columns and f != target]
    data = df[used + [target]].dropna()
    X, y = data[used], data[target].astype(str)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y)

    models = build_models(random_state)
    rows, reports, matrices, preds = [], {}, {}, {}
    for name, model in models.items():
        model.fit(X_train, y_train)
        y_hat = model.predict(X_test)
        preds[name] = y_hat
        rep = classification_report(y_test, y_hat, output_dict=True, zero_division=0)
        reports[name] = rep
        matrices[name] = confusion_matrix(y_test, y_hat, labels=sorted(y.unique()))
        row = {
            "Model": name,
            "Accuracy_%": round(100 * float(rep["accuracy"]), 2),
            "Precision_macro": round(precision_score(y_test, y_hat, average="macro",
                                                     zero_division=0), 4),
            "Recall_macro": round(recall_score(y_test, y_hat, average="macro",
                                               zero_division=0), 4),
            "F1_macro": round(f1_score(y_test, y_hat, average="macro", zero_division=0), 4),
            "Precision_weighted": round(precision_score(y_test, y_hat,
                                                        average="weighted",
                                                        zero_division=0), 4),
            "F1_weighted": round(f1_score(y_test, y_hat, average="weighted",
                                          zero_division=0), 4),
            "Lift_over_Baseline_pp": None,
            "CV_Folds": cv_folds if cv_folds else "not run",
        }
        if cv_folds and cv_folds >= 2:
            # n_jobs=1 on purpose: nested parallelism (outer CV x inner forest
            # threads) exhausted memory on a laptop-class machine.
            scores = cross_val_score(model, X, y,
                                     scoring="accuracy",
                                     cv=StratifiedKFold(n_splits=cv_folds,
                                                        shuffle=True,
                                                        random_state=random_state),
                                     n_jobs=1)
            row["CV_Accuracy_%"] = round(100 * float(np.mean(scores)), 2)
            row["CV_Std_pp"] = round(100 * float(np.std(scores)), 2)
        rows.append(row)

    comp = pd.DataFrame(rows)
    base = comp.loc[comp["Model"] == "Baseline (prior)", "Accuracy_%"]
    if not base.empty:
        comp["Lift_over_Baseline_pp"] = (comp["Accuracy_%"] - float(base.iloc[0])).round(2)
    comp = comp.sort_values("F1_macro", ascending=False).reset_index(drop=True)

    split_info = {
        "features_used": used, "n_features": len(used), "target": target,
        "train_rows": int(len(X_train)), "test_rows": int(len(X_test)),
        "test_size": test_size, "stratified": True, "random_state": random_state,
        "classes": sorted(y.unique()), "excluded_leaky_column": C.AQI_COL,
    }
    pred_frame = X_test.copy()
    pred_frame["Actual"] = y_test.values
    for name, y_hat in preds.items():
        pred_frame[f"Pred_{name}"] = y_hat
    return comp, reports, matrices, split_info, pred_frame, y_test, X_test


def fit_reference_model(df: pd.DataFrame, features: list[str], target: str,
                        name: str = "Random Forest", random_state: int = C.RANDOM_STATE):
    """Fit one named model on the whole frame, purely to read its importances."""
    used = [f for f in features if f in df.columns and f != target]
    data = df[used + [target]].dropna()
    model = build_models(random_state)[name]
    model.fit(data[used], data[target].astype(str))
    return model, used


def feature_importance(model, features: list[str], top: int = 15) -> pd.DataFrame:
    """Mean decrease in impurity for a fitted RandomForest (no permutation here)."""
    est = model.named_steps["clf"] if isinstance(model, Pipeline) else model
    if not hasattr(est, "feature_importances_"):
        return pd.DataFrame(columns=["Feature", "Importance"])
    imp = pd.DataFrame({"Feature": features,
                        "Importance": np.round(est.feature_importances_, 5)})
    return imp.sort_values("Importance", ascending=False).head(top).reset_index(drop=True)


def report_to_frame(name: str, report: dict) -> pd.DataFrame:
    """classification_report dict -> tidy table (per-class precision/recall/F1)."""
    rows = []
    for cls, vals in report.items():
        if isinstance(vals, dict):
            rows.append({"Model": name, "Class": cls,
                         "Precision": round(float(vals.get("precision", np.nan)), 4),
                         "Recall": round(float(vals.get("recall", np.nan)), 4),
                         "F1-Score": round(float(vals.get("f1-score", np.nan)), 4),
                         "Support": int(vals.get("support", 0))})
    return pd.DataFrame(rows)


def confusion_to_frame(matrix: np.ndarray, labels: list[str], model: str) -> pd.DataFrame:
    return (pd.DataFrame(matrix, index=labels, columns=labels)
            .rename_axis(index="Actual", columns="Predicted")
            .reset_index().melt(id_vars="Actual", var_name="Predicted",
                                value_name="Count").assign(Model=model))
