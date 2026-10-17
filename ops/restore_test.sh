#!/usr/bin/env bash
# Prove the latest backup can be restored: load it into a scratch database,
# compare row counts with the live one, then drop the scratch copy.
# Needs a login allowed to create databases (run as the postgres user on the server).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; [ -f .env ] && . ./.env; set +a
DIR="${BACKUP_DIR:-backups}"
FILE="${1:-$(ls -t "$DIR"/hub-*.sql.gz | head -1)}"
SCRATCH="hub_restore_test_$$"
ADMIN_URL="${RESTORE_ADMIN_URL:-$DATABASE_URL}"
echo "restoring $FILE into $SCRATCH"
psql "$ADMIN_URL" -q -c "CREATE DATABASE $SCRATCH"
trap 'psql "$ADMIN_URL" -q -c "DROP DATABASE IF EXISTS $SCRATCH"' EXIT
SCRATCH_URL="${ADMIN_URL%/*}/$SCRATCH"
gunzip -c "$FILE" | psql "$SCRATCH_URL" -q -v ON_ERROR_STOP=1 >/dev/null
Q="SELECT 'crm.opportunities', count(*) FROM crm.opportunities UNION ALL SELECT 'crm.opportunity_history', count(*) FROM crm.opportunity_history
   UNION ALL SELECT 'acct.invoices', count(*) FROM acct.invoices UNION ALL SELECT 'core.app_users', count(*) FROM core.app_users"
diff <(psql "$SCRATCH_URL" -At -c "$Q") <(psql "$DATABASE_URL" -At -c "$Q") \
  && echo "restore test passed: row counts match" \
  || echo "row counts differ (normal if a sync ran since the backup); check the numbers above"
psql "$SCRATCH_URL" -At -c "$Q"
