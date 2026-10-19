"""Generate Cottonwood Precision Manufacturing's systems (a FICTIONAL contract manufacturer) as of a given day.

CRM (quotes and blanket orders), ERP customer orders and shipping, production (work centers, production orders,
downtime), inventory (raw materials and finished goods per plant), purchasing (raw materials), accounting (an invoice
per shipped order) and HR/payroll. Each week, customer demand becomes production orders at each plant; production
uses machine time and raw materials; raw materials are reordered; late production leaves customers short.
Stories planted on purpose:
- The old Waco press brake keeps breaking down: lots of downtime, low effectiveness, late production orders, and
  trailer components and enclosures short for customers.
- Scrap on the Fort Worth CNC machines jumped in July, after two experienced machinists left.
- The steel service center raised prices about 12% a year and delivers late; prices to customers were set in January,
  so margin on steel-heavy products is slipping.
- Data problems: lapsed welder certifications, staff with no manager, a missing timesheet, a duplicate vendor,
  received orders with no vendor bill, negative stock, an item with no cost, orders shipped but not invoiced.

Usage:  python clients/demo_manufacturing/generate.py [--as-of YYYY-MM-DD] [--out DIR]
"""
import datetime as dt
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

import company_profile as p  # noqa: E402

from kit.demos import buying, crm, people, stock  # noqa: E402
from kit.demos.common import Rand, business_days, growth, mondays, poisson, season  # noqa: E402
from kit.demos.writer import main  # noqa: E402

DOWNTIME = [  # reason, chance per day, minutes range
    ("Changeover", 0.60, (20, 70)),
    ("Breakdown", 0.04, (60, 300)),
    ("Waiting on material", 0.04, (45, 240)),
    ("No operator", 0.02, (120, 480)),
    ("Planned maintenance", 0.20, (30, 90)),
]


