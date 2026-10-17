"""The hub's pages. Each takes the request (for the signed-in user) and returns HTML."""
import calendar
import csv
import datetime as dt
import io
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from .. import cleanup, db, metrics
from ..ai import insights as ai_insights, usage as ai_usage
from ..config import get_settings
from . import ui
from .ui import esc, money, pct


def scope_of(request):
    u = request.state.user
    return u["branches"] or None


def _date_param(v):
    try:
        return dt.date.fromisoformat(v) if v else None
    except ValueError:
        return None


def _branches(scope):
    rows = db.query("SELECT code, name, region FROM core.branches WHERE active ORDER BY region, name")
    return [r for r in rows if not scope or r["code"] in scope]


# ---------------------------------------------------------------- home

def home(request):
    scope = scope_of(request)
    t = metrics.today()
    (ys, ye), (ls, le) = metrics.ytd_windows(t)
    cur, prev = metrics.closed_summary(ys, ye, scope), metrics.closed_summary(ls, le, scope)
    pipe = metrics.pipeline_summary(t, scope)
    bill, bill_ly = metrics.billing_summary(ys, ye, scope), metrics.billing_summary(ls, le, scope)
    ar = metrics.ar_aging(scope)
    ly_title = f"Compared with {ui.date(ls)} to {ui.date(le)}"

    tiles = "".join([
        ui.tile("Bookings this year", money(cur["won_amount"], True),
                ui.delta(cur["won_amount"], prev["won_amount"], label="vs last year", title=ly_title),
                metrics.deals_link(status="won", close_from=ys, close_to=ye), metrics.HOW["bookings"]),
        ui.tile("Win rate this year (by $)", pct(cur["win_rate_dollars"]),
                f'{pct(cur["win_rate_count"])} by count<br>' + ui.points_delta(cur["win_rate_dollars"], prev["win_rate_dollars"], "vs last year"),
                metrics.deals_link(status="closed", close_from=ys, close_to=ye), metrics.HOW["win_rate"]),
        ui.tile("Open pipeline closing this year", money(pipe["this_year"], True),
                f'{money(pipe["this_year_weighted"], True)} weighted · {int(pipe["this_year_count"])} deals',
                metrics.deals_link(status="open", close_from=t, close_to=dt.date(t.year, 12, 31)), metrics.HOW["pipeline"]),
        ui.tile("Billed this year", money(bill["billed"], True), ui.delta(bill["billed"], bill_ly["billed"], label="vs last year", title=ly_title),
                metrics.invoices_link(date_from=ys, date_to=ye), metrics.HOW["billed"]),
        ui.tile("Cash collected this year", money(bill["collected"], True),
                ui.delta(bill["collected"], bill_ly["collected"], label="vs last year", title=ly_title), None, metrics.HOW["collected"]),
        ui.tile("Receivables over 60 days late", money(ar["over_60"], True), f'of {money(ar["total"], True)} unpaid in total',
                "/receivables", metrics.HOW["ar"]),
    ])

    # Charts: monthly bookings vs last year, and cumulative against the goal.
    this_m = metrics.bookings_by_month(t.year, scope)
    last_m = metrics.bookings_by_month(t.year - 1, scope)
    months = [calendar.month_abbr[m] for m in range(1, 13)]
    shown = [v if m < t.month else (v if m == t.month else None) for m, v in enumerate(this_m, start=1)]
    links = [metrics.deals_link(status="won", close_from=dt.date(t.year, m, 1),
                                close_to=dt.date(t.year, m, calendar.monthrange(t.year, m)[1])) for m in range(1, 13)]
    monthly = ui.chart("bk-month", {"type": "bar", "format": "money", "labels": months, "links": links, "datasets": [
        {"label": str(t.year), "data": shown, "color": "--series-1"},
        {"label": str(t.year - 1), "data": last_m, "color": "--series-ly"}]}, label="Bookings by month")
    cum, run = [], 0.0
    for m, v in enumerate(this_m, start=1):
        run += v
        cum.append(run if m <= t.month else None)
    goal = None if scope else metrics.bookings_goal(t.year)
    datasets = [{"label": f"{t.year} bookings, cumulative", "data": cum, "color": "--series-1", "type": "line"}]
    if goal:
        datasets.append({"label": "Goal pace", "data": [goal * m / 12 for m in range(1, 13)], "color": "--axis",
                         "type": "line", "points": False, "dash": True})
    cumulative = ui.chart("bk-cum", {"type": "line", "format": "money", "labels": months, "datasets": datasets},
                          height=220, label="Cumulative bookings against goal")
    goal_line = ""
    if goal:
        pace = goal * (t.timetuple().tm_yday / (366 if calendar.isleap(t.year) else 365))
        goal_line = (f'<p class="muted" style="margin:6px 0 0">Goal {money(goal, True)} for {t.year}. '
                     f'{money(cur["won_amount"], True)} booked vs {money(pace, True)} on pace to date '
                     f'({pct(cur["won_amount"] / pace if pace else None, 0)} of pace).</p>')

    changes = _changes_card(metrics.recent_changes(t, 7, scope), t)
    issues = cleanup.run_checks(scope, limit=0)
    issue_items = "".join(
        f'<li><a href="/cleanup#{c["check"].key}">{esc(c["check"].title)}</a><span class="amt">{c["count"]}</span></li>'
        for c in sorted(issues, key=lambda c: -c["count"]) if c["count"])
    fresh = metrics.freshness()
    if fresh and fresh.get("latest"):
        local = fresh["latest"].astimezone(ZoneInfo(get_settings().tz))
        fresh_txt = f'Data last synced {ui.date(local.date())} at {local.strftime("%-I:%M %p")}'
    else:
        fresh_txt = "Not synced yet"

    insights_html = ""
    found = [] if scope else ai_insights.latest()
    if found:
        when = found[0]["created_at"].astimezone(ZoneInfo(get_settings().tz))
        cards = "".join(
            f'<article class="insight"><h3>{esc(i["headline"])}</h3><div class="detail">{i["detail_html"]}</div>'
            + (f'<a class="more" href="{esc(i["link"])}">{esc(i["link_label"] or "See the records")} →</a>' if i["link"] else "")
            + "</article>" for i in found)
        insights_html = (f'<div class="insights-head"><h2><span aria-hidden="true" style="color:var(--accent)">✦</span> '
                         f'AI insights</h2><span>Written {ui.short_date(when.date())} at {when.strftime("%-I:%M %p")} · '
                         f'check the linked records before acting</span></div><div class="insights">{cards}</div>')
    body = f"""
<div class="tiles">{tiles}</div>
{insights_html}
<div class="cols">
  <div>
    <section class="card"><div class="card-head"><h2>Bookings by month</h2>
      <div class="legend"><span><i style="background:var(--series-1)"></i>{t.year}</span><span><i style="background:var(--series-ly)"></i>{t.year - 1}</span></div></div>
      {monthly}{ui.how(metrics.HOW["bookings"] + " Click a month to see its deals.")}</section>
    <section class="card"><div class="card-head"><h2>{"Progress to goal" if goal else "Bookings so far this year"}</h2>
      <div class="legend"><span><i style="background:var(--series-1)"></i>Cumulative bookings</span>{'<span><i style="background:var(--axis)"></i>Goal pace</span>' if goal else ''}</div></div>
      {cumulative}{goal_line}</section>
  </div>
  <div>
    {changes}
    <section class="card"><div class="card-head"><h2>Needs fixing at the source</h2><a href="/cleanup">See all</a></div>
      <ul class="list">{issue_items or '<li>Nothing flagged.</li>'}</ul></section>
    <p class="muted" style="font-size:13px">{esc(fresh_txt)}. Today is {ui.date(t)} ({esc(get_settings().tz)}).</p>
  </div>
</div>"""
    return ui.page(request, "Where we stand", body, "Home",
                   subtitle=f"Year to date, {ui.date(dt.date(t.year, 1, 1))} to {ui.date(t)}, compared with the same dates last year")


