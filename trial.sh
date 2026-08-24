#!/usr/bin/env bash
# Wait until enough people of both groups have been processed, then run the full
# analysis once as a rehearsal. Catches problems that only show up on real data
# while there is still time to fix them, instead of at the end of a long run.
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export PYTHONUNBUFFERED=1
PY="$PWD/.venv/bin/python"
NEED="${1:-8}"

while true; do
  read -r np nc <<< "$("$PY" - <<'PYEOF'
import pathlib
F = pathlib.Path("derivatives/features")
subs = {f.name.split("_")[0] for f in F.glob("sub-*_LH.npz")}
print(sum(s.startswith("sub-1") for s in subs), sum(s.startswith("sub-2") for s in subs))
PYEOF
)"
  if [ "${np:-0}" -ge "$NEED" ] && [ "${nc:-0}" -ge "$NEED" ]; then
    echo "[$(date +%H:%M:%S)] $np patients, $nc controls. Running trial analysis."
    "$PY" -m neuroswitch.run_analysis --stages cohort,main --repeats 3 --perm 50 2>&1 | tail -30
    echo "[$(date +%H:%M:%S)] trial done"
    break
  fi
  echo "[$(date +%H:%M:%S)] waiting: $np patients, $nc controls (need $NEED each)"
  sleep 600
done
