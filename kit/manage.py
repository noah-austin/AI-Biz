"""Admin commands for one client install.

    python -m kit.manage init-db          create/upgrade tables, views and the AI's read-only login
    python -m kit.manage create-user EMAIL "Full Name" [--admin] [--branches DAL-01,FTW-02]
    python -m kit.manage set-password EMAIL
    python -m kit.manage list-users
    python -m kit.manage check-readonly   prove the AI login can read reports and nothing else

Passwords are typed with hidden input (or piped in with --password-stdin),
never passed on the command line, so they don't land in shell history.
"""
import argparse
import getpass
import sys
from pathlib import Path

import psycopg2
from psycopg2 import sql

from . import db
from .config import get_settings
from .passwords import hash_password
from .sync import load_reference

SCHEMA_DIR = Path(__file__).parent / "schema"
AI_ROLE = "ai_reader"


def init_db():
    settings = get_settings()
    with db.connect() as conn:
        with conn.cursor() as cur:
            for f in sorted(SCHEMA_DIR.glob("*.sql")):
                cur.execute(f.read_text())
                print(f"applied {f.name}")
        load_reference(conn, settings.client)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (AI_ROLE,))
            exists = cur.fetchone()
            if settings.ai_reader_password:
                verb = "ALTER" if exists else "CREATE"
                cur.execute(sql.SQL(verb + " ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(AI_ROLE)),
                            (settings.ai_reader_password,))
                exists = True
            if exists:
                ident = sql.Identifier(AI_ROLE)
                cur.execute(sql.SQL("ALTER ROLE {} SET default_transaction_read_only = on").format(ident))
                cur.execute(sql.SQL("ALTER ROLE {} SET statement_timeout = '15s'").format(ident))
                cur.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA core, crm, acct FROM {}").format(ident))
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA rpt TO {}").format(ident))
                cur.execute(sql.SQL("GRANT SELECT ON ALL TABLES IN SCHEMA rpt TO {}").format(ident))
                # The views run as their owner, but the AI role still needs the helper functions.
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA core TO {}").format(ident))
                cur.execute(sql.SQL("GRANT EXECUTE ON FUNCTION core.client_tz(), core.local_today() TO {}").format(ident))
                print(f"granted read-only report access to {AI_ROLE}")
            else:
                print(f"AI_READER_PASSWORD not set; skipped the {AI_ROLE} login")
        with conn.cursor() as cur:
            cur.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
    print("done")


def _read_password(stdin: bool) -> str:
    if stdin:
        pw = sys.stdin.readline().rstrip("\n")
    else:
        pw = getpass.getpass("Password: ")
        if pw != getpass.getpass("Again: "):
            sys.exit("Passwords didn't match.")
    if len(pw) < 12:
        sys.exit("Use at least 12 characters.")
    return pw


def create_user(email, name, admin, branches, stdin):
    pw = _read_password(stdin)
    branch_list = [b.strip() for b in branches.split(",")] if branches else None
    db.execute("""INSERT INTO core.app_users (email, name, password_hash, role, branches)
                  VALUES (lower(%(e)s), %(n)s, %(h)s, %(r)s, %(b)s)""",
               {"e": email, "n": name, "h": hash_password(pw), "r": "admin" if admin else "viewer", "b": branch_list})
    print(f"created {email}")


def set_password(email, stdin):
    pw = _read_password(stdin)
    n = db.execute("UPDATE core.app_users SET password_hash = %(h)s WHERE email = lower(%(e)s)",
                   {"h": hash_password(pw), "e": email})
    db.execute("DELETE FROM core.sessions WHERE user_id IN (SELECT id FROM core.app_users WHERE email = lower(%(e)s))",
               {"e": email})
    print("updated" if n else "no such user")


def list_users():
    for u in db.query("SELECT email, name, role, branches, active, last_login_at FROM core.app_users ORDER BY email"):
        print(u)


def check_readonly():
    """Sign in as the AI's login and confirm what it can and can't do."""
    settings = get_settings()
    if not settings.ai_reader_password:
        sys.exit("AI_READER_PASSWORD not set.")
    dsn = psycopg2.extensions.parse_dsn(settings.database_url)
    dsn.update(user=AI_ROLE, password=settings.ai_reader_password)
    conn = psycopg2.connect(**dsn)
    conn.autocommit = True
    checks = [
        ("read rpt.deals", "SELECT count(*) FROM rpt.deals", True),
        ("read rpt.invoices", "SELECT count(*) FROM rpt.invoices", True),
        ("read crm.opportunities directly", "SELECT count(*) FROM crm.opportunities", False),
        ("read core.app_users (logins)", "SELECT count(*) FROM core.app_users", False),
        ("write to core.settings", "UPDATE core.settings SET value = value", False),
        ("create a table", "CREATE TABLE rpt.ai_test (x int)", False),
    ]
    ok = True
    for label, q, should_work in checks:
        try:
            with conn.cursor() as cur:
                cur.execute(q)
            worked = True
        except psycopg2.Error:
            worked = False
        passed = worked == should_work
        ok &= passed
        print(f"{'PASS' if passed else 'FAIL'}  {label}: {'allowed' if worked else 'refused'}")
    conn.close()
    sys.exit(0 if ok else 1)


def main():
    p = argparse.ArgumentParser(description="Admin commands")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db")
    c = sub.add_parser("create-user")
    c.add_argument("email")
    c.add_argument("name")
    c.add_argument("--admin", action="store_true")
    c.add_argument("--branches")
    c.add_argument("--password-stdin", action="store_true")
    s = sub.add_parser("set-password")
    s.add_argument("email")
    s.add_argument("--password-stdin", action="store_true")
    sub.add_parser("list-users")
    sub.add_parser("check-readonly")
    a = p.parse_args()
    if a.cmd == "init-db":
        init_db()
    elif a.cmd == "create-user":
        create_user(a.email, a.name, a.admin, a.branches, a.password_stdin)
    elif a.cmd == "set-password":
        set_password(a.email, a.password_stdin)
    elif a.cmd == "list-users":
        list_users()
    elif a.cmd == "check-readonly":
        check_readonly()


if __name__ == "__main__":
    main()
