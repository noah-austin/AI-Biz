"""HR and payroll for a demo company: people, licenses, weekly timesheets and open roles.

Generalised from Bluestem's operations generator. The profile's PEOPLE dict says who works there:
    head_office: [(title, department, pay type)]                 one person each, at the first branch
    roles: [{"title", "department", "seats": {branch: n} or a number per unit of branch size,
             "quit": monthly chance of leaving, "fill_days": mean days to refill, "pay": "Hourly" or "Salary",
             "lead": title for the first seat (optional)}]
    frontline: the department whose staffing drives overtime and whose licenses matter (e.g. "Field Service")
    short: (branch, [seat numbers]) - planted: these frontline seats were vacated recently and not yet refilled
    growth: [(branch, date)] - new frontline seats opened on these dates
    certs: [(name, years valid or None, department or title it applies to)], license: the cert name that's a legal must
    overtime: {"base": hours, "frontline": hours, "summer": hours, "short_factor": hours per missing share, "branch": {code: extra}}
Sales staff come from the CRM's users, so names match across systems.
"""
import datetime as dt

from .common import month_starts, pick_name


def active_on(e, day):
    d = day.isoformat()
    return e["HireDate"] <= d and (not e["TerminationDate"] or e["TerminationDate"] >= d)


def build_staff(p, R, users, as_of):
    P = p.PEOPLE
    employees, reqs, used = [], [], {u["Name"] for u in users}
    n, rn = [1001], [1]
    hq = p.BRANCHES[0][0]

    def add(name, title, dept, code, hired, pay, manager=None, email=None):
        first, last = name.split(" ", 1)
        e = {"Id": f"E{n[0]}", "FirstName": first, "LastName": last,
             "Email": email or f"{first}.{last}@{p.DOMAIN}".lower(), "JobTitle": title, "Department": dept,
             "LocationCode": code, "HireDate": hired.isoformat(), "TerminationDate": None, "TerminationType": None,
             "ManagerId": manager, "PayType": pay, "EmploymentType": "Full-time"}
        n[0] += 1
        employees.append(e)
        return e

    def open_req(code, title, dept, opened, filled, reason):
        done = filled is not None and filled <= as_of
        reqs.append({"Id": f"REQ-{rn[0]:04d}", "Title": title, "Department": dept, "LocationCode": code,
                     "OpenedDate": opened.isoformat(), "FilledDate": filled.isoformat() if done else None,
                     "Status": "Filled" if done else "Open", "Reason": reason, "Applicants": R("req", rn[0]).randint(3, 28)})
        rn[0] += 1

    rng = R("staff", "head office")
    top = add(pick_name(rng, used), P.get("top_title", "President"), "Leadership", hq, dt.date(2015, 3, 2), "Salary")
    heads = {}
    for title, dept, pay in P["head_office"]:
        e = add(pick_name(rng, used), title, dept, hq, p.START - dt.timedelta(days=rng.randint(300, 2600)), pay, top["Id"])
        heads.setdefault(dept, e["Id"])
    ops_head = heads.get(P.get("frontline_head_dept", "Operations"), top["Id"])

    branch_mgr = {}
    for u in users:
        r = R("staff", u["Id"])
        e = add(u["Name"], u["Title"], "Sales", u["BranchCode"], p.START - dt.timedelta(days=r.randint(200, 2400)), "Salary",
                top["Id"], email=u["Email"])
        if u["Title"] == "Branch Manager":
            branch_mgr[u["BranchCode"]] = e["Id"]
        if not u["IsActive"]:
            e["TerminationDate"], e["TerminationType"] = (p.START + dt.timedelta(days=500)).isoformat(), "Voluntary"
    for e in employees:
        if e["Department"] == "Sales" and e["JobTitle"] != "Branch Manager" and e["Id"] != top["Id"] and e["ManagerId"] == top["Id"] \
                and e["LocationCode"] in branch_mgr and e["Id"] != branch_mgr[e["LocationCode"]]:
            e["ManagerId"] = branch_mgr[e["LocationCode"]]

    short_branch, short_seats = P.get("short", (None, []))
    seats = []
    for role in P["roles"]:
        for code, _city, size, _ in p.BRANCHES:
            k = role["seats"].get(code, 0) if isinstance(role["seats"], dict) else max(1, round(role["seats"] * size))
            seats += [(role, code, i) for i in range(k)]
    growth_seats = [(r, code, 100 + k) for k, (code, _when) in enumerate(P.get("growth", []))
                    for r in P["roles"][:1]]
    opened_at = {(code, 100 + k): when for k, (code, when) in enumerate(P.get("growth", []))}
    for role, code, i in seats + growth_seats:
        r = R("seat", code, role["title"], i)
        frontline = role["department"] == P["frontline"]
        title = role.get("lead") if (i == 0 and role.get("lead")) else role["title"]
        manager = None if frontline else branch_mgr.get(code, top["Id"])
        if (code, i) in opened_at:
            opened = opened_at[(code, i)]
            hired = opened + dt.timedelta(days=max(14, int(r.gauss(role.get("fill_days", 45), 14))))
            open_req(code, title, role["department"], opened, hired, "New position")
        else:
            hired = p.START - dt.timedelta(days=r.randint(60, 3000))
        forced = (as_of - dt.timedelta(days=52 if i == short_seats[0] else 23)) if (
            code == short_branch and role is P["roles"][0] and i in short_seats) else None
        while hired <= as_of:
            e = add(pick_name(r, used), title, role["department"], code, hired, role.get("pay", "Hourly"), manager)
            leave = None
            for m in month_starts(max(hired, p.START), as_of):
                if m > hired and r.random() < role.get("quit", 0.012) * (P.get("quit_branch", {}).get(code, 1.0) if frontline else 1):
                    leave = m + dt.timedelta(days=r.randint(0, 27))
                    break
            if (leave is None or leave > as_of) and forced and hired < forced - dt.timedelta(days=45):
                e["TerminationDate"], e["TerminationType"] = forced.isoformat(), "Voluntary"
                open_req(code, title, role["department"], forced, None, "Replacement")
                break
            if leave is None or leave > as_of:
                break
            e["TerminationDate"] = leave.isoformat()
            e["TerminationType"] = "Voluntary" if r.random() < 0.78 else "Involuntary"
            fill = leave + dt.timedelta(days=max(10, int(r.gauss(role.get("fill_days", 45) * (1.4 if code == short_branch else 1), 16))))
            open_req(code, title, role["department"], leave, fill, "Replacement")
            hired = fill
    # Frontline staff report to their branch lead (or the operations head); leads to the operations head.
    leads = [e for e in employees if e["Department"] == P["frontline"] and any(e["JobTitle"] == r.get("lead") for r in P["roles"])]
    for e in employees:
        if e["Department"] == P["frontline"]:
            if e in leads:
                e["ManagerId"] = ops_head
            else:
                mine = [x for x in leads if x["LocationCode"] == e["LocationCode"] and x["HireDate"] <= e["HireDate"]
                        and (not x["TerminationDate"] or x["TerminationDate"] >= e["HireDate"])]
                e["ManagerId"] = mine[-1]["Id"] if mine else ops_head
    for e in sorted((e for e in employees if not e["TerminationDate"] and e["Department"] == P["frontline"]),
                    key=lambda e: e["HireDate"])[-2:]:
        e["ManagerId"] = None   # planted: the newest two hires were never given a manager
    return employees, reqs


