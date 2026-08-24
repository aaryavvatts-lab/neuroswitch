"""Which regions did the model rely on?

Importance is recomputed inside every cross-validation fold and rank-aggregated,
because a single fit's attribution map at this sample size is close to noise.
Only regions that rank highly *consistently* are reported as findings.

Whichever model actually wins on AUC provides the attributions -- if a linear
model on connectivity edges beats the graph network, then its coefficients are
the interpretability result, and they are considerably more stable than GNN
saliency.
"""
from __future__ import annotations

import argparse
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

from .experiments import build_bundle, node_meta
from .explain import (fdr, gnn_node_attributions, linear_edge_importance,
                      network_enrichment, stability_rank_aggregate)
from .models.baselines import ConnEdgeModel
from .models.gnn import GNNModel
from .run_analysis import _Enc, RESULTS
from .validate import assert_no_leakage, metrics


def node_scores_linear(model, n_nodes: int) -> np.ndarray:
    """Total absolute edge weight attached to each node."""
    mat = np.abs(linear_edge_importance(model, n_nodes))
    return mat.sum(axis=1)


def compute(cond: str = "LH", model_name: str = "auto", n_splits: int = 5,
            n_repeats: int = 4, seed: int = 0) -> dict:
    b = build_bundle(cond)
    nm = node_meta()
    n_nodes = b.ts[0].shape[1]

    if model_name == "auto":
        res = (json.loads((RESULTS / f"models_{cond}.json").read_text())
               if (RESULTS / f"models_{cond}.json").is_file() else {})
        scored = {k: (v.get("auc_mean") or 0) for k, v in res.get("models", {}).items()
                  if not k.startswith("NULL ") and "error" not in v}
        model_name = max(scored, key=scored.get) if scored else "tangent+logreg"

    def make():
        if model_name in ("GCN", "GAT", "GIN"):
            return GNNModel(conv=model_name.lower())
        kind, clf = (model_name.split("+") + ["logreg"])[:2]
        kind = {"tangent": "tangent", "partialcorr": "partial correlation",
                "correlation": "correlation"}.get(kind, "tangent")
        return ConnEdgeModel(kind, clf)

    fold_scores, fold_aucs = [], []
    for rep in range(n_repeats):
        cv = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=seed + rep)
        for tr, te in cv.split(np.zeros(len(b)), b.y, b.subs):
            assert_no_leakage(tr, te, b.subs)
            m = make().fit(tr, b)
            fold_aucs.append(metrics(b.y[te], m.predict_proba(te, b))["auc"])
            if isinstance(m, GNNModel):
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    att = gnn_node_attributions(m, tr, b)
                fold_scores.append(att.mean(axis=0))
            else:
                fold_scores.append(node_scores_linear(m, n_nodes))

    agg = stability_rank_aggregate(fold_scores)
    scores = agg["mean_score"]
    enr = network_enrichment(scores, nm["networks"], n_perm=10000)
    passed = fdr({k: v["p_value"] for k, v in enr.items()})
    for k in enr:
        enr[k]["fdr_pass"] = bool(passed.get(k, False))

    order = np.argsort(-scores)
    top = [{"id": int(i + 1), "name": nm["names"][i], "network": nm["networks"][i],
            "hemi": nm["hemis"][i], "score": float(scores[i]),
            "mean_rank": float(agg["mean_rank"][i]),
            "selection_frequency": float(agg["selection_frequency"][i])}
           for i in order[:30]]

    stable = [t for t in top if t["selection_frequency"] >= 0.8]
    return {
        "condition": cond, "model": model_name, "n_folds": int(agg["n_folds"]),
        "cv_auc_mean": float(np.nanmean(fold_aucs)),
        "n_nodes": int(n_nodes),
        "node_importance": [float(x) for x in scores],
        "selection_frequency": [float(x) for x in agg["selection_frequency"]],
        "top_nodes": top,
        "n_stable_nodes": len(stable),
        "stable_nodes": stable,
        "network_enrichment": enr,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", default="LH")
    ap.add_argument("--model", default="auto")
    ap.add_argument("--repeats", type=int, default=4)
    a = ap.parse_args()
    r = compute(a.condition, a.model, n_repeats=a.repeats)
    RESULTS.mkdir(exist_ok=True)
    p = RESULTS / f"importance_{a.condition}.json"
    p.write_text(json.dumps(r, indent=1, cls=_Enc))
    print(f"model={r['model']}  folds={r['n_folds']}  cv AUC={r['cv_auc_mean']:.3f}")
    print(f"stable nodes (selected in >=80% of folds): {r['n_stable_nodes']}")
    for t in r["top_nodes"][:10]:
        print(f"  {t['score']:9.4f}  freq={t['selection_frequency']:.2f}  "
              f"{t['hemi']:3s} {t['network']:12s} {t['name'][:44]}")
    print("-> ", p.name)


if __name__ == "__main__":
    main()
