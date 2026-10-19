"""Purchasing for a demo company: vendors and purchase orders with their lines.

VENDORS rows: (key, name, category, terms days, lead days, chance of arriving late, yearly price drift).
Orders come from the generator: weekly restocking from what was used, plus one-off orders (equipment, materials,
subcontracts) it passes in. Planted: received orders never billed by the vendor, orders with no expected date.
"""
import datetime as dt


class Buying:
    def __init__(self, p, R, as_of):
        self.p, self.R, self.as_of = p, R, as_of
        self.vid = {v[0]: f"V{100 + k}" for k, v in enumerate(p.VENDORS)}
        self.info = {v[0]: v for v in p.VENDORS}
        self.drift = {v[0]: v[6] for v in p.VENDORS}
        self.pos, self.lines, self.n, self.ln = [], [], 1, 1

    def vendors(self):
        return [{"Id": self.vid[k], "Name": name, "Category": cat, "TermsDays": terms}
                for k, name, cat, terms, _lead, _late, _drift in self.p.VENDORS]

    def price(self, base, vendor, day):
        return base * (1 + self.drift[vendor] * (day - self.p.START_OPS).days / 365)

    def order(self, vendor, code, kind, ordered, lines, rng, ref=None):
        """lines: [(sku or None, description, qty, unit price)]"""
        _k, _name, _cat, _terms, lead, late_p, _drift = self.info[vendor]
        expected = ordered + dt.timedelta(days=max(1, int(rng.gauss(lead, lead * 0.25))))
        received = expected + dt.timedelta(days=rng.randint(2, 12) if rng.random() < late_p else -rng.randint(0, 1))
        status, billed = "Open", None
        amount = round(sum(q * pr for _s, _d, q, pr in lines), 2)
        if rng.random() < 0.015:
            status, received = "Canceled", None
        elif received <= self.as_of:
            status = "Received"
            bill_day = received + dt.timedelta(days=rng.randint(3, 22))
            if bill_day <= self.as_of and not (rng.random() < 0.035 and received >= self.as_of - dt.timedelta(days=200)):
                status, billed = "Closed", amount
        else:
            received = None
        po_id = f"PO-{self.n:05d}"
        self.pos.append({"Id": po_id, "PONumber": f"{self.n + 20000}", "VendorId": self.vid[vendor], "BranchCode": code, "Kind": kind,
                         "OrderedDate": ordered.isoformat(), "ExpectedDate": None if rng.random() < 0.012 else expected.isoformat(),
                         "ReceivedDate": received.isoformat() if received else None, "Status": status, "Amount": amount,
                         "BilledAmount": billed, "DealId": ref})
        self.n += 1
        for sku, desc, q, pr in lines:
            self.lines.append({"Id": f"POL-{self.ln:06d}", "POId": po_id, "Sku": sku, "Description": desc, "Qty": q,
                               "UnitPrice": round(pr, 2)})
            self.ln += 1

    def restock_weekly(self, used_by_week, dup_vendor=None, dup_of=None):
        """used_by_week: {(branch, monday): {sku: qty}}. Each branch orders roughly last week's use, grouped by vendor."""
        items = {it[0]: it for it in self.p.ITEMS}
        for (code, monday), used in sorted(used_by_week.items()):
            order_day = monday + dt.timedelta(days=8)   # the Tuesday after
            if order_day > self.as_of or not used:
                continue
            r = self.R("restock", code, monday.isoformat())
            by_vendor = {}
            for sku, qty in sorted(used.items()):
                it = items[sku]
                vend = it[5]
                if dup_vendor and vend == dup_of and r.random() < 0.04:
                    vend = dup_vendor
                q = max(1, round(qty * r.uniform(0.85, 1.2)))
                by_vendor.setdefault(vend, []).append((sku, it[1], q, self.price(it[3], dup_of if vend == dup_vendor else vend, order_day)
                                                        * r.uniform(0.98, 1.03)))
            for vend, ls in sorted(by_vendor.items()):
                self.order(vend, code, getattr(self.p, "RESTOCK_KIND", "Stock"), order_day, ls, r)

    def files(self):
        return {"purchasing/vendors.json": self.vendors(), "purchasing/purchase_orders.json": self.pos,
                "purchasing/po_lines.json": self.lines}
