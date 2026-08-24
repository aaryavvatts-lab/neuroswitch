"""Delete a subject's raw NIfTIs -- but only once its derivatives are proven good.

The dataset is CC0 and public, and every local file is recorded in
derivatives/MANIFEST.json with its OpenNeuro S3 key and byte size, so a reaped
subject can always be re-fetched byte-identical.  Nothing here is irreversible;
it is still gated behind explicit verification because a silent bad extraction
followed by deletion would cost hours.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .preprocess import BIDS
from .run_subject import DERIV, TASKS, available_runs

MIN_COVERED_FRACTION = 0.90     # parcels with usable signal
MIN_REG_DICE = 0.85             # MNI->EPI overlap
LOG = DERIV / "reaped.jsonl"


def verify(sub: str, expect_nodes: int | None = None,
           tasks: tuple[str, ...] = TASKS) -> tuple[bool, list[str]]:
    """Return (ok, reasons_it_failed)."""
    out, bad = DERIV / sub, []
    qc_file = out / "subject_qc.json"
    if not qc_file.is_file():
        return False, ["no subject_qc.json"]
    qc = json.loads(qc_file.read_text())
    if qc.get("status") == "failed":
        bad.append("status=failed")
    failed_in_scope = [f for f in qc.get("failures", []) if f.get("task") in tasks]
    if failed_in_scope:
        bad.append(f"{len(failed_in_scope)} failed runs in {sorted(tasks)}")

    expected = {(t, r) for t in tasks for r in available_runs(sub, t)}
    if not expected:
        bad.append("no raw runs found")
    for task, run in sorted(expected):
        f = out / f"{sub}_task-{task}_run-{run}.npz"
        if not f.is_file() or f.stat().st_size == 0:
            bad.append(f"missing derivative {task} run-{run}")
            continue
        with np.load(f) as z:
            ts, cover = z["ts"], z["cover"]
        n_t, n_nodes = ts.shape
        if expect_nodes and n_nodes != expect_nodes:
            bad.append(f"{task} run-{run}: {n_nodes} nodes, expected {expect_nodes}")
        if n_t < 100:
            bad.append(f"{task} run-{run}: only {n_t} volumes")
        usable = ~np.isnan(ts).all(axis=0)
        if usable.mean() < MIN_COVERED_FRACTION:
            bad.append(f"{task} run-{run}: only {usable.mean():.0%} parcels covered")
        if np.isnan(ts[:, usable]).any():
            bad.append(f"{task} run-{run}: NaNs inside covered parcels")
        if float(np.nanstd(ts[:, usable])) == 0.0:
            bad.append(f"{task} run-{run}: zero variance")

    for r in qc.get("runs", []):
        if r["task"] not in tasks:
            continue
        if r.get("reg_dice_mni_to_epi", 0) < MIN_REG_DICE:
            bad.append(f"{r['task']} run-{r['run']}: registration dice "
                       f"{r.get('reg_dice_mni_to_epi'):.2f} < {MIN_REG_DICE}")
    return (not bad), bad


def _manifest_index() -> dict[str, int]:
    f = DERIV / "MANIFEST.json"
    if not f.is_file():
        return {}
    return {e["rel"]: e["bytes"] for e in json.loads(f.read_text())["files"]}


def reap(sub: str, dry_run: bool = True, expect_nodes: int | None = None,
         tasks: tuple[str, ...] = TASKS) -> dict:
    ok, reasons = verify(sub, expect_nodes, tasks)
    if not ok:
        return {"sub": sub, "reaped": False, "reasons": reasons, "freed_bytes": 0}

    manifest = _manifest_index()
    targets, freed, unrecoverable = [], 0, []
    for f in sorted((BIDS / sub).rglob("*.nii.gz")):
        rel = str(f.relative_to(BIDS))
        if rel not in manifest:
            unrecoverable.append(rel)          # never delete what we cannot restore
            continue
        targets.append(f)
        freed += f.stat().st_size

    if unrecoverable:
        return {"sub": sub, "reaped": False, "freed_bytes": 0,
                "reasons": [f"{len(unrecoverable)} files absent from MANIFEST"],
                "unrecoverable": unrecoverable[:5]}

    if not dry_run:
        for f in targets:
            f.unlink()
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(json.dumps({"sub": sub, "n_files": len(targets),
                                 "freed_bytes": freed,
                                 "files": [str(t.relative_to(BIDS)) for t in targets]}) + "\n")
    return {"sub": sub, "reaped": not dry_run, "n_files": len(targets),
            "freed_bytes": freed, "reasons": []}


def main() -> None:
    ap = argparse.ArgumentParser(description="Delete raw NIfTIs for verified subjects.")
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--execute", action="store_true", help="actually delete (default: dry run)")
    ap.add_argument("--expect-nodes", type=int, default=None)
    ap.add_argument("--tasks", default=",".join(TASKS),
                    help="only require derivatives for these tasks")
    a = ap.parse_args()
    tasks = tuple(a.tasks.split(","))
    total = 0
    for sub in a.subjects:
        r = reap(sub, dry_run=not a.execute, expect_nodes=a.expect_nodes, tasks=tasks)
        total += r["freed_bytes"] if r.get("reaped") else 0
        verb = "REAPED" if r.get("reaped") else ("would free" if not r["reasons"] else "SKIP")
        print(f"{sub}: {verb} {r['freed_bytes']/2**30:.2f} GiB"
              + (f" -- {'; '.join(r['reasons'])}" if r["reasons"] else ""))
    if a.execute:
        print(f"total freed: {total/2**30:.2f} GiB")


if __name__ == "__main__":
    main()
