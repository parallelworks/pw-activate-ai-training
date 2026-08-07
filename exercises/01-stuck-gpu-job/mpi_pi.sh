#!/usr/bin/env bash
# One MPI rank of a Monte Carlo pi estimate — plain bash + awk, no compiler.
# Launched under the scheduler as:  srun bash mpi_pi.sh <samples> <outdir>
set -euo pipefail

SAMPLES="${1:-100000}"
OUTDIR="${2:-pi_out}"
RANK="${SLURM_PROCID:-${PMI_RANK:-${OMPI_COMM_WORLD_RANK:-0}}}"
NRANKS="${SLURM_NTASKS:-${PMI_SIZE:-${OMPI_COMM_WORLD_SIZE:-1}}}"

mkdir -p "$OUTDIR"

awk -v seed="$((RANK + 1))" -v n="$SAMPLES" 'BEGIN {
    srand(seed)
    inside = 0
    for (i = 0; i < n; i++) {
        x = rand(); y = rand()
        if (x * x + y * y <= 1) inside++
    }
    print inside, n
}' > "$OUTDIR/rank_${RANK}.count"

echo "rank ${RANK}/${NRANKS}: wrote $OUTDIR/rank_${RANK}.count"

# Rank 0 waits for every rank's partial count, then aggregates.
if [ "$RANK" -eq 0 ]; then
    while [ "$(find "$OUTDIR" -name 'rank_*.count' | wc -l)" -lt "$NRANKS" ]; do
        sleep 1
    done
    awk '{ inside += $1; total += $2 }
         END { printf "pi ~= %.6f (%d samples across %d ranks)\n", 4 * inside / total, total, NR }' \
        "$OUTDIR"/rank_*.count
fi
