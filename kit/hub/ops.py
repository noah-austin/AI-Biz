"""Operations pages: Field service, Inventory, Purchasing and People. The numbers come from kit/metrics.py."""
import datetime as dt

from .. import db, metrics
from . import ui
from .ui import esc, money, pct


def _scope(request):
    return request.state.user["branches"] or None


def _hrs(v) -> str:
    return "—" if v is None else f"{float(v):.1f} hrs"


def _pct_bars(rows, key, sub, label):
    """Bars for a rate (0 to 1) on a 0-100% scale, so a short bar always means a low rate."""
    return ui.hbars([{"label": r["branch"], "value": (r[key] or 0) * 100, "shown": pct(r[key], 0), "sub": sub(r)}
                     for r in rows if r[key] is not None], label=label, top=100)


def _table(head: list[str], rows: list[str], empty: str, numeric=()) -> str:
    th = "".join(f'<th{" class=n" if i in numeric else ""}>{esc(h)}</th>' for i, h in enumerate(head))
    return (f'<div class="scroll"><table class="data"><thead><tr>{th}</tr></thead><tbody>'
            f'{"".join(rows) or f"<tr><td colspan={len(head)}>{esc(empty)}</td></tr>"}</tbody></table></div>')


# ---------------------------------------------------------------- field service

def jobs_page(request):
    scope, t = _scope(request), metrics.today()
    last30, prev30 = (t - dt.timedelta(days=29), t), (t - dt.timedelta(days=59), t - dt.timedelta(days=30))
    s, p = metrics.jobs_summary(*last30, scope), metrics.jobs_summary(*prev30, scope)
    s90 = metrics.jobs_summary(t - dt.timedelta(days=89), t, scope)
    util = metrics.utilization(t, 4, scope)
    on_jobs, worked = sum(float(u["on_jobs"]) for u in util), sum(float(u["worked"] or 0) for u in util)
    not_inv = metrics.jobs_not_invoiced(t, scope)
    tiles = "".join([
        ui.tile("Jobs completed, last 30 days", ui.num(s["completed"]), ui.delta(s["completed"], p["completed"], label="vs the 30 days before"),
                None, metrics.HOW["jobs_completed"]),
        ui.tile("Emergency calls on time", pct(s["emergency_on_time"], 0),
                f'{int(s["em_on_time"] or 0)} of {int(s["em_reached"] or 0)} within 4 hours · avg {_hrs(s["em_response"])}', None,
                metrics.HOW["emergency_on_time"]),
        ui.tile("First-time fix, last 90 days", pct(s90["first_time_fix"], 0),
                f'{int(s90["return_visits"] or 0)} return visits on {int(s90["repairs"] or 0)} repairs', None, metrics.HOW["first_time_fix"]),
        ui.tile("Technician utilization", pct(on_jobs / worked if worked else None, 0), "hours on jobs ÷ hours worked, last 4 weeks",
                None, metrics.HOW["utilization"]),
        ui.tile("Completed, not invoiced", money(sum(float(j["billable_amount"] or 0) for j in not_inv), True),
                f'{len(not_inv)} jobs finished 14+ days ago', "/cleanup#job_not_invoiced", metrics.HOW["not_invoiced"]),
    ])
    weeks = metrics.jobs_by_week(t, 12, scope)
    weekly = ui.chart("jobs-wk", {"type": "bar", "format": "count", "stacked": True,
                                  "labels": [ui.short_date(w["week"]) for w in weeks], "datasets": [
        {"label": "First visits", "data": [w["completed"] - w["return_visits"] for w in weeks], "color": "--series-1"},
        {"label": "Return visits", "data": [w["return_visits"] for w in weeks], "color": "--series-2"}]},
        height=240, label="Jobs completed by week")
    by_branch = metrics.jobs_by_branch(*last30, scope)
    by_branch90 = metrics.jobs_by_branch(t - dt.timedelta(days=89), t, scope)
    em_bars = _pct_bars(by_branch, "emergency_on_time",
                        lambda r: f'{int(r["em_reached"])} calls · avg {_hrs(r["em_response"])}', "Emergency calls on time by branch")
    ftf_bars = _pct_bars(by_branch90, "first_time_fix", lambda r: f'{int(r["return_visits"])} return visits',
                         "First-time fix by branch")
    util_branch = {}
    for u in util:
        b = util_branch.setdefault(u["branch"], [0.0, 0.0, 0])
        b[0] += float(u["on_jobs"])
        b[1] += float(u["worked"] or 0)
        b[2] += 1
    util_bars = _pct_bars([{"branch": k, "u": v[0] / v[1] if v[1] else None, "n": v[2]} for k, v in sorted(util_branch.items())],
                          "u", lambda r: f'{r["n"]} technicians', "Utilization by branch")
    rows = [f'<tr><td>{ui.source_link("fsm_job", j["id"], "Job " + j["number"])}</td><td class="wrap">{esc(j["account_name"])}</td>'
            f'<td>{esc(j["branch"])}</td><td>{esc(j["job_type"])}</td><td class="n">{ui.date(j["completed_date"])}</td>'
            f'<td class="n">{money(j["billable_amount"])}</td></tr>' for j in not_inv[:10]]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Jobs completed by week</h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>First visits</span><span><i style="background:var(--series-2)"></i>Return visits</span></div></div>
    {weekly}{ui.how(metrics.HOW["jobs_completed"])}</section>
  <section class="card"><div class="card-head"><h2>Emergency calls reached within 4 hours</h2><span class="muted">Last 30 days · goal 90%</span></div>
    {em_bars}{ui.how(metrics.HOW["emergency_on_time"])}</section>
