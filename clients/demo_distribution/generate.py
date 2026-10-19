"""Generate Bramblewood Industrial Supply's systems (a FICTIONAL distributor) as of a given day.

CRM (quotes and supply agreements), ERP orders and shipping, accounting (an invoice per shipped order), inventory,
purchasing and HR/payroll, all from one cast of customers, products and people. Stories planted on purpose:
- Corpus Christi is two warehouse staff short: overtime is high, fill rate and on-time shipping are low.
- Safety & PPE margin is sliding: the vendor raised costs about 10% a year and prices didn't follow.
- One Dallas rep discounts heavily; the valve vendor delivers late (and valves backorder more).
- The biggest Houston customer started paying slowly in spring.
- Data problems: orders shipped but never invoiced, lines sold below cost, negative stock, an item with no cost,
  received orders with no vendor bill, a duplicate vendor, staff with no manager, missing timesheets, two lapsed CDLs.

Usage:  python clients/demo_distribution/generate.py [--as-of YYYY-MM-DD] [--out DIR]
"""
import datetime as dt
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

import company_profile as p  # noqa: E402

from kit.demos import buying, crm, people, stock  # noqa: E402
from kit.demos.common import Rand, business_days, growth, poisson, season  # noqa: E402
from kit.demos.writer import main  # noqa: E402


