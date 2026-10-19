"""Generate Mesquite Ridge Constructors' systems (a FICTIONAL commercial general contractor) as of a given day.

CRM (bids), job cost (jobs, change orders, monthly costs by category, monthly pay applications with retainage),
accounting (an invoice per pay application, Reference = the CRM deal), purchasing (subcontracts and materials)
and HR/payroll. Won bids become jobs; costs follow an S-curve; the project manager's estimate at completion
catches up with any overrun as the job goes. Stories planted on purpose:
- One Houston project manager's jobs keep losing margin as they go (fade of several points).
- One big San Antonio job is now projected to lose money (and a fading Houston job is about to).
- One Austin job bills two months behind its progress: under-billed, so the company is financing the owner.
- A Houston job has a pile of change orders the owner hasn't signed for months.
- San Antonio is short of field crew: overtime runs high.
- Data problems: a lapsed crane operator certification, staff with no manager, a missing timesheet, a duplicate
  vendor, received orders with no vendor bill, plus the CRM problems.

Usage:  python clients/demo_construction/generate.py [--as-of YYYY-MM-DD] [--out DIR]
"""
import datetime as dt
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent))

import company_profile as p  # noqa: E402

from kit.demos import buying, crm, people  # noqa: E402
from kit.demos.common import Rand, month_starts, poisson  # noqa: E402
from kit.demos.writer import main  # noqa: E402

SPLIT = {"Labor": 0.24, "Materials": 0.26, "Subcontract": 0.44, "Equipment": 0.06}


