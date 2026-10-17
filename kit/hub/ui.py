"""Shared look and helpers for every hub page: one header, one set of styles.

Pages are plain HTML strings. Everything that comes from data goes through
esc() before it's placed in a page.
"""
import datetime as dt
import html
import json

from ..config import get_settings

CHART_JS = "/static/vendor/chart-4.4.1.umd.js"  # pinned copy, MIT licence; no outside CDN needed

PRACTICE_NAV = [
    ("/", "Today", False),
    ("/inbox", "Inbox", False),
    ("/pipeline", "Pipeline", False),
    ("/clients", "Clients", False),
    ("/tasks", "Tasks", False),
    ("/time", "Time", False),
    ("/money", "Money", False),
    ("/agents", "Agents", False),
]
NAV = [  # path, label, admin only
    ("/", "Home", False),
    ("/scorecard", "Scorecard", False),
    ("/deals?status=open", "Pipeline", False),
    ("/winloss", "Win / loss", False),
    ("/receivables", "Receivables", False),
    ("/cleanup", "Clean-up", False),
    ("/health", "Health", True),
]


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def money(v, compact=False) -> str:
    if v is None:
        return "—"
    v = float(v)
    sign = "-" if v < 0 else ""
    a = abs(v)
    if compact:
        if a >= 1e6:
            return f"{sign}${a / 1e6:.1f}M"
        if a >= 1e3:
            return f"{sign}${a / 1e3:.0f}K"
    return f"{sign}${a:,.0f}"


def pct(v, digits=1) -> str:
    return "—" if v is None else f"{float(v) * 100:.{digits}f}%"


def num(v) -> str:
    return "—" if v is None else f"{float(v):,.0f}"


def date(d) -> str:
    if not d:
        return "—"
    if isinstance(d, str):
        d = dt.date.fromisoformat(d[:10])
    return d.strftime("%b %-d, %Y")


def short_date(d) -> str:
    return d.strftime("%b %-d") if d else "—"


def source_link(kind: str, rec_id, label) -> str:
    """Link a record back to the system it lives in, in a new tab."""
    tmpl = get_settings().client.get("links", {}).get(kind)
    if not tmpl or rec_id is None:
        return esc(label)
    url = tmpl.format(id=rec_id)
    return (f'<a href="{esc(url)}" target="_blank" rel="noopener" class="src">{esc(label)}'
            f'<span class="ext" aria-hidden="true">↗</span></a>')


def delta(cur, prev, higher_is_better=True, label="vs last year", title="") -> str:
    if cur is None or not prev:
        return f'<span class="delta muted">no comparison {esc(label)}</span>'
    change = (float(cur) - float(prev)) / abs(float(prev))
    up = change >= 0
    good = up == higher_is_better
    arrow = "▲" if up else "▼"
    cls = "good" if good else "bad"
    return (f'<span class="delta {cls}" title="{esc(title)}"><span aria-hidden="true">{arrow}</span> '
            f'{abs(change) * 100:.1f}% <span class="muted">{esc(label)}</span></span>')


def points_delta(cur, prev, label="vs same period last year") -> str:
    """For percentages: show the change in percentage points, not a % of a %."""
    if cur is None or prev is None:
        return f'<span class="delta muted">no comparison {esc(label)}</span>'
    diff = (float(cur) - float(prev)) * 100
    cls = "good" if diff >= 0 else "bad"
    arrow = "▲" if diff >= 0 else "▼"
    return (f'<span class="delta {cls}"><span aria-hidden="true">{arrow}</span> {abs(diff):.1f} pts '
            f'<span class="muted">{esc(label)}</span></span>')


def how(text: str) -> str:
    return f'<details class="how"><summary>How this is counted</summary><p>{esc(text)}</p></details>'


def tile(label, value, sub="", link=None, how_text=None) -> str:
    inner = f'<div class="tile-label">{esc(label)}</div><div class="tile-value">{value}</div>'
    if sub:
        inner += f'<div class="tile-sub">{sub}</div>'
    body = f'<a class="tile-link" href="{esc(link)}">{inner}</a>' if link else inner
    return f'<div class="tile">{body}{how(how_text) if how_text else ""}</div>'


def status_pill(status: str) -> str:
    icons = {"ok": ("✓", "good", "OK"), "warning": ("!", "warn", "Warning"), "failed": ("✕", "bad", "Failed"),
             "stale": ("!", "warn", "Out of date")}
    icon, cls, label = icons.get(status, ("?", "warn", status or "Unknown"))
    return f'<span class="pill {cls}"><span aria-hidden="true">{icon}</span> {esc(label)}</span>'


