"""The Inbox (agents' work waiting for approval) and the Agents page."""
import datetime as dt

import psycopg2.extras

from .. import db
from ..agents.registry import AGENTS, BY_KEY
from ..ai import render, usage
from ..hub import forms, ui
from ..hub.ui import esc, money
from . import metrics as pm

KIND_LABEL = {"prospect": "New prospects", "message": "Messages to send", "post": "LinkedIn posts",
              "brief": "Briefs", "task": "Suggested tasks", "note": "Notes"}
ORDER = ["brief", "message", "prospect", "post", "task", "note"]


def _btn(token, action, label, cls="btn secondary", confirm=None):
    js = f' onsubmit="return confirm(\'{esc(confirm)}\')"' if confirm else ""
    return (f'<form method="post" action="{esc(action)}" class="inline"{js}><input type="hidden" name="_csrf" value="{token}">'
            f'<button class="{cls}" type="submit">{esc(label)}</button></form>')


def _item(i, token):
    d = i["data"] or {}
    agent = BY_KEY[i["agent"]].name if i["agent"] in BY_KEY else i["agent"]
    meta = f'<span class="meta">{esc(agent)} · {ui.short_date(i["created_at"].date())}</span>'
    base = f"/inbox/{i['id']}"
    if i["kind"] == "prospect":
        facts = " · ".join(esc(x) for x in (d.get("industry"), d.get("size"),
                                            ", ".join(v for v in (d.get("city"), d.get("state")) if v)) if x)
        contact = " · ".join(esc(x) for x in (d.get("contact_name"), d.get("contact_title")) if x) or "Contact: not found yet"
        signals = "".join(f"<li>{esc(x)}</li>" for x in d.get("signals") or [])
        sources = " ".join(f'<a href="{esc(u)}" target="_blank" rel="noopener nofollow">source {n}</a>'
                           for n, u in enumerate(d.get("sources") or [], 1))
        site = f'<a href="{esc(d["website"])}" target="_blank" rel="noopener nofollow">{esc(d["website"])}</a>' if d.get("website") else ""
        body = (f'<p class="meta">{facts}</p><p><strong>{contact}</strong> {site}</p><p>{esc(d.get("why_fit"))}</p>'
                f'{"<ul class=signals>" + signals + "</ul>" if signals else ""}'
                f'{"<p><strong>Angle:</strong> " + esc(d.get("angle")) + "</p>" if d.get("angle") else ""}'
                f'<details><summary>Drafted first message</summary><div class="draft pre" data-copy>{esc(d.get("first_message"))}</div></details>'
                f'<p class="meta">{sources}</p>')
        actions = _btn(token, base + "/approve", "Add to pipeline", "btn") + _btn(token, base + "/dismiss", "Not a fit")
    elif i["kind"] == "message":
        subject = f'<p><strong>Subject:</strong> {esc(d.get("subject"))}</p>' if d.get("subject") else ""
        body = (f'<p class="meta">{esc(d.get("reason") or "")}</p>{subject}<div class="draft pre" data-copy>{esc(i["body"])}</div>')
        link = f' · <a href="/companies/{i["company_id"]}">company</a>' if i["company_id"] else ""
        meta = meta.replace("</span>", f"{link}</span>", 1)
        actions = (f'<button class="btn" type="button" data-copy-btn>Copy</button>'
                   + _btn(token, base + "/sent", "I sent it", "btn secondary") + _btn(token, base + "/dismiss", "Skip"))
    elif i["kind"] == "post":
        body = (f'<p class="meta">{esc(d.get("why_now") or "")}</p><div class="draft pre" data-copy>{esc(i["body"])}</div>')
        actions = (f'<button class="btn" type="button" data-copy-btn>Copy</button>'
                   + _btn(token, base + "/done", "I posted it", "btn secondary") + _btn(token, base + "/dismiss", "Skip"))
    elif i["kind"] == "task":
        due = f' · due {ui.short_date(dt.date.fromisoformat(d["due_date"]))}' if d.get("due_date") else ""
        body = f'<p class="meta">{esc(i["body"] or "")}{esc(due)}</p>'
        actions = _btn(token, base + "/approve", "Add task", "btn") + _btn(token, base + "/dismiss", "Skip")
    else:  # brief, note
        body = f'<div class="brief">{render.to_html(i["body"] or "")}</div>'
        actions = _btn(token, base + "/done", "Done", "btn secondary")
    return (f'<article class="inbox-item" id="item-{i["id"]}"><div class="inbox-head"><h3>{esc(i["title"])}</h3>{meta}</div>'
            f'{body}<div class="inbox-actions">{actions}</div></article>')


