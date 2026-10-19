"""Alerts, Agents and Forecast pages for the reporting hub. The facts come from kit/watch.py."""
import datetime as dt

from .. import metrics, watch
from ..config import get_settings
from . import auth, ui
from .ui import esc, money

SEV = {"critical": ("bad", "!"), "warning": ("warn", "!"), "good": ("good", "✓")}


def _scope(request):
    return request.state.user["branches"] or None


def _is_guest(request) -> bool:
    return request.state.user["email"].endswith("@demo.invalid")


def _record(a: dict) -> str:
    for key, kind in (("job_id", "fsm_job"), ("item_id", "inv_item"), ("employee_id", "hr_employee"), ("po_id", "ap_po")):
        if a.get(key):
            return ui.source_link(kind, a[key], a["title"])
    if a.get("deal_id"):
        return ui.source_link("crm_deal", a["deal_id"], a["title"])
    if a.get("invoice_id"):
        return ui.source_link("accounting_invoice", a["invoice_id"], a["title"])
    if a.get("branch"):
        return f'<a href="{esc(metrics.invoices_link(branch=a["branch"]))}">{esc(a["title"])}</a>'
    return esc(a["title"])


# ---------------------------------------------------------------- Alerts

def alerts_page(request) -> str:
    t, scope = metrics.today(), _scope(request)
    found = watch.alerts(t, scope, days=7)
    r = watch.rules()
    rows = "".join(
        f'<li class="alert-row"><span class="pill {SEV[a["severity"]][0]}"><span aria-hidden="true">{SEV[a["severity"]][1]}</span> {esc(a["kind"])}</span>'
        f'<div><strong>{_record(a)}</strong><div class="meta">{esc(a["detail"])}</div></div>'
        f'<div class="alert-side"><strong>{money(a["amount"], True) if a.get("amount") else ""}</strong>'
        f'<div class="meta">{ui.date(a["date"])}</div></div></li>' for a in found)
    late = " and ".join(f"{n}" for n in r["late_days"])
    rule_rows = [("Deal slipped", f"An open deal of {money(r['slipped_min'], True)} or more is pushed to a later month."),
                 ("Big win / big loss", f"A deal of {money(r['big_win'], True)}+ is won, or {money(r['big_loss'], True)}+ is lost."),
                 ("Invoice late", f"An unpaid invoice passes {late} days past due ({r['late_days'][-1]} is urgent)."),
                 ("Billing behind pace", f"A branch has billed under {r['billing_pace']:.0%} of last year's figure for the month so far.")]
    apps = get_settings().apps
    if "field_service" in apps:
        rule_rows.append(("Emergency call late", f"A technician reaches an emergency call {r['emergency_late_hours']} or more hours after it came in."))
    if "inventory" in apps:
        rule_rows.append(("Out of stock", "A critical part runs out at a warehouse (urgent)."))
    if "purchasing" in apps:
        rule_rows.append(("Delivery late", f"An open purchase order of {money(r['late_po_min'], True)} or more passes its expected date."))
    if "people" in apps:
        rule_rows += [("License expiring", f"A license or certification runs out within {r['license_days']} days; expired is urgent."),
                      ("Overtime high", f"A branch's overtime goes above {r['overtime_pct']:.0%} of hours worked in a week.")]
    rules_html = "".join(f"<tr><th scope=row>{esc(k)}</th><td>{esc(v)}</td></tr>" for k, v in rule_rows)
    kinds = {}
    for a in found:
        k = kinds.setdefault(a["kind"], {"n": 0, "amount": 0.0, "severity": a["severity"]})
        k["n"] += 1
        k["amount"] += float(a.get("amount") or 0)
    kind_tiles = "".join(
        ui.tile(k, f'{v["n"]}', f'{money(v["amount"], True)} involved' if v["amount"] else "this week")
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1]["n"]))
    body = f"""
{f'<div class="tiles alert-kinds">{kind_tiles}</div>' if kind_tiles else ""}
<div class="cols top">
  <section class="card"><div class="card-head"><h2>This week</h2><span class="muted">{len(found)} alert{"s" if len(found) != 1 else ""}</span></div>
    <ul class="list alert-list">{rows or '<li>Nothing has crossed a line this week.</li>'}</ul>
    {ui.how("Each alert goes to the person who owns it, by email, Teams or a phone notification, the moment it happens. Every one links to the record behind it.")}</section>
  <section class="card"><h2>The rules</h2>
    <p class="muted">Set with each client and changed any time. These are the demo's.</p>
    <table class="data rules">{rules_html}</table></section>
</div>"""
    return ui.page(request, "Alerts", body, "Alerts", subtitle="What would have reached a leader's phone or inbox in the last 7 days")


# ---------------------------------------------------------------- Agents

