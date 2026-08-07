# Exercise 01 — The stuck GPU job

## The situation

A colleague submitted `submit_pi.sh` to the cluster over an hour ago. The job
is still sitting in the queue, even though — in their words — *"the cluster
looks half-empty."* They're about to email the admins to complain that the
scheduler is broken.

Your job: figure out **why** the job isn't running, using only evidence pulled
from the live cluster.

## Ground rules

- Work inside `pw code`, using only the **pw-commands** MCP server to query
  the cluster. No manual SSH sessions, no guessing.
- **Justify every query before you run it.** What do you expect it to tell
  you? What decision does it feed?
- Pull the minimum evidence that supports a conclusion — this is a diagnosis
  exercise, not a data-collection exercise.

## Getting started

1. Submit the job (or use the job id your facilitator gives you):
   ask pw code to run `sbatch submit_pi.sh` on the training cluster from this
   directory.
2. Confirm the job is pending, and start investigating.

## Deliverable

A short written diagnosis:
- Why is the job pending? Quote the specific scheduler evidence.
- Is the "half-empty cluster" observation relevant? Why or why not?
- What do you recommend — and does it involve changing any code at all?
