"""Pages for the practice app. Each GET returns HTML; each POST reads a form, saves, and redirects."""
import calendar
import datetime as dt

from .. import db
from ..hub import forms, ui
from ..hub.forms import Field, FormError
from ..hub.ui import esc, money, pct
from . import metrics as pm

# ---------------------------------------------------------------- field lists

def _companies(kinds=None, blank="—"):
    rows = db.query("""SELECT id, name, kind FROM practice.companies WHERE NOT archived
                       AND (%(k)s::text[] IS NULL OR kind = ANY(%(k)s)) ORDER BY name""", {"k": kinds})
    return [("", blank)] + [(str(r["id"]), r["name"]) for r in rows]


def _engagements(company_id=None):
    rows = db.query("""SELECT e.id, e.name, c.name AS company FROM practice.engagements e
                       JOIN practice.companies c ON c.id = e.company_id
                       WHERE e.status IN ('proposed', 'active') AND (%(c)s::int IS NULL OR e.company_id = %(c)s)
                       ORDER BY c.name, e.name""", {"c": company_id})
    return [("", "—")] + [(str(r["id"]), f'{r["company"]}: {r["name"]}') for r in rows]


SOURCES = ["Referral partner", "Personal network", "LinkedIn", "Event / talk", "Cold outreach", "Website", "Other"]


def company_fields():
    return [
        Field("name", "Company", required=True, max_len=200),
        Field("kind", "Type", "select", options=list(pm.KINDS.items()), default="prospect"),
        Field("stage", "Stage", "select", options=[(k, l) for k, l, _ in pm.STAGES], default="lead",
              hint="For prospects."),
        Field("contact_name", "Contact"), Field("contact_title", "Title"),
        Field("contact_email", "Email", "email"), Field("contact_phone", "Phone", "tel"),
        Field("industry", "Industry"), Field("size_note", "Size", hint="e.g. 120 people, $40M"),
        Field("city", "City"), Field("website", "Website", "url"),
        Field("source", "How we met", "select", options=[("", "—")] + [(s, s) for s in SOURCES]),
        Field("referred_by", "Referred by", "select", options=_companies(["partner"])),
        Field("est_value", "Est. first-year value ($)", "money"),
        Field("next_step", "Next step", wide=True), Field("next_step_date", "Next step date", "date"),
        Field("notes", "Notes", "textarea"),
    ]


def activity_fields():
    return [
        Field("happened_on", "Date", "date", required=True, default=pm.today()),
        Field("kind", "Type", "select", options=list(pm.ACTIVITY_KINDS.items()), default="call"),
        Field("summary", "What happened", "textarea", required=True),
        Field("next_step", "Next step (updates the company)", wide=True),
        Field("next_step_date", "Next step date", "date"),
        Field("stage", "Move to stage", "select", options=[("", "(no change)")] + [(k, l) for k, l, _ in pm.STAGES]),
    ]


def engagement_fields(company_id=None):
    return [
        Field("company_id", "Company", "select", required=True, options=_companies(), default=company_id),
        Field("offer", "Offer", "select", options=list(pm.OFFERS.items())),
        Field("name", "Name", required=True, hint="e.g. CRM Health Report, Q4 Build"),
        Field("status", "Status", "select", options=[(s, s.capitalize()) for s in ("proposed", "active", "done", "cancelled")]),
        Field("price", "Fixed price ($)", "money"), Field("monthly_fee", "Monthly fee ($)", "money", hint="Retainers"),
        Field("hours_budget", "Hours budget", "number"),
        Field("start_date", "Start", "date"), Field("end_date", "End", "date"),
        Field("notes", "Notes", "textarea"),
    ]


def time_fields():
    return [
        Field("work_date", "Date", "date", required=True, default=pm.today()),
        Field("hours", "Hours", "number", required=True),
        Field("company_id", "For", "select", options=_companies(["client", "prospect", "past_client"], "Running the business")),
        Field("engagement_id", "Engagement", "select", options=_engagements()),
        Field("billable", "Billable", "checkbox", default=True),
        Field("note", "What you did", wide=True),
    ]


def invoice_fields():
    t = pm.today()
    n = db.one("SELECT count(*) + 1 AS n FROM practice.invoices WHERE issued_date >= %(y)s",
               {"y": dt.date(t.year, 1, 1)})["n"]
    return [
        Field("company_id", "Client", "select", required=True, options=_companies(["client", "past_client", "prospect"])),
        Field("engagement_id", "Engagement", "select", options=_engagements()),
        Field("number", "Invoice no.", required=True, default=f"INV-{t.year}-{n:03d}", max_len=40),
        Field("issued_date", "Issued", "date", required=True, default=t),
        Field("due_date", "Due", "date", required=True, default=t + dt.timedelta(days=int(pm.settings()["invoice_terms_days"]))),
        Field("amount", "Amount ($)", "money", required=True),
        Field("paid_date", "Paid on", "date"),
        Field("note", "Note", wide=True),
    ]


EXPENSE_CATEGORIES = ["Software", "Hosting", "AI usage", "Insurance", "Legal & accounting", "Marketing", "Travel",
                      "Equipment", "Fees & licences", "Other"]


def expense_fields():
    return [
        Field("spent_date", "Date", "date", required=True, default=pm.today()),
        Field("category", "Category", "select", options=[(c, c) for c in EXPENSE_CATEGORIES]),
        Field("vendor", "Vendor"), Field("amount", "Amount ($)", "money", required=True),
        Field("note", "Note", wide=True),
    ]


# ---------------------------------------------------------------- helpers

def _int(v):
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _link(cid, name):
    return f'<a href="/companies/{int(cid)}">{esc(name)}</a>'


def _due(d, t):
    if not d:
        return ""
    if d < t:
        return f'<span class="pill bad"><span aria-hidden="true">!</span> {ui.short_date(d)}</span>'
    if d == t:
        return '<span class="pill warn">Today</span>'
    return esc(ui.short_date(d))


