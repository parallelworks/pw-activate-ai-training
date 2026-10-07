# Exercise 03 — The file that's right there

Runs on an **AWS cloud cluster** on ACTIVATE.

> **The compute node is already up.** Cloud clusters start compute nodes on
> demand, and a cold start takes several minutes. Your facilitator started
> the training cluster and a compute node before the session, so `sinfo`
> should show it `idle`, not `idle~` (powered off). Jobs start in seconds.
> If you see `idle~` or `alloc#`, tell your facilitator instead of waiting.

## The situation

A colleague staged today's sensor readings on the cluster with
`stage_input.sh`, then submitted `submit_analyze.sh`. The job failed in
seconds, complaining it can't open the input file. In their words: *"the file
is right there — I can `ls` it. The cluster must be broken."*

Your job: find out why the job can't see a file the colleague can see, using
evidence from the live cluster, and propose the smallest fix.

## Ground rules

- Work inside `pw code`, preferring the **pw-commands** MCP server. SSHing
  into the cluster and running the same commands by hand is a fine fallback.
- **Justify every query before you run it.** What do you expect it to tell
  you? What decision does it feed?
- Don't assume the machine you're logged into and the machine the job ran on
  see the same files. Check.

## Getting started

1. Put the four scripts in `~/03-missing-input/` on the cluster (see
   "Before you start" in the repo README).
2. On the cluster, in that directory, stage the input (a few seconds):
   `bash stage_input.sh`
3. Submit the job: `sbatch submit_analyze.sh`, wait for it to fail, then
   investigate.

Tip: `run_remote_command` runs on the cluster's login node. To look at a
compute node, go through the scheduler, e.g. `srun -w <node> ls <path>`.

## Deliverable

- Why can't the job open the file? Quote the evidence: the error, where the
  job ran, and what each machine sees at that path.
- Which paths are shared between the login node and the compute nodes, and
  how did you tell?
- The one-line fix, as a diff. Does any script besides that one need to
  change?

## Facilitator setup

Before the session:

1. Start an AWS cluster on ACTIVATE and confirm `/home` is shared and `/tmp`
   is not: on the login node and through `srun df -h ~ /tmp`, `~` should be
   the same network mount (e.g. `<cluster>-mgmt:/home`) and `/tmp` a local
   disk.
2. Bring up a compute node: submit a placeholder job
   (`sbatch --wrap hostname`) and wait for `sinfo` to show the node `idle` or
   `mix` instead of `idle~` or `#`. A cold start takes several minutes.
3. Check the node stays up: `scontrol show partition` should show
   `SuspendTime=INFINITE`. If it shows a number of seconds, the node powers
   off after that long idle; raise it for the session.
4. Run the exercise end to end once: the job should fail because it cannot
   open the input file, and pass after the fix.
