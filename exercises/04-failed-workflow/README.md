# Exercise 04 — The workflow that fails

Runs on the same **AWS cloud cluster** as exercise 03, with its compute node
already up.

## The situation

A colleague turned a sensor report into an ACTIVATE workflow
(`workflow.yaml`): a Slurm job analyzes sensor readings on a compute node,
then the workflow publishes the charts as a browser session with
`pw endpoints serve`. It
worked on the cluster they built it on, but on the training cluster every run
fails within seconds, and no session ever appears. In their words: *"the cloud
node must not be up yet."*

Your job: find out why the run fails, using `pw code`'s built-in
**`diagnose-run`** skill, and propose the smallest fix.

## Ground rules

- Let the skill drive. It knows the `pw workflows runs` commands; your job is
  to read what it pulls, check that its conclusion follows from the evidence,
  and push back when it doesn't.
- **Work read-only.** Don't edit or rerun the workflow until you have a
  diagnosis.
- Don't read `workflow.yaml` first. Start from the failed run, the way you
  would with a run someone else launched.

## Getting started

Create and run the workflow in the ACTIVATE UI or with the `pw` CLI; both
produce the same run. The session demo uses the UI.

### In the ACTIVATE UI

1. Go to **Workflows** and create a new workflow named `ex04-report`.
2. Open its **Build** tab, replace the YAML with the contents of
   `workflow.yaml`, and **Save**.
3. Run the workflow: pick the training cluster, leave every other input at
   its default, and **Execute**.
4. Note the run slug (e.g. `swift-falcon-17`) on the run's page. The run
   fails within seconds.

### With the `pw` CLI

1. Save the workflow to your account, from this directory:

   ```bash
   pw workflows create --yaml workflow.yaml ex04-report
   ```

2. Run it on the training cluster with its default inputs, and note the run
   slug it prints:

   ```bash
   pw workflows run -i '{"resource": "pw://<cluster-name>"}' ex04-report
   ```

   The run fails within seconds.

### Diagnose it

In `pw code`, ask *"why did run `<slug>` fail?"*, or invoke the skill
directly with `/diagnose-run <slug>`. It doesn't matter whether the run was
started from the UI or the CLI.

### See it work

Once you've fixed the run, the report job takes a few seconds, and then the
charts are published: open the `report_<run slug>` session from **Sessions**
in ACTIVATE, or follow the URL in the **Serve report** step's log. It shows
hourly temperature and the average per sensor, and stays up for 30 minutes,
or until you cancel the run.

The workflow declares `permissions: ['*']`, which lets the run create the
endpoint session as you.

## Deliverable

- Why did the run fail? Quote the evidence the skill found: the failed job
  and step, and the log line.
- Is the "node isn't up yet" theory right? Why or why not?
- Where does the root cause live: the workflow's YAML, the inputs the run
  used, or the cluster? What's the fix, and what would you change so the next
  person doesn't hit it?
- Which `pw` commands did the skill run, and was any of them unnecessary?

## Facilitator setup

The training cluster must not have a partition named `render` (check with
`sinfo`). Run the workflow once with its defaults to confirm it fails within
seconds, and once with `partition` set to `default` to confirm the report
session opens with both charts.