def _changes_card(ch, t):
    def group(title, rows, total, extra=lambda r: "", see_all=None):
        if not rows:
            return f'<div class="change-group"><h3><span>{esc(title)}</span><span class="muted">none</span></h3></div>'
        items = "".join(
            f'<li><div>{ui.source_link("crm_deal", r["id"], r["name"])}<div class="meta">{esc(r.get("branch") or "")}{extra(r)}</div></div>'
            f'<span class="amt">{money(r["amount"], True)}</span></li>' for r in rows[:3])
        more = ""
        if len(rows) > 3:
            more = (f'<li class="meta"><a href="{esc(see_all)}">and {len(rows) - 3} more</a></li>' if see_all
                    else f'<li class="meta">and {len(rows) - 3} more</li>')
        return (f'<div class="change-group"><h3><span>{esc(title)} ({len(rows)})</span><span class="amt">{money(total, True)}</span></h3>'
                f'<ul class="list">{items}{more}</ul></div>')
    slip = lambda r: f' · close {ui.short_date(r["old_close"])} → {ui.short_date(r["new_close"])}'
    return f"""<section class="card"><div class="card-head"><h2>Last 7 days</h2><span class="muted">since {ui.short_date(ch["since"])}</span></div>
      {group("Won", ch["won"], ch["totals"]["won"], see_all=metrics.deals_link(status="won", close_from=ch["since"], close_to=t))}
      {group("Lost", ch["lost"], ch["totals"]["lost"], see_all=metrics.deals_link(status="lost", close_from=ch["since"], close_to=t))}
      {group("Pushed to a later month", ch["slipped"], ch["totals"]["slipped"], slip)}
      {group("New deals", ch["created"], ch["totals"]["created"], see_all=metrics.deals_link(status="all", created_from=ch["since"], created_to=t, sort="created"))}
      {ui.how("Won and lost are by close date, the same rule as bookings. 'Pushed to a later month' comes from the CRM's change history, which we keep even where the CRM drops it.")}</section>"""


# ---------------------------------------------------------------- scorecard

def scorecard(request):
    scope = scope_of(request)
    t = metrics.today()
    sc = metrics.scorecard(t, 13, scope)
    weeks = sc["weeks"]
    head = "".join(f'<th class="n">{ui.short_date(w)}{"<br><span class=muted>so far</span>" if i == len(weeks) - 1 else ""}</th>'
                   for i, w in enumerate(weeks))
    fmt = {"money": lambda v: money(v, True), "count": ui.num, "pct": lambda v: "—" if v is None else f"{v:.1f}%"}
    rows = []
    for r in sc["rows"]:
        cells, scored, hits = [], 0, 0
        for i, v in enumerate(r["values"]):
            last = i == len(weeks) - 1
            cls = ""
            # This week isn't over, so totals aren't scored yet. Rates and balances are, since they're "as of now".
            if r["goal"] is not None and v is not None and not (last and r["key"] not in ("win_rate_dollars", "ar_over_60", "billed_4wk")):
                hit = v >= r["goal"] if r["higher_is_better"] else v <= r["goal"]
                cls = "hit" if hit else "miss"
                if not last:
                    scored += 1
                    hits += hit
            if last:
                cls += " partial"
            cells.append(f'<td class="n {cls}">{fmt[r["format"]](v)}</td>')
        goal = "" if r["goal"] is None else (("Goal ≥ " if r["higher_is_better"] else "Goal ≤ ") + fmt[r["format"]](r["goal"]))
        record = f"{hits} of {scored}" if scored else "—"
        rows.append(f'<tr><th class="sticky measure" scope="row">{esc(r["label"])}'
                    f'<span class="goal">{goal}</span>'
                    f'<details class="how"><summary>How</summary><p>{esc(r["how"])}</p></details></th>'
                    f'{"".join(cells)}<td class="n record">{record}</td></tr>')
    note = ("Goals are company-wide, so they're hidden when you see only some branches." if scope else
            "Green: goal hit. Red (✕): missed. This week is still in progress, so its totals aren't scored yet.")
    body = f"""<section class="card">
<p class="muted" style="margin-top:0">{esc(note)}</p>
<div class="scroll" data-scroll-end><table class="data scorecard"><thead><tr><th class="sticky">Measure</th>{head}<th class="n">Weeks on goal</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div></section>"""
    return ui.page(request, "Weekly scorecard", body, "Scorecard",
                   subtitle="Fills itself in from the CRM and accounting every hour. Weeks run Monday to Sunday.", wide=True)


# ---------------------------------------------------------------- deals

STATUS_SQL = {
    "open": "is_open", "won": "is_won", "lost": "is_lost", "closed": "is_closed", "all": "true",
}
SORTS = {"amount": "amount DESC NULLS LAST", "close": "close_date ASC NULLS LAST", "created": "created_at DESC"}


