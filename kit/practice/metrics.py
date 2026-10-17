"""Every practice number, defined once (the company rulebook says the same in words)."""
import calendar
import datetime as dt

from .. import db
from ..config import get_settings
from ..metrics import today

STAGES = [  # key, label, probability used for the weighted pipeline
    ("lead", "Lead", 0.05), ("contacted", "Contacted", 0.10), ("conversation", "Conversation", 0.25),
    ("proposal", "Proposal sent", 0.50), ("won", "Won", 1.0), ("lost", "Lost", 0.0), ("not_now", "Not now", 0.0),
]
OPEN_STAGES = ["lead", "contacted", "conversation", "proposal"]
STAGE_LABEL = {k: label for k, label, _ in STAGES}
STAGE_PROB = {k: p for k, _, p in STAGES}
KINDS = {"prospect": "Prospect", "client": "Client", "partner": "Referral partner", "past_client": "Past client"}
OFFERS = {"health_report": "CRM Health Report", "assessment": "Assessment", "build": "Build",
          "retainer": "Run & Grow retainer", "other": "Other"}
ACTIVITY_KINDS = {"call": "Call", "meeting": "Meeting", "email": "Email", "linkedin": "LinkedIn", "event": "Event",
                  "note": "Note"}
CONVERSATION_KINDS = ("call", "meeting")

HOW = {
    "revenue": "Invoices issued in the period, by issue date (paid or not).",
    "cash": "Invoices paid in the period, by paid date.",
    "mrr": "Monthly fees of retainers that are active today.",
    "pipeline": "Open prospects' estimated first-year value. Weighted = value × stage probability "
                "(lead 5%, contacted 10%, conversation 25%, proposal 50%).",
    "conversations": "Calls and meetings logged this calendar month, with anyone.",
    "hours": "All hours logged this week (Monday to Sunday), billable or not.",
    "effective_rate": "Revenue this year ÷ all hours logged this year. Shows what an hour of your time is really earning.",
    "unpaid": "Invoices issued and not yet paid.",
    "profit": "Revenue minus expenses, by issue and spend date.",
}


def settings() -> dict:
    defaults = {"revenue_goal": 90000, "weekly_hours_target": 20, "monthly_conversations_target": 15,
                "invoice_terms_days": 15}
    return {**defaults, **get_settings().client.get("practice", {})}


def _f(v):
    return float(v or 0)


def overview(t: dt.date | None = None) -> dict:
    t = t or today()
    s = settings()
    ys = dt.date(t.year, 1, 1)
    ms = t.replace(day=1)
    ws = t - dt.timedelta(days=t.weekday())
    r = db.one("""
        SELECT (SELECT coalesce(sum(amount), 0) FROM practice.invoices WHERE issued_date BETWEEN %(ys)s AND %(t)s) AS revenue_ytd,
               (SELECT coalesce(sum(amount), 0) FROM practice.invoices WHERE paid_date BETWEEN %(ys)s AND %(t)s) AS cash_ytd,
               (SELECT coalesce(sum(amount), 0) FROM practice.invoices WHERE paid_date IS NULL) AS unpaid,
               (SELECT coalesce(sum(amount), 0) FROM practice.invoices WHERE paid_date IS NULL AND due_date < %(t)s) AS overdue,
               (SELECT coalesce(sum(amount), 0) FROM practice.expenses WHERE spent_date BETWEEN %(ys)s AND %(t)s) AS expenses_ytd,
               (SELECT coalesce(sum(monthly_fee), 0) FROM practice.engagements
                 WHERE offer = 'retainer' AND status = 'active'
                   AND (start_date IS NULL OR start_date <= %(t)s) AND (end_date IS NULL OR end_date >= %(t)s)) AS mrr,
               (SELECT count(*) FROM practice.activities WHERE kind IN ('call', 'meeting') AND happened_on BETWEEN %(ms)s AND %(t)s) AS conversations_month,
               (SELECT coalesce(sum(hours), 0) FROM practice.time_entries WHERE work_date BETWEEN %(ws)s AND %(t)s) AS hours_week,
               (SELECT coalesce(sum(hours), 0) FROM practice.time_entries WHERE work_date BETWEEN %(ws)s AND %(t)s AND billable) AS billable_week,
               (SELECT coalesce(sum(hours), 0) FROM practice.time_entries WHERE work_date BETWEEN %(ys)s AND %(t)s) AS hours_ytd
        """, {"ys": ys, "ms": ms, "ws": ws, "t": t})
    out = {k: _f(v) for k, v in r.items()}
    pipe = pipeline_by_stage()
    out["pipeline"] = sum(p["value"] for p in pipe if p["stage"] in OPEN_STAGES)
    out["pipeline_weighted"] = sum(p["weighted"] for p in pipe if p["stage"] in OPEN_STAGES)
    out["pipeline_count"] = sum(p["count"] for p in pipe if p["stage"] in OPEN_STAGES)
    out["effective_rate"] = out["revenue_ytd"] / out["hours_ytd"] if out["hours_ytd"] else None
    days_in_year = 366 if calendar.isleap(t.year) else 365
    out["goal"] = float(s["revenue_goal"])
    out["goal_pace"] = out["goal"] * t.timetuple().tm_yday / days_in_year
    out["profit_ytd"] = out["revenue_ytd"] - out["expenses_ytd"]
    out["week_start"], out["month_start"], out["today"] = ws, ms, t
    out["targets"] = {"hours": float(s["weekly_hours_target"]), "conversations": float(s["monthly_conversations_target"])}
    return out


