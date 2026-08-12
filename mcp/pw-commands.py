#!/usr/bin/env python3
"""Parallel Works MCP server (FastMCP).

A Model Context Protocol server that exposes the `pw` CLI to an MCP client
(Claude Desktop, pw code, etc.). Built on the official MCP Python SDK's
FastMCP, so each tool is a plain decorated function.

Tools:
  - list_clusters            list clusters, optionally filtered by status/owner
  - check_cluster            check whether a single cluster is connected (active)
  - run_remote_command       run an allowlisted command on a resource via `pw ssh`
  - transfer_file_to_remote  copy a small local file (100 KB max) to a resource
                             by base64-encoding it and decoding it remotely

Requirements: Python 3.10+ and the `mcp` package (`pip install mcp`). The `pw`
CLI must be installed, on PATH, and authenticated (`pw auth`).

Wire it up in an MCP client with something like:

    {
      "mcpServers": {
        "pw-commands": {
          "command": "python3",
          "args": ["mcp/pw-commands.py"]
        }
      }
    }
"""

import base64
import functools
import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("pw-commands")

# Every tool call — the input received and the output returned — is logged
# as JSON lines to LOG_FILE (<server name>.logs next to this script). Set to
# False to disable.
ENABLE_LOGGING = True
LOG_FILE = Path(__file__).resolve().with_suffix(".logs")

# Seconds to wait before giving up on a `pw` invocation.
DEFAULT_TIMEOUT = 120

# transfer_file_to_remote: maximum local file size, in KB (default 100).
# Override with the PW_MCP_MAX_TRANSFER_KB environment variable. Every ~45 KB
# of file content costs one `pw ssh` round trip, so keep this small — beyond
# a few MB, use a real transfer tool (scp/rsync) instead.
MAX_TRANSFER_KB = int(os.environ.get("PW_MCP_MAX_TRANSFER_KB", "100"))
MAX_TRANSFER_BYTES = MAX_TRANSFER_KB * 1024

# Base64 characters sent per remote `echo`. Must be a multiple of 4 so each
# chunk decodes independently when appended, and must stay well under Linux's
# 128 KiB per-argument limit, because the whole remote command is passed to
# the local `pw` binary as a single argument.
TRANSFER_CHUNK_CHARS = 60_000

# run_command only permits these binaries: schedulers plus read-only basics.
ALLOWED_COMMANDS = {
    # Slurm
    "sinfo", "squeue", "sbatch", "scancel", "scontrol", "sacct",
    "salloc", "srun", "sstat", "sacctmgr", "sprio", "sshare",
    # PBS / Torque
    "qstat", "qsub", "qdel", "qhold", "qrls", "pbsnodes", "qmgr",
    # Read-only basic Linux commands
    "ls", "cat", "head", "tail", "less", "more", "stat", "file", "readlink",
    "pwd", "cd", "echo", "date", "hostname", "uname", "uptime", "whoami", "id",
    "groups", "who", "w", "env", "printenv", "df", "du", "free", "ps", "top",
    "wc", "which", "nproc", "lscpu", "lsblk", "lsmem", "find", "grep", "tree",
    "module", "quota", "base64",
    # Other useful commands
    "show_queues", "show_storage", "show_usage"
}


# ---------------------------------------------------------------------------
# Tool-call logging
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# pw CLI helpers
# ---------------------------------------------------------------------------


class PwError(Exception):
    """A `pw` invocation failed; message is safe to return to the client."""


def _run_pw(args, timeout=DEFAULT_TIMEOUT):
    """Run `pw <args...>` and return stdout. Raise PwError on failure."""
    if shutil.which("pw") is None:
        raise PwError("`pw` CLI not found on PATH. Install it and run `pw auth`.")
    cmd = ["pw", *args]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise PwError(f"`{' '.join(cmd)}` timed out after {timeout}s")
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise PwError(f"`{' '.join(cmd)}` exited {proc.returncode}: {detail}")
    return proc.stdout


def _list_clusters(status=None, owned=False):
    """Return the parsed list of clusters from `pw cluster ls -o json`."""
    args = ["cluster", "ls", "-o", "json"]
    if status:
        args += ["--status", status]
    if owned:
        args.append("--owned")
    out = _run_pw(args)
    try:
        return json.loads(out or "[]")
    except json.JSONDecodeError as e:
        raise PwError(f"could not parse `pw cluster ls` output: {e}")


def _clean_command(command):
    """Strip one layer of surrounding matched quotes a caller may have added."""
    c = command.strip()
    if len(c) >= 2 and c[0] == c[-1] and c[0] in "\"'":
        c = c[1:-1]
    return c


def _ssh_run(resource, command, timeout):
    """Run `command` on `resource` via `pw ssh` and return combined output."""
    # Pass the command as one arg (like a quoted shell command) so it isn't
    # re-split; `--` stops pw ssh's flag parser in case the command starts with a dash.
    args = ["ssh", resource, command]
    return _run_pw(args, timeout=timeout)


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
@logged
def list_clusters(status: str | None = None, owned: bool = False) -> str:
    """List Parallel Works clusters.

    Each entry includes a `connected` flag (true when the cluster's provision
    status is 'active').

    Args:
        status: Filter by status, e.g. 'active', 'off', 'failed'.
        owned: Only clusters owned by the authenticated user.
    """
    clusters = _list_clusters(status=status, owned=owned)
    if not clusters:
        return "No clusters found."
    rows = [
        {
            "name": c.get("name"),
            "displayName": c.get("displayName") or None,
            "status": c.get("status"),
            "connected": c.get("status") == "active",
            "schedulerType": c.get("schedulerType"),
            "type": c.get("type"),
            "csp": c.get("csp"),
            "activeNodes": c.get("activeNodes"),
            "maxNodes": c.get("maxNodes"),
            "ipAddress": c.get("ipAddress") or None,
        }
        for c in clusters
    ]
    return json.dumps(rows, indent=2)


