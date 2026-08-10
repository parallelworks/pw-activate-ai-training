# MCP servers

Three command-type (stdio) MCP servers, each a single FastMCP Python script
launched by `pw code` from the repo-root `.mcp.json`. Each is a long-running
process — spawned once per session, tools discovered at the handshake — and
together they cover the three access patterns the training contrasts:

| Server | Script | Reaches | Auth | Writes |
|---|---|---|---|---|
| `pw-commands` | `pw-commands.py` | Live cluster/scheduler state via the `pw` CLI | Inherits your `pw auth` identity | None — allowlisted read/scheduler commands only |
| `database` | `database.py` | Local `pw_training` Postgres | Credentials from `.env` | None — SELECT-only by construction |
| `backend-api` | `backend-api.py` | Curated `tickets` API over the same Postgres | Token validated against the DB on every call | Exactly one: `update_ticket_status` |

---

## pw-commands

The bridge to **live cluster state**: instead of pasting scheduler output
into a prompt, the agent queries the cluster itself and reasons from what
actually comes back.

Every tool shells out to the `pw` binary on PATH (120s default timeout).
Remote execution rides on `pw ssh <resource> <command>`, so the server needs
no host, key, or network configuration of its own — it inherits whatever
resources the authenticated `pw` user can already reach. No database or
`.env` dependency; just `pw` installed and authenticated (`pw auth`).

| Tool | Arguments | What it does |
|---|---|---|
| `list_clusters` | `status` (active/off/failed), `owned` (bool) | Lists clusters from `pw cluster ls -o json`, each with a `connected` flag |
| `check_cluster` | `name` | Reports whether one cluster is provisioned and active |
| `run_remote_command` | `resource`, `command`, `timeout` | Runs an **allowlisted** command on a remote resource via `pw ssh` |

**Safety model**: `run_remote_command` refuses any command whose first
binary is not in `ALLOWED_COMMANDS` (top of the script) — Slurm and
PBS/Torque scheduler commands plus read-only Linux basics (`ls`, `cat`,
`tail`, `df`, `grep`, `module`, ...). Nothing destructive (`rm`, `mv`,
`chmod`, editors, shells) is reachable, and every invocation is bounded by a
timeout.

*Try:* "Is the gpu partition busy right now?" · "Why is job 4242 still
pending? Check its Reason field first."

---

## database

**Read-only** SQL access to the local `pw_training` Postgres — the connector
pattern for operational data. Connection settings come exclusively from the
repo-root `.env` (names documented in `.env.example`; run
`scripts/setup_db.sh` to create and seed the database).

Although the server process is long-running, every tool call opens a fresh,
short-lived connection: `.env` is re-read each call, the connection is set
read-only with a 10-second statement timeout, and closed when the call
returns.

| Tool | Arguments | What it does |
|---|---|---|
| `list_tables` | — | Tables in the public schema with column counts |
| `describe_table` | `table` | Column names, types, nullability, defaults |
| `run_query` | `sql` | Runs a single read-only SELECT, capped at 200 rows |

**Safety model**: `run_query` enforces one statement only (no `;`-chaining),
first keyword `SELECT`/`WITH`, a 200-row cap — and beneath all that, the
connection itself is read-only, so even a clever bypass cannot write.

*Try:* "What tables exist, and what does `tickets` look like?" · "Which open
tickets have been untouched for more than 30 days?"

---

## backend-api

A **token-authenticated API** over the `tickets` dataset — the enterprise
shape: a curated surface whose every call is authenticated and whose single
write path is deliberately constrained.

On every tool call the server reads `API_TOKEN` from `.env` (re-read each
call, so swapping tokens takes effect immediately), hashes it (SHA-256, only
the hash is stored), looks it up in `api_tokens`, and rejects unknown,
expired, or revoked tokens — each with a distinct error. Any change is
attributed to the token's owner. The seed data includes an expired and a
revoked demo token so auth failures can be demonstrated live.

| Tool | Arguments | What it does |
|---|---|---|
| `whoami` | — | Who the configured token belongs to and when it expires |
| `get_ticket` | `ticket_id` | Full detail for one ticket |
| `search_tickets` | `status`, `assignee`, `urgency`, `category`, `unassigned`, `limit` | Filtered ticket list (max 100 rows) |
| `ticket_stats` | `group_by` | Counts per team/status/urgency/category/assignee |
| `update_ticket_status` | `ticket_id`, `status`, `note` | **The only mutation** — change one ticket's status |

**The safe-mutation demo**: `update_ticket_status` shows what *controlled*
write access looks like, in contrast to handing an agent raw SQL —
validated status values; one row addressed by primary key via a
parameterized query; a nonexistent id is an error and a same-status write is
an explicit no-op; `updated_at`/`resolved_at` maintained automatically; an
audit line (`status closed -> in_progress by attendee: <note>`) appended to
the ticket; and the before/after state returned for verification.

*Try:* "Who does my API token belong to?" · "Resolve ticket 84 with a note
explaining the switch firmware rollback."

---

## Logging (all servers)

Each script has an `ENABLE_LOGGING` boolean near the top (default `True`).
Every tool call — the input received and the output returned — is appended
as pretty-printed JSON to a sibling log file named after the script:
`pw-commands.logs`, `database.logs`, `backend-api.logs`. All gitignored via
`*.logs`.

Because each server is a long-running process loaded once per session,
toggling the boolean (or any script change) takes effect after a reconnect —
`/mcp` → server → Reconnect, or restart `pw code`.

Useful in the seminar for replaying exactly which queries a session issued,
and in what order, when reviewing an exercise.
