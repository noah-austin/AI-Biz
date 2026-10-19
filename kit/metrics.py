"""Every number the hub shows is computed here, once.

Pages call these functions, and the AI layer will call the same ones, so a
figure is the same wherever it appears. The plain-English definitions live in
HOW (shown as "how this is counted" footnotes) and in the client's rulebook.

Rules that apply throughout:
- Percentages are weighted: sum of numerators / sum of denominators over the
  filtered rows. Never an average of percentages.
- A missing value is not zero: deals with no margin are left out of margin %.
- Year-to-date compares like with like: Jan 1 to today vs. Jan 1 to the same
  day last year.
- Dates are the client's local dates (see core.client_tz()).
- `scope` is a list of branch codes a user may see; None means all branches.
"""
import datetime as dt
from urllib.parse import urlencode

from . import db

HOW = {
    "bookings": "Total amount of deals marked Closed Won, by close date. Excludes deals flagged "
                "'exclude from reporting'.",
    "win_rate": "Of deals closed (won or lost) in the period: won ÷ (won + lost). By dollars it's won amount ÷ "
                "closed amount; by count it's the number of deals. Open deals don't count.",
    "margin": "Weighted margin on won deals: total margin dollars ÷ total amount, counting only deals that have "
              "a margin entered. Deals with no margin are left out, not counted as 0%.",
    "pipeline": "Open deals by expected close date. Weighted = amount × the stage's probability. Deals whose "
                "close date has already passed are shown separately as 'past due'.",
    "new_pipeline": "Deals created in the period, whatever has happened to them since.",
    "billed": "Total of invoices dated in the period, from accounting.",
    "billed_4wk": "Invoices dated in the 31 days ending each week. Service contracts bill on the 1st of the month, "
                  "so single weeks swing a lot; any 31 days holds at least one month-start.",
    "collected": "Payments received in the period (by paid date), from accounting.",
    "ar": "Unpaid invoice balances today, grouped by how far past the due date they are.",
    "ar_over_60": "Unpaid balance on invoices more than 60 days past due, as it stood at the end of each week.",
}


def _scope(scope, col="branch_code"):
    return f" AND {col} = ANY(%(scope)s)" if scope else ""


def deals_link(**filters) -> str:
    return "/deals?" + urlencode({k: v for k, v in filters.items() if v not in (None, "")})


def invoices_link(**filters) -> str:
    return "/invoices?" + urlencode({k: v for k, v in filters.items() if v not in (None, "")})


def today() -> dt.date:
    return db.one("SELECT core.local_today() AS d")["d"]


def same_day_last_year(d: dt.date) -> dt.date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # Feb 29
        return d.replace(year=d.year - 1, day=28)


def ytd_windows(t: dt.date):
    this = (dt.date(t.year, 1, 1), t)
    last = (dt.date(t.year - 1, 1, 1), same_day_last_year(t))
    return this, last


def _ratio(num, den):
    return float(num) / float(den) if den else None


# ---------- deals ----------

def closed_summary(start, end, scope=None) -> dict:
    r = db.one(f"""
        SELECT coalesce(sum(amount) FILTER (WHERE is_won), 0)  AS won_amount,
               count(*) FILTER (WHERE is_won)                  AS won_count,
               coalesce(sum(amount) FILTER (WHERE is_lost), 0) AS lost_amount,
               count(*) FILTER (WHERE is_lost)                 AS lost_count,
               coalesce(sum(margin_amount) FILTER (WHERE is_won), 0) AS margin_dollars,
               coalesce(sum(amount) FILTER (WHERE is_won AND margin_pct IS NOT NULL), 0) AS margin_base,
               count(*) FILTER (WHERE is_won AND margin_pct IS NULL) AS won_missing_margin
        FROM rpt.deals
        WHERE is_closed AND close_date BETWEEN %(start)s AND %(end)s {_scope(scope)}""",
                 {"start": start, "end": end, "scope": scope})
    r = {k: float(v) if v is not None else None for k, v in r.items()}
    r["win_rate_dollars"] = _ratio(r["won_amount"], r["won_amount"] + r["lost_amount"])
    r["win_rate_count"] = _ratio(r["won_count"], r["won_count"] + r["lost_count"])
    r["margin_pct"] = _ratio(r["margin_dollars"], r["margin_base"])
    return r


def pipeline_summary(t: dt.date, scope=None) -> dict:
    year_end = dt.date(t.year, 12, 31)
    r = db.one(f"""
        SELECT coalesce(sum(amount) FILTER (WHERE close_date BETWEEN %(t)s AND %(ye)s), 0) AS this_year,
               coalesce(sum(weighted_amount) FILTER (WHERE close_date BETWEEN %(t)s AND %(ye)s), 0) AS this_year_weighted,
               count(*) FILTER (WHERE close_date BETWEEN %(t)s AND %(ye)s) AS this_year_count,
               coalesce(sum(amount) FILTER (WHERE close_date > %(ye)s AND close_date < %(far)s), 0) AS later,
               coalesce(sum(amount) FILTER (WHERE close_date < %(t)s), 0) AS past_due,
               count(*) FILTER (WHERE close_date < %(t)s) AS past_due_count
        FROM rpt.deals WHERE is_open {_scope(scope)}""",
                 {"t": t, "ye": year_end, "far": dt.date(t.year + 5, 1, 1), "scope": scope})
    return {k: float(v) for k, v in r.items()}


def created_summary(start, end, scope=None) -> dict:
    r = db.one(f"""SELECT count(*) AS count, coalesce(sum(amount), 0) AS amount FROM rpt.deals
                   WHERE created_date BETWEEN %(start)s AND %(end)s {_scope(scope)}""",
               {"start": start, "end": end, "scope": scope})
    return {k: float(v) for k, v in r.items()}


def bookings_by_month(year: int, scope=None) -> list[float]:
    rows = db.query(f"""
        SELECT extract(month FROM close_date)::int AS m, sum(amount) AS amount FROM rpt.deals
        WHERE is_won AND close_date BETWEEN %(s)s AND %(e)s {_scope(scope)} GROUP BY 1""",
                    {"s": dt.date(year, 1, 1), "e": dt.date(year, 12, 31), "scope": scope})
    out = [0.0] * 12
    for r in rows:
        out[r["m"] - 1] = float(r["amount"])
    return out


def bookings_goal(year: int) -> float | None:
    r = db.one("SELECT value FROM core.goals WHERE metric = 'bookings' AND period = %(p)s", {"p": str(year)})
    return float(r["value"]) if r else None


def sell_best_grid(start, end, scope=None, dim_a="segment", dim_b="deal_type", min_closed=5) -> dict:
    """Close rate and won dollars for every pair of two dimensions.

    'Where we sell best' ranks cells by won dollars, among cells with at least
    `min_closed` closed deals whose close rate (by dollars) beats the overall
    rate. Ranking by rate alone puts tiny 100%-win cells on top.
    """
    allowed = {"segment", "deal_type", "branch", "region", "lead_source", "owner_name"}
    if dim_a not in allowed or dim_b not in allowed or dim_a == dim_b:
        raise ValueError("unsupported dimension")
    rows = db.query(f"""
        SELECT {dim_a} AS a, {dim_b} AS b,
               coalesce(sum(amount) FILTER (WHERE is_won), 0) AS won_amount,
               coalesce(sum(amount), 0) AS closed_amount,
               count(*) FILTER (WHERE is_won) AS won_count, count(*) AS closed_count
        FROM rpt.deals WHERE is_closed AND close_date BETWEEN %(s)s AND %(e)s {_scope(scope)}
        GROUP BY 1, 2""", {"s": start, "e": end, "scope": scope})
    won = sum(float(r["won_amount"]) for r in rows)
    closed = sum(float(r["closed_amount"]) for r in rows)
    overall = _ratio(won, closed)
    cells = []
    for r in rows:
        c = {"a": r["a"] or "(blank)", "b": r["b"] or "(blank)", "won_amount": float(r["won_amount"]),
             "closed_amount": float(r["closed_amount"]), "won_count": r["won_count"],
             "closed_count": r["closed_count"]}
        c["rate_dollars"] = _ratio(c["won_amount"], c["closed_amount"])
        c["rate_count"] = _ratio(c["won_count"], c["closed_count"])
        cells.append(c)
    best = sorted((c for c in cells if c["closed_count"] >= min_closed and overall is not None
                   and (c["rate_dollars"] or 0) > overall), key=lambda c: -c["won_amount"])[:3]
    return {"cells": cells, "overall_rate": overall, "best": best,
            "a_values": sorted({c["a"] for c in cells}), "b_values": sorted({c["b"] for c in cells})}