def _deal_filters(request, scope):
    q = request.query_params
    f = {
        "status": q.get("status") if q.get("status") in STATUS_SQL else "open",
        "branch": q.get("branch") or "", "deal_type": q.get("deal_type") or "", "segment": q.get("segment") or "",
        "stage": q.get("stage") or "",
        "close_from": _date_param(q.get("close_from")), "close_to": _date_param(q.get("close_to")),
        "created_from": _date_param(q.get("created_from")), "created_to": _date_param(q.get("created_to")),
        "sort": q.get("sort") if q.get("sort") in SORTS else "amount",
    }
    where = [STATUS_SQL[f["status"]]]
    p = {"scope": scope}
    for key, col in (("branch", "branch_code"), ("deal_type", "deal_type"), ("segment", "segment"), ("stage", "stage")):
        if f[key]:
            where.append(f"{col} = %({key})s")
            p[key] = f[key]
    for key, col, op in (("close_from", "close_date", ">="), ("close_to", "close_date", "<="),
                         ("created_from", "created_date", ">="), ("created_to", "created_date", "<=")):
        if f[key]:
            where.append(f"{col} {op} %({key})s")
            p[key] = f[key]
    if scope:
        where.append("branch_code = ANY(%(scope)s)")
    return f, " AND ".join(where), p


def _deal_rows(where, p, sort, limit=None):
    lim = f" LIMIT {int(limit)}" if limit else ""
    return db.query(f"""SELECT id, name, account_id, account_name, segment, branch, deal_type, stage, probability,
                               amount, weighted_amount, margin_pct, close_date, created_date, owner_name, loss_reason
                        FROM rpt.deals WHERE {where} ORDER BY {SORTS[sort]}{lim}""", p)


STAGE_ORDER = ["Prospecting", "Qualification", "Proposal", "Negotiation"]


def deals(request):
    scope = scope_of(request)
    t = metrics.today()
    f, where, p = _deal_filters(request, scope)
    totals = db.one(f"""SELECT count(*) AS n, coalesce(sum(amount), 0) AS amount, coalesce(sum(weighted_amount), 0) AS weighted
                        FROM rpt.deals WHERE {where}""", p)
    rows = _deal_rows(where, p, f["sort"], limit=500)
    opts = lambda values, sel: "".join(f'<option value="{esc(v)}"{" selected" if v == sel else ""}>{esc(lbl)}</option>'
                                       for v, lbl in values)
    branches = [("", "All your branches" if scope else "All branches")] + [(b["code"], b["name"]) for b in _branches(scope)]
    types = [("", "All types")] + [(r["deal_type"], r["deal_type"]) for r in
                                   db.query("SELECT DISTINCT deal_type FROM rpt.deals WHERE deal_type IS NOT NULL ORDER BY 1")]
    segs = [("", "All segments")] + [(r["segment"], r["segment"]) for r in
                                     db.query("SELECT DISTINCT segment FROM rpt.deals WHERE segment IS NOT NULL ORDER BY 1")]
    statuses = [("open", "Open"), ("won", "Won"), ("lost", "Lost"), ("closed", "Won or lost"), ("all", "All")]
    sorts = [("amount", "Biggest first"), ("close", "Closing soonest"), ("created", "Newest first")]
    dv = lambda d: d.isoformat() if d else ""
    more_open = " open" if (f["created_from"] or f["created_to"] or f["stage"]) else ""
    stage_input = f'<input type="hidden" name="stage" value="{esc(f["stage"])}">' if f["stage"] else ""
    filters = f"""<form class="filters" method="get" action="/deals">
  <label>Status<select name="status">{opts(statuses, f["status"])}</select></label>
  <label>Branch<select name="branch">{opts(branches, f["branch"])}</select></label>
  <label>Type<select name="deal_type">{opts(types, f["deal_type"])}</select></label>
  <label>Segment<select name="segment">{opts(segs, f["segment"])}</select></label>
  <label>Close date<span class="range"><input type="date" name="close_from" value="{dv(f["close_from"])}" aria-label="Close date from">
    <span class="muted">to</span><input type="date" name="close_to" value="{dv(f["close_to"])}" aria-label="Close date to"></span></label>
  <label>Sort<select name="sort">{opts(sorts, f["sort"])}</select></label>
  <button class="primary" type="submit">Apply</button>
  <a class="btn ghost" href="/deals?status={esc(f["status"])}">Clear</a>
  <details class="more"{more_open}><summary>More filters</summary>
    <label>Created<span class="range"><input type="date" name="created_from" value="{dv(f["created_from"])}" aria-label="Created from">
    <span class="muted">to</span><input type="date" name="created_to" value="{dv(f["created_to"])}" aria-label="Created to"></span></label>
    {stage_input}{f'<span class="muted">Stage: {esc(f["stage"])}</span>' if f["stage"] else ""}
  </details>
</form>"""
    open_cols = f["status"] == "open"

    stages_html = ""
    if open_cols and not f["stage"]:
        st = db.query(f"""SELECT CASE WHEN close_date < %(t)s THEN 'Past due' ELSE stage END AS stage,
                                 count(*) AS n, sum(amount) AS amount, sum(weighted_amount) AS weighted
                          FROM rpt.deals WHERE {where} GROUP BY 1""", dict(p, t=t))
        by = {r["stage"]: r for r in st}
        top = max([float(r["amount"] or 0) for r in st] or [1]) or 1
        items = []
        base = dict(request.query_params)
        for name in STAGE_ORDER + ["Past due"]:
            r = by.get(name)
            if not r:
                continue
            width = 100 * float(r["amount"] or 0) / top
            if name == "Past due":
                link = "/deals?" + urlencode(
                    dict(base, close_to=(t - dt.timedelta(days=1)).isoformat(), close_from=""))
            else:
                # Match the bar: a stage's bar excludes past-due deals, so its link does too.
                link = "/deals?" + urlencode(dict(base, stage=name, close_from=max(f["close_from"] or t, t).isoformat()))
            items.append(f"""<a class="stage{' pastdue' if name == 'Past due' else ''}" href="{esc(link)}">
<span class="stage-name">{esc(name)}</span><span class="stage-bar"><i style="width:{width:.1f}%"></i></span>
<span class="stage-n">{r["n"]}</span><span class="stage-amt">{money(r["amount"], True)}</span>
<span class="stage-w muted">{money(r["weighted"], True)} wtd</span></a>""")
        if items:
            stages_html = (f'<div class="stages" aria-label="Pipeline by stage">{"".join(items)}</div>'
                           '<p class="muted" style="font-size:13px;margin:4px 0 14px">"Past due" means the close date has '
                           'already passed but the deal is still open. Usually these need updating in the CRM.</p>')

    trs = []
    for r in rows:
        margin = "—" if r["margin_pct"] is None else "%.1f%%" % float(r["margin_pct"])
        extra = (f'<td>{esc(r["stage"])}</td><td class="n">{r["probability"]:.0f}%</td><td class="n">{money(r["weighted_amount"])}</td>'
                 if open_cols else f'<td>{esc(r["stage"])}</td><td class="n">{margin}</td><td>{esc(r["loss_reason"] or "")}</td>')
        late = (' <span class="pill warn">past due</span>'
                if open_cols and r["close_date"] and r["close_date"] < t else "")
        trs.append(f'<tr><td class="wrap">{ui.source_link("crm_deal", r["id"], r["name"])}</td>'
                   f'<td>{esc(r["branch"])}</td><td>{esc(r["deal_type"])}</td><td class="n">{money(r["amount"])}</td>{extra}'
                   f'<td class="n">{ui.date(r["close_date"])}{late}</td><td>{esc(r["owner_name"])}</td></tr>')
    head_extra = ('<th>Stage</th><th class="n">Probability</th><th class="n">Weighted</th>' if open_cols
                  else '<th>Stage</th><th class="n">Margin</th><th>Loss reason</th>')
    shown = f"Showing the first 500 of {totals['n']:,}. Download for the full list." if totals["n"] > 500 else ""
    summary = (f'<div class="summary-row"><p><strong>{totals["n"]:,} deals</strong> · {money(totals["amount"])} total'
               + (f' · {money(totals["weighted"])} weighted' if open_cols else "") + f' <span class="muted">{shown}</span></p>'
               f'<a class="btn secondary" href="/deals.csv?{esc(request.url.query)}">Download for Excel</a></div>')
    body = f"""<section class="card">{filters}{stages_html}{summary}
<div class="scroll"><table class="data"><thead><tr><th>Deal</th><th>Branch</th><th>Type</th><th class="n">Amount</th>{head_extra}
<th class="n">Close date</th><th>Owner</th></tr></thead><tbody>{"".join(trs) or '<tr><td colspan="9">No deals match these filters.</td></tr>'}</tbody></table></div>
{ui.how(metrics.HOW["pipeline"] if open_cols else metrics.HOW["win_rate"])}</section>"""
    title = {"open": "Open pipeline", "won": "Won deals", "lost": "Lost deals", "closed": "Closed deals"}.get(f["status"], "All deals")
    bits = [dict(branches).get(f["branch"]) if f["branch"] else None, f["deal_type"] or None, f["segment"] or None,
            f["stage"] or None]
    if f["close_from"] or f["close_to"]:
        bits.append(f'closing {ui.date(f["close_from"]) if f["close_from"] else "any time"} to '
                    f'{ui.date(f["close_to"]) if f["close_to"] else "any time"}')
    subtitle = " · ".join(esc(b) for b in bits if b) or "Every deal links to its record in the CRM."
    return ui.page(request, title, body, "Pipeline", subtitle=subtitle, wide=True)


