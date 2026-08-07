#!/usr/bin/env bash
# Create and seed the pw_training database, then mint a fresh API token into .env.
# Idempotent: safe to re-run (drops and recreates the database).
set -euo pipefail
cd "$(dirname "$0")/.."

ENV_FILE=.env
[ -f "$ENV_FILE" ] || { cp .env.example "$ENV_FILE"; echo "Created .env from .env.example"; }

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

export PGHOST="${PG_HOST:-localhost}"
export PGPORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-$USER}"
export PGUSER="$PG_USER"
# Persist the resolved role so the MCP servers read the same one.
if grep -q '^PG_USER=$' "$ENV_FILE"; then
    tmp=$(mktemp)
    awk -v u="$PG_USER" '{ sub(/^PG_USER=$/, "PG_USER=" u); print }' "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
fi
[ -n "${PG_PASSWORD:-}" ] && export PGPASSWORD="$PG_PASSWORD"
DB="${PG_DATABASE:-pw_training}"

dropdb --if-exists "$DB"
createdb "$DB"
psql -q -v ON_ERROR_STOP=1 -d "$DB" -f db/init.sql

# Mint the live token: plaintext goes only into .env, the DB stores its hash.
TOKEN="pwtrain_$(openssl rand -hex 24)"
HASH=$(printf '%s' "$TOKEN" | shasum -a 256 | awk '{print $1}')
psql -q -v ON_ERROR_STOP=1 -d "$DB" \
    -c "INSERT INTO api_tokens (token_hash, owner, expires_at) VALUES ('$HASH', 'attendee', now() + interval '30 days');"

if grep -q '^API_TOKEN=' "$ENV_FILE"; then
    tmp=$(mktemp)
    awk -v t="$TOKEN" '{ if (sub(/^API_TOKEN=.*/, "API_TOKEN=" t)) done=1; print } END { if (!done) print "API_TOKEN=" t }' \
        "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
else
    printf 'API_TOKEN=%s\n' "$TOKEN" >> "$ENV_FILE"
fi

echo "Database '$DB' created and seeded:"
psql -d "$DB" -tAc "SELECT '  ' || count(*) || ' tickets, ' || count(DISTINCT coalesce(assignee, '(none)')) || ' assignees' FROM tickets;"
psql -d "$DB" -tAc "SELECT '  ' || count(*) || ' api tokens (1 live, 1 expired, 1 revoked)' FROM api_tokens;"
echo "A fresh API token was written to .env (owner: attendee, expires in 30 days)."
echo "The token is not printed here on purpose."
