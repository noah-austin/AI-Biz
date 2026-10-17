"""Generate the fake "source systems" for the Bluestem demo company.

Bluestem Facility Services is fictional. This script writes what its CRM and
accounting system would return from their APIs on a given day, as JSON files
under clients/demo/source/. The kit's demo connectors read those files the
same way a real connector reads Salesforce or QuickBooks.

The output is deterministic: the same seed and as-of date always give the
same data, and moving the as-of date forward plays the company's history
forward (new deals appear, open deals progress, invoices get paid). So the
demo can be regenerated daily and the sync, history capture and "what
changed" views all behave as they would with a live client.

Data problems are planted on purpose so the clean-up list has real work:
placeholder close dates, duplicates, stale open deals, missing margins in
one branch, lost deals with no reason, won deals never billed, and
accounting customers not linked to the CRM.

Usage:  python clients/demo/generate.py [--as-of YYYY-MM-DD] [--out DIR]
"""
import argparse
import datetime as dt
import json
import math
import random
from pathlib import Path
from zoneinfo import ZoneInfo

SEED = 20261017
START = dt.date(2024, 1, 2)
PLACEHOLDER_CLOSE = dt.date(2111, 12, 31)

# CRM branch codes. Friendly names and regions live in the client config,
# because that mapping is a business rule, not source data.
BRANCHES = [  # code, city, relative size, win-rate nudge
    ("DAL-01", "Dallas", 1.30, 0.00),
    ("FTW-02", "Fort Worth", 0.80, 0.02),
    ("AUS-03", "Austin", 1.00, 0.05),
    ("SAT-04", "San Antonio", 0.80, 0.00),
    ("HOU-05", "Houston", 1.10, 0.01),
    ("HOU-06", "Pasadena", 0.70, -0.06),
]
MISSING_MARGIN_BRANCH = "HOU-06"

SEGMENTS = {  # weight, amount multiplier, win nudge by deal type
    "Healthcare": (0.18, 1.30, {"Service Contract": 0.12, "Project": 0.02, "Repair": 0.03}),
    "Education": (0.17, 1.00, {"Service Contract": 0.00, "Project": 0.09, "Repair": 0.00}),
    "Commercial Office": (0.24, 0.90, {"Service Contract": -0.02, "Project": -0.03, "Repair": 0.02}),
    "Industrial": (0.16, 1.20, {"Service Contract": 0.03, "Project": 0.00, "Repair": 0.08}),
    "Retail": (0.15, 0.70, {"Service Contract": -0.06, "Project": -0.05, "Repair": -0.04}),
    "Government": (0.10, 1.50, {"Service Contract": -0.08, "Project": -0.10, "Repair": -0.05}),
}

DEAL_TYPES = {  # share, median amount, lognormal sigma, cap, base win rate, cycle days, margin mean
    "Repair": (0.45, 3_500, 0.70, 60_000, 0.72, (3, 25), 38),
    "Service Contract": (0.30, 48_000, 0.70, 900_000, 0.40, (25, 110), 26),
    "Project": (0.25, 70_000, 0.90, 2_500_000, 0.27, (40, 160), 18),
}

DESCRIPTORS = {
    "Repair": ["Emergency repair: rooftop unit", "Chiller repair", "Boiler repair", "Electrical panel repair",
               "Generator service call", "Leak repair", "Controls troubleshooting", "Cooling tower repair"],
    "Service Contract": ["Annual HVAC maintenance", "Preventive maintenance program", "Full facility maintenance",
                         "Generator maintenance agreement", "Building automation service plan", "Water treatment program"],
    "Project": ["Chiller replacement", "Rooftop unit replacement", "Controls upgrade", "LED retrofit",
                "Boiler replacement", "Air handler retrofit", "Building automation install", "Tenant fit-out MEP"],
}

STAGES = [("Prospecting", 10), ("Qualification", 20), ("Proposal", 50), ("Negotiation", 75)]
LOSS_REASONS = ["Price", "Chose incumbent", "Timing / budget", "Scope changed", "No decision"]
LEAD_SOURCES = ["Referral", "Existing customer", "Website", "Bid board", "Cold outreach", "Trade show"]

FIRST = ["Alex", "Jordan", "Taylor", "Morgan", "Casey", "Riley", "Jamie", "Avery", "Drew", "Quinn",
         "Reese", "Cameron", "Dana", "Parker", "Rowan", "Sydney", "Blake", "Hayden", "Emerson", "Kendall"]