def s_curve(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def month_end(m):
    return (m + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)


def generate(as_of: dt.date) -> dict:
    R = Rand(p.SEED)
    users, reps = crm.build_users(p, R)
    accounts, by_branch = crm.build_accounts(p, R)
    index = {a["Id"]: a for a in accounts}
    deals = crm.simulate_deals(p, R, reps, by_branch, index, as_of)
    files = crm.crm_files(p, R, deals, users, accounts, as_of)
    employees, hr = people.files(p, R, users, as_of, p.START_OPS)
    files.update(hr)
    pms = {code: [e for e in employees if e["JobTitle"] == "Project Manager" and e["LocationCode"] == code] for code, *_ in p.BRANCHES}
    supers = {code: [e for e in employees if e["JobTitle"] == "Superintendent" and e["LocationCode"] == code] for code, *_ in p.BRANCHES}

    # Planted: the first Houston project manager still on staff lets margin fade on every job.
    fade_pm = next((e for e in pms["HOU"] if people.active_on(e, as_of)), None)
    jobs = []
    for d in deals:
        if d["outcome"] != "won" or d["excluded"] or d["close_day"] > as_of or d["close_day"] < dt.date(2024, 3, 1):
            continue
        r = R("job", d["idx"])
        contract = crm.deal_amount(d)
        margin = (d["margin"] if d["margin"] is not None else p.DEAL_TYPES[d["type"]][6]) / 100
        service = d["type"] == "Service work"
        start = d["close_day"] + dt.timedelta(days=r.randint(7, 21) if service else r.randint(30, 60))
        months = r.randint(1, 3) if service else max(4, min(22, round(5 + 4 * math.log10(max(1.0, contract / 500_000)) + r.uniform(-1, 2))))
        pool = [e for e in pms[d["code"]] if people.active_on(e, min(start, as_of))] or pms[d["code"]]
        pm = pool[d["idx"] % len(pool)] if pool else None
        fading = pm is not None and pm is fade_pm
        jobs.append({"deal": d, "code": d["code"], "contract": contract, "budget": round(contract * (1 - margin), -2),
                     "start": start, "months": months, "end": start + dt.timedelta(days=30 * months), "pm": pm,
                     "super": (supers[d["code"]] or [None])[d["idx"] % max(1, len(supers[d["code"]]))],
                     "overrun": r.uniform(0.06, 0.09) if (fading and not service) else r.gauss(0.0, 0.015),
                     "retainage": 0.05 if service else 0.10, "id": f"JOB-{d['idx']:05d}", "number": f"{start:%y}{d['idx']:04d}",
                     "lag": 0, "cos": []})
    def big(code, taken=(), lo=0.33, hi=0.8):
        """The biggest job in this office that's well under way (between lo and hi of its time gone)."""
        live = [j for j in jobs if j["code"] == code and j["deal"]["type"] != "Service work" and j not in taken
                and lo <= (as_of - j["start"]).days / max(1, (j["end"] - j["start"]).days) <= hi]
        return max(live, key=lambda j: j["contract"], default=None)
    loss = big(p.LOSS_JOB_OFFICE, lo=0.5, hi=0.85)   # far enough along that the estimate has caught up
    if loss:   # enough overrun to end about 4% under water, whatever it was bid at
        loss["overrun"] = 1.04 / (loss["budget"] / loss["contract"]) - 1
    under = big(p.UNDERBILL_OFFICE)
    if under:
        under["lag"] = 1
    pending_job = big(p.PENDING_CO_OFFICE, [j for j in jobs if j["overrun"] > 0.05])

    # Change orders: a few per job, signed by the owner in two to six weeks, except the planted backlog.
    cn = 1
    for j in jobs:
        r = R("co", j["id"])
        for _ in range(poisson(r, max(0.3, j["contract"] / 1_200_000))):
            submitted = j["start"] + dt.timedelta(days=r.randint(20, max(25, j["months"] * 30 - 10)))
            if submitted > as_of:
                continue
            amount = round(j["contract"] * r.uniform(0.008, 0.035), -2)
            approved = submitted + dt.timedelta(days=r.randint(14, 45))
            status = "Approved" if approved <= as_of else "Pending"
            if r.random() < 0.06:
                status, approved = "Rejected", None
            j["cos"].append({"Id": f"CO-{cn:05d}", "JobId": j["id"], "Number": f"{len(j['cos']) + 1:03d}",
                             "Description": r.choice(["Owner-requested scope add", "Unforeseen site condition", "Design change",
                                                      "Allowance overrun", "Code-required upgrade"]),
                             "Amount": amount, "Cost": round(amount * r.uniform(0.8, 0.9), -2), "Status": status,
                             "SubmittedDate": submitted.isoformat(),
                             "ApprovedDate": approved.isoformat() if status == "Approved" else None})
            cn += 1
    if pending_job:
        r = R("pending", pending_job["id"])
        for k in range(4):
            submitted = as_of - dt.timedelta(days=r.randint(70, 160))
            amount = round(pending_job["contract"] * r.uniform(0.01, 0.025), -2)
            pending_job["cos"].append({"Id": f"CO-{cn:05d}", "JobId": pending_job["id"], "Number": f"P{k + 1:02d}",
                                       "Description": "Owner-directed change, awaiting signature", "Amount": amount,
                                       "Cost": round(amount * 0.85, -2), "Status": "Pending", "SubmittedDate": submitted.isoformat(),
                                       "ApprovedDate": None})
            cn += 1

    # Month by month: costs on an S-curve, pay applications with retainage, invoices in accounting.
    ledger = crm.Ledger(R, slow_share=0.10)
    costs, pay_apps, cost_n, pa_n = [], [], 1, 1
    buy = buying.Buying(p, R, as_of)
    for j in jobs:
        r = R("monthly", j["id"])
        billed, cost_so_far, history = 0.0, 0.0, []
        months = list(month_starts(j["start"], min(as_of, j["end"] + dt.timedelta(days=31))))
        for m in months:
            me = month_end(m)
            if me > as_of and m.month != as_of.month:
                break
            asof_m = min(me, as_of)
            x = (asof_m - j["start"]).days / max(1, (j["end"] - j["start"]).days)
            progress = s_curve(x)
            history.append(progress)
            co_cost = sum(c["Cost"] for c in j["cos"] if c["Status"] == "Approved" and c["ApprovedDate"] <= asof_m.isoformat())
            co_amt = sum(c["Amount"] for c in j["cos"] if c["Status"] == "Approved" and c["ApprovedDate"] <= asof_m.isoformat())
            target_cost = (j["budget"] + co_cost) * (1 + j["overrun"]) * progress
            spend = max(0.0, target_cost - cost_so_far) * r.uniform(0.97, 1.03)
            cost_so_far += spend
            for cat, share in SPLIT.items():
                if spend * share >= 1:
                    costs.append({"Id": f"JC-{cost_n:06d}", "JobId": j["id"], "Period": m.isoformat(), "Category": cat,
                                  "Amount": round(spend * share * r.uniform(0.9, 1.1), 2)})
                    cost_n += 1
            if spend > 0:
                buy.order("rental", j["code"], "Equipment", m + dt.timedelta(days=2), [(None, "Equipment rental", 1, round(spend * 0.05, 2))], r, ref=f"OPP-{j['deal']['idx']:05d}")
                vend = "concrete" if r.random() < 0.5 else ("lumber" if r.random() < 0.6 else "steel")
                if vend == "concrete" and r.random() < 0.05:
                    vend = "concrete_dup"
                buy.order(vend, j["code"], "Materials", m + dt.timedelta(days=5), [(None, "Materials for job " + j["number"], 1,
                                                                                    round(spend * SPLIT["Materials"], 2))], r,
                          ref=f"OPP-{j['deal']['idx']:05d}")
            if me > as_of:
                continue   # this month's pay application isn't out yet
            claimed = history[max(0, len(history) - 1 - j["lag"])]
            claimed = min(1.0, claimed * (1.03 if j["lag"] == 0 else 1.0))
            if x >= 1:
                claimed = 1.0
            gross = max(0.0, (j["contract"] + co_amt) * claimed - billed)
            if gross < 1:
                continue
            billed += gross
            held = round(gross * j["retainage"], 2)
            bill_day = me
            pay_apps.append({"Id": f"PA-{pa_n:05d}", "JobId": j["id"], "Period": m.isoformat(), "GrossBilled": round(gross, 2),
                             "RetainageHeld": held, "RetainageReleased": 0.0, "BillDate": bill_day.isoformat()})
            pa_n += 1
            ledger.add(j["deal"]["account"], bill_day, gross - held, f"OPP-{j['deal']['idx']:05d}", f"Pay application {m:%B %Y}, job {j['number']}",
                       f"{j['id']}|{m}")
        # Subcontracts are let at the start of the job.
        if j["start"] <= as_of:
            r2 = R("subs", j["id"])
            trades = r2.sample(["mep", "electric", "drywall", "roofing", "site"], k=3 if j["contract"] > 1_000_000 else 2)
            for t in trades:
                buy.order(t, j["code"], "Subcontract", j["start"], [(None, f"Subcontract, job {j['number']}", 1,
                                                                     round(j["budget"] * SPLIT["Subcontract"] / len(trades), -2))], r2,
                          ref=f"OPP-{j['deal']['idx']:05d}")
        # Retainage comes back after the job is finished and accepted.
        release = j["end"] + dt.timedelta(days=R("ret", j["id"]).randint(40, 80))
        if release <= as_of and pay_apps and any(a["JobId"] == j["id"] for a in pay_apps):
            held = sum(a["RetainageHeld"] for a in pay_apps if a["JobId"] == j["id"])
            pay_apps.append({"Id": f"PA-{pa_n:05d}", "JobId": j["id"], "Period": release.replace(day=1).isoformat(), "GrossBilled": 0.0,
                             "RetainageHeld": 0.0, "RetainageReleased": round(held, 2), "BillDate": release.isoformat()})
            pa_n += 1
            ledger.add(j["deal"]["account"], release, held, f"OPP-{j['deal']['idx']:05d}", f"Retainage release, job {j['number']}",
                       f"{j['id']}|ret")
        j["cost_so_far"] = cost_so_far
        j["progress"] = history[-1] if history else 0.0

    out_jobs = []
    for j in jobs:
        co_cost = sum(c["Cost"] for c in j["cos"] if c["Status"] == "Approved")
        seen = min(1.0, j["progress"] * 1.4)   # the estimate catches up with an overrun as the job goes
        est = (j["budget"] + co_cost) * (1 + j["overrun"] * seen)
        if j["progress"] >= 0.999:
            est = max(est, j["cost_so_far"])
        out_jobs.append({"Id": j["id"], "JobNumber": j["number"], "Name": f'{j["deal"]["account"]["Name"]} - {j["deal"]["descriptor"]}',
                         "AccountId": j["deal"]["account"]["Id"], "DealId": f"OPP-{j['deal']['idx']:05d}", "OfficeCode": j["code"],
                         "ProjectManagerId": j["pm"]["Id"] if j["pm"] else None, "SuperintendentId": j["super"]["Id"] if j["super"] else None,
                         "ContractValue": round(j["contract"], 2), "BudgetCost": j["budget"], "EstimateAtCompletion": round(est, 2),
                         "StartDate": j["start"].isoformat(), "EndDate": j["end"].isoformat(),
                         "Status": "Not started" if j["start"] > as_of else ("Completed" if j["end"] < as_of else "Active"),
                         "RetainagePct": j["retainage"] * 100})
    files["jobcost/jobs.json"] = out_jobs
    files["jobcost/change_orders.json"] = [c for j in jobs for c in j["cos"]]
    files["jobcost/costs.json"] = costs
    files["jobcost/pay_apps.json"] = pay_apps
    files.update(buy.files())
    files.update(ledger.files(as_of))
    return files


if __name__ == "__main__":
    main(generate, HERE, __doc__.splitlines()[0])
