#!/usr/bin/env bash
# One rank of the sensor rollup: takes every NRANKS-th row of the input,
# holds its slice in memory while building per-sensor statistics, then prints
# the rollup. Memory use is proportional to the slice size.
set -euo pipefail

INPUT="${1:?usage: process_data.sh <input.csv>}"
RANK="${SLURM_PROCID:-0}"
NRANKS="${SLURM_NTASKS:-1}"

awk -F, -v rank="$RANK" -v nranks="$NRANKS" '
    NR % nranks == rank {
        rows[++n] = $0                 # keep the raw slice for the detail pass
        sum[$2] += $3; cnt[$2]++
        if ($3 > peak[$2]) peak[$2] = $3
    }
    END {
        for (s in sum)
            printf "rank %d %s avg=%.3f peak=%.3f n=%d\n", rank, s, sum[s] / cnt[s], peak[s], cnt[s]
        printf "rank %d processed %d rows\n", rank, n > "/dev/stderr"
    }' "$INPUT"
