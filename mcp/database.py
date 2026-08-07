#!/usr/bin/env python3
"""Postgres MCP server (FastMCP).

Read-only access to the local `pw_training` Postgres database. Connection
settings come from the repo-root `.env` file — never hardcoded in this file.
Copy `.env.example` to `.env` and run `scripts/setup_db.sh` first.

Tools:
  - list_tables       tables in the public schema
  - describe_table    column names and types for one table
  - run_query         run a single read-only SELECT (row-limited)
"""

import functools
import json
import os
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("database")

# Every tool call — the input received and the output returned — is logged
# as JSON lines to LOG_FILE (<server name>.logs next to this script). Set to
# False to disable.
ENABLE_LOGGING = True
LOG_FILE = Path(__file__).resolve().with_suffix(".logs")

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env"

MAX_ROWS = 200
STATEMENT_TIMEOUT_MS = 10_000


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


class DbError(Exception):
    """A database problem; message is safe to return to the client."""


def _connect():
    """Open a read-only connection using settings from .env."""
    if not ENV_FILE.exists():
        raise DbError(
            "missing .env at the repo root. Copy .env.example to .env and run "
            "scripts/setup_db.sh. Variable names are documented in .env.example."
        )
    load_dotenv(ENV_FILE, override=True)
    missing = [k for k in ("PG_HOST", "PG_PORT", "PG_DATABASE", "PG_USER") if not os.getenv(k)]
    if missing:
        raise DbError(f".env is missing: {', '.join(missing)} (see .env.example)")
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
        raise DbError(f"could not connect to Postgres: {e}")
    conn.read_only = True
    conn.execute(f"SET statement_timeout = {STATEMENT_TIMEOUT_MS}")
    return conn


def _rows_to_json(rows, truncated):
    payload = {"rows": rows, "count": len(rows)}
    if truncated:
        payload["note"] = f"output truncated to {MAX_ROWS} rows; add filters or LIMIT"
    return json.dumps(payload, indent=2, default=str)


@mcp.tool()
@logged
def list_tables() -> str:
    """List tables in the public schema of the training database."""
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT table_name,
                   (SELECT count(*) FROM information_schema.columns c
                    WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columns
            FROM information_schema.tables t
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        ).fetchall()
    return _rows_to_json(rows, truncated=False)


@mcp.tool()
@logged
def describe_table(table: str) -> str:
    """Show column names, types, and nullability for one table.

    Args:
        table: Table name in the public schema, e.g. 'tickets'.
    """
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        ).fetchall()
    if not rows:
        raise DbError(f"no table named '{table}' in the public schema (try list_tables)")
    return _rows_to_json(rows, truncated=False)


@mcp.tool()
@logged
def run_query(sql: str) -> str:
    """Run a single read-only SELECT (or WITH ... SELECT) query.

    Results are capped at 200 rows. Anything other than one SELECT statement
    is rejected; the connection is read-only and statement-timeout protected.

    Args:
        sql: The query, e.g. "SELECT status, count(*) FROM tickets GROUP BY 1".
    """
    stmt = sql.strip().rstrip(";").strip()
    if not stmt:
        raise DbError("empty query")
    if ";" in stmt:
        raise DbError("only a single statement is allowed")
    if stmt.split(None, 1)[0].lower() not in ("select", "with"):
        raise DbError("only SELECT/WITH queries are allowed")
    with _connect() as conn:
        cur = conn.execute(stmt)
        rows = cur.fetchmany(MAX_ROWS)
        truncated = cur.fetchone() is not None
    return _rows_to_json(rows, truncated)


if __name__ == "__main__":
    mcp.run()
