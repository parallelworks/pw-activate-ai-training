# pw-ai-training

Hands-on repo for the Applied AI seminar: using AI on real systems without
pretending it has read everything. Attendees drive `pw code` against **live
system state** through MCP tool connectors — a Slurm/PBS cluster via the `pw`
CLI, a local Postgres database, and a token-authenticated API — and practice
one discipline throughout: *pull the minimum live context that justifies an
action, and let that context, not a guess, drive whether and what to change.*

## What's in here

| Path | What it is |
|---|---|
| `mcp/pw-commands.py` | MCP server exposing the `pw` CLI: list clusters, check status, run allowlisted commands and transfer small files to remote hosts via `pw ssh` |
| `mcp/database.py` | MCP server with read-only access to the local `pw_training` Postgres database |
| `mcp/backend-api.py` | MCP server that authenticates every call with a token validated against the database, then serves the `tickets` dataset |
| `db/init.sql` | Schema + seed data: `api_tokens` and ~110 support tickets |
| `exercises/01-failed-gpu-job/` | A GPU job the scheduler won't run — diagnose it from the evidence |
| `exercises/02-oom-kill/` | A data job dies partway with no obvious error — find the one-line fix |
| `AGENTS.TEMPLATE.md` | Reference template for the repo's `AGENTS.md` — agent roster plus the secrets-are-off-limits policy; copy it to `AGENTS.md` to make it live |
| `credentials/` | Secrets directory used in the `AGENTS.md` demo — off-limits to AI sessions |
| `.env.example` | Every configuration variable name (values live in the gitignored `.env`) |
| `.mcp.json` | Registers the three MCP servers for `pw code` |

Note there is deliberately **no `AGENTS.md`** in this repo: creating it — and
watching a restarted `pw code` session start obeying it — is part of the
training. The repo ships **[`AGENTS.TEMPLATE.md`](AGENTS.TEMPLATE.md)** for
reference only — `pw code` ignores it under that name. Write your own during
the exercise, or, to see the effect immediately:

```bash
cp AGENTS.TEMPLATE.md AGENTS.md   # then restart `pw code`
```

## Prerequisites

> **Note:** This training has only been tested on Linux and macOS. Some
> scripts or commands might not be compatible with Windows.

