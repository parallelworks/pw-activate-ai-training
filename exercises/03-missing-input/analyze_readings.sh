#!/usr/bin/env bash
# Per-sensor average and peak over the staged readings.
#   bash analyze_readings.sh <readings.csv>
set -euo pipefail

INPUT="${1:?usage: analyze_readings.sh <readings.csv>}"

awk -F, '
    { sum[$2] += $3; cnt[$2]++; if ($3 > peak[$2]) peak[$2] = $3 }
    END {
        for (s in sum)
            printf "%s avg=%.3f peak=%.3f n=%d\n", s, sum[s] / cnt[s], peak[s], cnt[s]
    }' "$INPUT" | sort -V

echo "analyzed $(wc -l < "$INPUT" | tr -d " ") readings"
