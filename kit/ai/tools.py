"""The tools the AI can call. Each one wraps a metric function the pages already use,
so the AI's figures match the screens exactly, and each one enforces the asking
person's branch access. Nothing here can change data.
"""
import datetime as dt
import json
import re
from decimal import Decimal

import psycopg2
import psycopg2.extras

from .. import cleanup, db, metrics
from ..config import get_settings

ROW_LIMIT = 200

DIMENSION_LIST = sorted(metrics.DIMENSIONS)
DATE = {"type": "string", "description": "YYYY-MM-DD"}

TOOLS = [
    {
        "name": "company_overview",
        "description": "Headline numbers for this year to date vs the same dates last year: bookings, win rate (by $ and "
                       "count), margin, open pipeline closing this year, billed, collected, receivables. Start here for "
                       "'how are we doing' questions.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "deal_results",
        "description": "Won and lost results for deals closed between two dates: amounts, counts, win rate by $ and by "
                       "count, weighted margin. Optionally split by one dimension (e.g. branch, segment, deal_type, "
                       "owner_name, lead_source, loss_reason). Use for bookings, win rate and margin questions.",
        "input_schema": {"type": "object", "properties": {
            "start": DATE, "end": DATE,
            "group_by": {"type": "string", "enum": DIMENSION_LIST, "description": "Optional split."}},
            "required": ["start", "end"], "additionalProperties": False},
    },
    {
        "name": "open_pipeline",
        "description": "Open (not yet won or lost) deals as of today: total, weighted (amount × stage probability), and "
                       "past-due deals whose close date has passed. Optionally split by one dimension (stage, branch, "
                       "segment, deal_type, owner_name...).",
        "input_schema": {"type": "object", "properties": {
            "group_by": {"type": "string", "enum": DIMENSION_LIST}}, "additionalProperties": False},
    },
    {
        "name": "find_deals",
        "description": "List individual deals matching filters, biggest first by default (max 50 rows), with totals for "
                       "everything that matched. Each deal comes with a CRM link. Use to name specific deals.",
        "input_schema": {"type": "object", "properties": {
            "status": {"type": "string", "enum": sorted(metrics.DEAL_STATUS), "description": "Default open."},
            "branch": {"type": "string", "description": "Branch name as people use it, e.g. 'Austin'."},
            "region": {"type": "string"}, "deal_type": {"type": "string"}, "segment": {"type": "string"},
            "stage": {"type": "string"}, "lead_source": {"type": "string"},
            "close_from": DATE, "close_to": DATE, "created_from": DATE, "created_to": DATE,
            "min_amount": {"type": "number"}, "max_amount": {"type": "number"},
            "account_contains": {"type": "string"}, "owner_contains": {"type": "string"},
            "sort": {"type": "string", "enum": sorted(metrics.DEAL_SORT)},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50}},
            "additionalProperties": False},
    },
    {
        "name": "weekly_scorecard",
        "description": "The weekly scorecard: 13 weeks (Monday to Sunday, newest last; the last week is in progress) of "
                       "new deals, new pipeline, bookings, trailing-90-day win rate, billing, collections and AR over "
                       "60 days, each with its goal.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "recent_changes",
        "description": "What changed in the last N days (1-31): deals created, won and lost (by close date), and open "
                       "deals whose close date was pushed to a later month (from the CRM's change history).",
        "input_schema": {"type": "object", "properties": {
            "days": {"type": "integer", "minimum": 1, "maximum": 31}}, "required": ["days"], "additionalProperties": False},
    },
    {
        "name": "where_we_sell_best",
        "description": "Close rate by $ and won dollars for every combination of two dimensions over a period, plus the "
                       "best slices (most won $ among slices with 5+ closed deals and an above-average close rate).",
        "input_schema": {"type": "object", "properties": {
            "start": DATE, "end": DATE,
            "rows": {"type": "string", "enum": ["segment", "deal_type", "branch", "region", "lead_source", "owner_name"]},
            "columns": {"type": "string", "enum": ["segment", "deal_type", "branch", "region", "lead_source", "owner_name"]}},
            "required": ["start", "end", "rows", "columns"], "additionalProperties": False},
    },
    {
        "name": "receivables",
        "description": "Unpaid invoices today by days past due (aging buckets), and the customers with the most overdue.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "data_problems",
        "description": "The clean-up list: counts of data problems in the source systems (placeholder dates, "
                       "duplicates, stale open deals, missing margins, missing loss reasons, won but not billed, "
                       "unlinked customers), with why each matters and how to fix it.",
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

SQL_TOOL = {
    "name": "run_sql",
    "description": (
        "Read-only SQL (PostgreSQL) for questions the other tools can't answer. One SELECT or WITH statement; at most "
        f"{ROW_LIMIT} rows come back; 10-second limit. Prefer the other tools: their numbers match the hub's pages. "
        "Available views (business rules already applied, excluded deals removed):\n"
        "rpt.deals(id, name, account_id, account_name, segment, owner_name, branch_code, branch, region, deal_type, "
        "stage, is_closed, is_won, is_lost, is_open, probability, amount, weighted_amount, margin_pct, margin_amount, "
        "close_date, created_date, loss_reason, lead_source)\n"
        "rpt.invoices(id, number, customer_id, customer_name, account_id, segment, deal_id, branch_code, branch, region, "
        "invoice_date, due_date, amount, amount_paid, paid_date, balance, is_open, days_past_due, aging_bucket, memo)\n"
        "rpt.deal_history(deal_id, deal_name, account_name, branch, deal_type, owner_name, field, old_value, new_value, "
        "changed_at, changed_date) - field is StageName, CloseDate or Amount\n"
        "rpt.branches(code, name, region). Percentages: sum numerators / sum denominators, never average them; leave "
        "blank margins out rather than counting them as zero."),
    "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"],
                     "additionalProperties": False},
}


