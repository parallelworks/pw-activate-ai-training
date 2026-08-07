# Exercise 02 — The job that keeps dying

## The situation

The `sensor_rollup` job processes a day's worth of sensor readings. Last week
it ran perfectly on a test file. This week, running against the full dataset,
it keeps dying partway through — and the output file shows no obvious error,
it just... stops.

Your job: find out what's killing it and propose the smallest possible fix.

## Ground rules

- Work inside `pw code`, using only the **pw-commands** MCP server to query
  the cluster. No manual SSH sessions.
- **Pull only the evidence you need.** The discipline here is knowing which
  record answers the question — not tailing every log on the machine, and not
  reading the application code first.
- Propose the fix as a diff; don't hunt through `process_data.sh` unless the
  evidence points there.

## Getting started

1. Generate the input data on the cluster (one-time, takes a few minutes):
   run `bash make_input.sh small` and `bash make_input.sh full` in this
   directory on the cluster.
2. Sanity-check the small run if you like: edit the input path in
   `submit_process.sh` to `data/input_small.csv` and submit — it completes.
3. Submit the real run: `sbatch submit_process.sh`, wait for it to die, then
   investigate.

## Deliverable

- What killed the job? Quote the specific accounting evidence.
- The one-line fix, as a diff.
- How much evidence did you need to justify it? What did you *not* look at?
