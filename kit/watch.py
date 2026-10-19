"""Business alerts and the agents' everyday output, worked out from the data by plain rules.

Used by the hub's Alerts, Agents and Forecast pages. In a live install the AI agents write the brief, drafts and
meeting prep from the same facts; these rules are the floor they start from, and what the public demo shows.
Thresholds can be changed per client under [watch] in clients/<name>/config.toml.
"""
import datetime as dt

from . import db, metrics
from .config import get_settings

DEFAULTS = {
    "slipped_min": 50_000,     # a deal pushed to a later month at least this big is an alert
    "big_win": 100_000,
    "big_loss": 150_000,
    "late_days": [60, 90],     # an invoice passing these many days past due is an alert (the last one is critical)
    "late_min": 0,             # ...if its unpaid balance is at least this much (for companies with many small invoices)
    "billing_pace": 0.85,      # a branch billing below this share of last year's month-to-date is an alert
    "billing_min": 50_000,     # ...if last year's month-to-date was at least this much
    "closing_days": 7,         # the brief lists deals due to close within this many days
    "emergency_late_hours": 8,  # an emergency call reached this many hours late or more is an alert
    "overtime_pct": 0.15,      # a branch whose overtime last week was above this share of hours worked is an alert
    "license_days": 30,        # a license or certification expiring within this many days is an alert
    "late_po_min": 5_000,      # an open purchase order this big that's past its expected date is an alert
}


def rules() -> dict:
    return {**DEFAULTS, **get_settings().client.get("watch", {})}


def _scope(scope, col="branch_code"):
    return f"AND {col} = ANY(%(scope)s)" if scope else ""


def _f(v) -> float:
    return float(v or 0)


# ---------------------------------------------------------------- alerts

