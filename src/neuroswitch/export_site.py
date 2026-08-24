"""Export compact JSON for the interactive brain page."""
from __future__ import annotations

import json
from pathlib import Path

import nibabel as nib
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
SITE_DATA = ROOT / "site" / "data"
ATLAS_DIR = ROOT / "derivatives" / "atlas-schaefer200"


def centroids() -> list[dict]:
    """MNI centre of mass for every parcel, for plotting."""
    img = nib.load(ATLAS_DIR / "atlas.nii.gz")
    data = np.asarray(img.dataobj).astype(np.int32)
    meta = json.loads((ATLAS_DIR / "atlas.json").read_text())
    aff = img.affine
    out = []
    for node in meta["nodes"]:
        i = node["id"]
        idx = np.argwhere(data == i)
        if idx.size == 0:
            xyz = [np.nan] * 3
        else:
            vox = idx.mean(axis=0)
            xyz = (aff @ np.append(vox, 1.0))[:3]
        out.append({
            "id": i,
            "name": node["name"],
            "network": node["network"],
            "hemi": node["hemi"],
            "source": node["source"],
            "n_voxels": node["n_voxels"],
            "x": round(float(xyz[0]), 1),
            "y": round(float(xyz[1]), 1),
            "z": round(float(xyz[2]), 1),
        })
    return out


def _pretty(name: str) -> str:
    """'17Networks_LH_SomMotB_S2_2' -> 'L SomMotB S2 2'."""
    n = name.replace("17Networks_", "")
    n = n.replace("LH_", "L ").replace("RH_", "R ")
    return n.replace("_", " ")


def build(importance_file: str = "importance_LH") -> dict:
    SITE_DATA.mkdir(parents=True, exist_ok=True)
    nodes = centroids()
    for n in nodes:
        n["label"] = _pretty(n["name"])

    imp = {}
    p = RESULTS / f"{importance_file}.json"
    if p.is_file():
        imp = json.loads(p.read_text())

    payload = {
        "nodes": nodes,
        "networks": sorted({n["network"] for n in nodes}),
        "importance": imp.get("node_importance"),
        "importance_meta": {k: v for k, v in imp.items() if k != "node_importance"},
        "extent": {
            "x": [min(n["x"] for n in nodes), max(n["x"] for n in nodes)],
            "y": [min(n["y"] for n in nodes), max(n["y"] for n in nodes)],
            "z": [min(n["z"] for n in nodes), max(n["z"] for n in nodes)],
        },
    }
    (SITE_DATA / "brain.json").write_text(json.dumps(payload, separators=(",", ":")))
    return payload


if __name__ == "__main__":
    p = build()
    print(f"{len(p['nodes'])} nodes -> site/data/brain.json "
          f"({(SITE_DATA/'brain.json').stat().st_size/1024:.0f} KB)")
    print("networks:", ", ".join(p["networks"]))
    import collections
    print("hemi:", collections.Counter(n["hemi"] for n in p["nodes"]))
    sm = [n for n in p["nodes"] if n["network"].startswith("SomMot")]
    print("example sensorimotor:", [(n["label"], n["x"]) for n in sm[:3]])
