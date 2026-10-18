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
    "billing_pace": 0.85,      # a branch billing below this share of last year's month-to-date is an alert
    "billing_min": 50_000,     # ...if last year's month-to-date was at least this much
    "closing_days": 7,         # the brief lists deals due to close within this many days
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
                            WHERE is_open AND balance > 0 AND (due_date + %(n)s) BETWEEN %(since)s AND %(t)s
                            {_scope(scope)}""", dict(p, n=n))
        for i in rows:
            out.append({"date": i["due_date"] + dt.timedelta(days=n), "severity": "critical" if n == marks[-1] else "warning",
                        "kind": f"Invoice {n} days late", "title": f'{i["customer_name"]}: invoice {i["number"]}',
                        "detail": f'{i["branch"]} · due {i["due_date"]:%b %-d}', "amount": _f(i["balance"]),
                        "invoice_id": i["id"]})
    for b in billing_pace(t, scope):
        if b["last_year"] >= r["billing_min"] and b["share"] < r["billing_pace"]:
            out.append({"date": t, "severity": "warning", "kind": "Billing behind pace",
                        "title": f'{b["branch"]} is at {b["share"]:.0%} of last year\'s billing for the month so far',
                        "detail": f'{metrics_money(b["this_year"])} vs {metrics_money(b["last_year"])} by this date last year',
                        "amount": None, "branch": b["branch"]})
    order = {"critical": 0, "warning": 1, "good": 2}
    out.sort(key=lambda a: (a["date"] or t, -order[a["severity"]], a.get("amount") or 0), reverse=True)
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
