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
from .run_subject import DERIV, TASKS, available_runs, derivative_runs

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

    # union of raw runs (not yet reaped) and preprocessed runs (already reaped)
    expected = {(t, r) for t in tasks
                for r in set(available_runs(sub, t)) | set(derivative_runs(sub, t))}
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


def _remote_size(rel: str, timeout: int = 30) -> int | None:
    """Byte size of this file on OpenNeuro, or None if it is not there.

    The local manifest only covers files that were on disk when it was written,
    so subjects fetched later are absent from it.  Rather than trust a local
    record, confirm against the public bucket at deletion time: if the object is
    there and the size matches, the file can always be pulled back.
    """
    import subprocess
    url = f"https://s3.amazonaws.com/openneuro.org/ds008162/{rel}"
    try:
        r = subprocess.run(["curl", "-sIL", "--max-time", str(timeout), url],
                           capture_output=True, text=True)
    except Exception:
        return None
    if " 200" not in r.stdout.split("\n")[0] and "200 OK" not in r.stdout:
        if "HTTP/2 200" not in r.stdout and "HTTP/1.1 200" not in r.stdout:
            return None
    sizes = [ln.split(":", 1)[1].strip() for ln in r.stdout.splitlines()
             if ln.lower().startswith("content-length")]
    try:
        return int(sizes[-1]) if sizes else None
    except ValueError:
        return None


def reap(sub: str, dry_run: bool = True, expect_nodes: int | None = None,
         tasks: tuple[str, ...] = TASKS) -> dict:
    ok, reasons = verify(sub, expect_nodes, tasks)
    if not ok:
        return {"sub": sub, "reaped": False, "reasons": reasons, "freed_bytes": 0}

    manifest = _manifest_index()
    targets, freed, unrecoverable = [], 0, []
    for f in sorted((BIDS / sub).rglob("*.nii.gz")):
        rel = str(f.relative_to(BIDS))
        size = f.stat().st_size
        if manifest.get(rel) == size:
            ok = True
        else:
            remote = _remote_size(rel)          # confirm against the public bucket
            ok = remote == size
        if not ok:
            unrecoverable.append(rel)           # never delete what we cannot restore
            continue
        targets.append(f)
        freed += size

    if unrecoverable:
        return {"sub": sub, "reaped": False, "freed_bytes": 0,
                "reasons": [f"{len(unrecoverable)} files not confirmed "
                            f"recoverable from OpenNeuro"],
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