@mcp.tool()
@logged
def check_cluster(name: str) -> str:
    """Check whether a specific cluster is connected (provisioned and active).

    Args:
        name: Cluster name.
    """
    match = next(
        (c for c in _list_clusters() if name in (c.get("name"), c.get("displayName"), c.get("id"))),
        None,
    )
    if match is None:
        return json.dumps({"name": name, "found": False, "connected": False})
    return json.dumps(
        {
            "name": match.get("name"),
            "found": True,
            "status": match.get("status"),
            "connected": match.get("status") == "active",
            "schedulerType": match.get("schedulerType"),
            "activeNodes": match.get("activeNodes"),
            "maxNodes": match.get("maxNodes"),
        },
        indent=2,
    )


@mcp.tool()
@logged
def run_remote_command(resource: str, command: str, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run a command on a remote resource (cluster, workspace) via `pw ssh`.

    The resource must be running and connected. Only allowlisted binaries are
    permitted: Slurm/PBS scheduler commands (sinfo, squeue, sbatch, scancel,
    sacct, qstat, qsub, qdel, pbsnodes, ...) and read-only basic Linux commands
    (ls, cat, df, hostname, uname, echo, ...).

    Args:
        resource: Resource name or pw:// URI (e.g. 'my-cluster', 'workspace').
        command: Command to run on the remote host, e.g. 'squeue -u $USER'.
        timeout: Seconds before giving up.
    """
    command = _clean_command(command)
    binary = shlex.split(command)[0] if command.strip() else ""
    if binary not in ALLOWED_COMMANDS:
        raise PwError(
            f"`{binary}` is not an allowed command. "
            f"Allowed: {', '.join(sorted(ALLOWED_COMMANDS))}"
        )
    out = _ssh_run(resource, command, timeout)
    return out.strip() or "(no output)"


@mcp.tool()
@logged
def transfer_file_to_remote(
    resource: str, local_path: str, remote_path: str, timeout: int = DEFAULT_TIMEOUT
) -> str:
    """Transfer a small local file to a remote resource via `pw ssh`.

    The file (at most MAX_TRANSFER_KB, default 100 KB) is base64-encoded
    locally, echoed to the remote host in chunks, and decoded into
    `remote_path` with `base64 -d`. Both `echo` and `base64` must be in this
    server's allowlist and present on the remote host; if either is not
    allowed or not found, the output says so explicitly.

    Args:
        resource: Resource name or pw:// URI (e.g. 'my-cluster', 'workspace').
        local_path: Path of the local file to send.
        remote_path: Destination file path on the remote host.
        timeout: Seconds before giving up on each remote command.
    """
    path = Path(local_path).expanduser()
    if not path.is_file():
        raise PwError(f"local file not found: {path}")
    size = path.stat().st_size
    if size > MAX_TRANSFER_BYTES:
        raise PwError(
            f"{path} is {size:,} bytes; transfer_file_to_remote supports at most "
            f"{MAX_TRANSFER_BYTES:,} bytes ({MAX_TRANSFER_KB} KB). "
            "Raise the limit with the PW_MCP_MAX_TRANSFER_KB environment variable."
        )

    not_allowed = sorted(b for b in ("echo", "base64") if b not in ALLOWED_COMMANDS)
    if not_allowed:
        return json.dumps(
            {
                "success": False,
                "error": "required binaries are not in this server's ALLOWED_COMMANDS: "
                + ", ".join(not_allowed),
            },
            indent=2,
        )
    try:
        _ssh_run(resource, "which echo base64", timeout)
    except PwError as e:
        return json.dumps(
            {
                "success": False,
                "error": "`echo` and/or `base64` not found on the remote host; cannot transfer",
                "detail": str(e),
            },
            indent=2,
        )

    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    dest = shlex.quote(remote_path)
    chunks = 0
    if not encoded:  # empty file: just (re)create the destination
        _ssh_run(resource, f"echo -n > {dest}", timeout)
    else:
        for start in range(0, len(encoded), TRANSFER_CHUNK_CHARS):
            redirect = ">" if start == 0 else ">>"
            chunk = encoded[start : start + TRANSFER_CHUNK_CHARS]
            _ssh_run(resource, f"echo {chunk} | base64 -d {redirect} {dest}", timeout)
            chunks += 1

    remote_size = None
    try:
        remote_size = int(_ssh_run(resource, f"wc -c < {dest}", timeout).strip())
    except (PwError, ValueError):
        pass

    return json.dumps(
        {
            "success": remote_size == size if remote_size is not None else True,
            "resource": resource,
            "local_path": str(path),
            "remote_path": remote_path,
            "bytes_sent": size,
            "remote_bytes": remote_size if remote_size is not None else "(verification failed)",
            "chunks": chunks,
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