</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>First-time fix</h2><span class="muted">Last 90 days · goal 85%</span></div>
    {ftf_bars}{ui.how(metrics.HOW["first_time_fix"])}</section>
  <section class="card"><div class="card-head"><h2>Technician utilization</h2><span class="muted">Last 4 weeks</span></div>
    {util_bars}{ui.how(metrics.HOW["utilization"])}</section>
</div>
<section class="card"><div class="card-head"><h2>Biggest jobs not invoiced yet</h2><a href="/cleanup#job_not_invoiced">See all {len(not_inv)}</a></div>
  {_table(["Job", "Customer", "Branch", "Type", "Completed", "Amount"], rows, "Every completed job has been invoiced.", (4, 5))}
  {ui.how(metrics.HOW["not_invoiced"])}</section>"""
    return ui.page(request, "Field service", body, "Field service", subtitle="Jobs from the field-service app, last 30 days unless noted")


# ---------------------------------------------------------------- inventory

def inventory_page(request):
    scope, t = _scope(request), metrics.today()
    s = metrics.inventory_summary(t, scope)
    reorder = metrics.reorder_list(scope)
    critical_out = [r for r in reorder if r["critical"] and float(r["on_hand"]) <= 0]
    tiles = "".join([
        ui.tile("Inventory value", money(s["value"], True), f'{money(s["van_value"], True)} of it on service vans', None, metrics.HOW["inventory_value"]),
        ui.tile("Turns, last 12 months", f'{s["turns"]:.1f}×' if s["turns"] else "—", f'{money(s["used_12m"], True)} of parts used on jobs',
                None, metrics.HOW["turns"]),
        ui.tile("Below reorder point", ui.num(s["below_reorder"]),
                f'<span class="delta bad">{len(critical_out)} critical part{"" if len(critical_out) == 1 else "s"} out of stock</span>'
                if critical_out else "no critical parts out", "#reorder", metrics.HOW["below_reorder"]),
        ui.tile("Dead stock", money(s["dead_value"], True), f'{pct(s["dead_value"] / s["value"] if s["value"] else None, 0)} of inventory, unused 180+ days',
                "#dead", metrics.HOW["dead_stock"]),
        ui.tile("Shrinkage, last 90 days", money(s["shrinkage_90d"], True), "count corrections at cost", None, metrics.HOW["shrinkage"]),
    ])
    by_branch = metrics.stock_value_by("branch", scope)
    by_cat = metrics.stock_value_by("category", scope)
    branch_bars = ui.hbars([{"label": r["key"], "value": r["value"], "shown": money(r["value"], True),
                             "sub": f'{money(r["dead"], True)} dead' if r["dead"] else ""} for r in by_branch], label="Inventory value by branch")
    cat_bars = ui.hbars([{"label": r["key"], "value": r["value"], "shown": money(r["value"], True),
                          "sub": f'{money(r["dead"], True)} dead' if r["dead"] else ""} for r in by_cat], label="Inventory value by category")
    rrows, any_on_order = [], any(r["on_order"] for r in reorder)
    for r in reorder:
        out = float(r["on_hand"]) <= 0
        flag = (' <span class="pill bad"><span aria-hidden="true">!</span> Out</span>' if out else "") + \
               (' <span class="pill warn">Critical</span>' if r["critical"] else "")
        level = max(0.0, min(1.0, float(r["on_hand"]) / float(r["reorder_point"]))) if r["reorder_point"] else 0
        rrows.append(f'<tr><td class="wrap">{ui.source_link("inv_item", r["sku"], r["description"])}{flag}<div class="meta">{esc(r["sku"])}</div></td>'
                     f'<td>{esc(r["branch"])}</td><td class="n"><span class="cellbar"><i style="width:{level * 100:.0f}%"></i></span>'
                     f'<span>{ui.num(r["on_hand"])} / {ui.num(r["reorder_point"])}</span></td>'
                     f'<td class="n">{ui.num(r["reorder_qty"])}</td><td>{esc(r["vendor"] or "—")}</td><td class="n">{money(r["order_value"])}</td>'
                     + (f'<td>{esc(r["on_order"] or "")}</td>' if any_on_order else "") + '</tr>')
    dead = metrics.dead_stock(scope)
    drows = [f'<tr><td class="wrap">{ui.source_link("inv_item", d["sku"], d["description"])}</td><td>{esc(d["location"])}</td>'
             f'<td class="n">{ui.num(d["on_hand"])}</td><td class="n">{money(d["value"])}</td>'
             f'<td class="n">{ui.date(d["last_issued_date"]) if d["last_issued_date"] else "never"}</td></tr>' for d in dead]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Where the money sits</h2><span class="muted">Warehouse and vans, by branch</span></div>{branch_bars}</section>
  <section class="card"><div class="card-head"><h2>By category</h2><span class="muted">At standard cost</span></div>{cat_bars}</section>
</div>
<section class="card" id="reorder"><div class="card-head"><h2>Reorder now</h2><span class="muted">{len(reorder)} warehouse items at or below their reorder point · critical first</span></div>
  {_table(["Part", "Warehouse", "On hand / reorder point", "Order qty", "Vendor", "Order value"] + (["Already on order"] if any_on_order else []), rrows,
          "Nothing is below its reorder point.", (2, 3, 5))}
  {ui.how(metrics.HOW["below_reorder"] + " 'Already on order' lists open purchase orders for the same part and branch.")}</section>
<section class="card" id="dead"><div class="card-head"><h2>Dead stock</h2><span class="muted">Candidates to return, sell or write off</span></div>
  {_table(["Part", "Location", "On hand", "Value", "Last used"], drows, "No dead stock.", (2, 3, 4))}
  {ui.how(metrics.HOW["dead_stock"])}</section>"""
    return ui.page(request, "Inventory", body, "Inventory", subtitle=f"Parts in every warehouse and service van, as of {ui.date(t)}")