def alerts(t: dt.date, scope=None, days: int = 7) -> list[dict]:
    """Everything that would have sent an alert in the last `days` days, newest first.

    Each alert: date, severity (critical / warning / good), kind, title, detail, and what to link to.
    """
    r = rules()
    since = t - dt.timedelta(days=days - 1)
    p = {"since": since, "t": t, "scope": scope}
    out = []
    ch = metrics.recent_changes(t, days, scope)
    for d in ch["slipped"]:
        if _f(d["amount"]) >= r["slipped_min"]:
            out.append({"date": None, "severity": "warning", "kind": "Deal slipped",
                        "title": f'{d["name"]} moved to a later month',
                        "detail": f'{d["branch"]} · close date {d["old_close"]:%b %-d} → {d["new_close"]:%b %-d}',
                        "amount": _f(d["amount"]), "deal_id": d["id"]})
    hist = {x["id"]: x["d"] for x in db.query(f"""
        SELECT deal_id AS id, max(changed_date) AS d FROM rpt.deal_history
        WHERE field = 'CloseDate' AND changed_date BETWEEN %(since)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
    for a in out:
        a["date"] = hist.get(a["deal_id"], t)
    for d in db.query(f"""SELECT id, name, branch, amount, close_date, is_won FROM rpt.deals
                          WHERE is_closed AND close_date BETWEEN %(since)s AND %(t)s {_scope(scope)}""", p):
        if d["is_won"] and _f(d["amount"]) >= r["big_win"]:
            out.append({"date": d["close_date"], "severity": "good", "kind": "Big win", "title": f'Won: {d["name"]}',
                        "detail": d["branch"], "amount": _f(d["amount"]), "deal_id": d["id"]})
        elif not d["is_won"] and _f(d["amount"]) >= r["big_loss"]:
            out.append({"date": d["close_date"], "severity": "warning", "kind": "Big loss", "title": f'Lost: {d["name"]}',
                        "detail": d["branch"], "amount": _f(d["amount"]), "deal_id": d["id"]})
    marks = sorted(r["late_days"])
    for n in marks:
        rows = db.query(f"""SELECT id, number, customer_name, branch, balance, due_date FROM rpt.invoices
                            WHERE is_open AND balance > 0 AND balance >= %(lm)s AND (due_date + %(n)s) BETWEEN %(since)s AND %(t)s
                            {_scope(scope)}""", dict(p, n=n, lm=r["late_min"]))
        for i in rows:
            out.append({"date": i["due_date"] + dt.timedelta(days=n), "severity": "critical" if n == marks[-1] else "warning",
                        "kind": f"Invoice {n} days late", "title": f'{i["customer_name"]}: invoice {i["number"]}',
                        "detail": f'{i["branch"]} · due {i["due_date"]:%b %-d}', "amount": _f(i["balance"]),
                        "invoice_id": i["id"]})
    for b in (billing_pace(t, scope) if r["billing_pace"] else []):   # 0 switches it off (e.g. firms that bill once a month)
        if b["last_year"] >= r["billing_min"] and b["share"] < r["billing_pace"]:
            out.append({"date": t, "severity": "warning", "kind": "Billing behind pace",
                        "title": f'{b["branch"]} is at {b["share"]:.0%} of last year\'s billing for the month so far',
                        "detail": f'{metrics_money(b["this_year"])} vs {metrics_money(b["last_year"])} by this date last year',
                        "amount": None, "branch": b["branch"]})
    out += ops_alerts(t, scope, since)
    order = {"critical": 0, "warning": 1, "good": 2}
    out.sort(key=lambda a: (a["date"] or t, -order[a["severity"]], a.get("amount") or 0), reverse=True)
    return out


def ops_alerts(t: dt.date, scope, since: dt.date) -> list[dict]:
    """Alerts from the operations systems, for the ones this install has switched on."""
    apps, r, p, out = get_settings().apps, rules(), {"since": since, "t": t, "scope": scope}, []
    if "field_service" in apps:
        for j in db.query(f"""SELECT id, number, account_name, branch, response_hours, arrived_date FROM rpt.jobs
                              WHERE priority = 'Emergency' AND arrived_date BETWEEN %(since)s AND %(t)s
                                AND response_hours >= %(h)s {_scope(scope)}""", dict(p, h=r["emergency_late_hours"])):
            out.append({"date": j["arrived_date"], "severity": "warning", "kind": "Emergency call late",
                        "title": f'{j["account_name"]}: reached after {float(j["response_hours"]):.1f} hours',
                        "detail": f'{j["branch"]} · job {j["number"]} · the promise is 4 hours', "amount": None, "job_id": j["id"]})
    if "job_cost" in apps:
        for j in metrics.wip_jobs(scope):
            if (j["projected_margin"] or 0) < 0:
                out.append({"date": t, "severity": "critical", "kind": "Job losing money",
                            "title": f'{j["name"]}: now projected at {float(j["projected_margin"]):.1%} margin (bid at {float(j["original_margin"]):.1%})',
                            "detail": f'{j["branch"]} · {j["pm_name"]}', "amount": float(j["contract"]), "jc_job_id": j["id"]})
            elif float(j["over_under"]) < -r.get("under_billed_min", 250_000):
                out.append({"date": t, "severity": "warning", "kind": "Under-billed",
                            "title": f'{j["name"]} is under-billed by {metrics_money(-float(j["over_under"]))}',
                            "detail": f'{float(j["pct_complete"]):.0%} complete · {j["branch"]}', "amount": -float(j["over_under"]),
                            "jc_job_id": j["id"]})
    if "projects" in apps:
        week = t - dt.timedelta(days=t.weekday() + 7)
        for b in metrics.utilization_by("branch", week, week + dt.timedelta(days=6), scope):
            if b["recorded"] >= 200 and (b["billable_util"] or 0) < r.get("util_min", 0.65):
                out.append({"date": week + dt.timedelta(days=6), "severity": "warning", "kind": "Utilization low",
                            "title": f'{b["key"]}: only {b["billable_util"]:.0%} of hours were billable last week',
                            "detail": f'week of {week:%b %-d} · target 75%', "amount": None})
        for pr in metrics.projects_at_risk(scope):
            if float(pr["budget_used"] or 0) > 1:
                out.append({"date": t, "severity": "warning", "kind": "Project over budget",
                            "title": f'{pr["name"]}: {float(pr["budget_used"]):.0%} of budget hours used at {float(pr["percent_complete"]):.0f}% complete',
                            "detail": f'{pr["branch"]} · {pr["pm_name"]}', "amount": None, "project_id": pr["id"]})
    if "orders" in apps:
        week = t - dt.timedelta(days=t.weekday() + 7)
        for b in metrics.orders_by("branch", week, week + dt.timedelta(days=6), scope):
            if b["lines"] >= 50 and b["fill_rate"] is not None and b["fill_rate"] < r.get("fill_rate_min", 0.9):
                out.append({"date": week + dt.timedelta(days=6), "severity": "warning", "kind": "Fill rate low",
                            "title": f'{b["key"]}: only {b["fill_rate"]:.0%} of order lines shipped complete last week',
                            "detail": f'{b["lines"] - b["lines_filled"]} lines short, week of {week:%b %-d}', "amount": None})
    if "inventory" in apps:
        for s_ in db.query(f"""SELECT sku, description, branch FROM rpt.stock WHERE critical AND location_kind = 'Warehouse'
                               AND on_hand <= 0 AND reorder_point > 0 {_scope(scope)}""", p):
            out.append({"date": t, "severity": "critical", "kind": "Out of stock", "title": f'{s_["description"]} is out at {s_["branch"]}',
                        "detail": "A critical part: jobs that need it will wait", "amount": None, "item_id": s_["sku"]})
    if "people" in apps:
        for c in db.query(f"""SELECT employee_id, employee_name, branch, certification, expires_date, status FROM rpt.certifications
                              WHERE is_active AND expires_date BETWEEN %(since)s - 30 AND %(t)s + %(d)s {_scope(scope)}""",
                          dict(p, d=r["license_days"])):
            expired = c["status"] == "Expired"
            out.append({"date": t if not expired else c["expires_date"], "severity": "critical" if expired else "warning",
                        "kind": "License expired" if expired else "License expiring",
                        "title": f'{c["employee_name"]}: {c["certification"]} {"expired" if expired else "expires"} {c["expires_date"]:%b %-d}',
                        "detail": c["branch"], "amount": None, "employee_id": c["employee_id"]})
        last_monday = t - dt.timedelta(days=t.weekday() + 7)
        for b in db.query(f"""SELECT branch, sum(overtime_hours) AS ot, sum(worked_hours) AS worked FROM rpt.timesheets
                              WHERE week_start = %(w)s {_scope(scope)} GROUP BY 1""", dict(p, w=last_monday)):
            share = _f(b["ot"]) / _f(b["worked"]) if _f(b["worked"]) else 0
            if share > r["overtime_pct"]:
                out.append({"date": last_monday + dt.timedelta(days=6), "severity": "warning", "kind": "Overtime high",
                            "title": f'{b["branch"]}: overtime was {share:.0%} of hours last week',
                            "detail": f'{_f(b["ot"]):,.0f} overtime hours, week of {last_monday:%b %-d}', "amount": None, "branch": None})
    if "purchasing" in apps:
        for po in db.query(f"""SELECT id, number, vendor, branch, amount, expected_date, days_late FROM rpt.purchase_orders
                               WHERE is_open AND days_late > 0 AND amount >= %(m)s {_scope(scope)}""", dict(p, m=r["late_po_min"])):
            out.append({"date": max(since, po["expected_date"] + dt.timedelta(days=1)), "severity": "warning", "kind": "Delivery late",
                        "title": f'{po["vendor"]}: PO {po["number"]} is {po["days_late"]} days late',
                        "detail": f'{po["branch"]} · expected {po["expected_date"]:%b %-d}', "amount": _f(po["amount"]), "po_id": po["id"]})
    return out


def billing_pace(t: dt.date, scope=None) -> list[dict]:
    """Month-to-date billing by branch, against the same dates last year."""
    start = t.replace(day=1)
    ly_t, ly_start = metrics.same_day_last_year(t), metrics.same_day_last_year(start)
    rows = db.query(f"""
        SELECT branch,
               coalesce(sum(amount) FILTER (WHERE invoice_date BETWEEN %(s)s AND %(t)s), 0) AS ty,
               coalesce(sum(amount) FILTER (WHERE invoice_date BETWEEN %(ls)s AND %(lt)s), 0) AS ly
        FROM rpt.invoices WHERE branch IS NOT NULL {_scope(scope)} GROUP BY 1 ORDER BY 1""",
                    {"s": start, "t": t, "ls": ly_start, "lt": ly_t, "scope": scope})
    return [{"branch": x["branch"], "this_year": _f(x["ty"]), "last_year": _f(x["ly"]),
             "share": (_f(x["ty"]) / _f(x["ly"])) if _f(x["ly"]) else 1.0} for x in rows]


def metrics_money(v) -> str:
    v = _f(v)
    if abs(v) >= 1_000_000:
        return f"${v / 1_000_000:.1f}M"
    if abs(v) >= 1_000:
        return f"${v / 1_000:.0f}K"
    return f"${v:,.0f}"


# ---------------------------------------------------------------- what the agents prepare

def closing_soon(t: dt.date, scope=None, days=None) -> list[dict]:
    days = days or rules()["closing_days"]
    return db.query(f"""SELECT id, name, account_id, account_name, branch, owner_name, stage, probability, amount, close_date
                        FROM rpt.deals WHERE is_open AND close_date BETWEEN %(t)s AND %(e)s {_scope(scope)}
                        ORDER BY amount DESC NULLS LAST""", {"t": t, "e": t + dt.timedelta(days=days), "scope": scope})


def last_week_scorecard(t: dt.date, scope=None) -> dict:
    """The most recent complete week of the scorecard: each measure with its value and goal."""
    sc = metrics.scorecard(t, weeks=2, scope=scope)
    week = sc["weeks"][0]
    rows = [{"label": r["label"], "key": r["key"], "format": r["format"], "value": r["values"][0], "goal": r["goal"],
             "hit": (None if r["goal"] is None or r["values"][0] is None else
                     (r["values"][0] >= r["goal"]) if r["higher_is_better"] else (r["values"][0] <= r["goal"]))}
            for r in sc["rows"]]
    return {"week": week, "rows": rows}


def daily_brief(t: dt.date, scope=None) -> list[dict]:
    """The morning brief: a handful of short lines, most important first. Each: text, and an optional link."""
    lines = []
    found = alerts(t, scope, days=1) or []
    late = [a for a in alerts(t, scope, days=7) if a["kind"].startswith("Invoice")]
    slipped = metrics.recent_changes(t, 7, scope)["slipped"]
    soon = closing_soon(t, scope)
    week = last_week_scorecard(t, scope)
    misses = [r["label"] for r in week["rows"] if r["hit"] is False]
    if soon:
        top = soon[0]
        lines.append({"text": f'{len(soon)} deal{"s" if len(soon) != 1 else ""} due to close in the next {rules()["closing_days"]} days, '
                              f'{metrics_money(sum(_f(d["amount"]) for d in soon))} in total. The biggest is {top["name"]} '
                              f'({metrics_money(top["amount"])}, {top["stage"]}, {top["owner_name"]}).',
                      "link": metrics.deals_link(status="open", close_from=t, close_to=t + dt.timedelta(days=rules()["closing_days"]))})
    over = db.one(f"""SELECT count(*) AS n, coalesce(sum(balance), 0) AS total, count(*) FILTER (WHERE days_past_due > 90) AS n90
                       FROM rpt.invoices WHERE is_open AND balance > 0 AND days_past_due > 60 {_scope(scope)}""", {"scope": scope})
    if over["n"]:
        new = f' {len(late)} of them crossed 60 or 90 days this week.' if late else ""
        lines.append({"text": f'{over["n"]} invoice{"s" if over["n"] != 1 else ""} are more than 60 days late, '
                              f'{metrics_money(over["total"])} in total ({over["n90"]} over 90 days).{new} '
                              f'Friendly reminders for the largest 61-120 days late are drafted; older ones need a call.', "link": "/receivables"})
    if slipped:
        lines.append({"text": f'{len(slipped)} open deal{"s" if len(slipped) != 1 else ""} pushed to a later month in the past week '
                              f'({metrics_money(sum(_f(d["amount"]) for d in slipped))}).', "link": "/"})
    if misses:
        lines.append({"text": f'Last week\'s scorecard missed on: {"; ".join(misses)}.', "link": "/scorecard"})
    elif week["rows"]:
        lines.append({"text": "Every measure on last week's scorecard hit its goal.", "link": "/scorecard"})
    behind = [a for a in found if a["kind"] == "Billing behind pace"]
    for a in behind[:2]:
        lines.append({"text": a["title"] + ".", "link": metrics.invoices_link(branch=a["branch"])})
    return lines + ops_brief(t, scope)


def ops_brief(t: dt.date, scope=None) -> list[dict]:
    """Morning-brief lines from the operations systems this install has switched on."""
    apps, lines = get_settings().apps, []
    if "job_cost" in apps:
        w = metrics.wip_summary(scope)
        if w["original_margin"] and w["projected_margin"] is not None and w["original_margin"] - w["projected_margin"] > 0.005:
            pm = max(metrics.fade_by("pm", scope), key=lambda r: float(r["orig_gp"] or 0) - float(r["proj_gp"] or 0), default=None)
            lost = float(pm["orig_gp"] or 0) - float(pm["proj_gp"] or 0) if pm else 0
            lines.append({"text": f'Active jobs are projected at {w["projected_margin"]:.1%} margin against {w["original_margin"]:.1%} at bid'
                                  + (f'; {pm["key"]}\'s {pm["jobs"]} jobs account for {metrics_money(lost)} of the gross profit lost.'
                                     if pm and lost > 100_000 else "."),
                          "link": "/job-cost#fade"})
        losing = [j for j in metrics.wip_jobs(scope) if (j["projected_margin"] or 0) < 0]
        for j in losing[:1]:
            lines.append({"text": f'{j["name"]} is now projected to lose money ({float(j["projected_margin"]):.1%}).', "link": "/job-cost#wip"})
        under = sorted(metrics.wip_jobs(scope), key=lambda j: float(j["over_under"]))[:1]
        if under and float(under[0]["over_under"]) < -250_000:
            j = under[0]
            lines.append({"text": f'{j["name"]} is under-billed by {metrics_money(-float(j["over_under"]))}: '
                                  f'{float(j["pct_complete"]):.0%} done, {float(j["billed"]) / float(j["contract"]):.0%} billed.', "link": "/job-cost#wip"})
        if w["pending"] > 0:
            lines.append({"text": f'{int(w["pending_n"])} change orders worth {metrics_money(w["pending"])} are waiting on owners\' signatures.',
                          "link": "/job-cost#changes"})
    if "projects" in apps:
        first, last = metrics._weeks_back(t, 4)
        offices = [b for b in metrics.utilization_by("branch", first, last, scope) if b["recorded"] >= 400]
        low = min(offices, key=lambda b: b["billable_util"] or 1, default=None)
        if low and (low["billable_util"] or 1) < 0.68:
            lines.append({"text": f'{low["key"]} billed only {low["billable_util"]:.0%} of its hours over the last four weeks, against '
                                  f'a 75% target: its people have room for more work.', "link": "/projects"})
        risk = metrics.projects_at_risk(scope)
        if risk:
            lines.append({"text": f'{len(risk)} fixed-fee project{"s are" if len(risk) != 1 else " is"} burning budget faster than '
                                  f'{"they progress" if len(risk) != 1 else "it progresses"}.', "link": "/projects#risk"})
        pms = [r for r in metrics.projects_by("pm", t, scope) if r["projects"] >= 5 and r["realization"] is not None]
        worst = min(pms, key=lambda r: r["realization"], default=None)
        if worst and worst["realization"] < 0.85:
            lines.append({"text": f'{worst["key"]}\'s projects billed {worst["realization"]:.0%} of the hours they took over the last year '
                                  f'(the firm averages {metrics.projects_summary(t, scope)["realization"]:.0%}): fixed fees running over.',
                          "link": "/projects#realization"})
        stale = [u for u in metrics.unbilled_projects(t, scope) if (u["days"] or 0) > 60]
        if stale:
            top = stale[0]
            lines.append({"text": f'{top["name"]} has {metrics_money(top["unbilled_value"])} of time not billed since '
                                  f'{top["oldest_unbilled"]:%B %-d}.', "link": "/projects#wip"})
    if "orders" in apps:
        month = metrics.orders_by("branch", t - dt.timedelta(days=29), t, scope)
        worst = min((b for b in month if b["lines"] >= 100), key=lambda b: b["fill_rate"] or 1, default=None)
        if worst and (worst["fill_rate"] or 1) < 0.92:
            lines.append({"text": f'{worst["key"]} shipped {worst["fill_rate"]:.0%} of order lines complete in the last 30 days, '
                                  f'against a 95% goal: customers there are waiting on backorders.', "link": "/orders#fill"})
        trend = metrics.margin_by_month(t, 12, scope=scope)
        drops = []
        for k, v in trend.items():
            ms = sorted(v)
            if len(ms) >= 6 and v[ms[0]] is not None and v[ms[-1]] is not None:
                drops.append((v[ms[0]] - v[ms[-1]], k, v[ms[0]], v[ms[-1]]))
        if drops and max(drops)[0] > 0.03:
            d, k, a, b = max(drops)
            lines.append({"text": f'{k} margin has slid from {a:.0%} to {b:.0%} over the year. Check whether vendor price '
                                  f'increases were passed on.', "link": "/orders#margin"})
    if "inventory" in apps:
        out = db.query(f"""SELECT description, branch FROM rpt.stock WHERE critical AND location_kind = 'Warehouse' AND on_hand <= 0
                           AND reorder_point > 0 {_scope(scope)}""", {"scope": scope})
        if out:
            lines.append({"text": f'Out of stock: {"; ".join(f"{o["description"]} at {o["branch"]}" for o in out[:3])}. '
                                  f'Both are critical items, so work that needs them will wait.' if len(out) == 2 else
                                  f'{len(out)} critical part{"s are" if len(out) != 1 else " is"} out of stock at a warehouse.',
                          "link": "/inventory#reorder"})
    if "field_service" in apps:
        month = metrics.jobs_by_branch(t - dt.timedelta(days=29), t, scope)
        worst = min((b for b in month if b["em_reached"] >= 10 and b["emergency_on_time"] is not None),
                    key=lambda b: b["emergency_on_time"], default=None)
        if worst and worst["emergency_on_time"] < 0.85:
            lines.append({"text": f'{worst["branch"]} reached {worst["emergency_on_time"]:.0%} of emergency calls within 4 hours in the '
                                  f'last 30 days ({int(worst["em_on_time"])} of {int(worst["em_reached"])}), against a 90% goal.', "link": "/jobs"})
        unbilled = metrics.jobs_not_invoiced(t, scope)
        if unbilled:
            lines.append({"text": f'{len(unbilled)} completed jobs are still not invoiced after 14 days '
                                  f'({metrics_money(sum(_f(j["billable_amount"]) for j in unbilled))}).', "link": "/cleanup#job_not_invoiced"})
    if "people" in apps:
        expired = [c for c in metrics.cert_problems(scope) if c["status"] == "Expired"]
        if expired:
            lines.append({"text": f'{len(expired)} {"people are" if len(expired) != 1 else "person is"} working on an expired license: '
                                  f'{", ".join(c["employee_name"] for c in expired[:3])}.', "link": "/people#certs"})
    return lines


def followup_drafts(t: dt.date, scope=None, n: int = 3) -> list[dict]:
    """Friendly payment reminders for the largest invoices 61-120 days late, ready for someone to approve.
    Anything older needs a call from a person, not a friendly email."""
    rows = db.query(f"""SELECT id, number, customer_name, branch, invoice_date, due_date, balance, days_past_due
                        FROM rpt.invoices WHERE is_open AND balance > 0 AND days_past_due BETWEEN 61 AND 120 {_scope(scope)}
                        ORDER BY balance DESC LIMIT {int(n)}""", {"scope": scope})
    company = get_settings().client.get("company", "us")
    out = []
    for i in rows:
        body = (f"Hi {i['customer_name']} team,\n\n"
                f"I hope all is well. Our records show invoice {i['number']} for {metrics_money(i['balance'])}, dated "
                f"{i['invoice_date']:%B %-d, %Y}, is now {i['days_past_due']} days past its due date of {i['due_date']:%B %-d, %Y}.\n\n"
                f"If it's already on its way, thank you, and please ignore this note. If anything about the invoice needs "
                f"sorting out, just reply and we'll take care of it.\n\nThank you,\n{company} accounts")
        out.append({"invoice_id": i["id"], "to": i["customer_name"], "branch": i["branch"],
                    "subject": f"Invoice {i['number']}: a friendly reminder", "body": body,
                    "amount": _f(i["balance"]), "days": i["days_past_due"]})
    return out


def weekly_update(t: dt.date, scope=None) -> dict:
    """A short written update on last week, from the scorecard and what changed."""
    week = last_week_scorecard(t, scope)
    start = week["week"]
    end = start + dt.timedelta(days=6)
    by = {r["key"]: r for r in week["rows"]}

    def fmt(r):
        if r["value"] is None:
            return "no figure"
        v = f'{r["value"]:.1f}%' if r["format"] == "pct" else (f'{int(r["value"])}' if r["format"] == "count" else metrics_money(r["value"]))
        if r["goal"] is None:
            return v
        g = f'{r["goal"]:.0f}%' if r["format"] == "pct" else (f'{int(r["goal"])}' if r["format"] == "count" else metrics_money(r["goal"]))
        return f"{v} against a {g} goal"
    closed = db.query(f"""SELECT name, amount, is_won, branch FROM rpt.deals
                          WHERE is_closed AND close_date BETWEEN %(s)s AND %(e)s {_scope(scope)}
                          ORDER BY amount DESC NULLS LAST""", {"s": start, "e": end, "scope": scope})
    won = [c for c in closed if c["is_won"]]
    lost = [c for c in closed if not c["is_won"]]
    hits = sum(1 for r in week["rows"] if r["hit"])
    scored = sum(1 for r in week["rows"] if r["hit"] is not None)
    paras = [
        f"Week of {start:%B %-d}: {hits} of {scored} scorecard measures hit their goal.",
        f"Bookings came in at {fmt(by['bookings'])}, from {len(won)} won deal{'s' if len(won) != 1 else ''}"
        + (f", led by {won[0]['name']} ({metrics_money(won[0]['amount'])})." if won else "."),
        f"New pipeline was {fmt(by['new_pipeline'])} across {fmt(by['new_deals']).split(' against')[0]} new deals. "
        f"The trailing 90-day win rate by dollars is {fmt(by['win_rate_dollars'])}.",
        f"On the money side, billing over the past 31 days was {fmt(by['billed_4wk'])}, cash collected was "
        f"{fmt(by['collected'])}, and receivables over 60 days stood at {fmt(by['ar_over_60'])}.",
    ]
    if lost:
        paras.append(f"The biggest loss was {lost[0]['name']} ({metrics_money(lost[0]['amount'])}).")
    return {"week": start, "title": f"Weekly update: week of {start:%B %-d}", "paragraphs": paras}


def meeting_prep(t: dt.date, scope=None, within_days: int = 21) -> dict | None:
    """One page on the biggest deal due to close soon: the deal, the account's history, and what to ask."""
    soon = closing_soon(t, scope, within_days)
    if not soon:
        return None
    d = soon[0]
    p = {"a": d["account_id"], "id": d["id"], "scope": scope}
    hist = db.one(f"""SELECT count(*) FILTER (WHERE is_won) AS won_n, coalesce(sum(amount) FILTER (WHERE is_won), 0) AS won_amt,
                             count(*) FILTER (WHERE is_lost) AS lost_n, count(*) FILTER (WHERE is_open) AS open_n,
                             min(created_date) AS first_seen
                      FROM rpt.deals WHERE account_id = %(a)s""", p)
    ar = db.one("""SELECT coalesce(sum(balance), 0) AS unpaid, coalesce(max(days_past_due), 0) AS oldest
                   FROM rpt.invoices WHERE account_id = %(a)s AND is_open""", p)
    changes = db.query("""SELECT changed_date, field, old_value, new_value FROM rpt.deal_history
                          WHERE deal_id = %(id)s ORDER BY changed_at DESC LIMIT 3""", p)
    asks = {"Negotiation": ["What would stop this from signing by the close date?", "Who else needs to approve it?"],
            "Proposal": ["How does our proposal compare with the alternatives they're weighing?", "What's their decision process and timing?"]}
    return {"deal": d, "history": hist, "ar": ar, "changes": changes,
            "questions": asks.get(d["stage"], ["What problem does this solve for them this quarter?", "Who decides, and when?"])
                         + ["Is there anything about past work or invoices we should clear up first?"]}


# ---------------------------------------------------------------- forecast

CALLS = {"commit": "Commit", "best": "Best case", "pipeline": "Pipeline", "omit": "Omit"}


def quarter(t: dt.date):
    q0 = dt.date(t.year, 3 * ((t.month - 1) // 3) + 1, 1)
    q1 = (dt.date(q0.year + (q0.month + 2) // 12, (q0.month + 2) % 12 + 1, 1) - dt.timedelta(days=1))
    return q0, q1


def default_call(probability) -> str:
    p = _f(probability)
    return "commit" if p >= 75 else ("best" if p >= 40 else "pipeline")


def forecast(t: dt.date, scope=None) -> dict:
    q0, q1 = quarter(t)
    deals = db.query(f"""SELECT id, name, account_name, branch, owner_name, stage, probability, amount, close_date
                         FROM rpt.deals WHERE is_open AND close_date BETWEEN %(t)s AND %(q1)s {_scope(scope)}
                         ORDER BY close_date, amount DESC""", {"t": t, "q1": q1, "scope": scope})
    saved = {r["deal_id"]: r for r in db.query("SELECT deal_id, call, updated_by, updated_at FROM core.forecast_calls")}
    for d in deals:
        s = saved.get(d["id"])
        d["call"] = s["call"] if s else default_call(d["probability"])
        d["saved"] = bool(s)
    booked = metrics.closed_summary(q0, t, scope)["won_amount"]
    total = lambda c: sum(_f(d["amount"]) for d in deals if d["call"] == c)
    return {"quarter_start": q0, "quarter_end": q1, "booked": booked, "deals": deals,
            "commit": booked + total("commit"), "best": booked + total("commit") + total("best"),
            "open_total": sum(_f(d["amount"]) for d in deals)}


def save_calls(calls: dict, user_email: str) -> int:
    """calls: deal id -> call. Saves only real open deals and known calls; returns how many were saved."""
    ok = {k: v for k, v in calls.items() if v in CALLS}
    if not ok:
        return 0
    known = {r["id"] for r in db.query("SELECT id FROM rpt.deals WHERE is_open AND id = ANY(%(ids)s)", {"ids": list(ok)})}
    n = 0
    with db.connect() as conn:
        for deal_id, call in ok.items():
            if deal_id in known:
                db.execute("""INSERT INTO core.forecast_calls (deal_id, call, updated_by) VALUES (%(d)s, %(c)s, %(u)s)
                              ON CONFLICT (deal_id) DO UPDATE SET call = EXCLUDED.call, updated_by = EXCLUDED.updated_by,
                                                                  updated_at = now()""",
                           {"d": deal_id, "c": call, "u": user_email}, conn)
                n += 1
    return n