def _card(title, body, action=""):
    return f'<section class="card"><div class="card-head"><h2>{esc(title)}</h2>{action}</div>{body}</section>'


QUICK = ('<div class="quick"><a class="btn" href="/companies/new">+ Prospect</a>'
         '<a class="btn secondary" href="/tasks">+ Task</a><a class="btn secondary" href="/time#add">+ Time</a>'
         '<a class="btn secondary" href="/money#invoice">+ Invoice</a></div>')


# ---------------------------------------------------------------- today

def today_page(request):
    o = pm.overview()
    t = o["today"]
    share = o["goal_share"] or 0
    goal = f"""<section class="card goal"><div class="card-head"><h2>Goal: {money(o["goal_amount"], True)} by {ui.date(o["goal_end"])}</h2>
<span class="meta">{o["goal_months_left"]} months left after this one</span></div>
<div class="goal-bar" role="img" aria-label="{pct(share, 0)} of goal"><i style="width:{min(100, share * 100):.1f}%"></i>
<b style="left:{min(100, 100 * o["goal_pace_amount"] / o["goal_amount"] if o["goal_amount"] else 0):.1f}%" title="Where you'd be on an even pace"></b></div>
<div class="goal-nums"><span><strong>{money(o["goal_so_far"], True)}</strong> invoiced</span>
<span>pace {money(o["goal_pace_amount"], True)}</span><span>forecast <strong>{money(o["goal_forecast"], True)}</strong></span>
<span>need {money(o["goal_needed_per_month"], True)} / month</span></div>
{ui.how(pm.HOW["goal"] + " " + pm.HOW["forecast"] + " " + pm.HOW["needed"])}</section>"""
    tiles = "".join([
        ui.tile("Monthly recurring", money(o["mrr"], True), "from active retainers", "/clients", pm.HOW["mrr"]),
        ui.tile("Pipeline", money(o["pipeline"], True),
                f'{money(o["pipeline_weighted"], True)} weighted · {int(o["pipeline_count"])} prospects', "/pipeline", pm.HOW["pipeline"]),
        ui.tile("Conversations this month", f'{int(o["conversations_month"])}',
                f'target {int(o["targets"]["conversations"])}', "/pipeline", pm.HOW["conversations"]),
        ui.tile("Hours this week", f'{o["hours_week"]:g}',
                f'of {o["targets"]["hours"]:g} · {o["billable_week"]:g} billable', "/time", pm.HOW["hours"]),
        ui.tile("Unpaid invoices", money(o["unpaid"], True),
                (f'{money(o["overdue"], True)} overdue' if o["overdue"] else "none overdue"), "/money", pm.HOW["unpaid"]),
    ])
    counts = pm.inbox_counts()
    waiting = sum(counts.values())
    labels = {"prospect": "prospect", "message": "message", "post": "post", "brief": "brief", "task": "task", "note": "note"}
    summary = " · ".join(f"{n} {labels.get(k, k)}" + ("s" if n != 1 else "") for k, n in counts.items())
    inbox = (f'<a class="inbox-banner" href="/inbox"><strong>{waiting} waiting in your inbox</strong>'
             f'<span>{summary}</span><span aria-hidden="true">→</span></a>'
             if waiting else "")
    brief = db.one("""SELECT id, title, body, created_at FROM practice.agent_items
                      WHERE kind = 'brief' AND agent = 'chief' AND status = 'pending' ORDER BY created_at DESC LIMIT 1""")
    brief_html = ""
    if brief:
        from ..ai import render
        brief_html = _card(brief["title"], f'<div class="brief">{render.to_html(brief["body"])}</div>',
                           '<a href="/inbox#brief">Inbox</a>')
    fu = pm.follow_ups(t)
    fu_html = "".join(
        f'<li><div>{_link(r["id"], r["name"])}<div class="meta">{esc(r["next_step"] or "Follow up")}'
        f'{" · " + esc(r["contact_name"]) if r["contact_name"] else ""}</div></div><span>{_due(r["next_step_date"], t)}</span></li>'
        for r in fu) or '<li class="meta">Nothing due in the next 7 days. Add next steps to your prospects so they show up here.</li>'
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    tasks = pm.open_tasks(8)
    task_html = "".join(
        f'<li><form method="post" action="/tasks/{r["id"]}/done" class="inline"><input type="hidden" name="_csrf" value="{token}">'
        f'<button class="tick" type="submit" aria-label="Mark done">✓</button></form>'
        f'<div class="grow">{esc(r["title"])}<div class="meta">{esc(r["category"])}{" · " + esc(r["company"]) if r["company"] else ""}</div></div>'
        f'<span>{_due(r["due_date"], t) if r["due_date"] else ""}</span></li>' for r in tasks) or '<li class="meta">No open tasks.</li>'
    sc = pm.weekly_scorecard(t, weeks=1)
    sc_html = "".join(
        f'<div class="sc-item{" hit" if r["target"] and r["values"][-1] >= r["target"] else ""}"><span>{esc(r["label"])}</span>'
        f'<strong>{money(r["values"][-1], True) if r["key"] == "revenue" else format(r["values"][-1], "g")}</strong>'
        f'<span class="meta">{"target " + format(r["target"], "g") if r["target"] else "this week"}</span></div>' for r in sc["rows"])
    body = f"""{inbox}{QUICK}{goal}
<div class="tiles">{tiles}</div>
<div class="cols">
  <div>{brief_html}
  {_card("Follow-ups (next 7 days)", f'<ul class="list">{fu_html}</ul>', '<a href="/pipeline">Pipeline</a>')}
  {_card("This week so far", f'<div class="sc-strip">{sc_html}</div>', '<a href="/scorecard">Scorecard</a>')}</div>
  <div>{_card("Tasks", f'<ul class="list tasks">{task_html}</ul>', '<a href="/tasks">All tasks</a>')}</div>
</div>"""
    return ui.page(request, "Today", body, "Today", subtitle=f"{ui.date(t)} · week of {ui.short_date(o['week_start'])}")


