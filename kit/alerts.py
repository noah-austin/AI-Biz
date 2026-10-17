"""Tell Noah when something needs attention: failed or late syncs, missing backups, failed agent
jobs, AI spending near its cap, a nearly full disk.

    python -m kit.alerts check     # from cron every 15 minutes
    python -m kit.alerts test      # send a test message

Where alerts go (settings in the install's env file):
- ALERT_NTFY_URL: a private ntfy topic, e.g. https://ntfy.sh/<long-random-name>. Install the free ntfy app on the
  phone and subscribe to the same topic. Treat the topic name like a password.
- ALERT_EMAIL_TO with SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASSWORD: email (e.g. Google Workspace).
A problem alerts once when it starts, again every 24 hours while it lasts, and once when it's fixed.
"""
import argparse
import os
import shutil
import smtplib
import socket
import sys
import urllib.request
from email.message import EmailMessage

from . import db
from .config import _load_env_file, env_file, get_settings

REPEAT_HOURS = 24


def find_problems() -> dict[str, tuple[str, str]]:
    """Return {key: (severity, message)} for everything wrong right now."""
    s = get_settings()
    name = s.client.get("short_name", "Hub")
    out = {}
    now = db.one("SELECT now() AS n")["n"]
    failed, late, warned = [], [], []
    for r in db.query("SELECT * FROM core.sync_state WHERE object <> 'backup' ORDER BY object"):
        if r["last_status"] == "failed":
            failed.append(f"{r['object']} ({(r['last_message'] or '')[:80]})")
        elif r["last_success_at"] and (now - r["last_success_at"]).total_seconds() > 3 * 3600:
            late.append(r["object"])
        elif r["last_status"] == "warning":
            warned.append(f"{r['object']}: {(r['last_message'] or '')[:100]}")
    if failed:
        out["syncs"] = ("critical", f"{name}: sync failed for {', '.join(failed)}.")
    elif late:
        out["syncs"] = ("warning", f"{name}: no successful sync for over 3 hours ({', '.join(late)}).")
    elif warned:
        out["syncs"] = ("warning", f"{name}: sync warning: {'; '.join(warned)}")
    b = db.one("SELECT * FROM core.sync_state WHERE object = 'backup'")
    first_user = db.one("SELECT min(created_at) AS t FROM core.app_users")["t"]
    if b and b["last_status"] == "failed":
        out["backup"] = ("critical", f"{name}: last night's backup failed: {(b['last_message'] or '')[:160]}")
    elif b and b["last_success_at"] and (now - b["last_success_at"]).total_seconds() > 26 * 3600:
        out["backup"] = ("critical", f"{name}: no successful backup in over 26 hours.")
    elif not b and first_user and (now - first_user).total_seconds() > 26 * 3600:
        out["backup"] = ("critical", f"{name}: no backup has ever run. Check the nightly backup job.")
    if db.one("SELECT to_regclass('practice.agent_runs') AS t")["t"]:
        failed = db.query("""SELECT agent, job, error FROM practice.agent_runs
                             WHERE status = 'failed' AND started_at > now() - interval '24 hours'""")
        if failed:
            f = failed[0]
            out["agents"] = ("warning", f"{name}: {len(failed)} agent job(s) failed in the last day, "
                                        f"e.g. {f['agent']}/{f['job']}: {(f['error'] or '')[:120]}")
    try:
        from .ai import usage
        for a in usage.summary():
            if a["cap"] and a["cost"] >= 0.8 * a["cap"]:
                out[f"ai_spend:{a['feature']}"] = ("warning", f"{name}: AI {a['feature']} has used ${a['cost']:.2f} "
                                                               f"of its ${a['cap']:.0f} monthly cap.")
    except Exception:
        pass
    total, used, free = shutil.disk_usage("/")
    full = used / (used + free) if used + free else 0  # same as df's "Use%" (ignores space reserved for root)
    if full > 0.85:
        out["disk"] = ("critical" if full > 0.95 else "warning", f"{name}: the server's disk is {100 * full:.0f}% full.")
    return out


