# Exercise 04 — The workflow that fails

Runs on the same **AWS cloud cluster** as exercise 03, with its compute node
already up.

## The situation

A colleague turned a frame-rendering job into an ACTIVATE workflow
(`workflow.yaml`). It worked when they tried it, but now every run fails
partway through. In their words: *"the cloud node must be getting reclaimed."*

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

1. Save the workflow to your account, from this directory:

   ```bash
   pw workflows create --yaml workflow.yaml ex04-render
   ```

2. Run it on the training cluster with its default inputs, and note the run
   slug it prints (e.g. `swift-falcon-17`):

   ```bash
   pw workflows run -i '{"resource": "pw://<cluster-name>"}' ex04-render
   ```

   The run takes about two minutes to fail.

3. In `pw code`, ask *"why did run `<slug>` fail?"*, or invoke the skill
   directly with `/diagnose-run <slug>`.

## Deliverable

- Why did the run fail? Quote the evidence the skill found: the failed job
  and step, the log line, and the scheduler state.
- Is the "node got reclaimed" theory right? Why or why not?
- Where does the root cause live: the workflow's YAML, the inputs the run
  used, or the cluster? What's the fix, and what would you change so the next
  person doesn't hit it?
- Which `pw` commands did the skill run, and was any of them unnecessary?