def agents_page(request) -> str:
    t, scope = metrics.today(), _scope(request)
    brief = watch.daily_brief(t, scope)
    drafts = watch.followup_drafts(t, scope)
    update = watch.weekly_update(t, scope)
    prep = watch.meeting_prep(t, scope)
    note = ("In a live install, AI agents write these from your data each morning and hand them to the right person. "
            "In this demo they're prepared from Bluestem's data by the same rules, so you can see the shape of the work."
            if get_settings().is_demo else
            "Prepared from your data by rules. With the AI agents switched on, they write these each morning.")
    brief_html = ""
    for line in brief:
        link = f' <a href="{esc(line["link"])}">See it</a>' if line.get("link") else ""
        brief_html += f"<li>{esc(line['text'])}{link}</li>"
    send = ('<button type="button" class="btn" disabled title="Switched off in the demo: nothing is ever sent from here">Approve and send</button>')
    draft_html = "".join(
        f'<article class="draft"><div><strong>{esc(d["subject"])}</strong>'
        f'<div class="meta">To {esc(d["to"])} · {esc(d["branch"])} · {money(d["amount"], True)}, {d["days"]} days late · '
        f'{ui.source_link("accounting_invoice", d["invoice_id"], "invoice")}</div></div>'
        f'<div class="pre" data-copy>{esc(d["body"])}</div>'
        f'<div class="form-actions">{send} <button type="button" class="btn secondary" data-copy-btn>Copy text</button></div></article>'
        for d in drafts)
    prep_html = ""
    if prep:
        d, h, ar = prep["deal"], prep["history"], prep["ar"]
        ch = "".join(f'<li>{ui.date(c["changed_date"])}: {esc(c["field"])} {esc(c["old_value"] or "—")} → {esc(c["new_value"] or "—")}</li>'
                     for c in prep["changes"]) or "<li>No changes recorded.</li>"
        qs = "".join(f"<li>{esc(q)}</li>" for q in prep["questions"])
        prep_html = f"""<section class="card"><div class="card-head"><h2>Meeting prep</h2><span class="muted">Biggest deal closing in the next 3 weeks</span></div>
  <div class="prep"><div>
    <h3>{ui.source_link("crm_deal", d["id"], d["name"])}</h3>
    <p class="meta">{esc(d["branch"])} · {esc(d["owner_name"])} · {esc(d["stage"])} ({d["probability"]:.0f}%) · closes {ui.date(d["close_date"])} · {money(d["amount"], True)}</p>
    <div class="facts"><div><span>Account since</span><strong>{ui.date(h["first_seen"])}</strong></div>
      <div><span>Won with them</span><strong>{h["won_n"]} deals · {money(h["won_amt"], True)}</strong></div>
      <div><span>Lost</span><strong>{h["lost_n"]}</strong></div><div><span>Other open deals</span><strong>{max(h["open_n"] - 1, 0)}</strong></div>
      <div><span>Unpaid invoices</span><strong>{money(ar["unpaid"], True)}{f' · oldest {ar["oldest"]} days late' if ar["oldest"] else ""}</strong></div></div></div>
    <div><h4>Recent changes</h4><ul class="list compact">{ch}</ul></div>
    <div><h4>Questions to ask</h4><ul class="list compact">{qs}</ul></div></div></section>"""
    paras = "".join(f"<p>{esc(p)}</p>" for p in update["paragraphs"])
    body = f"""
<p class="lead agents-note">{esc(note)}</p>
<div class="cols even">
  <section class="card brief"><div class="card-head"><h2>Daily brief</h2><span class="muted">For the COO · prepared 6:30 AM</span></div>
    <ul class="list">{brief_html}</ul></section>
  <section class="card"><div class="card-head"><h2>{esc(update["title"])}</h2><span class="muted">Draft for review</span></div>
    <div data-copy>{paras}</div>
    <div class="form-actions"><button type="button" class="btn secondary" data-copy-btn>Copy text</button></div></section>
</div>
<section class="card"><div class="card-head"><h2>Waiting for approval</h2><span class="muted">{len(drafts)} payment reminder{"" if len(drafts) == 1 else "s"} · agents prepare the work, a person approves anything that goes out</span></div>
  {f'<div class="drafts">{draft_html}</div>' if draft_html else '<p>Nothing waiting.</p>'}</section>
{prep_html}"""
    return ui.page(request, "AI agents", body, "AI agents", subtitle="What the AI agents prepared this morning")


# ---------------------------------------------------------------- Forecast