# ---------------------------------------------------------------- purchasing

def purchasing_page(request):
    scope, t = _scope(request), metrics.today()
    s = metrics.purchasing_summary(t, scope)
    vendors = metrics.vendor_scorecard(t, scope)
    tiles = "".join([
        ui.tile("Spend, last 12 months", money(s["spend"], True), "purchase orders placed", None, metrics.HOW["spend"]),
        ui.tile("Open orders", money(s["open_amount"], True),
                f'{int(s["open_count"])} orders' + (f' · <span class="delta bad">{int(s["late_open"])} past due</span>' if s["late_open"] else ""),
                "#late"),
        ui.tile("On-time delivery", pct(s["on_time_delivery"], 0), f'{int(s["received_on_time"])} of {int(s["received"])} orders, last 90 days',
                None, metrics.HOW["on_time_delivery"]),
        ui.tile("Received, not billed", money(s["not_billed"], True), f'{int(s["not_billed_count"])} orders waiting on a vendor bill',
                "/cleanup#po_not_billed", metrics.HOW["received_not_billed"]),
    ])
    spend_bars = ui.hbars([{"label": v["vendor"], "value": v["spend"], "shown": money(v["spend"], True),
                            "sub": f'{v["orders"]} orders'} for v in vendors if v["spend"]], label="Spend by vendor")
    otd = [dict(v, branch=v["vendor"]) for v in sorted(vendors, key=lambda v: (v["on_time_delivery"] is None, v["on_time_delivery"] or 0))
           if v["received"]]
    otd_bars = _pct_bars(otd, "on_time_delivery",
                         lambda v: f'avg {float(v["avg_days_late"]):.0f} days late when late' if v["avg_days_late"] else f'{v["received"]} received',
                         "On-time delivery by vendor")
    prices = metrics.price_changes(t, scope)
    def change(c):
        txt = f"{float(c) * 100:+.1f}%"
        return f'<span class="pill bad">{txt}</span>' if c > 0.08 else txt
    prows = [f'<tr><td class="wrap">{ui.source_link("inv_item", r["sku"], r["description"])}</td><td>{esc(r["vendor"])}</td>'
             f'<td class="n">{money(r["price_then"])}</td><td class="n">{money(r["price_now"])}</td>'
             f'<td class="n">{change(r["change"])}</td></tr>' for r in prices]
    late = db.query(f"""SELECT id, number, vendor, branch, kind, ordered_date, expected_date, days_late, amount FROM rpt.purchase_orders
                        WHERE is_open AND days_late > 0 {metrics._scope(scope)} ORDER BY days_late DESC, amount DESC""", {"scope": scope})
    lrows = [f'<tr><td>{ui.source_link("ap_po", r["id"], "PO " + r["number"])}</td><td>{esc(r["vendor"])}</td><td>{esc(r["branch"])}</td>'
             f'<td>{esc(r["kind"])}</td><td class="n">{ui.date(r["expected_date"])}</td><td class="n">{r["days_late"]} day{"" if r["days_late"] == 1 else "s"}</td>'
             f'<td class="n">{money(r["amount"])}</td></tr>' for r in late]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Spend by vendor</h2><span class="muted">Last 12 months</span></div>{spend_bars}
    {ui.how(metrics.HOW["spend"])}</section>
  <section class="card"><div class="card-head"><h2>On-time delivery by vendor</h2><span class="muted">Last 90 days, worst first</span></div>{otd_bars}
    {ui.how(metrics.HOW["on_time_delivery"])}</section>