def generate(as_of: dt.date) -> dict:
    R = Rand(p.SEED)
    users, reps = crm.build_users(p, R)
    accounts, by_branch = crm.build_accounts(p, R)
    index = {a["Id"]: a for a in accounts}
    deals = crm.simulate_deals(p, R, reps, by_branch, index, as_of)
    files = crm.crm_files(p, R, deals, users, accounts, as_of)

    buy = buying.Buying(p, R, as_of)
    items = {it[0]: it for it in p.ITEMS}
    sellable = [it for it in p.ITEMS if it[4] > 0]
    ledger = crm.Ledger(R, slow_share=0.06)
    biggest_houston = by_branch["HOU-01"][0]
    discounter = reps[p.DISCOUNTER[0]][p.DISCOUNTER[1]]
    orders, lines, usage, used_by_week = [], [], [], {}
    n, ln = 1, 1
    channels, cweights = [c for c, _ in p.CHANNELS], [w for _, w in p.CHANNELS]

    def sell_price(it, day, rng, rep):
        sku, _d, line, cost, _w, vend, _c = it
        markup = p.MARKUP[line]
        base = cost * (1 + 0.012 * (day - p.START_OPS).days / 365) if line == p.SQUEEZE_LINE else buy.price(cost, vend, day)
        price = base * (1 + markup) * rng.uniform(0.94, 1.04)
        if rep == discounter:
            price *= 0.89
        if rng.random() < 0.003:
            price = buy.price(cost, vend, day) * 0.88       # planted: a pricing mistake, below cost
        return round(price, 2)

    for day in business_days(p.START_OPS, as_of):
        for code, _city, size, _ in p.BRANCHES:
            rng = R("orders", day.isoformat(), code)
            count = poisson(rng, p.ORDERS_PER_DAY * size * season(day, 0.10, 110) * growth(day, p.START_OPS, 0.06))
            for _ in range(count):
                acc = crm.pick_account(rng, by_branch[code], index)
                rep = reps[code][1 + int(acc["Id"][1:]) % (len(reps[code]) - 1)]
                channel = rng.choices(channels, cweights)[0]
                requested = day if channel == "Counter" else day + dt.timedelta(days=rng.choice([1, 1, 2, 3]))
                first = day if channel == "Counter" else day + dt.timedelta(days=rng.choice([0, 1, 1, 2]))
                if rng.random() < p.LATE_SHIP.get(code, 0.06):
                    first = max(first, requested) + dt.timedelta(days=rng.randint(1, 3))
                oid = f"SO-{n:06d}"
                number = f"{n + 500000}"
                n += 1
                canceled = rng.random() < 0.01
                last, total = first, 0.0
                order_lines = []
                for _l in range(1 + poisson(rng, 1.6)):
                    it = rng.choices(sellable, [x[4] for x in sellable])[0]
                    sku = it[0]
                    qty = max(1, round(p.PACK.get(sku, 1) * rng.lognormvariate(math.log(6), 0.8)))
                    fill_p = p.FILL_BRANCH.get(code, p.FILL) + p.FILL_LINE.get(it[2], 0)
                    full = rng.random() < fill_p
                    first_qty = qty if full else int(qty * rng.uniform(0.0, 0.8))
                    later = None if full else first + dt.timedelta(days=rng.randint(3, 14))
                    shipped = qty if (full or later <= as_of) else first_qty
                    if first > as_of:
                        first_qty, shipped = 0, 0
                    price = sell_price(it, day, rng, rep)
                    cost = round(buy.price(it[3], it[5], day), 2)
                    if later and later <= as_of:
                        last = max(last, later)
                    order_lines.append({"Id": f"SOL-{ln:07d}", "OrderId": oid, "Sku": sku, "QtyOrdered": qty,
                                        "QtyFirstShipment": first_qty, "QtyShipped": shipped, "UnitPrice": price, "UnitCost": cost})
                    ln += 1
                    if not canceled:
                        total += shipped * price
                        for when, q in ((first, first_qty), (later, qty - first_qty if later and later <= as_of else 0)):
                            if q and when and when <= as_of:
                                usage.append((f"WH-{code}", sku, q, when))
                                week = when - dt.timedelta(days=when.weekday())
                                bucket = used_by_week.setdefault((code, week), {})
                                bucket[sku] = bucket.get(sku, 0) + q
                complete = all(l["QtyShipped"] >= l["QtyOrdered"] for l in order_lines)
                if canceled:
                    status, inv = "Canceled", None
                elif first > as_of:
                    status, inv = "Open", None
                elif not complete:
                    status, inv = "Partially shipped", None
                else:
                    inv_day = last + dt.timedelta(days=rng.choice([0, 0, 1]))
                    missed = rng.random() < 0.006 and last >= as_of - dt.timedelta(days=150)
                    if inv_day <= as_of and not missed:
                        status, inv = "Invoiced", f"INV-SO-{number}"
                        slow = 45 if (acc["Id"] == biggest_houston and inv_day >= p.SLOW_PAYER_FROM) else 0
                        ledger.add(acc, inv_day, total, f"SO {number}", f"Order {number}", oid, delay_extra=slow)
                    else:
                        status, inv = "Shipped", None
                orders.append({"Id": oid, "OrderNumber": number, "AccountId": acc["Id"], "BranchCode": code, "RepId": rep,
                               "Channel": channel, "OrderDate": day.isoformat(),
                               "RequestedDate": requested.isoformat(), "Status": status,
                               "FirstShipDate": first.isoformat() if first <= as_of and not canceled else None,
                               "LastShipDate": last.isoformat() if complete and first <= as_of and not canceled else None,
                               "InvoiceNumber": inv})
                lines += order_lines

    locations = [{"Id": f"WH-{code}", "Name": f"{city} warehouse", "Kind": "Warehouse", "BranchCode": code}
                 for code, city, *_ in p.BRANCHES]
    files.update(stock.build(
        p, R, usage, as_of, buy.vid, buy.drift, locations,
        legacy_at={"VLV-SPC10": ("WH-HOU-01", "WH-BMT-06"), "HYD-HOSE": ("WH-CRP-05", "WH-HOU-01"), "CTL-PNU": ("WH-DAL-02",)},
        stockouts={"WH-CRP-05|VLV-BALL1", "WH-CRP-05|FIT-ELB1"}, negatives={"WH-SAT-03|FAS-ROD": -4, "WH-DAL-02|PPE-HAT": -2},
        no_cost=p.NO_COST, weeks_held=(6, 10), shrink_branch="CRP-05"))
    buy.restock_weekly(used_by_week, dup_vendor="gulfway_dup", dup_of="gulfway")
    files.update(buy.files())
    _employees, hr = people.files(p, R, users, as_of, p.START_OPS)
    files.update(hr)
    files.update(ledger.files(as_of))
    files["orders/orders.json"] = orders
    files["orders/order_lines.json"] = lines
    return files


if __name__ == "__main__":
    main(generate, HERE, __doc__.splitlines()[0])