def scorecard_page(request):
    t = pm.today()
    sc = pm.weekly_scorecard(t, weeks=8)
    head = "".join(f'<th class="n">{ui.short_date(w)}{"<br><span class=muted>so far</span>" if i == len(sc["weeks"]) - 1 else ""}</th>'
                   for i, w in enumerate(sc["weeks"]))
    rows = []
    for r in sc["rows"]:
        cells = []
        for i, v in enumerate(r["values"]):
            last = i == len(r["values"]) - 1
            cls = ("hit" if v >= r["target"] else "miss") if r["target"] and not last else ""
            shown = money(v, True) if r["key"] == "revenue" else format(v, "g")
            cells.append(f'<td class="n {cls}{" partial" if last else ""}">{shown}</td>')
        tgt = f'<span class="goal">Target {format(r["target"], "g")} a week</span>' if r["target"] else ""
        rows.append(f'<tr><th class="sticky measure" scope="row">{esc(r["label"])}{tgt}</th>{"".join(cells)}</tr>')
    o = pm.overview(t)
    body = f"""<section class="card"><p class="muted" style="margin-top:0">The activity that leads to revenue. Green: target hit. Red (✕): missed.
This week is still in progress. Targets are set in the company settings.</p>
<div class="scroll" data-scroll-end><table class="data scorecard"><thead><tr><th class="sticky">Measure</th>{head}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></div></section>
{_card("Where this is heading", f'<p>{money(o["goal_so_far"])} invoiced toward {money(o["goal_amount"])}. Forecast {money(o["goal_forecast"])}. '
       f'You need about {money(o["goal_needed_per_month"])} a month from here.</p>' + ui.how(pm.HOW["forecast"]))}"""
    return ui.page(request, "My scorecard", body, "Today", subtitle="Weeks run Monday to Sunday", wide=True)


# ---------------------------------------------------------------- tasks

CATEGORIES = ["General", "Company setup", "Sales", "Marketing", "Client work", "Systems", "Finance"]


def task_fields():
    return [Field("title", "Task", required=True, wide=True),
            Field("category", "Category", "select", options=[(c, c) for c in CATEGORIES]),
            Field("due_date", "Due", "date"),
            Field("company_id", "Company", "select", options=_companies()),
            Field("notes", "Notes", "textarea")]


def _notes(text):
    return f'<div class="meta pre">{esc(text)}</div>' if text else ""


def tasks_page(request, values=None, errors=None):
    t = pm.today()
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    open_ = pm.open_tasks()
    groups = {}
    for r in open_:
        groups.setdefault(r["category"], []).append(r)
    blocks = []
    for cat in sorted(groups, key=lambda c: (CATEGORIES.index(c) if c in CATEGORIES else 99, c)):
        items = "".join(
            f'<li><form method="post" action="/tasks/{r["id"]}/done" class="inline"><input type="hidden" name="_csrf" value="{token}">'
            f'<button class="tick" type="submit" aria-label="Mark done">✓</button></form>'
            f'<div class="grow">{esc(r["title"])}<div class="meta">{esc(r["company"] or "")}'
            f'{" · by " + esc(r["created_by"]) if r["created_by"] != "noah" else ""}</div>'
            f'{_notes(r["notes"])}</div>'
            f'<span>{_due(r["due_date"], t) if r["due_date"] else ""}</span></li>' for r in groups[cat])
        blocks.append(f'<h3 class="task-group">{esc(cat)} <span class="meta">({len(groups[cat])})</span></h3><ul class="list tasks">{items}</ul>')
    done = db.query("SELECT title, done_at FROM practice.tasks WHERE done_at IS NOT NULL ORDER BY done_at DESC LIMIT 10")
    done_html = "".join(f'<li><div class="grow"><s>{esc(r["title"])}</s></div><span class="meta">{ui.short_date(r["done_at"].date())}</span></li>'
                        for r in done)
    seed = ""
    if not db.one("SELECT 1 AS x FROM practice.tasks WHERE category = 'Company setup' LIMIT 1"):
        seed = (f'<form method="post" action="/tasks/seed" class="inline"><input type="hidden" name="_csrf" value="{token}">'
                f'<button class="btn secondary" type="submit">Add the company launch checklist</button></form>')
    body = f"""<div class="cols">
  <section class="card"><div class="card-head"><h2>Open ({len(open_)})</h2>{seed}</div>{"".join(blocks) or "<p class=meta>Nothing open.</p>"}
  {"<h3 class=task-group>Recently done</h3><ul class=list>" + done_html + "</ul>" if done_html else ""}</section>
  {_card("Add a task", forms.render(request, task_fields(), values, "/tasks", "Add", errors))}
</div>"""
    return ui.page(request, "Tasks", body, "Tasks")


def save_task(request, form):
    data = forms.parse(task_fields(), form)
    data["company_id"] = _int(data["company_id"])
    db.execute("""INSERT INTO practice.tasks (title, category, due_date, company_id, notes)
                  VALUES (%(title)s, %(category)s, %(due_date)s, %(company_id)s, %(notes)s)""", data)


def task_done(tid):
    db.execute("UPDATE practice.tasks SET done_at = now() WHERE id = %(i)s AND done_at IS NULL", {"i": tid})


# ---------------------------------------------------------------- pipeline