</div>
<section class="card"><div class="card-head"><h2>Prices up the most</h2><span class="muted">Last 90 days against the same 90 days a year ago</span></div>
  {_table(["Part", "Vendor", "A year ago", "Now", "Change"], prows, "Not enough history yet.", (2, 3, 4))}
  {ui.how(metrics.HOW["price_change"])}</section>
<section class="card" id="late"><div class="card-head"><h2>Orders past their expected date</h2><span class="muted">{len(late)} open</span></div>
  {_table(["Order", "Vendor", "Branch", "Type", "Expected", "Late by", "Amount"], lrows, "No open orders are late.", (4, 5, 6))}</section>"""
    return ui.page(request, "Purchasing", body, "Purchasing", subtitle="Purchase orders and vendors, from the purchasing system")


# ---------------------------------------------------------------- people

def people_page(request):
    scope, t = _scope(request), metrics.today()
    s = metrics.people_summary(t, scope)
    tiles = "".join([
        ui.tile("Headcount", ui.num(s["headcount"]), f'{int(s["technicians"])} technicians', None, metrics.HOW["headcount"]),
        ui.tile("Open roles", ui.num(s["open_roles"]), f'avg {s["avg_days_open"]:.0f} days open' if s["avg_days_open"] is not None else "none open",
                "#roles", metrics.HOW["open_roles"]),
        ui.tile("Turnover, last 12 months", pct(s["turnover"], 0), f'{int(s["exits_12m"])} left ({int(s["quits_12m"])} by choice) · {int(s["hires_12m"])} hired',
                None, metrics.HOW["turnover"]),
        ui.tile("Overtime, last 4 weeks", pct(s["overtime_pct"], 1), "of hours worked, hourly staff", None, metrics.HOW["overtime"]),
        ui.tile("Licenses and certifications", ui.num(s["certs_expired"] + s["certs_expiring"]),
                (f'<span class="delta bad">{s["certs_expired"]} expired</span> · ' if s["certs_expired"] else "") + f'{s["certs_expiring"]} expiring in 30 days',
                "#certs", metrics.HOW["certs"]),
    ])
    months = metrics.headcount_by_month(t, 12, scope)
    labels = [m["month_end"].strftime("%b") if m["month_end"] != t else "Today" for m in months]
    hc = ui.chart("hc", {"type": "line", "format": "count", "labels": labels, "suggestedMax": max(m["headcount"] for m in months) + 5,
                         "datasets": [{"label": "Headcount", "data": [m["headcount"] for m in months], "color": "--series-1"}]},
                  height=220, label="Headcount at each month-end")
    flows = ui.chart("flows", {"type": "bar", "format": "count", "labels": labels, "datasets": [
        {"label": "Hired", "data": [m["hires"] for m in months], "color": "--series-3"},
        {"label": "Left", "data": [m["exits"] for m in months], "color": "--series-2"}]}, height=220, label="Hires and departures by month")
    ot = metrics.overtime_by_branch(t, 4, scope)
    ot_bars = ui.hbars([{"label": r["branch"], "value": r["overtime_pct"] or 0, "shown": pct(r["overtime_pct"], 1),
                         "sub": f'{float(r["ot"] or 0):,.0f} hrs'} for r in sorted(ot, key=lambda r: -(r["overtime_pct"] or 0))],
                       label="Overtime by branch")
    hb = metrics.headcount_by_branch(t, scope)
    hc_bars = ui.hbars([{"label": r["branch"], "value": r["headcount"], "shown": str(r["headcount"]),
                         "sub": f'{r["technicians"]} technicians'} for r in hb], label="Headcount by branch")
    certs = metrics.cert_problems(scope)
    def state(c):
        if c["status"] == "Expired":
            return '<span class="pill bad"><span aria-hidden="true">!</span> Expired</span>'
        return f'<span class="pill warn">{c["days_left"]} days left</span>'
    crows = [f'<tr><td>{ui.source_link("hr_employee", c["employee_id"], c["employee_name"])}'
             f'<div class="meta">{esc(c["title"])} · {esc(c["branch"])}</div></td>'
             f'<td class="wrap">{esc(c["certification"])}</td><td class="n">{ui.short_date(c["expires_date"])}</td>'
             f'<td>{state(c)}</td></tr>' for c in certs]
    roles = metrics.open_roles(t, scope)
    rrows = [f'<tr><td>{esc(r["title"])}</td><td>{esc(r["branch"])}</td><td>{esc(r["reason"])}</td><td class="n">{ui.date(r["opened_date"])}</td>'
             f'<td class="n">{r["days_open"]} days</td><td class="n">{r["applicants"]}</td></tr>' for r in roles]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Headcount</h2><span class="muted">At each month-end</span></div>{hc}{ui.how(metrics.HOW["headcount"])}</section>
  <section class="card"><div class="card-head"><h2>Hires and departures</h2>
    <div class="legend"><span><i style="background:var(--series-3)"></i>Hired</span><span><i style="background:var(--series-2)"></i>Left</span></div></div>
    {flows}{ui.how(metrics.HOW["turnover"])}</section>
</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Overtime by branch</h2><span class="muted">Last 4 weeks · goal under 8%</span></div>{ot_bars}
    {ui.how(metrics.HOW["overtime"])}</section>
  <section class="card"><div class="card-head"><h2>Who works where</h2><span class="muted">Today</span></div>{hc_bars}</section>
</div>
<div class="cols even">
  <section class="card" id="certs"><div class="card-head"><h2>Licenses to renew</h2><span class="muted">Expired or expiring in 30 days</span></div>
    {_table(["Person", "License", "Expires", ""], crows, "Everything is current.", (2,))}
    {ui.how(metrics.HOW["certs"])}</section>
  <section class="card" id="roles"><div class="card-head"><h2>Open roles</h2><span class="muted">{len(roles)} open</span></div>
    {_table(["Role", "Branch", "Why", "Opened", "Open for", "Applicants"], rrows, "No open roles.", (3, 4, 5))}</section>
</div>"""
    return ui.page(request, "People", body, "People", subtitle="From HR and payroll. Pay rates and personal details are never shown here.")


