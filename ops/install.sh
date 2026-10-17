#!/usr/bin/env bash
# One-command setup for a hub server (Ubuntu 24.04). Safe to re-run.
#
#   sudo ops/install.sh server                              # once per server: packages, firewall, Python, web server
#   sudo ops/install.sh add NAME CLIENT_DIR PORT [HOST]     # add an install, e.g. add company clients/company 8001 auto
#   sudo ops/install.sh update                              # pull the code, upgrade every install, restart, check
#   ops/install.sh list                                     # what's installed and whether it's running
#
# HOST is the web address for the install: a real domain (hub.example.com), "auto" for a free
# <name>.<ip>.sslip.io address with real HTTPS, or leave it out to reach it only from the server.
#
# Each install gets its own database, database logins, settings file (/etc/hub/NAME.env, owner-only),
# systemd service (hub-NAME), scheduled jobs (/etc/cron.d/hub-NAME) and web address (Caddy, automatic HTTPS).
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
RUN_USER="${RUN_USER:-$(stat -c %U "$REPO")}"
HUB_ETC="${HUB_ETC:-/etc/hub}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/backups/hub}"
LOG_DIR="${LOG_DIR:-/var/log/hub}"
CRON_DIR="${CRON_DIR:-/etc/cron.d}"
CADDY_SITES="${CADDY_SITES:-/etc/caddy/sites}"
NO_SYSTEMD="${NO_SYSTEMD:-0}"           # 1 = skip systemd and Caddy reloads (for testing)
PY="$REPO/venv/bin/python"

say() { printf '\n== %s\n' "$*"; }
need_root() { [ "$(id -u)" = 0 ] || { echo "Run this with sudo."; exit 1; }; }
as_user() { runuser -u "$RUN_USER" -- "$@"; }
psql_admin() { runuser -u postgres -- psql -v ON_ERROR_STOP=1 -q "$@"; }
secret() { python3 -c 'import secrets; print(secrets.token_urlsafe(32))'; }

