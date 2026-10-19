"""The assistant's toolbox: everything the agents can do, plus the changes Noah asks for in chat.

Claude Code on the server (Noah's subscription) is the assistant. It works on the hub only through these
tools, via bin/hub, so every change goes through the same checks as the hub's own pages:

    bin/hub tools                         # list the tools and their inputs
    bin/hub call NAME '{"arg": "value"}'  # run one tool (or pipe the JSON in on stdin); prints JSON
    bin/hub job bizdev find_prospects     # the full brief for a scheduled job

Read tools and propose_* tools are safe at any time (proposals wait in the Inbox). The change tools
(CHANGE_TOOLS) alter the hub's records; in chat the assistant confirms each one with Noah first.
"""
import datetime as dt
import json
import os

import psycopg2.extras

from .. import db
from ..agents import tools as agent_tools
from ..ai import tools as ai_tools
from ..practice import inbox
from ..practice import pages as practice_pages

STR = {"type": "string"}
DATE = {"type": "string", "description": "YYYY-MM-DD"}
STAGES = ["lead", "contacted", "conversation", "proposal", "won", "lost", "not_now"]
KINDS = ["prospect", "client", "partner", "past_client"]
ACTIVITY_KINDS = ["call", "meeting", "email", "linkedin", "event", "note"]
SETTINGS = {"ideal_client": STR, "prospects_per_run": {"type": "integer", "minimum": 1, "maximum": 25}}


def _schema(props, required):
    return {"type": "object", "properties": props, "required": required, "additionalProperties": False}


READ_TOOLS = agent_tools.READ_TOOLS + [
    {"name": "inbox", "description": "Everything waiting for Noah: agent items (with their id, kind, full text and data) "
     "and new website enquiries.", "input_schema": _schema({}, [])},
    {"name": "recent_runs", "description": "The latest scheduled job runs: which job, when, status, summary, items made.",
     "input_schema": _schema({"limit": {"type": "integer", "minimum": 1, "maximum": 50}}, [])},
    {"name": "get_settings", "description": "The assistant's settings: the ideal client and prospects per run.",
     "input_schema": _schema({}, [])},
]

CHANGE_TOOLS = [
    {"name": "decide_item", "description": "Act on an Inbox item. approve: a prospect joins the pipeline (and its first "
     "message waits in the Inbox), a task joins the list. dismiss: drop it. sent: Noah sent this message (logged on the "
     "company). done: finished.",
     "input_schema": _schema({"id": {"type": "integer"}, "action": {"type": "string", "enum": ["approve", "dismiss", "sent", "done"]}},
                             ["id", "action"])},
    {"name": "decide_enquiry", "description": "Act on a website enquiry. add: add it to the pipeline. dismiss: drop it.",
     "input_schema": _schema({"id": {"type": "integer"}, "action": {"type": "string", "enum": ["add", "dismiss"]}}, ["id", "action"])},
    {"name": "add_company", "description": "Add a company to the pipeline (someone Noah met, a referral...).",
     "input_schema": _schema({"name": STR, "kind": {"type": "string", "enum": KINDS}, "stage": {"type": "string", "enum": STAGES},
                              "industry": STR, "city": STR, "website": STR, "contact_name": STR, "contact_title": STR,
                              "contact_email": STR, "source": STR, "next_step": STR, "next_step_date": DATE, "notes": STR},
                             ["name"])},
    {"name": "update_company", "description": "Change a company's details. Only the fields given change; add_note "
     "appends to its notes.",
     "input_schema": _schema({"company": {"type": "string", "description": "its name"},
                              "kind": {"type": "string", "enum": KINDS}, "stage": {"type": "string", "enum": STAGES},
                              "industry": STR, "city": STR, "website": STR, "contact_name": STR, "contact_title": STR,
                              "contact_email": STR, "contact_phone": STR, "est_value": {"type": "number"},
                              "next_step": STR, "next_step_date": DATE, "add_note": STR}, ["company"])},
    {"name": "log_activity", "description": "Record a call, meeting, email, LinkedIn message, event or note with a company.",
     "input_schema": _schema({"company": STR, "kind": {"type": "string", "enum": ACTIVITY_KINDS}, "summary": STR,
                              "happened_on": DATE}, ["company", "kind", "summary"])},
    {"name": "add_task", "description": "Add a task to Noah's list.",
     "input_schema": _schema({"title": STR, "due_date": DATE, "company": STR, "notes": STR}, ["title"])},
    {"name": "complete_task", "description": "Mark a task done (ids come from open_tasks).",
     "input_schema": _schema({"id": {"type": "integer"}}, ["id"])},
    {"name": "set_setting", "description": "Change one of the assistant's settings, e.g. the ideal client the prospecting "
     "job looks for. Give the full new text, not just the change.",
     "input_schema": _schema({"key": {"type": "string", "enum": sorted(SETTINGS)}, "value": {}}, ["key", "value"])},
]

