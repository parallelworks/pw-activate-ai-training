# Exercise 01 — The failed GPU job

## The situation

A colleague submitted `submit_sum.sh` to the cluster this morning, and the
job never ran. Depending on how the cluster is configured, the scheduler
either bounced it at submission with a cryptic error, or accepted it and has
left it sitting there ever since. In their words: *"the cluster must be out
of GPUs."* They're about to email the admins to ask for more capacity.

Your job: figure out **why** the job won't run, using evidence pulled from
the live cluster — not by reading the script and guessing.

## Ground rules

- Work inside `pw code`, preferring the **pw-commands** MCP server to query
  the cluster. If the MCP route gets stuck, SSHing into the cluster and
  running the same scheduler commands by hand is a fine fallback — the
  discipline is about evidence, not the transport. No guessing either way.
- **Justify every query before you run it.** What do you expect it to tell
  you? What decision does it feed?
- Pull the minimum evidence that supports a conclusion — this is a diagnosis
  exercise, not a data-collection exercise.

## Getting started

1. Submit the job (or use the job id your facilitator gives you):
   ask pw code to run `sbatch submit_sum.sh` on the training cluster from this
   directory.
2. Look at what the scheduler did with it, and start investigating.

## Deliverable

A short written diagnosis:
- Why won't the job run? Quote the specific scheduler evidence — the
  submission error or pending Reason, and what the job asked for versus what
  the partition offers.
- Is the "cluster is out of GPUs" theory right? Why or why not?
- What do you recommend — which file, which line, and does the compute
  script need to change at all?