def build_certifications(p, R, employees, as_of):
    P, out, n = p.PEOPLE, [], 1
    for e in employees:
        r = R("certs", e["Id"])
        hired = dt.date.fromisoformat(e["HireDate"])
        for name, years, applies in P.get("certs", []):
            if applies not in (e["Department"], e["JobTitle"]):
                continue
            issued, expires = hired - dt.timedelta(days=r.randint(20, 900)), None
            if years:
                expires = issued + dt.timedelta(days=round(365 * years))
                while expires < as_of:
                    issued, expires = expires, expires + dt.timedelta(days=round(365 * years))
            out.append({"Id": f"CRT-{n:05d}", "EmployeeId": e["Id"], "Certification": name, "IssuedDate": issued.isoformat(),
                        "ExpiresDate": expires.isoformat() if expires else None})
            n += 1
    holders = [c for c in out if c["Certification"] == P.get("license")
               and any(e["Id"] == c["EmployeeId"] and not e["TerminationDate"] for e in employees)]
    for c in holders[3:4] + holders[len(holders) * 2 // 3:len(holders) * 2 // 3 + 1]:   # planted: two lapsed, never renewed
        c["ExpiresDate"] = (as_of - dt.timedelta(days=R("lapse", c["EmployeeId"]).randint(6, 25))).isoformat()
    return out


def build_timesheets(p, R, employees, as_of, start):
    """Weekly hours for hourly staff. Overtime rises when the frontline is short-staffed, in the busy season,
    and in branches the profile singles out."""
    P, O = p.PEOPLE, p.PEOPLE.get("overtime", {})
    last_monday = as_of - dt.timedelta(days=as_of.weekday() + 7)
    front = [e for e in employees if e["Department"] == P["frontline"]]
    seats = {code: sum(1 for e in front if e["LocationCode"] == code and active_on(e, as_of - dt.timedelta(days=200)))
             for code, *_ in p.BRANCHES}
    out, week = [], start - dt.timedelta(days=start.weekday())
    while week <= last_monday:
        for code, *_ in p.BRANCHES:
            crew = sum(1 for e in front if e["LocationCode"] == code and active_on(e, week))
            short = max(0.0, 1 - crew / seats[code]) if seats[code] else 0.0
            for e in employees:
                if e["PayType"] != "Hourly" or e["LocationCode"] != code or not active_on(e, week):
                    continue
                r = R("ts", e["Id"], week.isoformat())
                is_front = e["Department"] == P["frontline"]
                busy = O.get("summer", 2.0) if week.month in O.get("busy_months", (6, 7, 8)) else 0
                mean = (O.get("frontline", 2.5) + busy + O.get("short_factor", 26) * short + O.get("branch", {}).get(code, 0)
                        if is_front else O.get("base", 0.8))
                ot = max(0.0, r.gauss(mean, 2.2))
                pto = 8 * r.choice([0] * 14 + [1, 1, 2, 3, 5])
                hired = dt.date.fromisoformat(e["HireDate"])
                days = 5 - max(0, min(5, (hired - week).days)) if hired > week else 5
                if e["TerminationDate"]:
                    days = min(days, max(0, (dt.date.fromisoformat(e["TerminationDate"]) - week).days + 1))
                out.append({"Id": f"TS-{e['Id']}-{week.isoformat()}", "EmployeeId": e["Id"], "WeekStart": week.isoformat(),
                            "RegularHours": round(max(0.0, 8 * min(5, days) - pto), 1), "OvertimeHours": round(ot if days >= 4 else 0, 1),
                            "PtoHours": float(pto) if days == 5 else 0.0, "Approved": week < last_monday or r.random() < 0.8})
        week += dt.timedelta(days=7)
    missing = [e["Id"] for e in front if e["PayType"] == "Hourly" and active_on(e, last_monday)][5::23][:2]   # planted
    return [t for t in out if not (t["WeekStart"] == last_monday.isoformat() and t["EmployeeId"] in missing)]


def files(p, R, users, as_of, timesheets_from):
    employees, reqs = build_staff(p, R, users, as_of)
    return employees, {
        "hr/employees.json": employees,
        "hr/certifications.json": build_certifications(p, R, employees, as_of),
        "hr/timesheets.json": build_timesheets(p, R, employees, as_of, timesheets_from),
        "hr/requisitions.json": reqs,
    }
