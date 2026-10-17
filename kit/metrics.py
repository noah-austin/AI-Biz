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

SCORECARD = [  # key, label, format, higher_is_better, how
    ("new_deals", "New deals created", "count", True, "new_pipeline"),
    ("new_pipeline", "New pipeline created", "money", True, "new_pipeline"),
    ("bookings", "Bookings (won)", "money", True, "bookings"),
    ("win_rate_dollars", "Win rate by $, trailing 90 days", "pct", True, "win_rate"),
    ("billed", "Billed", "money", True, "billed"),
    ("collected", "Cash collected", "money", True, "collected"),
    ("ar_over_60", "AR over 60 days past due", "money", False, "ar_over_60"),
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
    billed = by_week(f"""SELECT {wk.format(col='invoice_date')} AS w, sum(amount) AS v FROM rpt.invoices
                         WHERE invoice_date BETWEEN %(first)s AND %(t)s {_scope(scope)} GROUP BY 1""")
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
    ar60 = by_week(f"""
        -- Accounting gives one paid date per invoice, so this treats payments as paid in full.
        SELECT w.s AS w, sum(i.amount) AS v
        FROM unnest(%(starts)s::date[], %(ends)s::date[]) AS w(s, e)
        JOIN rpt.invoices i ON i.invoice_date <= w.e AND i.due_date < w.e - 60
             AND (i.paid_date IS NULL OR i.paid_date > w.e) {_scope(scope, 'i.branch_code')}
        GROUP BY 1""", p2)
    series = {
        "new_deals": new_deals, "new_pipeline": new_pipe, "bookings": bookings, "billed": billed,
        "collected": collected, "ar_over_60": ar60,
        "win_rate_dollars": {w: (100 * a / b if b else None) for w, (a, b) in win.items()},
    }
    goals = {r["metric"]: float(r["value"]) for r in
             db.query("SELECT metric, value FROM core.goals WHERE period = 'weekly'")}
    rows = []
    for key, label, fmt, higher_better, how in SCORECARD:
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
    stage = db.query(f"""SELECT h.deal_id AS id, h.deal_name AS name, h.branch, d.amount, h.new_value AS stage, h.changed_date
                         FROM rpt.deal_history h JOIN rpt.deals d ON d.id = h.deal_id
                         WHERE h.field = 'StageName' AND h.new_value IN ('Closed Won', 'Closed Lost')
                           AND h.changed_date BETWEEN %(since)s AND %(t)s {_scope(scope, 'h.branch_code')}
                         ORDER BY d.amount DESC NULLS LAST""", p)
    slipped = db.query(f"""
        SELECT DISTINCT ON (h.deal_id) h.deal_id AS id, h.deal_name AS name, h.branch, d.amount,
               h.old_value::date AS old_close, h.new_value::date AS new_close
        FROM rpt.deal_history h JOIN rpt.deals d ON d.id = h.deal_id
        WHERE h.field = 'CloseDate' AND d.is_open AND h.changed_date BETWEEN %(since)s AND %(t)s
          AND h.new_value::date >= h.old_value::date + 30
          {_scope(scope, 'h.branch_code')}
        ORDER BY h.deal_id, h.changed_at DESC""", p)
    slipped.sort(key=lambda r: -(float(r["amount"] or 0)))
    won = [r for r in stage if r["stage"] == "Closed Won"]
    lost = [r for r in stage if r["stage"] == "Closed Lost"]
    total = lambda rows: sum(float(r["amount"] or 0) for r in rows)
    return {"since": since, "created": created, "won": won, "lost": lost, "slipped": slipped,
            "totals": {"created": total(created), "won": total(won), "lost": total(lost), "slipped": total(slipped)}}


def freshness() -> dict:
    r = db.one("""SELECT min(last_success_at) AS oldest, max(last_attempt_at) AS latest,
                         count(*) FILTER (WHERE last_status = 'failed') AS failed
                  FROM core.sync_state WHERE object <> 'backup'""")
    return r or {}