def deals_csv(request):
    scope = scope_of(request)
    f, where, p = _deal_filters(request, scope)
    rows = _deal_rows(where, p, f["sort"])
    out = io.StringIO()
    w = csv.writer(out)
    cols = ["id", "name", "account_name", "segment", "branch", "deal_type", "stage", "probability", "amount",
            "weighted_amount", "margin_pct", "close_date", "created_date", "owner_name", "loss_reason"]
    w.writerow(cols)
    for r in rows:
        w.writerow([_csv_safe(r[c]) for c in cols])
    return out.getvalue()


def _csv_safe(v):
    """Stop spreadsheet formula injection from text fields."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return "" if v is None else v


# ---------------------------------------------------------------- win / loss

DIMENSIONS = {"segment": "Segment", "deal_type": "Deal type", "branch": "Branch", "region": "Region",
              "lead_source": "Lead source", "owner_name": "Owner"}


def winloss(request):
    scope = scope_of(request)
    t = metrics.today()
    q = request.query_params
    months = int(q.get("months")) if q.get("months") in ("3", "6", "12", "24") else 12
    start = t - dt.timedelta(days=round(months * 30.44))
    a = q.get("a") if q.get("a") in DIMENSIONS else "segment"
    b = q.get("b") if q.get("b") in DIMENSIONS and q.get("b") != a else ("deal_type" if a != "deal_type" else "segment")
    s = metrics.closed_summary(start, t, scope)
    grid = metrics.sell_best_grid(start, t, scope, a, b)
    quarters = metrics.quarterly_win_rates(t, 8, scope)

    tiles = "".join([
        ui.tile("Win rate by $", pct(s["win_rate_dollars"]), f'{pct(s["win_rate_count"])} by count',
                metrics.deals_link(status="closed", close_from=start, close_to=t), metrics.HOW["win_rate"]),
        ui.tile("Won", money(s["won_amount"], True), f'{int(s["won_count"])} deals',
                metrics.deals_link(status="won", close_from=start, close_to=t)),
        ui.tile("Lost", money(s["lost_amount"], True), f'{int(s["lost_count"])} deals',
                metrics.deals_link(status="lost", close_from=start, close_to=t)),
        ui.tile("Margin on won deals", pct(s["margin_pct"]),
                f'{int(s["won_missing_margin"])} won deals have no margin entered', None, metrics.HOW["margin"]),
    ])
    qlabels = [x["label"] for x in quarters]
    bars = ui.chart("wl-q", {"type": "bar", "format": "money", "stacked": False, "labels": qlabels, "datasets": [
        {"label": "Won", "data": [x["won_amount"] for x in quarters], "color": "--series-1"},
        {"label": "Lost", "data": [x["lost_amount"] for x in quarters], "color": "--series-2"}]},
        height=240, label="Won and lost dollars by quarter")
    rates = ui.chart("wl-r", {"type": "line", "format": "pct", "labels": qlabels, "suggestedMax": 70, "datasets": [
        {"label": "By $", "data": [None if x["rate_dollars"] is None else 100 * x["rate_dollars"] for x in quarters], "color": "--series-1"},
        {"label": "By count", "data": [None if x["rate_count"] is None else 100 * x["rate_count"] for x in quarters], "color": "--series-3"}]},
        height=240, label="Close rate by quarter")

    # The heat grid.
    cells = {(c["a"], c["b"]): c for c in grid["cells"]}
    best_keys = {(c["a"], c["b"]) for c in grid["best"]}
    steps = ["--seq-1", "--seq-2", "--seq-3", "--seq-4", "--seq-5", "--seq-6"]
    code_by_name = {br["name"]: br["code"] for br in _branches(None)}

    def cell_link(av, bv):
        filters = {}
        for dim, val in ((a, av), (b, bv)):
            if dim in ("segment", "deal_type"):
                filters[dim] = val
            elif dim == "branch" and val in code_by_name:
                filters["branch"] = code_by_name[val]
            else:
                return None  # the deals list can't filter on this dimension yet
        return metrics.deals_link(status="closed", close_from=start, close_to=t, **filters)

    def cell(av, bv):
        c = cells.get((av, bv))
        if not c or not c["closed_count"]:
            return '<td class="cell muted">—</td>'
        link = cell_link(av, bv)
        title = (f'{c["won_count"]} of {c["closed_count"]} deals won; {money(c["won_amount"])} of {money(c["closed_amount"])}')
        if c["closed_count"] < 5:
            return (f'<td class="cell" style="background:var(--seq-0)" title="{esc(title)}"><span class="r muted">few</span>'
                    f'<span class="w">{c["closed_count"]} closed</span></td>')
        r = c["rate_dollars"] or 0
        i = min(len(steps) - 1, int(r * len(steps) / 0.8))
        ink = "#fff" if i >= 3 else "#0b0b0b"
        best = " best" if (av, bv) in best_keys else ""
        return (f'<td class="cell{best}" style="background:var({steps[i]});color:{ink}" title="{esc(title)}">'
                + (f'<a href="{esc(link)}" style="color:inherit">' if link else "")
                + f'<span class="r">{pct(r, 0)}</span><span class="w">{money(c["won_amount"], True)} won</span>'
                + ("</a>" if link else "") + "</td>")
    grid_rows = "".join(f'<tr><th class="sticky" scope="row">{esc(av)}</th>{"".join(cell(av, bv) for bv in grid["b_values"])}</tr>'
                        for av in grid["a_values"])
    dim_opts = lambda sel: "".join(f'<option value="{k}"{" selected" if k == sel else ""}>{v}</option>' for k, v in DIMENSIONS.items())
    month_opts = "".join(f'<option value="{m}"{" selected" if m == months else ""}>Last {m} months</option>' for m in (3, 6, 12, 24))
    best_txt = "; ".join(f'<strong>{esc(c["a"])} × {esc(c["b"])}</strong> ({pct(c["rate_dollars"], 0)}, {money(c["won_amount"], True)} won)'
                         for c in grid["best"]) or "No slice beats the overall rate with enough deals yet."

    reasons = db.query(f"""SELECT coalesce(loss_reason, '(not entered)') AS reason, count(*) AS n, sum(amount) AS amount
                           FROM rpt.deals WHERE is_lost AND close_date BETWEEN %(s)s AND %(t)s {metrics._scope(scope)}
                           GROUP BY 1 ORDER BY 3 DESC""", {"s": start, "t": t, "scope": scope})
    reason_rows = "".join(f'<tr><td>{esc(r["reason"])}</td><td class="n">{r["n"]}</td><td class="n">{money(r["amount"])}</td></tr>'
                          for r in reasons)

    body = f"""
