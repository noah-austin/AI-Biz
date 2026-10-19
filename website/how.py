"""'See how it works': a typical company's systems flow into one hub; open what the hub caught this week.

Pure HTML and CSS (the site runs no scripts): the cards are <details>. The examples are generic and illustrative.
"""
from html import escape as esc

from .visuals import icon

# The systems a typical company runs, and three things the hub caught. A preview is ("bars", title,
# [(label, value, highlight)], unit, goal or None) or ("line", title, [values], [first label, last label], unit)
# or ("brief", title, [lines]).
SYSTEMS = [("people", "CRM"), ("dollar", "Accounting"), ("clipboard", "Operations app"), ("box", "Inventory"),
           ("id", "HR & payroll"), ("sheet", "Spreadsheets")]

CATCHES = [
    ("bell", "Alert", "One location is answering urgent requests late",
     "It's two people short since summer, so overtime is up and customers wait. Every other location is on goal.",
     ("bars", "Urgent requests handled on time, last 30 days", [("Location A", 93, False), ("Location B", 91, False),
                                                                ("Location C", 74, True), ("Location D", 90, False),
                                                                ("Location E", 95, False)], "%", 90)),
    ("chart", "Dashboard", "Margin on your top product line slid from 23% to 17% in a year",
     "The supplier raised costs about 10%, and nobody passed it on to customers.",
     ("line", "Gross margin, top product line", [23.0, 22.6, 22.2, 21.8, 21.4, 20.9, 20.3, 19.8, 19.1, 18.5, 17.8, 17.0],
      ["A year ago", "Now"], "%")),
    ("agent", "AI brief", "This morning's brief, written before anyone got in",
     "An AI agent reads every system overnight and leaves a short list of what needs attention.",
     ("brief", "Daily brief, 6:30 AM", ["$101K of finished work still isn't invoiced after 14 days.",
                                        "Two fast-moving items will run out before the next delivery.",
                                        "One customer's payments have slowed from 30 to 55 days.",
                                        "Two employees are working on an expired certification."])),
]

def _w(value, top) -> int:
    """Bar width as a 5% step (the site allows no inline styles, so widths are classes)."""
    return max(5, min(100, int(round(100 * value / top / 5) * 5)))


def _preview(p) -> str:
    kind = p[0]
    if kind == "bars":
        _k, title, rows, unit, goal = p
        top = 100 if unit == "%" and max(v for _l, v, _h in rows) > 20 else max(v for _l, v, _h in rows) * 1.25
        bars = "".join(f'<li class="{"hl" if hl else ""}"><span class="pl">{esc(label)}</span><span class="pt"><i class="w{_w(v, top)}"></i></span>'
                       f'<b>{v:g}{unit}</b></li>' for label, v, hl in rows)
        goal_txt = f'<p class="pv-note">Goal {goal}{unit}</p>' if goal else ""
        return f'<div class="pv"><p class="pv-title">{esc(title)}</p><ul class="pv-bars">{bars}</ul>{goal_txt}</div>'
    if kind == "line":
        _k, title, values, (first, last), unit = p
        lo, hi = min(values), max(values)
        span = (hi - lo) or 1
        pts = " ".join(f"{8 + i * (284 / (len(values) - 1)):.1f},{12 + (hi - v) / span * 76:.1f}" for i, v in enumerate(values))
        end_x, end_y = pts.split()[-1].split(",")
        return (f'<div class="pv"><p class="pv-title">{esc(title)}</p>'
                f'<svg class="pv-line" viewBox="0 0 300 100" role="img" aria-label="{esc(title)}: from {values[0]:g}{unit} to {values[-1]:g}{unit}">'
                f'<line class="pv-grid" x1="8" y1="88" x2="292" y2="88"/><polyline class="pv-path" points="{pts}"/>'
                f'<circle class="pv-dot" cx="{end_x}" cy="{end_y}" r="4"/></svg>'
                f'<p class="pv-axis"><span>{esc(first)} · {values[0]:g}{unit}</span><span>{esc(last)} · <b>{values[-1]:g}{unit}</b></span></p></div>')
    _k, title, lines = p
    items = "".join(f"<li>{esc(x)}</li>" for x in lines)
    return f'<div class="pv brief"><p class="pv-title">{icon("agent")}{esc(title)}</p><ol>{items}</ol></div>'


def how_it_works() -> str:
    systems = "".join(f'<li class="s{k}">{icon(ic)}<span>{esc(name)}</span></li>' for k, (ic, name) in enumerate(SYSTEMS))
    cards = "".join(
        f'<details class="catch c{k}"><summary><span class="catch-kind">{icon(ic)}{esc(kind)}</span>'
        f'<strong>{esc(head)}</strong><span class="catch-why">{esc(why)}</span>'
        f'<span class="catch-open">See the screen</span></summary>{_preview(pv)}</details>'
        for k, (ic, kind, head, why, pv) in enumerate(CATCHES))
    return f"""<section class="how-section" id="how-it-works"><div class="wrap">
  <header class="sec-head center"><p class="eyebrow">See how it works</p><h2>From scattered systems to answers</h2>
  <p class="lead">Your systems flow into one hub. Then it starts telling you things, every morning, before anyone asks.</p></header>
  <div class="how-panel">
  <div class="how-step how-systems"><p class="how-label">1 · Your systems</p><ul>{systems}</ul></div>
  <div class="how-pipe" aria-hidden="true"><i></i></div>
  <div class="how-step how-core"><p class="how-label">2 · One hub</p>
    <div class="how-hub">{icon("db")}<strong>Your data hub</strong><span>connected, cleaned, one set of numbers</span></div>
    <p class="how-outs">Scorecard · Dashboards · Alerts · AI agents</p></div>
  <div class="how-pipe" aria-hidden="true"><i></i></div>
  <div class="how-step how-catches"><p class="how-label">3 · What it caught this week</p>{cards}</div>
  <p class="how-foot">Illustrative examples. Open a card to see the screen.</p>
  </div>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Book a call</a>
    <a class="btn ghost" href="/contact?interest=demo">Request a live demo →</a></div>
</div></section>"""
