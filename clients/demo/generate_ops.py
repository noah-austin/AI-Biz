"""Bluestem's operations systems: HR and payroll, field service, inventory and purchasing.

Called by generate.py, which passes in its own helpers (as `g`) so both halves share one
seed, one calendar and one cast of accounts and people. Like the CRM and accounting files,
everything here is a pure function of the as-of date, and the systems tie together the way
real ones do: technicians in HR do the jobs in the field-service app, jobs use parts from the
inventory system, and purchasing restocks the warehouses and buys equipment for won projects.

Stories planted on purpose, so each page has something real to find:
- Houston (HOU-05) runs short of technicians: more overtime, slower emergency response.
- Fort Worth (FTW-02) needs more return visits (lower first-time fix).
- One refrigerant vendor keeps raising prices; one motors vendor delivers late.
- A couple of licenses have lapsed on technicians who still have jobs scheduled; others expire soon.
- Data problems for the clean-up list: completed jobs never invoiced, jobs left on people who have
  left, negative stock, parts with no cost, received orders with no vendor bill, a duplicate vendor,
  staff with no manager, and missing timesheets.
"""
import datetime as dt
import math

OPS_START = dt.date(2025, 1, 1)      # purchasing history
JOBS_START = dt.date(2025, 7, 1)     # field-service history (keeps the files a sensible size)
TS_START = dt.date(2025, 6, 30)      # first timesheet week (a Monday)

TECH_SEATS = {"DAL-01": 10, "FTW-02": 6, "AUS-03": 8, "SAT-04": 6, "HOU-05": 8, "HOU-06": 5}
QUIT_PER_MONTH = {"HOU-05": 0.028, "FTW-02": 0.017}   # others 0.013; office staff 0.006
GROWTH_SEATS = [("AUS-03", dt.date(2025, 9, 2)), ("DAL-01", dt.date(2026, 3, 2)), ("SAT-04", dt.date(2026, 8, 3))]
FIRST_TIME_FIX = {"FTW-02": 0.74, "HOU-05": 0.83, "HOU-06": 0.84}  # others 0.88
SLA_HOURS = {"Emergency": 4, "Urgent": 24}

# sku, description, category, base unit cost, weekly use per branch, vendor key, critical
ITEMS = [
    ("FLT-2020", "Pleated filter 20x20x2 (case of 12)", "Filters", 54, 6.0, "prairie", False),
    ("FLT-2424", "Pleated filter 24x24x2 (case of 12)", "Filters", 66, 5.0, "prairie", False),
    ("FLT-1625", "Pleated filter 16x25x2 (case of 12)", "Filters", 48, 4.0, "prairie", False),
    ("FLT-BAG", "Bag filter 24x24x22", "Filters", 31, 3.0, "prairie", False),
    ("FLT-HEPA", "HEPA filter 24x24x12", "Filters", 214, 0.6, "prairie", False),
    ("BLT-A42", "V-belt A42", "Belts", 11, 3.0, "gulf", False),
    ("BLT-B55", "V-belt B55", "Belts", 16, 2.5, "gulf", False),
    ("BLT-B75", "V-belt B75", "Belts", 21, 1.8, "gulf", False),
    ("CAP-3505", "Run capacitor 35/5 MFD", "Capacitors", 19, 4.0, "gulf", True),
    ("CAP-4505", "Run capacitor 45/5 MFD", "Capacitors", 22, 3.0, "gulf", True),
    ("CAP-SUB", "Start capacitor 88-108 MFD", "Capacitors", 17, 1.5, "gulf", True),
    ("CON-2P30", "Contactor 2-pole 30A", "Contactors", 27, 3.0, "texan", True),
    ("CON-3P40", "Contactor 3-pole 40A", "Contactors", 48, 1.6, "texan", True),
    ("MTR-CF14", "Condenser fan motor 1/4 HP", "Motors", 186, 1.2, "redline", True),
    ("MTR-CF12", "Condenser fan motor 1/2 HP", "Motors", 242, 0.9, "redline", True),
    ("MTR-BL34", "Blower motor 3/4 HP ECM", "Motors", 418, 0.6, "redline", False),
    ("MTR-PMP", "Pump motor 5 HP", "Motors", 905, 0.15, "redline", False),
    ("REF-410", "Refrigerant R-410A (25 lb)", "Refrigerant", 262, 2.2, "lonestar", True),
    ("REF-454", "Refrigerant R-454B (25 lb)", "Refrigerant", 391, 1.0, "lonestar", True),
    ("REF-134", "Refrigerant R-134a (30 lb)", "Refrigerant", 214, 0.7, "lonestar", False),
    ("REF-22", "Refrigerant R-22, reclaimed (30 lb)", "Refrigerant", 655, 0.0, "lonestar", False),
    ("CTL-TSTAT", "Programmable thermostat", "Controls", 138, 1.2, "summit", False),
    ("CTL-SNS", "Duct temperature sensor", "Controls", 54, 1.4, "summit", False),
    ("CTL-ACT", "Damper actuator 24V", "Controls", 229, 0.7, "summit", False),
    ("CTL-BAC", "BACnet controller", "Controls", 1260, 0.12, "summit", False),
    ("CTL-PNU", "Pneumatic thermostat (legacy)", "Controls", 96, 0.0, "summit", False),
    ("ELE-FUS", "Fuse 30A time delay (10 pack)", "Electrical", 28, 2.0, "texan", False),
    ("ELE-BRK", "Breaker 2-pole 40A", "Electrical", 64, 0.8, "texan", False),
    ("ELE-DIS", "Fused disconnect 60A", "Electrical", 118, 0.5, "texan", False),
    ("ELE-WIRE", "THHN wire 12 AWG (500 ft)", "Electrical", 132, 0.6, "texan", False),
    ("VLV-TXV", "Thermal expansion valve 3-5 ton", "Valves", 158, 0.6, "gulf", False),
    ("VLV-BALL", "Ball valve 1 in", "Valves", 34, 1.0, "hillcountry", False),
    ("VLV-ZONE", "Zone valve 3/4 in", "Valves", 121, 0.5, "hillcountry", False),
    ("CMP-3T", "Scroll compressor 3 ton", "Compressors", 1390, 0.15, "gulf", False),
    ("CMP-5T", "Scroll compressor 5 ton", "Compressors", 1940, 0.1, "gulf", False),
    ("CMP-REC", "Reciprocating compressor 7.5 ton (discontinued)", "Compressors", 3720, 0.0, "gulf", False),
    ("PMP-CIRC", "Circulator pump 1/6 HP", "Pumps", 288, 0.3, "hillcountry", False),
    ("PMP-COND", "Condensate pump", "Pumps", 92, 0.9, "hillcountry", False),
    ("WTR-INH", "Cooling tower inhibitor (5 gal)", "Water treatment", 118, 0.8, "hillcountry", False),
    ("WTR-BIO", "Biocide (5 gal)", "Water treatment", 96, 0.7, "hillcountry", False),
    ("SUP-COIL", "Coil cleaner (gallon)", "Supplies", 22, 3.0, "gulf", False),
    ("SUP-TAPE", "Foil tape (case)", "Supplies", 46, 1.0, "gulf", False),
    ("SUP-DRY", "Filter drier 3/8 in", "Supplies", 18, 1.6, "gulf", False),
]
NO_COST = {"SUP-TAPE", "ELE-WIRE"}