ALL_TOOLS = READ_TOOLS + agent_tools.PROPOSE_TOOLS + CHANGE_TOOLS
NAMES = {t["name"] for t in ALL_TOOLS}
CHANGE_NAMES = {t["name"] for t in CHANGE_TOOLS}


class ToolError(ValueError):
    pass


def _company(name, conn=None) -> dict:
    cid = agent_tools._company_id(name)
    if not cid:
        raise ToolError(f"No company called {name!r} in the hub. Check find_companies, or add it first.")
    return db.one("SELECT * FROM practice.companies WHERE id = %(i)s", {"i": cid}, conn)


def _date(v, field):
    if v in (None, ""):
        return None
    try:
        return dt.date.fromisoformat(str(v))
    except ValueError:
        raise ToolError(f"{field} must be YYYY-MM-DD")


def _check(args, schema):
    """Enforce the tool's schema on the basics: required fields, no unknown fields, allowed values."""
    props = schema.get("properties", {})
    unknown = set(args) - set(props)
    if unknown:
        raise ToolError(f"Unknown field(s): {', '.join(sorted(unknown))}. Allowed: {', '.join(props)}")
    missing = [k for k in schema.get("required", []) if args.get(k) in (None, "")]
    if missing:
        raise ToolError(f"Missing: {', '.join(missing)}")
    for k, v in args.items():
        enum = props[k].get("enum")
        if enum and v is not None and v not in enum:
            raise ToolError(f"{k} must be one of: {', '.join(enum)}")


def get_settings() -> dict:
    from ..agents import engine
    s = engine.settings()
    return {k: s[k] for k in SETTINGS}