cmd_server() {
  need_root
  say "Packages"
  apt-get update -q
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q postgresql python3-venv python3-pip caddy ufw \
    unattended-upgrades tmux git curl
  say "Security updates and firewall"
  echo 'APT::Periodic::Update-Package-Lists "1"; APT::Periodic::Unattended-Upgrade "1";' > /etc/apt/apt.conf.d/20auto-upgrades
  ufw allow OpenSSH >/dev/null && ufw allow 80 >/dev/null && ufw allow 443 >/dev/null && ufw --force enable >/dev/null
  say "Python environment for $REPO"
  [ -x "$PY" ] || as_user python3 -m venv "$REPO/venv"
  as_user "$PY" -m pip install -q --upgrade pip
  as_user "$PY" -m pip install -q -r "$REPO/requirements.txt"
  say "Folders"
  install -d -m 750 -o root -g "$RUN_USER" "$HUB_ETC"
  install -d -m 750 -o "$RUN_USER" -g "$RUN_USER" "$BACKUP_ROOT" "$LOG_DIR"
  cat > /etc/logrotate.d/hub <<EOF
$LOG_DIR/*.log {
  weekly
  rotate 8
  compress
  missingok
  notifempty
}
EOF
  say "Web server (Caddy, automatic HTTPS)"
  install -d "$CADDY_SITES"
  grep -q "import $CADDY_SITES/\*.caddy" /etc/caddy/Caddyfile 2>/dev/null || {
    printf '# Managed by ops/install.sh: each install adds a file in %s\nimport %s/*.caddy\n' "$CADDY_SITES" "$CADDY_SITES" \
      > /etc/caddy/Caddyfile
  }
  [ "$NO_SYSTEMD" = 1 ] || systemctl reload caddy || systemctl restart caddy
  say "Server ready. Next: sudo ops/install.sh add NAME CLIENT_DIR PORT auto"
}

cmd_add() {
  need_root
  local name="${1:-}" client_dir="${2:-}" port="${3:-}" host="${4:-}"
  [[ "$name" =~ ^[a-z][a-z0-9_]{1,20}$ ]] || { echo "NAME: lowercase letters, numbers, _ (e.g. company)"; exit 2; }
  [[ "$port" =~ ^[0-9]{4,5}$ ]] || { echo "PORT: a number like 8001"; exit 2; }
  case "$client_dir" in /*) ;; *) client_dir="$REPO/$client_dir" ;; esac
  [ -f "$client_dir/config.toml" ] || { echo "No config.toml in $client_dir"; exit 2; }
  [ -x "$PY" ] || { echo "Run 'sudo ops/install.sh server' first."; exit 2; }
  local envf="$HUB_ETC/$name.env" db="hub_$name" role="hub_$name" ai_role="ai_reader_$name"

  if [ -f "$envf" ]; then
    say "$name already has settings ($envf); keeping them"
  else
    say "Database and logins for $name"
    local pw ai_pw
    pw="$(secret)"; ai_pw="$(secret)"
    psql_admin <<SQL
DO \$\$BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$role') THEN CREATE ROLE $role LOGIN; END IF;
END\$\$;
ALTER ROLE $role PASSWORD '$pw' CREATEDB CREATEROLE;
SQL
    local owner
    owner="$(psql_admin -tAc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname = '$db'")"
    if [ -z "$owner" ]; then
      psql_admin -c "CREATE DATABASE $db OWNER $role"
    elif [ "$owner" != "$role" ]; then
      echo "A database called $db already exists and belongs to $owner, not $role."
      echo "Pick another NAME, or move that database out of the way first. Nothing was changed."
      exit 3
    fi
    psql_admin -d "$db" -c "ALTER SCHEMA public OWNER TO $role"
    install -d -m 750 -o "$RUN_USER" -g "$RUN_USER" "$BACKUP_ROOT/$name"
    local secure=1; [ -n "$host" ] || secure=0
    umask 077
    cat > "$envf" <<EOF
# Settings for the "$name" install. Owner-only. Never commit or share this file.
DATABASE_URL=postgresql://$role:$pw@127.0.0.1:5432/$db
SESSION_SECRET=$(secret)$(secret)
CLIENT_DIR=$client_dir
AI_READER_ROLE=$ai_role
AI_READER_PASSWORD=$ai_pw
SECURE_COOKIES=$secure
BACKUP_DIR=$BACKUP_ROOT/$name
KEEP_DAYS=14
# OFFSITE_CMD=aws s3 cp {} s3://your-bucket/$name/   (or rclone; {} is the backup file)
# API keys: sudo -u $RUN_USER env HUB_ENV_FILE=$envf $PY -m kit.manage set-secret ANTHROPIC_API_KEY_CHAT
# Alerts: ALERT_NTFY_URL=https://ntfy.sh/<long-random-topic>
EOF
    chown "$RUN_USER:$RUN_USER" "$envf"; chmod 600 "$envf"; umask 022
  fi

  say "Tables, views and settings"
  as_user env HUB_ENV_FILE="$envf" "$PY" -m kit.manage init-db | tail -1

  # What this install needs on a schedule depends on its config.
  read -r apps has_sources is_demo < <(as_user "$PY" - "$client_dir/config.toml" <<'PY'
import sys, tomllib
c = tomllib.load(open(sys.argv[1], "rb"))
print(",".join(c.get("apps", ["analytics"])), int(bool(c.get("sources"))), int(bool(c.get("demo"))))
PY
)
  say "Scheduled jobs ($apps)"
  local run="cd $REPO && HUB_ENV_FILE=$envf" log="$LOG_DIR/$name"
  {
    echo "# Managed by ops/install.sh for the $name install. Times are UTC."
    echo "SHELL=/bin/bash"
    echo "*/15 * * * * $RUN_USER $run $PY -m kit.alerts check >> $log-alerts.log 2>&1"
    echo "30 7 * * *   $RUN_USER $run ops/backup.sh >> $log-backup.log 2>&1"
    echo "0 9 * * 0    $RUN_USER $run ops/restore_test.sh >> $log-restore.log 2>&1"
    if [ "$has_sources" = 1 ]; then
      [ "$is_demo" = 1 ] && echo "50 10 * * *  $RUN_USER $run $PY $client_dir/generate.py >> $log-generate.log 2>&1"
      echo "7 * * * *    $RUN_USER $run $PY -m kit.sync >> $log-sync.log 2>&1"
    fi
    [[ ",$apps," == *",practice,"* ]] && echo "*/15 * * * * $RUN_USER $run $PY -m kit.agents tick >> $log-agents.log 2>&1"
    [[ ",$apps," == *",analytics,"* ]] && echo "15 12,17,21 * * 1-5 $RUN_USER $run $PY -m kit.ai.insights >> $log-insights.log 2>&1"
    true
  } > "$CRON_DIR/hub-$name"
  chmod 644 "$CRON_DIR/hub-$name"
  if [ "$has_sources" = 1 ]; then
    [ "$is_demo" = 1 ] && as_user env HUB_ENV_FILE="$envf" "$PY" "$client_dir/generate.py" >/dev/null
    as_user env HUB_ENV_FILE="$envf" "$PY" -m kit.sync | tail -3 || true
  fi

  say "Service hub-$name on 127.0.0.1:$port"
  if [ "$NO_SYSTEMD" != 1 ]; then
    cat > "/etc/systemd/system/hub-$name.service" <<EOF
