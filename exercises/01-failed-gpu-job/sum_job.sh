#!/usr/bin/env bash
# One task of a distributed sum: add up the integers 1..N, split across
# parallel tasks — plain bash + awk, no compiler.
# Launched under the scheduler as:  srun bash sum_job.sh <N> <outdir>
set -euo pipefail

N="${1:-1000000}"
OUTDIR="${2:-sum_out}"
TASK="${SLURM_PROCID:-0}"
NTASKS="${SLURM_NTASKS:-1}"

mkdir -p "$OUTDIR"

# This task sums its own slice of 1..N.
awk -v task="$TASK" -v ntasks="$NTASKS" -v n="$N" 'BEGIN {
    chunk = int(n / ntasks)
    start = task * chunk + 1
    end   = (task == ntasks - 1) ? n : (task + 1) * chunk
    sum = 0
    for (i = start; i <= end; i++) sum += i
    print sum
}' > "$OUTDIR/task_${TASK}.sum"

echo "task ${TASK}/${NTASKS}: wrote $OUTDIR/task_${TASK}.sum"

# Task 0 waits for every task's partial sum, then aggregates.
if [ "$TASK" -eq 0 ]; then
    while [ "$(find "$OUTDIR" -name 'task_*.sum' | wc -l)" -lt "$NTASKS" ]; do
        sleep 1
    done
    awk -v n="$N" '{ total += $1 }
         END { printf "sum(1..%d) = %.0f (expected %.0f) across %d tasks\n",
               n, total, n * (n + 1) / 2, NR }' \
        "$OUTDIR"/task_*.sum
fi
