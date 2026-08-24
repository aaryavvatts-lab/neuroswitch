#!/usr/bin/env bash
# Second pass over anyone the main run left incomplete.
#
# run_subject resumes: it skips runs whose derivative already exists and only
# redoes the reference run, so a retry costs one extra run rather than a whole
# subject. Anything still incomplete after this needs looking at by hand.
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export NEUROSWITCH_TMP="$PWD/.antstmp"
export PYTHONUNBUFFERED=1
PY="$PWD/.venv/bin/python"
mkdir -p logs "$NEUROSWITCH_TMP"

"$PY" - > /tmp/neuroswitch_retry.txt <<'PYEOF'
import json, pathlib, re
from neuroswitch.dataset import AUTHOR_EXCLUDED
from neuroswitch.preprocess import BIDS
D = pathlib.Path("derivatives")
todo = []
for f in sorted(D.glob("sub-*/subject_qc.json")):
    sub = f.parent.name
    if sub in AUTHOR_EXCLUDED:
        continue
    q = json.loads(f.read_text())
    failed = [x for x in q.get("failures", []) if x["task"].startswith("draw")]
    have = {(r["task"], r["run"]) for r in q.get("runs", []) if r["task"].startswith("draw")}
    # what the raw tree still offers, if it has not been reaped
    raw = set()
    for t in ("drawLH", "drawRH"):
        for p in (BIDS / sub / "func").glob(f"{sub}_task-{t}_run-*_bold.nii.gz"):
            m = re.search(r"run-(\d+)", p.name)
            if m:
                raw.add((t, int(m.group(1))))
    if failed or (raw - have):
        todo.append(sub)
print("\n".join(todo))
PYEOF

n=$(grep -c . /tmp/neuroswitch_retry.txt || true)
if [ "${n:-0}" -eq 0 ]; then
  echo "nothing to retry"
  exit 0
fi
echo "retrying $n subjects:"
cat /tmp/neuroswitch_retry.txt
while IFS= read -r sub; do
  [ -z "$sub" ] && continue
  echo "== $sub"
  "$PY" -m neuroswitch.run_subject "$sub" --fetch --tasks drawLH,drawRH >>logs/"$sub".log 2>&1
  "$PY" -m neuroswitch.reap "$sub" --execute --expect-nodes 241 --tasks drawLH,drawRH
done < /tmp/neuroswitch_retry.txt
echo "retry pass done"
