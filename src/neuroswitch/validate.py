"""Cross-validation, permutation testing, and the leakage guarantees.

Every model implements ``fit(train_idx, bundle)`` / ``predict_proba(test_idx,
bundle)`` and receives raw *time series*, never precomputed connectivity.  Any
estimator that pools across subjects (tangent embedding, scalers, feature
selection) is therefore forced to be fit on training indices only.

Splits are grouped by subject, so runs or conditions belonging to one person
can never straddle the train/test boundary.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from sklearn.metrics import (average_precision_score, balanced_accuracy_score,
                             roc_auc_score)
from sklearn.model_selection import StratifiedGroupKFold


@dataclass
class Bundle:
    """Everything a model might need, indexed consistently by sample."""
    ts: list[np.ndarray]                       # cleaned parcel time series
    y: np.ndarray                              # 1 = patient
    subs: np.ndarray                           # subject id per sample
    tables: dict[str, np.ndarray] = field(default_factory=dict)   # motion, behaviour, ...
    node_meta: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.y)


class Model(Protocol):
    name: str
    def fit(self, idx: np.ndarray, b: Bundle) -> "Model": ...
    def predict_proba(self, idx: np.ndarray, b: Bundle) -> np.ndarray: ...


def metrics(y_true: np.ndarray, p: np.ndarray) -> dict[str, float]:
    out = {"n": int(len(y_true)), "n_pos": int(y_true.sum())}
    if len(np.unique(y_true)) < 2:
        return {**out, "auc": np.nan, "pr_auc": np.nan, "balanced_acc": np.nan,
                "sensitivity": np.nan, "specificity": np.nan}
    pred = (p >= 0.5).astype(int)
    tp = int(((pred == 1) & (y_true == 1)).sum()); fn = int(((pred == 0) & (y_true == 1)).sum())
    tn = int(((pred == 0) & (y_true == 0)).sum()); fp = int(((pred == 1) & (y_true == 0)).sum())
    return {**out,
            "auc": float(roc_auc_score(y_true, p)),
            "pr_auc": float(average_precision_score(y_true, p)),
            "balanced_acc": float(balanced_accuracy_score(y_true, pred)),
            "sensitivity": float(tp / (tp + fn)) if tp + fn else np.nan,
            "specificity": float(tn / (tn + fp)) if tn + fp else np.nan}


def _splits(y, groups, n_splits, seed):
    cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    return list(cv.split(np.zeros(len(y)), y, groups))


def assert_no_leakage(train_idx, test_idx, subs) -> None:
    overlap = set(subs[train_idx]) & set(subs[test_idx])
    if overlap:
        raise AssertionError(f"subject leakage across folds: {sorted(overlap)[:5]}")


def cross_validate(make_model, b: Bundle, n_splits: int = 5, n_repeats: int = 10,
                   seed: int = 0, collect_oof: bool = True) -> dict:
    """Repeated stratified group K-fold.  Returns per-repeat and pooled metrics."""
    per_repeat, oof_all = [], []
    for rep in range(n_repeats):
        p_oof = np.full(len(b), np.nan)
        for tr, te in _splits(b.y, b.subs, n_splits, seed + rep):
            assert_no_leakage(tr, te, b.subs)
            m = make_model().fit(tr, b)
            p_oof[te] = m.predict_proba(te, b)
        per_repeat.append(metrics(b.y, p_oof))
        if collect_oof:
            oof_all.append(p_oof)
    aucs = np.array([r["auc"] for r in per_repeat], dtype=float)
    agg = {k: float(np.nanmean([r[k] for r in per_repeat]))
           for k in per_repeat[0] if k not in ("n", "n_pos")}
    lo, hi = (np.nanpercentile(aucs, [2.5, 97.5]) if n_repeats > 1 else (np.nan, np.nan))
    return {"auc_mean": float(np.nanmean(aucs)), "auc_sd": float(np.nanstd(aucs)),
            "auc_ci": [float(lo), float(hi)], "n_repeats": n_repeats,
            "n_splits": n_splits, "aggregate": agg, "per_repeat": per_repeat,
            "oof": np.nanmean(oof_all, axis=0) if collect_oof else None}


def permutation_test(make_model, b: Bundle, n_perm: int = 1000, n_splits: int = 5,
                     seed: int = 0, observed: float | None = None) -> dict:
    """Shuffle labels *at the subject level* and rebuild the null distribution."""
    if observed is None:
        observed = cross_validate(make_model, b, n_splits, n_repeats=1,
                                  seed=seed, collect_oof=False)["auc_mean"]
    uniq = np.unique(b.subs)
    sub_y = np.array([b.y[b.subs == s][0] for s in uniq])
    rng = np.random.RandomState(seed)
    null = []
    for i in range(n_perm):
        perm = rng.permutation(sub_y)
        mapping = dict(zip(uniq, perm))
        y_perm = np.array([mapping[s] for s in b.subs])
        bp = Bundle(b.ts, y_perm, b.subs, b.tables, b.node_meta)
        null.append(cross_validate(make_model, bp, n_splits, n_repeats=1,
                                   seed=seed + 1000 + i, collect_oof=False)["auc_mean"])
    null = np.array(null, dtype=float)
    # +1 correction: an observed value can never yield p = 0
    p = float((np.sum(null >= observed) + 1) / (len(null) + 1))
    # A compact histogram travels to the site instead of every draw, so a
    # reader can see where the real score sits against chance.
    edges = np.linspace(0.0, 1.0, 41)
    counts, _ = np.histogram(null[np.isfinite(null)], bins=edges)
    return {"observed_auc": float(observed), "p_value": p, "n_perm": int(n_perm),
            "null_mean": float(np.nanmean(null)), "null_sd": float(np.nanstd(null)),
            "null_q95": float(np.nanpercentile(null, 95)),
            "null_hist": {"edges": [round(x, 4) for x in edges.tolist()],
                          "counts": [int(c) for c in counts.tolist()]},
            "null": null.tolist()}