def pipeline_page(request):
    t = pm.today()
    rows = db.query("""SELECT id, name, stage, est_value, contact_name, next_step, next_step_date, source, industry
                       FROM practice.companies WHERE NOT archived AND kind = 'prospect'
                       ORDER BY next_step_date NULLS LAST, est_value DESC NULLS LAST""")
    by = {}
    for r in rows:
        by.setdefault(r["stage"], []).append(r)
    stages = pm.pipeline_by_stage()
    cols = []
    for s in stages:
        if s["stage"] in ("won", "lost", "not_now") and not s["count"]:
            continue
        cards = "".join(
            f'<a class="deal-card" href="/companies/{r["id"]}"><strong>{esc(r["name"])}</strong>'
            f'<span class="meta">{esc(r["contact_name"] or r["industry"] or "")}</span>'
            f'<span class="meta">{esc(r["next_step"] or "No next step")}</span>'
            f'<span class="row">{_due(r["next_step_date"], t)}<span class="amt">{money(r["est_value"], True) if r["est_value"] else ""}</span></span></a>'
            for r in by.get(s["stage"], []))
        cols.append(f'<div class="stage-col"><div class="stage-col-head"><strong>{esc(s["label"])}</strong>'
                    f'<span class="meta">{s["count"]} · {money(s["value"], True)}</span></div>{cards or "<p class=meta>None</p>"}</div>')
    src = pm.source_results()
    src_rows = "".join(f'<tr><td>{esc(r["source"])}</td><td class="n">{r["companies"]}</td>'
                       f'<td class="n">{r["reached_conversation"]}</td><td class="n">{r["won"]}</td></tr>' for r in src)
    o = pm.overview()
    body = f"""{QUICK}
<p class="lead">{int(o["pipeline_count"])} open prospects · {money(o["pipeline"], True)} est. value · {money(o["pipeline_weighted"], True)} weighted</p>
<div class="board">{"".join(cols)}</div>
<div class="cols even" style="margin-top:16px">
{_card("What's working", f'<div class="scroll"><table class="data"><thead><tr><th>How we met</th><th class="n">Companies</th><th class="n">Reached a conversation</th><th class="n">Won</th></tr></thead><tbody>{src_rows or "<tr><td colspan=4>Nothing yet.</td></tr>"}</tbody></table></div>' + ui.how("Counts every prospect and client by how you met them, so you can put your hours where the conversations come from."))}
{_card("Everyone else", '<ul class="list"><li><a href="/companies?kind=partner">Referral partners</a></li><li><a href="/companies?kind=client">Clients</a></li><li><a href="/companies?kind=past_client">Past clients</a></li><li><a href="/companies?archived=1">Archived</a></li></ul>')}
</div>{ui.how(pm.HOW["pipeline"])}"""
    return ui.page(request, "Pipeline", body, "Pipeline", subtitle="Prospects by stage. Tap one to log a conversation or move it on.",
                   wide=True)


def companies_page(request):
    kind = request.query_params.get("kind")
    archived = request.query_params.get("archived") == "1"
    if kind not in pm.KINDS:
        kind = None
    rows = db.query("""SELECT id, name, kind, stage, contact_name, contact_email, city, source, next_step_date, updated_at
                       FROM practice.companies WHERE archived = %(a)s AND (%(k)s::text IS NULL OR kind = %(k)s)
                       ORDER BY name""", {"a": archived, "k": kind})
    trs = "".join(f'<tr><td>{_link(r["id"], r["name"])}</td><td>{esc(pm.KINDS[r["kind"]])}</td>'
                  f'<td>{esc(pm.STAGE_LABEL[r["stage"]]) if r["kind"] == "prospect" else ""}</td>'
                  f'<td>{esc(r["contact_name"] or "")}</td><td>{esc(r["city"] or "")}</td><td>{esc(r["source"] or "")}</td></tr>'
                  for r in rows)
    title = "Archived" if archived else (pm.KINDS[kind] + "s" if kind else "All companies")
    body = (f'{QUICK}<section class="card"><div class="scroll"><table class="data"><thead><tr><th>Company</th><th>Type</th>'
            f'<th>Stage</th><th>Contact</th><th>City</th><th>How we met</th></tr></thead><tbody>'
            f'{trs or "<tr><td colspan=6>None yet.</td></tr>"}</tbody></table></div>'
            f'<p><a class="btn secondary" href="/export/companies.csv">Download all for Excel</a></p></section>')
    return ui.page(request, title, body, "Pipeline")


# ---------------------------------------------------------------- one company

def company_form_page(request, cid=None, values=None, errors=None):
    if cid and values is None:
        values = db.one("SELECT * FROM practice.companies WHERE id = %(i)s", {"i": cid})
        if not values:
            return None
        values = {k: (str(v) if k == "referred_by" and v else v) for k, v in values.items()}
    action = f"/companies/{cid}/edit" if cid else "/companies/new"
    form = forms.render(request, company_fields(), values, action, "Save", errors)
    title = f"Edit {values.get('name')}" if cid and values else "New company"
    return ui.page(request, title, f'<section class="card">{form}</section>', "Pipeline")


def save_company(request, form, cid=None):
    data = forms.parse(company_fields(), form)
    data["referred_by"] = _int(data["referred_by"])
    if data["kind"] == "client" and data["stage"] in pm.OPEN_STAGES:
        data["stage"] = "won"
    cols = list(data)
    if cid:
        db.execute(f"UPDATE practice.companies SET {', '.join(f'{c} = %({c})s' for c in cols)}, updated_at = now() "
                   "WHERE id = %(id)s", {**data, "id": cid})
        return cid
    with db.connect() as conn:
        row = db.one(f"INSERT INTO practice.companies ({', '.join(cols)}) VALUES ({', '.join(f'%({c})s' for c in cols)}) "
                     "RETURNING id", data, conn)
    return row["id"]