# key, name, category, terms days, lead days, chance of arriving late, yearly price drift
VENDORS = [
    ("gulf", "Gulf Coast HVAC Supply", "Parts", 30, 3, 0.08, 0.03),
    ("lonestar", "Lone Star Refrigerants", "Refrigerant", 30, 4, 0.10, 0.12),
    ("redline", "RedLine Motors & Drives", "Parts", 45, 6, 0.38, 0.04),
    ("prairie", "Prairie Filters Co.", "Parts", 30, 4, 0.06, 0.02),
    ("summit", "Summit Controls", "Controls", 30, 7, 0.12, 0.03),
    ("texan", "Texan Electrical Wholesale", "Electrical", 30, 2, 0.07, 0.03),
    ("hillcountry", "Hill Country Plumbing Supply", "Parts", 30, 3, 0.09, 0.03),
    ("equipment", "Brazos Mechanical Equipment", "Equipment", 45, 40, 0.25, 0.04),
    ("crane", "Pecos Crane & Rigging", "Subcontract", 30, 10, 0.05, 0.03),
    ("sheetmetal", "Alamo Sheet Metal", "Subcontract", 30, 14, 0.12, 0.03),
    ("gulf_dup", "GULF COAST HVAC SUPPLY INC", "Parts", 30, 3, 0.08, 0.03),
]
CERTS = [  # name, years valid, who needs it
    ("State HVAC license (TDLR)", 1, "tech"),
    ("EPA 608 Universal", None, "tech"),
    ("NATE certification", 2, "lead"),
    ("DOT medical card", 2, "tech"),
    ("OSHA 30", None, "lead"),
    ("Forklift operator", 3, "warehouse"),
]


def _month_starts(start, end):
    d = start.replace(day=1)
    while d <= end:
        yield d
        d = (d + dt.timedelta(days=32)).replace(day=1)


def _poisson(rng, lam):
    if lam <= 0:
        return 0
    if lam > 30:
        return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))
    k, p, target = 0, 1.0, math.exp(-lam)
    while True:
        p *= rng.random()
        if p <= target:
            return k
        k += 1


