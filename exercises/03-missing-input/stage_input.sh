#!/usr/bin/env bash
# Stage today's sensor readings for the analysis job (one-time, a few seconds).
#   bash stage_input.sh   -> $DATA_DIR/readings.csv
set -euo pipefail
cd "$(dirname "$0")"
source ./config.sh

ROWS=50000

mkdir -p "$DATA_DIR"
awk -v n="$ROWS" 'BEGIN {
    srand(11)
    for (i = 1; i <= n; i++)
        printf "%d,sensor-%d,%.4f\n", i, i % 50, rand() * 100
}' > "$DATA_DIR/readings.csv"

ls -lh "$DATA_DIR/readings.csv"
