"""Sales history for a demo company: reps, customer accounts and deals, plus customers and invoices in accounting.

Generalised from Bluestem's generator. A profile `p` supplies who the company is:
    SEED, START, DOMAIN, EXEC = (name, title)
    BRANCHES = [(code, city, relative size, win-rate nudge)]
    SEGMENTS = {segment: (weight, amount multiplier, {deal type: win nudge})}
    DEAL_TYPES = {type: (share, median amount, lognormal sigma, cap, base win rate, (min, max) cycle days, margin mean)}
    DESCRIPTORS = {type: [what the deal is for]}, ACCOUNT_WORDS = {segment: ([first words], [second words])}
    STAGES = [(stage, probability)], QUICK_TYPES = {types that skip straight to Proposal}
    LOSS_REASONS, LEAD_SOURCES, ACCOUNTS_PER_BRANCH, DEALS_PER_DAY, MISSING_MARGIN_BRANCH (or None)
Data problems are planted at the same low rates as Bluestem: placeholder close dates, duplicates, stale deals,
missing margins, lost deals with no reason, unlinked accounting customers.
"""
import datetime as dt
import math

from .common import business_days, growth, pick_name, season, stamp

PLACEHOLDER_CLOSE = dt.date(2111, 12, 31)


def build_users(p, R):
    """The sales team: an executive, then a branch manager and reps for each branch."""
    users = [{"Id": "U000", "Name": p.EXEC[0], "Email": _email(p.EXEC[0], p.DOMAIN), "Title": p.EXEC[1],
              "BranchCode": p.BRANCHES[0][0], "IsActive": True}]
    reps, used, n = {}, {p.EXEC[0]}, 1
    for code, _city, size, _ in p.BRANCHES:
        rng = R("people", code)
        reps[code] = []
        for i in range(getattr(p, "REPS_BASE", 2) + (1 if size >= 1.0 else 0) + 1):
            name = pick_name(rng, used)
            uid = f"U{n:03d}"
            n += 1
            users.append({"Id": uid, "Name": name, "Email": _email(name, p.DOMAIN),
                          "Title": "Branch Manager" if i == 0 else getattr(p, "REP_TITLE", "Account Executive"),
                          "BranchCode": code, "IsActive": True})
            reps[code].append(uid)
    users[min(4, len(users) - 1)]["IsActive"] = False   # one rep left; their deals stay with them
    return users, reps


def _email(name, domain):
    return f"{name.replace(' ', '.')}@{domain}".lower()


def build_accounts(p, R):
    accounts, by_branch, n = [], {}, 1
    seg_names = list(p.SEGMENTS)
    weights = [p.SEGMENTS[s][0] for s in seg_names]
    for code, city, size, _ in p.BRANCHES:
        rng = R("accounts", code)
        by_branch[code], used = [], set()
        for _ in range(int(p.ACCOUNTS_PER_BRANCH * size)):
            seg = rng.choices(seg_names, weights)[0]
            a, b = p.ACCOUNT_WORDS[seg]
            for _try in range(20):
                name = f"{rng.choice(a)} {rng.choice(b)}"
                if name not in used:
                    break
                name = f"{name} {city}"
            used.add(name)
            aid = f"A{n:04d}"
            n += 1
            accounts.append({"Id": aid, "Name": name, "Segment": seg, "City": city, "State": "TX", "BranchCode": code,
                             "CreatedDate": stamp(p.START - dt.timedelta(days=rng.randint(30, 3000)), rng)})
            by_branch[code].append(aid)
    return accounts, by_branch


def pick_account(rng, pool, index):
    """Favour repeat customers: a few accounts get most of the work."""
    if rng.random() < 0.6:
        return index[pool[min(len(pool) - 1, int(rng.paretovariate(1.2)) - 1 + rng.randint(0, 3))]]
    return index[pool[rng.randrange(len(pool))]]