def company_page(request, cid, activity_values=None, errors=None):
    c = db.one("""SELECT c.*, p.name AS referrer FROM practice.companies c
                  LEFT JOIN practice.companies p ON p.id = c.referred_by WHERE c.id = %(i)s""", {"i": cid})
    if not c:
        return None
    t = pm.today()
    facts = [("Type", pm.KINDS[c["kind"]]), ("Stage", pm.STAGE_LABEL[c["stage"]] if c["kind"] == "prospect" else None),
             ("Contact", " · ".join(x for x in (c["contact_name"], c["contact_title"]) if x) or None),
             ("Email", c["contact_email"]), ("Phone", c["contact_phone"]), ("Industry", c["industry"]),
             ("Size", c["size_note"]), ("City", c["city"]), ("How we met", c["source"]), ("Referred by", c["referrer"]),
             ("Est. first-year value", money(c["est_value"]) if c["est_value"] else None)]
    kv = "".join(f"<dt>{esc(k)}</dt><dd>{esc(v)}</dd>" for k, v in facts if v)
    if c["website"]:
        kv += f'<dt>Website</dt><dd><a href="{esc(c["website"])}" target="_blank" rel="noopener">{esc(c["website"])}</a></dd>'
    if c["contact_email"]:
        kv = kv.replace(f"<dd>{esc(c['contact_email'])}</dd>",
                        f'<dd><a href="mailto:{esc(c["contact_email"])}">{esc(c["contact_email"])}</a></dd>', 1)
    next_step = (f'<p class="next-step"><strong>Next step:</strong> {esc(c["next_step"] or "none set")} '
                 f'{_due(c["next_step_date"], t)}</p>')
    acts = db.query("SELECT * FROM practice.activities WHERE company_id = %(i)s ORDER BY happened_on DESC, id DESC", {"i": cid})
    acts_html = "".join(
        f'<li><div><strong>{esc(pm.ACTIVITY_KINDS[a["kind"]])}</strong> · {ui.short_date(a["happened_on"])}'
        f'<div class="meta pre">{esc(a["summary"])}</div></div></li>' for a in acts) or '<li class="meta">Nothing logged yet.</li>'
    act_form = forms.render(request, activity_fields(), activity_values, f"/companies/{cid}/activities", "Log it", errors)
    engs = db.query("""SELECT e.*, coalesce((SELECT sum(hours) FROM practice.time_entries te WHERE te.engagement_id = e.id), 0) AS hours_used
                       FROM practice.engagements e WHERE company_id = %(i)s ORDER BY created_at DESC""", {"i": cid})
    eng_html = "".join(
        f'<li><div><a href="/engagements/{e["id"]}/edit">{esc(e["name"])}</a><div class="meta">{esc(pm.OFFERS[e["offer"]])} · '
        f'{esc(e["status"])}{" · " + money(e["price"]) if e["price"] else ""}{" · " + money(e["monthly_fee"]) + "/mo" if e["monthly_fee"] else ""}</div></div>'
        f'<span class="amt">{float(e["hours_used"]):g} h</span></li>' for e in engs) or '<li class="meta">None yet.</li>'
    invs = db.query("SELECT * FROM practice.invoices WHERE company_id = %(i)s ORDER BY issued_date DESC", {"i": cid})
    inv_html = "".join(
        f'<li><div>{esc(i["number"])}<div class="meta">{ui.short_date(i["issued_date"])} · '
        f'{"paid " + ui.short_date(i["paid_date"]) if i["paid_date"] else "due " + ui.short_date(i["due_date"])}</div></div>'
        f'<span class="amt">{money(i["amount"])}</span></li>' for i in invs) or '<li class="meta">None yet.</li>'
    archive_label = "Restore" if c["archived"] else "Archive"
    archive = (f'<form method="post" action="/companies/{cid}/archive" class="inline" '
               f'onsubmit="return confirm(\'{archive_label} this company?\')">'
               f'<input type="hidden" name="_csrf" value="{forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))}">'
               f'<button class="btn ghost" type="submit">{archive_label}</button></form>')
    notes = f'<h3 style="margin-top:14px">Notes</h3><p class="pre">{esc(c["notes"])}</p>' if c["notes"] else ""
    body = f"""<div class="quick"><a class="btn secondary" href="/companies/{cid}/edit">Edit details</a>
<a class="btn secondary" href="/engagements/new?company={cid}">+ Engagement</a>{archive}</div>
<div class="cols">
  <div>{_card("Log a conversation or note", next_step + act_form)}
  {_card("History", f'<ul class="list">{acts_html}</ul>')}</div>
  <div>{_card("Details", f'<dl class="kv">{kv}</dl>{notes}')}
  {_card("Engagements", f'<ul class="list">{eng_html}</ul>')}
  {_card("Invoices", f'<ul class="list">{inv_html}</ul>', '<a href="/money#invoice">+ Invoice</a>')}</div>
</div>"""
    sub = pm.KINDS[c["kind"]] + (" · " + pm.STAGE_LABEL[c["stage"]] if c["kind"] == "prospect" else "")
    return ui.page(request, c["name"] + (" (archived)" if c["archived"] else ""), body, "Pipeline", subtitle=esc(sub))


def save_activity(request, form, cid):
    data = forms.parse(activity_fields(), form)
    with db.connect() as conn:
        db.execute("""INSERT INTO practice.activities (company_id, happened_on, kind, summary)
                      VALUES (%(c)s, %(d)s, %(k)s, %(s)s)""",
                   {"c": cid, "d": data["happened_on"], "k": data["kind"], "s": data["summary"]}, conn)
        sets, p = ["updated_at = now()"], {"c": cid}
        if data["next_step"] or data["next_step_date"]:
            sets += ["next_step = %(ns)s", "next_step_date = %(nd)s"]
            p.update(ns=data["next_step"], nd=data["next_step_date"])
        if data["stage"]:
            sets.append("stage = %(st)s")
            p["st"] = data["stage"]
            if data["stage"] == "won":
                sets.append("kind = CASE WHEN kind = 'prospect' THEN 'client' ELSE kind END")
        db.execute(f"UPDATE practice.companies SET {', '.join(sets)} WHERE id = %(c)s", p, conn)


def toggle_archive(cid):
    db.execute("UPDATE practice.companies SET archived = NOT archived, updated_at = now() WHERE id = %(i)s", {"i": cid})


# ---------------------------------------------------------------- engagements

def engagement_form_page(request, eid=None, company_id=None, values=None, errors=None):
    if eid and values is None:
        values = db.one("SELECT * FROM practice.engagements WHERE id = %(i)s", {"i": eid})
        if not values:
            return None
        values["company_id"] = str(values["company_id"])
    action = f"/engagements/{eid}/edit" if eid else "/engagements/new"
    form = forms.render(request, engagement_fields(str(company_id) if company_id else None), values, action, "Save", errors)
    return ui.page(request, "Edit engagement" if eid else "New engagement", f'<section class="card">{form}</section>', "Clients")


