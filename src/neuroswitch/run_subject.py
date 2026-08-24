"""Process one subject end-to-end: preprocess every run, save derivatives.

Deliberately checkpointed per run, so an interrupted batch resumes without
redoing finished work.  Raw NIfTI deletion is handled separately by reap.py and
only ever after these outputs exist and pass verification.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import traceback
from pathlib import Path

import ants
import numpy as np

from . import preprocess as pp

ROOT = Path(__file__).resolve().parents[2]
DERIV = ROOT / "derivatives"
TASKS = ("drawLH", "drawRH", "restingstate")


def available_runs(sub: str, task: str) -> list[int]:
    d = pp.BIDS / sub / "func"
    if not d.is_dir():
        return []
    runs = []
    for f in sorted(d.glob(f"{sub}_task-{task}_run-*_bold.nii.gz")):
        try:
            runs.append(int(f.name.split("_run-")[1].split("_")[0]))
        except (IndexError, ValueError):
            continue
    return sorted(runs)


def derivative_runs(sub: str, task: str) -> list[int]:
    """Runs that have been preprocessed, read from derivatives.

    Deliberately does not consult the raw BIDS tree: reaping deletes the source
    NIfTIs once derivatives are verified, so anything keyed on raw files reports
    zero runs for every completed subject.
    """
    import re
    runs = []
    for f in (DERIV / sub).glob(f"{sub}_task-{task}_run-*.npz"):
        m = re.search(r"run-(\d+)", f.name)
        if m:
            runs.append(int(m.group(1)))
    return sorted(runs)


def subject_done(sub: str) -> bool:
    f = DERIV / sub / "subject_qc.json"
    if not f.is_file():
        return False
    try:
        return json.loads(f.read_text()).get("status") == "complete"
    except json.JSONDecodeError:
        return False


def ensure_raw(sub: str, tasks: tuple[str, ...]) -> None:
    """Fetch this subject from OpenNeuro if their scans are not on disk."""
    have_t1 = (pp.BIDS / sub / "anat" / f"{sub}_T1w.nii.gz").is_file()
    have_run = any(available_runs(sub, t) for t in tasks)
    if have_t1 and have_run:
        return
    from .acquire import fetch_subject
    print(f"  {sub}: fetching from OpenNeuro...", flush=True)
    r = fetch_subject(sub)
    if not r.get("ok"):
        raise RuntimeError(f"fetch failed for {sub}: {r.get('failures') or r.get('reason')}")
    print(f"  {sub}: fetched {r['n_files']} files ({r['bytes']/2**30:.2f} GiB)", flush=True)


def process(sub: str, atlas_name: str = "atlas-schaefer200",
            tasks: tuple[str, ...] = TASKS, force: bool = False,
            fetch: bool = False) -> dict:
    out = DERIV / sub
    out.mkdir(parents=True, exist_ok=True)
    if subject_done(sub) and not force:
        return json.loads((out / "subject_qc.json").read_text())

    if fetch:
        ensure_raw(sub, tasks)

    atlas_dir = DERIV / atlas_name
    atlas_mni = ants.image_read(str(atlas_dir / "atlas.nii.gz"))
    n_nodes = json.loads((atlas_dir / "atlas.json").read_text())["n_nodes"]

    t0 = time.time()
    anat = pp.prep_anat(sub, out)
    (out / "anat_qc.json").write_text(json.dumps(anat.qc, indent=1))
    t_anat = time.time() - t0

    # The reference run defines the subject's T1->EPI registration.  Prefer a
    # drawLH run because that is the primary analysis condition.
    plan: list[tuple[str, int]] = []
    for task in tasks:
        plan += [(task, r) for r in available_runs(sub, task)]
    plan.sort(key=lambda tr_: (tr_[0] != "drawLH", tr_[0], tr_[1]))

    ref, run_qc, failed = None, [], []
    for task, run in plan:
        dest = out / f"{sub}_task-{task}_run-{run}.npz"
        if dest.is_file() and not force and ref is not None:
            run_qc.append(json.loads((out / f"{sub}_task-{task}_run-{run}_qc.json").read_text()))
            continue
        try:
            t1 = time.time()
            # One retry: the dominant failure mode is a transient inability to
            # write ANTs scratch when the volume is momentarily full, which
            # usually clears once another worker finishes.
            for attempt in range(2):
                try:
                    r = pp.prep_func_run(sub, task, run, anat, atlas_mni, n_nodes, ref=ref)
                    break
                except RuntimeError as exc:
                    if attempt == 1 or "unreadable" not in str(exc):
                        raise
                    print(f"  {sub} {task} run-{run}: retrying after {exc}",
                          file=sys.stderr, flush=True)
                    time.sleep(30)
            ref = r["ref"]
            c = r["confounds"]
            np.savez_compressed(
                dest, ts=r["ts"], cover=r["cover"], motion=c["motion"], fd=c["fd"],
                dvars=c["dvars"], compcor_wm=c["compcor_wm"], compcor_csf=c["compcor_csf"])
            r["qc"]["seconds"] = round(time.time() - t1, 1)
            (out / f"{sub}_task-{task}_run-{run}_qc.json").write_text(
                json.dumps(r["qc"], indent=1))
            run_qc.append(r["qc"])
            print(f"  {sub} {task} run-{run}: {r['qc']['seconds']}s "
                  f"FD={r['qc']['mean_fd']:.3f} dice={r['qc']['reg_dice_mni_to_epi']:.3f}",
                  flush=True)
        except Exception as exc:                      # keep going; record the failure
            failed.append({"task": task, "run": run, "error": repr(exc),
                           "traceback": traceback.format_exc()[-2000:]})
            print(f"  {sub} {task} run-{run}: FAILED {exc!r}", file=sys.stderr, flush=True)

    summary = {
        "sub": sub, "status": "complete" if run_qc and not failed else
                              ("partial" if run_qc else "failed"),
        "n_runs": len(run_qc), "n_failed": len(failed),
        "anat_qc": anat.qc, "anat_seconds": round(t_anat, 1),
        "total_seconds": round(time.time() - t0, 1),
        "atlas": atlas_name, "n_nodes": n_nodes,
        "runs": run_qc, "failures": failed,
    }
    (out / "subject_qc.json").write_text(json.dumps(summary, indent=1))
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("subjects", nargs="+")
    ap.add_argument("--atlas", default="atlas-schaefer200")
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--fetch", action="store_true",
                    help="download the subject from OpenNeuro if absent locally")
    a = ap.parse_args()
    for sub in a.subjects:
        t = time.time()
        s = process(sub, a.atlas, tuple(a.tasks.split(",")), a.force, a.fetch)
        print(f"{sub}: {s['status']} {s['n_runs']} runs "
              f"{s['total_seconds']}s ({(time.time()-t)/60:.1f} min)", flush=True)


if __name__ == "__main__":
    main()