def pipeline_by_stage() -> list[dict]:
    rows = {r["stage"]: r for r in db.query("""
        SELECT stage, count(*) AS n, coalesce(sum(est_value), 0) AS value FROM practice.companies
        WHERE NOT archived AND kind = 'prospect' GROUP BY 1""")}
    out = []
    for key, label, prob in STAGES:
        r = rows.get(key)
        value = _f(r["value"]) if r else 0.0
        out.append({"stage": key, "label": label, "count": r["n"] if r else 0, "value": value, "weighted": value * prob})
    return out


def follow_ups(t: dt.date | None = None, days=7) -> list[dict]:
    t = t or today()
    return db.query("""SELECT id, name, kind, stage, next_step, next_step_date, contact_name,
                              (next_step_date < %(t)s) AS overdue
                       FROM practice.companies
                       WHERE NOT archived AND next_step_date IS NOT NULL AND next_step_date <= %(until)s
                       ORDER BY next_step_date, name""", {"t": t, "until": t + dt.timedelta(days=days)})


def monthly_money(year: int) -> dict:
    def by_month(sql):
        out = [0.0] * 12
        for r in db.query(sql, {"s": dt.date(year, 1, 1), "e": dt.date(year, 12, 31)}):
            out[int(r["m"]) - 1] = _f(r["v"])
        return out
    return {
        "revenue": by_month("SELECT extract(month FROM issued_date) AS m, sum(amount) AS v FROM practice.invoices "
                            "WHERE issued_date BETWEEN %(s)s AND %(e)s GROUP BY 1"),
        "cash": by_month("SELECT extract(month FROM paid_date) AS m, sum(amount) AS v FROM practice.invoices "
                         "WHERE paid_date BETWEEN %(s)s AND %(e)s GROUP BY 1"),
        "expenses": by_month("SELECT extract(month FROM spent_date) AS m, sum(amount) AS v FROM practice.expenses "
                             "WHERE spent_date BETWEEN %(s)s AND %(e)s GROUP BY 1"),
    }


def engagements_with_hours(status=("proposed", "active")) -> list[dict]:
    return db.query("""
        SELECT e.*, c.name AS company_name,
               coalesce((SELECT sum(hours) FROM practice.time_entries te WHERE te.engagement_id = e.id), 0) AS hours_used,
               coalesce((SELECT sum(amount) FROM practice.invoices i WHERE i.engagement_id = e.id), 0) AS invoiced
        FROM practice.engagements e JOIN practice.companies c ON c.id = e.company_id
        WHERE e.status = ANY(%(s)s) ORDER BY e.status, e.start_date NULLS LAST, c.name""", {"s": list(status)})


def hours_by_company(start: dt.date, end: dt.date) -> list[dict]:
    return db.query("""
        SELECT coalesce(c.name, 'Running the business') AS company, sum(t.hours) AS hours,
               sum(t.hours) FILTER (WHERE t.billable) AS billable
        FROM practice.time_entries t LEFT JOIN practice.companies c ON c.id = t.company_id
        WHERE t.work_date BETWEEN %(s)s AND %(e)s GROUP BY 1 ORDER BY 2 DESC""", {"s": start, "e": end})


def source_results() -> list[dict]:
    """Which channels produce conversations and wins, so effort goes where it works."""
    return db.query("""
        SELECT coalesce(nullif(source, ''), '(not recorded)') AS source, count(*) AS companies,
               count(*) FILTER (WHERE stage IN ('conversation', 'proposal', 'won')) AS reached_conversation,
               count(*) FILTER (WHERE stage = 'won' OR kind IN ('client', 'past_client')) AS won
        FROM practice.companies WHERE NOT archived AND kind <> 'partner' GROUP BY 1 ORDER BY 2 DESC""")
