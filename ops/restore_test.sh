#!/usr/bin/env bash
# Prove the latest backup can be restored: load it into a scratch database,
# compare row counts with the live one, then drop the scratch copy.
# Exits non-zero if the restore fails or the counts look wrong, so cron can alert.
# Needs a login allowed to create databases: set RESTORE_ADMIN_URL in .env
# (otherwise DATABASE_URL is used).
set -euo pipefail
cd "$(dirname "$0")/.."
eval "$(python3 -m kit.pgenv)"
LIVE_DB="$PGDATABASE"
DIR="${BACKUP_DIR:-backups}"
FILE="${1:-$(ls -t "$DIR"/hub-*.sql.gz 2>/dev/null | head -1)}"
[ -f "$FILE" ] || { echo "no backup file found in $DIR"; exit 1; }
SCRATCH="hub_restore_test_$$"
if python3 -m kit.pgenv RESTORE_ADMIN_URL >/dev/null 2>&1; then
  ADMIN_ENV="$(python3 -m kit.pgenv RESTORE_ADMIN_URL)"
else
  ADMIN_ENV="$(python3 -m kit.pgenv)"
fi
admin() { ( eval "$ADMIN_ENV"; "$@" ); }

echo "restoring $FILE into $SCRATCH"
admin psql -q -d postgres -c "CREATE DATABASE $SCRATCH"
trap 'admin psql -q -d postgres -c "DROP DATABASE IF EXISTS $SCRATCH"' EXIT
gunzip -c "$FILE" | admin psql -q -v ON_ERROR_STOP=1 -d "$SCRATCH" >/dev/null

Q="SELECT 'crm.opportunities', count(*) FROM crm.opportunities UNION ALL
   SELECT 'crm.opportunity_history', count(*) FROM crm.opportunity_history UNION ALL
   SELECT 'acct.invoices', count(*) FROM acct.invoices UNION ALL
   SELECT 'core.app_users', count(*) FROM core.app_users"
RESTORED="$(admin psql -At -d "$SCRATCH" -c "$Q")"
LIVE="$(psql -At -d "$LIVE_DB" -c "$Q")"
echo "table | restored | live"
paste -d'|' <(echo "$RESTORED") <(echo "$LIVE" | cut -d'|' -f2)

# Pass if every table restored with rows, and within 5% of live (a sync may have run since the backup).
python3 - "$RESTORED" "$LIVE" <<'PY'
import sys
restored = dict(l.split("|") for l in sys.argv[1].splitlines())
live = dict(l.split("|") for l in sys.argv[2].splitlines())
bad = [t for t, n in restored.items() if int(n) == 0 or abs(int(n) - int(live[t])) > 0.05 * max(int(live[t]), 1)]
if bad:
    print("RESTORE TEST FAILED: counts wrong for", ", ".join(bad)); sys.exit(1)
print("restore test passed")
PY
