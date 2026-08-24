#!/usr/bin/env bash
# Parallel per-subject preprocessing.  One OS process per subject: memory
# isolation, and a crash takes down only that subject.
#   ./run_batch.sh 5 sub-2002 sub-2003 ...
# NB: call .venv/bin/python directly.  `uv run` locks the environment, so
# concurrent invocations serialise and most workers sit idle.
set -uo pipefail
cd "$(dirname "$0")"
export TEMPLATEFLOW_HOME="$PWD/.templateflow"
export ITK_GLOBAL_DEFAULT_NUMBER_OF_THREADS=1   # ANTs moco is serial anyway
export PYTHONUNBUFFERED=1
mkdir -p logs
PY="$PWD/.venv/bin/python"
WORKERS="$1"; shift
printf '%s\n' "$@" | xargs -P "$WORKERS" -I{} sh -c \
  "$PY -m neuroswitch.run_subject {} >logs/{}.log 2>&1; printf '%s exit=%s\n' {} \$?"
