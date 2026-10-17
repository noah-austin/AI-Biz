"""Tools for the agents: read the hub, and propose work for Noah to approve. Nothing here sends or deletes."""
import datetime as dt
import json
import re

import psycopg2.extras

from .. import db
from ..ai import tools as ai_tools
from ..practice import metrics as pm

STR = {"type": "string"}
URLS = {"type": "array", "items": {"type": "string"}, "maxItems": 10}


def _schema(props, required):
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


READ_TOOLS = [t for t in ai_tools.PRACTICE_TOOLS] + [
    {"name": "weekly_scorecard", "description": "Noah's weekly scorecard: outreach, new prospects, conversations, "
     "proposals, revenue and hours for the last 8 weeks (Monday to Sunday, newest last), with weekly targets.",
     "input_schema": _schema({}, [])},
    {"name": "open_tasks", "description": "Open tasks with due dates.", "input_schema": _schema({}, [])},
    {"name": "recent_items", "description": "What agents have already produced recently (prospects, messages, posts, "
     "briefs, tasks) and whether Noah approved, dismissed or finished them. Use it to avoid repeating work.",
     "input_schema": _schema({"kind": {"type": "string", "enum": ["prospect", "message", "post", "brief", "task"]},
                              "days": {"type": "integer", "minimum": 1, "maximum": 120}}, [])},
    {"name": "company_exists", "description": "Check whether a company is already in the pipeline or was already "
     "proposed or dismissed. Always check before proposing a prospect.",
     "input_schema": _schema({"name": STR, "website": STR}, ["name"])},
]

PROPOSE_TOOLS = [
    {"name": "propose_prospect", "description": "Propose one new prospect for Noah to approve into the pipeline.",
     "input_schema": _schema({
         "company": STR, "website": STR, "industry": STR, "size": {"type": "string", "description": "people / revenue if known"},
         "city": STR, "state": STR,
         "contact_name": {"type": "string", "description": "Only if a cited public source names them."},
         "contact_title": STR,
         "why_fit": {"type": "string", "description": "2-3 sentences."},
         "signals": {"type": "array", "items": STR, "maxItems": 8},
         "sources": URLS, "angle": STR,
         "first_message": {"type": "string", "description": "Under 90 words, ready to send."}},
         ["company", "why_fit", "sources", "first_message"])},
    {"name": "propose_message", "description": "Draft one message (email or LinkedIn) for Noah to send himself.",
     "input_schema": _schema({"company": STR, "channel": {"type": "string", "enum": ["email", "linkedin"]},
                              "to": STR, "subject": STR, "body": STR, "reason": STR}, ["company", "channel", "body"])},
    {"name": "propose_post", "description": "Draft one LinkedIn post for Noah to edit and post himself.",
     "input_schema": _schema({"text": STR, "why_now": STR}, ["text"])},
    {"name": "write_brief", "description": "Write a brief or report for Noah to read.",
     "input_schema": _schema({"title": STR, "body": STR, "company": STR}, ["title", "body"])},
    {"name": "propose_task", "description": "Suggest a task for Noah's list.",
     "input_schema": _schema({"title": STR, "due_date": {"type": "string", "description": "YYYY-MM-DD"},
                              "company": STR, "reason": STR}, ["title"])},
]

ALL_TOOLS = READ_TOOLS + PROPOSE_TOOLS


class ToolError(ValueError):
    pass


def _company_id(name):
    if not name:
        return None
    r = db.one("""SELECT id FROM practice.companies WHERE lower(name) = lower(%(n)s)
                  OR name ILIKE '%%' || %(n)s || '%%' ORDER BY (lower(name) = lower(%(n)s)) DESC, length(name) LIMIT 1""",
               {"n": name})
    return r["id"] if r else None


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower().replace("https://", "").replace("http://", "").replace("www.", ""))