LAST = ["Alvarez", "Brooks", "Castillo", "Dawson", "Ellison", "Fuentes", "Garner", "Holloway", "Ibarra",
        "Jennings", "Keller", "Lockhart", "Medina", "Nolan", "Ortega", "Pruitt", "Quintero", "Ramsey",
        "Salinas", "Thornton", "Underwood", "Villarreal", "Whitaker", "Yates"]

ACCOUNT_WORDS = {
    "Healthcare": (["Lakeside", "Prairie", "Riverbend", "Live Oak", "Cedar Hill", "Brazos", "Trinity", "Hill Country"],
                   ["Medical Center", "Surgical Hospital", "Family Clinic", "Rehab Center", "Imaging Center", "Health Partners"]),
    "Education": (["Pecan Grove", "Red Oak", "Blanco Valley", "Mesquite Creek", "Bluebonnet", "Caliche Flats", "Cypress Bend"],
                  ["ISD", "Community College", "Academy", "Christian School", "Prep School", "Learning Center"]),
    "Commercial Office": (["Canyon", "Granite", "Summit", "Parkway", "Northgate", "Ironwood", "Westlake", "Lamar"],
                          ["Office Park", "Tower", "Plaza", "Business Center", "Corporate Campus", "Place"]),
    "Industrial": (["Gulf", "Lone Star", "Red River", "Coastal", "Big Thicket", "Permian", "Southfork"],
                   ["Fabrication", "Logistics", "Packaging", "Cold Storage", "Manufacturing", "Distribution"]),
    "Retail": (["Main Street", "Crossroads", "Market Square", "Old Town", "Sunset", "Villa"],
               ["Shopping Center", "Outlets", "Grocers", "Marketplace", "Home Store", "Commons"]),
    "Government": (["Hays", "Comal", "Tarrant", "Bastrop", "Harris", "Bexar", "Collin"],
                   ["County Annex", "Municipal Court", "Public Library", "Water District", "City Hall", "Parks Department"]),
}


def rng_for(*parts):
    return random.Random("|".join(str(p) for p in (SEED,) + parts))


def stamp(day, rng):
    """A UTC timestamp during Central business hours on `day`."""
    t = dt.datetime.combine(day, dt.time(13, 0)) + dt.timedelta(minutes=rng.randint(0, 10 * 60))
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def season(day):
    return 1.0 + 0.18 * math.sin((day.timetuple().tm_yday - 60) / 365 * 2 * math.pi)


def growth(day):
    return 1.0 + 0.09 * ((day - START).days / 365)


