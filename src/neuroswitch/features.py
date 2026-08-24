"""Per-subject, per-condition feature store.

We save cleaned *time series*, not connectivity matrices.  Correlation and
partial correlation are computed per subject and would be safe to precompute,
but tangent-space embedding estimates a group mean -- fitting it on all
subjects and then cross-validating would leak test data into training.  Keeping
time series here forces every connectivity estimator to be fit inside the CV
loop, where it belongs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from . import signals as sg
from .run_subject import DERIV, available_runs

FEAT = DERIV / "features"
TR = 0.662

# condition -> (task, events variant, trial types kept, whether it is a task block)
CONDITIONS = {
    "LH":      ("drawLH", "", ("draw",), True),
    "RH":      ("drawRH", "", ("draw",), True),
    "LHeasy":  ("drawLH", "easyhard", ("draw-Easy",), True),
    "LHhard":  ("drawLH", "easyhard", ("draw-Hard",), True),
    "RHeasy":  ("drawRH", "easyhard", ("draw-Easy",), True),
    "RHhard":  ("drawRH", "easyhard", ("draw-Hard",), True),
    "REST":    ("restingstate", "", None, False),
}


def _usable(sub: str, task: str) -> list[int]:
    runs = []
    for r in available_runs(sub, task):
        f = DERIV / sub / f"{sub}_task-{task}_run-{r}_qc.json"
        if not f.is_file():
            continue
        q = json.loads(f.read_text())
        from .dataset import MAX_MEAN_FD, MAX_PCT_CENSORED, MIN_REG_DICE
        if (q["mean_fd"] <= MAX_MEAN_FD and q["pct_censored"] <= MAX_PCT_CENSORED
                and q["reg_dice_mni_to_epi"] >= MIN_REG_DICE):
            runs.append(r)
    return runs


def build_condition(sub: str, cond: str) -> dict | None:
    """Clean each run, keep the requested volumes, concatenate across runs."""
    task, variant, trial_types, is_task = CONDITIONS[cond]
    runs = _usable(sub, task)
    if not runs:
        return None

    segments, betas_draw, betas_hard, alffs, falffs, kept, censored = [], [], [], [], [], 0, 0
    for run in runs:
        f = DERIV / sub / f"{sub}_task-{task}_run-{run}.npz"
        if not f.is_file():
            continue
        d = sg.load_run(sub, task, run)
        ts = d["ts"]
        n_t = ts.shape[0]
        conf = sg.build_confounds(d, n_t)

        # connectivity band-pass for the graph; wider band for task betas
        clean_bp = sg.clean_ts(ts, conf, TR)
        keep = np.ones(n_t, dtype=bool) if not is_task else \
            sg.block_mask(sub, task, run, n_t, TR, conditions=trial_types, variant=variant)
        # drop high-motion frames
        keep &= d["fd"][:n_t] <= 0.5
        censored += int((d["fd"][:n_t] > 0.5).sum())
        if keep.sum() < 20:
            continue
        seg = clean_bp[keep]
        segments.append((seg - np.nanmean(seg, 0)) / (np.nanstd(seg, 0) + 1e-8))
        kept += int(keep.sum())

        if is_task and variant == "":
            clean_task = sg.clean_ts(ts, conf, TR, low_pass=None)
            dm = sg.design_matrix(sub, task, run, n_t, TR)
            b = sg.glm_betas(clean_task, dm)
            if "draw" in b:
                betas_draw.append(b["draw"])
            dmh = sg.design_matrix(sub, task, run, n_t, TR, variant="easyhard")
            bh = sg.glm_betas(clean_task, dmh)
            if "draw-Hard" in bh and "draw-Easy" in bh:
                betas_hard.append(bh["draw-Hard"] - bh["draw-Easy"])
        a, fa = sg.alff(clean_bp, TR)
        alffs.append(a); falffs.append(fa)

    if not segments:
        return None
    cat = np.vstack(segments).astype(np.float32)
    out = {"ts": cat, "n_runs": len(segments), "n_volumes": kept,
           "n_censored": censored, "runs": np.array(runs)}
    out["alff"] = np.nanmean(alffs, 0) if alffs else np.full(cat.shape[1], np.nan)
    out["falff"] = np.nanmean(falffs, 0) if falffs else np.full(cat.shape[1], np.nan)
    out["beta_draw"] = np.nanmean(betas_draw, 0) if betas_draw else np.full(cat.shape[1], np.nan)
    out["beta_hard_minus_easy"] = (np.nanmean(betas_hard, 0) if betas_hard
                                   else np.full(cat.shape[1], np.nan))
    return out


def build_subject(sub: str, conditions=tuple(CONDITIONS)) -> dict:
    FEAT.mkdir(parents=True, exist_ok=True)
    made = {}
    for cond in conditions:
        try:
            r = build_condition(sub, cond)
        except FileNotFoundError:
            r = None
        if r is None:
            made[cond] = None
            continue
        np.savez_compressed(FEAT / f"{sub}_{cond}.npz", **r)
        made[cond] = {"n_volumes": int(r["n_volumes"]), "n_runs": int(r["n_runs"])}
    return made


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    a = ap.parse_args()
    for sub in a.subjects:
        m = build_subject(sub)
        got = {k: v["n_volumes"] for k, v in m.items() if v}
        print(f"{sub}: {got}", flush=True)


if __name__ == "__main__":
    main()
