#!/usr/bin/env bash
# Build the per-condition feature store for any subject whose preprocessing has
# finished but whose features are missing, then refresh the sanity check and the
# site.  Runs alongside the preprocessing driver; each pass is seconds of CPU.
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export PYTHONUNBUFFERED=1
PY="$PWD/.venv/bin/python"
INTERVAL="${1:-900}"

while true; do
  todo=$("$PY" - <<'PYEOF'
import json, pathlib
D = pathlib.Path("derivatives"); F = D / "features"
out = []
for f in sorted(D.glob("sub-*/subject_qc.json")):
    sub = f.parent.name
    try: q = json.loads(f.read_text())
    except Exception: continue
    runs = {(r["task"], r["run"]) for r in q.get("runs", []) if r["task"].startswith("draw")}
    if len(runs) < 2:
        continue
    if not (F / f"{sub}_LH.npz").is_file():
        out.append(sub)
print(" ".join(out))
PYEOF
)
  if [ -n "$todo" ]; then
    echo "[$(date +%H:%M:%S)] features: $todo"
    # shellcheck disable=SC2086
    "$PY" -m neuroswitch.features $todo 2>&1 | grep -v RuntimeWarning | grep -v "^  out\[" || true
    "$PY" -m neuroswitch.sanity >/dev/null 2>&1 || true
    "$PY" -m neuroswitch.run_analysis --stages cohort >/dev/null 2>&1 || true
    "$PY" -m neuroswitch.site_build >/dev/null 2>&1 || true
    echo "[$(date +%H:%M:%S)] site refreshed"
  fi
  sleep "$INTERVAL"
done
