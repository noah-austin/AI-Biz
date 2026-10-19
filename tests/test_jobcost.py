"""Job cost (construction): the generator's promises and the work-in-progress rules."""
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from kit import db, metrics

CON = Path(__file__).resolve().parent.parent / "clients" / "demo_construction"


@pytest.fixture(scope="module")
def con():
    sys.path.insert(0, str(CON))
    sys.modules.pop("company_profile", None)
    try:
        spec = importlib.util.spec_from_file_location("con_generate", CON / "generate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        as_of = dt.date(2025, 11, 3)
        return mod.generate(as_of), mod.generate(as_of), as_of
    finally:
        sys.path.remove(str(CON))
        sys.modules.pop("company_profile", None)


def test_same_day_gives_same_data(con):
    a, b, _ = con
    digest = lambda files: hashlib.sha256(json.dumps(files, sort_keys=True, default=str).encode()).hexdigest()
    assert digest(a) == digest(b)


def test_billing_never_runs_past_the_contract(con):
    files, _, as_of = con
    jobs = {j["Id"]: j for j in files["jobcost/jobs.json"]}
    approved = {}
    for c in files["jobcost/change_orders.json"]:
        if c["Status"] == "Approved":
            approved[c["JobId"]] = approved.get(c["JobId"], 0) + c["Amount"]
    billed = {}
    for a in files["jobcost/pay_apps.json"]:
        assert a["BillDate"] <= as_of.isoformat()
        billed[a["JobId"]] = billed.get(a["JobId"], 0) + a["GrossBilled"]
    for jid, b in billed.items():
        assert b <= (jobs[jid]["ContractValue"] + approved.get(jid, 0)) * 1.0001


@pytest.fixture
def job_rows():
    t = metrics.today()
    last_month = (t.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
    for table in ("jc.costs", "jc.pay_apps", "jc.change_orders", "jc.jobs"):
        db.execute(f"DELETE FROM {table} WHERE id LIKE 'T-%%'")
    db.execute("""INSERT INTO jc.jobs (id, number, name, branch_code, contract_value, budget_cost, estimate_at_completion,
                                       start_date, end_date, status, retainage_pct, synced_at)
                  VALUES ('T-J1', 'T1', 'Test job', 'DAL-01', 1000000, 880000, 950000, %(s)s, %(e)s, 'Active', 10, now())""",
               {"s": t - dt.timedelta(days=200), "e": t + dt.timedelta(days=100)})
    db.execute("""INSERT INTO jc.change_orders (id, job_id, number, amount, cost, status, submitted_date, approved_date, synced_at)
                  VALUES ('T-C1', 'T-J1', '1', 100000, 70000, 'Approved', %(d)s, %(d)s, now()),
                         ('T-C2', 'T-J1', '2', 50000, 40000, 'Pending', %(d)s, NULL, now())""", {"d": t - dt.timedelta(days=90)})
    db.execute("""INSERT INTO jc.costs (id, job_id, period, category, amount, synced_at)
                  VALUES ('T-K1', 'T-J1', %(lm)s, 'Labor', 475000, now()),
                         ('T-K2', 'T-J1', %(tm)s, 'Labor', 99999, now())""", {"lm": last_month, "tm": t.replace(day=1)})
    db.execute("""INSERT INTO jc.pay_apps (id, job_id, period, gross_billed, retainage_held, retainage_released, bill_date, synced_at)
                  VALUES ('T-B1', 'T-J1', %(lm)s, 500000, 50000, 0, %(lm)s, now())""", {"lm": last_month})
    yield
    for table in ("jc.costs", "jc.pay_apps", "jc.change_orders", "jc.jobs"):
        db.execute(f"DELETE FROM {table} WHERE id LIKE 'T-%%'")


def test_wip_rules(job_rows):
    w = db.one("SELECT * FROM rpt.wip WHERE id = 'T-J1'")
    assert float(w["contract"]) == 1_100_000                     # original + approved change orders only
    assert float(w["cost_to_date"]) == 475_000                   # this month's costs wait for month-end
    assert abs(float(w["pct_complete"]) - 0.5) < 1e-9             # 475,000 ÷ 950,000
    assert abs(float(w["earned"]) - 550_000) < 1e-6
    assert abs(float(w["over_under"]) - (500_000 - 550_000)) < 1e-6   # under-billed by $50K
    assert abs(float(w["original_margin"]) - 0.12) < 1e-9
    assert abs(float(w["projected_margin"]) - 150_000 / 1_100_000) < 1e-9
    assert float(w["pending_changes"]) == 50_000 and float(w["retainage"]) == 50_000