def save_engagement(request, form, eid=None):
    data = forms.parse(engagement_fields(), form)
    data["company_id"] = _int(data["company_id"])
    cols = list(data)
    with db.connect() as conn:
        if eid:
            db.execute(f"UPDATE practice.engagements SET {', '.join(f'{c} = %({c})s' for c in cols)}, updated_at = now() "
                       "WHERE id = %(id)s", {**data, "id": eid}, conn)
        else:
            db.execute(f"INSERT INTO practice.engagements ({', '.join(cols)}) VALUES ({', '.join(f'%({c})s' for c in cols)})",
                       data, conn)
        if data["status"] == "active":  # an active engagement makes the company a client
            db.execute("""UPDATE practice.companies SET kind = 'client', stage = 'won', updated_at = now()
                          WHERE id = %(c)s AND kind IN ('prospect', 'past_client')""", {"c": data["company_id"]}, conn)
    return data["company_id"]


# ---------------------------------------------------------------- clients

def clients_page(request):
    t = pm.today()
    ms = t.replace(day=1)
    rows = db.query("""
        SELECT c.id, c.name, c.contact_name,
               coalesce((SELECT sum(monthly_fee) FROM practice.engagements e WHERE e.company_id = c.id AND e.offer = 'retainer'
                         AND e.status = 'active'), 0) AS mrr,
               coalesce((SELECT sum(hours) FROM practice.time_entries te WHERE te.company_id = c.id AND te.work_date >= %(ms)s), 0) AS hours_month,
               coalesce((SELECT sum(amount) FROM practice.invoices i WHERE i.company_id = c.id), 0) AS billed_total,
               coalesce((SELECT sum(amount) FROM practice.invoices i WHERE i.company_id = c.id AND i.paid_date IS NULL), 0) AS unpaid
        FROM practice.companies c WHERE NOT c.archived AND c.kind = 'client' ORDER BY c.name""", {"ms": ms})
    trs = "".join(f'<tr><td>{_link(r["id"], r["name"])}</td><td>{esc(r["contact_name"] or "")}</td>'
                  f'<td class="n">{money(r["mrr"])}</td><td class="n">{float(r["hours_month"]):g}</td>'
                  f'<td class="n">{money(r["billed_total"])}</td><td class="n">{money(r["unpaid"])}</td></tr>' for r in rows)
    engs = pm.engagements_with_hours(("proposed", "active"))
    etrs = "".join(
        f'<tr><td><a href="/engagements/{e["id"]}/edit">{esc(e["name"])}</a></td><td>{_link(e["company_id"], e["company_name"])}</td>'
        f'<td>{esc(pm.OFFERS[e["offer"]])}</td><td>{esc(e["status"])}</td>'
        f'<td class="n">{money(e["price"]) if e["price"] else (money(e["monthly_fee"]) + "/mo" if e["monthly_fee"] else "—")}</td>'
        f'<td class="n">{float(e["hours_used"]):g}{" / " + format(float(e["hours_budget"]), "g") if e["hours_budget"] else ""}</td>'
        f'<td class="n">{money(e["invoiced"])}</td></tr>' for e in engs)
    fees = pm.referral_fees()
    frows = "".join(f'<tr><td>{_link(r["id"], r["partner"])}</td><td>{_link(r["client_id"], r["client"])}</td>'
                    f'<td class="n">{money(r["first_year"])}</td><td class="n">{money(r["fee"])}</td></tr>' for r in fees)
    partners = db.query("""SELECT p.id, p.name, p.contact_name, count(c.id) AS intros
                           FROM practice.companies p LEFT JOIN practice.companies c ON c.referred_by = p.id
                           WHERE p.kind = 'partner' AND NOT p.archived GROUP BY 1, 2, 3 ORDER BY 4 DESC, 2""")
    prows = "".join(f'<li><div>{_link(r["id"], r["name"])}<div class="meta">{esc(r["contact_name"] or "")}</div></div>'
                    f'<span class="amt">{r["intros"]} intro{"s" if r["intros"] != 1 else ""}</span></li>' for r in partners)
    partner_html = _card("Referral partners", f'<ul class="list">{prows or "<li class=meta>No partners yet. Add one as a company of type Referral partner.</li>"}</ul>'
                         + (f'<h3 style="margin-top:14px">Referral fees</h3><div class="scroll"><table class="data"><thead><tr><th>Partner</th><th>Client</th>'
                            f'<th class="n">First-year invoices</th><th class="n">Fee</th></tr></thead><tbody>{frows}</tbody></table></div>' if frows else "")
                         + ui.how(pm.HOW["referral_fees"]))
    body = f"""<div class="quick"><a class="btn" href="/engagements/new">+ Engagement</a></div>
{_card("Clients", f'<div class="scroll"><table class="data"><thead><tr><th>Client</th><th>Contact</th><th class="n">Monthly</th><th class="n">Hours this month</th><th class="n">Billed to date</th><th class="n">Unpaid</th></tr></thead><tbody>{trs or "<tr><td colspan=6>No clients yet. Your first one goes here.</td></tr>"}</tbody></table></div>')}
{partner_html}
{_card("Open engagements", f'<div class="scroll"><table class="data"><thead><tr><th>Engagement</th><th>Client</th><th>Offer</th><th>Status</th><th class="n">Price</th><th class="n">Hours (used / budget)</th><th class="n">Invoiced</th></tr></thead><tbody>{etrs or "<tr><td colspan=7>None yet.</td></tr>"}</tbody></table></div>')}"""
    return ui.page(request, "Clients", body, "Clients")


# ---------------------------------------------------------------- time