- The `pw` CLI installed, on PATH, and authenticated (`pw auth`); verify with
  `pw cluster ls`. Installation and authentication steps are in the
  [PW CLI docs](https://parallelworks.com/docs/cli)
- Python 3.10+
- *(Optional)* A PostgreSQL database running locally that you can `createdb`
  against — only required for the `database` and `backend-api` MCP servers
- Access to an on-prem cluster on ACTIVATE

## Setup

```bash
# 1. Clone the repo and cd into it
git clone https://github.com/parallelworks/pw-activate-ai-training.git
cd pw-activate-ai-training

# 2. Create the virtual environment at .venv (this exact path — .mcp.json
#    launches the MCP servers with .venv/bin/python3) and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Create + seed the database; mints an API token into .env
bash scripts/setup_db.sh

# 4. Plant the fake secrets for the AGENTS.md demo (see AGENTS.TEMPLATE.md)
bash scripts/seed_credentials.sh
```

You never need to activate the venv: the MCP servers are launched through
`.venv/bin/python3` directly. (If you prefer an activated shell for your own
work, `source .venv/bin/activate` and plain `pip install -r requirements.txt`
does the same thing.)

`scripts/setup_db.sh` creates `.env` from `.env.example` on first run and
fills in `PG_USER` (your OS username) and a fresh `API_TOKEN` automatically.
If your Postgres needs a different role or a password, edit `PG_USER` /
`PG_PASSWORD` in `.env` and re-run the script — it is idempotent (drops and
recreates the database each time).

Then start `pw code` in the repo root. It picks up the three MCP servers from
`.mcp.json`:

- **pw-commands** — `list_clusters`, `check_cluster`, `run_remote_command`,
  `transfer_file_to_remote` (copies a small local file to a resource by
  base64-encoding it locally and decoding it remotely; 100 KB max by
  default, configurable via the `PW_MCP_MAX_TRANSFER_KB` environment
  variable)
- **database** — `list_tables`, `describe_table`, `run_query` (SELECT-only)
- **backend-api** — `whoami`, `get_ticket`, `search_tickets`, `ticket_stats`,
  `update_ticket_status` (every call re-validates the token; try `whoami`
  first). `update_ticket_status` is the one deliberate mutation in the whole
  setup: it demonstrates *safe* write access — validated status values, a
  single row addressed by primary key, `updated_at`/`resolved_at` maintained
  automatically, an audit line recording who changed what appended to the
  ticket, and the before/after state returned for verification.

The three servers are documented in detail in [`mcp/README.md`](mcp/README.md)
— tools, safety models, and logging, side by side.

All three servers work **out of the box**: once the Setup steps above are
done, `pw code` picks them up from `.mcp.json` automatically — no further
configuration needed. Just make sure you launch `pw code` **from the repo's
directory**: the config discovery and the relative paths in `.mcp.json`
(`.venv/bin/python3`, `mcp/*.py`) are resolved against the directory you
start it in, so the servers won't load from anywhere else. They are also plain FastMCP Python scripts, so they
double as templates: you can write your own MCP server the same way and add
it to `pw code` using either method below.

### Configuring MCP servers

Full documentation: <https://parallelworks.com/docs/ai/code/mcp>

**Option 1 — JSON config file.** This repo ships `.mcp.json` at the root, the
cross-tool standard location, so the servers work out of the box:

```json
{
  "mcpServers": {
    "pw-commands": {
      "command": ".venv/bin/python3",
      "args": ["mcp/pw-commands.py"]
    }
  }
}
```

`pw code` reads the first config file (highest priority first) whose
`mcpServers` map is non-empty — the winning file is used wholesale, they are
not merged:

1. `<workspace>/.agents/settings.local.json` — personal, per-project (gitignore it)
2. `<workspace>/.agents/settings.json` — shared project settings
3. `<workspace>/.mcp.json` — cross-tool standard (what this repo uses)
4. `~/.config/pw/code.json` — user-global

Note the priority order: if you add a server to a higher-priority file (e.g.
`.agents/settings.local.json`), that file replaces `.mcp.json` entirely, so
copy the three training servers along with it.

**Option 2 — command line.** `pw code mcp` manages the same files for you:

```bash
# Add a stdio (command-type) server; command goes after "--"
pw code mcp add my-server -- .venv/bin/python3 mcp/my-server.py

# Add with an environment variable
pw code mcp add -e API_KEY=secret my-server -- python3 server.py

# Add an HTTP server
pw code mcp add --transport http context7 https://mcp.context7.com/mcp

# Inspect / remove
pw code mcp list
pw code mcp get my-server
pw code mcp remove my-server

# Run with no arguments to be prompted for each value
pw code mcp add
```

By default `add` writes to `.agents/settings.local.json` (personal). Use
`--scope` to target a different file: `user` (`~/.config/pw/code.json`),
`project` (`.mcp.json`), `agents` (`.agents/settings.json`), or `local`.
Inside a running session, `/mcp` shows each server's status and lets you
reconnect after a config or script change.

Warm-up prompts: "who has the most open critical tickets?", "list unassigned
criticals", "is the gpu partition busy right now?" — and notice which server
each question *has* to go to.

### Tool-call logging

Each server has an `ENABLE_LOGGING` boolean near the top of its script
(default `True`). Every tool call — the input received and the output
returned — is recorded as JSON lines:

```
mcp/pw-commands.logs
mcp/database.logs
mcp/backend-api.logs
```

The log file sits next to its server script, named after it (the path is set
by `LOG_FILE` right below the boolean), and is gitignored via `*.logs`.
To turn logging off, set `ENABLE_LOGGING = False` and restart `pw code` (or
reconnect the server in `/mcp`). Entries are pretty-printed JSON, one per
tool-call input and output:

```json
{
  "ts": "2026-08-07T13:00:37.049996-05:00",
  "event": "input",
  "tool": "search_tickets",
  "args": [],
  "kwargs": {
    "urgency": "critical",
    "unassigned": true
  }
}
{
  "ts": "2026-08-07T13:00:37.066784-05:00",
  "event": "output",
  "tool": "search_tickets",
  "output": {
    "tickets": ["..."],
    "count": 4
  }
}
```

Useful in the seminar for replaying exactly which queries a session issued —
and in what order — when reviewing an exercise.

## The exercises

Each exercise directory has its own README with the scenario, ground rules,
and step-by-step instructions — read it before starting. Both exercises run
through `pw code` + the pw-commands server (with plain SSH as a fallback
when the MCP route gets stuck):

1. **[01 — the failed GPU job](exercises/01-failed-gpu-job/)** — a GPU job
   the scheduler won't run. The cluster isn't out of GPUs, and the fix is
   one line — in the right file. Needs `submit_sum.sh` and `sum_job.sh` on
   the cluster.
2. **[02 — the job that keeps dying](exercises/02-oom-kill/)** — it stops
   partway with no error in sight. Three pieces of evidence and a one-line
   fix. Needs `make_input.sh`, `process_data.sh`, and `submit_process.sh`
   on the cluster.

### Before you start

1. **Check the cluster is reachable**: `pw cluster ls` locally, or ask
   `pw code` to run `check_cluster` on the training cluster. The cluster
   must show as `active`/connected before anything else will work.
2. **Put the exercise files on the cluster.** The jobs are submitted *on*
   the cluster, so the exercise scripts must exist there first. Either:
   - ask `pw code` to copy them with the `transfer_file_to_remote` tool,
     e.g. *"transfer both scripts in exercises/01-failed-gpu-job/ to
     ~/01-failed-gpu-job/ on the training cluster"* (all the exercise
     scripts are well under the 100 KB cap),
   - or copy them yourself with `scp`:

     ```bash
     scp -r exercises/01-failed-gpu-job <user>@<cluster-address>:~/
     ```
3. Then follow the exercise's own README, starting with its
   "Getting started" section.
