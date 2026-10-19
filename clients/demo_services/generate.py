"""Generate Kestrel Ridge Engineering's systems (a FICTIONAL engineering firm) as of a given day.

CRM (proposals), project and time tracking (projects, weekly time by person and project), accounting (monthly
invoices per project, Reference = the CRM deal) and HR/payroll. Won deals become projects; each week every active
project needs hours, and the office's people supply them, so utilization, overtime and budgets follow from real
staffing. Stories planted on purpose:
- Austin lost its biggest client in February: its people are under-used (about 60% against a 75% target).
- Houston is stretched: high utilization and overtime for its hourly designers and inspectors.
- One Dallas project manager's fixed-fee projects run about a third over budget, so their margin is thin or negative.
- A large hourly project in Houston hasn't been invoiced for three months: unbilled work in progress piling up.
- Hours on state-agency work get written down at billing (realization around 80%).
- Data problems: two lapsed PE licenses, staff with no manager, a missing timesheet, plus the CRM problems.

Usage:  python clients/demo_services/generate.py [--as-of YYYY-MM-DD] [--out DIR]
"""
import datetime as dt
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

import company_profile as p  # noqa: E402

from kit.demos import crm, people  # noqa: E402
from kit.demos.common import Rand, mondays  # noqa: E402
from kit.demos.writer import main  # noqa: E402

BILLING = {"Design services": "Fixed fee", "Study / assessment": "Time & materials", "On-call retainer": "Retainer"}
DURATION_WEEKS = {"Fixed fee": (14, 44), "Time & materials": (5, 18), "Retainer": (52, 52)}
MIX = {"Project Engineer": 0.42, "CAD Designer": 0.22, "Senior Engineer": 0.12, "Construction Inspector": 0.12,
       "Project Manager": 0.12}
BLENDED = sum(p.ROLES[r][1] * w for r, w in MIX.items())