def generate(as_of: dt.date) -> dict:
    R = Rand(p.SEED)
    users, reps = crm.build_users(p, R)
    accounts, by_branch = crm.build_accounts(p, R)
    index = {a["Id"]: a for a in accounts}
    deals = crm.simulate_deals(p, R, reps, by_branch, index, as_of)
    files = crm.crm_files(p, R, deals, users, accounts, as_of)
    _employees, hr = people.files(p, R, users, as_of, p.START_OPS)
    files.update(hr)

    buy = buying.Buying(p, R, as_of)
    items = {it[0]: it for it in p.ITEMS}
    goods = [it for it in p.ITEMS if it[2] != "Raw material" and it[4] > 0]
    raw = {it[0]: it for it in p.ITEMS if it[2] == "Raw material"}

    def std_cost(it, day):
        """Standard cost moves with steel prices for the steel share of each product."""
        share = p.STEEL_SHARE.get(it[2], 0)
        steel = 1 + p.VENDORS[0][6] * (day - p.START_OPS).days / 365
        return it[3] * (1 - share + share * steel)

    def list_price(it, day):
        jan = dt.date(day.year, 1, 1)
        return round(std_cost(it, jan) * (1 + p.MARKUP[it[2]]), 2)

    # Downtime first: it decides which weeks each work center falls behind.
    downtime, dn = [], 1
    lost = {}   # (work center, monday) -> minutes lost
    for wc_id, _name, code, hours, _fam, _std in p.WORK_CENTERS:
        for day in business_days(p.START_OPS, as_of):
            r = R("down", wc_id, day.isoformat())
            for reason, chance, (lo, hi) in DOWNTIME:
                if reason == "Breakdown" and wc_id == p.PROBLEM_MACHINE:
                    chance, lo, hi = 0.28, 90, 420
                if reason == "No operator" and code == "FTW" and day >= p.SCRAP_SPIKE[1]:
                    chance = 0.07
                if reason == "Waiting on material" and r.random() < 0.3 and code == "WAC":
                    chance *= 2
                if r.random() < chance:
                    minutes = r.randint(lo, hi)
                    downtime.append({"Id": f"DT-{dn:06d}", "WorkCenterId": wc_id, "Date": day.isoformat(), "Minutes": minutes,
                                     "Reason": reason})
                    dn += 1
                    week = day - dt.timedelta(days=day.weekday())
                    lost[(wc_id, week)] = lost.get((wc_id, week), 0) + minutes

    # Customer orders, shipped from finished goods. Short shipments when the plant's production is behind.
    ledger = crm.Ledger(R, slow_share=0.08)
    orders, lines, usage, demand = [], [], [], {}
    n, ln = 1, 1
    channels, cweights = [c for c, _ in p.CHANNELS], [w for _, w in p.CHANNELS]

    def behind(code, family, day):
        """Share of scheduled time lost last week at the work centers that make this family in this plant."""
        week = day - dt.timedelta(days=day.weekday() + 7)
        wcs = [w for w in p.WORK_CENTERS if w[2] == code and family in w[4]]
        if not wcs:
            return 0.0
        return max(lost.get((w[0], week), 0) / (w[3] * 60 * 5) for w in wcs)

    for day in business_days(p.START_OPS, as_of):
        for code, _city, size, _ in p.BRANCHES:
            rng = R("orders", day.isoformat(), code)
            for _ in range(poisson(rng, p.ORDERS_PER_DAY * size * season(day, 0.08, 120) * growth(day, p.START_OPS, 0.05))):
                acc = crm.pick_account(rng, by_branch[code], index)
                rep = reps[code][1 + int(acc["Id"][1:]) % (len(reps[code]) - 1)]
                channel = rng.choices(channels, cweights)[0]
                requested = day + dt.timedelta(days=rng.choice([3, 5, 7, 10]))
                first = day + dt.timedelta(days=rng.choice([2, 3, 4, 5, 7]))
                oid, number = f"SO-{n:06d}", f"{n + 700000}"
                n += 1
                total, last, order_lines = 0.0, first, []
                for _l in range(1 + poisson(rng, 0.9)):
                    it = rng.choices(goods, [g[4] for g in goods])[0]
                    qty = max(1, round(rng.lognormvariate(math.log(max(1.0, it[4] / 2)), 0.7)))
                    slip = behind(code, it[2], day)
                    full = rng.random() < (0.97 - 2.5 * max(0.0, slip - 0.08))   # normal changeovers don't cause shortages
                    late_by = 0 if full else rng.randint(4, 15)
                    first_qty = qty if full else int(qty * rng.uniform(0.0, 0.7))
                    later = None if full else first + dt.timedelta(days=late_by)
                    shipped = qty if (full or later <= as_of) else first_qty
                    if first > as_of:
                        first_qty, shipped = 0, 0
                    price = list_price(it, day) * rng.uniform(0.96, 1.03)
                    cost = round(std_cost(it, day), 2)
                    if later and later <= as_of:
                        last = max(last, later)
                    order_lines.append({"Id": f"SOL-{ln:07d}", "OrderId": oid, "Sku": it[0], "QtyOrdered": qty,
                                        "QtyFirstShipment": first_qty, "QtyShipped": shipped, "UnitPrice": round(price, 2),
                                        "UnitCost": cost})
                    ln += 1
                    total += shipped * price
                    if shipped:
                        usage.append((f"FG-{code}", it[0], shipped, min(as_of, later or first) if shipped == qty else first))
                    week = day - dt.timedelta(days=day.weekday())
                    demand[(code, week, it[0])] = demand.get((code, week, it[0]), 0) + qty
                complete = all(l["QtyShipped"] >= l["QtyOrdered"] for l in order_lines)
                late_ship = first > requested or rng.random() < 0.05
                if first > as_of:
                    status, inv = "Open", None
                elif not complete:
                    status, inv = "Partially shipped", None
                else:
                    inv_day = last + dt.timedelta(days=rng.choice([0, 1]))
                    if inv_day <= as_of and not (rng.random() < 0.006 and last >= as_of - dt.timedelta(days=150)):
                        status, inv = "Invoiced", f"INV-SO-{number}"
                        ledger.add(acc, inv_day, total, f"SO {number}", f"Order {number}", oid)
                    else:
                        status, inv = "Shipped", None
                orders.append({"Id": oid, "OrderNumber": number, "AccountId": acc["Id"], "BranchCode": code, "RepId": rep,
                               "Channel": channel, "OrderDate": day.isoformat(),
                               "RequestedDate": (requested if not late_ship else first - dt.timedelta(days=1)).isoformat(),
                               "Status": status, "FirstShipDate": first.isoformat() if first <= as_of else None,
                               "LastShipDate": last.isoformat() if complete and first <= as_of else None, "InvoiceNumber": inv})
                lines += order_lines

    # Production: each week every plant makes roughly what was ordered, on the work centers that make that family.
    prod, pn, raw_by_week = [], 1, {}
    last_monday = as_of - dt.timedelta(days=as_of.weekday())
    for week in mondays(p.START_OPS, last_monday + dt.timedelta(days=7)):
        for code, *_ in p.BRANCHES:
            for it in goods:
                qty = demand.get((code, week - dt.timedelta(days=7), it[0]), 0)
                if not qty:
                    continue
                r = R("prod", code, week.isoformat(), it[0])
                wcs = [w for w in p.WORK_CENTERS if w[2] == code and it[2] in w[4]]
                if not wcs:
                    continue
                wc = r.choice(wcs)
                start, due = week + dt.timedelta(days=1), week + dt.timedelta(days=8)
                slip = lost.get((wc[0], week), 0) / (wc[3] * 60 * 5)
                late_days = (r.randint(2, 12) if wc[0] == p.PROBLEM_MACHINE else r.randint(1, 5)) \
                    if r.random() < (0.05 + 5.0 * max(0.0, slip - 0.08)) else 0
                done = due - dt.timedelta(days=r.randint(0, 2)) + dt.timedelta(days=late_days)
                spike = wc[0] == p.SCRAP_SPIKE[0] and week >= p.SCRAP_SPIKE[1]
                scrap = round(qty * max(0.0, r.gauss(0.075, 0.025) if spike else r.gauss(0.02, 0.01)))
                std_hours = round(qty * wc[5], 1)
                actual = round(std_hours * max(0.8, r.gauss(1.25 if spike else 1.08, 0.08)), 1)
                status = "Completed" if done <= as_of else ("In progress" if start <= as_of else "Planned")
                prod.append({"Id": f"MO-{pn:06d}", "OrderNumber": f"{pn + 300000}", "Sku": it[0], "WorkCenterId": wc[0],
                             "PlantCode": code, "QtyPlanned": qty, "QtyCompleted": qty if status == "Completed" else 0,
                             "QtyScrapped": scrap if status == "Completed" else 0, "DueDate": due.isoformat(),
                             "StartDate": start.isoformat() if start <= as_of else None,
                             "CompletedDate": done.isoformat() if status == "Completed" else None, "Status": status,
                             "StandardHours": std_hours, "ActualHours": actual if status == "Completed" else None})
                pn += 1
                if start <= as_of:
                    for raw_sku, per in p.BOM_RAW[it[2]]:
                        q = max(1, round((qty + scrap) * per))
                        usage.append((f"RM-{code}", raw_sku, q, min(start, as_of)))
                        bucket = raw_by_week.setdefault((code, week), {})
                        bucket[raw_sku] = bucket.get(raw_sku, 0) + q

    locations = []
    for code, city, *_ in p.BRANCHES:
        locations.append({"Id": f"FG-{code}", "Name": f"{city} finished goods", "Kind": "Warehouse", "BranchCode": code})
        locations.append({"Id": f"RM-{code}", "Name": f"{city} raw materials", "Kind": "Warehouse", "BranchCode": code})
    files.update(stock.build(
        p, R, usage, as_of, buy.vid, buy.drift, locations,
        legacy_at={"OLD-TANK": ("FG-WAC",)}, stockouts={"RM-WAC|RM-WIRE", "RM-FTW|RM-SHT14"},
        negatives={"FG-FTW|BRK-310": -6, "RM-WAC|RM-FAST": -3}, no_cost=p.NO_COST, weeks_held=(2, 4),
        stocked=lambda loc, it: (it[2] == "Raw material") == loc["Id"].startswith("RM-")))
    buy.restock_weekly(raw_by_week, dup_vendor="steel_dup", dup_of="steel")
    files.update(buy.files())
    files.update(ledger.files(as_of))
    files["orders/orders.json"] = orders
    files["orders/order_lines.json"] = lines
    files["production/work_centers.json"] = [{"Id": w[0], "Name": w[1], "PlantCode": w[2], "HoursPerDay": w[3]} for w in p.WORK_CENTERS]
    files["production/production_orders.json"] = prod
    files["production/downtime.json"] = downtime
    return files


if __name__ == "__main__":
    main(generate, HERE, __doc__.splitlines()[0])
