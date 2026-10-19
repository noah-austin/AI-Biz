"""Operations pages: Field service, Inventory, Purchasing and People. The numbers come from kit/metrics.py."""
import datetime as dt

from .. import db, metrics
from . import ui
from .ui import esc, money, pct


def _scope(request):
    return request.state.user["branches"] or None


def _frontline() -> str:
    """What this company calls its frontline staff, from [people] frontline_label in config.toml."""
    from ..config import get_settings
    return get_settings().client.get("people", {}).get("frontline_label", "technicians")


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
        ui.tile("Turns, last 12 months", f'{s["turns"]:.1f}×' if s["turns"] else "—", f'{money(s["used_12m"], True)} used or shipped at cost',
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
{f"""<section class="card"><div class="card-head"><h2>Prices up the most</h2><span class="muted">Last 90 days against the same 90 days a year ago</span></div>
  {_table(["Part", "Vendor", "A year ago", "Now", "Change"], prows, "", (2, 3, 4))}
  {ui.how(metrics.HOW["price_change"])}</section>""" if prows else ""}
<section class="card" id="late"><div class="card-head"><h2>Orders past their expected date</h2><span class="muted">{len(late)} open</span></div>
  {_table(["Order", "Vendor", "Branch", "Type", "Expected", "Late by", "Amount"], lrows, "No open orders are late.", (4, 5, 6))}</section>"""
    return ui.page(request, "Purchasing", body, "Purchasing", subtitle="Purchase orders and vendors, from the purchasing system")


# ---------------------------------------------------------------- people

def people_page(request):
    scope, t = _scope(request), metrics.today()
    s = metrics.people_summary(t, scope)
    tiles = "".join([
        ui.tile("Headcount", ui.num(s["headcount"]), f'{int(s["frontline"])} {esc(_frontline())}', None, metrics.HOW["headcount"]),
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
                         "sub": f'{r["frontline"]} {esc(_frontline())}'} for r in hb], label="Headcount by branch")
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
<section class="card" id="certs"><div class="card-head"><h2>Licenses to renew</h2><span class="muted">Expired or expiring in 30 days</span></div>
  {_table(["Person", "License", "Expires", ""], crows, "Everything is current.", (2,))}
  {ui.how(metrics.HOW["certs"])}</section>
<section class="card" id="roles"><div class="card-head"><h2>Open roles</h2><span class="muted">{len(roles)} open</span></div>
  {_table(["Role", "Branch", "Why", "Opened", "Open for", "Applicants"], rrows, "No open roles.", (3, 4, 5))}</section>"""
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
    "job": [("number", "Job number"), ("name", "Job"), ("customer", "Owner"), ("status", "Status"), ("contract_value", "Original contract"),
            ("budget_cost", "Budget cost"), ("estimate_at_completion", "Estimate at completion"), ("start_date", "Start"),
            ("end_date", "Finish"), ("pm", "Project manager"), ("retainage_pct", "Retainage %"), ("deal_id", "CRM deal"), ("id", "Record ID")],
    "project": [("number", "Project number"), ("name", "Project"), ("customer", "Client"), ("billing_type", "Billing"),
                ("status", "Status"), ("contract_value", "Contract value"), ("budget_hours", "Budget hours"),
                ("percent_complete", "Percent complete (PM)"), ("start_date", "Start"), ("end_date", "End"), ("pm", "Project manager"),
                ("deal_id", "CRM deal"), ("id", "Record ID")],
    "order": [("number", "Order number"), ("customer", "Customer"), ("channel", "Channel"), ("status", "Status"),
              ("order_date", "Ordered"), ("requested_date", "Customer wants it by"), ("first_ship_date", "First shipment"),
              ("last_ship_date", "Last shipment"), ("rep", "Sales rep"), ("invoice_number", "Invoice number"), ("id", "Record ID")],
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
    if (system, obj) == ("jobcost", "job"):
        r = db.one("""SELECT j.*, a.name AS customer, e.name AS pm FROM jc.jobs j LEFT JOIN crm.accounts a ON a.id = j.account_id
                      LEFT JOIN hr.employees e ON e.id = j.pm_id WHERE j.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        cos = db.query("SELECT number, description, amount, status, submitted_date FROM jc.change_orders WHERE job_id = %(i)s ORDER BY submitted_date",
                       {"i": rec_id})
        apps = db.query("SELECT period, gross_billed, retainage_held, retainage_released FROM jc.pay_apps WHERE job_id = %(i)s ORDER BY period",
                        {"i": rec_id})

        def released(a):
            return f" · {money(a['retainage_released'])} released" if a["retainage_released"] else ""
        rel = ("<h3>Change orders</h3><ul class=\"list\">" + "".join(
            f'<li>CO {esc(c["number"])}: {esc(c["description"])}<span class="amt">{money(c["amount"])} · {esc(c["status"])}</span></li>'
            for c in cos) + "</ul>") if cos else ""
        rel += "<h3>Pay applications</h3><ul class=\"list\">" + "".join(
            f'<li>{a["period"]:%B %Y}<span class="amt">{money(a["gross_billed"])} billed · {money(a["retainage_held"])} retainage held'
            f'{released(a)}</span></li>'
            for a in apps) + "</ul>"
        return r, "Job cost", "job", rel
    if (system, obj) == ("projects", "project"):
        r = db.one("""SELECT p.*, a.name AS customer, e.name AS pm FROM psa.projects p LEFT JOIN crm.accounts a ON a.id = p.account_id
                      LEFT JOIN hr.employees e ON e.id = p.pm_id WHERE p.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        team = db.query("""SELECT e.name, e.title, sum(t.hours) AS hours FROM psa.time_entries t JOIN hr.employees e ON e.id = t.employee_id
                           WHERE t.project_id = %(i)s GROUP BY 1, 2 ORDER BY 3 DESC""", {"i": rec_id})
        rel = "<h3>Time by person</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(x["name"])} <span class="muted">{esc(x["title"])}</span><span class="amt">{float(x["hours"]):,.1f} hrs</span></li>'
            for x in team) + "</ul>"
        return r, "Projects and time", "project", rel
    if (system, obj) == ("orders", "order"):
        r = db.one("""SELECT o.*, a.name AS customer, u.name AS rep FROM ord.orders o LEFT JOIN crm.accounts a ON a.id = o.account_id
                      LEFT JOIN crm.users u ON u.id = o.rep_id WHERE o.id = %(i)s""", {"i": rec_id})
        if not r or not ok(r["branch_code"]):
            return None
        lines = db.query("""SELECT l.*, coalesce(i.description, l.sku) AS description FROM ord.order_lines l
                            LEFT JOIN inv.items i ON i.id = l.sku WHERE l.order_id = %(i)s ORDER BY l.id""", {"i": rec_id})
        rel = "<h3>Lines</h3><ul class=\"list\">" + "".join(
            f'<li>{esc(x["description"])}<span class="amt">{ui.num(x["qty_shipped"])} of {ui.num(x["qty_ordered"])} shipped × '
            f'{money(x["unit_price"])} (cost {money(x["unit_cost"])})</span></li>' for x in lines) + "</ul>"
        return r, "Orders (ERP)", "order", rel
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


# ---------------------------------------------------------------- orders and shipping

def orders_page(request):
    scope, t = _scope(request), metrics.today()
    last30, prev30 = (t - dt.timedelta(days=29), t), (t - dt.timedelta(days=59), t - dt.timedelta(days=30))
    s, p = metrics.orders_summary(*last30, scope), metrics.orders_summary(*prev30, scope)
    tiles = "".join([
        ui.tile("Sales, last 30 days", money(s["sales"], True), ui.delta(s["sales"], p["sales"], label="vs the 30 days before"),
                None, metrics.HOW["sales_shipped"]),
        ui.tile("Gross margin", pct(s["gross_margin"], 1), ui.points_delta(s["gross_margin"], p["gross_margin"], "vs the 30 days before"),
                "#margin", metrics.HOW["gross_margin"]),
        ui.tile("Fill rate", pct(s["fill_rate"], 1), f'{int(s["lines_filled"]):,} of {int(s["lines"]):,} lines complete first time',
                "#fill", metrics.HOW["fill_rate"]),
        ui.tile("Shipped on time", pct(s["on_time_ship"], 0), f'{int(s["orders_shipped"]):,} orders shipped', "#fill", metrics.HOW["on_time_ship"]),
        ui.tile("Backorders", money(s["backorder_value"], True), f'{s["backorder_orders"]} orders waiting on stock', "#backorders",
                metrics.HOW["backorders"]),
    ])
    weeks = metrics.orders_by_week(t, 12, scope)
    weekly = ui.chart("orders-wk", {"type": "bar", "format": "money", "labels": [ui.short_date(w["week"]) for w in weeks], "datasets": [
        {"label": "Sales", "data": [float(w["sales"]) for w in weeks], "color": "--series-1"}]}, height=230, label="Sales by week")
    lines = metrics.orders_by("product_line", *last30, scope)
    margin_bars = ui.hbars([{"label": r["key"], "value": (r["gross_margin"] or 0) * 100, "shown": pct(r["gross_margin"], 1),
                             "sub": f'{money(r["sales"], True)} sales'} for r in sorted(lines, key=lambda r: -(r["gross_margin"] or 0))],
                           label="Gross margin by product line", top=50)
    squeeze = metrics.margin_by_month(t, 12, scope=scope)
    months = sorted({m for v in squeeze.values() for m in v})
    worst = sorted(squeeze.items(), key=lambda kv: (kv[1].get(months[-1]) or 0) - (kv[1].get(months[0]) or 0))[:3] if months else []
    trend = ui.chart("margin-trend", {"type": "line", "format": "pct", "labels": [m.strftime("%b") for m in months], "datasets": [
        {"label": k, "data": [None if v.get(m) is None else 100 * v[m] for m in months], "color": f"--series-{i + 1}"}
        for i, (k, v) in enumerate(worst)]}, height=230, label="Gross margin by month for the product lines that fell most")
    reps = metrics.orders_by("rep", *last30, scope)
    rep_bars = ui.hbars([{"label": r["key"], "value": (r["gross_margin"] or 0) * 100, "shown": pct(r["gross_margin"], 1),
                          "sub": f'{money(r["sales"], True)}'} for r in sorted(reps, key=lambda r: r["gross_margin"] or 0)[:10]],
                        label="Gross margin by rep, lowest first", top=50)
    fill = metrics.orders_by("branch", *last30, scope)
    ontime = {r["branch"]: r for r in metrics.orders_on_time_by_branch(*last30, scope)}
    fill_bars = _pct_bars([dict(r, branch=r["key"]) for r in fill], "fill_rate",
                          lambda r: f'{pct(ontime.get(r["key"], {}).get("on_time_ship"), 0)} shipped on time', "Fill rate by branch")
    custs = metrics.orders_by("customer", *last30, scope)[:10]
    crows = [f'<tr><td class="wrap">{esc(c["key"])}</td><td class="n">{money(c["sales"])}</td><td class="n">{pct(c["gross_margin"], 1)}</td>'
             f'<td class="n">{c["orders"]}</td></tr>' for c in custs]
    bo = metrics.backorders(scope, 15)
    brows = [f'<tr><td>{ui.source_link("ord_order", b["order_id"], "Order " + b["order_number"])}</td><td class="wrap">{esc(b["account_name"])}</td>'
             f'<td class="wrap">{esc(b["description"])}</td><td>{esc(b["branch"])}</td><td class="n">{ui.num(b["qty_open"])}</td>'
             f'<td class="n">{money(b["backorder_value"])}</td><td class="n">{ui.short_date(b["order_date"])}</td></tr>' for b in bo]
    legend = "".join(f'<span><i style="background:var(--series-{i + 1})"></i>{esc(k)}</span>' for i, (k, _v) in enumerate(worst))
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Sales by week</h2><span class="muted">What shipped, at the order price</span></div>
    {weekly}{ui.how(metrics.HOW["sales_shipped"])}</section>
  <section class="card" id="fill"><div class="card-head"><h2>Fill rate by branch</h2><span class="muted">Last 30 days · goal 95%</span></div>
    {fill_bars}{ui.how(metrics.HOW["fill_rate"] + " " + metrics.HOW["on_time_ship"])}</section>
</div>
<div class="cols even" id="margin">
  <section class="card"><div class="card-head"><h2>Gross margin by product line</h2><span class="muted">Last 30 days</span></div>
    {margin_bars}{ui.how(metrics.HOW["gross_margin"])}</section>
  <section class="card"><div class="card-head"><h2>Where margin is slipping</h2><div class="legend">{legend}</div></div>
    {trend}<p class="muted" style="margin:6px 0 0;font-size:13px">The product lines whose margin fell most over 12 months. Usually a vendor raised costs and prices didn't follow.</p></section>
</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Margin by rep</h2><span class="muted">Lowest first, last 30 days</span></div>{rep_bars}</section>
  <section class="card"><div class="card-head"><h2>Top customers</h2><span class="muted">Last 30 days</span></div>
    {_table(["Customer", "Sales", "Margin", "Orders"], crows, "No orders yet.", (1, 2, 3))}</section>
</div>
<section class="card" id="backorders"><div class="card-head"><h2>Biggest backorders</h2><span class="muted">Ordered, not yet shipped</span></div>
  {_table(["Order", "Customer", "Item", "Branch", "Qty open", "Value", "Ordered"], brows, "Nothing on backorder.", (4, 5, 6))}
  {ui.how(metrics.HOW["backorders"])}</section>"""
    return ui.page(request, "Orders", body, "Orders", subtitle="Sales orders and shipping, from the ERP, last 30 days unless noted")


# ---------------------------------------------------------------- projects and time

def projects_page(request):
    scope, t = _scope(request), metrics.today()
    first, last = metrics._weeks_back(t, 4)
    pfirst, plast = metrics._weeks_back(t - dt.timedelta(weeks=4), 4)
    u, up = metrics.time_summary(first, last, scope), metrics.time_summary(pfirst, plast, scope)
    s = metrics.projects_summary(t, scope)
    tiles = "".join([
        ui.tile("Billable utilization", pct(u["billable_util"], 0), ui.points_delta(u["billable_util"], up["billable_util"], "vs the 4 weeks before"),
                "#util", metrics.HOW["billable_util"]),
        ui.tile("Realization", pct(s["realization"], 0), f'{s["completed"]} projects completed in 12 months', "#realization",
                metrics.HOW["realization"]),
        ui.tile("Unbilled work in progress", money(s["unbilled_wip"], True),
                f'<span class="delta bad">{money(s["unbilled_over_60"], True)} over 60 days</span>' if s["unbilled_over_60"] else "all recent",
                "#wip", metrics.HOW["unbilled_wip"]),
        ui.tile("Backlog", money(s["backlog"], True), f'{s["active"]} active projects', None, metrics.HOW["backlog"]),
        ui.tile("Projects over pace", ui.num(s["at_risk"]), "fixed fees burning budget ahead of progress", "#risk", metrics.HOW["budget_used"]),
    ])
    by_office = metrics.utilization_by("branch", first, last, scope)
    office_bars = _pct_bars([dict(r, branch=r["key"]) for r in by_office], "billable_util",
                            lambda r: f'{float(r["billable"]):,.0f} of {float(r["recorded"]):,.0f} hrs', "Billable utilization by office")
    weekly = metrics.utilization_by_week(t, 52, scope)
    weeks = sorted({w["week"] for w in weekly})
    offices = sorted({w["branch"] for w in weekly})
    trend = ui.chart("util-trend", {"type": "line", "format": "pct", "labels": [ui.short_date(w) for w in weeks], "suggestedMax": 100,
                                    "datasets": [{"label": o, "data": [next((100 * float(x["util"]) for x in weekly if x["branch"] == o and x["week"] == w
                                                                             and x["util"] is not None), None) for w in weeks],
                                                  "color": f"--series-{i + 1}", "points": False} for i, o in enumerate(offices[:3])]},
                     height=230, label="Billable utilization by week for each office")
    legend = "".join(f'<span><i style="background:var(--series-{i + 1})"></i>{esc(o)}</span>' for i, o in enumerate(offices[:3]))
    by_role = metrics.utilization_by("title", first, last, scope)
    role_bars = _pct_bars([dict(r, branch=r["key"]) for r in by_role], "billable_util", lambda r: "", "Billable utilization by role")
    by_pm = [r for r in metrics.projects_by("pm", t, scope) if r["key"] != "(none)"]
    pm_bars = ui.hbars([{"label": r["key"], "value": max(0, (r["realization"] or 0) * 100), "shown": pct(r["realization"], 0),
                         "sub": f'{r["projects"]} projects · margin {pct(r["project_margin"], 0)}'}
                        for r in sorted(by_pm, key=lambda r: r["realization"] or 0)], label="Realization by project manager", top=110)
    by_seg = metrics.projects_by("segment", t, scope)
    seg_bars = ui.hbars([{"label": r["key"], "value": max(0, (r["realization"] or 0) * 100), "shown": pct(r["realization"], 0),
                          "sub": money(r["billed"], True)} for r in sorted(by_seg, key=lambda r: r["realization"] or 0)],
                        label="Realization by client type", top=110)
    risk = metrics.projects_at_risk(scope)
    rrows = [f'<tr><td class="wrap">{ui.source_link("psa_project", r["id"], r["name"])}<div class="meta">{esc(r["number"])} · {esc(r["pm_name"] or "")}</div></td>'
             f'<td>{esc(r["branch"])}</td><td class="n"><span class="cellbar"><i style="width:{min(100, float(r["budget_used"]) * 100 / 1.5):.0f}%"></i></span>'
             f'<span>{float(r["budget_used"]):.0%}</span></td><td class="n">{float(r["percent_complete"]):.0f}%</td>'
             f'<td class="n">{money(r["contract_value"])}</td></tr>' for r in risk]
    wip = metrics.unbilled_projects(t, scope)
    wrows = [f'<tr><td class="wrap">{ui.source_link("psa_project", w["id"], w["name"])}<div class="meta">{esc(w["pm_name"] or "")}</div></td>'
             f'<td>{esc(w["branch"])}</td><td class="n">{money(w["unbilled_value"])}</td><td class="n">{ui.date(w["oldest_unbilled"])}</td>'
             f'<td class="n">{w["days"]} days</td></tr>' for w in wip]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even" id="util">
  <section class="card"><div class="card-head"><h2>Billable utilization by office</h2><span class="muted">Last 4 weeks · target 75%</span></div>
    {office_bars}{ui.how(metrics.HOW["billable_util"])}</section>
  <section class="card"><div class="card-head"><h2>Utilization, last 12 months</h2><div class="legend">{legend}</div></div>{trend}</section>
</div>
<div class="cols even" id="realization">
  <section class="card"><div class="card-head"><h2>Realization by project manager</h2><span class="muted">Projects completed in 12 months</span></div>
    {pm_bars}{ui.how(metrics.HOW["realization"] + " " + metrics.HOW["project_margin"])}</section>
  <section class="card"><div class="card-head"><h2>Realization by client type</h2><span class="muted">Where hours get written down</span></div>
    {seg_bars}<div style="margin-top:14px"><h3 style="font-size:14px">Utilization by role, last 4 weeks</h3>{role_bars}</div></section>
</div>
<section class="card" id="risk"><div class="card-head"><h2>Fixed-fee projects burning ahead of progress</h2><span class="muted">Budget used vs percent complete</span></div>
  {_table(["Project", "Office", "Budget used", "Complete", "Fee"], rrows, "Every fixed-fee project is on pace.", (2, 3, 4))}
  {ui.how(metrics.HOW["budget_used"])}</section>
<section class="card" id="wip"><div class="card-head"><h2>Unbilled hourly work</h2><span class="muted">From before this month, oldest first</span></div>
  {_table(["Project", "Office", "Unbilled", "Since", "Age"], wrows, "All hourly work is billed.", (2, 3, 4))}
  {ui.how(metrics.HOW["unbilled_wip"])}</section>"""
    return ui.page(request, "Projects", body, "Projects", subtitle="Projects, budgets and time, from the project and time system")


# ---------------------------------------------------------------- job cost (construction)

def jobcost_page(request):
    scope = _scope(request)
    s = metrics.wip_summary(scope)
    jobs = metrics.wip_jobs(scope)
    tiles = "".join([
        ui.tile("Backlog", money(s["backlog"], True), f'{int(s["active"])} active jobs', None, metrics.HOW["backlog_jobs"]),
        ui.tile("Margin on active jobs", pct(s["projected_margin"], 1),
                f'<span class="delta {"bad" if (s["projected_margin"] or 0) < (s["original_margin"] or 0) else "good"}">'
                f'bid at {pct(s["original_margin"], 1)}</span>', "#fade", metrics.HOW["fade"]),
        ui.tile("Under-billed", money(-s["under"], True), f'{money(s["over"], True)} over-billed', "#wip", metrics.HOW["over_under"]),
        ui.tile("Retainage held", money(s["retainage"], True), "owed back by owners", None, metrics.HOW["retainage"]),
        ui.tile("Change orders waiting", money(s["pending"], True), f'{int(s["pending_n"])} not yet signed by owners', "#changes",
                metrics.HOW["pending_changes"]),
    ])
    pm = metrics.fade_by("pm", scope)
    fade_bars = ui.hbars([{"label": r["key"], "value": max(0, (r["projected_margin"] or 0) * 100), "shown": pct(r["projected_margin"], 1),
                           "sub": f'bid {pct(r["original_margin"], 1)} · {r["jobs"]} jobs'} for r in sorted(pm, key=lambda r: r["projected_margin"] or 0)],
                         label="Projected margin by project manager", top=25)
    ou = sorted(jobs, key=lambda j: float(j["over_under"]))
    ou_bars = ui.hbars([{"label": j["name"][:42], "title": j["name"], "value": abs(float(j["over_under"])),
                         "shown": money(j["over_under"], True), "sub": "under" if j["over_under"] < 0 else "over",
                         "dim": j["over_under"] >= 0} for j in (ou[:5] + ou[-3:]) if abs(float(j["over_under"])) > 1000],
                       label="Biggest over- and under-billed jobs")

    def row(j):
        fade = (j["original_margin"] or 0) - (j["projected_margin"] or 0)
        warn = '<span class="pill bad">loss</span>' if (j["projected_margin"] or 0) < 0 else (
            '<span class="pill warn">fading</span>' if fade > 0.03 else "")
        return (f'<tr><td class="wrap">{ui.source_link("jc_job", j["id"], j["name"])} {warn}<div class="meta">{esc(j["number"])} · '
                f'{esc(j["pm_name"] or "")} · {esc(j["branch"])}</div></td>'
                f'<td class="n">{money(j["contract"], True)}</td><td class="n">{pct(j["pct_complete"], 0)}</td>'
                f'<td class="n">{money(j["earned"], True)}</td><td class="n">{money(j["billed"], True)}</td>'
                f'<td class="n">{money(j["over_under"], True)}</td><td class="n">{pct(j["original_margin"], 1)}</td>'
                f'<td class="n">{pct(j["projected_margin"], 1)}</td></tr>')
    pending = sorted((j for j in jobs if j["pending_n"]), key=lambda j: j["oldest_pending"])
    prow = [f'<tr><td class="wrap">{ui.source_link("jc_job", j["id"], j["name"])}<div class="meta">{esc(j["pm_name"] or "")}</div></td>'
            f'<td class="n">{j["pending_n"]}</td><td class="n">{money(j["pending_changes"])}</td><td class="n">{ui.date(j["oldest_pending"])}</td></tr>'
            for j in pending]
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even" id="fade">
  <section class="card"><div class="card-head"><h2>Margin by project manager</h2><span class="muted">Projected today, active jobs</span></div>
    {fade_bars}{ui.how(metrics.HOW["fade"])}</section>
  <section class="card"><div class="card-head"><h2>Over and under billing</h2><span class="muted">Grey = over-billed</span></div>
    {ou_bars}{ui.how(metrics.HOW["over_under"])}</section>
</div>
<section class="card" id="wip"><div class="card-head"><h2>Work in progress</h2><span class="muted">Active jobs, as of the end of last month</span></div>
  {_table(["Job", "Contract", "Complete", "Earned", "Billed", "Over / (under)", "Bid margin", "Projected"], [row(j) for j in jobs],
          "No active jobs.", (1, 2, 3, 4, 5, 6, 7))}
  {ui.how(metrics.HOW["wip"])}</section>
<section class="card" id="changes"><div class="card-head"><h2>Change orders waiting on owners</h2><span class="muted">Oldest first</span></div>
  {_table(["Job", "Waiting", "Amount", "Oldest submitted"], prow, "Nothing waiting.", (1, 2, 3))}
  {ui.how(metrics.HOW["pending_changes"])}</section>"""
    return ui.page(request, "Job cost", body, "Job cost", subtitle="Jobs, costs and billing from the job-cost system", wide=True)
