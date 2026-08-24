#!/usr/bin/env bash
# Process subjects in chunks, reaping each chunk before the next wave so free
# disk grows monotonically instead of being consumed.
#
#   ./drive.sh <workers> <min_free_gb> <subjects_file>
#
# Takes a file (one subject per line) rather than argv: the caller's shell may
# be zsh, which does not word-split unquoted variables, and a 45-element list
# silently arriving as one argument is a nasty failure mode.
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export TMPDIR="$PWD/.antstmp"
export PYTHONUNBUFFERED=1
export NEUROSWITCH_TMP="$PWD/.antstmp"
mkdir -p logs "$TMPDIR"
PY="$PWD/.venv/bin/python"

WORKERS="$1"; MIN_FREE_GB="$2"; LIST="$3"; TASKS="${4:-drawLH,drawRH}"
free_gb() { df -g /Users/aaryav-sharma | awk 'NR==2{print $4}'; }

# macOS ships bash 3.2, which has no `mapfile`.
subs=()
while IFS= read -r line; do
  [ -n "$line" ] && subs+=("$line")
done < "$LIST"
total=${#subs[@]}; done_n=0
echo "== ${total} subjects, ${WORKERS} workers, floor ${MIN_FREE_GB} GiB"
while [ ${#subs[@]} -gt 0 ]; do
  free=$(free_gb)
  if [ "$free" -lt "$MIN_FREE_GB" ]; then
    echo "!! only ${free} GiB free (floor ${MIN_FREE_GB}); stopping." >&2; exit 3
  fi
  chunk=("${subs[@]:0:$WORKERS}"); subs=("${subs[@]:$WORKERS}")
  echo "== wave [${done_n}/${total}, ${free} GiB free]: ${chunk[*]}"
  printf '%s\n' "${chunk[@]}" | xargs -P "$WORKERS" -I{} sh -c \
    "$PY -m neuroswitch.run_subject {} --fetch --tasks '"$TASKS"' >>logs/{}.log 2>&1 || echo '{} FAILED' >&2"
  for s in "${chunk[@]}"; do
    $PY -m neuroswitch.reap "$s" --execute --expect-nodes 241 --tasks "$TASKS"
    done_n=$((done_n+1))
  done
  rm -rf "$TMPDIR"/* 2>/dev/null
done
echo "== all done: ${done_n}/${total}, $(free_gb) GiB free"
