#!/usr/bin/env python3
"""Backend API MCP server (FastMCP).

Serves the training `tickets` dataset — but only to an authenticated caller.
Every tool call validates API_TOKEN (from the repo-root `.env`) against the
`api_tokens` table in the local Postgres database: the stored value is a
SHA-256 hash, and a token can be expired or revoked server-side, at which
point these tools stop working immediately.

Run `scripts/setup_db.sh` to create the database and mint a token into `.env`.

Tools:
  - whoami           who the current token belongs to
  - get_ticket       full detail for one ticket
  - search_tickets   filter by status / assignee / urgency / category
  - ticket_stats     counts grouped by team, status, urgency, category, or assignee
"""

import functools
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("backend-api")

# Every tool call — the input received and the output returned — is logged
# as JSON lines to LOG_FILE (<server name>.logs next to this script). Set to
# False to disable.
ENABLE_LOGGING = True
LOG_FILE = Path(__file__).resolve().with_suffix(".logs")

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"


def _unescape(value):
    """Parse a JSON-encoded string so logs show structure, not escaped text."""
    if isinstance(value, str) and value.lstrip()[:1] in ("{", "["):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    return value


def _log(event, payload):
    if not ENABLE_LOGGING:
        return
    entry = {"ts": datetime.now().astimezone().isoformat(), "event": event, **payload}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, indent=2, default=str) + "\n")


def logged(fn):
    """Log a tool's input and output when ENABLE_LOGGING is True."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        _log("input", {"tool": fn.__name__, "args": list(args), "kwargs": kwargs})
        try:
            result = fn(*args, **kwargs)
        except Exception as e:
            _log("error", {"tool": fn.__name__, "error": str(e)})
            raise
        _log("output", {"tool": fn.__name__, "output": _unescape(result)})
        return result

    return wrapper

STATEMENT_TIMEOUT_MS = 10_000
MAX_ROWS = 100

TICKET_COLUMNS = (
    "id, title, description, reporter, assignee, team, status, urgency, "
    "category, created_at, updated_at, resolved_at"
)
GROUPABLE = {"team", "status", "urgency", "category", "assignee"}


class ApiError(Exception):
    """An API problem; message is safe to return to the client."""


def _connect():
    if not ENV_FILE.exists():
        raise ApiError(
            "missing .env at the repo root. Copy .env.example to .env and run "
            "scripts/setup_db.sh."
        )
    load_dotenv(ENV_FILE, override=True)
    missing = [k for k in ("PG_HOST", "PG_PORT", "PG_DATABASE", "PG_USER") if not os.getenv(k)]
    if missing:
        raise ApiError(f".env is missing: {', '.join(missing)} (see .env.example)")
    try:
        conn = psycopg.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            dbname=os.getenv("PG_DATABASE"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD") or None,
            row_factory=dict_row,
            connect_timeout=5,
        )
    except psycopg.OperationalError as e:
        raise ApiError(f"could not connect to Postgres: {e}")
    conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
    return conn


def _authenticate(conn):
    """Validate API_TOKEN against api_tokens; return the token row."""
    token = os.getenv("API_TOKEN", "").strip()
    if not token:
        raise ApiError("no API_TOKEN in .env — run scripts/setup_db.sh to mint one")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = conn.execute(
        """
        SELECT owner, expires_at, revoked, (expires_at < now()) AS expired
        FROM api_tokens WHERE token_hash = %s
        """,
        (token_hash,),
    ).fetchone()
    if row is None:
        raise ApiError("authentication failed: unknown token")
    if row["revoked"]:
        raise ApiError(f"authentication failed: token for '{row['owner']}' has been revoked")
    if row["expired"]:
        raise ApiError(
            f"authentication failed: token for '{row['owner']}' expired at {row['expires_at']}"
        )
    return row


def _json(data):
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
@logged
def whoami() -> str:
    """Show who the configured API token belongs to and when it expires."""
    with _connect() as conn:
        row = _authenticate(conn)
    return _json({"owner": row["owner"], "expires_at": row["expires_at"], "authenticated": True})


@mcp.tool()
@logged
def get_ticket(ticket_id: int) -> str:
    """Fetch one ticket with full detail.

    Args:
        ticket_id: The ticket id, e.g. 42.
    """
    with _connect() as conn:
        _authenticate(conn)
        row = conn.execute(
            f"SELECT {TICKET_COLUMNS} FROM tickets WHERE id = %s", (ticket_id,)
        ).fetchone()
    if row is None:
        raise ApiError(f"no ticket with id {ticket_id}")
    return _json(row)


@mcp.tool()
@logged
def search_tickets(
    status: str | None = None,
    assignee: str | None = None,
    urgency: str | None = None,
    category: str | None = None,
    unassigned: bool = False,
    limit: int = 25,
) -> str:
    """Search tickets by any combination of filters.

    Args:
        status: open, in_progress, blocked, resolved, or closed.
        assignee: Username, e.g. 'mchen'.
        urgency: low, medium, high, or critical.
        category: access-request, hardware, software, network, or billing.
        unassigned: Only tickets with no assignee (overrides `assignee`).
        limit: Max rows to return (default 25, cap 100).
    """
    clauses, params = [], []
    for col, val in (("status", status), ("urgency", urgency), ("category", category)):
        if val:
            clauses.append(f"{col} = %s")
            params.append(val)
    if unassigned:
        clauses.append("assignee IS NULL")
    elif assignee:
        clauses.append("assignee = %s")
        params.append(assignee)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = max(1, min(int(limit), MAX_ROWS))
    with _connect() as conn:
        _authenticate(conn)
        rows = conn.execute(
            f"""
            SELECT {TICKET_COLUMNS} FROM tickets {where}
            ORDER BY created_at DESC LIMIT {limit}
            """,
            params,
        ).fetchall()
    return _json({"tickets": rows, "count": len(rows)})


@mcp.tool()
@logged
def ticket_stats(group_by: str = "status") -> str:
    """Ticket counts grouped by one dimension.

    Args:
        group_by: One of team, status, urgency, category, assignee.
    """
    if group_by not in GROUPABLE:
        raise ApiError(f"group_by must be one of: {', '.join(sorted(GROUPABLE))}")
    with _connect() as conn:
        _authenticate(conn)
        rows = conn.execute(
            f"""
            SELECT coalesce({group_by}::text, '(none)') AS {group_by},
                   count(*) AS total,
                   count(*) FILTER (WHERE status NOT IN ('resolved', 'closed')) AS open_like
            FROM tickets GROUP BY 1 ORDER BY total DESC
            """
        ).fetchall()
    return _json({"group_by": group_by, "stats": rows})


if __name__ == "__main__":
    mcp.run()