[Unit]
Description=Hub: $name
After=network.target postgresql.service

[Service]
User=$RUN_USER
WorkingDirectory=$REPO
Environment=HUB_ENV_FILE=$envf
ExecStart=$REPO/venv/bin/uvicorn kit.hub.app:app --host 127.0.0.1 --port $port --workers 2 --proxy-headers --forwarded-allow-ips 127.0.0.1
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable --now "hub-$name" >/dev/null
    systemctl restart "hub-$name"
  fi

  if [ -n "$host" ]; then
    if [ "$host" = auto ]; then
      local ip; ip="$(curl -fsS https://api.ipify.org)"
      host="$name.${ip//./-}.sslip.io"
    fi
    say "Web address https://$host"
    printf '%s {\n\tencode gzip\n\treverse_proxy 127.0.0.1:%s\n}\n' "$host" "$port" > "$CADDY_SITES/$name.caddy"
    [ "$NO_SYSTEMD" = 1 ] || systemctl reload caddy
  fi

  say "Done: $name"
  echo "Create your sign-in (you'll type the password, hidden):"
  echo "  sudo -u $RUN_USER env HUB_ENV_FILE=$envf $PY -m kit.manage create-user you@example.com \"Your Name\" --admin"
  [ -n "$host" ] && echo "Then open https://$host"
  true
}

cmd_update() {
  need_root
  say "Code"
  as_user git -C "$REPO" pull --ff-only
  as_user "$PY" -m pip install -q -r "$REPO/requirements.txt"
  for envf in "$HUB_ETC"/*.env; do
    [ -e "$envf" ] || continue
    local name; name="$(basename "$envf" .env)"
    say "Upgrading $name"
    as_user env HUB_ENV_FILE="$envf" "$PY" -m kit.manage init-db | tail -1
    if [ "$NO_SYSTEMD" != 1 ]; then
      systemctl restart "hub-$name"
      sleep 2
      local port; port="$(grep -o -- '--port [0-9]*' "/etc/systemd/system/hub-$name.service" | awk '{print $2}')"
      echo "health: $(curl -s "http://127.0.0.1:$port/healthz" || echo 'NOT RESPONDING')"
    fi
  done
  say "Updated. If anything looks wrong: git log, then git revert the bad commit and run update again."
}

cmd_list() {
  for envf in "$HUB_ETC"/*.env; do
    [ -e "$envf" ] || { echo "No installs yet."; return; }
    local name state; name="$(basename "$envf" .env)"
    state="$( [ "$NO_SYSTEMD" = 1 ] && echo "(systemd skipped)" || systemctl is-active "hub-$name" 2>/dev/null || true)"
    printf '%-12s %-10s %s\n' "$name" "$state" "$(grep -h '^\s*[a-z0-9.-]* {' "$CADDY_SITES/$name.caddy" 2>/dev/null | sed 's/ {//')"
  done
}

case "${1:-}" in
  server) cmd_server ;;
  add) shift; cmd_add "$@" ;;
  update) cmd_update ;;
  list) cmd_list ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
