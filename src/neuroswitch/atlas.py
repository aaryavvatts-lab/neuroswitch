"""Build the combined brain parcellation used as GNN nodes.

Cortex   : Schaefer-2018 (200 parcels / 17 networks)
Subcortex: Harvard-Oxford subcortical (thalamus, caudate, putamen, pallidum,
           hippocampus, amygdala, accumbens, brainstem)
Cerebellum: AAL cerebellar hemispheres + vermis

All three natively inhabit FSL's MNI152 space, so they are combined without any
cross-template warp.  Everything is resampled (nearest-neighbour) onto one
canonical grid: tpl-MNI152NLin6Asym_res-02.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import nibabel as nib
import numpy as np
from nilearn import datasets
from nilearn.image import resample_to_img

ROOT = Path(__file__).resolve().parents[2]
NILEARN_DATA = str(ROOT / ".nilearn_data")

# Harvard-Oxford entries that are tissue compartments, not grey-matter nuclei.
_HO_SKIP = {
    "Background",
    "Left Cerebral White Matter", "Right Cerebral White Matter",
    "Left Cerebral Cortex", "Right Cerebral Cortex",
    "Left Lateral Ventricle", "Right Lateral Ventricle",
}


def _as_img(maps):
    return nib.load(maps) if isinstance(maps, (str, os.PathLike)) else maps


def _decode(label) -> str:
    return label.decode() if isinstance(label, bytes) else str(label)


def _network_of(schaefer_label: str) -> str:
    """'17Networks_LH_VisCent_ExStr_1' -> 'VisCent'."""
    parts = schaefer_label.split("_")
    return parts[2] if len(parts) > 2 else "Unknown"


def _hemi_of(schaefer_label: str) -> str:
    parts = schaefer_label.split("_")
    return parts[1] if len(parts) > 1 else "NA"


def build(n_rois: int = 200, yeo_networks: int = 17, out_dir: Path | None = None) -> dict:
    """Assemble the parcellation; returns metadata dict and writes NIfTI + JSON."""
    out_dir = Path(out_dir or ROOT / "derivatives" / "atlas")
    out_dir.mkdir(parents=True, exist_ok=True)

    import templateflow.api as tf
    target = _as_img(tf.get("MNI152NLin6Asym", resolution=2, suffix="T1w",
                            extension=".nii.gz", desc=None))

    shape, affine = target.shape, target.affine
    combined = np.zeros(shape, dtype=np.int16)
    records: list[dict] = []
    nxt = 1

    def _stamp(src_img, keep, name_of, source, network_of, hemi_of):
        """Write `keep` source-label values into the combined volume."""
        nonlocal nxt
        res = resample_to_img(src_img, target, interpolation="nearest",
                              force_resample=True, copy_header=True)
        data = np.asarray(res.dataobj).round().astype(np.int32)
        for src_val in keep:
            mask = data == src_val
            n_vox = int(mask.sum())
            if n_vox == 0:
                continue
            # Never overwrite an already-claimed voxel (cortex wins ties).
            mask &= combined == 0
            n_kept = int(mask.sum())
            if n_kept < 10:            # too small to yield a stable time series
                continue
            combined[mask] = nxt
            records.append({
                "id": nxt, "name": name_of(src_val), "source": source,
                "network": network_of(src_val), "hemi": hemi_of(src_val),
                "n_voxels": n_kept, "src_value": int(src_val),
            })
            nxt += 1

    # ---- cortex -----------------------------------------------------------
    sch = datasets.fetch_atlas_schaefer_2018(
        n_rois=n_rois, yeo_networks=yeo_networks, resolution_mm=2, data_dir=NILEARN_DATA)
    sch_labels = [_decode(x) for x in sch.labels]
    if sch_labels and sch_labels[0] == "Background":
        sch_labels = sch_labels[1:]                      # values are 1..n_rois
    _stamp(_as_img(sch.maps), range(1, len(sch_labels) + 1),
           name_of=lambda v: sch_labels[v - 1],
           source="Schaefer2018",
           network_of=lambda v: _network_of(sch_labels[v - 1]),
           hemi_of=lambda v: _hemi_of(sch_labels[v - 1]))

    # ---- subcortex --------------------------------------------------------
    ho = datasets.fetch_atlas_harvard_oxford("sub-maxprob-thr25-2mm", data_dir=NILEARN_DATA)
    ho_labels = [_decode(x) for x in ho.labels]
    keep_ho = [i for i, lab in enumerate(ho_labels) if lab not in _HO_SKIP]
    _stamp(_as_img(ho.maps), keep_ho,
           name_of=lambda v: ho_labels[v],
           source="HarvardOxford-sub",
           network_of=lambda v: "Subcortex",
           hemi_of=lambda v: ("LH" if ho_labels[v].startswith("Left")
                              else "RH" if ho_labels[v].startswith("Right") else "NA"))

    # ---- cerebellum -------------------------------------------------------
    aal = datasets.fetch_atlas_aal(data_dir=NILEARN_DATA)
    aal_labels = [_decode(x) for x in aal.labels]
    aal_idx = [int(x) for x in aal.indices]
    cereb = {idx: lab for lab, idx in zip(aal_labels, aal_idx)
             if lab.lower().startswith(("cerebel", "vermis"))}
    _stamp(_as_img(aal.maps), sorted(cereb),
           name_of=lambda v: cereb[v],
           source="AAL",
           network_of=lambda v: "Cerebellum",
           hemi_of=lambda v: ("LH" if cereb[v].endswith("_L")
                              else "RH" if cereb[v].endswith("_R") else "NA"))

    # ---- write ------------------------------------------------------------
    img = nib.Nifti1Image(combined, affine)
    img.set_data_dtype(np.int16)
    nii_path = out_dir / "atlas.nii.gz"
    nib.save(img, nii_path)

    meta = {
        "space": "MNI152NLin6Asym", "resolution_mm": 2, "shape": list(shape),
        "n_nodes": len(records),
        "sources": {
            "cortex": f"Schaefer2018 {n_rois}Parcels {yeo_networks}Networks",
            "subcortex": "HarvardOxford sub-maxprob-thr25-2mm",
            "cerebellum": "AAL (cerebellar hemispheres + vermis)",
        },
        "nodes": records,
    }
    (out_dir / "atlas.json").write_text(json.dumps(meta, indent=1))
    return meta


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    m = build(n_rois=n, out_dir=ROOT / "derivatives" / f"atlas-schaefer{n}")
    from collections import Counter
    print(f"nodes: {m['n_nodes']}")
    for src, c in Counter(r["source"] for r in m["nodes"]).items():
        print(f"  {src:24s} {c}")
    for net, c in sorted(Counter(r["network"] for r in m["nodes"]).items()):
        print(f"    {net:14s} {c}")
