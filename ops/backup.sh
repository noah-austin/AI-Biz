#!/usr/bin/env bash
# Nightly database backup. Verifies each file before deleting anything older
# than KEEP_DAYS, copies off-site if OFFSITE_CMD is set, and records the result
# in core.sync_state so the Health page and alerts can see it.
#
#   ops/backup.sh            nightly run (from cron)
#   ops/backup.sh before-x   tagged manual backup before a big change (kept forever)
set -euo pipefail
cd "$(dirname "$0")/.."
eval "$(python3 -m kit.pgenv)"     # reads .env safely; password goes in the environment, not on the command line
DIR="${BACKUP_DIR:-backups}"; KEEP_DAYS="${KEEP_DAYS:-14}"
mkdir -p "$DIR"; chmod 700 "$DIR"
TAG="${1:-nightly}"
if [[ ! "$TAG" =~ ^[A-Za-z0-9_-]{1,40}$ ]]; then echo "tag must be letters, numbers, - or _"; exit 2; fi
FILE="$DIR/hub-$(date -u +%Y%m%dT%H%M%SZ)-$TAG.sql.gz"

record() {  # status, message
  psql -q -v ON_ERROR_STOP=1 -v st="$1" -v msg="$2" <<'SQL' || true
INSERT INTO core.sync_state (object, source, last_attempt_at, last_success_at, last_status, last_message)
VALUES ('backup', 'pg_dump', now(), CASE WHEN :'st' = 'ok' THEN now() END, :'st', :'msg')
ON CONFLICT (object) DO UPDATE SET last_attempt_at = now(),
  last_success_at = CASE WHEN :'st' = 'ok' THEN now() ELSE core.sync_state.last_success_at END,
  last_status = EXCLUDED.last_status, last_message = EXCLUDED.last_message;
SQL
}
trap 'record failed "backup failed at line $LINENO"' ERR

pg_dump --no-owner | gzip -9 > "$FILE"
gzip -t "$FILE"                                   # verify before trusting it
chmod 600 "$FILE"
SIZE=$(du -h "$FILE" | cut -f1)

if [ -n "${OFFSITE_CMD:-}" ]; then                # e.g. "aws s3 cp {} s3://client-backups/hub/"
  # OFFSITE_CMD comes from the root-only .env; {} is replaced by the (validated) backup file name.
  eval "${OFFSITE_CMD//\{\}/\"$FILE\"}"
  OFF=", copied off-site"
else
  OFF=", NOT copied off-site (set OFFSITE_CMD)"
fi

if [ "$TAG" = nightly ]; then                     # only prune nightly files, never tagged ones
  find "$DIR" -name 'hub-*-nightly.sql.gz' -mtime +"$KEEP_DAYS" -delete
fi
record ok "$(basename "$FILE") ($SIZE)$OFF"
echo "backup ok: $FILE ($SIZE)$OFF"