def business_days(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += dt.timedelta(days=1)


def build_people():
    users = [{"Id": "U000", "Name": "Pat Whitaker", "Email": "pat.whitaker@bluestem.example",
              "Title": "VP of Sales", "BranchCode": "DAL-01", "IsActive": True}]
    reps = {}
    n = 1
    for code, _city, size, _ in BRANCHES:
        rng = rng_for("people", code)
        count = 2 + (1 if size >= 1.0 else 0)
        reps[code] = []
        for i in range(count + 1):
            uid = f"U{n:03d}"
            n += 1
            first, last = rng.choice(FIRST), rng.choice(LAST)
            title = "Branch Manager" if i == 0 else "Account Executive"
            users.append({"Id": uid, "Name": f"{first} {last}",
                          "Email": f"{first}.{last}@bluestem.example".lower(),
                          "Title": title, "BranchCode": code, "IsActive": True})
            reps[code].append(uid)
    # One rep left the company in 2025; their deals stay assigned to them.
    users[4]["IsActive"] = False
    return users, reps


def build_accounts():
    accounts = []
    by_branch = {}
    n = 1
    seg_names = list(SEGMENTS)
    seg_weights = [SEGMENTS[s][0] for s in seg_names]
    for code, city, size, _ in BRANCHES:
        rng = rng_for("accounts", code)
        by_branch[code] = []
        used = set()
        for _ in range(int(110 * size)):
            seg = rng.choices(seg_names, seg_weights)[0]
            a, b = ACCOUNT_WORDS[seg]
            for _try in range(20):
                name = f"{rng.choice(a)} {rng.choice(b)}"
                if name not in used:
                    break
                name = f"{name} {city}"
            used.add(name)
            aid = f"A{n:04d}"
            n += 1
            created = START - dt.timedelta(days=rng.randint(30, 3000))
            accounts.append({"Id": aid, "Name": name, "Segment": seg, "City": city, "State": "TX",
                             "BranchCode": code, "CreatedDate": stamp(created, rng)})
            by_branch[code].append(aid)
    return accounts, by_branch


def simulate_deal(idx, created, code, win_nudge, reps, account, rng):
    """The full life of one deal: a list of timed events plus its final shape."""
    deal_type = rng.choices(list(DEAL_TYPES), [v[0] for v in DEAL_TYPES.values()])[0]
    share, median, sigma, cap, base_win, (cmin, cmax), margin_mean = DEAL_TYPES[deal_type]
    seg_mult = SEGMENTS[account["Segment"]][1]
    amount = min(cap, rng.lognormvariate(math.log(median * seg_mult), sigma))
    amount = round(amount, -1 if amount < 10_000 else -2)
    win = base_win + win_nudge + SEGMENTS[account["Segment"]][2][deal_type]
    win -= 0.05 * max(0.0, math.log10(amount / median))  # bigger deals are harder to win
    win = max(0.05, min(0.92, win))

    cycle = rng.randint(cmin, cmax)
    roll = rng.random()
    outcome = "won" if roll < win else "lost"
    if rng.random() < (0.035 if deal_type != "Repair" else 0.01):
        outcome = "stale"  # the rep stops updating it; it sits open forever
    close_day = created + dt.timedelta(days=cycle)

    margin = round(rng.gauss(margin_mean, 5), 1)
    if code == MISSING_MARGIN_BRANCH and created.year == 2025 and rng.random() < 0.8:
        margin = None
    elif rng.random() < 0.08:
        margin = None

    # Expected close date: starts optimistic and slips toward the real close.
    expected = [(created, created + dt.timedelta(days=int(cycle * rng.uniform(0.6, 0.95))))]
    if outcome != "stale":
        while expected[-1][1] < close_day:
            prev = expected[-1][1]
            when = max(expected[-1][0] + dt.timedelta(days=1), prev - dt.timedelta(days=rng.randint(0, 7)))
            new = min(close_day, prev + dt.timedelta(days=rng.randint(15, 60)))
            if when >= close_day:
                break
            expected.append((when, new))
        if expected[-1][1] != close_day:
            expected.append((close_day, close_day))

    events = []  # (day, field, old, new)
    stage_path = STAGES if deal_type != "Repair" else STAGES[2:3]
    end_for_stages = close_day if outcome != "stale" else created + dt.timedelta(days=int(cycle * 0.5))
    if outcome == "lost":
        stage_path = stage_path[: rng.randint(1, len(stage_path))]
    elif outcome == "stale":
        stage_path = stage_path[:2]
    span = max(1, (end_for_stages - created).days)
    for i, (stage, prob) in enumerate(stage_path):
        day = created + dt.timedelta(days=int(span * i / max(1, len(stage_path))))
        events.append((day, "StageName", stage_path[i - 1][0] if i else None, stage))
    for when, new in expected:
        events.append((when, "CloseDate", None, new.isoformat()))

    amount_events = [(created, amount)]
    if deal_type != "Repair" and rng.random() < 0.3:
        revised = round(amount * rng.uniform(0.85, 1.15), -2)
        amount_events.append((created + dt.timedelta(days=int(span * 0.6)), revised))
        amount = revised
    for when, value in amount_events:
        events.append((when, "Amount", None, value))

    placeholder = outcome == "won" and rng.random() < 0.006
    if outcome == "won":
        events.append((close_day, "StageName", stage_path[-1][0], "Closed Won"))
        if placeholder:
            events.append((close_day, "CloseDate", None, PLACEHOLDER_CLOSE.isoformat()))
    elif outcome == "lost":
        events.append((close_day, "StageName", stage_path[-1][0], "Closed Lost"))

    events.sort(key=lambda e: (e[0], e[1] != "StageName"))
    owner = rng.choice(reps[code][1:] if len(reps[code]) > 1 else reps[code])
    if rng.random() < 0.15:
        owner = reps[code][0]
    return {
        "idx": idx, "type": deal_type, "code": code, "account": account, "owner": owner,
        "created": created, "close_day": close_day, "outcome": outcome, "margin": margin,
        "events": events, "lead": rng.choice(LEAD_SOURCES),
        "loss_reason": rng.choice(LOSS_REASONS) if rng.random() < 0.55 else None,
        "descriptor": rng.choice(DESCRIPTORS[deal_type]),
        "excluded": rng.random() < 0.008, "placeholder": placeholder,
        "duplicate": rng.random() < 0.006 and outcome in ("won", "lost", "stale"),
        "not_billed": outcome == "won" and deal_type != "Service Contract" and rng.random() < 0.03,
        "has_reference": rng.random() < 0.97,
    }


def state_at(deal, as_of):
    """Apply a deal's events up to `as_of` and return the CRM record, or None."""
    if deal["created"] > as_of:
        return None, []
    rec = {"Stage": None, "CloseDate": None, "Amount": None}
    history = []
    last_change = deal["created"]
    rng = rng_for("stamps", deal["idx"])
    for k, (day, field, _old, new) in enumerate(deal["events"]):
        if day > as_of:
            break
        key = {"StageName": "Stage"}.get(field, field)
        old = rec[key]
        rec[key] = new
        last_change = max(last_change, day)
        if old is not None and old != new:
            history.append({"Id": f"H{deal['idx']:05d}-{k:02d}", "OpportunityId": None, "Field": field,
                            "OldValue": str(old), "NewValue": str(new), "CreatedDate": stamp(day, rng)})
    stage = rec["Stage"]
    closed = stage in ("Closed Won", "Closed Lost")
    prob = 100 if stage == "Closed Won" else 0 if stage == "Closed Lost" else dict(STAGES)[stage]
    return {"stage": stage, "closed": closed, "won": stage == "Closed Won", "prob": prob,
            "close": rec["CloseDate"], "amount": rec["Amount"], "modified": last_change}, history


def generate(as_of):
    users, reps = build_people()
    accounts, accounts_by_branch = build_accounts()
    acct_index = {a["Id"]: a for a in accounts}

    deals = []
    idx = 1
    for day in business_days(START, as_of):
        for code, _city, size, nudge in BRANCHES:
            rng = rng_for("day", day.isoformat(), code)
            expected = 0.9 * size * season(day) * growth(day)
            count = int(expected) + (1 if rng.random() < expected - int(expected) else 0)
            pool = accounts_by_branch[code]
            for _ in range(count):
                # Favour repeat customers: a few accounts get most of the work.
                if rng.random() < 0.6:
                    pick = min(len(pool) - 1, int(rng.paretovariate(1.2)) - 1 + rng.randint(0, 3))
                else:
                    pick = rng.randrange(len(pool))
                account = acct_index[pool[pick]]
                deal = simulate_deal(idx, day, code, nudge, reps, account, rng_for("deal", idx))
                deals.append(deal)
                idx += 1

    opportunities, history_rows = [], []
    dup_n = 1
    for deal in deals:
        state, hist = state_at(deal, as_of)
        if not state:
            continue
        oid = f"OPP-{deal['idx']:05d}"
        acc = deal["account"]
        name = f"{acc['Name']} - {deal['descriptor']}"
        excluded = deal["excluded"]
        if excluded:
            name = f"INTERNAL - training opportunity {deal['idx']}"
        rng = rng_for("rec", deal["idx"])
        rec = {
            "Id": oid, "Name": name, "AccountId": acc["Id"], "OwnerId": deal["owner"],
            "BranchCode": deal["code"], "RecordType": deal["type"], "StageName": state["stage"],
            "IsClosed": state["closed"], "IsWon": state["won"], "Probability": state["prob"],
            "Amount": state["amount"], "MarginPct": deal["margin"], "CloseDate": state["close"],
            "CreatedDate": stamp(deal["created"], rng), "LastModifiedDate": stamp(state["modified"], rng),
            "LossReason": deal["loss_reason"] if state["stage"] == "Closed Lost" else None,
            "LeadSource": deal["lead"], "ExcludeFromReporting": excluded,
        }
        opportunities.append(rec)
        for h in hist:
            h["OpportunityId"] = oid
        history_rows.extend(hist)
        if deal["duplicate"] and deal["created"] + dt.timedelta(days=2) <= as_of:
            dup = dict(rec)
            dup.update({"Id": f"OPP-D{dup_n:04d}", "StageName": "Prospecting", "IsClosed": False,
                        "IsWon": False, "Probability": 10, "LossReason": None,
                        "CreatedDate": stamp(deal["created"] + dt.timedelta(days=rng.randint(0, 2)), rng)})
            if dup["CloseDate"] == PLACEHOLDER_CLOSE.isoformat():
                dup["CloseDate"] = deal["close_day"].isoformat()
            opportunities.append(dup)
            dup_n += 1

    customers, invoices = build_accounting(deals, acct_index, as_of)
    return {
        "crm/users.json": users,
        "crm/accounts.json": accounts,
        "crm/opportunities.json": opportunities,
        "crm/opportunity_history.json": history_rows,
        "accounting/customers.json": customers,
        "accounting/invoices.json": invoices,
    }


def build_accounting(deals, acct_index, as_of):
    customers = {}
    raw_invoices = []
    for deal in deals:
        if deal["outcome"] != "won" or deal["close_day"] > as_of or deal["excluded"] or deal["not_billed"]:
            continue
        acc = deal["account"]
        if acc["Id"] not in customers:
            rng = rng_for("customer", acc["Id"])
            name = acc["Name"]
            style = rng.random()
            if style < 0.12:
                name = f"{name}, Inc."
            elif style < 0.22:
                name = name.upper()
            elif style < 0.30:
                name = f"{name} LLC"
            slow = rng.random() < 0.14
            customers[acc["Id"]] = {
                "Id": f"C{10000 + int(acc['Id'][1:])}", "DisplayName": name,
                "CrmAccountId": acc["Id"] if rng.random() > 0.06 else None,
                "TermsDays": 30, "_delay": (rng.gauss(100, 25) if slow else rng.gauss(33, 9)),
            }
        cust = customers[acc["Id"]]
        rng = rng_for("billing", deal["idx"])
        close = deal["close_day"]
        amount = next(v for d, f, o, v in reversed(deal["events"]) if f == "Amount")
        if deal["type"] == "Repair":
            schedule = [(close + dt.timedelta(days=rng.randint(2, 14)), amount)]
        elif deal["type"] == "Project":
            dur = rng.randint(45, 180)
            schedule = [(close + dt.timedelta(days=20), round(amount * 0.3, 2)),
                        (close + dt.timedelta(days=dur // 2), round(amount * 0.4, 2)),
                        (close + dt.timedelta(days=dur), round(amount - round(amount * 0.3, 2) - round(amount * 0.4, 2), 2))]
        else:
            first = (close.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
            monthly = round(amount / 12, 2)
            schedule = []
            for m in range(12):
                y, mo = divmod(first.month - 1 + m, 12)
                schedule.append((dt.date(first.year + y, mo + 1, 1), monthly))
        for k, (day, amt) in enumerate(schedule):
            delay = max(5, int(rng.gauss(cust["_delay"], 8)))
            disputed = rng.random() < 0.015
            raw_invoices.append({
                "day": day, "cust": cust["Id"], "amount": amt,
                "paid_day": None if disputed else day + dt.timedelta(days=delay),
                "ref": f"OPP-{deal['idx']:05d}" if deal["has_reference"] else None,
                "memo": f"{deal['descriptor']} ({k + 1}/{len(schedule)})",
            })
    raw_invoices.sort(key=lambda r: (r["day"], r["cust"], r["memo"]))
    invoices = []
    for n, r in enumerate(raw_invoices, start=1):
        if r["day"] > as_of:
            continue
        paid = r["paid_day"] is not None and r["paid_day"] <= as_of
        invoices.append({
            "Id": f"INV-{n:06d}", "DocNumber": f"{n:06d}", "CustomerId": r["cust"],
            "TxnDate": r["day"].isoformat(), "DueDate": (r["day"] + dt.timedelta(days=30)).isoformat(),
            "TotalAmt": r["amount"], "AmountPaid": r["amount"] if paid else 0.0,
            "PaidDate": r["paid_day"].isoformat() if paid else None,
            "Reference": r["ref"], "Memo": r["memo"],
        })
    out = []
    for c in customers.values():
        c = {k: v for k, v in c.items() if not k.startswith("_")}
        out.append(c)
    return out, invoices


def main():
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    local_today = dt.datetime.now(ZoneInfo("America/Chicago")).date()
    p.add_argument("--as-of", default=local_today.isoformat(), help="the 'today' of the fake systems")
    p.add_argument("--out", default=str(here / "source"))
    args = p.parse_args()
    as_of = dt.date.fromisoformat(args.as_of)
    out = Path(args.out)
    files = generate(as_of)
    for rel, rows in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(rows, indent=0, default=str))
        print(f"{rel:32} {len(rows):6} records")
    (out / "meta.json").write_text(json.dumps({"as_of": as_of.isoformat()}))


if __name__ == "__main__":
    main()
