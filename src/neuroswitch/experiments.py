"""Assemble analysis bundles and run the model suite.

One place decides which subjects and which condition go into an experiment, so
every result on the website traces back to the same cohort definition.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .dataset import BEHAV_LH, BEHAV_RH, cohort
from .features import FEAT
from .run_subject import DERIV
from .validate import Bundle

ATLAS_DIR = DERIV / "atlas-schaefer200"


def node_meta() -> dict:
    meta = json.loads((ATLAS_DIR / "atlas.json").read_text())
    nodes = meta["nodes"]
    nets = [n["network"] for n in nodes]
    uniq = sorted(set(nets))
    onehot = np.zeros((len(nodes), len(uniq)), dtype=np.float32)
    for i, n in enumerate(nets):
        onehot[i, uniq.index(n)] = 1.0
    return {"nodes": nodes, "names": [n["name"] for n in nodes],
            "networks": nets, "hemis": [n["hemi"] for n in nodes],
            "network_names": uniq, "network_onehot": onehot,
            "n_nodes": meta["n_nodes"]}


def _feat_file(sub: str, cond: str) -> Path:
    return FEAT / f"{sub}_{cond}.npz"


def available(cond: str) -> set[str]:
    return {f.name.split("_")[0] for f in FEAT.glob(f"sub-*_{cond}.npz")}


def build_bundle(cond: str, df: pd.DataFrame | None = None,
                 min_volumes: int = 60) -> Bundle:
    """One sample per subject for the requested condition."""
    df = cohort() if df is None else df
    nm = node_meta()
    ts, y, subs, rows = [], [], [], []
    per_node = {k: [] for k in ("beta_draw", "beta_hard_minus_easy", "alff", "falff")}
    for _, r in df[df["included"]].iterrows():
        f = _feat_file(r["sub"], cond)
        if not f.is_file():
            continue
        with np.load(f) as z:
            if int(z["n_volumes"]) < min_volumes:
                continue
            ts.append(z["ts"])
            for k in per_node:
                per_node[k].append(z[k] if k in z.files else np.full(nm["n_nodes"], np.nan))
        y.append(int(r["is_patient"])); subs.append(r["sub"]); rows.append(r)

    meta = pd.DataFrame(rows)
    tables = {k: np.vstack(v) for k, v in per_node.items() if v}
    if not meta.empty:
        tables["motion"] = meta[["mean_fd", "max_fd"]].to_numpy(dtype=float)
        beh_cols = BEHAV_LH if cond.startswith("LH") else BEHAV_RH
        tables["behaviour"] = meta[beh_cols].to_numpy(dtype=float)
        tables["behaviour_lh"] = meta[BEHAV_LH].to_numpy(dtype=float)
        tables["demographics"] = pd.get_dummies(
            meta[["age", "sex"]], columns=["sex"], dummy_na=True).to_numpy(dtype=float)
    return Bundle(ts=ts, y=np.array(y), subs=np.array(subs),
                  tables=tables, node_meta=nm)


def model_suite(include_gnn: bool = True) -> dict:
    """The models reported side by side, nulls included."""
    from .models.baselines import ConnEdgeModel, GraphMetricModel, TableModel
    from .models.gnn import GNNModel
    suite = {
        "tangent+logreg": lambda: ConnEdgeModel("tangent", "logreg", C=1.0),
        "tangent+svm": lambda: ConnEdgeModel("tangent", "svm", C=1.0),
        "partialcorr+logreg": lambda: ConnEdgeModel("partial correlation", "logreg"),
        "correlation+svm": lambda: ConnEdgeModel("correlation", "svm"),
        "graph-metrics+gb": lambda: GraphMetricModel(),
        "NULL motion-only": lambda: TableModel("motion"),
        "NULL behaviour-only": lambda: TableModel("behaviour"),
        "NULL demographics-only": lambda: TableModel("demographics"),
    }
    if include_gnn:
        suite |= {
            "GCN": lambda: GNNModel(conv="gcn"),
            "GAT": lambda: GNNModel(conv="gat"),
            "GIN": lambda: GNNModel(conv="gin"),
        }
    return suite


def describe(b: Bundle) -> dict:
    return {"n_samples": len(b), "n_patients": int(b.y.sum()),
            "n_controls": int((b.y == 0).sum()),
            "n_nodes": int(b.ts[0].shape[1]) if b.ts else 0,
            "volumes_median": float(np.median([t.shape[0] for t in b.ts])) if b.ts else 0}
