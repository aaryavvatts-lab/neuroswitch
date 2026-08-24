"""Cohort assembly: who is in, who is out, and why.

Exclusions are decided here, once, and every downstream analysis reads this
table -- so the CONSORT numbers on the website cannot drift from the numbers
the models actually saw.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from .preprocess import BIDS
from .run_subject import DERIV, available_runs

# Flagged by the dataset authors in participants.tsv; see README "Missing data".
AUTHOR_EXCLUDED = {"sub-1020", "sub-1026", "sub-1051",   # motion x task correlation
                   "sub-2011",                          # tablet use error
                   "sub-2019"}                           # high motion
# Patients who could not draw with the injured right hand.
NO_RIGHT_HAND = {"sub-1002", "sub-1019", "sub-1045"}

MAX_MEAN_FD = 0.30          # mm, per run
MAX_PCT_CENSORED = 30.0     # %
MIN_RUNS_PER_HAND = 2
MIN_REG_DICE = 0.85

BEHAV_LH = ["velSm_LH", "dirAcc_LH", "posAcc_LH", "spd_LH"]
BEHAV_RH = ["velSm_RH", "dirAcc_RH", "posAcc_RH", "spd_RH"]


def participants() -> pd.DataFrame:
    df = pd.read_csv(BIDS / "participants.tsv", sep="\t", na_values=["n/a", "NaN"])
    df["is_patient"] = df["isPatient"].astype(float).astype("Int64")
    return df


def run_qc() -> pd.DataFrame:
    """One row per preprocessed run, from the per-run QC JSONs."""
    rows = []
    for f in sorted(DERIV.glob("sub-*/*_qc.json")):
        if f.name.endswith("subject_qc.json") or f.name == "anat_qc.json":
            continue
        try:
            rows.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return pd.DataFrame(rows)


def usable_runs(qc: pd.DataFrame) -> pd.DataFrame:
    if qc.empty:
        return qc.assign(usable=[])
    ok = ((qc["mean_fd"] <= MAX_MEAN_FD)
          & (qc["pct_censored"] <= MAX_PCT_CENSORED)
          & (qc["reg_dice_mni_to_epi"] >= MIN_REG_DICE))
    return qc.assign(usable=ok)


def cohort(require_both_hands: bool = False) -> pd.DataFrame:
    """Subject-level table with labels, covariates, QC summaries and exclusions."""
    p = participants().set_index("participant_id")
    qc = usable_runs(run_qc())
    rows = []
    for sub, r in p.iterrows():
        d = {"sub": sub, "is_patient": int(r["is_patient"]) if pd.notna(r["is_patient"]) else np.nan,
             "age": r.get("age"), "sex": r.get("sex"),
             "DASH_ability": r.get("DASH_ability"),
             "monthsSinceInjury": r.get("monthsSinceInjury"),
             "edinburghCurrent": r.get("edinburghCurrent"),
             "edinburghPre": r.get("edinburghPre"),
             "author_exclusion": r.get("exclusion")}
        for c in BEHAV_LH + BEHAV_RH:
            d[c] = r.get(c)
        # handedness shift: positive = moved away from right-hand preference
        d["edinburgh_shift"] = (r.get("edinburghPre") - r.get("edinburghCurrent")
                                if pd.notna(r.get("edinburghPre")) and
                                   pd.notna(r.get("edinburghCurrent")) else np.nan)
        sq = qc[qc["sub"] == sub] if not qc.empty else qc
        for task in ("drawLH", "drawRH", "restingstate"):
            t = sq[sq["task"] == task] if not sq.empty else sq
            d[f"n_{task}"] = int(t["usable"].sum()) if not t.empty else 0
            d[f"fd_{task}"] = float(t.loc[t["usable"], "mean_fd"].mean()) if not t.empty and t["usable"].any() else np.nan
        d["n_raw_drawLH"] = len(available_runs(sub, "drawLH"))
        d["preprocessed"] = (DERIV / sub / "subject_qc.json").is_file()
        d["mean_fd"] = float(sq.loc[sq["usable"], "mean_fd"].mean()) if not sq.empty and sq["usable"].any() else np.nan
        d["max_fd"] = float(sq.loc[sq["usable"], "max_fd"].max()) if not sq.empty and sq["usable"].any() else np.nan
        rows.append(d)

    df = pd.DataFrame(rows)
    reasons = []
    for _, r in df.iterrows():
        why = []
        if r["sub"] in AUTHOR_EXCLUDED:
            why.append("author-flagged")
        if not r["preprocessed"]:
            why.append("not preprocessed")
        elif r["n_drawLH"] < MIN_RUNS_PER_HAND:
            why.append(f"only {r['n_drawLH']} usable drawLH runs")
        if require_both_hands and r["n_drawRH"] < MIN_RUNS_PER_HAND:
            why.append(f"only {r['n_drawRH']} usable drawRH runs")
        reasons.append("; ".join(why))
    df["exclude_reason"] = reasons
    df["included"] = df["exclude_reason"] == ""
    return df


def summary(df: pd.DataFrame) -> dict:
    inc = df[df["included"]]
    return {
        "n_total": int(len(df)),
        "n_included": int(len(inc)),
        "n_patients": int((inc["is_patient"] == 1).sum()),
        "n_controls": int((inc["is_patient"] == 0).sum()),
        "n_excluded": int((~df["included"]).sum()),
        "exclusion_counts": df.loc[~df["included"], "exclude_reason"]
                              .value_counts().to_dict(),
    }


if __name__ == "__main__":
    df = cohort()
    print(json.dumps(summary(df), indent=1))
    print(df[["sub", "is_patient", "preprocessed", "n_drawLH", "n_drawRH",
              "mean_fd", "included", "exclude_reason"]].head(20).to_string(index=False))