def run(name: str, args: dict | None = None, run_id: int | None = None, by: str = "assistant") -> str:
    """Run one tool. Returns JSON text. run_id links proposals to a scheduled run."""
    args = dict(args or {})
    if name not in NAMES:
        raise ToolError(f"Unknown tool {name!r}. Run `bin/hub tools` for the list.")
    _check(args, next(t for t in ALL_TOOLS if t["name"] == name)["input_schema"])
    if name in {t["name"] for t in agent_tools.ALL_TOOLS}:
        try:
            return agent_tools.run(name, args, run_id, "assistant" if run_id is None else _run_agent(run_id))
        except (agent_tools.ToolError, ai_tools.ToolError) as e:
            raise ToolError(str(e))

    if name == "inbox":
        out = {"items": db.query("""SELECT i.id, i.kind, i.agent, i.title, i.body, i.data, i.created_at, c.name AS company
                                    FROM practice.agent_items i LEFT JOIN practice.companies c ON c.id = i.company_id
                                    WHERE i.status = 'pending' ORDER BY i.created_at"""),
               "website_enquiries": db.query("""SELECT id, name, email, company, role, company_size, crm, interest, message,
                                                       created_at FROM practice.inbound_leads WHERE status = 'new'
                                                ORDER BY created_at""")}
    elif name == "recent_runs":
        out = {"runs": db.query("""SELECT id, agent, job, status, summary, error, items_created, started_at, finished_at
                                   FROM practice.agent_runs ORDER BY started_at DESC LIMIT %(l)s""",
                                {"l": int(args.get("limit") or 15)})}
    elif name == "get_settings":
        out = get_settings()
    elif name == "decide_item":
        i = db.one("SELECT kind, status FROM practice.agent_items WHERE id = %(i)s", {"i": args["id"]})
        if not i or i["status"] != "pending":
            raise ToolError(f"No pending Inbox item {args['id']}.")
        if args["action"] == "approve" and i["kind"] not in ("prospect", "task"):
            raise ToolError(f"A {i['kind']} can't be approved; use sent, done or dismiss.")
        if args["action"] == "sent" and i["kind"] != "message":
            raise ToolError("Only messages can be marked sent.")
        nxt = inbox.decide(int(args["id"]), args["action"])
        out = {"ok": True, "link": nxt}
    elif name == "decide_enquiry":
        if not db.one("SELECT 1 AS x FROM practice.inbound_leads WHERE id = %(i)s AND status = 'new'", {"i": args["id"]}):
            raise ToolError(f"No new website enquiry {args['id']}.")
        out = {"ok": True, "link": inbox.decide_lead(int(args["id"]), args["action"])}
    elif name == "add_company":
        if db.one("SELECT 1 AS x FROM practice.companies WHERE lower(name) = lower(%(n)s)", {"n": args["name"].strip()}):
            raise ToolError(f"{args['name']} is already in the hub; use update_company.")
        args["next_step_date"] = _date(args.get("next_step_date"), "next_step_date")
        cols = [k for k in args if args[k] not in (None, "")]
        with db.connect() as conn:
            row = db.one(f"INSERT INTO practice.companies ({', '.join(cols)}) VALUES ({', '.join(f'%({c})s' for c in cols)}) "
                         "RETURNING id", args, conn)
        out = {"ok": True, "id": row["id"], "link": f"/companies/{row['id']}"}
    elif name == "update_company":
        c = _company(args.pop("company"))
        note = args.pop("add_note", None)
        if "next_step_date" in args:
            args["next_step_date"] = _date(args["next_step_date"], "next_step_date")
        if not args and not note:
            raise ToolError("Nothing to change.")
        sets = [f"{k} = %({k})s" for k in args]
        if note:
            stamp = dt.date.today().strftime("%b %-d, %Y")
            sets.append("notes = concat_ws(E'\\n', nullif(notes, ''), %(note)s)")
            args["note"] = f"{stamp}: {note}"
        db.execute(f"UPDATE practice.companies SET {', '.join(sets)}, updated_at = now() WHERE id = %(id)s",
                   {**args, "id": c["id"]})
        out = {"ok": True, "company": c["name"], "changed": sorted(k for k in args if k != "note") + (["notes"] if note else []),
               "link": f"/companies/{c['id']}"}
    elif name == "log_activity":
        c = _company(args["company"])
        db.execute("""INSERT INTO practice.activities (company_id, happened_on, kind, summary)
                      VALUES (%(c)s, coalesce(%(d)s, core.local_today()), %(k)s, %(s)s)""",
                   {"c": c["id"], "d": _date(args.get("happened_on"), "happened_on"), "k": args["kind"], "s": args["summary"]})
        db.execute("UPDATE practice.companies SET updated_at = now() WHERE id = %(c)s", {"c": c["id"]})
        out = {"ok": True, "company": c["name"], "link": f"/companies/{c['id']}"}
    elif name == "add_task":
        cid = _company(args["company"])["id"] if args.get("company") else None
        with db.connect() as conn:
            row = db.one("""INSERT INTO practice.tasks (title, due_date, company_id, notes, created_by)
                            VALUES (%(t)s, %(d)s, %(c)s, %(n)s, %(b)s) RETURNING id""",
                         {"t": args["title"], "d": _date(args.get("due_date"), "due_date"), "c": cid,
                          "n": args.get("notes"), "b": by}, conn)
        out = {"ok": True, "id": row["id"]}
    elif name == "complete_task":
        if not db.one("SELECT 1 AS x FROM practice.tasks WHERE id = %(i)s AND done_at IS NULL", {"i": args["id"]}):
            raise ToolError(f"No open task {args['id']}.")
        practice_pages.task_done(int(args["id"]))
        out = {"ok": True}
    elif name == "set_setting":
        key, value = args["key"], args["value"]
        if key == "ideal_client" and (not isinstance(value, str) or len(value.strip()) < 20):
            raise ToolError("Give the full ideal-client description (at least a sentence).")
        if key == "prospects_per_run" and (not isinstance(value, int) or not 1 <= value <= 25):
            raise ToolError("prospects_per_run must be a whole number from 1 to 25.")
        before = get_settings()[key]
        db.execute("""INSERT INTO practice.settings (key, value, updated_by) VALUES (%(k)s, %(v)s, %(b)s)
                      ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = now(), updated_by = EXCLUDED.updated_by""",
                   {"k": key, "v": psycopg2.extras.Json(value.strip() if isinstance(value, str) else value), "b": by})
        out = {"ok": True, "key": key, "before": before, "after": get_settings()[key]}
    return json.dumps(ai_tools._clean(out), default=str)


def _run_agent(run_id: int) -> str:
    r = db.one("SELECT agent FROM practice.agent_runs WHERE id = %(i)s", {"i": run_id})
    return r["agent"] if r else "assistant"


def current_run_id() -> int | None:
    """Scheduled runs pass their run id to the assistant's tool calls through the environment."""
    v = os.environ.get("HUB_RUN_ID", "")
    return int(v) if v.isdigit() else None