def simulate_deal(p, idx, created, code, win_nudge, reps, account, rng):
    deal_type = rng.choices(list(p.DEAL_TYPES), [v[0] for v in p.DEAL_TYPES.values()])[0]
    _share, median, sigma, cap, base_win, (cmin, cmax), margin_mean = p.DEAL_TYPES[deal_type]
    seg = p.SEGMENTS[account["Segment"]]
    amount = min(cap, rng.lognormvariate(math.log(median * seg[1]), sigma))
    amount = round(amount, -1 if amount < 10_000 else -2)
    win = base_win + win_nudge + seg[2].get(deal_type, 0) - 0.05 * max(0.0, math.log10(amount / median))
    win = max(0.05, min(0.92, win))
    cycle = rng.randint(cmin, cmax)
    outcome = "won" if rng.random() < win else "lost"
    if rng.random() < (0.035 if deal_type not in p.QUICK_TYPES else 0.01):
        outcome = "stale"
    close_day = created + dt.timedelta(days=cycle)
    margin = round(rng.gauss(margin_mean, 5), 1)
    if code == p.MISSING_MARGIN_BRANCH and created.year == p.START.year + 1 and rng.random() < 0.8:
        margin = None
    elif rng.random() < 0.08:
        margin = None
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
    events = []
    path = p.STAGES if deal_type not in p.QUICK_TYPES else p.STAGES[2:3]
    end_for_stages = close_day if outcome != "stale" else created + dt.timedelta(days=int(cycle * 0.5))
    if outcome == "lost":
        path = path[: rng.randint(1, len(path))]
    elif outcome == "stale":
        path = path[:2]
    span = max(1, (end_for_stages - created).days)
    for i, (stage, _prob) in enumerate(path):
        events.append((created + dt.timedelta(days=int(span * i / max(1, len(path)))), "StageName", path[i - 1][0] if i else None, stage))
    for when, new in expected:
        events.append((when, "CloseDate", None, new.isoformat()))
    events.append((created, "Amount", None, amount))
    if deal_type not in p.QUICK_TYPES and rng.random() < 0.3:
        amount = round(amount * rng.uniform(0.85, 1.15), -2)
        events.append((created + dt.timedelta(days=int(span * 0.6)), "Amount", None, amount))
    placeholder = outcome == "won" and rng.random() < 0.006
    if outcome == "won":
        events.append((close_day, "StageName", path[-1][0], "Closed Won"))
        if placeholder:
            events.append((close_day, "CloseDate", None, PLACEHOLDER_CLOSE.isoformat()))
    elif outcome == "lost":
        events.append((close_day, "StageName", path[-1][0], "Closed Lost"))
    events.sort(key=lambda e: (e[0], e[1] != "StageName"))
    owner = rng.choice(reps[code][1:] or reps[code])
    if rng.random() < 0.15:
        owner = reps[code][0]
    return {"idx": idx, "type": deal_type, "code": code, "account": account, "owner": owner, "created": created,
            "close_day": close_day, "outcome": outcome, "margin": margin, "events": events, "amount": amount,
            "lead": rng.choice(p.LEAD_SOURCES), "loss_reason": rng.choice(p.LOSS_REASONS) if rng.random() < 0.55 else None,
            "descriptor": rng.choice(p.DESCRIPTORS[deal_type]), "excluded": rng.random() < 0.008, "placeholder": placeholder,
            "duplicate": rng.random() < 0.006 and outcome in ("won", "lost", "stale")}


def simulate_deals(p, R, reps, accounts_by_branch, acct_index, as_of):
    deals, idx = [], 1
    for day in business_days(p.START, as_of):
        for code, _city, size, nudge in p.BRANCHES:
            rng = R("day", day.isoformat(), code)
            expected = p.DEALS_PER_DAY * size * season(day, getattr(p, "SEASON_AMPLITUDE", 0.18)) * growth(day, p.START)
            count = int(expected) + (1 if rng.random() < expected - int(expected) else 0)
            for _ in range(count):
                account = pick_account(rng, accounts_by_branch[code], acct_index)
                deals.append(simulate_deal(p, idx, day, code, nudge, reps, account, R("deal", idx)))
                idx += 1
    return deals


def state_at(deal, as_of, R):
    if deal["created"] > as_of:
        return None, []
    rec, history, last_change = {"Stage": None, "CloseDate": None, "Amount": None}, [], deal["created"]
    rng = R("stamps", deal["idx"])
    for k, (day, field, _old, new) in enumerate(deal["events"]):
        if day > as_of:
            break
        key = {"StageName": "Stage"}.get(field, field)
        old, rec[key] = rec[key], new
        last_change = max(last_change, day)
        if old is not None and old != new:
            history.append({"Id": f"H{deal['idx']:05d}-{k:02d}", "OpportunityId": None, "Field": field, "OldValue": str(old),
                            "NewValue": str(new), "CreatedDate": stamp(day, rng)})
    stage = rec["Stage"]
    return {"stage": stage, "closed": stage in ("Closed Won", "Closed Lost"), "won": stage == "Closed Won",
            "close": rec["CloseDate"], "amount": rec["Amount"], "modified": last_change}, history


