"""Projects and time (professional services): the generator's promises and the numbers' rules."""
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from kit import db, metrics

SVC = Path(__file__).resolve().parent.parent / "clients" / "demo_services"


@pytest.fixture(scope="module")
def svc():
    sys.path.insert(0, str(SVC))
    sys.modules.pop("company_profile", None)   # another demo's profile may already be loaded under the same name
    try:
        spec = importlib.util.spec_from_file_location("svc_generate", SVC / "generate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        as_of = dt.date(2025, 9, 1)
        return mod.generate(as_of), mod.generate(as_of), as_of
    finally:
        sys.path.remove(str(SVC))
        sys.modules.pop("company_profile", None)


def test_same_day_gives_same_data(svc):
    a, b, _ = svc
    digest = lambda files: hashlib.sha256(json.dumps(files, sort_keys=True, default=str).encode()).hexdigest()
    assert digest(a) == digest(b)


def test_time_and_billing_hang_together(svc):
    files, _, as_of = svc
    projects = {p["Id"]: p for p in files["projects/projects.json"]}
    entries = files["projects/time_entries.json"]
    assert all(e["WeekEnding"] <= as_of.isoformat() for e in entries)
    assert all(e["ProjectId"] in projects for e in entries if e["ProjectId"])
    assert all(e["Billable"] == bool(e["ProjectId"]) for e in entries)            # internal time is never billable
    refs = {i["Reference"] for i in files["accounting/invoices.json"]}
    assert refs <= {p["DealId"] for p in projects.values()}                      # every invoice belongs to a project's deal


@pytest.fixture
def project_rows():
    t = metrics.today()
    db.execute("DELETE FROM psa.time_entries WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM psa.projects WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM acct.invoices WHERE id LIKE 'T-%%'")
    emp = db.one("SELECT id FROM hr.employees WHERE branch_code = 'DAL-01' LIMIT 1")
    db.execute("""INSERT INTO psa.projects (id, number, name, deal_id, branch_code, billing_type, contract_value, budget_hours,
                                            start_date, end_date, status, percent_complete, synced_at)
                  VALUES ('T-P1', 'T1', 'Done fixed fee', 'T-D1', 'DAL-01', 'Fixed fee', 10000, 100, %(s)s, %(e)s, 'Completed', 100, now()),
                         ('T-P2', 'T2', 'Running over', 'T-D2', 'DAL-01', 'Fixed fee', 20000, 100, %(s)s, %(f)s, 'Active', 50, now())""",
               {"s": t - dt.timedelta(days=120), "e": t - dt.timedelta(days=10), "f": t + dt.timedelta(days=60)})
    db.execute("""INSERT INTO psa.time_entries (id, employee_id, project_id, week_ending, hours, billable, bill_rate, cost_rate, synced_at)
                  VALUES ('T-1', %(e)s, 'T-P1', %(w)s, 125, true, 100, 40, now()),
                         ('T-2', %(e)s, NULL, %(w)s, 25, false, 0, 40, now()),
                         ('T-3', %(e)s, 'T-P2', %(w)s, 80, true, 100, 40, now())""", {"e": emp["id"], "w": t - dt.timedelta(days=12)})
    db.execute("""INSERT INTO acct.invoices (id, number, invoice_date, due_date, amount, reference, synced_at)
                  VALUES ('T-I1', 'T1', %(d)s, %(d)s, 10000, 'T-D1', now())""", {"d": t - dt.timedelta(days=10)})
    yield t, emp["id"]
    db.execute("DELETE FROM psa.time_entries WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM psa.projects WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM acct.invoices WHERE id LIKE 'T-%%'")


def test_project_rules(project_rows):
    t, emp = project_rows
    r = db.one("SELECT budget_used, billed, standard_value, cost FROM rpt.projects WHERE id = 'T-P1'")
    assert float(r["budget_used"]) == 1.25 and float(r["billed"]) == 10000
    # Realization: $10,000 billed for 125 hours worth $12,500 at standard rates.
    assert abs(float(r["billed"]) / float(r["standard_value"]) - 0.8) < 1e-9
    risky = {p["id"] for p in metrics.projects_at_risk(["DAL-01"])}
    assert "T-P2" in risky                                       # 80% of budget used at 50% complete
    week = db.one("SELECT week_ending FROM psa.time_entries WHERE id = 'T-1'")["week_ending"]
    u = {x["key"]: x for x in metrics.utilization_by("person", week, week, ["DAL-01"])}
    name = db.one("SELECT name FROM hr.employees WHERE id = %(e)s", {"e": emp})["name"]
    assert abs(u[name]["billable_util"] - 205 / 230) < 1e-9     # billable ÷ everything recorded that week
