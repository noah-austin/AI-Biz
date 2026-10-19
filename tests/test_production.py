"""Production (manufacturing): the generator's promises and the numbers' rules."""
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from kit import db, metrics

MFG = Path(__file__).resolve().parent.parent / "clients" / "demo_manufacturing"


@pytest.fixture(scope="module")
def mfg():
    sys.path.insert(0, str(MFG))
    sys.modules.pop("company_profile", None)
    try:
        spec = importlib.util.spec_from_file_location("mfg_generate", MFG / "generate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        as_of = dt.date(2025, 5, 5)
        return mod.generate(as_of), mod.generate(as_of), as_of
    finally:
        sys.path.remove(str(MFG))
        sys.modules.pop("company_profile", None)


def test_same_day_gives_same_data(mfg):
    a, b, _ = mfg
    digest = lambda files: hashlib.sha256(json.dumps(files, sort_keys=True, default=str).encode()).hexdigest()
    assert digest(a) == digest(b)


def test_production_orders_make_sense(mfg):
    files, _, as_of = mfg
    centers = {w["Id"] for w in files["production/work_centers.json"]}
    for o in files["production/production_orders.json"]:
        assert o["WorkCenterId"] in centers
        if o["Status"] == "Completed":
            assert o["CompletedDate"] <= as_of.isoformat() and o["QtyCompleted"] == o["QtyPlanned"]
        else:
            assert o["CompletedDate"] is None and o["QtyCompleted"] == 0
    assert all(d["Date"] <= as_of.isoformat() and d["Minutes"] > 0 for d in files["production/downtime.json"])


@pytest.fixture
def mfg_rows():
    t = metrics.today()
    for table in ("mfg.downtime", "mfg.production_orders", "mfg.work_centers"):
        db.execute(f"DELETE FROM {table} WHERE id LIKE 'T-%%'")
    db.execute("INSERT INTO mfg.work_centers (id, name, branch_code, hours_per_day, synced_at) VALUES ('T-WC', 'Test cell', 'DAL-01', 8, now())")
    db.execute("""INSERT INTO mfg.production_orders (id, number, sku, work_center_id, branch_code, qty_planned, qty_completed, qty_scrapped,
                                                     due_date, start_date, completed_date, status, standard_hours, actual_hours, synced_at)
                  VALUES ('T-M1', 'T1', 'X', 'T-WC', 'DAL-01', 100, 100, 0, %(d)s, %(s)s, %(d)s, 'Completed', 8, 10, now()),
                         ('T-M2', 'T2', 'X', 'T-WC', 'DAL-01', 100, 100, 25, %(d)s, %(s)s, %(l)s, 'Completed', 12, 10, now()),
                         ('T-M3', 'T3', 'X', 'T-WC', 'DAL-01', 50, 0, 0, %(d)s, %(s)s, NULL, 'In progress', 4, NULL, now())""",
               {"s": t - dt.timedelta(days=10), "d": t - dt.timedelta(days=3), "l": t - dt.timedelta(days=1)})
    db.execute("""INSERT INTO mfg.downtime (id, work_center_id, event_date, minutes, reason, synced_at)
                  VALUES ('T-D1', 'T-WC', %(d)s, 300, 'Breakdown', now())""", {"d": t - dt.timedelta(days=2)})
    yield t
    for table in ("mfg.downtime", "mfg.production_orders", "mfg.work_centers"):
        db.execute(f"DELETE FROM {table} WHERE id LIKE 'T-%%'")


def test_production_rules(mfg_rows):
    t = mfg_rows
    s = metrics.production_summary(t - dt.timedelta(days=29), t, ["DAL-01"])
    assert s["completed"] == 2 and s["on_time_rate"] == 0.5          # T-M2 finished two days after its due date
    assert abs(s["scrap_rate"] - 25 / 225) < 1e-9                       # scrapped ÷ (good + scrapped)
    assert abs(s["labor_efficiency"] - 20 / 20) < 1e-9                  # standard ÷ actual hours
    assert s["late_open"] == 1                                          # T-M3 is past due and not finished
    wc = next(r for r in metrics.oee_by_work_center(t, 30, ["DAL-01"]) if r["id"] == "T-WC")
    assert abs(wc["availability"] - 1200 / (1200 + 300)) < 1e-9        # 20 hours running, 5 hours down
    assert abs(wc["performance"] - 1.0) < 1e-9 and abs(wc["quality"] - 200 / 225) < 1e-9