def generate(as_of: dt.date) -> dict:
    R = Rand(p.SEED)
    users, reps = crm.build_users(p, R)
    accounts, by_branch = crm.build_accounts(p, R)
    index = {a["Id"]: a for a in accounts}
    deals = crm.simulate_deals(p, R, reps, by_branch, index, as_of)
    files = crm.crm_files(p, R, deals, users, accounts, as_of)
    # Won deals become projects. The overrun ones are picked up front and all go to one Dallas project manager.
    projects = []
    for d in deals:
        if d["outcome"] != "won" or d["excluded"] or d["close_day"] > as_of or d["close_day"] < p.START_OPS - dt.timedelta(days=240):
            continue
        r = R("project", d["idx"])
        kind = BILLING[d["type"]]
        start = d["close_day"] + dt.timedelta(days=r.randint(7, 21))
        weeks = r.randint(*DURATION_WEEKS[kind])
        fee = crm.deal_amount(d)
        overrun = kind == "Fixed fee" and d["code"] == "DFW" and d["idx"] % 3 == 1
        projects.append({"deal": d, "kind": kind, "start": start, "end": start + dt.timedelta(weeks=weeks), "weeks": weeks,
                         "fee": fee, "budget_hours": round(fee / BLENDED), "pm": None, "code": d["code"], "overrun": overrun,
                         "factor": r.uniform(1.25, 1.45) if overrun else r.uniform(0.97, 1.15),
                         "id": f"PRJ-{d['idx']:05d}", "number": f"{d['close_day']:%y}-{d['idx']:04d}", "hours": 0.0})

    # Staff each office for the work it really has (the average of the last six months before the stories start),
    # then let the stories play: Austin's work drops in February with the same people; Houston runs short.
    window = [w for w in mondays(dt.date(2025, 7, 7), dt.date(2026, 1, 26))]
    for role in p.PEOPLE["roles"]:
        if role["title"] in MIX:
            seats = {}
            for code, *_ in p.BRANCHES:
                need = sum(pr["budget_hours"] / pr["weeks"] * pr["factor"] for w in window for pr in projects
                           if pr["code"] == code and pr["start"] <= w <= pr["end"]) / len(window) * MIX[role["title"]]
                seats[code] = max(1, round(need / (40 * p.TARGET_UTIL[role["title"]]) * p.STAFFING.get(code, 1.0)))
            role["seats"] = seats
    employees, hr = people.files(p, R, users, as_of, p.START_OPS)
    files.update(hr)

    def active(e, day):
        return people.active_on(e, day)

    staff = [e for e in employees if e["JobTitle"] in p.ROLES]
    pms = {code: [e for e in employees if e["JobTitle"] == "Project Manager" and e["LocationCode"] == code] for code, *_ in p.BRANCHES}
    for k, pr in enumerate(projects):
        pool = [e for e in pms[pr["code"]] if active(e, min(pr["start"], as_of))] or pms[pr["code"]]
        if pr["overrun"] and len(pms["DFW"]) > p.OVERRUN_PM_INDEX:
            pr["pm"] = pms["DFW"][p.OVERRUN_PM_INDEX]
        elif pool:
            others = [e for e in pool if not (pr["code"] == "DFW" and len(pms["DFW"]) > p.OVERRUN_PM_INDEX
                                              and e is pms["DFW"][p.OVERRUN_PM_INDEX])] or pool
            pr["pm"] = others[k % len(others)]
    stalled = max((pr for pr in projects if pr["code"] == p.STALLED_OFFICE and pr["kind"] == "Time & materials"
                   and pr["start"] <= as_of - dt.timedelta(days=110) <= pr["end"] + dt.timedelta(days=120)),
                  key=lambda pr: pr["fee"], default=None)
    if stalled:   # a big hourly job that ran long: extend it so it's still active and racking up hours
        stalled["end"] = max(stalled["end"], as_of + dt.timedelta(days=30))
        stalled["weeks"] = max(1, (stalled["end"] - stalled["start"]).days // 7)

    # Weekly time: projects ask for hours; each office's people supply them.
    entries, en = [], 1
    last_monday = as_of - dt.timedelta(days=as_of.weekday() + 7)
    month_hours = {}   # (project id, month) -> [(entry index)]
    first_week = min(pr["start"] for pr in projects)
    for week in mondays(first_week, last_monday):
        for code, *_ in p.BRANCHES:
            r = R("week", code, week.isoformat())
            live = [pr for pr in projects if pr["code"] == code and pr["start"] <= week <= pr["end"]]
            crew = [e for e in staff if e["LocationCode"] == code and active(e, week)]
            if not crew:
                continue
            capacity = {e["Id"]: 40 * p.TARGET_UTIL[e["JobTitle"]] * r.uniform(0.9, 1.1) for e in crew}
            asked = {pr["id"]: pr["budget_hours"] / pr["weeks"] * pr["factor"] * r.uniform(0.8, 1.2) for pr in live}
            # Real work is lumpy (a few big projects); keep each office's week within a band of what its people can do,
            # so the planted stories stand out. Austin's work then drops by a fifth in February with the same people.
            total, target = sum(asked.values()), sum(capacity.values()) * (1.12 if code in p.STAFFING else 1.0)
            scale = min(1.35, max(0.75, target / total)) if total else 1.0
            if code == "AUS" and week >= dt.date(2026, 2, 2):
                scale *= p.AUSTIN_DROP
            asked = {k: v * scale for k, v in asked.items()}
            booked = {e["Id"]: 0.0 for e in crew}
            for pr in live:
                need = asked[pr["id"]]
                for role, share in MIX.items():
                    want = need * share
                    pool = sorted((e for e in crew if e["JobTitle"] == role), key=lambda e: booked[e["Id"]] - capacity[e["Id"]])
                    if not pool:
                        pool = sorted((e for e in crew if e["JobTitle"] == "Project Engineer"), key=lambda e: booked[e["Id"]])
                    for e in pool[:2]:
                        give = min(want / min(2, len(pool)), max(0.0, 50 - booked[e["Id"]]))
                        if give < 0.5:
                            continue
                        give = round(give * 2) / 2
                        booked[e["Id"]] += give
                        pr["hours"] += give
                        title = e["JobTitle"]
                        entries.append({"Id": f"TE-{en:06d}", "EmployeeId": e["Id"], "ProjectId": pr["id"],
                                        "WeekEnding": (week + dt.timedelta(days=4)).isoformat(), "Hours": give, "Billable": True,
                                        "BillRate": p.ROLES[title][1], "CostRate": p.ROLES[title][2], "InvoiceNumber": None})
                        month_hours.setdefault((pr["id"], week.replace(day=1)), []).append(len(entries) - 1)
                        en += 1
            for e in crew:
                internal = max(0.0, round(40 - booked[e["Id"]] - (8 if r.random() < 0.12 else 0), 1))
                if internal:
                    entries.append({"Id": f"TE-{en:06d}", "EmployeeId": e["Id"], "ProjectId": None,
                                    "WeekEnding": (week + dt.timedelta(days=4)).isoformat(), "Hours": internal, "Billable": False,
                                    "BillRate": 0, "CostRate": p.ROLES[e["JobTitle"]][2], "InvoiceNumber": None})
                    en += 1

    # Monthly billing: hourly work at standard rates (with write-downs), fixed fees by percent complete, retainers monthly.
    ledger = crm.Ledger(R, slow_share=0.08)
    billed = {}
    inv_n = 1
    months = sorted({m for (_pid, m) in month_hours})
    for m in months:
        bill_day = (m + dt.timedelta(days=32)).replace(day=1) + dt.timedelta(days=4)
        if bill_day > as_of:
            continue
        month_end = (m + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
        for pr in projects:
            idxs = month_hours.get((pr["id"], m), [])
            if not idxs and pr["kind"] != "Retainer":
                continue
            r = R("bill", pr["id"], m.isoformat())
            if pr is stalled and m >= (as_of - dt.timedelta(days=100)).replace(day=1):
                continue   # planted: nobody has invoiced this one lately
            if pr["kind"] == "Time & materials":
                std = sum(entries[i]["Hours"] * entries[i]["BillRate"] for i in idxs)
                amount = std * r.uniform(0.95, 1.0)
            elif pr["kind"] == "Fixed fee":
                done = min(1.0, max(0.0, (month_end - pr["start"]).days / max(1, (pr["end"] - pr["start"]).days)))
                amount = pr["fee"] * done - billed.get(pr["id"], 0.0)
            else:
                if not (pr["start"] <= month_end and m <= pr["end"]):
                    continue
                amount = pr["fee"] / 12
            if pr["deal"]["account"]["Segment"] == p.WRITE_DOWN_SEGMENT:
                amount *= 0.82    # planted: these clients push back on every invoice
            if amount < 1:
                continue
            number = f"K{inv_n:05d}"
            inv_n += 1
            billed[pr["id"]] = billed.get(pr["id"], 0.0) + amount
            ledger.add(pr["deal"]["account"], bill_day, amount, f"OPP-{pr['deal']['idx']:05d}", f"Project {pr['number']}, {m:%B %Y}",
                       f"{pr['id']}|{m}")
            for i in idxs:
                entries[i]["InvoiceNumber"] = number

    files["projects/projects.json"] = [{
        "Id": pr["id"], "ProjectNumber": pr["number"], "Name": f'{pr["deal"]["account"]["Name"]} - {pr["deal"]["descriptor"]}',
        "AccountId": pr["deal"]["account"]["Id"], "DealId": f"OPP-{pr['deal']['idx']:05d}", "OfficeCode": pr["code"],
        "ProjectManagerId": pr["pm"]["Id"] if pr["pm"] else None, "BillingType": pr["kind"], "ContractValue": round(pr["fee"], 2),
        "BudgetHours": pr["budget_hours"], "StartDate": pr["start"].isoformat(), "EndDate": pr["end"].isoformat(),
        "Status": "Not started" if pr["start"] > as_of else ("Completed" if pr["end"] < as_of else "Active"),
        "PercentComplete": round(100 * min(1.0, max(0.0, (as_of - pr["start"]).days / max(1, (pr["end"] - pr["start"]).days))))}
        for pr in projects]
    files["projects/time_entries.json"] = entries
    files.update(ledger.files(as_of))
    return files


if __name__ == "__main__":
    main(generate, HERE, __doc__.splitlines()[0])
