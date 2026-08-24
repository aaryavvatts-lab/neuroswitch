"""The four control analyses that decide whether the headline claim survives.

The reel's design -- classify patient vs control from left-hand-drawing
connectivity -- can be right for the wrong reasons.  Each analysis here is a way
of being wrong, made explicit and tested.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import GroupKFold

from ..dataset import BEHAV_LH, cohort
from ..experiments import build_bundle, model_suite
from ..graphs import Connectivity, vectorize
from ..models.paired import (CrossConditionWrapper, DiffConnEdgeModel,
                             ResidualizedConnModel)
from ..validate import Bundle, cross_validate, permutation_test

RESULTS = Path(__file__).resolve().parents[3] / "results"


# ------------------------------------------------------------------ T1
def handflip(n_repeats: int = 10, n_perm: int = 500) -> dict:
    """Is the signature specific to the non-dominant hand, or just 'these brains'?

    Three questions:
      1. does a left-hand model transfer to right-hand data?
      2. does the within-subject LH-RH difference still classify?  (kills all
         fixed subject-level confounds)
      3. is the difference-graph result better than chance?
    """
    lh, rh = build_bundle("LH"), build_bundle("RH")
    common = [s for s in lh.subs if s in set(rh.subs)]
    if len(common) < 20:
        return {"error": f"only {len(common)} subjects have both hands"}

    li = np.array([list(lh.subs).index(s) for s in common])
    ri = np.array([list(rh.subs).index(s) for s in common])
    paired = Bundle(ts=[lh.ts[i] for i in li], y=lh.y[li], subs=lh.subs[li],
                    tables={k: v[li] for k, v in lh.tables.items()},
                    node_meta={**lh.node_meta, "ts_pair": [rh.ts[i] for i in ri]})

    out = {"n_subjects": len(common),
           "n_patients": int(paired.y.sum()),
           "n_controls": int((paired.y == 0).sum())}

    diff = cross_validate(lambda: DiffConnEdgeModel("tangent"), paired,
                          n_repeats=n_repeats)
    out["difference_graph"] = {k: diff[k] for k in
                               ("auc_mean", "auc_sd", "auc_ci", "aggregate")}
    out["difference_graph"]["permutation"] = permutation_test(
        lambda: DiffConnEdgeModel("tangent"), paired, n_perm=n_perm,
        observed=diff["auc_mean"])
    out["difference_graph"]["permutation"].pop("null", None)

    for cond, b in (("LH", lh), ("RH", rh)):
        r = cross_validate(lambda: __import__(
            "neuroswitch.models.baselines", fromlist=["ConnEdgeModel"]
        ).ConnEdgeModel("tangent", "logreg"), b, n_repeats=n_repeats)
        out[f"within_{cond}"] = {k: r[k] for k in ("auc_mean", "auc_sd", "auc_ci")}
    return out


# ------------------------------------------------------------------ T2
def behaviour(n_repeats: int = 10, n_perm: int = 500) -> dict:
    """Is it the brain, or is it that patients simply draw worse?

    If a handful of tablet-derived performance numbers classify as well as the
    connectome, the brain model may be an expensive performance detector.  The
    decisive test is whether connectivity still predicts once performance is
    regressed out, and within a performance-matched subsample.
    """
    from ..models.baselines import ConnEdgeModel, TableModel
    b = build_bundle("LH")
    out = {"n_subjects": len(b), "n_patients": int(b.y.sum())}

    brain = cross_validate(lambda: ConnEdgeModel("tangent", "logreg"), b, n_repeats=n_repeats)
    beh = cross_validate(lambda: TableModel("behaviour_lh"), b, n_repeats=n_repeats)
    resid = cross_validate(lambda: ResidualizedConnModel("behaviour_lh"), b,
                           n_repeats=n_repeats)
    out["brain_only"] = {k: brain[k] for k in ("auc_mean", "auc_sd", "auc_ci")}
    out["behaviour_only"] = {k: beh[k] for k in ("auc_mean", "auc_sd", "auc_ci")}
    out["brain_residualised_on_behaviour"] = {k: resid[k] for k in
                                              ("auc_mean", "auc_sd", "auc_ci")}
    out["brain_residualised_permutation"] = permutation_test(
        lambda: ResidualizedConnModel("behaviour_lh"), b, n_perm=n_perm,
        observed=resid["auc_mean"])
    out["brain_residualised_permutation"].pop("null", None)

    # performance-matched subsample: patients and controls paired on LH quality
    beh_x = b.tables["behaviour_lh"]
    score = np.nanmean((beh_x - np.nanmean(beh_x, 0)) / (np.nanstd(beh_x, 0) + 1e-9), axis=1)
    out["performance_gap"] = {
        "patient_mean_z": float(np.nanmean(score[b.y == 1])),
        "control_mean_z": float(np.nanmean(score[b.y == 0])),
    }
    keep = _match_on(score, b.y)
    out["matched_n"] = int(len(keep))
    if len(keep) >= 24:
        bm = Bundle([b.ts[i] for i in keep], b.y[keep], b.subs[keep],
                    {k: v[keep] for k, v in b.tables.items()}, b.node_meta)
        mm = cross_validate(lambda: ConnEdgeModel("tangent", "logreg"), bm,
                            n_splits=4, n_repeats=n_repeats)
        out["brain_performance_matched"] = {k: mm[k] for k in
                                            ("auc_mean", "auc_sd", "auc_ci")}
        out["matched_performance_gap"] = {
            "patient_mean_z": float(np.nanmean(score[keep][bm.y == 1])),
            "control_mean_z": float(np.nanmean(score[keep][bm.y == 0]))}
    return out


def _match_on(score: np.ndarray, y: np.ndarray, caliper: float = 0.5) -> np.ndarray:
    """Greedy 1:1 nearest-neighbour matching of controls to patients."""
    pat = np.flatnonzero((y == 1) & np.isfinite(score))
    ctl = list(np.flatnonzero((y == 0) & np.isfinite(score)))
    keep = []
    for p in pat:
        if not ctl:
            break
        d = [abs(score[p] - score[c]) for c in ctl]
        j = int(np.argmin(d))
        if d[j] <= caliper:
            keep += [p, ctl.pop(j)]
    return np.array(sorted(keep), dtype=int)


# ------------------------------------------------------------------ T3
def severity(n_perm: int = 2000) -> dict:
    """Within patients only: does the network signature scale with disability?

    A binary classifier can separate groups for many uninteresting reasons.  A
    graded relationship with DASH disability, time since injury, or the shift in
    hand preference is much harder to explain away.
    """
    b = build_bundle("LH")
    df = cohort().set_index("sub")
    pat = np.flatnonzero(b.y == 1)
    out = {"n_patients": int(len(pat))}
    if len(pat) < 12:
        return {**out, "error": "too few patients for a stable within-group model"}

    conn = Connectivity("tangent", n_nodes=b.ts[0].shape[1]).fit([b.ts[i] for i in pat])
    x = vectorize(conn.transform([b.ts[i] for i in pat]))
    subs = b.subs[pat]

    for target in ("DASH_ability", "monthsSinceInjury", "edinburgh_shift"):
        yv = df.loc[subs, target].to_numpy(dtype=float)
        ok = np.isfinite(yv)
        if ok.sum() < 12:
            out[target] = {"error": f"only {int(ok.sum())} patients have {target}"}
            continue
        pred = _loo_ridge(x[ok], yv[ok], subs[ok])
        rho, _ = spearmanr(yv[ok], pred)
        rng = np.random.RandomState(0)
        null = []
        for _ in range(n_perm):
            yp = rng.permutation(yv[ok])
            null.append(spearmanr(yp, _loo_ridge(x[ok], yp, subs[ok]))[0])
        null = np.array(null, dtype=float)
        p = float((np.sum(np.abs(null) >= abs(rho)) + 1) / (n_perm + 1))
        out[target] = {"n": int(ok.sum()), "spearman_rho": float(rho),
                       "p_value": p, "null_mean": float(np.nanmean(null))}
    return out


def _loo_ridge(x: np.ndarray, y: np.ndarray, groups: np.ndarray) -> np.ndarray:
    """Leave-one-subject-out ridge prediction."""
    pred = np.full(len(y), np.nan)
    cv = GroupKFold(n_splits=min(len(np.unique(groups)), 10))
    for tr, te in cv.split(x, y, groups):
        m = RidgeCV(alphas=np.logspace(-2, 4, 25)).fit(x[tr], y[tr])
        pred[te] = m.predict(x[te])
    return pred


# ------------------------------------------------------------------ T4
def rest_vs_task(n_repeats: int = 10) -> dict:
    """Task-driven recruitment, or a persistent trait?

    If the same classifier works on resting-state data, the reorganisation is
    not specific to drawing with the impaired-side hand.
    """
    from ..models.baselines import ConnEdgeModel
    out = {}
    for cond in ("LH", "REST"):
        try:
            b = build_bundle(cond)
        except Exception as exc:
            out[cond] = {"error": repr(exc)}
            continue
        if len(b) < 24:
            out[cond] = {"error": f"only {len(b)} subjects with {cond} data"}
            continue
        r = cross_validate(lambda: ConnEdgeModel("tangent", "logreg"), b,
                           n_repeats=n_repeats)
        out[cond] = {"n": len(b), "n_patients": int(b.y.sum()),
                     **{k: r[k] for k in ("auc_mean", "auc_sd", "auc_ci")}}
    return out


# ------------------------------------------------------------------ bonus
def difficulty(n_repeats: int = 10) -> dict:
    """Do patients show the 'hard block' configuration even on easy blocks?"""
    from ..models.baselines import ConnEdgeModel
    out = {}
    for cond in ("LHeasy", "LHhard"):
        try:
            b = build_bundle(cond, min_volumes=40)
        except Exception as exc:
            out[cond] = {"error": repr(exc)}
            continue
        if len(b) < 24:
            out[cond] = {"error": f"only {len(b)} subjects"}
            continue
        r = cross_validate(lambda: ConnEdgeModel("tangent", "logreg"), b,
                           n_repeats=n_repeats)
        out[cond] = {"n": len(b), **{k: r[k] for k in ("auc_mean", "auc_sd", "auc_ci")}}
    return out