def time_page(request, values=None, errors=None):
    t = pm.today()
    ws = t - dt.timedelta(days=t.weekday())
    days = [ws + dt.timedelta(days=i) for i in range(7)]
    per_day = {r["work_date"]: float(r["h"]) for r in db.query(
        "SELECT work_date, sum(hours) AS h FROM practice.time_entries WHERE work_date BETWEEN %(s)s AND %(e)s GROUP BY 1",
        {"s": ws, "e": ws + dt.timedelta(days=6)})}
    target = float(pm.settings()["weekly_hours_target"])
    total = sum(per_day.values())
    week = "".join(f'<div class="day{" today" if d == t else ""}"><span>{d.strftime("%a")}</span><strong>{per_day.get(d, 0):g}</strong></div>'
                   for d in days)
    entries = db.query("""SELECT t.*, c.name AS company, e.name AS engagement FROM practice.time_entries t
                          LEFT JOIN practice.companies c ON c.id = t.company_id
                          LEFT JOIN practice.engagements e ON e.id = t.engagement_id
                          ORDER BY t.work_date DESC, t.id DESC LIMIT 40""")
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    trs = "".join(
        f'<tr><td class="n">{ui.short_date(r["work_date"])}</td><td>{esc(r["company"] or "Running the business")}</td>'
        f'<td>{esc(r["engagement"] or "")}</td><td class="n">{float(r["hours"]):g}</td><td>{"Yes" if r["billable"] else "No"}</td>'
        f'<td class="wrap">{esc(r["note"] or "")}</td><td><form method="post" action="/time/{r["id"]}/delete" class="inline" '
        f'onsubmit="return confirm(\'Delete this entry?\')"><input type="hidden" name="_csrf" value="{token}">'
        f'<button class="linkish" type="submit">Delete</button></form></td></tr>' for r in entries)
    by_co = pm.hours_by_company(t.replace(day=1), t)
    co_rows = "".join(f'<tr><td>{esc(r["company"])}</td><td class="n">{float(r["hours"]):g}</td>'
                      f'<td class="n">{float(r["billable"] or 0):g}</td></tr>' for r in by_co)
    body = f"""<section class="card"><div class="card-head"><h2>This week: {total:g} of {target:g} hours</h2></div>
<div class="week">{week}</div><div class="meter"><i style="width:{min(100, 100 * total / target if target else 0):.0f}%"></i></div></section>
<div class="cols">
  {_card("Log time", forms.render(request, time_fields(), values, "/time", "Add", errors)).replace('<section class="card">', '<section class="card" id="add">', 1)}
  {_card("This month by company", f'<div class="scroll"><table class="data"><thead><tr><th>For</th><th class="n">Hours</th><th class="n">Billable</th></tr></thead><tbody>{co_rows or "<tr><td colspan=3>Nothing yet.</td></tr>"}</tbody></table></div>')}
</div>
{_card("Recent entries", f'<div class="scroll"><table class="data"><thead><tr><th class="n">Date</th><th>For</th><th>Engagement</th><th class="n">Hours</th><th>Billable</th><th>Note</th><th></th></tr></thead><tbody>{trs or "<tr><td colspan=7>No time logged yet.</td></tr>"}</tbody></table></div><p><a class="btn secondary" href="/export/time.csv">Download for Excel</a></p>')}"""
    return ui.page(request, "Time", body, "Time", subtitle="Your 20 hours a week, and where they go")


def save_time(request, form):
    data = forms.parse(time_fields(), form)
    data["company_id"], data["engagement_id"] = _int(data["company_id"]), _int(data["engagement_id"])
    if data["engagement_id"] and not data["company_id"]:
        data["company_id"] = db.one("SELECT company_id FROM practice.engagements WHERE id = %(e)s",
                                    {"e": data["engagement_id"]})["company_id"]
    if data["hours"] is not None and data["hours"] > 24:
        raise FormError({"hours": "Hours must be 24 or less."})
    db.execute("""INSERT INTO practice.time_entries (work_date, hours, company_id, engagement_id, billable, note)
                  VALUES (%(work_date)s, %(hours)s, %(company_id)s, %(engagement_id)s, %(billable)s, %(note)s)""", data)


def delete_time(tid):
    db.execute("DELETE FROM practice.time_entries WHERE id = %(i)s", {"i": tid})


# ---------------------------------------------------------------- money

