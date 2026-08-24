"""Run the full model suite plus control analyses; write results/ as JSON.

Everything the website shows is produced here, so the site can never quote a
number that was not computed by this script.
"""
from __future__ import annotations

import argparse
import json
import time
import traceback
from pathlib import Path

import numpy as np

from .dataset import cohort, summary
from .experiments import build_bundle, describe, model_suite
from .validate import cross_validate, permutation_test

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


class _Enc(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, (np.floating,)):
            return None if np.isnan(o) else float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, (np.bool_,)):
            return bool(o)
        return super().default(o)


def _write(name: str, obj) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1, cls=_Enc))
    print(f"  -> {p.relative_to(ROOT)}")
    return p


def main_models(cond: str = "LH", n_repeats: int = 10, n_perm: int = 500,
                include_gnn: bool = True) -> dict:
    b = build_bundle(cond)
    out = {"condition": cond, "bundle": describe(b), "models": {}}
    for name, make in model_suite(include_gnn).items():
        t0 = time.time()
        try:
            r = cross_validate(make, b, n_repeats=n_repeats)
            entry = {k: r[k] for k in ("auc_mean", "auc_sd", "auc_ci")}
            entry["aggregate"] = r["aggregate"]
            # permutation-test the headline models and every null
            if n_perm and (name.startswith("NULL") or name in
                           ("tangent+logreg", "GCN", "tangent+svm")):
                pt = permutation_test(make, b, n_perm=n_perm, observed=r["auc_mean"])
                pt.pop("null", None)
                entry["permutation"] = pt
            entry["seconds"] = round(time.time() - t0, 1)
            out["models"][name] = entry
            print(f"  {name:26s} AUC={entry['auc_mean']:.3f} "
                  f"+/-{entry['auc_sd']:.3f}  ({entry['seconds']}s)", flush=True)
        except Exception as exc:
            out["models"][name] = {"error": repr(exc),
                                   "traceback": traceback.format_exc()[-1500:]}
            print(f"  {name:26s} FAILED {exc!r}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default="cohort,main,controls",
                    help="comma list: cohort,main,controls,explain")
    ap.add_argument("--condition", default="LH")
    ap.add_argument("--repeats", type=int, default=10)
    ap.add_argument("--perm", type=int, default=500)
    ap.add_argument("--no-gnn", action="store_true")
    a = ap.parse_args()
    stages = set(a.stages.split(","))

    if "cohort" in stages:
        print("[cohort]")
        df = cohort()
        _write("cohort", {"summary": summary(df),
                          "subjects": df.to_dict(orient="records")})

    if "main" in stages:
        print(f"[main models: {a.condition}]")
        _write(f"models_{a.condition}",
               main_models(a.condition, a.repeats, a.perm, not a.no_gnn))

    if "controls" in stages:
        from .analyses import controls as C
        for name, fn in (("handflip", C.handflip), ("behaviour", C.behaviour),
                         ("severity", C.severity), ("rest_vs_task", C.rest_vs_task),
                         ("difficulty", C.difficulty)):
            print(f"[control: {name}]")
            try:
                _write(f"control_{name}", fn())
            except Exception as exc:
                print(f"  FAILED {exc!r}")
                _write(f"control_{name}", {"error": repr(exc),
                                           "traceback": traceback.format_exc()[-1500:]})


if __name__ == "__main__":
    main()