class ToolError(ValueError):
    """A problem the model can fix (bad dates, unknown names). Sent back as an error result."""


def tools_for(user) -> list[dict]:
    """Branch-limited users don't get raw SQL, because SQL can't be held to their branches."""
    sql_ok = not user.get("branches") and bool(get_settings().ai_reader_password)
    return TOOLS + ([SQL_TOOL] if sql_ok else [])


def _d(v, name):
    if not v:
        raise ToolError(f"{name} is required (YYYY-MM-DD)")
    try:
        return dt.date.fromisoformat(str(v)[:10])
    except ValueError:
        raise ToolError(f"{name} must be a date like 2026-03-31, got {v!r}")


def _clean(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_clean(x) for x in v]
    if isinstance(v, float):
        return round(v, 4)
    return v


def _crm_link(rec_id):
    tmpl = get_settings().client.get("links", {}).get("crm_deal")
    return tmpl.format(id=rec_id) if tmpl else None


def _branch_code(name, scope):
    rows = db.query("SELECT code, name FROM core.branches")
    for r in rows:
        if name and name.lower() in (r["name"].lower(), r["code"].lower()):
            if scope and r["code"] not in scope:
                raise ToolError(f"This person can only see these branches: {', '.join(scope)}")
            return r["code"], r["name"]
    raise ToolError(f"Unknown branch {name!r}. Branches: {', '.join(r['name'] for r in rows)}")


