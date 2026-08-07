#!/usr/bin/env bash
# Generate sensor-reading input data on the cluster.
#   bash make_input.sh small   -> data/input_small.csv  (~5 MB, for quick tests)
#   bash make_input.sh full    -> data/input_full.csv   (~2.5 GB, the real run)
set -euo pipefail
cd "$(dirname "$0")"

SIZE="${1:-small}"
case "$SIZE" in
    small) ROWS=100000 ;;
    full)  ROWS=60000000 ;;
    *) echo "usage: $0 [small|full]" >&2; exit 1 ;;
esac

mkdir -p data
awk -v n="$ROWS" 'BEGIN {
    srand(7)
    for (i = 1; i <= n; i++)
        printf "%d,sensor-%d,%.4f,%.4f,%d\n", i, i % 500, rand() * 100, rand() * 50, 1700000000 + i
}' > "data/input_${SIZE}.csv"

ls -lh "data/input_${SIZE}.csv"