def money_page(request, inv_values=None, inv_errors=None, exp_values=None, exp_errors=None):
    t = pm.today()
    o = pm.overview(t)
    mm = pm.monthly_money(t.year)
    months = [calendar.month_abbr[m] for m in range(1, 13)]
    cum, run = [], 0.0
    for m, v in enumerate(mm["revenue"], start=1):
        run += v
        cum.append(run if m <= t.month else None)
    chart = ui.chart("rev", {"type": "line", "format": "money", "labels": months, "datasets": [
        {"label": "Revenue, cumulative", "data": cum, "color": "--series-1"},
        {"label": "Goal pace", "data": [o["goal"] * m / 12 for m in range(1, 13)], "color": "--axis", "points": False, "dash": True}]},
        height=220, label="Revenue against goal")
    bars = ui.chart("mo", {"type": "bar", "format": "money", "labels": months, "datasets": [
        {"label": "Revenue", "data": mm["revenue"], "color": "--series-1"},
        {"label": "Expenses", "data": mm["expenses"], "color": "--series-2"}]}, height=220, label="Revenue and expenses by month")
    tiles = "".join([
        ui.tile("Revenue this year", money(o["revenue_ytd"], True), f'goal {money(o["goal"], True)}', None, pm.HOW["revenue"]),
        ui.tile("Cash collected", money(o["cash_ytd"], True), "this year", None, pm.HOW["cash"]),
        ui.tile("Expenses", money(o["expenses_ytd"], True), "this year"),
        ui.tile("Profit", money(o["profit_ytd"], True), "revenue − expenses", None, pm.HOW["profit"]),
        ui.tile("Effective hourly rate", money(o["effective_rate"]) if o["effective_rate"] else "—", "revenue ÷ all hours",
                None, pm.HOW["effective_rate"]),
    ])
    token = forms.auth.csrf_token(request.cookies.get(forms.auth.COOKIE))
    invs = db.query("""SELECT i.*, c.name AS company FROM practice.invoices i JOIN practice.companies c ON c.id = i.company_id
                       ORDER BY (i.paid_date IS NULL) DESC, i.issued_date DESC LIMIT 50""")
    inv_rows = "".join(
        f'<tr><td>{esc(r["number"])}</td><td>{_link(r["company_id"], r["company"])}</td><td class="n">{ui.short_date(r["issued_date"])}</td>'
        f'<td class="n">{money(r["amount"])}</td><td>'
        + (f'Paid {ui.short_date(r["paid_date"])}' if r["paid_date"] else
           f'{_due(r["due_date"], t) if r["due_date"] < t else "Due " + ui.short_date(r["due_date"])} '
           f'<form method="post" action="/invoices/{r["id"]}/paid" class="inline"><input type="hidden" name="_csrf" value="{token}">'
           f'<button class="linkish" type="submit">Mark paid today</button></form>')
        + "</td></tr>" for r in invs)
    exps = db.query("SELECT * FROM practice.expenses ORDER BY spent_date DESC, id DESC LIMIT 30")
    exp_rows = "".join(
        f'<tr><td class="n">{ui.short_date(r["spent_date"])}</td><td>{esc(r["category"])}</td><td>{esc(r["vendor"] or "")}</td>'
        f'<td class="n">{money(r["amount"])}</td><td><form method="post" action="/expenses/{r["id"]}/delete" class="inline" '
        f'onsubmit="return confirm(\'Delete this expense?\')"><input type="hidden" name="_csrf" value="{token}">'
        f'<button class="linkish" type="submit">Delete</button></form></td></tr>' for r in exps)
    inv_form = forms.render(request, invoice_fields(), inv_values, "/invoices/new", "Add invoice", inv_errors)
    exp_form = forms.render(request, expense_fields(), exp_values, "/expenses/new", "Add expense", exp_errors)
    body = f"""<div class="tiles">{tiles}</div>
<div class="cols even">
  {_card("Revenue against goal", chart)}
  <section class="card"><div class="card-head"><h2>By month</h2><div class="legend"><span><i style="background:var(--series-1)"></i>Revenue</span><span><i style="background:var(--series-2)"></i>Expenses</span></div></div>{bars}</section>
</div>
{_card("Invoices", f'<div class="scroll"><table class="data"><thead><tr><th>No.</th><th>Client</th><th class="n">Issued</th><th class="n">Amount</th><th>Status</th></tr></thead><tbody>{inv_rows or "<tr><td colspan=5>No invoices yet.</td></tr>"}</tbody></table></div>')}
<div class="cols even">
  <section class="card" id="invoice"><h2>Add an invoice</h2><p class="meta">Records invoices you send from your accounting or invoicing tool, so revenue shows up here.</p>{inv_form}</section>
  <section class="card" id="expense"><h2>Add an expense</h2>{exp_form}
  <div class="scroll" style="margin-top:14px"><table class="data"><thead><tr><th class="n">Date</th><th>Category</th><th>Vendor</th><th class="n">Amount</th><th></th></tr></thead><tbody>{exp_rows or "<tr><td colspan=5>None yet.</td></tr>"}</tbody></table></div></section>
</div>"""
    return ui.page(request, "Money", body, "Money", subtitle=f"{t.year} so far")


def save_invoice(request, form):
    data = forms.parse(invoice_fields(), form)
    data["company_id"], data["engagement_id"] = _int(data["company_id"]), _int(data["engagement_id"])
    if data["due_date"] < data["issued_date"]:
        raise FormError({"due_date": "Due date can't be before the issue date."})
    if db.one("SELECT 1 AS x FROM practice.invoices WHERE number = %(n)s", {"n": data["number"]}):
        raise FormError({"number": "That invoice number is already used."})
    db.execute("""INSERT INTO practice.invoices (company_id, engagement_id, number, issued_date, due_date, amount, paid_date, note)
                  VALUES (%(company_id)s, %(engagement_id)s, %(number)s, %(issued_date)s, %(due_date)s, %(amount)s,
                          %(paid_date)s, %(note)s)""", data)


def mark_paid(iid):
    db.execute("UPDATE practice.invoices SET paid_date = core.local_today() WHERE id = %(i)s AND paid_date IS NULL", {"i": iid})


def save_expense(request, form):
    data = forms.parse(expense_fields(), form)
    db.execute("""INSERT INTO practice.expenses (spent_date, category, vendor, amount, note)
                  VALUES (%(spent_date)s, %(category)s, %(vendor)s, %(amount)s, %(note)s)""", data)


def delete_expense(xid):
    db.execute("DELETE FROM practice.expenses WHERE id = %(i)s", {"i": xid})


# ---------------------------------------------------------------- export

EXPORTS = {
    "companies": "SELECT id, name, kind, stage, contact_name, contact_title, contact_email, contact_phone, industry, size_note, "
                 "city, website, source, est_value, next_step, next_step_date, notes, archived, created_at FROM practice.companies ORDER BY name",
    "time": "SELECT t.work_date, coalesce(c.name, 'Running the business') AS company, e.name AS engagement, t.hours, t.billable, t.note "
            "FROM practice.time_entries t LEFT JOIN practice.companies c ON c.id = t.company_id "
            "LEFT JOIN practice.engagements e ON e.id = t.engagement_id ORDER BY t.work_date",
    "invoices": "SELECT i.number, c.name AS client, i.issued_date, i.due_date, i.amount, i.paid_date, i.note "
                "FROM practice.invoices i JOIN practice.companies c ON c.id = i.company_id ORDER BY i.issued_date",
    "expenses": "SELECT spent_date, category, vendor, amount, note FROM practice.expenses ORDER BY spent_date",
}


def export_csv(name):
    import csv
    import io
    from ..hub.pages import _csv_safe
    rows = db.query(EXPORTS[name])
    out = io.StringIO()
    w = csv.writer(out)
    if rows:
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow([_csv_safe(v) for v in r.values()])
    return out.getvalue()
