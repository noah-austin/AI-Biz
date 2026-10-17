import datetime as dt
import sys

import pytest

from kit import db, metrics
from kit.connectors.base import ObjectSpec
from kit.hub.auth import safe_next
from kit.sync import SyncRefused, sync_object


# ---------- sync safety ----------

@pytest.fixture
def conn():
    with db.connect() as c:
        with c.cursor() as cur:
            cur.execute("CREATE TEMP TABLE t_sync (id text PRIMARY KEY, v text, synced_at timestamptz)")
        yield c
        c.rollback()


def spec(mode="snapshot"):
    return ObjectSpec("test", "t_sync", ["id", "v"], lambda: [], mode=mode)


def rows(n, prefix="r"):
    return [{"id": f"{prefix}{i}", "v": "x"} for i in range(n)]


def count(conn):
    return db.one("SELECT count(*) AS n FROM t_sync", conn=conn)["n"]


def test_refuses_empty_pull(conn):
    sync_object(conn, spec(), rows(10))
    with pytest.raises(SyncRefused):
        sync_object(conn, spec(), [])
    assert count(conn) == 10


def test_prunes_small_deletions(conn):
    sync_object(conn, spec(), rows(100))
    _, pruned, warning = sync_object(conn, spec(), rows(95))
    assert pruned == 5 and warning is None and count(conn) == 95


def test_refuses_large_deletions(conn):
    sync_object(conn, spec(), rows(100))
    _, pruned, warning = sync_object(conn, spec(), rows(50))
    assert pruned == 0 and warning and count(conn) == 100


def test_upsert_updates_values(conn):
    sync_object(conn, spec(), rows(3))
    sync_object(conn, spec(), [{"id": "r0", "v": "new"}, {"id": "r1", "v": "x"}, {"id": "r2", "v": "x"}])
    assert db.one("SELECT v FROM t_sync WHERE id = 'r0'", conn=conn)["v"] == "new"


def test_history_only_adds(conn):
    sync_object(conn, spec("history"), rows(5))
    added, pruned, _ = sync_object(conn, spec("history"), rows(2) + rows(3, "new"))
    assert added == 3 and pruned == 0 and count(conn) == 8


def test_rejects_duplicate_ids(conn):
    with pytest.raises(SyncRefused):
        sync_object(conn, spec(), [{"id": "a", "v": 1}, {"id": "a", "v": 2}])


# ---------- business rules match straight SQL ----------

def test_win_rate_is_weighted_not_averaged():
    s, e = dt.date(2025, 1, 1), dt.date(2025, 12, 31)
    m = metrics.closed_summary(s, e)
    r = db.one("""SELECT sum(amount) FILTER (WHERE is_won) / sum(amount) AS rate FROM crm.opportunities
                  WHERE is_closed AND NOT exclude_from_reporting AND close_date BETWEEN %(s)s AND %(e)s""", {"s": s, "e": e})
    assert m["win_rate_dollars"] == pytest.approx(float(r["rate"]))


def test_missing_margin_is_left_out_not_zero():
    s, e = dt.date(2025, 1, 1), dt.date(2025, 12, 31)
    m = metrics.closed_summary(s, e)
    r = db.one("""SELECT sum(amount * margin_pct / 100) / sum(amount) AS m FROM crm.opportunities
                  WHERE is_won AND margin_pct IS NOT NULL AND NOT exclude_from_reporting
                    AND close_date BETWEEN %(s)s AND %(e)s""", {"s": s, "e": e})
    assert m["margin_pct"] == pytest.approx(float(r["m"]))
    assert m["won_missing_margin"] > 0


def test_branch_rollup_sums_to_company():
    s, e = dt.date(2025, 1, 1), dt.date(2025, 12, 31)
    total = metrics.closed_summary(s, e)["won_amount"]
    codes = [r["code"] for r in db.query("SELECT code FROM core.branches")]
    parts = sum(metrics.closed_summary(s, e, [c])["won_amount"] for c in codes)
    unmapped = db.one("""SELECT coalesce(sum(amount), 0) AS a FROM rpt.deals WHERE is_won AND region = 'Unmapped'
                         AND close_date BETWEEN %(s)s AND %(e)s""", {"s": s, "e": e})["a"]
    assert parts + float(unmapped) == pytest.approx(total)


def test_excluded_deals_never_reported():
    n = db.one("SELECT count(*) AS n FROM rpt.deals d JOIN crm.opportunities o USING (id) WHERE o.exclude_from_reporting")["n"]
    assert n == 0


def test_same_day_last_year_handles_leap_day():
    assert metrics.same_day_last_year(dt.date(2028, 2, 29)) == dt.date(2027, 2, 28)


# ---------- web security ----------

@pytest.mark.parametrize("target,expected", [
    ("/deals?status=won", "/deals?status=won"), ("//evil.example", "/"), ("/\\evil.example", "/"),
    ("https://evil.example", "/"), ("", "/"), (None, "/"), ("/ok\r\nSet-Cookie: x", "/"),
])
def test_safe_next(target, expected):
    assert safe_next(target) == expected


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from kit.hub.app import app
    from kit.passwords import hash_password
    pw = "test-password-123"
    db.execute("DELETE FROM core.app_users WHERE email LIKE '%%@test.invalid'")
    db.execute("""INSERT INTO core.app_users (email, name, password_hash, role, branches) VALUES
                  ('admin@test.invalid', 'Test Admin', %(h)s, 'admin', NULL),
                  ('austin@test.invalid', 'Test Austin', %(h)s, 'viewer', ARRAY['AUS-03'])""", {"h": hash_password(pw)})
    yield TestClient(app), pw
    db.execute("DELETE FROM core.app_users WHERE email LIKE '%%@test.invalid'")


def login(c, email, pw):
    c.cookies.clear()
    r = c.post("/login", data={"email": email, "password": pw, "next": "/"}, follow_redirects=False)
    assert r.status_code == 303
    return c


def test_pages_need_sign_in(client):
    c, _ = client
    c.cookies.clear()
    r = c.get("/deals", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"].startswith("/login")


def test_wrong_password_refused(client):
    c, _ = client
    r = c.post("/login", data={"email": "admin@test.invalid", "password": "nope"}, follow_redirects=False)
    assert r.status_code == 401


def test_security_headers_and_pages(client):
    c, pw = client
    login(c, "admin@test.invalid", pw)
    for path in ["/", "/scorecard", "/deals?status=open", "/winloss", "/receivables", "/invoices", "/cleanup", "/health"]:
        r = c.get(path)
        assert r.status_code == 200, path
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_branch_user_sees_only_their_branch(client):
    c, pw = client
    login(c, "austin@test.invalid", pw)
    csv = c.get("/deals.csv?status=all").text.splitlines()
    branch_col = csv[0].split(",").index("branch")
    assert len(csv) > 1 and {line.split(",")[branch_col] for line in csv[1:] if line.count(",") == csv[0].count(",")} <= {"Austin"}
    other = db.one("SELECT id FROM crm.opportunities WHERE branch_code = 'DAL-01' LIMIT 1")["id"]
    assert "isn't there" in c.get(f"/demo-source/crm/opportunity/{other}").text
    assert c.get("/health").status_code == 403


def test_csv_blocks_formula_injection():
    from kit.hub.pages import _csv_safe
    assert _csv_safe("=HYPERLINK(1)") == "'=HYPERLINK(1)"
    assert _csv_safe("Dallas") == "Dallas"