def forecast_page(request, saved: int | None = None) -> str:
    t, scope = metrics.today(), _scope(request)
    f = watch.forecast(t, scope)
    can_save = request.state.user["role"] == "admin" and not _is_guest(request)
    token = auth.csrf_token(request.cookies.get(auth.COOKIE))
    opts = lambda cur: "".join(f'<option value="{k}"{" selected" if k == cur else ""}>{esc(v)}</option>' for k, v in watch.CALLS.items())
    rows = "".join(
        f'<tr data-amount="{float(d["amount"] or 0):.2f}"><td>{ui.source_link("crm_deal", d["id"], d["name"])}<div class="meta">{esc(d["owner_name"])}</div></td>'
        f'<td>{esc(d["branch"])}</td><td>{esc(d["stage"])}</td><td class="n">{d["probability"]:.0f}%</td>'
        f'<td class="n">{ui.short_date(d["close_date"])}</td><td class="n">{money(d["amount"])}</td>'
        f'<td><label class="sr" for="c-{esc(d["id"])}">Call for {esc(d["name"])}</label>'
        f'<select id="c-{esc(d["id"])}" name="call:{esc(d["id"])}" data-call>{opts(d["call"])}</select></td></tr>'
        for d in f["deals"])
    q = f'{ui.date(f["quarter_start"])} to {ui.date(f["quarter_end"])}'
    tiles = "".join([
        ui.tile("Booked so far this quarter", money(f["booked"], True), "Won deals, from the CRM"),
        f'<div class="tile"><div class="tile-label">Commit forecast</div><div class="tile-value" data-total="commit" data-booked="{f["booked"]:.2f}">{money(f["commit"], True)}</div><div class="tile-sub">Booked + deals called Commit</div></div>',
        f'<div class="tile"><div class="tile-label">Best case</div><div class="tile-value" data-total="best">{money(f["best"], True)}</div><div class="tile-sub">Commit + Best case</div></div>',
        ui.tile("Open deals closing this quarter", money(f["open_total"], True), f'{len(f["deals"])} deals'),
    ])
    if can_save:
        action = '<button type="submit" class="btn">Save calls</button>'
        hint = "Changes are saved for everyone, with who changed what."
    else:
        action = '<button type="submit" class="btn" disabled>Save calls</button>'
        hint = ("Try changing a few calls: the totals update as you go. In the demo nothing is saved; in a live hub "
                "the sales leader's calls are saved and everyone sees the same numbers." if _is_guest(request)
                else "Only admins can save calls. You can still try changes: the totals update as you go.")
    done = f'<p class="pill good">Saved {saved} call{"s" if saved != 1 else ""}.</p>' if saved is not None else ""
    total = float(f["booked"]) + float(f["open_total"] or 0)
    w = lambda v: f"{100 * float(v) / total:.1f}%" if total else "0%"
    commit_open, best_open = float(f["commit"]) - float(f["booked"]), float(f["best"]) - float(f["commit"])
    fbar = f"""<section class="card"><div class="card-head"><h2>How the quarter adds up</h2>
  <span class="muted">Out of {money(total, True)}: booked plus every open deal closing this quarter</span></div>
  <div class="fbar" data-fbar data-total="{total:.2f}" role="img" aria-label="Booked, commit and best case as parts of the quarter">
    <i class="booked" style="width:{w(f["booked"])}"></i><i class="commit" data-seg="commit" style="width:{w(commit_open)}"></i>
    <i class="best" data-seg="best" style="width:{w(best_open)}"></i></div>
  <div class="fbar-legend"><span><i style="background:var(--seq-6)"></i>Booked <strong>{money(f["booked"], True)}</strong></span>
    <span><i style="background:var(--seq-4)"></i>Called Commit <strong data-leg="commit">{money(commit_open, True)}</strong></span>
    <span><i style="background:var(--seq-2)"></i>Called Best case <strong data-leg="best">{money(best_open, True)}</strong></span>
    <span><i style="background:var(--card-2);outline:1px solid var(--border)"></i>Pipeline and not counted</span></div></section>"""
    body = f"""
<div class="tiles">{tiles}</div>
{fbar}
<form method="post" action="/forecast" class="card" data-forecast>
  <div class="card-head"><h2>Deals closing {esc(q)}</h2>{done}</div>
  <p class="muted">Each deal starts with a call from its stage (75%+ Commit, 40%+ Best case, otherwise Pipeline). Change any call to match what you know. {esc(hint)}</p>
  <input type="hidden" name="_csrf" value="{esc(token)}">
  <div class="scroll"><table class="data"><thead><tr><th>Deal</th><th>Branch</th><th>Stage</th><th class="n">Prob.</th><th class="n">Close</th><th class="n">Amount</th><th>Call</th></tr></thead>
  <tbody>{rows or '<tr><td colspan=7>No open deals close this quarter.</td></tr>'}</tbody></table></div>
  <div class="form-actions">{action}</div>
  {ui.how("Replaces the forecast spreadsheet: one list, one set of calls, and totals everyone can trust. Deals past their close date aren't included; they show in the pipeline as past due.")}
</form>"""
    return ui.page(request, "Forecast", body, "Forecast", subtitle=f"This quarter: {q}", wide=True)


def save_forecast(request, form) -> int:
    if request.state.user["role"] != "admin" or _is_guest(request):
        return 0
    calls = {k[5:]: str(v) for k, v in form.items() if k.startswith("call:")}
    return watch.save_calls(calls, request.state.user["email"])