# ---------------------------------------------------------------- demo stand-in records

SOURCE_FIELDS = {
    "job": [("number", "Job number"), ("customer", "Customer"), ("job_type", "Job type"), ("priority", "Priority"),
            ("status", "Status"), ("created_at", "Call received"), ("scheduled_date", "Scheduled for"),
            ("arrived_at", "Technician arrived"), ("completed_at", "Completed"), ("technician", "Technician"),
            ("labor_hours", "Labor hours"), ("billable_amount", "Billable amount"), ("invoice_number", "Invoice number"),
            ("is_callback", "Return visit"), ("parent_id", "Return visit for job"), ("id", "Record ID")],
    "item": [("id", "Part number"), ("description", "Description"), ("category", "Category"), ("standard_cost", "Standard cost"),
             ("vendor", "Preferred vendor"), ("critical", "Critical part"), ("active", "Active")],
    "po": [("number", "PO number"), ("vendor", "Vendor"), ("kind", "Type"), ("status", "Status"), ("ordered_date", "Ordered"),
           ("expected_date", "Expected"), ("received_date", "Received"), ("amount", "Amount"), ("billed_amount", "Billed by vendor"),
           ("deal_id", "For deal"), ("id", "Record ID")],
    "employee": [("name", "Name"), ("title", "Job title"), ("department", "Department"), ("branch_code", "Location"),
                 ("hire_date", "Hire date"), ("termination_date", "Last day"), ("manager", "Manager"), ("pay_type", "Pay type"),
                 ("id", "Employee ID")],
}


