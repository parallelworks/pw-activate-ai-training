# Exercise 02 — The job that keeps dying

## The situation

The `sensor_rollup` job processes a day's worth of sensor readings. It keeps
dying partway through — and the output file shows no obvious error, it
just... stops.

Your job: find out what's killing it and propose the smallest possible fix.

## Ground rules

- Work inside `pw code`, preferring the **pw-commands** MCP server to query
  the cluster. If the MCP route gets stuck, SSHing into the cluster and
  running the same commands by hand is a fine fallback — the discipline is
  about evidence, not the transport.
- **Pull only the evidence you need.** The discipline here is knowing which
  record answers the question — not tailing every log on the machine, and not
  reading the application code first.
- Propose the fix as a diff; don't hunt through `process_data.sh` unless the
  evidence points there.

## Getting started

1. Generate the input data on the cluster (one-time, takes a few minutes):
   run `bash make_input.sh` in this directory on the cluster.
2. Submit the run: `sbatch submit_process.sh`, wait for it to die, then
   investigate.

## Deliverable

- What killed the job? Quote the specific accounting evidence.
- The one-line fix, as a diff.
- How much evidence did you need to justify it? What did you *not* look at?