def send(title: str, message: str, critical: bool = False) -> list[str]:
    _load_env_file(env_file())
    sent = []
    url = os.environ.get("ALERT_NTFY_URL")
    if url:
        req = urllib.request.Request(url, data=message.encode(), method="POST",
                                     headers={"Title": title.encode("ascii", "ignore").decode(),
                                              "Priority": "high" if critical else "default",
                                              "Tags": "rotating_light" if critical else "warning"})
        urllib.request.urlopen(req, timeout=15).read()
        sent.append("ntfy")
    to = os.environ.get("ALERT_EMAIL_TO")
    if to and os.environ.get("SMTP_HOST"):
        msg = EmailMessage()
        msg["Subject"], msg["To"] = title, to
        msg["From"] = os.environ.get("SMTP_USER", f"hub@{socket.gethostname()}")
        msg.set_content(message)
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=20) as smtp:
            smtp.starttls()
            if os.environ.get("SMTP_USER"):
                smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            smtp.send_message(msg)
        sent.append("email")
    return sent


def check(deliver=send) -> dict:
    problems = find_problems()
    sent, resolved = [], []
    with db.connect() as conn:
        open_rows = {r["key"]: r for r in db.query("SELECT * FROM core.alerts WHERE resolved_at IS NULL", conn=conn)}
        for key, (sev, msg) in problems.items():
            row = open_rows.get(key)
            due = row is None or row["last_sent"] is None or (
                db.one("SELECT now() - %(t)s > interval '%(h)s hours' AS due", {"t": row["last_sent"], "h": REPEAT_HOURS},
                       conn)["due"])
            if row is None:
                db.execute("""INSERT INTO core.alerts (key, severity, message) VALUES (%(k)s, %(s)s, %(m)s)
                              ON CONFLICT (key) DO UPDATE SET severity = EXCLUDED.severity, message = EXCLUDED.message,
                              first_seen = now(), last_seen = now(), last_sent = NULL, resolved_at = NULL""",
                           {"k": key, "s": sev, "m": msg}, conn)
            else:
                db.execute("UPDATE core.alerts SET last_seen = now(), severity = %(s)s, message = %(m)s WHERE key = %(k)s",
                           {"k": key, "s": sev, "m": msg}, conn)
            if due:
                try:
                    if deliver("Hub alert" if sev == "warning" else "Hub problem", msg, sev == "critical"):
                        db.execute("UPDATE core.alerts SET last_sent = now() WHERE key = %(k)s", {"k": key}, conn)
                        sent.append(key)
                except Exception as e:  # never let a delivery problem stop the check
                    print(f"could not send alert {key}: {e}", file=sys.stderr)
        for key, row in open_rows.items():
            if key not in problems:
                db.execute("UPDATE core.alerts SET resolved_at = now() WHERE key = %(k)s", {"k": key}, conn)
                resolved.append(key)
                if row["last_sent"]:
                    try:
                        deliver("Hub: fixed", f"Fixed: {row['message']}")
                    except Exception as e:
                        print(f"could not send resolution {key}: {e}", file=sys.stderr)
    return {"open": sorted(problems), "sent": sent, "resolved": resolved}


def open_alerts() -> list[dict]:
    try:
        return db.query("SELECT * FROM core.alerts WHERE resolved_at IS NULL ORDER BY severity, first_seen")
    except Exception:
        return []


def main():
    p = argparse.ArgumentParser(description="Check for problems and send alerts.")
    p.add_argument("cmd", choices=["check", "test"])
    a = p.parse_args()
    if a.cmd == "test":
        sent = send("Hub test", "Test alert from your hub. If you can read this, alerts work.")
        print("sent via: " + (", ".join(sent) if sent else "nothing (set ALERT_NTFY_URL or ALERT_EMAIL_TO + SMTP_*)"))
        return 0
    print(check())
    return 0


if __name__ == "__main__":
    sys.exit(main())