def inbox_page(request):
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    items = db.query("SELECT * FROM practice.agent_items WHERE status = 'pending' ORDER BY created_at DESC LIMIT 200")
    groups = {}
    for i in items:
        groups.setdefault(i["kind"], []).append(i)
    blocks = []
    for kind in ORDER:
        if kind in groups:
            blocks.append(f'<section class="card" id="{kind}"><div class="card-head"><h2>{KIND_LABEL[kind]} '
                          f'<span class="meta">({len(groups[kind])})</span></h2></div>'
                          + "".join(_item(i, token) for i in groups[kind]) + "</section>")
    empty = ("" if items else '<section class="card"><p>Nothing waiting. The agents drop their work here: new prospects, '
             'drafted messages and posts, briefs and suggested tasks. <a href="/agents">See the agents</a>.</p></section>')
    body = (f'<p class="lead">Everything the agents produce waits here. Nothing is sent or posted until you do it yourself.</p>'
            f'{empty}{"".join(blocks)}')
    return ui.page(request, "Inbox", body, "Inbox", subtitle=f"{len(items)} waiting")


def decide(item_id: int, action: str) -> str:
    """Apply an inbox decision. Returns where to go next."""
    i = db.one("SELECT * FROM practice.agent_items WHERE id = %(i)s AND status = 'pending'", {"i": item_id})
    if not i:
        return "/inbox"
    d = i["data"] or {}
    status = {"dismiss": "dismissed", "approve": "approved", "sent": "done", "done": "done"}[action]
    nxt = "/inbox"
    with db.connect() as conn:
        if action == "approve" and i["kind"] == "prospect":
            notes = "\n".join(x for x in [
                f"Found by the business development agent on {i['created_at']:%b %-d, %Y}.",
                f"Why they fit: {d.get('why_fit')}" if d.get("why_fit") else "",
                ("Signals: " + "; ".join(d.get("signals") or [])) if d.get("signals") else "",
                ("Sources: " + " ".join(d.get("sources") or [])) if d.get("sources") else "",
                f"Angle: {d.get('angle')}" if d.get("angle") else ""] if x)
            row = db.one("""INSERT INTO practice.companies (name, kind, stage, industry, size_note, city, website, contact_name,
                                                           contact_title, source, next_step, next_step_date, notes)
                            VALUES (%(n)s, 'prospect', 'lead', %(ind)s, %(size)s, %(city)s, %(web)s, %(cn)s, %(ct)s,
                                    'Agent research', 'Send first message', core.local_today(), %(notes)s) RETURNING id""",
                         {"n": d.get("company") or i["title"], "ind": d.get("industry"), "size": d.get("size"),
                          "city": ", ".join(v for v in (d.get("city"), d.get("state")) if v) or None,
                          "web": d.get("website"), "cn": d.get("contact_name"), "ct": d.get("contact_title"), "notes": notes},
                         conn)
            if d.get("first_message"):
                db.execute("""INSERT INTO practice.agent_items (agent, kind, title, body, data, company_id)
                              VALUES ('bizdev', 'message', %(t)s, %(b)s, %(d)s, %(c)s)""",
                           {"t": f"First message to {d.get('contact_name') or d.get('company')}", "b": d["first_message"],
                            "d": psycopg2.extras.Json({"channel": "email", "company": d.get("company"),
                                                                             "reason": "First contact"}),
                            "c": row["id"]}, conn)
            db.execute("UPDATE practice.agent_items SET company_id = %(c)s WHERE id = %(i)s", {"c": row["id"], "i": item_id}, conn)
            nxt = f"/companies/{row['id']}"
        elif action == "approve" and i["kind"] == "task":
            db.execute("""INSERT INTO practice.tasks (title, category, due_date, company_id, notes, created_by)
                          VALUES (%(t)s, 'General', %(d)s, %(c)s, %(n)s, %(a)s)""",
                       {"t": i["title"], "d": d.get("due_date") or None, "c": i["company_id"], "n": i["body"], "a": i["agent"]}, conn)
        elif action == "sent" and i["kind"] == "message" and i["company_id"]:
            db.execute("""INSERT INTO practice.activities (company_id, happened_on, kind, summary)
                          VALUES (%(c)s, core.local_today(), %(k)s, %(s)s)""",
                       {"c": i["company_id"], "k": "linkedin" if d.get("channel") == "linkedin" else "email",
                        "s": "Sent: " + (i["body"] or "")[:1500]}, conn)
            db.execute("""UPDATE practice.companies SET stage = CASE WHEN stage = 'lead' THEN 'contacted' ELSE stage END,
                          updated_at = now() WHERE id = %(c)s""", {"c": i["company_id"]}, conn)
        db.execute("UPDATE practice.agent_items SET status = %(s)s, decided_at = now() WHERE id = %(i)s",
                   {"s": status, "i": item_id}, conn)
    return nxt