def _ts_from_dt(t):
    """A Central local time as UTC (Central is UTC-5 or -6; -5 is close enough for a demo)."""
    return (t + dt.timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- people

def build_staff(g, users, as_of):
    """Everyone on payroll since 2024: sales (the CRM's users), technicians, branch office and head office.
    Returns employees, requisitions and a helper to find who was active on a day."""
    employees, reqs = [], []
    n = [1001]

    def add(name, title, dept, code, hired, pay="Hourly", manager=None, email=None, rng=None):
        eid = f"E{n[0]}"
        n[0] += 1
        first, last = name.split(" ", 1)
        employees.append({"Id": eid, "FirstName": first, "LastName": last, "Email": email or f"{first}.{last}@bluestem.example".lower(),
                          "JobTitle": title, "Department": dept, "LocationCode": code, "HireDate": hired.isoformat(),
                          "TerminationDate": None, "TerminationType": None, "ManagerId": manager, "PayType": pay,
                          "EmploymentType": "Full-time"})
        return employees[-1]

    rng = g.rng_for("staff", "head office")
    president = add("Morgan Ellison", "President", "Leadership", "DAL-01", dt.date(2016, 3, 1), "Salary", rng=rng)
    ops_dir = add("Avery Castillo", "Director of Operations", "Operations", "DAL-01", dt.date(2018, 6, 4), "Salary", president["Id"])
    add("Riley Nolan", "Controller", "Finance", "DAL-01", dt.date(2019, 1, 14), "Salary", president["Id"])
    add("Jamie Pruitt", "AP Specialist", "Finance", "DAL-01", dt.date(2021, 8, 2), "Hourly", president["Id"])
    add("Sydney Holloway", "HR Generalist", "People", "DAL-01", dt.date(2022, 2, 7), "Salary", president["Id"])

    # Sales: the CRM's users, with the same names, emails and branches.
    branch_mgr = {}
    for u in users:
        r = g.rng_for("staff", u["Id"])
        hired = g.START - dt.timedelta(days=r.randint(200, 2400))
        e = add(u["Name"], u["Title"], "Sales", u["BranchCode"], hired, "Salary", president["Id"], email=u["Email"])
        if u["Title"] == "Branch Manager":
            branch_mgr[u["BranchCode"]] = e["Id"]
        if not u["IsActive"]:
            e["TerminationDate"], e["TerminationType"] = "2025-05-16", "Voluntary"
    for e in employees:
        if e["Department"] == "Sales" and e["JobTitle"] == "Account Executive":
            e["ManagerId"] = branch_mgr.get(e["LocationCode"], president["Id"])

    # Field and branch staff, as seats that people fill, leave and get refilled.
    seats = []
    for code, size in TECH_SEATS.items():
        seats += [(code, "tech", i, size) for i in range(size)]
        seats += [(code, "coord", 0, 1), (code, "parts", 0, 1)]
    seats += [(code, "tech", 100 + k, None) for k, (code, _when) in enumerate(GROWTH_SEATS)]
    growth_open = {(code, 100 + k): when for k, (code, when) in enumerate(GROWTH_SEATS)}

    def title_for(kind, i, size):
        if kind == "coord":
            return "Service Coordinator", "Operations"
        if kind == "parts":
            return "Parts Clerk", "Warehouse"
        if i == 0:
            return "Lead Technician", "Field Service"
        if size is not None and i == size - 1:
            return "Apprentice Technician", "Field Service"
        return "HVAC Technician", "Field Service"

    req_n = [1]

    def open_req(code, title, dept, opened, filled, reason):
        rid = f"REQ-{req_n[0]:04d}"
        req_n[0] += 1
        reqs.append({"Id": rid, "Title": title, "Department": dept, "LocationCode": code, "OpenedDate": opened.isoformat(),
                     "FilledDate": filled.isoformat() if filled and filled <= as_of else None,
                     "Status": "Filled" if filled and filled <= as_of else "Open", "Reason": reason,
                     "Applicants": None})
        return rid

    # Planted: Houston lost two technicians recently and hasn't replaced them yet.
    forced = {("HOU-05", "tech", 2): as_of - dt.timedelta(days=52), ("HOU-05", "tech", 5): as_of - dt.timedelta(days=23)}
    for code, kind, i, size in seats:
        r = g.rng_for("seat", code, kind, i)
        title, dept = title_for(kind, i, size)
        manager = branch_mgr.get(code) if kind != "tech" else None
        quit_p = (QUIT_PER_MONTH.get(code, 0.013) if kind == "tech" else 0.006)
        if (code, i) in growth_open and kind == "tech":
            opened = growth_open[(code, i)]
            hired = opened + dt.timedelta(days=max(14, int(r.gauss(48, 14))))
            open_req(code, title, dept, opened, hired, "New position")
        else:
            hired = g.START - dt.timedelta(days=r.randint(60, 3000))
        while hired <= as_of:
            first, last = r.choice(g.FIRST), r.choice(g.LAST)
            e = add(f"{first} {last}", title, dept, code, hired, "Hourly", manager)
            e["_seat"] = (code, kind, i)
            # Months until they leave.
            leave = None
            for m in _month_starts(max(hired, g.START), as_of):
                if m <= hired:
                    continue
                if r.random() < quit_p:
                    leave = m + dt.timedelta(days=r.randint(0, 27))
                    break
            force = forced.get((code, kind, i))
            if (leave is None or leave > as_of) and force and hired < force - dt.timedelta(days=45):
                e["TerminationDate"], e["TerminationType"] = force.isoformat(), "Voluntary"
                open_req(code, title, dept, force, None, "Replacement")
                break
            if leave is None or leave > as_of:
                break
            e["TerminationDate"] = leave.isoformat()
            e["TerminationType"] = "Voluntary" if r.random() < 0.78 else "Involuntary"
            fill = leave + dt.timedelta(days=max(10, int(r.gauss(46 if code != "HOU-05" else 68, 16))))
            open_req(code, title, dept, leave, fill, "Replacement")
            hired = fill
    # Technicians report to their branch's lead technician; leads to the director of operations.
    for e in employees:
        if e["Department"] == "Field Service":
            if e["JobTitle"] == "Lead Technician":
                e["ManagerId"] = ops_dir["Id"]
            else:
                leads = [x for x in employees if x["JobTitle"] == "Lead Technician" and x["LocationCode"] == e["LocationCode"]
                         and x["HireDate"] <= e["HireDate"] and (not x["TerminationDate"] or x["TerminationDate"] >= e["HireDate"])]
                e["ManagerId"] = (leads[-1]["Id"] if leads else ops_dir["Id"])
    # Planted: the two most recent hires were never given a manager in HR.
    recent = sorted((e for e in employees if not e["TerminationDate"] and e["Department"] == "Field Service"),
                    key=lambda e: e["HireDate"])[-2:]
    for e in recent:
        e["ManagerId"] = None
    for r_ in reqs:
        r_["Applicants"] = g.rng_for("req", r_["Id"]).randint(3, 28)
    return employees, reqs


def active_on(e, day):
    return e["HireDate"] <= day.isoformat() and (not e["TerminationDate"] or e["TerminationDate"] >= day.isoformat())


def build_certifications(g, employees, as_of):
    out, n = [], 1
    for e in employees:
        kind = ("lead" if e["JobTitle"] == "Lead Technician" else "tech" if e["Department"] == "Field Service"
                else "warehouse" if e["Department"] == "Warehouse" else None)
        if not kind:
            continue
        r = g.rng_for("certs", e["Id"])
        hired = dt.date.fromisoformat(e["HireDate"])
        for name, years, who in CERTS:
            if not (who == kind or (who == "tech" and kind == "lead")):
                continue
            issued = hired - dt.timedelta(days=r.randint(20, 900))
            expires = None
            if years:
                # Renewed on time until now, so the current one runs out sometime in the next term.
                expires = issued + dt.timedelta(days=365 * years)
                while expires < as_of - dt.timedelta(days=30):
                    issued, expires = expires, expires + dt.timedelta(days=365 * years)
            out.append({"Id": f"CRT-{n:05d}", "EmployeeId": e["Id"], "Certification": name, "IssuedDate": issued.isoformat(),
                        "ExpiresDate": expires.isoformat() if expires else None})
            n += 1
    # Planted: two active technicians whose state license lapsed and was never renewed.
    techs = [e for e in employees if not e["TerminationDate"] and e["Department"] == "Field Service"]
    for pick in (techs[3], techs[17]):
        for c in out:
            if c["EmployeeId"] == pick["Id"] and c["Certification"].startswith("State HVAC"):
                c["ExpiresDate"] = (as_of - dt.timedelta(days=g.rng_for("lapse", pick["Id"]).randint(6, 25))).isoformat()
    return out


# ---------------------------------------------------------------- field service

def build_jobs(g, employees, accounts_by_branch, acct_index, as_of):
    techs_by_branch = {}
    for e in employees:
        if e["Department"] == "Field Service":
            techs_by_branch.setdefault(e["LocationCode"], []).append(e)
    jobs, parts = [], []
    n, pn = [1], [1]
    weights = [(it[0], it[4]) for it in ITEMS if it[4] > 0]

    def add_parts(job, kind, day, code, rng):
        k = {"Repair": rng.choice([0, 1, 1, 2, 2, 3]), "Maintenance visit": rng.choice([1, 1, 2]),
             "Install": rng.choice([2, 3, 4])}[kind]
        for _ in range(k):
            if kind == "Maintenance visit":
                sku = rng.choice(["FLT-2020", "FLT-2424", "FLT-1625", "FLT-BAG", "BLT-A42", "BLT-B55", "SUP-COIL", "WTR-INH", "WTR-BIO"])
            else:
                sku = rng.choices([w[0] for w in weights], [w[1] for w in weights])[0]
            loc = f"VAN-{code[:3]}{code[-1]}" if rng.random() < 0.8 else f"WH-{code}"
            parts.append({"Id": f"WOP-{pn[0]:06d}", "WorkOrderId": job["Id"], "Sku": sku, "Qty": rng.choice([1, 1, 1, 2, 2, 4]),
                          "LocationId": loc, "UsedDate": day.isoformat()})
            pn[0] += 1

    for day in g.business_days(JOBS_START, as_of + dt.timedelta(days=14)):
        for code, _city, size, _ in g.BRANCHES:
            rng = g.rng_for("jobs", day.isoformat(), code)
            crew = [e for e in techs_by_branch.get(code, []) if active_on(e, min(day, as_of))]
            seats = TECH_SEATS[code] + sum(1 for c, w in GROWTH_SEATS if c == code and w <= day)
            staffing = len(crew) / seats if seats else 1
            demand = seats * 2.15 * g.season(day)
            count = _poisson(rng, demand)
            future = day > as_of
            if future:
                count = _poisson(rng, demand * (0.45 if (day - as_of).days < 4 else 0.2))  # only routine work booked ahead
            for _ in range(count):
                pool = accounts_by_branch[code]
                acc = acct_index[pool[min(len(pool) - 1, int(rng.paretovariate(1.3)) - 1 + rng.randint(0, 5))]]
                kind = rng.choices(["Repair", "Maintenance visit", "Install"], [0.55, 0.36, 0.09])[0]
                prio = rng.choices(["Emergency", "Urgent", "Routine"], [0.2, 0.4, 0.4])[0] if kind == "Repair" else "Routine"
                if future:
                    prio = "Routine"
                created_dt = dt.datetime.combine(day, dt.time(7, 0)) + dt.timedelta(minutes=rng.randint(0, 9 * 60))
                if prio == "Routine":
                    created_dt -= dt.timedelta(days=rng.randint(1, 12))
                tech = rng.choice(crew) if crew else None
                # Response: short-staffed branches answer slower.
                if prio == "Emergency":
                    arrive = created_dt + dt.timedelta(hours=max(0.6, rng.gauss(2.9 + 2.6 * max(0, 1 - staffing), 1.0)))
                elif prio == "Urgent":
                    arrive = created_dt + dt.timedelta(hours=max(1.5, rng.gauss(13 + 16 * max(0, 1 - staffing), 6)))
                else:
                    arrive = dt.datetime.combine(day, dt.time(8, 0)) + dt.timedelta(minutes=rng.randint(0, 8 * 60))
                    if rng.random() < 0.05:
                        arrive += dt.timedelta(days=rng.randint(1, 3))
                hours = round(max(0.5, rng.gauss({"Repair": 2.4, "Maintenance visit": 1.9, "Install": 6.5}[kind], 0.9)), 1)
                done = arrive + dt.timedelta(hours=hours)
                status = "Completed"
                if arrive.date() > as_of:
                    status = "Scheduled"
                elif done.date() > as_of or (done.date() == as_of and rng.random() < 0.4):
                    status = "In progress"
                if status == "Completed" and rng.random() < 0.02:
                    status = "Canceled"
                billable = kind != "Maintenance visit"
                amount = round(hours * 135 + (rng.uniform(80, 900) if kind == "Repair" else rng.uniform(1500, 9000) if kind == "Install" else 0), 2)
                jid = f"WO-{n[0]:06d}"
                n[0] += 1
                job = {"Id": jid, "JobNumber": f"{n[0] - 1 + 40000}", "AccountId": acc["Id"], "BranchCode": code,
                       "JobType": kind, "Priority": prio, "Status": status,
                       "CreatedAt": _ts_from_dt(min(created_dt, dt.datetime.combine(as_of, dt.time(17, 0)))),
                       "ScheduledDate": day.isoformat(),
                       "ArrivedAt": _ts_from_dt(arrive) if status in ("Completed", "In progress") else None,
                       "CompletedAt": _ts_from_dt(done) if status == "Completed" else None,
                       "TechnicianId": tech["Id"] if tech else None, "LaborHours": hours if status == "Completed" else None,
                       "Billable": billable, "BillableAmount": amount if billable and status == "Completed" else None,
                       "InvoiceNumber": None, "IsCallback": False, "ParentWorkOrderId": None}
                if status == "Completed" and billable:
                    inv_day = done.date() + dt.timedelta(days=rng.randint(0, 6))
                    missed = rng.random() < 0.008 and done.date() >= as_of - dt.timedelta(days=200)
                    if inv_day <= as_of and not missed:
                        job["InvoiceNumber"] = f"FS-{n[0] + 70000}"
                jobs.append(job)
                if status == "Completed":
                    add_parts(job, kind, done.date(), code, rng)
                # A return visit when the first one didn't fix it.
                if status == "Completed" and kind == "Repair" and rng.random() > FIRST_TIME_FIX.get(code, 0.88):
                    back = done + dt.timedelta(days=rng.randint(1, 18), hours=rng.randint(-3, 3))
                    if back.date() <= as_of:
                        cb_hours = round(max(0.5, rng.gauss(1.8, 0.7)), 1)
                        cid = f"WO-{n[0]:06d}"
                        n[0] += 1
                        cb_tech = rng.choice([e for e in techs_by_branch.get(code, []) if active_on(e, back.date())] or [tech] if tech else [None])
                        jobs.append({**job, "Id": cid, "JobNumber": f"{n[0] - 1 + 40000}", "Priority": "Urgent",
                                     "CreatedAt": _ts_from_dt(back - dt.timedelta(hours=6)), "ScheduledDate": back.date().isoformat(),
                                     "ArrivedAt": _ts_from_dt(back), "CompletedAt": _ts_from_dt(back + dt.timedelta(hours=cb_hours)),
                                     "TechnicianId": cb_tech["Id"] if cb_tech else None, "LaborHours": cb_hours,
                                     "Billable": False, "BillableAmount": None, "InvoiceNumber": None,
                                     "IsCallback": True, "ParentWorkOrderId": jid, "Status": "Completed"})
                        add_parts(jobs[-1], "Repair", back.date(), code, rng)
    return jobs, parts


# ---------------------------------------------------------------- inventory and purchasing

def build_inventory(g, parts, as_of):
    items = []
    vendor_name = {v[0]: f"V{100 + k}" for k, v in enumerate(VENDORS)}
    for sku, desc, cat, cost, weekly, vend, critical in ITEMS:
        items.append({"Sku": sku, "Description": desc, "Category": cat,
                      "StandardCost": None if sku in NO_COST else round(price_on(sku, cost, vend, as_of), 2),
                      "PreferredVendorId": vendor_name[vend], "Critical": critical, "Active": True})
    locations = []
    for code, city, *_ in g.BRANCHES:
        locations.append({"Id": f"WH-{code}", "Name": f"{city} warehouse", "Kind": "Warehouse", "BranchCode": code})
        locations.append({"Id": f"VAN-{code[:3]}{code[-1]}", "Name": f"{city} service vans", "Kind": "Van stock", "BranchCode": code})
    last_use = {}
    for p in parts:
        key = (p["LocationId"], p["Sku"])
        if p["UsedDate"] > last_use.get(key, ""):
            last_use[key] = p["UsedDate"]
    stock = []
    for loc in locations:
        size = next(b[2] for b in g.BRANCHES if b[0] == loc["BranchCode"])
        for sku, desc, cat, cost, weekly, vend, critical in ITEMS:
            r = g.rng_for("stock", loc["Id"], sku)
            wk = weekly * size
            rp = rq = None
            if loc["Kind"] == "Warehouse":
                rp, rq = max(1, round(wk * 2)), max(2, round(wk * 4))
                if weekly == 0:
                    rp, rq = 0, 0
                on_hand = rp + r.randint(0, rq) if r.random() > 0.12 else r.randint(0, max(0, rp - 1))
                if weekly == 0:
                    on_hand = r.randint(3, 14) if sku != "CMP-REC" else 2   # legacy parts nobody uses any more
            else:
                on_hand = r.randint(0, max(1, round(wk * 1.2)))
                if weekly == 0:
                    continue
            if weekly == 0 and loc["Kind"] == "Warehouse":
                last = (as_of - dt.timedelta(days=r.randint(220, 640))).isoformat()
            else:
                last = last_use.get((loc["Id"], sku))
            stock.append({"Id": f"{loc['Id']}|{sku}", "LocationId": loc["Id"], "Sku": sku, "OnHand": on_hand,
                          "ReorderPoint": rp, "ReorderQty": rq,
                          "LastIssuedDate": last, "LastCountedDate": (as_of - dt.timedelta(days=r.randint(3, 95))).isoformat()})
    # Planted: critical parts out of stock in Houston, and two negative balances from issues posted before receipts.
    for row in stock:
        if row["LocationId"] == "WH-HOU-05" and row["Sku"] in ("CAP-3505", "MTR-CF14"):
            row["OnHand"] = 0
        if row["Id"] in ("WH-SAT-04|ELE-FUS", "WH-HOU-06|BLT-B55"):
            row["OnHand"] = -2 if row["Sku"] == "ELE-FUS" else -1
    adjustments = []
    n = 1
    for m in _month_starts(as_of - dt.timedelta(days=365), as_of):
        for loc in locations:
            if loc["Kind"] != "Warehouse":
                continue
            r = g.rng_for("count", loc["Id"], m.isoformat())
            day = m + dt.timedelta(days=r.randint(1, 25))
            if day > as_of:
                continue
            for _ in range(r.randint(3, 7)):
                sku = r.choice([it[0] for it in ITEMS if it[4] > 0])
                shrink = 0.75 if loc["BranchCode"] != "HOU-06" else 0.9
                qty = -r.randint(1, 4) if r.random() < shrink else r.randint(1, 2)
                adjustments.append({"Id": f"ADJ-{n:05d}", "Date": day.isoformat(), "LocationId": loc["Id"], "Sku": sku,
                                    "Qty": qty, "Reason": "Cycle count" if r.random() < 0.85 else "Damaged"})
                n += 1
    return items, locations, stock, adjustments


def price_on(sku, base, vend, day):
    drift = next(v[6] for v in VENDORS if v[0] == vend)
    years = (day - OPS_START).days / 365
    return base * (1 + drift * years)


def build_purchasing(g, deals, as_of):
    vendors = [{"Id": f"V{100 + k}", "Name": name, "Category": cat, "TermsDays": terms}
               for k, (_key, name, cat, terms, _lead, _late, _drift) in enumerate(VENDORS)]
    vid = {v[0]: f"V{100 + k}" for k, v in enumerate(VENDORS)}
    vinfo = {v[0]: v for v in VENDORS}
    pos, lines = [], []
    n, ln = [1], [1]

    def add_po(vendor_key, code, kind, ordered, amount_lines, deal_id=None, rng=None):
        _k, name, cat, terms, lead, late_p, _drift = vinfo[vendor_key]
        expected = ordered + dt.timedelta(days=max(1, int(rng.gauss(lead, lead * 0.25))))
        late = rng.random() < late_p
        received = expected + dt.timedelta(days=rng.randint(2, 12) if late else -rng.randint(0, 1))
        canceled = rng.random() < 0.015
        po_id = f"PO-{n[0]:05d}"
        n[0] += 1
        amount = round(sum(q * p for _s, _d, q, p in amount_lines), 2)
        billed = None
        status = "Open"
        if canceled:
            status, received = "Canceled", None
        elif received <= as_of:
            status = "Received"
            bill_day = received + dt.timedelta(days=rng.randint(3, 22))
            if bill_day <= as_of and not (rng.random() < 0.035 and received >= as_of - dt.timedelta(days=200)):
                status, billed = "Closed", amount
        else:
            received = None
        pos.append({"Id": po_id, "PONumber": f"{n[0] - 1 + 20000}", "VendorId": vid[vendor_key], "BranchCode": code, "Kind": kind,
                    "OrderedDate": ordered.isoformat(),
                    "ExpectedDate": None if rng.random() < 0.012 else expected.isoformat(),
                    "ReceivedDate": received.isoformat() if received else None, "Status": status,
                    "Amount": amount, "BilledAmount": billed, "DealId": deal_id})
        for sku, desc, q, p in amount_lines:
            lines.append({"Id": f"POL-{ln[0]:06d}", "POId": po_id, "Sku": sku, "Description": desc, "Qty": q, "UnitPrice": round(p, 2)})
            ln[0] += 1

    # Weekly restocking for each warehouse: the vendors with the most parts due, a few lines each.
    for code, _city, size, _ in g.BRANCHES:
        d = OPS_START + dt.timedelta(days=(1 - OPS_START.weekday()) % 7)
        while d <= as_of:
            r = g.rng_for("restock", code, d.isoformat())
            picks = r.sample([it for it in ITEMS if it[4] > 0], k=min(9, 4 + int(size * 4)))
            by_vendor = {}
            for sku, desc, cat, cost, weekly, vend, crit in picks:
                if vend == "gulf" and r.random() < 0.04:
                    vend = "gulf_dup"   # the duplicate vendor record gets used now and then
                q = max(1, round(weekly * size * r.uniform(2.5, 5)))
                by_vendor.setdefault(vend, []).append((sku, desc, q, price_on(sku, cost, vend if vend != "gulf_dup" else "gulf", d) * r.uniform(0.98, 1.03)))
            for vend, ls in sorted(by_vendor.items()):
                add_po(vend, code, "Parts", d, ls, rng=r)
            d += dt.timedelta(days=7)
    # Equipment and subcontract orders for won projects.
    for deal in deals:
        if deal["outcome"] != "won" or deal["type"] != "Project" or deal["excluded"]:
            continue
        ordered = deal["close_day"] + dt.timedelta(days=7)
        if ordered < OPS_START or ordered > as_of:
            continue
        r = g.rng_for("projpo", deal["idx"])
        amount = next(v for d_, f, o, v in reversed(deal["events"]) if f == "Amount")
        ref = f"OPP-{deal['idx']:05d}"
        add_po("equipment", deal["code"], "Equipment", ordered,
               [(None, f"Equipment for {deal['descriptor'].lower()}", 1, round(amount * r.uniform(0.28, 0.42), -1))], ref, rng=r)
        if r.random() < 0.35:
            vend = "crane" if r.random() < 0.5 else "sheetmetal"
            add_po(vend, deal["code"], "Subcontract", ordered + dt.timedelta(days=r.randint(5, 30)),
                   [(None, "Crane and rigging" if vend == "crane" else "Ductwork fabrication", 1, round(r.uniform(2500, 14000), -1))],
                   ref, rng=r)
    return vendors, pos, lines


# ---------------------------------------------------------------- payroll

def build_timesheets(g, employees, as_of):
    """Weekly hours for everyone paid hourly. Overtime rises when a branch is short of technicians and in summer."""
    last_monday = as_of - dt.timedelta(days=as_of.weekday() + 7)
    out = []
    week = TS_START
    while week <= last_monday:
        for code, *_ in g.BRANCHES:
            crew = [e for e in employees if e["Department"] == "Field Service" and e["LocationCode"] == code and active_on(e, week)]
            seats = TECH_SEATS[code] + sum(1 for c, w in GROWTH_SEATS if c == code and w <= week)
            short = max(0.0, 1 - len(crew) / seats)
            for e in employees:
                if e["PayType"] != "Hourly" or e["LocationCode"] != code or not active_on(e, week):
                    continue
                r = g.rng_for("ts", e["Id"], week.isoformat())
                summer = 2.5 if week.month in (6, 7, 8) else 0
                field = e["Department"] == "Field Service"
                ot = max(0.0, r.gauss((2.0 + summer + 26 * short + (1.5 if code == "HOU-05" else 0)) if field else 0.8, 2.2))
                pto = 8 * r.choice([0] * 14 + [1, 1, 2, 3, 5])
                hired = dt.date.fromisoformat(e["HireDate"])
                days = 5 - max(0, min(5, (hired - week).days)) if hired > week else 5
                if e["TerminationDate"]:
                    days = min(days, max(0, (dt.date.fromisoformat(e["TerminationDate"]) - week).days + 1))
                regular = max(0.0, 8 * min(5, days) - pto)
                out.append({"Id": f"TS-{e['Id']}-{week.isoformat()}", "EmployeeId": e["Id"], "WeekStart": week.isoformat(),
                            "RegularHours": round(regular, 1), "OvertimeHours": round(ot if days >= 4 else 0, 1),
                            "PtoHours": float(pto) if days == 5 else 0.0, "Approved": week < last_monday or r.random() < 0.8})
        week += dt.timedelta(days=7)
    # Planted: two people never turned in last week's timesheet.
    missing = [e["Id"] for e in employees if e["PayType"] == "Hourly" and active_on(e, last_monday)
               and e["Department"] == "Field Service"][5::23][:2]
    return [t for t in out if not (t["WeekStart"] == last_monday.isoformat() and t["EmployeeId"] in missing)]


# ---------------------------------------------------------------- all of it

def build(g, deals, users, accounts, accounts_by_branch, as_of):
    acct_index = {a["Id"]: a for a in accounts}
    employees, reqs = build_staff(g, users, as_of)
    certs = build_certifications(g, employees, as_of)
    jobs, parts = build_jobs(g, employees, accounts_by_branch, acct_index, as_of)
    items, locations, stock, adjustments = build_inventory(g, parts, as_of)
    vendors, pos, lines = build_purchasing(g, deals, as_of)
    timesheets = build_timesheets(g, employees, as_of)
    # Planted: jobs still booked to technicians who have left (dispatch never reassigned them).
    gone = [e for e in employees if e["Department"] == "Field Service" and e["TerminationDate"]
            and dt.date.fromisoformat(e["TerminationDate"]) >= as_of - dt.timedelta(days=60)]
    for k, job in enumerate(j for j in jobs if j["Status"] == "Scheduled"):
        if k % 37 == 5 and gone:
            pick = gone[k % len(gone)]
            if pick["LocationCode"] == job["BranchCode"]:
                job["TechnicianId"] = pick["Id"]
    clean = lambda rows: [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    return {
        "hr/employees.json": clean(employees),
        "hr/certifications.json": certs,
        "hr/timesheets.json": timesheets,
        "hr/requisitions.json": reqs,
        "fieldservice/work_orders.json": jobs,
        "fieldservice/work_order_parts.json": parts,
        "inventory/items.json": items,
        "inventory/locations.json": locations,
        "inventory/stock.json": stock,
        "inventory/adjustments.json": adjustments,
        "purchasing/vendors.json": vendors,
        "purchasing/purchase_orders.json": pos,
        "purchasing/po_lines.json": lines,
    }