def crm_files(p, R, deals, users, accounts, as_of):
    stage_prob = dict(p.STAGES)
    opportunities, history_rows, dup_n = [], [], 1
    for deal in deals:
        state, hist = state_at(deal, as_of, R)
        if not state:
            continue
        oid = f"OPP-{deal['idx']:05d}"
        acc = deal["account"]
        name = f"{acc['Name']} - {deal['descriptor']}" if not deal["excluded"] else f"INTERNAL - training opportunity {deal['idx']}"
        rng = R("rec", deal["idx"])
        prob = 100 if state["stage"] == "Closed Won" else 0 if state["stage"] == "Closed Lost" else stage_prob[state["stage"]]
        rec = {"Id": oid, "Name": name, "AccountId": acc["Id"], "OwnerId": deal["owner"], "BranchCode": deal["code"],
               "RecordType": deal["type"], "StageName": state["stage"], "IsClosed": state["closed"], "IsWon": state["won"],
               "Probability": prob, "Amount": state["amount"], "MarginPct": deal["margin"], "CloseDate": state["close"],
               "CreatedDate": stamp(deal["created"], rng), "LastModifiedDate": stamp(state["modified"], rng),
               "LossReason": deal["loss_reason"] if state["stage"] == "Closed Lost" else None, "LeadSource": deal["lead"],
               "ExcludeFromReporting": deal["excluded"]}
        opportunities.append(rec)
        for h in hist:
            h["OpportunityId"] = oid
        history_rows.extend(hist)
        if deal["duplicate"] and deal["created"] + dt.timedelta(days=2) <= as_of:
            dup = dict(rec, Id=f"OPP-D{dup_n:04d}", StageName=p.STAGES[0][0], IsClosed=False, IsWon=False,
                       Probability=p.STAGES[0][1], LossReason=None,
                       CreatedDate=stamp(deal["created"] + dt.timedelta(days=rng.randint(0, 2)), rng))
            if dup["CloseDate"] == PLACEHOLDER_CLOSE.isoformat():
                dup["CloseDate"] = deal["close_day"].isoformat()
            opportunities.append(dup)
            dup_n += 1
    return {"crm/users.json": users, "crm/accounts.json": accounts, "crm/opportunities.json": opportunities,
            "crm/opportunity_history.json": history_rows}


def deal_amount(deal):
    return next(v for d, f, o, v in reversed(deal["events"]) if f == "Amount")


class Ledger:
    """Accounting: customers (one per CRM account that buys) and invoices, with paid dates.

    add() takes invoices from wherever the company bills from: won deals, shipped orders, project progress.
    A few customers are slow payers; a few customers aren't linked to the CRM; names drift between systems."""

    def __init__(self, R, terms_days=30, slow_share=0.14):
        self.R, self.terms, self.slow_share = R, terms_days, slow_share
        self.customers, self.raw = {}, []

    def customer(self, acc):
        if acc["Id"] not in self.customers:
            rng = self.R("customer", acc["Id"])
            name, style = acc["Name"], rng.random()
            name = f"{name}, Inc." if style < 0.12 else name.upper() if style < 0.22 else f"{name} LLC" if style < 0.30 else name
            slow = rng.random() < self.slow_share
            self.customers[acc["Id"]] = {"Id": f"C{10000 + int(acc['Id'][1:])}", "DisplayName": name,
                                         "CrmAccountId": acc["Id"] if rng.random() > 0.06 else None, "TermsDays": self.terms,
                                         "_delay": rng.gauss(100, 25) if slow else rng.gauss(self.terms + 3, 9)}
        return self.customers[acc["Id"]]

    def add(self, acc, day, amount, ref, memo, key, delay_extra=0.0):
        cust = self.customer(acc)
        rng = self.R("billing", key)
        delay = max(5, int(rng.gauss(cust["_delay"] + delay_extra, 8)))
        disputed = rng.random() < 0.015
        self.raw.append({"day": day, "cust": cust["Id"], "amount": round(amount, 2),
                         "paid_day": None if disputed else day + dt.timedelta(days=delay), "ref": ref, "memo": memo})

    def files(self, as_of):
        self.raw.sort(key=lambda r: (r["day"], r["cust"], r["memo"]))
        invoices = []
        for n, r in enumerate(self.raw, start=1):
            if r["day"] > as_of:
                continue
            paid = r["paid_day"] is not None and r["paid_day"] <= as_of
            invoices.append({"Id": f"INV-{n:06d}", "DocNumber": f"{n:06d}", "CustomerId": r["cust"], "TxnDate": r["day"].isoformat(),
                             "DueDate": (r["day"] + dt.timedelta(days=self.terms)).isoformat(), "TotalAmt": r["amount"],
                             "AmountPaid": r["amount"] if paid else 0.0, "PaidDate": r["paid_day"].isoformat() if paid else None,
                             "Reference": r["ref"], "Memo": r["memo"]})
        customers = [{k: v for k, v in c.items() if not k.startswith("_")} for c in self.customers.values()]
        return {"accounting/customers.json": customers, "accounting/invoices.json": invoices}