def _job_name(agent, job):
    a = BY_KEY.get(agent)
    return next((j.name for j in a.jobs if j.key == job), job) if a else job


def agents_page(request, message=""):
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    configured = usage.is_configured("agents")
    spend = usage.month_spend("agents")
    cap = float(usage.ai_settings()["agents_monthly_cap_usd"])
    cards = []
    for a in AGENTS:
        rows = []
        for j in a.jobs:
            last = db.one("""SELECT status, summary, error, cost_usd, started_at, items_created FROM practice.agent_runs
                             WHERE agent = %(a)s AND job = %(j)s ORDER BY started_at DESC LIMIT 1""", {"a": a.key, "j": j.key})
            when = ", ".join(d.capitalize() for d in j.days) + f" at {j.time}" if j.days else "On demand"
            if last:
                state = ui.status_pill({"done": "ok", "failed": "failed", "running": "warning"}[last["status"]])
                info = (f'{state} {ui.short_date(last["started_at"].date())} · {last["items_created"]} item{"" if last["items_created"] == 1 else "s"} · '
                        f'${float(last["cost_usd"]):.2f}<div class="meta">{esc(last["error"] or last["summary"] or "")}</div>')
            else:
                info = '<span class="meta">Hasn\'t run yet</span>'
            run_btn = _btn(token, f"/agents/{a.key}/{j.key}/run", "Run now") if configured else ""
            rows.append(f'<li><div class="grow"><strong>{esc(j.name)}</strong><div class="meta">{esc(when)}'
                        f'{" · uses the web" if j.web else ""}</div><div class="run-info">{info}</div></div>{run_btn}</li>')
        cards.append(f'<section class="card agent"><div class="card-head"><h2>{esc(a.name)}</h2></div>'
                     f'<p class="meta" style="margin-top:0">{esc(a.role)}</p><ul class="list">{"".join(rows)}</ul></section>')
    runs = db.query("SELECT * FROM practice.agent_runs ORDER BY started_at DESC LIMIT 15")
    run_rows = "".join(
        f'<tr><td>{esc(BY_KEY[r["agent"]].name if r["agent"] in BY_KEY else r["agent"])}</td><td>{esc(_job_name(r["agent"], r["job"]))}</td>'
        f'<td>{ui.status_pill({"done": "ok", "failed": "failed", "running": "warning"}[r["status"]])}</td>'
        f'<td class="n">{r["items_created"]}</td><td class="n">${float(r["cost_usd"]):.2f}</td>'
        f'<td class="n">{ui.short_date(r["started_at"].date())}</td></tr>' for r in runs)
    note = (f'<p class="lead">{esc(message)}</p>' if message else "") + (
        "" if configured else '<section class="card warn-card"><strong>The agents are switched off</strong>: they need their '
        'API key (<code>ANTHROPIC_API_KEY_AGENTS</code>). Once it\'s added on the server they run on the schedules below.</section>')
    body = f"""{note}<div class="tiles">
{ui.tile("Agent spending this month", f"${spend:,.2f}", f"cap ${cap:,.0f}")}
{ui.tile("Waiting in your inbox", str(sum(pm.inbox_counts().values())), "items to review", "/inbox")}</div>
<div class="agents-grid">{"".join(cards)}</div>
<section class="card"><h2>Recent runs</h2><div class="scroll"><table class="data"><thead><tr><th>Agent</th><th>Job</th><th>Status</th>
<th class="n">Items</th><th class="n">Cost</th><th class="n">Date</th></tr></thead><tbody>{run_rows or "<tr><td colspan=6>No runs yet.</td></tr>"}</tbody></table></div>
{ui.how("Agents never send, post or delete anything; their work waits in your Inbox. They use public web information only and never open LinkedIn. Each run has its own cost limit, and all agents share the monthly cap.")}</section>"""
    return ui.page(request, "Agents", body, "Agents", subtitle="Your staff. Times are Central.")
