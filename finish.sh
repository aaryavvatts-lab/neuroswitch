#!/usr/bin/env bash
# Runs after the main preprocessing queue empties, and takes the project the
# rest of the way without supervision:
#   1. retry anyone the main pass left incomplete
#   2. fetch and process the resting scans (the rest versus task control)
#   3. rebuild the feature store
#   4. run the full analysis, the control tests and region importance
#   5. rebuild the site
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export NEUROSWITCH_TMP="$PWD/.antstmp"
export PYTHONUNBUFFERED=1
PY="$PWD/.venv/bin/python"
mkdir -p logs

echo "== waiting for the main queue to finish"
while pgrep -f "drive.sh 1 3 subjects_queue.txt" >/dev/null; do sleep 120; done
echo "== main queue done at $(date +%H:%M)"

echo "== step 1: retry incomplete subjects"
./retry.sh 2>&1 | tail -20

echo "== step 2: resting scans"
"$PY" - > /tmp/neuroswitch_rest.txt <<'PYEOF'
import json, pathlib
from neuroswitch.dataset import AUTHOR_EXCLUDED
D = pathlib.Path("derivatives")
out = []
for f in sorted(D.glob("sub-*/subject_qc.json")):
    sub = f.parent.name
    if sub in AUTHOR_EXCLUDED:
        continue
    if not list((D / sub).glob(f"{sub}_task-restingstate_run-*.npz")):
        out.append(sub)
print("\n".join(out))
PYEOF
n=$(grep -c . /tmp/neuroswitch_rest.txt || true)
echo "   ${n:-0} subjects need resting scans"
./drive.sh 1 4 /tmp/neuroswitch_rest.txt restingstate 2>&1 | tail -15 || true

echo "== step 3: feature store"
"$PY" - <<'PYEOF'
import pathlib, subprocess, sys
D = pathlib.Path("derivatives")
subs = sorted({p.parent.name for p in D.glob("sub-*/subject_qc.json")})
subprocess.run([sys.executable, "-m", "neuroswitch.features", *subs])
PYEOF

echo "== step 4: analysis"
"$PY" -m neuroswitch.sanity 2>&1 | tail -5
"$PY" -m neuroswitch.run_analysis --stages cohort,main,controls --repeats 10 --perm 500 2>&1 | tail -40
"$PY" -m neuroswitch.run_importance --condition LH --repeats 4 2>&1 | tail -15

echo "== step 5: site"
"$PY" -m neuroswitch.site_build
"$PY" -m neuroswitch.export_site
echo "== finished at $(date +%H:%M)"