def run(name: str, args: dict, user: dict) -> str:
    """Run one tool for one user. Returns JSON text for the model."""
    scope = user.get("branches") or None
    t = metrics.today()
    args = args or {}
    if name == "company_overview":
        (ys, ye), (ls, le) = metrics.ytd_windows(t)
        out = {"today": t, "this_year": {"from": ys, "to": ye, **metrics.closed_summary(ys, ye, scope),
                                         **metrics.billing_summary(ys, ye, scope)},
               "same_dates_last_year": {"from": ls, "to": le, **metrics.closed_summary(ls, le, scope),
                                        **metrics.billing_summary(ls, le, scope)},
               "open_pipeline": metrics.pipeline_summary(t, scope), "receivables": metrics.ar_aging(scope),
               "bookings_goal_this_year": None if scope else metrics.bookings_goal(t.year),
               "links": {"home": "/", "won_this_year": metrics.deals_link(status="won", close_from=ys, close_to=ye)}}
    elif name == "deal_results":
        s, e = _d(args.get("start"), "start"), _d(args.get("end"), "end")
        out = {"period": {"from": s, "to": e}, "total": metrics.closed_summary(s, e, scope),
               "link": metrics.deals_link(status="closed", close_from=s, close_to=e)}
        if args.get("group_by"):
            out["by_" + args["group_by"]] = metrics.closed_breakdown(s, e, args["group_by"], scope)
    elif name == "open_pipeline":
        out = {"as_of": t, "summary": metrics.pipeline_summary(t, scope), "link": "/deals?status=open"}
        if args.get("group_by"):
            out["by_" + args["group_by"]] = metrics.pipeline_breakdown(t, args["group_by"], scope)
    elif name == "find_deals":
        filters = dict(args)
        link_params = {"status": filters.get("status") or "open"}
        if filters.get("branch"):
            code, bname = _branch_code(filters["branch"], scope)
            filters["branch"] = bname
            link_params["branch"] = code
        for key in ("close_from", "close_to", "created_from", "created_to"):
            if filters.get(key):
                filters[key] = _d(filters[key], key)
                link_params[key] = filters[key]
        for key in ("deal_type", "segment", "stage"):
            if filters.get(key):
                link_params[key] = filters[key]
        res = metrics.find_deals(filters, scope, limit=filters.get("limit") or 15, sort=filters.get("sort") or "amount")
        for d in res["deals"]:
            d["crm_link"] = _crm_link(d["id"])
        simple = not any(filters.get(k) for k in ("region", "lead_source", "min_amount", "max_amount",
                                                  "account_contains", "owner_contains"))
        res["list_link"] = metrics.deals_link(**link_params) if simple else None
        out = res
    elif name == "weekly_scorecard":
        sc = metrics.scorecard(t, 13, scope)
        out = {"week_starts": sc["weeks"], "last_week_in_progress": True,
               "measures": [{"measure": r["label"], "goal": r["goal"], "goal_direction": "at least" if r["higher_is_better"]
                             else "at most", "values": r["values"]} for r in sc["rows"]], "link": "/scorecard"}
    elif name == "recent_changes":
        days = max(1, min(31, int(args.get("days") or 7)))
        ch = metrics.recent_changes(t, days, scope)
        trim = lambda rows: [dict(r, crm_link=_crm_link(r["id"])) for r in rows[:10]]
        out = {"since": ch["since"], "to": t, "totals": ch["totals"],
               "counts": {k: len(ch[k]) for k in ("created", "won", "lost", "slipped")},
               "biggest_won": trim(ch["won"]), "biggest_lost": trim(ch["lost"]),
               "pushed_to_later_month": trim(ch["slipped"]), "biggest_new": trim(ch["created"])}
    elif name == "where_we_sell_best":
        s, e = _d(args.get("start"), "start"), _d(args.get("end"), "end")
        try:
            g = metrics.sell_best_grid(s, e, scope, args.get("rows"), args.get("columns"))
        except ValueError as err:
            raise ToolError(str(err))
        out = {"period": {"from": s, "to": e}, "overall_close_rate_dollars": g["overall_rate"], "best_slices": g["best"],
               "cells": g["cells"], "link": f"/winloss?a={args.get('rows')}&b={args.get('columns')}"}
    elif name == "receivables":
        out = {"as_of": t, "aging": metrics.ar_aging(scope), "most_overdue_customers": metrics.overdue_customers(scope),
               "link": "/receivables"}
    elif name == "data_problems":
        out = {"checks": [{"key": r["check"].key, "problem": r["check"].title, "records": r["count"],
                           "amount": r["amount"], "why_it_matters": r["check"].why, "fix": r["check"].fix,
                           "system": r["check"].system} for r in cleanup.run_checks(scope, limit=0)],
               "link": "/cleanup"}
    elif name == "run_sql":
        if scope:
            raise ToolError("SQL isn't available for branch-limited users.")
        out = run_sql(args.get("query", ""))
    else:
        raise ToolError(f"Unknown tool {name}")
    return json.dumps(_clean(out), default=str)


_SQL_START = re.compile(r"^\s*(select|with)\b", re.I)


def run_sql(query: str) -> dict:
    """Run one read-only statement as the ai_reader login (SELECT on rpt.* only, read-only, timed out)."""
    q = query.strip().rstrip(";").strip()
    if not _SQL_START.match(q) or ";" in q:
        raise ToolError("Only a single SELECT (or WITH ... SELECT) statement is allowed.")
    settings = get_settings()
    dsn = psycopg2.extensions.parse_dsn(settings.database_url)
    dsn.update(user="ai_reader", password=settings.ai_reader_password, options="-c statement_timeout=10000")
    conn = psycopg2.connect(**dsn)
    try:
        conn.set_session(readonly=True)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            try:
                cur.execute(q)
            except psycopg2.Error as e:
                raise ToolError(f"SQL error: {e.pgerror or e}".strip())
            rows = cur.fetchmany(ROW_LIMIT + 1)
        conn.rollback()
    finally:
        conn.close()
    return {"rows": [dict(r) for r in rows[:ROW_LIMIT]], "truncated": len(rows) > ROW_LIMIT}


def describe_call(name: str, args: dict) -> str:
    """A short plain-English line for the progress indicator."""
    labels = {"company_overview": "Checking the headline numbers", "deal_results": "Looking at won and lost deals",
              "open_pipeline": "Looking at the open pipeline", "find_deals": "Finding the deals",
              "weekly_scorecard": "Reading the scorecard", "recent_changes": "Checking what changed",
              "where_we_sell_best": "Comparing where we win", "receivables": "Checking receivables",
              "data_problems": "Checking the clean-up list", "run_sql": "Running a custom query"}
    return labels.get(name, "Working")
