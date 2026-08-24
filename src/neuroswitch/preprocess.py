"""Minimal, pure-Python fMRI preprocessing for ds008162.

No FSL / FreeSurfer / AFNI / Docker.  Registration and motion correction come
from ANTs via ``antspyx``; everything else is numpy/nibabel/nilearn.

Design note -- the expensive thing in a conventional pipeline is resampling a
488-volume 4-D series into template space.  We never do that.  Instead the
*atlas* is pulled into each run's native EPI grid through the composed
transform chain MNI -> T1 -> EPI, and parcel means are read straight off the
motion-corrected native-space data.

That is exact rather than approximate for our purposes: confound regression and
band-pass filtering are linear operators acting along time, and parcel
averaging is a linear operator acting across space, so the two commute.
Averaging first and cleaning the 241 parcel series is algebraically identical
to cleaning ~150k voxels and then averaging -- for a fraction of the cost.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from types import SimpleNamespace
from pathlib import Path

import ants
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
BIDS = Path("/Users/aaryav-sharma/Right Hand NeuralNetwork Insta Project")

DROP_VOLUMES = 10          # ~6.6 s of T1 equilibration, inside the opening rest block
FD_SPIKE_MM = 0.5          # censoring threshold
N_COMPCOR = 5              # components per tissue compartment
ANAT_REG_MM = 2.0          # T1 registration resolution (see prep_anat)


# --------------------------------------------------------------------------
# small numeric helpers
# --------------------------------------------------------------------------
def slice_time_correct(arr: np.ndarray, slice_times, tr: float,
                       ref_time: float = 0.0, pad: int | None = None) -> np.ndarray:
    """Shift every slice to a common acquisition time by Fourier phase shift.

    Slice ``z`` is sampled at ``k*TR + t_z``; we want it at ``k*TR + ref``.
    The corrected series is the original delayed by ``d = (t_z - ref)/TR``
    samples, which in the frequency domain is a multiply by exp(-2*pi*i*f*d).

    A discrete Fourier shift is circular, so a series that is not periodic over
    the acquisition window wraps its end onto its start.  We reflect-pad before
    transforming and crop afterwards, which suppresses that by ~2 orders of
    magnitude at the run edges.
    """
    arr = np.asarray(arr, dtype=np.float32)
    n_t = arr.shape[-1]
    slice_times = np.asarray(slice_times, dtype=float)
    if pad is None:
        pad = int(min(n_t // 4, 64))
    n_p = n_t + 2 * pad
    freqs = np.fft.fftfreq(n_p)                      # cycles per sample
    out = arr.copy()
    for z, t_z in enumerate(slice_times):
        d = (t_z - ref_time) / tr
        if abs(d) < 1e-9:
            continue
        sl = arr[:, :, z, :]
        if pad:
            sl = np.concatenate([sl[..., pad:0:-1][..., -pad:], sl,
                                 sl[..., -2:-pad - 2:-1]], axis=-1)
        spec = np.fft.fft(sl, axis=-1)
        spec *= np.exp(-2j * np.pi * freqs * d)
        shifted = np.real(np.fft.ifft(spec, axis=-1))
        out[:, :, z, :] = shifted[..., pad:pad + n_t] if pad else shifted
    return out


def rigid_params_from_mat(path: str) -> np.ndarray:
    """ANTs .mat -> [tx, ty, tz, rx, ry, rz] (mm, radians)."""
    tx = ants.read_transform(path)
    p = np.asarray(tx.parameters, dtype=float)
    rot, trans = p[:9].reshape(3, 3), p[9:12]
    # ZYX Euler decomposition
    sy = float(np.sqrt(rot[0, 0] ** 2 + rot[1, 0] ** 2))
    if sy > 1e-6:
        rx = np.arctan2(rot[2, 1], rot[2, 2])
        ry = np.arctan2(-rot[2, 0], sy)
        rz = np.arctan2(rot[1, 0], rot[0, 0])
    else:
        rx, ry, rz = np.arctan2(-rot[1, 2], rot[1, 1]), np.arctan2(-rot[2, 0], sy), 0.0
    return np.array([*trans, rx, ry, rz])


def friston24(motion: np.ndarray) -> np.ndarray:
    """6 params -> 24 regressors: params, derivatives, and both squared."""
    d = np.vstack([np.zeros((1, motion.shape[1])), np.diff(motion, axis=0)])
    return np.hstack([motion, d, motion ** 2, d ** 2])


def dvars(data4d: np.ndarray, mask3d: np.ndarray) -> np.ndarray:
    """RMS of the temporal derivative inside the brain, scaled to units of %."""
    ts = data4d[mask3d]                                   # (n_vox, T)
    med = np.median(ts, axis=1, keepdims=True)
    med[med == 0] = 1.0
    ts = 100.0 * ts / med
    dv = np.sqrt((np.diff(ts, axis=1) ** 2).mean(axis=0))
    return np.concatenate([[0.0], dv])


def compcor(data4d: np.ndarray, mask3d: np.ndarray, n_comp: int = N_COMPCOR) -> np.ndarray:
    """Top principal components of a noise compartment (aCompCor)."""
    ts = data4d[mask3d].astype(np.float64)                # (n_vox, T)
    if ts.shape[0] < n_comp * 2:
        return np.zeros((data4d.shape[-1], n_comp))
    ts = ts - ts.mean(axis=1, keepdims=True)
    sd = ts.std(axis=1, keepdims=True)
    keep = (sd > 0).ravel()
    ts, sd = ts[keep], sd[keep]
    if ts.shape[0] < n_comp * 2:
        return np.zeros((data4d.shape[-1], n_comp))
    ts /= sd
    # economy SVD over time
    _, _, vt = np.linalg.svd(ts, full_matrices=False)
    return vt[:n_comp].T                                  # (T, n_comp)


def dice(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.astype(bool), b.astype(bool)
    denom = a.sum() + b.sum()
    return float(2.0 * (a & b).sum() / denom) if denom else 0.0



def _tmp_root() -> str:
    """Temp directory we control, so ANTs scratch is never scattered into
    /var/folders where we cannot monitor or clean it."""
    root = os.environ.get("NEUROSWITCH_TMP") or os.environ.get("TMPDIR") or tempfile.gettempdir()
    Path(root).mkdir(parents=True, exist_ok=True)
    return root


def _read_motion(params) -> tuple[np.ndarray, int]:
    """Decode per-volume transforms; carry forward on failure and count them."""
    rows, n_bad, last = [], 0, np.zeros(6)
    for p in params:
        path = p[0] if isinstance(p, (list, tuple)) else p
        try:
            last = rigid_params_from_mat(path)
        except Exception:
            n_bad += 1
        rows.append(last)
    return np.vstack(rows), n_bad


# --------------------------------------------------------------------------
# anatomical stage
# --------------------------------------------------------------------------
@dataclass
class AnatResult:
    t1_brain: "ants.ANTsImage"
    brain_mask: "ants.ANTsImage"
    wm_mask: "ants.ANTsImage"
    csf_mask: "ants.ANTsImage"
    mni_to_t1: list = field(default_factory=list)
    qc: dict = field(default_factory=dict)


def _template():
    import templateflow.api as tf
    head = ants.image_read(str(tf.get("MNI152NLin6Asym", resolution=2, suffix="T1w",
                                      extension=".nii.gz", desc=None)))
    mask = ants.image_read(str(tf.get("MNI152NLin6Asym", resolution=2, suffix="mask",
                                      extension=".nii.gz", desc="brain")))
    return head, mask


def prep_anat(sub: str, workdir: Path) -> AnatResult:
    """Bias-correct, brain-extract via template mask, and segment tissue."""
    t1_path = BIDS / sub / "anat" / f"{sub}_T1w.nii.gz"
    t1 = ants.image_read(str(t1_path))
    t1n4 = ants.n4_bias_field_correction(t1)
    # Register at 2 mm, not the native ~1 mm.  The EPI is 3 mm and the atlas is
    # 2 mm, so finer deformation fields add no recoverable precision -- but they
    # cost ~8x the time and produce 121 MB warp files per registration, which is
    # what exhausted the disk on the first attempt.
    if min(t1n4.spacing) < ANAT_REG_MM - 1e-3:
        t1n4 = ants.resample_image(t1n4, (ANAT_REG_MM,) * 3, use_voxels=False, interp_type=4)

    head, tmask = _template()
    mni_brain = head * tmask

    # whole-head registration is enough to transfer a brain mask
    r1 = ants.registration(fixed=t1n4, moving=head, type_of_transform="SyN")
    bmask = ants.apply_transforms(fixed=t1n4, moving=tmask,
                                  transformlist=r1["fwdtransforms"],
                                  interpolator="nearestNeighbor")
    bmask = ants.threshold_image(bmask, 0.5, 1e9)
    bmask = ants.iMath(bmask, "MD", 1)                      # slight dilation
    t1_brain = t1n4 * bmask

    # refine on brain-extracted images -- this chain is what the atlas rides on
    r2 = ants.registration(fixed=t1_brain, moving=mni_brain, type_of_transform="SyN")

    # subject-specific tissue segmentation (no template priors)
    seg = ants.atropos(a=t1_brain, x=bmask, i="kmeans[3]", m="[0.2,1x1x1]", c="[3,0]")
    probs = seg["probabilityimages"]                        # ordered CSF, GM, WM
    csf = ants.threshold_image(probs[0], 0.95, 1e9)
    wm = ants.threshold_image(probs[2], 0.95, 1e9)
    csf = ants.iMath(csf, "ME", 1)                          # erode away partial volume
    wm = ants.iMath(wm, "ME", 2)

    qc = {
        "brain_mask_voxels": int(bmask.numpy().sum()),
        "wm_mask_voxels": int(wm.numpy().sum()),
        "csf_mask_voxels": int(csf.numpy().sum()),
        "mni2t1_dice": dice(
            ants.apply_transforms(fixed=t1_brain, moving=tmask,
                                  transformlist=r2["fwdtransforms"],
                                  interpolator="nearestNeighbor").numpy() > 0.5,
            bmask.numpy() > 0.5),
    }
    return AnatResult(t1_brain, bmask, wm, csf, r2["fwdtransforms"], qc)


# --------------------------------------------------------------------------
# functional stage
# --------------------------------------------------------------------------
def _to_ants3d(arr: np.ndarray, ref) -> "ants.ANTsImage":
    return ants.from_numpy(np.ascontiguousarray(arr.astype(np.float32)),
                           spacing=ref.spacing[:3], origin=ref.origin[:3],
                           direction=ref.direction[:3, :3])


def parcel_means(data4d: np.ndarray, atlas: np.ndarray, n_nodes: int,
                 min_voxels: int = 10):
    """Mean time series per parcel, plus per-parcel voxel coverage.

    Parcels that fall outside the EPI field of view or inside a susceptibility
    dropout come back as NaN rather than as a misleading near-zero series.
    """
    n_t = data4d.shape[-1]
    flat = data4d.reshape(-1, n_t)
    lab = atlas.ravel()
    ts = np.full((n_t, n_nodes), np.nan, dtype=np.float32)
    cover = np.zeros(n_nodes, dtype=np.int32)
    for i in range(1, n_nodes + 1):
        idx = np.flatnonzero(lab == i)
        cover[i - 1] = idx.size
        if idx.size >= min_voxels:
            ts[:, i - 1] = flat[idx].mean(axis=0)
    return ts, cover


def prep_func_run(sub: str, task: str, run: int, anat: AnatResult,
                  atlas_mni: "ants.ANTsImage", n_nodes: int,
                  ref: dict | None = None, do_stc: bool = True) -> dict:
    """Preprocess one BOLD run and return parcel time series + confounds.

    ``ref`` carries the subject's reference-run registration.  The first run
    processed pays for a full SyN T1->EPI registration; later runs only pay for
    a cheap rigid alignment onto that reference, which is where most of the
    per-subject speed-up comes from.
    """
    fbase = BIDS / sub / "func" / f"{sub}_task-{task}_run-{run}_bold"
    meta = json.loads(Path(f"{fbase}.json").read_text())
    tr = float(meta["RepetitionTime"])
    slice_times = meta.get("SliceTiming")

    img = ants.image_read(f"{fbase}.nii.gz")
    # Hold the 4-D geometry, then drop the full-length image: a 488-volume run is
    # ~600 MB and several copies alive at once is what drives the machine into
    # swap when workers run in parallel.
    geom = {"spacing": img.spacing, "origin": img.origin, "direction": img.direction}
    arr = np.array(img.numpy()[..., DROP_VOLUMES:], copy=True)
    del img
    n_t = arr.shape[-1]

    if do_stc and slice_times:
        arr = slice_time_correct(arr, slice_times, tr)

    geom3 = SimpleNamespace(spacing=geom["spacing"], origin=geom["origin"],
                            direction=geom["direction"])
    mean0 = _to_ants3d(arr.mean(-1), geom3)
    epi_mask = ants.get_mask(mean0)
    ants4d = ants.from_numpy(np.ascontiguousarray(arr), **geom)
    del arr

    with tempfile.TemporaryDirectory(dir=_tmp_root()) as td:
        mc = ants.motion_correction(ants4d, mask=epi_mask,
                                    type_of_transform="BOLDRigid",
                                    outprefix=str(Path(td) / "mc"))
        moco = mc["motion_corrected"].numpy()
        fd = np.asarray(mc["FD"], dtype=float)
        motion, n_bad = _read_motion(mc["motion_parameters"])
    if n_bad:
        # ANTs writes one transform per volume; if the filesystem refused some
        # of them the motion model is incomplete and the confound regression
        # would be quietly wrong.  Better to fail this run and retry it.
        raise RuntimeError(f"{n_bad}/{len(motion)} motion transforms unreadable "
                           f"(likely transient disk exhaustion); retry this run")

    del ants4d, mc
    mean_epi = _to_ants3d(moco.mean(-1), geom3)
    epi_mask = ants.get_mask(mean_epi)
    epi_brain = mean_epi * epi_mask

    # ---- registration chain -------------------------------------------
    if ref is None:
        # fixed = EPI so that the chain is all-forward: MNI -> T1 -> EPI
        r = ants.registration(fixed=epi_brain, moving=anat.t1_brain,
                              type_of_transform="SyN")
        chain_t1_to_epi = r["fwdtransforms"]
        ref = {"mean": mean_epi, "brain": epi_brain, "t1_to_epi": chain_t1_to_epi}
        extra: list = []
    else:
        rr = ants.registration(fixed=epi_brain, moving=ref["brain"],
                               type_of_transform="Rigid")
        extra = rr["fwdtransforms"]
        chain_t1_to_epi = ref["t1_to_epi"]

    # ANTs applies a transformlist back-to-front, so it reads last-step-first.
    full = list(extra) + list(chain_t1_to_epi) + list(anat.mni_to_t1)

    atlas_epi = ants.apply_transforms(fixed=mean_epi, moving=atlas_mni,
                                      transformlist=full,
                                      interpolator="nearestNeighbor").numpy()
    atlas_epi = np.rint(atlas_epi).astype(np.int32)

    tissue_chain = list(extra) + list(chain_t1_to_epi)
    wm_epi = ants.apply_transforms(fixed=mean_epi, moving=anat.wm_mask,
                                   transformlist=tissue_chain,
                                   interpolator="nearestNeighbor").numpy() > 0.5
    csf_epi = ants.apply_transforms(fixed=mean_epi, moving=anat.csf_mask,
                                    transformlist=tissue_chain,
                                    interpolator="nearestNeighbor").numpy() > 0.5

    # ---- registration QC ----------------------------------------------
    _, tmask = _template()
    mni_brain_in_epi = ants.apply_transforms(
        fixed=mean_epi, moving=tmask, transformlist=full,
        interpolator="nearestNeighbor").numpy() > 0.5
    reg_dice = dice(mni_brain_in_epi, epi_mask.numpy() > 0.5)

    # ---- signals -------------------------------------------------------
    ts, cover = parcel_means(moco, atlas_epi, n_nodes)
    brain = epi_mask.numpy() > 0.5
    conf = {
        "motion": motion, "fd": fd, "dvars": dvars(moco, brain),
        "compcor_wm": compcor(moco, wm_epi & brain),
        "compcor_csf": compcor(moco, csf_epi & brain),
    }
    qc = {
        "sub": sub, "task": task, "run": run, "n_volumes": int(n_t), "tr": tr,
        "mean_fd": float(np.nanmean(fd)), "max_fd": float(np.nanmax(fd)),
        "pct_censored": float(100.0 * (fd > FD_SPIKE_MM).mean()),
        "mean_dvars": float(np.mean(conf["dvars"][1:])),
        "reg_dice_mni_to_epi": reg_dice,
        "is_reference_run": bool(not extra),
        "n_parcels_covered": int((cover >= 10).sum()),
        "n_parcels_missing": int((cover < 10).sum()),
        "wm_voxels_epi": int((wm_epi & brain).sum()),
        "csf_voxels_epi": int((csf_epi & brain).sum()),
        "stc_applied": bool(do_stc and slice_times),
    }
    return {"ts": ts, "cover": cover, "confounds": conf, "qc": qc, "ref": ref}