<form class="filters" method="get"><label>Period<select name="months" onchange="this.form.submit()">{month_opts}</select></label>
<input type="hidden" name="a" value="{esc(a)}"><input type="hidden" name="b" value="{esc(b)}"></form>
<div class="tiles">{tiles}</div>
<div class="cols even">
  <section class="card"><div class="card-head"><h2>Won and lost by quarter</h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>Won</span><span><i style="background:var(--series-2)"></i>Lost</span></div></div>{bars}</section>
  <section class="card"><div class="card-head"><h2>Close rate by quarter</h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>By $</span><span><i style="background:var(--series-3)"></i>By count</span></div></div>{rates}
    <p class="muted" style="margin:6px 0 0;font-size:13px">By count is usually higher: small repairs are won often, big projects less often.</p></section>
</div>
<section class="card"><div class="card-head"><h2>Where we sell best</h2>
  <form class="filters" method="get" style="margin:0"><input type="hidden" name="months" value="{months}">
  <label>Rows<select name="a" onchange="this.form.submit()">{dim_opts(a)}</select></label>
  <label>Columns<select name="b" onchange="this.form.submit()">{dim_opts(b)}</select></label></form></div>
  <p>Best slices: {best_txt}</p>
  <div class="scroll"><table class="data"><thead><tr><th class="sticky">{esc(DIMENSIONS[a])}</th>
  {"".join(f'<th style="text-align:center">{esc(bv)}</th>' for bv in grid["b_values"])}</tr></thead><tbody>{grid_rows}</tbody></table></div>
  {ui.how("Each cell is the close rate by dollars for deals closed in the period; darker is higher. Outlined cells are the "
          "best slices: the most dollars won among slices with at least 5 closed deals and a close rate above the overall "
          f"{pct(grid['overall_rate'], 0)}. Slices with fewer than 5 deals are marked 'few' because their rates aren't reliable.")}
</section>
<section class="card"><h2>Why we lose</h2>
  <div class="scroll"><table class="data"><thead><tr><th>Loss reason</th><th class="n">Deals</th><th class="n">Amount</th></tr></thead>
  <tbody>{reason_rows or '<tr><td colspan="3">No lost deals in this period.</td></tr>'}</tbody></table></div></section>"""
    return ui.page(request, "Win / loss", body, "Win / loss",
                   subtitle=f"Deals closed {ui.date(start)} to {ui.date(t)}")


# ---------------------------------------------------------------- receivables

def receivables(request):
    scope = scope_of(request)
    t = metrics.today()
    ar = metrics.ar_aging(scope)
    last30 = metrics.billing_summary(t - dt.timedelta(days=29), t, scope)
    tiles = "".join([
        ui.tile("Unpaid invoices", money(ar["total"], True), f'{sum(b["count"] for b in ar["buckets"])} invoices',
                metrics.invoices_link(status="open"), metrics.HOW["ar"]),
        ui.tile("Over 60 days late", money(ar["over_60"], True), pct(ar["over_60"] / ar["total"] if ar["total"] else None, 0) + " of unpaid",
                metrics.invoices_link(status="open", bucket="61+")),
        ui.tile("Collected, last 30 days", money(last30["collected"], True), f'{money(last30["billed"], True)} billed in the same 30 days',
                None, metrics.HOW["collected"]),
    ])
    buckets = [b for b in ar["buckets"]]
    bucket_param = {"Current": "current", "1–30 days": "1-30", "31–60 days": "31-60", "61–90 days": "61-90", "Over 90 days": "90+"}
    aging = ui.chart("ar-aging", {"type": "bar", "format": "money", "labels": [b["bucket"] for b in buckets],
                                  "links": [metrics.invoices_link(status="open", bucket=bucket_param[b["bucket"]]) for b in buckets],
                                  "datasets": [{"label": "Unpaid", "data": [b["balance"] for b in buckets], "color": "--series-1"}]},
                     height=230, label="Unpaid balance by days past due")
    custs = db.query(f"""SELECT customer_id, customer_name, sum(balance) AS balance,
                                sum(balance) FILTER (WHERE days_past_due > 60) AS over_60,
                                max(days_past_due) AS oldest, count(*) AS n
                         FROM rpt.invoices WHERE is_open {metrics._scope(scope)}
                         GROUP BY 1, 2 HAVING sum(balance) FILTER (WHERE days_past_due > 0) > 0
                         ORDER BY over_60 DESC NULLS LAST, balance DESC LIMIT 25""", {"scope": scope})
    rows = "".join(f'<tr><td>{ui.source_link("accounting_customer", c["customer_id"], c["customer_name"])}</td>'
                   f'<td class="n">{money(c["balance"])}</td><td class="n">{money(c["over_60"] or 0)}</td>'
                   f'<td class="n">{c["oldest"] or 0} days</td><td class="n"><a href="{esc(metrics.invoices_link(status="open", customer=c["customer_id"]))}">{c["n"]}</a></td></tr>'
                   for c in custs)
    body = f"""<div class="tiles">{tiles}</div>
