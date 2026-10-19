"""Operations: field service, inventory, purchasing and people (the demo's stand-in systems)."""
import datetime as dt

from kit import cleanup, db, metrics, watch
from tests.test_kit import client, login  # noqa: F401  (fixture)


def t():
    return metrics.today()


def test_first_time_fix_counts_return_visits_in_the_same_period():
    start, end = t() - dt.timedelta(days=89), t()
    s = metrics.jobs_summary(start, end)
    r = db.one("""SELECT count(*) FILTER (WHERE job_type = 'Repair' AND NOT is_callback AND status = 'Completed') AS repairs,
                         count(*) FILTER (WHERE is_callback AND status = 'Completed') AS back
                  FROM rpt.jobs WHERE completed_date BETWEEN %(s)s AND %(e)s""", {"s": start, "e": end})
    assert s["repairs"] == r["repairs"] and s["return_visits"] == r["back"]
    assert abs(s["first_time_fix"] - (1 - r["back"] / r["repairs"])) < 1e-9


def test_branch_rates_roll_up_to_the_company_rate():
    start, end = t() - dt.timedelta(days=29), t()
    rows, total = metrics.jobs_by_branch(start, end), metrics.jobs_summary(start, end)
    assert sum(r["em_reached"] for r in rows) == total["em_reached"]
    assert abs(sum(r["em_on_time"] for r in rows) / sum(r["em_reached"] for r in rows) - total["emergency_on_time"]) < 1e-9


def test_overtime_is_weighted_by_hours_not_averaged():
    rows = metrics.overtime_by_branch(t(), 4)
    company = metrics.people_summary(t())["overtime_pct"]
    weighted = sum(float(r["ot"]) for r in rows) / sum(float(r["worked"]) for r in rows)
    assert abs(company - weighted) < 1e-9


def test_inventory_rules():
    s = metrics.inventory_summary(t())
    value = db.one("SELECT sum(greatest(s.on_hand, 0) * i.standard_cost) AS v FROM inv.stock s JOIN inv.items i ON i.id = s.sku")["v"]
    assert abs(s["value"] - float(value)) < 0.01                       # negatives count as zero; no-cost parts drop out
    assert abs(s["turns"] - s["used_12m"] / s["value"]) < 1e-9
    assert all(r["location_id"].startswith("WH-") for r in metrics.reorder_list())   # vans aren't on the reorder list
    assert all(float(r["on_hand"]) <= float(r["reorder_point"]) for r in metrics.reorder_list())


def test_planted_stories_and_problems_show_up():
    found = {r["check"].key: r["count"] for r in cleanup.run_checks(limit=0)}
    for key in ("job_not_invoiced", "job_left_tech", "expired_license_booked", "missing_timesheet", "no_manager",
                "negative_stock", "item_no_cost", "po_not_billed", "duplicate_vendor"):
        assert found[key] > 0, key
    ot = {r["branch"]: r["overtime_pct"] for r in metrics.overtime_by_branch(t(), 4)}
    assert ot["Houston"] == max(ot.values())
    kinds = {a["kind"] for a in watch.alerts(t(), None, 7)}
    assert {"Out of stock", "License expired"} <= kinds


def test_operations_pages_and_grouped_menu(client):
    c, pw = client
    login(c, "admin@test.invalid", pw)
    for path in ["/jobs", "/inventory", "/purchasing", "/people"]:
        r = c.get(path)
        assert r.status_code == 200, path
    assert ">Operations</a>" in r.text and ">Sales</a>" in r.text
    jobs = c.get("/jobs").text
    assert 'class="subtabs"' in jobs and ">Inventory</a>" in jobs
    job = db.one("SELECT id FROM fsm.work_orders LIMIT 1")["id"]
    assert "Stand-in Field service" in c.get(f"/demo-source/fieldservice/job/{job}").text


def test_branch_user_sees_only_their_branch_operations(client):
    c, pw = client
    login(c, "austin@test.invalid", pw)
    page = c.get("/people").text
    assert "Austin" in page and "San Antonio" not in page
    other = db.one("SELECT id FROM fsm.work_orders WHERE branch_code = 'DAL-01' LIMIT 1")["id"]
    assert "isn't there" in c.get(f"/demo-source/fieldservice/job/{other}").text
    worker = db.one("SELECT id FROM hr.employees WHERE branch_code = 'DAL-01' LIMIT 1")["id"]
    assert "isn't there" in c.get(f"/demo-source/hr/employee/{worker}").text