def demo_record(system: str, obj: str, rec_id: str, scope):
    """The stand-in record for an operations system: (record, system name, kind, related HTML), or None."""
    def ok(code):
        return not scope or code in scope
    if (system, obj) == ("fieldservice", "job"):
        r = db.one("""SELECT w.*, a.name AS customer, e.name AS technician FROM fsm.work_orders w
                      LEFT JOIN crm.accounts a ON a.id = w.account_id LEFT JOIN hr.employees e ON e.id = w.technician_id
                      WHERE w.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        parts = db.query("""SELECT p.sku, i.description, p.qty, p.location_id FROM fsm.work_order_parts p
                            LEFT JOIN inv.items i ON i.id = p.sku WHERE p.work_order_id = %(i)s""", {"i": rec_id})
        rel = ("<h3>Parts used</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(p["description"] or p["sku"])}<span class="amt">{ui.num(p["qty"])} from {esc(p["location_id"])}</span></li>'
            for p in parts) + "</ul>") if parts else ""
        return r, "Field service", "job", rel
    if (system, obj) == ("inventory", "item"):
        r = db.one("""SELECT i.*, v.name AS vendor FROM inv.items i LEFT JOIN ap.vendors v ON v.id = i.preferred_vendor_id
                      WHERE i.id = %(i)s""", {"i": rec_id})
        if not r:
            return None
        stock = db.query(f"""SELECT location, on_hand, reorder_point, last_issued_date FROM rpt.stock WHERE sku = %(i)s
                             {metrics._scope(scope)} ORDER BY location""", {"i": rec_id, "scope": scope})
        rel = ("<h3>Stock by location</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(s["location"])}<span class="amt">{ui.num(s["on_hand"])} on hand'
            f'{f" · reorder at {ui.num(s["reorder_point"])}" if s["reorder_point"] else ""}</span></li>' for s in stock) + "</ul>")
        return r, "Inventory", "item", rel
    if (system, obj) == ("purchasing", "po"):
        r = db.one("""SELECT p.*, v.name AS vendor FROM ap.purchase_orders p LEFT JOIN ap.vendors v ON v.id = p.vendor_id
                      WHERE p.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        lines = db.query("SELECT sku, description, qty, unit_price FROM ap.po_lines WHERE po_id = %(i)s ORDER BY id", {"i": rec_id})
        rel = "<h3>Lines</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(x["description"])}<span class="amt">{ui.num(x["qty"])} × {money(x["unit_price"])}</span></li>' for x in lines) + "</ul>"
        return r, "Purchasing", "po", rel
    if (system, obj) == ("hr", "employee"):
        r = db.one("""SELECT e.*, m.name AS manager FROM hr.employees e LEFT JOIN hr.employees m ON m.id = e.manager_id
                      WHERE e.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        certs = db.query("SELECT name, expires_date FROM hr.certifications WHERE employee_id = %(i)s ORDER BY name", {"i": rec_id})
        rel = ("<h3>Licenses and certifications</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(c["name"])}<span class="amt">{"expires " + ui.date(c["expires_date"]) if c["expires_date"] else "no expiry"}</span></li>'
            for c in certs) + "</ul>") if certs else ""
        return r, "HR and payroll", "employee", rel
    return None
