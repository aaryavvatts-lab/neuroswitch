"""Run the same data through many defensible analysis pipelines.

A single result hides how much it depended on choices nobody reports: which
atlas, which connectivity measure, which confounds, which model. Those choices
are all defensible on their own, and together they give a researcher a lot of
room to land on whichever answer they like.

This runs the whole grid and keeps every result, so the spread is visible
rather than hidden. It is the same idea as a specification curve.

Confound handling is redone here from the run-level files rather than reusing
the feature store, because the confound set is itself one of the choices.
"""
from __future__ import annotations

import argparse
import itertools
import json
import time
import warnings
from pathlib import Path

import numpy as np

from . import signals as sg
from .dataset import cohort
from .preprocess import friston24
from .run_subject import DERIV, derivative_runs
from .validate import Bundle, cross_validate

RESULTS = Path(__file__).resolve().parents[2] / "results"
TR = 0.662

# ---- the choices -----------------------------------------------------------
CONFOUND_SETS = {
    "motion6": "six head movement numbers only",
    "friston24": "24 movement terms",
    "friston24+compcor": "24 movement terms plus white matter and fluid components",
    "full": "everything, including spikes, framewise displacement and DVARS",
}
CONNECTIVITY = {
    "correlation": "plain correlation",
    "partial correlation": "partial correlation",
    "tangent": "tangent space",
}
BANDS = {
    "0.008-0.10": (0.008, 0.10),
    "0.01-0.08": (0.01, 0.08),
    "none": (None, None),
}
MODELS = {
    "logreg": "linear classifier",
    "svm": "support vector machine",
    "gb": "gradient boosting on network measures",
    "gcn": "graph neural network",
}
CONDITIONS = {
    "LH": "left hand drawing",
    "RH": "right hand drawing",
    "LH-RH": "left hand minus right hand",
}


def _confounds(d: dict, n_t: int, kind: str) -> np.ndarray | None:
    m = d["motion"][:n_t]
    if kind == "motion6":
        c = m
    elif kind == "friston24":
        c = friston24(m)
    elif kind == "friston24+compcor":
        c = np.hstack([friston24(m), d["compcor_wm"][:n_t], d["compcor_csf"][:n_t]])
    else:
        return sg.build_confounds(d, n_t)
    c = np.nan_to_num(c, nan=0.0, posinf=0.0, neginf=0.0)
    return c[:, c.std(axis=0) > 0]


def series(sub: str, task: str, confound: str, band: str,
           censor: bool = True) -> np.ndarray | None:
    """Cleaned, task-block-only signals for one person under one recipe."""
    lo, hi = BANDS[band]
    segs = []
    for run in derivative_runs(sub, task):
        f = DERIV / sub / f"{sub}_task-{task}_run-{run}.npz"
        if not f.is_file():
            continue
        d = sg.load_run(sub, task, run)
        n_t = d["ts"].shape[0]
        clean = sg.clean_ts(d["ts"], _confounds(d, n_t, confound), TR,
                            low_pass=hi, high_pass=lo)
        keep = sg.block_mask(sub, task, run, n_t, TR, conditions=("draw",))
        if censor:
            keep &= d["fd"][:n_t] <= 0.5
        if keep.sum() < 20:
            continue
        seg = clean[keep]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            segs.append((seg - np.nanmean(seg, 0)) / (np.nanstd(seg, 0) + 1e-8))
    return np.vstack(segs).astype(np.float32) if segs else None


def build(condition: str, confound: str, band: str, df) -> Bundle | None:
    inc = df[df["included"]]
    ts, pair, y, subs, rows = [], [], [], [], []
    for _, r in inc.iterrows():
        sub = r["sub"]
        if condition == "LH-RH":
            a = series(sub, "drawLH", confound, band)
            c = series(sub, "drawRH", confound, band)
            if a is None or c is None:
                continue
            pair.append(c)
        else:
            a = series(sub, "drawLH" if condition == "LH" else "drawRH",
                       confound, band)
            if a is None:
                continue
        ts.append(a); y.append(int(r["is_patient"])); subs.append(sub); rows.append(r)
    if len(ts) < 16 or len(set(y)) < 2:
        return None
    import pandas as pd
    meta = pd.DataFrame(rows)
    b = Bundle(ts=ts, y=np.array(y), subs=np.array(subs),
               tables={"motion": meta[["mean_fd", "max_fd"]].to_numpy(dtype=float)},
               node_meta={"ts_pair": pair} if pair else {})
    return b


