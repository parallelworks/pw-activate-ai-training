#!/usr/bin/env bash
# Generate the sensor-reading input data on the cluster (~2.5 GB, one-time).
#   bash make_input.sh   -> data/input_full.csv
set -euo pipefail
cd "$(dirname "$0")"

ROWS=60000000

mkdir -p data
awk -v n="$ROWS" 'BEGIN {
    srand(7)
    for (i = 1; i <= n; i++)
        printf "%d,sensor-%d,%.4f,%.4f,%d\n", i, i % 500, rand() * 100, rand() * 50, 1700000000 + i
}' > data/input_full.csv

ls -lh data/input_full.csv
