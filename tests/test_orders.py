"""Orders and shipping (distribution): the generator's promises and the numbers' rules."""
import datetime as dt
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from kit import db, metrics

DIST = Path(__file__).resolve().parent.parent / "clients" / "demo_distribution"


def _load_generator():
    sys.path.insert(0, str(DIST))
    sys.modules.pop("company_profile", None)   # another demo's profile may already be loaded under the same name
    try:
        spec = importlib.util.spec_from_file_location("dist_generate", DIST / "generate.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(DIST))
        sys.modules.pop("company_profile", None)


@pytest.fixture(scope="module")
def dist():
    gen = _load_generator()
    as_of = dt.date(2025, 3, 3)
    return gen.generate(as_of), gen.generate(as_of), as_of


def test_same_day_gives_same_data(dist):
    a, b, _ = dist
    digest = lambda files: hashlib.sha256(json.dumps(files, sort_keys=True, default=str).encode()).hexdigest()
    assert digest(a) == digest(b)


def test_orders_ship_and_bill_consistently(dist):
    files, _, as_of = dist
    orders = {o["Id"]: o for o in files["orders/orders.json"]}
    assert orders and all(o["OrderDate"] <= as_of.isoformat() for o in orders.values())
    for line in files["orders/order_lines.json"]:
        assert 0 <= line["QtyFirstShipment"] <= line["QtyShipped"] <= line["QtyOrdered"]
    refs = {i["Reference"] for i in files["accounting/invoices.json"]}
    invoiced = [o for o in orders.values() if o["Status"] == "Invoiced"]
    assert invoiced and all(f'SO {o["OrderNumber"]}' in refs for o in invoiced)


@pytest.fixture
def orders_rows():
    """Three orders: one shipped complete, one shipped short (a backorder), one placed today and not shipped yet."""
    t = metrics.today()
    db.execute("DELETE FROM ord.order_lines WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM ord.orders WHERE id LIKE 'T-%%'")
    db.execute("""INSERT INTO ord.orders (id, number, branch_code, order_date, requested_date, status, first_ship_date, last_ship_date, synced_at)
                  VALUES ('T-1', 'T1', 'DAL-01', %(d)s, %(d)s, 'Invoiced', %(d)s, %(d)s, now()),
                         ('T-2', 'T2', 'DAL-01', %(d)s, %(d)s, 'Partially shipped', %(d1)s, NULL, now()),
                         ('T-3', 'T3', 'DAL-01', %(t)s, %(t1)s, 'Open', NULL, NULL, now())""",
               {"d": t - dt.timedelta(days=3), "d1": t - dt.timedelta(days=2), "t": t, "t1": t + dt.timedelta(days=1)})
    db.execute("""INSERT INTO ord.order_lines (id, order_id, sku, qty_ordered, qty_first_shipment, qty_shipped, unit_price, unit_cost, synced_at)
                  VALUES ('T-1a', 'T-1', 'X', 10, 10, 10, 10, 8, now()),
                         ('T-2a', 'T-2', 'X', 10, 4, 4, 100, 60, now()),
                         ('T-3a', 'T-3', 'X', 5, 0, 0, 10, 8, now())""")
    yield t
    db.execute("DELETE FROM ord.order_lines WHERE id LIKE 'T-%%'")
    db.execute("DELETE FROM ord.orders WHERE id LIKE 'T-%%'")


def test_order_rules(orders_rows):
    t = orders_rows
    s = metrics.orders_summary(t - dt.timedelta(days=5), t, ["DAL-01"])
    assert s["lines"] == 3 and s["lines_filled"] == 1                       # only the complete first shipment counts
    assert s["backorder_value"] == 600                                       # 6 units short at $100; today's new order isn't a backorder
    assert abs(s["gross_margin"] - ((100 + 400) - (80 + 240)) / (100 + 400)) < 1e-9   # weighted by sales, from what shipped
    assert s["on_time_ship"] == 0.5                                          # T-1 on time, T-2 shipped a day late