def chart(canvas_id: str, config: dict, height=260, label="Chart") -> str:
    """A Chart.js chart. Colors are filled in by hub.js from the theme tokens."""
    payload = json.dumps(config, default=str).replace("</", "<\\/")  # never let data close the <script>
    return (f'<div class="chart" style="height:{height}px"><canvas id="{esc(canvas_id)}" role="img" '
            f'aria-label="{esc(label)}"></canvas></div>'
            f'<script>window.hubCharts=window.hubCharts||[];window.hubCharts.push({{id:{json.dumps(canvas_id)},'
            f'config:{payload}}});</script>')


ASK_BUTTON = ('<button type="button" class="ask-open" data-ask-open aria-controls="ask" aria-expanded="false">'
              '<span aria-hidden="true">✦</span> Ask AI</button>')
ASK_PANEL = """<aside id="ask" class="ask" hidden aria-label="Ask AI about the numbers">
  <div class="ask-head"><strong>Ask about the numbers</strong>
    <span><button type="button" class="linkish" data-ask-new>New chat</button>
    <button type="button" class="ask-x" data-ask-close aria-label="Close">✕</button></span></div>
  <div class="ask-thread" id="ask-thread" aria-live="polite"></div>
  <form class="ask-form" id="ask-form"><label class="sr" for="ask-q">Your question</label>
    <textarea id="ask-q" rows="2" maxlength="2000" placeholder="Ask about sales, pipeline, billing…"></textarea>
    <button class="primary" type="submit">Ask</button></form>
  <p class="ask-foot">Answers come from this hub's data, with links to check them. The AI can read, never change anything.</p>
</aside>"""


def page(request, title: str, body: str, active: str = "", subtitle: str = "", wide=False) -> str:
    settings = get_settings()
    client = settings.client
    user = getattr(request.state, "user", None)
    nav = []
    apps = settings.apps
    items = (PRACTICE_NAV if "practice" in apps else []) + (
        [n for n in NAV if n[1] != "Health" and not ("practice" in apps and n[0] == "/")] if "analytics" in apps else [])
    items.append(NAV[-1])  # Health
    for path, label, admin_only in items:
        if admin_only and (not user or user["role"] != "admin"):
            continue
        cur = ' aria-current="page"' if active == label else ""
        nav.append(f'<a href="{path}"{cur}>{esc(label)}</a>')
    who = ""
    if user:
        scope = "All branches" if not user["branches"] else ", ".join(user["branches"])
        who = (f'<div class="who"><span title="{esc(scope)}">{esc(user["name"])}</span>'
               f'<form method="post" action="/logout"><button type="submit" class="linkish">Sign out</button></form></div>')
    alert_bar = ""
    if user and user["role"] == "admin":
        from ..alerts import open_alerts
        found = open_alerts()
        if found:
            worst = "critical" if any(a["severity"] == "critical" for a in found) else "warning"
            alert_bar = (f'<a class="alert-banner {worst}" href="/health#alerts"><span aria-hidden="true">!</span> '
                         f'{esc(found[0]["message"])}{f" (+{len(found) - 1} more)" if len(found) > 1 else ""}</a>')
    demo = ('<div class="demo-banner">Demo company with made-up data. Bluestem Facility Services is fictional.'
            + (' You\'re looking around as a guest.' if user and user["email"].endswith("@demo.invalid") else "")
            + '</div>' if settings.is_demo else "")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {esc(client.get("short_name", "Hub"))}</title>
<link rel="stylesheet" href="/static/hub.css"><link rel="icon" href="/static/icon.svg" type="image/svg+xml">
<script src="{CHART_JS}" defer></script><script src="/static/hub.js" defer></script><script src="/static/ask.js" defer></script>
</head><body>
{demo}{alert_bar}
<header class="top"><div class="bar">
  <a class="brand" href="/"><span class="mark" aria-hidden="true"></span>{esc(client.get("short_name", "Hub"))} <span class="muted">Hub</span></a>
  <nav>{"".join(nav)}</nav>{ASK_BUTTON if user else ""}{who}
</div></header>
<main class="{'wide' if wide else ''}">
<div class="page-head"><h1>{esc(title)}</h1>{f'<p class="subtitle">{subtitle}</p>' if subtitle else ''}</div>
{body}
</main>
{ASK_PANEL if user else ""}
</body></html>"""


def bare_page(title: str, body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(title)}</title>
<link rel="stylesheet" href="/static/hub.css"><link rel="icon" href="/static/icon.svg" type="image/svg+xml"></head><body class="bare">{body}</body></html>"""