<div>
<section class="card"><h2>Unpaid balance by days past due</h2>{aging}{ui.how(metrics.HOW["ar"] + " Click a bar to see the invoices.")}</section>
<section class="card"><h2>Who to call first</h2>
<div class="scroll"><table class="data"><thead><tr><th>Customer</th><th class="n">Unpaid</th><th class="n">Over 60 days</th><th class="n">Oldest</th><th class="n">Invoices</th></tr></thead>
<tbody>{rows or '<tr><td colspan="5">Nothing overdue.</td></tr>'}</tbody></table></div></section></div>"""
    return ui.page(request, "Receivables", body, "Receivables", subtitle=f"As of {ui.date(t)}, from accounting")


BUCKETS = {"current": "aging_bucket = 'Current'", "1-30": "aging_bucket = '1–30 days'", "31-60": "aging_bucket = '31–60 days'",
           "61-90": "aging_bucket = '61–90 days'", "90+": "aging_bucket = 'Over 90 days'",
           "61+": "aging_bucket IN ('61–90 days', 'Over 90 days')"}


def invoices(request):
    scope = scope_of(request)
    q = request.query_params
    where, p = ["true"], {"scope": scope}
    if q.get("status") == "open":
        where.append("is_open")
    if q.get("bucket") in BUCKETS:
        where.append(BUCKETS[q.get("bucket")])
    if q.get("customer"):
        where.append("customer_id = %(customer)s")
        p["customer"] = q.get("customer")
    for key, op in (("date_from", ">="), ("date_to", "<=")):
        d = _date_param(q.get(key))
        if d:
            where.append(f"invoice_date {op} %({key})s")
            p[key] = d
    if scope:
        where.append("branch_code = ANY(%(scope)s)")
    w = " AND ".join(where)
    tot = db.one(f"SELECT count(*) AS n, coalesce(sum(amount),0) AS amount, coalesce(sum(balance),0) AS balance FROM rpt.invoices WHERE {w}", p)
    rows = db.query(f"""SELECT id, number, customer_id, customer_name, branch, invoice_date, due_date, amount, balance,
                               aging_bucket, deal_id, memo FROM rpt.invoices WHERE {w}
                        ORDER BY days_past_due DESC NULLS LAST, invoice_date DESC LIMIT 500""", p)
    trs = "".join(
        f'<tr><td>{ui.source_link("accounting_invoice", r["id"], r["number"])}</td>'
        f'<td class="wrap">{ui.source_link("accounting_customer", r["customer_id"], r["customer_name"])}</td>'
        f'<td>{esc(r["branch"])}</td><td class="n">{ui.date(r["invoice_date"])}</td><td class="n">{ui.date(r["due_date"])}</td>'
        f'<td class="n">{money(r["amount"])}</td><td class="n">{money(r["balance"])}</td><td>{esc(r["aging_bucket"])}</td>'
        f'<td>{ui.source_link("crm_deal", r["deal_id"], r["deal_id"]) if r["deal_id"] else "—"}</td></tr>' for r in rows)
    more = f' <span class="muted">Showing the first 500.</span>' if tot["n"] > 500 else ""
    body = f"""<section class="card"><p><strong>{tot["n"]:,} invoices</strong> · {money(tot["amount"])} billed · {money(tot["balance"])} unpaid{more}</p>
<div class="scroll"><table class="data"><thead><tr><th>Invoice</th><th>Customer</th><th>Branch</th><th class="n">Date</th><th class="n">Due</th>
<th class="n">Amount</th><th class="n">Unpaid</th><th>Status</th><th>Deal</th></tr></thead><tbody>{trs or '<tr><td colspan="9">No invoices match.</td></tr>'}</tbody></table></div></section>"""
    return ui.page(request, "Invoices", body, "Receivables", subtitle="From accounting. Each invoice links to its record.", wide=True)


# ---------------------------------------------------------------- clean-up

def cleanup_page(request):
    scope = scope_of(request)
    results = cleanup.run_checks(scope)
    total = sum(r["count"] for r in results)
    short = {"placeholder_close": "Placeholder date", "duplicates": "Duplicates", "stale_open": "Stale open",
             "missing_margin": "No margin", "lost_no_reason": "No loss reason", "won_not_billed": "Not billed",
             "unlinked_customer": "Unlinked customer", "unmapped_branch": "Unknown branch"}
    active = [r["check"] for r in results if r["count"]]
    branch_rows = "".join(
        f'<tr><th class="sticky" scope="row">{esc(b["branch"])}</th><td class="n"><strong>{b["count"]}</strong></td>'
        + "".join(f'<td class="n">{b["checks"].get(c.key, 0) or "<span class=muted>·</span>"}</td>' for c in active) + "</tr>"
        for b in cleanup.by_branch(results))
    summary = (f'<section class="card"><h2>Where the clean-up is</h2><div class="scroll"><table class="data">'
               f'<thead><tr><th class="sticky">Branch</th><th class="n">Total</th>'
               + "".join(f'<th class="n"><a href="#{c.key}">{esc(short.get(c.key, c.key))}</a></th>' for c in active)
               + f'</tr></thead><tbody>{branch_rows}</tbody></table></div></section>') if total else ""
    blocks = []
    for r in results:
        c = r["check"]
        rows = "".join(f'<tr><td class="wrap">{ui.source_link(c.link, x["id"], x["label"])}</td><td>{esc(x["detail"])}</td>'
                       f'<td>{esc(x.get("branch") or "")}</td><td>{esc(x.get("owner_name") or "")}</td>'
                       f'<td class="n">{money(x["amount"])}</td></tr>' for x in r["rows"])
        more = f'<p class="muted">Showing the first {len(r["rows"])} of {r["count"]}.</p>' if r["count"] > len(r["rows"]) else ""
        table = (f'<div class="scroll" style="max-height:420px"><table class="data"><thead><tr><th>Record</th><th>Detail</th>'
                 f'<th>Branch</th><th>Owner</th><th class="n">Amount</th></tr></thead><tbody>{rows}</tbody></table></div>{more}') if r["count"] else ""
        status = ui.status_pill("ok") if not r["count"] else f'<span class="count">{r["count"]} · {money(r["amount"], True)}</span>'
        blocks.append(f"""<details class="check" id="{c.key}"{' open' if r["count"] and len(blocks) < 1 else ''}>