def make_model(model: str, conn: str, density: float):
    from .models.baselines import ConnEdgeModel, GraphMetricModel
    from .models.gnn import GNNModel
    from .models.paired import DiffConnEdgeModel
    if model == "logreg":
        return lambda: ConnEdgeModel(conn, "logreg")
    if model == "svm":
        return lambda: ConnEdgeModel(conn, "svm")
    if model == "gb":
        return lambda: GraphMetricModel(kind=conn, density=density)
    return lambda: GNNModel(conv="gcn", kind=conn, density=density,
                            epochs=120, patience=20)


def run(n_repeats: int = 3, include_gnn: bool = True,
        conditions=tuple(CONDITIONS)) -> dict:
    df = cohort()
    specs, cache = [], {}
    grid = list(itertools.product(conditions, CONFOUND_SETS, BANDS,
                                 CONNECTIVITY, MODELS))
    t0 = time.time()
    for i, (cond, conf, band, conn, model) in enumerate(grid):
        if model == "gcn" and not include_gnn:
            continue
        # the graph network and network measures need a threshold; the linear
        # models use every edge, so a density here would mean nothing
        density = 0.10
        key = (cond, conf, band)
        if key not in cache:
            cache[key] = build(cond, conf, band, df)
        b = cache[key]
        if b is None:
            continue
        if cond == "LH-RH" and model in ("gb", "gcn"):
            continue                      # those wrappers do not take a pair
        try:
            if cond == "LH-RH":
                from .models.paired import DiffConnEdgeModel
                make = (lambda c=conn: DiffConnEdgeModel(c))
            else:
                make = make_model(model, conn, density)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                r = cross_validate(make, b, n_splits=5, n_repeats=n_repeats,
                                   collect_oof=False)
            specs.append({
                "condition": cond, "confounds": conf, "band": band,
                "connectivity": conn, "model": model,
                "auc": round(float(r["auc_mean"]), 4),
                "auc_sd": round(float(r["auc_sd"]), 4),
                "n": len(b), "n_patients": int(b.y.sum()),
            })
            print(f"  [{i+1}/{len(grid)}] {cond:6s} {conf:18s} {band:10s} "
                  f"{conn:20s} {model:7s} AUC={r['auc_mean']:.3f}", flush=True)
        except Exception as exc:
            print(f"  [{i+1}/{len(grid)}] failed: {exc!r}", flush=True)
    aucs = np.array([s["auc"] for s in specs], dtype=float)
    return {
        "n_specifications": len(specs),
        "seconds": round(time.time() - t0, 1),
        "auc_median": float(np.median(aucs)) if len(aucs) else None,
        "auc_min": float(aucs.min()) if len(aucs) else None,
        "auc_max": float(aucs.max()) if len(aucs) else None,
        "frac_above_chance": float((aucs > 0.5).mean()) if len(aucs) else None,
        "choices": {"conditions": CONDITIONS, "confounds": CONFOUND_SETS,
                    "band": {k: k for k in BANDS}, "connectivity": CONNECTIVITY,
                    "models": MODELS},
        "specifications": specs,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--no-gnn", action="store_true")
    a = ap.parse_args()
    r = run(n_repeats=a.repeats, include_gnn=not a.no_gnn)
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "multiverse.json").write_text(json.dumps(r, indent=1))
    print(f"\n{r['n_specifications']} pipelines in {r['seconds']}s")
    if r["auc_median"]:
        print(f"AUC ranged {r['auc_min']:.3f} to {r['auc_max']:.3f}, "
              f"middle {r['auc_median']:.3f}")


if __name__ == "__main__":
    main()
