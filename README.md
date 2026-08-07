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
| `mcp/pw-commands.py` | MCP server exposing the `pw` CLI: list clusters, check status, run allowlisted commands on remote hosts via `pw ssh` |
| `mcp/database.py` | MCP server with read-only access to the local `pw_training` Postgres database |
| `mcp/backend-api.py` | MCP server that authenticates every call with a token validated against the database, then serves the `tickets` dataset |
| `db/init.sql` | Schema + seed data: `api_tokens` and ~110 support tickets |
| `exercises/01-stuck-gpu-job/` | A GPU job pends for an hour on a "half-empty" cluster — diagnose it |
| `exercises/02-oom-kill/` | A data job dies partway with no obvious error — find the one-line fix |
| `credentials/` | Secrets directory used in the AGENTS.md demo — off-limits to AI sessions |
| `.env.example` | Every configuration variable name (values live in the gitignored `.env`) |
| `.mcp.json` | Registers the three MCP servers for `pw code` |

Note there is deliberately **no `AGENTS.md`** in this repo: creating it — and
watching a restarted `pw code` session start obeying it — is part of the
training.

## Prerequisites

- The `pw` CLI installed, on PATH, and authenticated (`pw auth`); verify with
  `pw cluster ls`. Installation and authentication steps are in the
  [PW CLI docs](https://parallelworks.com/docs/cli)
- Python 3.10+
- A local Postgres server you can `createdb` against
- Access to a training cluster on ACTIVATE

## Setup

```bash
# 1. Create the virtual environment at .venv (this exact path — .mcp.json
#    launches the MCP servers with .venv/bin/python3) and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Create + seed the database; mints an API token into .env
bash scripts/setup_db.sh

# 3. Plant the fake secrets for the AGENTS.md demo
bash scripts/seed_credentials.sh
```

You never need to activate the venv: the MCP servers are launched through
`.venv/bin/python3` directly. (If you prefer an activated shell for your own
work, `source .venv/bin/activate` and plain `pip install -r requirements.txt`
does the same thing.)

Then start `pw code` in the repo root. It picks up the three MCP servers from
`.mcp.json`:

- **pw-commands** — `list_clusters`, `check_cluster`, `run_remote_command`
- **database** — `list_tables`, `describe_table`, `run_query` (SELECT-only)
- **backend-api** — `whoami`, `get_ticket`, `search_tickets`, `ticket_stats`
  (every call re-validates the token; try `whoami` first)

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

Each exercise directory has its own README with the scenario and ground
rules. Both run entirely through `pw code` + the pw-commands server:

1. **[01 — the stuck GPU job](exercises/01-stuck-gpu-job/)** — the queue
   looks broken; the scheduler says otherwise. Sometimes the right move is no
   code change at all.
2. **[02 — the job that keeps dying](exercises/02-oom-kill/)** — worked last
   week, dies today. Three pieces of evidence and a one-line fix.

Facilitators: solutions, tuning knobs, and demo scripts are kept out of this
repo — ask the training team for the facilitator guide.