<summary><strong>{esc(c.title)}</strong>{status}</summary>
<p>{esc(c.why)} <strong>Fix:</strong> {esc(c.fix)} <span class="muted">({'CRM' if c.system == 'crm' else 'Accounting'})</span></p>{table}</details>""")
    body = f"""<p class="lead">{total} records to fix. They get fixed in the source systems, not patched over here, so every report
gets more accurate. Each record opens in its own system, and the owner column says who should fix it.</p>
{summary}<section class="card">{"".join(blocks)}</section>"""
    return ui.page(request, "Clean-up list", body, "Clean-up", subtitle="Data problems that make reports wrong")


# ---------------------------------------------------------------- health (admin)

SYNC_NAMES = {"crm.users": "CRM · Users", "crm.accounts": "CRM · Accounts", "crm.opportunities": "CRM · Deals",
              "crm.opportunity_history": "CRM · Deal change history", "acct.customers": "Accounting · Customers",
              "acct.invoices": "Accounting · Invoices", "backup": "Nightly backup"}
PAGE_NAMES = {"/": "Home", "/scorecard": "Scorecard", "/deals": "Pipeline / deals", "/winloss": "Win / loss",
              "/receivables": "Receivables", "/invoices": "Invoices", "/cleanup": "Clean-up", "/health": "Health"}


def _local(ts):
    if not ts:
        return "never"
    return ts.astimezone(ZoneInfo(get_settings().tz)).strftime("%b %-d, %-I:%M %p")


def health(request):
    syncs = db.query("SELECT * FROM core.sync_state ORDER BY object = 'backup', object")
    now = db.one("SELECT now() AS n")["n"]
    rows = []
    for s_ in syncs:
        status = s_["last_status"]
        limit = 26 * 3600 if s_["object"] == "backup" else 3 * 3600
        if status in ("ok", "warning") and s_["last_success_at"] and (now - s_["last_success_at"]).total_seconds() > limit:
            status = "stale"
        rows.append(f'<tr><td>{esc(SYNC_NAMES.get(s_["object"], s_["object"]))}</td><td>{ui.status_pill(status)}</td>'
                    f'<td class="n">{_local(s_["last_success_at"])}</td>'
                    f'<td class="n">{ui.num(s_["rows_seen"])}</td><td class="n">{ui.num(s_["rows_pruned"])}</td>'
                    f'<td class="wrap">{esc(s_["last_message"])}</td></tr>')
    visits = db.query("""SELECT path, count(*) AS n, count(DISTINCT user_id) AS users FROM core.page_visits
                         WHERE at > now() - interval '30 days' GROUP BY 1 ORDER BY 2 DESC LIMIT 12""")
    vrows = "".join(f'<tr><td>{esc(PAGE_NAMES.get(v["path"], v["path"]))}</td><td class="n">{v["n"]}</td>'
                    f'<td class="n">{v["users"]}</td></tr>' for v in visits)
    users = db.query("SELECT email, name, role, branches, last_login_at FROM core.app_users WHERE active ORDER BY name")
    names = {b["code"]: b["name"] for b in _branches(None)}
    urows = "".join(f'<tr><td>{esc(u["name"])}<div class="meta muted">{esc(u["email"])}</div></td>'
                    f'<td>{"Admin" if u["role"] == "admin" else "Viewer"}</td>'
                    f'<td>{esc(", ".join(names.get(b, b) for b in u["branches"]) if u["branches"] else "All branches")}</td>'
                    f'<td class="n">{_local(u["last_login_at"])}</td></tr>' for u in users)
    tz = esc(get_settings().tz)
    ai_rows = "".join(
        f'<tr><td>{"Ask AI chat" if a["feature"] == "chat" else "Home page insights"}</td>'
        f'<td>{ui.status_pill("ok") if a["configured"] else "<span class=muted>No API key yet</span>"}</td>'
        f'<td class="n">{a["calls"]:,}</td><td class="n">${a["cost"]:,.2f}</td><td class="n">${a["cap"]:,.0f}</td>'
        f'<td class="n">{"—" if not a["answers_30d"] else "$%.3f" % a["avg_answer_cost"]}</td></tr>'
        for a in ai_usage.summary())
    ai_card = f"""<section class="card"><h2>AI usage this month</h2>
<div class="scroll"><table class="data"><thead><tr><th>Feature</th><th>Status</th><th class="n">Model calls</th>
<th class="n">Spent</th><th class="n">Monthly cap</th><th class="n">Avg per answer (30 days)</th></tr></thead><tbody>{ai_rows}</tbody></table></div>
{ui.how("Every AI call is logged with its tokens and cost. When a feature reaches its cap it stops until the 1st. Each feature has its own API key, so one can be switched off without touching the other.")}</section>"""
    from ..alerts import open_alerts
    alerts = open_alerts()
    alert_rows = "".join(f'<li><div>{ui.status_pill("failed" if a["severity"] == "critical" else "warning")} {esc(a["message"])}'
                         f'<div class="meta">since {_local(a["first_seen"])}</div></div></li>' for a in alerts)
    alerts_card = (f'<section class="card" id="alerts"><h2>Open alerts</h2><ul class="list">{alert_rows}</ul>'
                   f'{ui.how("Checked every 15 minutes. You get a message when a problem starts, every 24 hours while it lasts, and when it is fixed.")}</section>'
                   if alerts else "")
    body = f"""{alerts_card}<section class="card"><h2>Data syncs and backups</h2>
