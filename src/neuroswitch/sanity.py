"""The pipeline's proof of life.

Moving one hand drives the opposite hemisphere.  If that does not appear, then
registration, parcel labelling, hemisphere assignment or event timing is wrong,
and everything downstream is noise.

The test is the within-subject hand x hemisphere *interaction*: for each person,
(left-hand drawing - right-hand drawing), which should be positive in right
sensorimotor cortex and negative in left.  Two earlier framings were rejected
because they are far less sensitive:

  * averaging the 34 sensorimotor parcels dilutes a hand-specific effect with
    auditory, face and trunk representations that the task barely engages;
  * comparing conditions *between* subjects re-introduces every between-subject
    difference the paired contrast cancels.
"""
from __future__ import annotations

import glob
import json
import re
import warnings
from pathlib import Path

import numpy as np

from . import signals as sg
from .experiments import node_meta
from .run_subject import DERIV

TR = 0.662
ROOT = Path(__file__).resolve().parents[2]


def _runs_on_disk(sub: str, task: str) -> list[int]:
    return sorted(int(re.search(r"run-(\d+)", f).group(1))
                  for f in glob.glob(str(DERIV / sub / f"{sub}_task-{task}_run-*.npz")))


def mean_draw_beta(sub: str, task: str) -> np.ndarray | None:
    """Average draw>rest beta across a subject's runs of one task."""
    out = []
    for run in _runs_on_disk(sub, task):
        d = sg.load_run(sub, task, run)
        n_t = d["ts"].shape[0]
        clean = sg.clean_ts(d["ts"], sg.build_confounds(d, n_t), TR, low_pass=None)
        out.append(sg.glm_betas(clean, sg.design_matrix(sub, task, run, n_t, TR))["draw"])
    if not out:
        return None
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(out, axis=0)


def lateralisation(subs: list[str] | None = None) -> dict:
    nm = node_meta()
    nets = np.array([str(x) for x in nm["networks"]])
    hemis = np.array([str(x) for x in nm["hemis"]])
    names = nm["names"]
    som = np.char.startswith(nets, "SomMot")
    lh = np.flatnonzero(som & (hemis == "LH"))
    rh = np.flatnonzero(som & (hemis == "RH"))

    subs = subs or sorted({p.parent.name for p in DERIV.glob("sub-*/*_task-draw*.npz")})
    per_sub, contrasts = [], []
    for sub in subs:
        bl, br = mean_draw_beta(sub, "drawLH"), mean_draw_beta(sub, "drawRH")
        if bl is None or br is None:
            continue
        li = bl - br                      # + = more active when drawing left-handed
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            L, R = float(np.nanmean(li[lh])), float(np.nanmean(li[rh]))
        per_sub.append({"sub": sub, "left_sensorimotor": L, "right_sensorimotor": R,
                        "interaction": R - L, "correct": bool(R > L)})
        contrasts.append(li)

    out = {"n_sensorimotor_left": int(len(lh)), "n_sensorimotor_right": int(len(rh)),
           "n_subjects": len(per_sub), "per_subject": per_sub, "conditions": []}
    if not per_sub:
        out["all_pass"] = False
        return out

    inter = np.array([p["interaction"] for p in per_sub])
    n_ok = int(sum(p["correct"] for p in per_sub))
    out["interaction_mean"] = float(inter.mean())
    out["interaction_sd"] = float(inter.std())
    out["subjects_correct"] = n_ok
    out["pct_subjects_correct"] = round(100.0 * n_ok / len(per_sub), 1)
    if len(inter) > 1:
        from scipy.stats import wilcoxon
        try:
            out["wilcoxon_p"] = float(wilcoxon(inter, alternative="greater").pvalue)
        except ValueError:
            out["wilcoxon_p"] = None

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        grand = np.nanmean(contrasts, axis=0)
    ok = np.isfinite(grand)
    idx = np.flatnonzero(ok)
    order = idx[np.argsort(-grand[idx])]
    out["top_left_hand"] = [
        {"name": names[i], "network": nets[i], "hemi": hemis[i],
         "value": float(grand[i])} for i in order[:10]]
    out["top_right_hand"] = [
        {"name": names[i], "network": nets[i], "hemi": hemis[i],
         "value": float(grand[i])} for i in order[::-1][:10]]
    top_rh = sum(1 for r in out["top_left_hand"] if r["hemi"] == "RH")
    top_lh = sum(1 for r in out["top_right_hand"] if r["hemi"] == "LH")
    out["top10_left_hand_in_right_hemisphere"] = top_rh
    out["top10_right_hand_in_left_hemisphere"] = top_lh

    # rendered by the site
    out["conditions"] = [
        {"label": "Left-hand drawing", "expected_side": "right",
         "lh_mean": float(np.mean([p["left_sensorimotor"] for p in per_sub])),
         "rh_mean": float(np.mean([p["right_sensorimotor"] for p in per_sub])),
         "verdict": ""},
    ]
    c = out["conditions"][0]
    c["verdict"] = "yes" if c["rh_mean"] > c["lh_mean"] else "NO — pipeline suspect"
    out["all_pass"] = bool(out["interaction_mean"] > 0 and top_rh >= 6)
    return out


if __name__ == "__main__":
    r = lateralisation()
    print(f"subjects with both hands: {r['n_subjects']}")
    if r["n_subjects"]:
        print(f"mean hand x hemisphere interaction: {r['interaction_mean']:+.3f} "
              f"({r['subjects_correct']}/{r['n_subjects']} subjects correct)")
        print(f"of the 10 parcels most left-hand-dominant, "
              f"{r['top10_left_hand_in_right_hemisphere']}/10 are right hemisphere")
        print(f"of the 10 parcels most right-hand-dominant, "
              f"{r['top10_right_hand_in_left_hemisphere']}/10 are left hemisphere")
    print("ALL PASS:", r["all_pass"])
    p = ROOT / "results" / "sanity_lateralisation.json"
    p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(r, indent=1))
    print("->", p.relative_to(ROOT))
