"""Inventory for a demo company: items, locations, stock on hand and count corrections.

ITEMS rows: (sku, description, category, base unit cost, weekly use per unit of branch size, vendor key, critical).
Items with no weekly use are legacy stock that sits unused (dead stock). Stock levels are set from what was really
used in the last 13 weeks (usage: [(location id, sku, qty, date)]), so turns come out realistic.
Planted: two critical items out at one warehouse, two negative balances, items with no cost.
"""
import datetime as dt

from .common import month_starts


def price_on(base, drift, start, day):
    return base * (1 + drift * (day - start).days / 365)


def build(p, R, usage, as_of, vendor_ids, drift, locations, legacy_at, stockouts, negatives, no_cost=(),
          weeks_held=(3, 6), shrink_branch=None, stocked=None):
    """stocked(location, item row) -> bool says which items each location carries (default: all of them)."""
    items = [{"Sku": sku, "Description": desc, "Category": cat,
              "StandardCost": None if sku in no_cost else round(price_on(cost, drift[vend], p.START_OPS, as_of), 2),
              "PreferredVendorId": vendor_ids[vend], "Critical": crit, "Active": True}
             for sku, desc, cat, cost, weekly, vend, crit in p.ITEMS]
    loc_branch = {l["Id"]: l["BranchCode"] for l in locations}
    last_use, used_91 = {}, {}
    since = (as_of - dt.timedelta(days=91)).isoformat()
    for loc, sku, qty, day in usage:
        d = day.isoformat() if isinstance(day, dt.date) else day
        if d > last_use.get((loc, sku), ""):
            last_use[(loc, sku)] = d
        if d >= since:
            key = (loc_branch[loc], sku)
            used_91[key] = used_91.get(key, 0) + qty
    hold, reorder = weeks_held
    stock = []
    for loc in locations:
        for item in p.ITEMS:
            sku, desc, cat, cost, weekly, vend, crit = item
            if stocked and not stocked(loc, item):
                continue
            r = R("stock", loc["Id"], sku)
            wk = used_91.get((loc["BranchCode"], sku), 0) / 13
            rp = rq = None
            if loc["Kind"] == "Warehouse":
                if weekly == 0:
                    if loc["Id"] not in legacy_at.get(sku, ()):
                        continue
                    rp, rq, on_hand = 0, 0, r.randint(2, 9)
                else:
                    rp, rq = max(1, round(wk * hold)), max(2, round(wk * reorder))
                    low = r.random() < 0.08
                    on_hand = rp + r.randint(0, rq) if not low else r.randint(1 if crit else 0, max(1, rp - 1))
            else:
                if weekly == 0:
                    continue
                on_hand = r.randint(0, max(1, round(wk * 0.8)))
            last = (as_of - dt.timedelta(days=r.randint(220, 640))).isoformat() if weekly == 0 else last_use.get((loc["Id"], sku))
            row = {"Id": f"{loc['Id']}|{sku}", "LocationId": loc["Id"], "Sku": sku, "OnHand": on_hand, "ReorderPoint": rp,
                   "ReorderQty": rq, "LastIssuedDate": last, "LastCountedDate": (as_of - dt.timedelta(days=r.randint(3, 95))).isoformat()}
            if row["Id"] in stockouts:
                row["OnHand"] = 0
            if row["Id"] in negatives:
                row["OnHand"] = negatives[row["Id"]]
            stock.append(row)
    adjustments, n = [], 1
    for m in month_starts(as_of - dt.timedelta(days=365), as_of):
        for loc in locations:
            if loc["Kind"] != "Warehouse":
                continue
            r = R("count", loc["Id"], m.isoformat())
            day = m + dt.timedelta(days=r.randint(1, 25))
            if day > as_of:
                continue
            for _ in range(r.randint(3, 6)):
                sku = r.choice([it[0] for it in p.ITEMS if it[4] > 0 and (not stocked or stocked(loc, it))])
                qty = -r.randint(1, 2) if r.random() < (0.85 if loc["BranchCode"] == shrink_branch else 0.62) else r.randint(1, 2)
                adjustments.append({"Id": f"ADJ-{n:05d}", "Date": day.isoformat(), "LocationId": loc["Id"], "Sku": sku, "Qty": qty,
                                    "Reason": "Cycle count" if r.random() < 0.85 else "Damaged"})
                n += 1
    return {"inventory/items.json": items, "inventory/locations.json": locations, "inventory/stock.json": stock,
            "inventory/adjustments.json": adjustments}