<div class="scroll"><table class="data"><thead><tr><th>What</th><th>Status</th><th class="n">Last success</th>
<th class="n">Rows</th><th class="n">Removed</th><th>Note</th></tr></thead><tbody>{"".join(rows) or '<tr><td colspan="6">Nothing has synced yet.</td></tr>'}</tbody></table></div>
{ui.how(f"Syncs run hourly and are flagged out of date after 3 hours without success; the backup after 26 hours. The removal step refuses to delete more than 10% of a table in one run. Times are {tz}.")}</section>
{ai_card}
<div class="cols even"><section class="card"><h2>Most-used pages, last 30 days</h2>
<div class="scroll"><table class="data"><thead><tr><th>Page</th><th class="n">Visits</th><th class="n">People</th></tr></thead><tbody>{vrows}</tbody></table></div></section>
<section class="card"><h2>People with access</h2>
<div class="scroll"><table class="data"><thead><tr><th>Person</th><th>Role</th><th>Sees</th><th class="n">Last sign-in</th></tr></thead><tbody>{urows}</tbody></table></div></section></div>"""
    return ui.page(request, "Health", body, "Health", subtitle="Is the data fresh, are backups running, who's using what")


# ---------------------------------------------------------------- demo stand-in source pages

FIELD_LABELS = {
    "opportunity": [("name", "Opportunity name"), ("account", "Account"), ("stage", "Stage"), ("amount", "Amount"),
                    ("probability", "Probability (%)"), ("close_date", "Close date"), ("deal_type", "Record type"),
                    ("owner", "Owner"), ("branch_code", "Branch code"), ("margin_pct", "Margin (%)"),
                    ("lead_source", "Lead source"), ("loss_reason", "Loss reason"), ("created_at", "Created"),
                    ("modified_at", "Last modified"), ("exclude_from_reporting", "Exclude from reporting"), ("id", "Record ID")],
    "account": [("name", "Account name"), ("segment", "Segment"), ("city", "City"), ("state", "State"),
                ("branch_code", "Branch code"), ("created_at", "Created"), ("id", "Record ID")],
    "invoice": [("number", "Invoice no."), ("customer", "Customer"), ("invoice_date", "Invoice date"), ("due_date", "Due date"),
                ("amount", "Total"), ("amount_paid", "Amount paid"), ("paid_date", "Paid date"), ("reference", "Reference"),
                ("memo", "Memo"), ("id", "Record ID")],
    "customer": [("name", "Display name"), ("crm_account_id", "CRM account ID"), ("terms_days", "Payment terms (days)"),
                 ("id", "Record ID")],
}


def _fmt_field(key, v):
    if v is None or v == "":
        return '<span class="muted">(blank)</span>'
    if key in ("amount", "amount_paid"):
        return money(v)
    if isinstance(v, bool):
        return "Yes" if v else "No"
    if isinstance(v, dt.datetime):
        return esc(_local(v))
    if isinstance(v, dt.date):
        return esc(ui.date(v))
    return esc(v)


def demo_source(request, system: str, obj: str, rec_id: str):
    scope = scope_of(request)
    hist, related = [], ""
    if system == "crm" and obj == "opportunity":
        r = db.one("""SELECT o.*, a.name AS account, u.name AS owner FROM crm.opportunities o
                      LEFT JOIN crm.accounts a ON a.id = o.account_id LEFT JOIN crm.users u ON u.id = o.owner_id
                      WHERE o.id = %(i)s""", {"i": rec_id})
        if r and scope and r["branch_code"] not in scope:
            r = None
        if r:
            hist = db.query("""SELECT field, old_value, new_value, changed_at FROM crm.opportunity_history
                               WHERE opportunity_id = %(i)s ORDER BY changed_at""", {"i": rec_id})
            inv = db.query("SELECT id, number, invoice_date, amount, amount_paid FROM acct.invoices WHERE reference = %(i)s ORDER BY invoice_date",
                           {"i": rec_id})
            if inv:
                related = ("<h3>Invoices in accounting that reference this deal</h3><ul class=\"list\">" + "".join(
                    f'<li>{ui.source_link("accounting_invoice", x["id"], "Invoice " + x["number"])}'
                    f'<span class="amt">{ui.date(x["invoice_date"])} · {money(x["amount"])}'
                    f'{" · paid" if x["amount_paid"] else " · unpaid"}</span></li>' for x in inv) + "</ul>")
        system_name, kind = "CRM", "opportunity"
    elif system == "crm" and obj == "account":
        r = db.one("SELECT * FROM crm.accounts WHERE id = %(i)s", {"i": rec_id})
        if r and scope and r["branch_code"] not in scope:
            r = None
        system_name, kind = "CRM", "account"
    elif system == "accounting" and obj == "invoice":
        r = db.one("""SELECT i.*, c.name AS customer FROM acct.invoices i LEFT JOIN acct.customers c ON c.id = i.customer_id
                      WHERE i.id = %(i)s""", {"i": rec_id})
        if r and scope and not db.one("SELECT 1 AS ok FROM rpt.invoices WHERE id = %(i)s AND branch_code = ANY(%(s)s)",
                                      {"i": rec_id, "s": scope}):
            r = None
        system_name, kind = "Accounting", "invoice"
    elif system == "accounting" and obj == "customer":
        r = db.one("SELECT * FROM acct.customers WHERE id = %(i)s", {"i": rec_id})
        if r and scope and not db.one("SELECT 1 AS ok FROM rpt.invoices WHERE customer_id = %(i)s AND branch_code = ANY(%(s)s) LIMIT 1",
                                      {"i": rec_id, "s": scope}):
            r = None
        system_name, kind = "Accounting", "customer"
    else:
        r, system_name, kind = None, "", ""
    if not r:
        return ui.page(request, "Record not found", '<section class="card">That record isn\'t there, or you don\'t have access to it.</section>')
    kv = "".join(f"<dt>{esc(label)}</dt><dd>{_fmt_field(key, r.get(key))}</dd>" for key, label in FIELD_LABELS[kind])
    labels = {"StageName": "Stage", "CloseDate": "Close date", "Amount": "Amount"}
    def hv(field, v):
        if field == "Amount" and v:
            return money(v)
        if field == "CloseDate" and v:
            return esc(ui.date(v))
        return esc(v)
    h = "".join(f'<tr><td class="n">{esc(_local(c["changed_at"]))}</td><td>{esc(labels.get(c["field"], c["field"]))}</td>'
                f'<td>{hv(c["field"], c["old_value"])}</td><td>{hv(c["field"], c["new_value"])}</td></tr>' for c in hist)
    hist_html = (f'<h3>Field history</h3><div class="scroll"><table class="data"><thead><tr><th class="n">When</th>'
                 f'<th>Field</th><th>From</th><th>To</th></tr></thead><tbody>{h}</tbody></table></div>') if hist else ""
    title = r.get("name") or r.get("number") or rec_id
    body = f"""<div class="fake-src"><div class="fake-src-head"><span class="pill warn">Stand-in {esc(system_name)}</span>
<span class="muted">With a real client, this link opens the record in their own system (Salesforce, HubSpot, QuickBooks and so on).</span></div>
<dl class="kv">{kv}</dl>{related}{hist_html}</div>"""
    return ui.page(request, f"{kind.capitalize()}: {title}", body, subtitle=f"{system_name} record")
