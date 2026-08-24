"""Confound regression, task regressors, and per-parcel features.

Cleaning happens on the 241 parcel series rather than on ~150k voxels.  That is
not an approximation: residualisation by a fixed design matrix and band-pass
filtering are linear along time, parcel averaging is linear across space, and
linear operators on independent axes commute.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from nilearn.glm.first_level import make_first_level_design_matrix
from nilearn.signal import clean

from .preprocess import BIDS, DROP_VOLUMES, FD_SPIKE_MM, friston24

ROOT = Path(__file__).resolve().parents[2]
DERIV = ROOT / "derivatives"

HIGH_PASS = 0.008          # Hz
LOW_PASS = 0.10            # Hz -- the 30.5 s block cycle (0.033 Hz) sits inside
HRF_LAG_S = 4.0            # shift applied when selecting task-block volumes


def load_run(sub: str, task: str, run: int) -> dict:
    f = DERIV / sub / f"{sub}_task-{task}_run-{run}.npz"
    with np.load(f) as z:
        return {k: z[k] for k in z.files}


def frame_times(n_t: int, tr: float) -> np.ndarray:
    """Acquisition times of the *retained* volumes, in original scan time."""
    return (np.arange(n_t) + DROP_VOLUMES) * tr


def build_confounds(d: dict, n_t: int, add_spikes: bool = True) -> np.ndarray:
    """Friston-24 motion + aCompCor(WM,CSF) + FD/DVARS + spike regressors."""
    parts = [friston24(d["motion"][:n_t]),
             d["compcor_wm"][:n_t], d["compcor_csf"][:n_t],
             d["fd"][:n_t, None], d["dvars"][:n_t, None]]
    if add_spikes:
        idx = np.flatnonzero(d["fd"][:n_t] > FD_SPIKE_MM)
        if idx.size:
            sp = np.zeros((n_t, idx.size))
            sp[idx, np.arange(idx.size)] = 1.0
            parts.append(sp)
    conf = np.hstack(parts)
    conf = np.nan_to_num(conf, nan=0.0, posinf=0.0, neginf=0.0)
    keep = conf.std(axis=0) > 0                       # drop constant columns
    return conf[:, keep]


def clean_ts(ts: np.ndarray, confounds: np.ndarray, tr: float,
             low_pass: float | None = LOW_PASS,
             high_pass: float | None = HIGH_PASS) -> np.ndarray:
    """Detrend, regress confounds, band-pass, z-score. NaN parcels stay NaN."""
    good = ~np.isnan(ts).any(axis=0)
    out = np.full_like(ts, np.nan, dtype=np.float32)
    if good.sum() == 0:
        return out
    cleaned = clean(ts[:, good].astype(np.float64), detrend=True, standardize="zscore_sample",
                    confounds=confounds, t_r=tr, low_pass=low_pass, high_pass=high_pass,
                    ensure_finite=True)
    out[:, good] = cleaned.astype(np.float32)
    return out


def events_path(sub: str, task: str, run: int, variant: str = "") -> Path:
    return BIDS / sub / "func" / f"{sub}_task-{task}{variant}_run-{run}_events.tsv"


def load_events(sub: str, task: str, run: int, variant: str = "") -> pd.DataFrame:
    return pd.read_csv(events_path(sub, task, run, variant), sep="\t")


BASELINE_TRIAL_TYPES = ("rest",)


def design_matrix(sub: str, task: str, run: int, n_t: int, tr: float,
                  variant: str = "", drop_baseline: bool = True) -> pd.DataFrame:
    """HRF-convolved task design on the retained volumes.

    Rest is left as the *implicit* baseline rather than given its own column.
    Every volume in these runs is either drawing or rest, so modelling both
    alongside an intercept makes the design near-collinear (draw + rest is
    almost exactly the constant) and the individual betas become unstable and
    can flip sign.  Dropping rest makes each remaining beta a clean
    condition-versus-rest contrast.
    """
    ev = load_events(sub, task, run, variant)
    if drop_baseline:
        ev = ev[~ev["trial_type"].astype(str).isin(BASELINE_TRIAL_TYPES)]
    return make_first_level_design_matrix(
        frame_times(n_t, tr), events=ev, hrf_model="spm",
        drift_model=None, high_pass=None)


def block_mask(sub: str, task: str, run: int, n_t: int, tr: float,
               conditions=("draw",), variant: str = "",
               lag_s: float = HRF_LAG_S) -> np.ndarray:
    """Boolean mask of volumes inside the requested blocks, shifted for the HRF."""
    ev = load_events(sub, task, run, variant)
    ft = frame_times(n_t, tr) - lag_s
    m = np.zeros(n_t, dtype=bool)
    for _, row in ev.iterrows():
        if str(row["trial_type"]) in conditions:
            m |= (ft >= row["onset"]) & (ft < row["onset"] + row["duration"])
    return m


def glm_betas(ts_clean: np.ndarray, design: pd.DataFrame) -> dict[str, np.ndarray]:
    """OLS betas per parcel for every column of the design matrix."""
    x = design.to_numpy(dtype=np.float64)
    good = ~np.isnan(ts_clean).any(axis=0)
    beta = np.full((x.shape[1], ts_clean.shape[1]), np.nan)
    if good.sum():
        b, *_ = np.linalg.lstsq(x, ts_clean[:, good].astype(np.float64), rcond=None)
        beta[:, good] = b
    return {name: beta[i] for i, name in enumerate(design.columns)}


def alff(ts: np.ndarray, tr: float, band=(0.01, 0.08)) -> tuple[np.ndarray, np.ndarray]:
    """Amplitude of low-frequency fluctuation, and its fractional form."""
    good = ~np.isnan(ts).any(axis=0)
    n_t = ts.shape[0]
    a = np.full(ts.shape[1], np.nan)
    fa = np.full(ts.shape[1], np.nan)
    if good.sum() == 0:
        return a, fa
    x = ts[:, good] - ts[:, good].mean(0)
    freqs = np.fft.rfftfreq(n_t, d=tr)
    amp = np.abs(np.fft.rfft(x, axis=0))
    in_band = (freqs >= band[0]) & (freqs <= band[1])
    total = amp[1:].sum(0)
    total[total == 0] = np.nan
    a[good] = amp[in_band].sum(0)
    fa[good] = amp[in_band].sum(0) / total
    return a, fa