def quarterly_win_rates(t: dt.date, quarters=8, scope=None) -> list[dict]:
    start = dt.date(t.year - (quarters // 4), ((t.month - 1) // 3) * 3 + 1, 1)
    rows = db.query(f"""
        SELECT date_trunc('quarter', close_date)::date AS q,
               coalesce(sum(amount) FILTER (WHERE is_won), 0) AS won_amount, coalesce(sum(amount), 0) AS closed_amount,
               count(*) FILTER (WHERE is_won) AS won_count, count(*) AS closed_count
        FROM rpt.deals WHERE is_closed AND close_date BETWEEN %(s)s AND %(t)s {_scope(scope)}
        GROUP BY 1 ORDER BY 1""", {"s": start, "t": t, "scope": scope})
    out = []
    for r in rows[-quarters:]:
        q = r["q"]
        out.append({"label": f"Q{(q.month - 1) // 3 + 1} {q.year}", "start": q,
                    "won_amount": float(r["won_amount"]), "lost_amount": float(r["closed_amount"] - r["won_amount"]),
                    "rate_dollars": _ratio(r["won_amount"], r["closed_amount"]),
                    "rate_count": _ratio(r["won_count"], r["closed_count"])})
    return out


# ---------- money in ----------

def billing_summary(start, end, scope=None) -> dict:
    r = db.one(f"""
        SELECT coalesce(sum(amount) FILTER (WHERE invoice_date BETWEEN %(s)s AND %(e)s), 0) AS billed,
               coalesce(sum(amount_paid) FILTER (WHERE paid_date BETWEEN %(s)s AND %(e)s), 0) AS collected
        FROM rpt.invoices WHERE true {_scope(scope)}""", {"s": start, "e": end, "scope": scope})
    return {k: float(v) for k, v in r.items()}


AGING_ORDER = ["Current", "1–30 days", "31–60 days", "61–90 days", "Over 90 days"]


def ar_aging(scope=None) -> dict:
    rows = db.query(f"""SELECT aging_bucket AS bucket, sum(balance) AS balance, count(*) AS n
                        FROM rpt.invoices WHERE is_open {_scope(scope)} GROUP BY 1""", {"scope": scope})
    by = {r["bucket"]: (float(r["balance"]), r["n"]) for r in rows}
    buckets = [{"bucket": b, "balance": by.get(b, (0.0, 0))[0], "count": by.get(b, (0.0, 0))[1]} for b in AGING_ORDER]
    total = sum(b["balance"] for b in buckets)
    over_60 = sum(b["balance"] for b in buckets if b["bucket"] in ("61–90 days", "Over 90 days"))
    return {"buckets": buckets, "total": total, "over_60": over_60}


# ---------- weekly scorecard ----------

SCORECARD = [  # key, label, format, higher_is_better, how, app it needs
    ("new_deals", "New deals created", "count", True, "new_pipeline", "analytics"),
    ("new_pipeline", "New pipeline created", "money", True, "new_pipeline", "analytics"),
    ("bookings", "Bookings (won)", "money", True, "bookings", "analytics"),
    ("win_rate_dollars", "Win rate by $, trailing 90 days", "pct", True, "win_rate", "analytics"),
    ("billed_4wk", "Billed, past 31 days", "money", True, "billed_4wk", "analytics"),
    ("collected", "Cash collected", "money", True, "collected", "analytics"),
    ("ar_over_60", "AR over 60 days past due", "money", False, "ar_over_60", "analytics"),
    ("emergency_on_time", "Emergency calls reached in 4 hours", "pct", True, "emergency_on_time", "field_service"),
    ("first_time_fix", "First-time fix", "pct", True, "first_time_fix", "field_service"),
    ("overtime_pct", "Overtime, % of hours worked", "pct", False, "overtime", "people"),
    ("billable_util", "Billable utilization", "pct", True, "billable_util", "projects"),
    ("fill_rate", "Fill rate (lines complete first time)", "pct", True, "fill_rate", "orders"),
    ("on_time_ship", "Orders shipped on time", "pct", True, "on_time_ship", "orders"),
    ("gross_margin", "Gross margin on orders", "pct", True, "gross_margin", "orders"),
]


def scorecard(t: dt.date, weeks=13, scope=None) -> dict:
    """One column per week (Monday to Sunday), newest last; the last column is this week so far."""
    this_monday = t - dt.timedelta(days=t.weekday())
    starts = [this_monday - dt.timedelta(weeks=i) for i in range(weeks - 1, -1, -1)]
    first = starts[0]
    p = {"first": first, "t": t, "scope": scope}
    wk = "date_trunc('week', {col})::date"

    def by_week(sql_text, params=p):
        return {r["w"]: float(r["v"] or 0) for r in db.query(sql_text, params)}

    created = db.query(f"""SELECT {wk.format(col='created_date')} AS w, count(*) AS n, sum(amount) AS amt
                           FROM rpt.deals WHERE created_date BETWEEN %(first)s AND %(t)s {_scope(scope)}
                           GROUP BY 1""", p)
    new_deals = {r["w"]: float(r["n"]) for r in created}
    new_pipe = {r["w"]: float(r["amt"] or 0) for r in created}
    bookings = by_week(f"""SELECT {wk.format(col='close_date')} AS w, sum(amount) AS v FROM rpt.deals
                           WHERE is_won AND close_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""")
    collected = by_week(f"""SELECT {wk.format(col='paid_date')} AS w, sum(amount_paid) AS v FROM rpt.invoices
                            WHERE paid_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""")
    # Point-in-time figures, rebuilt for the last day of each week.
    ends = {s: min(t, s + dt.timedelta(days=6)) for s in starts}
    p2 = dict(p, starts=starts, ends=[ends[s] for s in starts])
    win = {r["w"]: (float(r["won"] or 0), float(r["closed"] or 0)) for r in db.query(f"""
        SELECT w.s AS w, sum(d.amount) FILTER (WHERE d.is_won) AS won, sum(d.amount) AS closed
        FROM unnest(%(starts)s::date[], %(ends)s::date[]) AS w(s, e)
        JOIN rpt.deals d ON d.is_closed AND d.close_date BETWEEN w.e - 89 AND w.e {_scope(scope, 'd.branch_code')}
        GROUP BY 1""", p2)}
    billed_4wk = by_week(f"""
        SELECT w.s AS w, sum(i.amount) AS v
        FROM unnest(%(starts)s::date[], %(ends)s::date[]) AS w(s, e)
        JOIN rpt.invoices i ON i.invoice_date BETWEEN w.e - 30 AND w.e {_scope(scope, 'i.branch_code')}
        GROUP BY 1""", p2)
    ar60 = by_week(f"""
        -- Accounting gives one paid date per invoice, so this treats payments as paid in full.
        SELECT w.s AS w, sum(i.amount) AS v
        FROM unnest(%(starts)s::date[], %(ends)s::date[]) AS w(s, e)
        JOIN rpt.invoices i ON i.invoice_date <= w.e AND i.due_date < w.e - 60
             AND (i.paid_date IS NULL OR i.paid_date > w.e) {_scope(scope, 'i.branch_code')}
        GROUP BY 1""", p2)
    series = {
        "new_deals": new_deals, "new_pipeline": new_pipe, "bookings": bookings, "billed_4wk": billed_4wk,
        "collected": collected, "ar_over_60": ar60,
        "win_rate_dollars": {w: (100 * a / b if b else None) for w, (a, b) in win.items()},
    }
    from .config import get_settings
    apps = get_settings().apps
    if "field_service" in apps:
        jobs = {r["w"]: r for r in db.query(f"""
            SELECT {wk.format(col='arrived_date')} AS w, count(*) FILTER (WHERE on_time) AS ok, count(*) AS n FROM rpt.jobs
            WHERE priority = 'Emergency' AND arrived_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["emergency_on_time"] = {w: 100 * r["ok"] / r["n"] for w, r in jobs.items() if r["n"]}
        fix = {r["w"]: r for r in db.query(f"""
            SELECT {wk.format(col='completed_date')} AS w, count(*) FILTER (WHERE fixed_first_time IS NOT NULL) AS repairs,
                   count(*) FILTER (WHERE is_callback AND status = 'Completed') AS back FROM rpt.jobs
            WHERE completed_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["first_time_fix"] = {w: 100 * (1 - r["back"] / r["repairs"]) for w, r in fix.items() if r["repairs"]}
    if "people" in apps:
        ot = {r["w"]: r for r in db.query(f"""
            SELECT week_start AS w, sum(overtime_hours) AS ot, sum(worked_hours) AS worked FROM rpt.timesheets
            WHERE week_start BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["overtime_pct"] = {w: 100 * float(r["ot"] or 0) / float(r["worked"]) for w, r in ot.items() if r["worked"]}
    if "projects" in apps:
        te = {r["w"]: r for r in db.query(f"""
            SELECT date_trunc('week', week_ending)::date AS w, sum(hours) FILTER (WHERE billable) AS b, sum(hours) AS n
            FROM rpt.time_entries WHERE week_ending BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["billable_util"] = {w: 100 * float(r["b"] or 0) / float(r["n"]) for w, r in te.items() if r["n"]}
    if "orders" in apps:
        ol = {r["w"]: r for r in db.query(f"""
            SELECT {wk.format(col='order_date')} AS w, count(*) AS lines, count(*) FILTER (WHERE filled_first_time) AS filled,
                   sum(sales) AS sales, sum(cost) AS cost FROM rpt.order_lines
            WHERE status <> 'Canceled' AND order_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["fill_rate"] = {w: 100 * r["filled"] / r["lines"] for w, r in ol.items() if r["lines"]}
        series["gross_margin"] = {w: 100 * float(r["sales"] - r["cost"]) / float(r["sales"]) for w, r in ol.items() if r["sales"]}
        oo = {r["w"]: r for r in db.query(f"""
            SELECT {wk.format(col='order_date')} AS w, count(*) FILTER (WHERE on_time IS NOT NULL) AS n, count(*) FILTER (WHERE on_time) AS ok
            FROM rpt.orders WHERE status <> 'Canceled' AND order_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""", p)}
        series["on_time_ship"] = {w: 100 * r["ok"] / r["n"] for w, r in oo.items() if r["n"]}
    goals = {r["metric"]: float(r["value"]) for r in
             db.query("SELECT metric, value FROM core.goals WHERE period = 'weekly'")}
    rows = []
    for key, label, fmt, higher_better, how, app in SCORECARD:
        if app not in apps:
            continue
        goal = goals.get(key)
        if scope and goal is not None and fmt != "pct":
            goal = None  # company goals don't split by branch; hide rather than mislead
        values = [series[key].get(s, 0.0 if fmt != "pct" else None) for s in starts]
        rows.append({"key": key, "label": label, "format": fmt, "higher_is_better": higher_better,
                     "goal": goal, "values": values, "how": HOW[how]})
    return {"weeks": starts, "partial_last": True, "rows": rows}


# ---------- what changed ----------

def recent_changes(t: dt.date, days=7, scope=None) -> dict:
    since = t - dt.timedelta(days=days - 1)
    p = {"since": since, "t": t, "scope": scope}
    created = db.query(f"""SELECT id, name, account_name, branch, deal_type, amount FROM rpt.deals
                           WHERE created_date BETWEEN %(since)s AND %(t)s {_scope(scope)}
                           ORDER BY amount DESC NULLS LAST""", p)
    closed = db.query(f"""SELECT id, name, branch, amount, is_won FROM rpt.deals
                          WHERE is_closed AND close_date BETWEEN %(since)s AND %(t)s {_scope(scope)}
                          ORDER BY amount DESC NULLS LAST""", p)
    slipped = db.query(f"""
        SELECT DISTINCT ON (h.deal_id) h.deal_id AS id, h.deal_name AS name, h.branch, d.amount,
               CASE WHEN h.field = 'CloseDate' THEN h.old_value::date END AS old_close,
               CASE WHEN h.field = 'CloseDate' THEN h.new_value::date END AS new_close
        FROM rpt.deal_history h JOIN rpt.deals d ON d.id = h.deal_id
        WHERE h.field = 'CloseDate' AND d.is_open AND h.changed_date BETWEEN %(since)s AND %(t)s
          -- Only CloseDate rows hold dates; the CASE stops the cast ever touching Amount or Stage values.
          AND date_trunc('month', CASE WHEN h.field = 'CloseDate' THEN h.new_value::date END)
            > date_trunc('month', CASE WHEN h.field = 'CloseDate' THEN h.old_value::date END)
          {_scope(scope, 'h.branch_code')}
        ORDER BY h.deal_id, h.changed_at DESC""", p)
    slipped.sort(key=lambda r: -(float(r["amount"] or 0)))
    won = [r for r in closed if r["is_won"]]
    lost = [r for r in closed if not r["is_won"]]
    total = lambda rows: sum(float(r["amount"] or 0) for r in rows)
    return {"since": since, "created": created, "won": won, "lost": lost, "slipped": slipped,
            "totals": {"created": total(created), "won": total(won), "lost": total(lost), "slipped": total(slipped)}}


def freshness() -> dict:
    r = db.one("""SELECT min(last_success_at) AS oldest, max(last_attempt_at) AS latest,
                         count(*) FILTER (WHERE last_status = 'failed') AS failed
                  FROM core.sync_state WHERE object <> 'backup'""")
    return r or {}


# ---------- breakdowns (used by the AI layer; same rules as the pages) ----------

DIMENSIONS = {"segment", "deal_type", "branch", "region", "lead_source", "owner_name", "stage", "loss_reason"}


def closed_breakdown(start, end, dim: str, scope=None) -> list[dict]:
    """Won/lost results for closed deals, split by one dimension."""
    if dim not in DIMENSIONS:
        raise ValueError(f"group_by must be one of {sorted(DIMENSIONS)}")
    rows = db.query(f"""
        SELECT coalesce({dim}::text, '(blank)') AS key,
               coalesce(sum(amount) FILTER (WHERE is_won), 0) AS won_amount, count(*) FILTER (WHERE is_won) AS won_count,
               coalesce(sum(amount) FILTER (WHERE is_lost), 0) AS lost_amount, count(*) FILTER (WHERE is_lost) AS lost_count,
               coalesce(sum(margin_amount) FILTER (WHERE is_won), 0) AS margin_dollars,
               coalesce(sum(amount) FILTER (WHERE is_won AND margin_pct IS NOT NULL), 0) AS margin_base
        FROM rpt.deals WHERE is_closed AND close_date BETWEEN %(s)s AND %(e)s {_scope(scope)}
        GROUP BY 1 ORDER BY 2 DESC""", {"s": start, "e": end, "scope": scope})
    out = []
    for r in rows:
        r = {k: (float(v) if k != "key" and v is not None else v) for k, v in r.items()}
        r["win_rate_dollars"] = _ratio(r["won_amount"], r["won_amount"] + r["lost_amount"])
        r["win_rate_count"] = _ratio(r["won_count"], r["won_count"] + r["lost_count"])
        r["margin_pct"] = _ratio(r["margin_dollars"], r["margin_base"])
        out.append(r)
    return out


def pipeline_breakdown(t: dt.date, dim: str, scope=None) -> list[dict]:
    """Open pipeline split by one dimension, with past-due deals counted separately."""
    if dim not in DIMENSIONS:
        raise ValueError(f"group_by must be one of {sorted(DIMENSIONS)}")
    rows = db.query(f"""
        SELECT coalesce({dim}::text, '(blank)') AS key, count(*) FILTER (WHERE close_date >= %(t)s) AS deals,
               coalesce(sum(amount) FILTER (WHERE close_date >= %(t)s), 0) AS amount,
               coalesce(sum(weighted_amount) FILTER (WHERE close_date >= %(t)s), 0) AS weighted,
               count(*) FILTER (WHERE close_date < %(t)s) AS past_due_deals,
               coalesce(sum(amount) FILTER (WHERE close_date < %(t)s), 0) AS past_due_amount
        FROM rpt.deals WHERE is_open {_scope(scope)} GROUP BY 1 ORDER BY 3 DESC""", {"t": t, "scope": scope})
    return [{k: (float(v) if k != "key" else v) for k, v in r.items()} for r in rows]


DEAL_FILTERS = {  # filter name -> SQL, each bound to a parameter of the same name
    "branch": "branch = %(branch)s", "region": "region = %(region)s", "deal_type": "deal_type = %(deal_type)s",
    "segment": "segment = %(segment)s", "stage": "stage = %(stage)s", "lead_source": "lead_source = %(lead_source)s",
    "close_from": "close_date >= %(close_from)s", "close_to": "close_date <= %(close_to)s",
    "created_from": "created_date >= %(created_from)s", "created_to": "created_date <= %(created_to)s",
    "min_amount": "amount >= %(min_amount)s", "max_amount": "amount <= %(max_amount)s",
    "account_contains": "account_name ILIKE '%%' || %(account_contains)s || '%%'",
    "owner_contains": "owner_name ILIKE '%%' || %(owner_contains)s || '%%'",
}
DEAL_STATUS = {"open": "is_open", "won": "is_won", "lost": "is_lost", "closed": "is_closed", "all": "true"}
DEAL_SORT = {"amount": "amount DESC NULLS LAST", "close_date": "close_date ASC NULLS LAST", "newest": "created_at DESC"}


def find_deals(filters: dict, scope=None, limit=25, sort="amount") -> dict:
    status = filters.get("status") or "open"
    if status not in DEAL_STATUS:
        raise ValueError(f"status must be one of {sorted(DEAL_STATUS)}")
    where, p = [DEAL_STATUS[status]], {"scope": scope}
    for key, sql in DEAL_FILTERS.items():
        if filters.get(key) not in (None, ""):
            where.append(sql)
            p[key] = filters[key]
    if scope:
        where.append("branch_code = ANY(%(scope)s)")
    w = " AND ".join(where)
    totals = db.one(f"""SELECT count(*) AS n, coalesce(sum(amount), 0) AS amount, coalesce(sum(weighted_amount), 0) AS weighted
                        FROM rpt.deals WHERE {w}""", p)
    rows = db.query(f"""SELECT id, name, account_name, branch, deal_type, segment, stage, amount, probability, margin_pct,
                               close_date, created_date, owner_name, loss_reason
                        FROM rpt.deals WHERE {w} ORDER BY {DEAL_SORT.get(sort, DEAL_SORT['amount'])}
                        LIMIT {max(1, min(int(limit), 50))}""", p)
    return {"total_deals": totals["n"], "total_amount": float(totals["amount"]),
            "total_weighted": float(totals["weighted"]), "deals": rows}


def overdue_customers(scope=None, limit=15) -> list[dict]:
    return db.query(f"""SELECT customer_id, customer_name, sum(balance) AS unpaid,
                               coalesce(sum(balance) FILTER (WHERE days_past_due > 60), 0) AS over_60,
                               max(days_past_due) AS oldest_days, count(*) AS invoices
                        FROM rpt.invoices WHERE is_open {_scope(scope)}
                        GROUP BY 1, 2 HAVING sum(balance) FILTER (WHERE days_past_due > 0) > 0
                        ORDER BY over_60 DESC, unpaid DESC LIMIT {int(limit)}""", {"scope": scope})


# ---------- operations: field service, inventory, purchasing, people ----------

HOW.update({
    "jobs_completed": "Field-service jobs marked Completed, by the day they were completed. Canceled jobs don't count.",
    "emergency_on_time": "Emergency calls reached within 4 hours of the call coming in ÷ emergency calls reached, by arrival date.",
    "first_time_fix": "100% minus return visits as a share of repairs: return visits completed in the period ÷ repairs "
                      "completed in the period (not counting the return visits themselves). Counting both in the same period "
                      "means recent weeks don't look better just because their return visits haven't happened yet.",
    "response": "Average hours from the call coming in to the technician arriving, emergency calls only.",
    "not_invoiced": "Completed billable jobs (repairs and installs) finished more than 14 days ago with no invoice number "
                    "in the field-service app. Maintenance visits are covered by the contract and aren't billed per visit.",
    "utilization": "Hours on completed jobs ÷ hours worked (regular + overtime, from payroll), field technicians only, over the "
                   "last 4 complete weeks. Travel and shop time make up the rest.",
    "inventory_value": "On hand × standard cost, for every warehouse and van. Negative balances count as zero; parts with no "
                       "standard cost are left out (see Data checks).",
    "turns": "Cost of what was used on jobs or shipped on orders in the last 12 months ÷ today's inventory value. Higher means "
             "stock moves faster.",
    "below_reorder": "Warehouse stock at or below its reorder point. Vans are restocked from the warehouse, so they're not listed.",
    "dead_stock": "Parts on hand that haven't been used on a job in 180 days, at standard cost.",
    "shrinkage": "Cycle-count and damage corrections in the last 90 days, at standard cost. Negative means stock went missing.",
    "spend": "Purchase orders placed in the last 12 months, by order date. Canceled orders don't count.",
    "on_time_delivery": "Orders received on or before their expected date ÷ orders received, last 90 days by received date. "
                        "Orders with no expected date are left out.",
    "received_not_billed": "Orders received more than 30 days ago with no vendor bill yet: money owed that isn't in the books.",
    "price_change": "For each part, the quantity-weighted average price paid in the last 90 days against the same 90 days a "
                    "year earlier. Only parts bought in both periods.",
    "headcount": "People on payroll today: hired on or before today and not yet past their last day.",
    "turnover": "People who left in the last 12 months ÷ average headcount (the average of the 12 month-end counts).",
    "overtime": "Overtime hours ÷ hours worked (regular + overtime), hourly staff, last 4 complete weeks.",
    "open_roles": "Job openings not yet filled, with days since each was opened.",
    "certs": "Certifications and licenses held by people on payroll: expired, or running out within 30 days.",
    "frontline": "People on payroll today in the frontline department set for this company (technicians, drivers, crews).",
})


def _weeks_back(t: dt.date, weeks: int):
    """The last `weeks` complete Monday-to-Sunday weeks before this one: (first Monday, last Sunday)."""
    this_monday = t - dt.timedelta(days=t.weekday())
    return this_monday - dt.timedelta(weeks=weeks), this_monday - dt.timedelta(days=1)


def jobs_summary(start, end, scope=None) -> dict:
    p = {"s": start, "e": end, "scope": scope}
    r = db.one(f"""
        SELECT count(*) FILTER (WHERE status = 'Completed' AND completed_date BETWEEN %(s)s AND %(e)s) AS completed,
               count(*) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s) AS em_reached,
               count(*) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s AND on_time) AS em_on_time,
               avg(response_hours) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s) AS em_response,
               count(*) FILTER (WHERE fixed_first_time IS NOT NULL AND completed_date BETWEEN %(s)s AND %(e)s) AS repairs,
               count(*) FILTER (WHERE is_callback AND status = 'Completed' AND completed_date BETWEEN %(s)s AND %(e)s) AS return_visits
        FROM rpt.jobs WHERE true {_scope(scope)}""", p)
    r = {k: float(v) if v is not None else None for k, v in r.items()}
    r["emergency_on_time"] = _ratio(r["em_on_time"], r["em_reached"])
    r["first_time_fix"] = 1 - r["return_visits"] / r["repairs"] if r["repairs"] else None
    return r


def jobs_by_week(t: dt.date, weeks=12, scope=None) -> list[dict]:
    """Complete weeks only, so the chart doesn't end on a half-finished week."""
    first, last = _weeks_back(t, weeks)
    rows = db.query(f"""
        SELECT w::date AS week,
               (SELECT count(*) FROM rpt.jobs j WHERE j.status = 'Completed' AND j.completed_date BETWEEN w::date AND w::date + 6
                  {_scope(scope, 'j.branch_code')}) AS completed,
               (SELECT count(*) FROM rpt.jobs j WHERE j.is_callback AND j.completed_date BETWEEN w::date AND w::date + 6
                  {_scope(scope, 'j.branch_code')}) AS return_visits
        FROM generate_series(%(f)s::date, %(l)s::date - 6, interval '7 days') AS w ORDER BY 1""", {"f": first, "l": last, "scope": scope})
    return [{"week": r["week"], "completed": r["completed"], "return_visits": r["return_visits"]} for r in rows]


def jobs_by_branch(start, end, scope=None) -> list[dict]:
    rows = db.query(f"""
        SELECT branch, count(*) FILTER (WHERE status = 'Completed' AND completed_date BETWEEN %(s)s AND %(e)s) AS completed,
               count(*) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s) AS em_reached,
               count(*) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s AND on_time) AS em_on_time,
               avg(response_hours) FILTER (WHERE priority = 'Emergency' AND arrived_date BETWEEN %(s)s AND %(e)s) AS em_response,
               count(*) FILTER (WHERE fixed_first_time IS NOT NULL AND completed_date BETWEEN %(s)s AND %(e)s) AS repairs,
               count(*) FILTER (WHERE is_callback AND status = 'Completed' AND completed_date BETWEEN %(s)s AND %(e)s) AS return_visits
        FROM rpt.jobs WHERE true {_scope(scope)} GROUP BY 1 ORDER BY 1""", {"s": start, "e": end, "scope": scope})
    for r in rows:
        r["emergency_on_time"] = _ratio(r["em_on_time"], r["em_reached"])
        r["first_time_fix"] = 1 - r["return_visits"] / r["repairs"] if r["repairs"] else None
    return rows


def jobs_not_invoiced(t: dt.date, scope=None) -> list[dict]:
    return db.query(f"""SELECT id, number, account_name, branch, job_type, completed_date, billable_amount, technician_name
                        FROM rpt.jobs WHERE status = 'Completed' AND billable AND invoice_number IS NULL
                          AND completed_date <= %(t)s - 14 {_scope(scope)}
                        ORDER BY billable_amount DESC NULLS LAST""", {"t": t, "scope": scope})


def utilization(t: dt.date, weeks=4, scope=None) -> list[dict]:
    """Per technician: hours on completed jobs ÷ hours worked, over the last `weeks` complete weeks."""
    first, last = _weeks_back(t, weeks)
    return db.query(f"""
        WITH worked AS (SELECT employee_id, sum(worked_hours) AS worked FROM rpt.timesheets
                        WHERE is_frontline AND week_start BETWEEN %(f)s AND %(l)s GROUP BY 1),
             onjob AS (SELECT technician_id, sum(labor_hours) AS on_jobs FROM rpt.jobs
                       WHERE status = 'Completed' AND completed_date BETWEEN %(f)s AND %(l)s GROUP BY 1)
        SELECT e.id, e.name, e.title, e.branch, e.branch_code, coalesce(o.on_jobs, 0) AS on_jobs, w.worked,
               coalesce(o.on_jobs, 0) / nullif(w.worked, 0) AS utilization
        FROM worked w JOIN rpt.employees e ON e.id = w.employee_id LEFT JOIN onjob o ON o.technician_id = w.employee_id
        WHERE true {_scope(scope, 'e.branch_code')} ORDER BY utilization DESC NULLS LAST""", {"f": first, "l": last, "scope": scope})


def inventory_summary(t: dt.date, scope=None) -> dict:
    p = {"t": t, "scope": scope}
    s = db.one(f"""SELECT coalesce(sum(value), 0) AS value, coalesce(sum(value) FILTER (WHERE is_dead), 0) AS dead_value,
                          count(*) FILTER (WHERE is_dead) AS dead_rows,
                          count(*) FILTER (WHERE below_reorder) AS below_reorder,
                          count(*) FILTER (WHERE critical AND location_kind = 'Warehouse' AND on_hand <= 0 AND reorder_point > 0) AS critical_out,
                          coalesce(sum(value) FILTER (WHERE location_kind = 'Van stock'), 0) AS van_value
                   FROM rpt.stock WHERE true {_scope(scope)}""", p)
    used = db.one(f"""SELECT coalesce(sum(cost), 0) AS c FROM rpt.part_usage WHERE used_date BETWEEN %(t)s - 364 AND %(t)s
                      {_scope(scope)}""", p)["c"]
    used += db.one(f"""SELECT coalesce(sum(cost), 0) AS c FROM rpt.order_lines WHERE status <> 'Canceled'
                       AND order_date BETWEEN %(t)s - 364 AND %(t)s {_scope(scope)}""", p)["c"]
    shrink = db.one(f"""SELECT coalesce(sum(a.qty * i.standard_cost), 0) AS v FROM inv.adjustments a
                        JOIN inv.items i ON i.id = a.sku JOIN inv.locations l ON l.id = a.location_id
                        WHERE a.adj_date BETWEEN %(t)s - 89 AND %(t)s {_scope(scope, 'l.branch_code')}""", p)["v"]
    out = {k: float(v) for k, v in s.items()}
    out["used_12m"] = float(used)
    out["turns"] = _ratio(used, out["value"])
    out["shrinkage_90d"] = float(shrink)
    return out


def stock_value_by(dim: str, scope=None) -> list[dict]:
    if dim not in ("branch", "category", "location_kind"):
        raise ValueError("unsupported dimension")
    return db.query(f"""SELECT {dim} AS key, sum(value) AS value, sum(value) FILTER (WHERE is_dead) AS dead
                        FROM rpt.stock WHERE true {_scope(scope)} GROUP BY 1 ORDER BY 2 DESC NULLS LAST""", {"scope": scope})


def reorder_list(scope=None) -> list[dict]:
    """Warehouse stock at or below its reorder point, critical parts first, with any open order for it."""
    return db.query(f"""
        SELECT s.location_id, s.branch, s.branch_code, s.sku, s.description, s.category, s.critical, s.on_hand, s.reorder_point,
               s.reorder_qty, s.vendor, s.standard_cost * s.reorder_qty AS order_value,
               (SELECT string_agg(DISTINCT l.po_number, ', ') FROM rpt.po_lines l
                 WHERE l.sku = s.sku AND l.branch_code = s.branch_code AND l.status = 'Open') AS on_order
        FROM rpt.stock s WHERE s.below_reorder {_scope(scope, 's.branch_code')}
        ORDER BY s.critical DESC, s.on_hand <= 0 DESC, s.on_hand - s.reorder_point, s.branch""", {"scope": scope})


def dead_stock(scope=None) -> list[dict]:
    return db.query(f"""SELECT location, branch, sku, description, on_hand, value, last_issued_date FROM rpt.stock
                        WHERE is_dead {_scope(scope)} ORDER BY value DESC NULLS LAST""", {"scope": scope})


def purchasing_summary(t: dt.date, scope=None) -> dict:
    r = db.one(f"""
        SELECT coalesce(sum(amount) FILTER (WHERE status <> 'Canceled' AND ordered_date BETWEEN %(t)s - 364 AND %(t)s), 0) AS spend,
               coalesce(sum(amount) FILTER (WHERE is_open), 0) AS open_amount, count(*) FILTER (WHERE is_open) AS open_count,
               count(*) FILTER (WHERE is_open AND days_late > 0) AS late_open,
               count(*) FILTER (WHERE on_time IS NOT NULL AND received_date BETWEEN %(t)s - 89 AND %(t)s) AS received,
               count(*) FILTER (WHERE on_time AND received_date BETWEEN %(t)s - 89 AND %(t)s) AS received_on_time,
               coalesce(sum(amount) FILTER (WHERE status = 'Received' AND received_date <= %(t)s - 30), 0) AS not_billed,
               count(*) FILTER (WHERE status = 'Received' AND received_date <= %(t)s - 30) AS not_billed_count
        FROM rpt.purchase_orders WHERE true {_scope(scope)}""", {"t": t, "scope": scope})
    r = {k: float(v) for k, v in r.items()}
    r["on_time_delivery"] = _ratio(r["received_on_time"], r["received"])
    return r


def vendor_scorecard(t: dt.date, scope=None) -> list[dict]:
    rows = db.query(f"""
        SELECT vendor_id, vendor, vendor_category,
               coalesce(sum(amount) FILTER (WHERE status <> 'Canceled' AND ordered_date BETWEEN %(t)s - 364 AND %(t)s), 0) AS spend,
               count(*) FILTER (WHERE status <> 'Canceled' AND ordered_date BETWEEN %(t)s - 364 AND %(t)s) AS orders,
               count(*) FILTER (WHERE on_time IS NOT NULL AND received_date BETWEEN %(t)s - 89 AND %(t)s) AS received,
               count(*) FILTER (WHERE on_time AND received_date BETWEEN %(t)s - 89 AND %(t)s) AS on_time,
               avg(days_late) FILTER (WHERE NOT on_time AND received_date BETWEEN %(t)s - 89 AND %(t)s) AS avg_days_late
        FROM rpt.purchase_orders WHERE true {_scope(scope)} GROUP BY 1, 2, 3 ORDER BY 4 DESC""", {"t": t, "scope": scope})
    for r in rows:
        r["on_time_delivery"] = _ratio(r["on_time"], r["received"])
    return rows


def price_changes(t: dt.date, scope=None, limit=12) -> list[dict]:
    return db.query(f"""
        WITH now_ AS (SELECT sku, max(description) AS description, max(vendor) AS vendor, sum(amount) / sum(qty) AS price
                      FROM rpt.po_lines WHERE sku IS NOT NULL AND status <> 'Canceled'
                        AND ordered_date BETWEEN %(t)s - 89 AND %(t)s {_scope(scope)} GROUP BY 1),
             then_ AS (SELECT sku, sum(amount) / sum(qty) AS price FROM rpt.po_lines
                       WHERE sku IS NOT NULL AND status <> 'Canceled'
                         AND ordered_date BETWEEN %(t)s - 454 AND %(t)s - 365 {_scope(scope)} GROUP BY 1)
        SELECT n.sku, n.description, n.vendor, th.price AS price_then, n.price AS price_now,
               n.price / th.price - 1 AS change
        FROM now_ n JOIN then_ th ON th.sku = n.sku ORDER BY change DESC LIMIT {int(limit)}""", {"t": t, "scope": scope})


def people_summary(t: dt.date, scope=None) -> dict:
    p = {"t": t, "scope": scope}
    h = db.one(f"""SELECT count(*) FILTER (WHERE hire_date <= %(t)s AND (termination_date IS NULL OR termination_date >= %(t)s)) AS headcount,
                          count(*) FILTER (WHERE is_frontline AND hire_date <= %(t)s AND (termination_date IS NULL OR termination_date >= %(t)s)) AS frontline,
                          count(*) FILTER (WHERE termination_date BETWEEN %(t)s - 364 AND %(t)s) AS exits_12m,
                          count(*) FILTER (WHERE termination_date BETWEEN %(t)s - 364 AND %(t)s AND termination_type = 'Voluntary') AS quits_12m,
                          count(*) FILTER (WHERE hire_date BETWEEN %(t)s - 364 AND %(t)s) AS hires_12m
                   FROM rpt.employees WHERE true {_scope(scope)}""", p)
    months = headcount_by_month(t, 12, scope)
    avg_hc = sum(m["headcount"] for m in months) / len(months) if months else None
    reqs = db.one(f"""SELECT count(*) AS n, avg(%(t)s - opened_date) AS avg_days FROM hr.requisitions
                      WHERE status = 'Open' {_scope(scope)}""", p)
    first, last = _weeks_back(t, 4)
    ot = db.one(f"""SELECT sum(overtime_hours) AS ot, sum(worked_hours) AS worked FROM rpt.timesheets
                    WHERE week_start BETWEEN %(f)s AND %(l)s {_scope(scope)}""", dict(p, f=first, l=last))
    certs = db.one(f"""SELECT count(*) FILTER (WHERE status = 'Expired') AS expired, count(*) FILTER (WHERE status = 'Expiring') AS expiring
                       FROM rpt.certifications WHERE is_active {_scope(scope)}""", p)
    out = {k: float(v) for k, v in h.items()}
    out.update({"turnover": _ratio(h["exits_12m"], avg_hc), "open_roles": reqs["n"],
                "avg_days_open": float(reqs["avg_days"]) if reqs["avg_days"] is not None else None,
                "overtime_pct": _ratio(ot["ot"] or 0, ot["worked"]), "certs_expired": certs["expired"],
                "certs_expiring": certs["expiring"]})
    return out


def headcount_by_month(t: dt.date, months=12, scope=None) -> list[dict]:
    """Headcount at each month-end (the last one is today), with hires and exits in that month."""
    ends = []
    m = t.replace(day=1)
    for _ in range(months):
        ends.append(m - dt.timedelta(days=1))
        m = (m - dt.timedelta(days=1)).replace(day=1)
    ends = sorted(ends)[1:] + [t]
    rows = db.query(f"""
        SELECT e AS month_end,
               (SELECT count(*) FROM rpt.employees x WHERE x.hire_date <= e AND (x.termination_date IS NULL OR x.termination_date >= e)
                  {_scope(scope, 'x.branch_code')}) AS headcount,
               (SELECT count(*) FROM rpt.employees x WHERE x.hire_date BETWEEN date_trunc('month', e)::date AND e
                  {_scope(scope, 'x.branch_code')}) AS hires,
               (SELECT count(*) FROM rpt.employees x WHERE x.termination_date BETWEEN date_trunc('month', e)::date AND e
                  {_scope(scope, 'x.branch_code')}) AS exits
        FROM unnest(%(ends)s::date[]) AS e ORDER BY 1""", {"ends": ends, "scope": scope})
    return rows


def overtime_by_branch(t: dt.date, weeks=4, scope=None) -> list[dict]:
    first, last = _weeks_back(t, weeks)
    rows = db.query(f"""SELECT branch, sum(overtime_hours) AS ot, sum(worked_hours) AS worked FROM rpt.timesheets
                        WHERE week_start BETWEEN %(f)s AND %(l)s {_scope(scope)} GROUP BY 1 ORDER BY 1""",
                    {"f": first, "l": last, "scope": scope})
    for r in rows:
        r["overtime_pct"] = _ratio(r["ot"] or 0, r["worked"])
    return rows


def headcount_by_branch(t: dt.date, scope=None) -> list[dict]:
    return db.query(f"""SELECT branch, count(*) AS headcount, count(*) FILTER (WHERE is_frontline) AS frontline
                        FROM rpt.employees WHERE hire_date <= %(t)s AND (termination_date IS NULL OR termination_date >= %(t)s)
                        {_scope(scope)} GROUP BY 1 ORDER BY 2 DESC""", {"t": t, "scope": scope})


def cert_problems(scope=None) -> list[dict]:
    return db.query(f"""SELECT id, employee_id, employee_name, title, branch, certification, expires_date, days_left, status
                        FROM rpt.certifications WHERE is_active AND status IN ('Expired', 'Expiring') {_scope(scope)}
                        ORDER BY expires_date""", {"scope": scope})


def open_roles(t: dt.date, scope=None) -> list[dict]:
    return db.query(f"""SELECT r.id, r.title, r.department, coalesce(b.name, r.branch_code) AS branch, r.opened_date,
                               %(t)s - r.opened_date AS days_open, r.reason, r.applicants
                        FROM hr.requisitions r LEFT JOIN core.branches b ON b.code = r.branch_code
                        WHERE r.status = 'Open' {_scope(scope, 'r.branch_code')} ORDER BY r.opened_date""", {"t": t, "scope": scope})


# ---------- orders and shipping (distribution) ----------

HOW.update({
    "sales_shipped": "Value of what shipped in the period, at the order price (by order date). Backorders count when they ship.",
    "fill_rate": "Order lines whose first shipment carried the whole quantity ordered ÷ order lines, for orders placed in the period. "
                 "The share of lines a customer got complete, first time.",
    "on_time_ship": "Orders whose first shipment left on or before the date the customer asked for ÷ orders shipped, by order date.",
    "gross_margin": "(Sales − cost of what shipped) ÷ sales, for orders placed in the period. Cost is the item cost on the order.",
    "backorders": "What's still owed on orders that have already shipped once, at the order price, as of today. New orders "
                  "that haven't shipped yet aren't backorders.",
    "below_cost": "Order lines priced below their cost: a pricing error or a deal nobody approved.",
})


def orders_summary(start, end, scope=None) -> dict:
    p = {"s": start, "e": end, "scope": scope}
    r = db.one(f"""SELECT count(DISTINCT order_id) AS orders, coalesce(sum(sales), 0) AS sales, coalesce(sum(cost), 0) AS cost,
                          count(*) AS lines, count(*) FILTER (WHERE filled_first_time) AS lines_filled
                   FROM rpt.order_lines WHERE status <> 'Canceled' AND order_date BETWEEN %(s)s AND %(e)s {_scope(scope)}""", p)
    o = db.one(f"""SELECT count(*) FILTER (WHERE on_time IS NOT NULL) AS shipped, count(*) FILTER (WHERE on_time) AS on_time
                   FROM rpt.orders WHERE status <> 'Canceled' AND order_date BETWEEN %(s)s AND %(e)s {_scope(scope)}""", p)
    b = db.one(f"""SELECT coalesce(sum(backorder_value), 0) AS v, count(*) FILTER (WHERE backorder_value > 0) AS n
                   FROM rpt.orders WHERE status <> 'Canceled' AND backorder_value > 0 {_scope(scope)}""", p)
    out = {k: float(v) for k, v in r.items()}
    out.update({"fill_rate": _ratio(r["lines_filled"], r["lines"]), "on_time_ship": _ratio(o["on_time"], o["shipped"]),
                "gross_margin": _ratio(r["sales"] - r["cost"], r["sales"]), "backorder_value": float(b["v"]),
                "backorder_orders": b["n"], "orders_shipped": o["shipped"]})
    return out


def orders_by(dim: str, start, end, scope=None) -> list[dict]:
    """Sales, margin and fill rate split by branch, product line, rep, segment or customer."""
    cols = {"branch": "branch", "product_line": "product_line", "rep": "rep_name", "segment": "segment", "customer": "account_name"}
    if dim not in cols:
        raise ValueError("unsupported dimension")
    rows = db.query(f"""SELECT coalesce({cols[dim]}, '(none)') AS key, coalesce(sum(sales), 0) AS sales, coalesce(sum(cost), 0) AS cost,
                               count(*) AS lines, count(*) FILTER (WHERE filled_first_time) AS lines_filled,
                               count(DISTINCT order_id) AS orders
                        FROM rpt.order_lines WHERE status <> 'Canceled' AND order_date BETWEEN %(s)s AND %(e)s {_scope(scope)}
                        GROUP BY 1 ORDER BY 2 DESC""", {"s": start, "e": end, "scope": scope})
    for r in rows:
        r["gross_margin"] = _ratio(r["sales"] - r["cost"], r["sales"])
        r["fill_rate"] = _ratio(r["lines_filled"], r["lines"])
    return rows


def orders_on_time_by_branch(start, end, scope=None) -> list[dict]:
    rows = db.query(f"""SELECT branch, count(*) FILTER (WHERE on_time IS NOT NULL) AS shipped, count(*) FILTER (WHERE on_time) AS on_time
                        FROM rpt.orders WHERE status <> 'Canceled' AND order_date BETWEEN %(s)s AND %(e)s {_scope(scope)}
                        GROUP BY 1 ORDER BY 1""", {"s": start, "e": end, "scope": scope})
    for r in rows:
        r["on_time_ship"] = _ratio(r["on_time"], r["shipped"])
    return rows


def margin_by_month(t: dt.date, months=12, dim="product_line", scope=None) -> dict:
    """Gross margin % by month for each value of `dim` (for spotting a squeeze), oldest first."""
    first = (t.replace(day=1) - dt.timedelta(days=31 * (months - 1))).replace(day=1)
    rows = db.query(f"""SELECT date_trunc('month', order_date)::date AS m, product_line AS key, sum(sales) AS sales, sum(cost) AS cost
                        FROM rpt.order_lines WHERE status <> 'Canceled' AND order_date BETWEEN %(f)s AND %(t)s {_scope(scope)}
                        GROUP BY 1, 2 ORDER BY 1""", {"f": first, "t": t, "scope": scope})
    out = {}
    for r in rows:
        out.setdefault(r["key"], {})[r["m"]] = _ratio(r["sales"] - r["cost"], r["sales"])
    return out


def orders_by_week(t: dt.date, weeks=12, scope=None) -> list[dict]:
    first, last = _weeks_back(t, weeks)
    return db.query(f"""SELECT date_trunc('week', order_date)::date AS week, count(DISTINCT order_id) AS orders,
                               coalesce(sum(sales), 0) AS sales, coalesce(sum(cost), 0) AS cost
                        FROM rpt.order_lines WHERE status <> 'Canceled' AND order_date BETWEEN %(f)s AND %(l)s {_scope(scope)}
                        GROUP BY 1 ORDER BY 1""", {"f": first, "l": last, "scope": scope})


def backorders(scope=None, limit=25) -> list[dict]:
    return db.query(f"""SELECT order_id, order_number, account_name, branch, sku, description, product_line,
                               qty_ordered - qty_shipped AS qty_open, backorder_value, order_date
                        FROM rpt.order_lines WHERE backorder_value > 0 {_scope(scope)}
                        ORDER BY backorder_value DESC LIMIT {int(limit)}""", {"scope": scope})


# ---------- projects and time (professional services) ----------

HOW.update({
    "billable_util": "Billable hours ÷ all hours recorded (billable and internal, not time off), for people who record time "
                     "to projects, by week ending.",
    "realization": "For projects completed in the last 12 months: amount billed ÷ standard value of the hours spent (hours × "
                   "standard rates). Below 100% means hours were written down, or a fixed fee was outrun.",
    "unbilled_wip": "Billable hours on hourly projects not yet on an invoice, at standard rates, as of today.",
    "backlog": "For projects not finished yet: contract value minus what's been billed so far.",
    "budget_used": "Hours to date ÷ budget hours, against the project manager's percent complete. Flagged when the budget "
                   "used is more than 20 points ahead of the progress: it's heading over.",
    "project_margin": "For projects completed in the last 12 months: (billed − cost of the hours) ÷ billed.",
})


def time_summary(start, end, scope=None) -> dict:
    r = db.one(f"""SELECT coalesce(sum(hours) FILTER (WHERE billable), 0) AS billable, coalesce(sum(hours), 0) AS recorded,
                          coalesce(sum(standard_value) FILTER (WHERE billable), 0) AS standard_value
                   FROM rpt.time_entries WHERE week_ending BETWEEN %(s)s AND %(e)s {_scope(scope)}""",
               {"s": start, "e": end, "scope": scope})
    out = {k: float(v) for k, v in r.items()}
    out["billable_util"] = _ratio(out["billable"], out["recorded"])
    return out


def utilization_by(dim: str, start, end, scope=None) -> list[dict]:
    cols = {"branch": "branch", "title": "title", "person": "employee_name"}
    if dim not in cols:
        raise ValueError("unsupported dimension")
    rows = db.query(f"""SELECT {cols[dim]} AS key, max(branch) AS branch, coalesce(sum(hours) FILTER (WHERE billable), 0) AS billable,
                               coalesce(sum(hours), 0) AS recorded
                        FROM rpt.time_entries WHERE week_ending BETWEEN %(s)s AND %(e)s {_scope(scope)} GROUP BY 1 ORDER BY 1""",
                    {"s": start, "e": end, "scope": scope})
    for r in rows:
        r["billable_util"] = _ratio(r["billable"], r["recorded"])
    return rows


def utilization_by_week(t: dt.date, weeks=26, scope=None) -> list[dict]:
    first, last = _weeks_back(t, weeks)
    return db.query(f"""SELECT branch, date_trunc('week', week_ending)::date AS week,
                               sum(hours) FILTER (WHERE billable) / nullif(sum(hours), 0) AS util
                        FROM rpt.time_entries WHERE week_ending BETWEEN %(f)s AND %(l)s {_scope(scope)}
                        GROUP BY 1, 2 ORDER BY 2""", {"f": first, "l": last, "scope": scope})


def projects_summary(t: dt.date, scope=None) -> dict:
    p = {"t": t, "scope": scope}
    done = db.one(f"""SELECT coalesce(sum(billed), 0) AS billed, coalesce(sum(standard_value), 0) AS std, coalesce(sum(cost), 0) AS cost,
                             count(*) AS n
                      FROM rpt.projects WHERE status = 'Completed' AND end_date BETWEEN %(t)s - 364 AND %(t)s {_scope(scope)}""", p)
    live = db.one(f"""SELECT count(*) FILTER (WHERE status = 'Active') AS active,
                             coalesce(sum(greatest(contract_value - billed, 0)) FILTER (WHERE status IN ('Active', 'Not started')), 0) AS backlog,
                             count(*) FILTER (WHERE status = 'Active' AND billing_type = 'Fixed fee'
                                              AND budget_used * 100 > percent_complete + 20) AS at_risk
                      FROM rpt.projects WHERE true {_scope(scope)}""", p)
    wip = db.one(f"""SELECT coalesce(sum(standard_value), 0) AS v,
                            coalesce(sum(standard_value) FILTER (WHERE week_ending < %(t)s - 60), 0) AS old
                     FROM rpt.time_entries WHERE billable AND invoice_number IS NULL AND billing_type = 'Time & materials'
                       AND week_ending < date_trunc('month', %(t)s::date) {_scope(scope)}""", p)
    return {"realization": _ratio(done["billed"], done["std"]), "project_margin": _ratio(float(done["billed"]) - float(done["cost"]), done["billed"]),
            "completed": done["n"], "active": live["active"], "backlog": float(live["backlog"]), "at_risk": live["at_risk"],
            "unbilled_wip": float(wip["v"]), "unbilled_over_60": float(wip["old"])}


def projects_by(dim: str, t: dt.date, scope=None) -> list[dict]:
    """Realization and margin on projects completed in the last 12 months, by project manager, segment or office."""
    cols = {"pm": "pm_name", "segment": "segment", "branch": "branch", "billing_type": "billing_type"}
    rows = db.query(f"""SELECT coalesce({cols[dim]}, '(none)') AS key, count(*) AS projects, sum(billed) AS billed,
                               sum(standard_value) AS std, sum(cost) AS cost
                        FROM rpt.projects WHERE status = 'Completed' AND end_date BETWEEN %(t)s - 364 AND %(t)s {_scope(scope)}
                        GROUP BY 1 ORDER BY 3 DESC""", {"t": t, "scope": scope})
    for r in rows:
        r["realization"] = _ratio(r["billed"], r["std"])
        r["project_margin"] = _ratio(float(r["billed"] or 0) - float(r["cost"] or 0), r["billed"])
    return rows


def projects_at_risk(scope=None) -> list[dict]:
    return db.query(f"""SELECT id, number, name, branch, pm_name, contract_value, budget_hours, hours, budget_used, percent_complete
                        FROM rpt.projects WHERE status = 'Active' AND billing_type = 'Fixed fee'
                          AND budget_used * 100 > percent_complete + 20 {_scope(scope)}
                        ORDER BY budget_used * 100 - percent_complete DESC""", {"scope": scope})


def unbilled_projects(t: dt.date, scope=None) -> list[dict]:
    return db.query(f"""SELECT id, number, name, account_name, branch, pm_name, unbilled_value, oldest_unbilled,
                               %(t)s - oldest_unbilled AS days
                        FROM rpt.projects WHERE billing_type = 'Time & materials' AND unbilled_value > 0
                          AND oldest_unbilled < date_trunc('month', %(t)s::date) {_scope(scope)}
                        ORDER BY oldest_unbilled, unbilled_value DESC""", {"t": t, "scope": scope})