def _add_item(run_id, agent, kind, title, body, data, company_id=None):
    with db.connect() as conn:
        db.execute("""INSERT INTO practice.agent_items (run_id, agent, kind, title, body, data, company_id)
                      VALUES (%(r)s, %(a)s, %(k)s, %(t)s, %(b)s, %(d)s, %(c)s)""",
                   {"r": run_id, "a": agent, "k": kind, "t": title[:300], "b": body,
                    "d": psycopg2.extras.Json(data), "c": company_id}, conn)
        db.execute("UPDATE practice.agent_runs SET items_created = items_created + 1 WHERE id = %(r)s", {"r": run_id}, conn)


def run(name: str, args: dict, run_id: int, agent: str) -> str:
    args = args or {}
    if name in {t["name"] for t in ai_tools.PRACTICE_TOOLS}:
        return json.dumps(ai_tools._clean(ai_tools.run_practice(name, args)), default=str)
    if name == "weekly_scorecard":
        out = pm.weekly_scorecard()
    elif name == "open_tasks":
        out = {"tasks": pm.open_tasks(50)}
    elif name == "recent_items":
        days = max(1, min(120, int(args.get("days") or 30)))
        out = {"items": db.query("""SELECT kind, title, status, created_at, data->>'company' AS company
                                    FROM practice.agent_items WHERE created_at > now() - make_interval(days => %(d)s)
                                      AND (%(k)s::text IS NULL OR kind = %(k)s) ORDER BY created_at DESC LIMIT 60""",
                                 {"d": days, "k": args.get("kind")})}
    elif name == "company_exists":
        n, w = _norm(args.get("name")), _norm(args.get("website"))
        known = db.query("SELECT name, website, kind, stage FROM practice.companies")
        proposed = db.query("""SELECT data->>'company' AS name, data->>'website' AS website, status FROM practice.agent_items
                               WHERE kind = 'prospect'""")
        hits = [r for r in known if n and (_norm(r["name"]) == n or (w and _norm(r["website"]) == w))]
        hits += [r for r in proposed if n and (_norm(r["name"]) == n or (w and _norm(r["website"]) == w))]
        out = {"exists": bool(hits), "matches": hits[:5]}
    elif name == "propose_prospect":
        sources = [s for s in (args.get("sources") or []) if str(s).startswith(("http://", "https://"))]
        if not sources:
            raise ToolError("Every prospect needs at least one source link (http/https).")
        if json.loads(run("company_exists", {"name": args["company"], "website": args.get("website")}, run_id, agent))["exists"]:
            raise ToolError(f"{args['company']} is already known or was already proposed; pick another company.")
        args["sources"] = sources
        _add_item(run_id, agent, "prospect", args["company"], args.get("why_fit"), args)
        out = {"ok": True}
    elif name == "propose_message":
        cid = _company_id(args.get("company"))
        if not cid:
            raise ToolError(f"No company called {args.get('company')!r} in the hub.")
        title = f"{'Email' if args['channel'] == 'email' else 'LinkedIn'} to {args.get('to') or args['company']}"
        _add_item(run_id, agent, "message", title, args["body"], args, cid)
        out = {"ok": True}
    elif name == "propose_post":
        first = args["text"].strip().splitlines()[0][:120] if args["text"].strip() else "LinkedIn post"
        _add_item(run_id, agent, "post", first, args["text"], args)
        out = {"ok": True}
    elif name == "write_brief":
        _add_item(run_id, agent, "brief", args["title"], args["body"], args, _company_id(args.get("company")))
        out = {"ok": True}
    elif name == "propose_task":
        if args.get("due_date"):
            try:
                dt.date.fromisoformat(args["due_date"])
            except ValueError:
                raise ToolError("due_date must be YYYY-MM-DD")
        _add_item(run_id, agent, "task", args["title"], args.get("reason"), args, _company_id(args.get("company")))
        out = {"ok": True}
    else:
        raise ToolError(f"Unknown tool {name}")
    return json.dumps(ai_tools._clean(out), default=str)
