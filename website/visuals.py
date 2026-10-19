"""Graphics for the website: icons, the "systems -> one place -> put to work" diagram, and small example screens.

Everything is inline SVG or plain HTML styled by static/site.css (the site's security policy allows no inline styles
or scripts), so it follows light and dark mode. All example figures are made up; most match the fictional Bluestem demo.
"""

# 24x24 stroke icons, drawn with currentColor.
_ICONS = {
    "db": '<ellipse cx="12" cy="5.5" rx="7.5" ry="2.8"/><path d="M4.5 5.5v13c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8v-13"/><path d="M4.5 12c0 1.6 3.4 2.8 7.5 2.8s7.5-1.2 7.5-2.8"/>',
    "people": '<circle cx="9" cy="8" r="3.4"/><path d="M2.8 20a6.2 6.2 0 0 1 12.4 0"/><path d="M15.5 4.8a3.4 3.4 0 0 1 0 6.4M17.6 14.2A6 6 0 0 1 21.2 20"/>',
    "dollar": '<circle cx="12" cy="12" r="9"/><path d="M15 9.4c-.5-.9-1.6-1.4-3-1.4-1.7 0-3 .8-3 2s1.3 1.6 3 2 3 .8 3 2-1.3 2-3 2c-1.4 0-2.5-.5-3-1.4M12 6v2M12 16v2"/>',
    "factory": '<path d="M3 21V10.5l6 3.5v-3.5l6 3.5V5h6v16z"/><path d="M7 17.5h2M12 17.5h2M17 17.5h1.5"/>',
    "clipboard": '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V2.8h6V4M8.5 10h7M8.5 14h7M8.5 18h4"/>',
    "id": '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="9" cy="11" r="2.2"/><path d="M5.6 16.2a3.5 3.5 0 0 1 6.8 0M14.5 10h4M14.5 13.5h4"/>',
    "sheet": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9.5h18M3 14.8h18M9 4v16M15 4v16"/>',
    "truck": '<path d="M2.5 6h11v10h-11zM13.5 9.5h4.2l3 3.4V16h-7.2"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    "box": '<path d="M12 2.8 20.5 7v10L12 21.2 3.5 17V7z"/><path d="M3.5 7 12 11.2 20.5 7M12 11.2v10"/>',
    "cart": '<path d="M2.5 3.5h3l2.2 11h10.6l2-7.5H6.6"/><circle cx="9" cy="19" r="1.6"/><circle cx="17" cy="19" r="1.6"/>',
    "megaphone": '<path d="M3.5 10v4h3l7 4.5v-13l-7 4.5z"/><path d="M17 9a4 4 0 0 1 0 6M6.5 14l1.2 5.5h2.8L9.6 15.4"/>',
    "headset": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="13.5" width="4" height="6" rx="1.5"/><rect x="17" y="13.5" width="4" height="6" rx="1.5"/><path d="M19 19.5c0 1.3-2 2-4.5 2H12"/>',
    "chart": '<path d="M3.5 20.5h17"/><rect x="5" y="11" width="3" height="7" rx=".8"/><rect x="10.5" y="5" width="3" height="13" rx=".8"/><rect x="16" y="8.5" width="3" height="9.5" rx=".8"/>',
    "scorecard": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 13.5l1.6 1.6L12.5 12M8 17h.01M14.5 13.5H18M14.5 17H18"/>',
    "bell": '<path d="M6 16.5v-5a6 6 0 1 1 12 0v5l1.8 1.8H4.2z"/><path d="M10 20.8a2.1 2.1 0 0 0 4 0"/>',
    "spark": '<path d="M12 3.2 13.9 8.6 19.3 10.5 13.9 12.4 12 17.8 10.1 12.4 4.7 10.5 10.1 8.6z"/><path d="M18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>',
    "agent": '<rect x="4.5" y="8" width="15" height="11.5" rx="3.2"/><path d="M12 8V4.6"/><circle cx="12" cy="3.6" r="1.1"/><path d="M9.2 13h.01M14.8 13h.01M9.6 16.2h4.8M2.5 12.5v3M21.5 12.5v3"/>',
    "blocks": '<rect x="3" y="3" width="8" height="8" rx="1.6"/><rect x="13" y="3" width="8" height="8" rx="1.6"/><rect x="3" y="13" width="8" height="8" rx="1.6"/><path d="M17 13.5v7M13.5 17h7"/>',
    "chat": '<path d="M4 4.5h16v11.5H9.5L4 20.5z"/><path d="M8 9h8M8 12.5h5"/>',
    "doc": '<path d="M6 2.8h8.6L19 7.2V21H6z"/><path d="M14 2.8v5h5M9 12.5h7M9 16.5h7"/>',
    "refresh": '<path d="M19.6 10.5A8 8 0 0 0 5.3 7.2L4 8.8"/><path d="M4 3.8v5h5"/><path d="M4.4 13.5a8 8 0 0 0 14.3 3.3l1.3-1.6"/><path d="M20 20.2v-5h-5"/>',
    "shield": '<path d="M12 2.8 19.5 5.6v6c0 4.8-3.3 8-7.5 9.6-4.2-1.6-7.5-4.8-7.5-9.6v-6z"/><path d="M8.8 12l2.2 2.2 4.3-4.4"/>',
    "server": '<rect x="3" y="3.5" width="18" height="7.5" rx="2"/><rect x="3" y="13" width="18" height="7.5" rx="2"/><path d="M7 7.3h.01M7 16.8h.01M11 7.3h6M11 16.8h6"/>',
    "cloud": '<path d="M7 18.5a4.3 4.3 0 0 1-.6-8.6 6 6 0 0 1 11.6 1.4 3.6 3.6 0 0 1-.4 7.2z"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.2 8.5-6.2"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.2l3.4 2"/>',
    "check": '<path d="m5 12.5 4.2 4.2L19 7"/>',
    "x": '<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>',
    "cursor": '<path d="M5 3.5 18.5 11l-6 1.5L9.2 18.5z"/>',
    "lock": '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7M12 14.5v2.5"/>',
    "search": '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/>',
    "calendar": '<rect x="3" y="4.5" width="18" height="16" rx="2"/><path d="M3 9.5h18M8 2.8v3.4M16 2.8v3.4M7.5 13.5h3M13.5 13.5h3M7.5 17h3"/>',
    "book": '<path d="M4 4.5h6.5a2.5 2.5 0 0 1 2.5 2.5v13a2 2 0 0 0-2-2H4zM20 4.5h-6.5A2.5 2.5 0 0 0 11 7"/><path d="M20 4.5v13.5h-7"/>',
}


def icon(name: str, cls: str = "ico") -> str:
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_ICONS[name]}</svg>')


def _svg_icon(name: str, x: float, y: float, size: float = 20, cls: str = "d-ico") -> str:
    s = size / 24
    return (f'<g class="{cls}" transform="translate({x} {y}) scale({s:.3f})" fill="none" stroke="currentColor" '
            f'stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">{_ICONS[name]}</g>')


SOURCES = [("people", "CRM"), ("dollar", "Accounting"), ("factory", "ERP"), ("clipboard", "Projects"),
           ("id", "HR & payroll"), ("sheet", "Spreadsheets")]
OUTPUTS = [("scorecard", "Scorecard"), ("chart", "Dashboards"), ("bell", "Alerts"), ("spark", "Ask AI"),
           ("agent", "AI agents")]


def hub_diagram() -> str:
    """The home-page hero graphic. A wide SVG on desktop; a stacked HTML version on phones."""
    w, pill_w, pill_h = 620, 158, 42
    hub_x, hub_y, hub_r = 310, 222, 66
    src_y = [27 + i * 69 for i in range(len(SOURCES))]           # pill tops
    out_y = [49 + i * 76 for i in range(len(OUTPUTS))]
    parts = [f'<svg class="hub-diagram" viewBox="0 0 {w} 444" role="img" '
             'aria-label="Your systems (CRM, accounting, ERP, projects, HR, spreadsheets) flow into your data hub, which '
             'powers a scorecard, dashboards, alerts, Ask AI and AI agents.">']
    for i, y in enumerate(src_y):                                   # wires in
        cy = y + pill_h / 2
        ey = hub_y + (i - 2.5) * 14
        ex = hub_x - (hub_r ** 2 - (ey - hub_y) ** 2) ** 0.5 + 3
        d = f"M{pill_w} {cy} C {pill_w + 70} {cy}, {ex - 60} {ey}, {ex:.1f} {ey:.1f}"
        parts.append(f'<path class="d-wire" d="{d}"/><path class="d-flow d{i}" d="{d}"/>')
    for i, y in enumerate(out_y):                                   # wires out
        cy = y + pill_h / 2
        x0 = w - pill_w
        sy = hub_y + (i - 2) * 16
        sx = hub_x + (hub_r ** 2 - (sy - hub_y) ** 2) ** 0.5 - 3
        d = f"M{sx:.1f} {sy:.1f} C {sx + 60:.1f} {sy}, {x0 - 70} {cy}, {x0} {cy}"
        parts.append(f'<path class="d-wire out" d="{d}"/><path class="d-flow out d{i}" d="{d}"/>')
    for (ic, label), y in zip(SOURCES, src_y):
        parts.append(f'<rect class="d-pill" x="1" y="{y}" width="{pill_w - 2}" height="{pill_h}" rx="21"/>'
                     + _svg_icon(ic, 15, y + 11) + f'<text class="d-label" x="45" y="{y + 26.5}">{label}</text>')
    for i, ((ic, label), y) in enumerate(zip(OUTPUTS, out_y)):
        x0 = w - pill_w
        parts.append(f'<rect class="d-pill out o{i}" x="{x0 + 1}" y="{y}" width="{pill_w - 2}" height="{pill_h}" rx="21"/>'
                     + _svg_icon(ic, x0 + 15, y + 11, cls="d-ico out") + f'<text class="d-label" x="{x0 + 45}" y="{y + 26.5}">{label}</text>')
    parts.append(f'<circle class="d-halo" cx="{hub_x}" cy="{hub_y}" r="{hub_r + 14}"/>'
                 f'<circle class="d-hub" cx="{hub_x}" cy="{hub_y}" r="{hub_r}"/>'
                 + _svg_icon("db", hub_x - 17, hub_y - 34, 34, "d-ico hub")
                 + f'<text class="d-hub-label" x="{hub_x}" y="{hub_y + 22}" text-anchor="middle">Your data hub</text>'
                 f'<text class="d-hub-sub" x="{hub_x}" y="{hub_y + 40}" text-anchor="middle">every system</text>')
    parts.append(f'<text class="d-col" x="{pill_w / 2}" y="12" text-anchor="middle">YOUR SYSTEMS</text>'
                 f'<text class="d-col" x="{w - pill_w / 2}" y="12" text-anchor="middle">PUT TO WORK</text></svg>')
    return f'<div class="hero-visual">{"".join(parts).replace("hub-diagram", "hub-diagram wide", 1)}{_hub_diagram_tall()}</div>'


def _hub_diagram_tall() -> str:
    """The same hero graphic for phones: systems above, the hub in the middle, what it powers below. The wires run
    behind the pills, from each one to the hub and from the hub to each output."""
    w, pill_w, pill_h = 360, 168, 40
    hub_x, hub_y, hub_r = 180, 268, 58
    src = [(4 + (i % 2) * 184, 24 + (i // 2) * 50) for i in range(len(SOURCES))]
    out = [(4 + (i % 2) * 184, 392 + (i // 2) * 50) for i in range(4)] + [(96, 492)]
    parts = [f'<svg class="hub-diagram tall" viewBox="0 0 {w} 540" aria-hidden="true">']
    for i, (x, y) in enumerate(src):                                 # wires in, to the top of the hub
        cx, ey = x + pill_w / 2, hub_y - hub_r + 3
        ex = hub_x + (1 if i % 2 else -1) * (6 + (2 - i // 2) * 10)   # left pills enter left of centre, top rows outermost
        d = f"M{cx} {y + pill_h / 2} C {cx} {y + 110}, {ex} {ey - 70}, {ex} {ey}"
        parts.append(f'<path class="d-wire" d="{d}"/><path class="d-flow d{i}" d="{d}"/>')
    for i, (x, y) in enumerate(out):                                 # wires out, from the bottom of the hub
        cx, sy = x + pill_w / 2, hub_y + hub_r - 3
        sx = hub_x + (0 if i == 4 else (1 if i % 2 else -1) * (8 + i // 2 * 10))
        d = f"M{sx} {sy} C {sx} {sy + 60}, {cx} {y - 60}, {cx} {y + pill_h / 2}"
        parts.append(f'<path class="d-wire out" d="{d}"/><path class="d-flow out d{i}" d="{d}"/>')
    for (ic, label), (x, y) in zip(SOURCES, src):
        parts.append(f'<rect class="d-pill" x="{x}" y="{y}" width="{pill_w}" height="{pill_h}" rx="20"/>'
                     + _svg_icon(ic, x + 14, y + 10) + f'<text class="d-label" x="{x + 44}" y="{y + 25.5}">{label}</text>')
    for (ic, label), (x, y) in zip(OUTPUTS, out):
        parts.append(f'<rect class="d-pill out" x="{x}" y="{y}" width="{pill_w}" height="{pill_h}" rx="20"/>'
                     + _svg_icon(ic, x + 14, y + 10, cls="d-ico out") + f'<text class="d-label" x="{x + 44}" y="{y + 25.5}">{label}</text>')
    parts.append(f'<circle class="d-halo tall" cx="{hub_x}" cy="{hub_y}" r="{hub_r + 13}"/>'
                 f'<circle class="d-hub" cx="{hub_x}" cy="{hub_y}" r="{hub_r}"/>'
                 + _svg_icon("db", hub_x - 15, hub_y - 31, 30, "d-ico hub")
                 + f'<text class="d-hub-label" x="{hub_x}" y="{hub_y + 18}" text-anchor="middle">Your data hub</text>'
                 f'<text class="d-hub-sub" x="{hub_x}" y="{hub_y + 35}" text-anchor="middle">every system</text>'
                 f'<text class="d-col" x="{w / 2}" y="12" text-anchor="middle">YOUR SYSTEMS</text>'
                 f'<rect class="d-tag" x="{w / 2 - 50}" y="{hub_y + hub_r + 24}" width="100" height="18" rx="9"/>'
                 f'<text class="d-col" x="{w / 2}" y="{hub_y + hub_r + 37}" text-anchor="middle">PUT TO WORK</text></svg>')
    return "".join(parts)



def _window(title: str, body: str, cls: str = "") -> str:
    """A small app-window frame around an example screen."""
    return (f'<div class="mock {cls}"><div class="mock-bar"><i></i><i></i><i></i><span>{title}</span></div>'
            f'<div class="mock-body">{body}</div></div>')


def before_after() -> str:
    cells = [["", "Q3", "Q4", "Total"], ["Bookings", "4,212", "3,870", "8,082"], ["Billed", "3,955", "#REF!", "#REF!"],
             ["Cash", "3,610", "3,402", "7,012"], ["Pipeline", "18.9", "??", ""]]
    grid = "".join("<tr>" + "".join(f'<td class="{"bad" if "#" in v or "?" in v else ""}">{v}</td>' for v in row) + "</tr>"
                   for row in cells)
    sheet = _window("leadership_report_v7_FINAL(2).xlsx", f'<table class="mini-sheet">{grid}</table>', "sheet")
    kpis = [("Bookings", "$664K", "up"), ("Billed", "$2.3M", "up"), ("Cash collected", "$532K", "up"), ("Win rate", "36.1%", "up")]
    tiles = "".join(f'<div class="kpi"><span>{k}</span><strong>{v}</strong><em class="{t}">on goal</em></div>' for k, v, t in kpis)
    before_list = "".join(f'<li>{icon("x")}{t}</li>' for t in
                          ["Data in ten places", "Monday is report day", "Two meetings, two numbers", "AI that knows nothing about you"])
    after_list = "".join(f'<li>{icon("check")}{t}</li>' for t in
                         ["Every system in one place", "Reports that build themselves", "One number everyone agrees on",
                          "AI that knows your business"])
    return f"""<div class="ba">
  <div class="ba-col before">
    <p class="ba-tag">Before</p>
    <div class="ba-stage">
      {sheet}
      <div class="note n1">Sales says<b>$4.2M</b></div>
      <div class="note n2">Finance says<b>$3.9M</b></div>
    </div>
    <ul class="ba-list">{before_list}</ul>
  </div>
  <div class="ba-arrow" aria-hidden="true"><span>{icon("refresh")}</span></div>
  <div class="ba-col after">
    <p class="ba-tag">After</p>
    <div class="ba-stage">
      <div class="notif">{icon("mail")}<div><strong>Your weekly scorecard is ready</strong><span>Monday 6:45 AM · built from 6 systems</span></div></div>
      <div class="kpis">{tiles}</div>
    </div>
    <ul class="ba-list">{after_list}</ul>
  </div>
</div>"""


def _spark(points: list[float], cls: str = "spark") -> str:
    lo, hi = min(points), max(points)
    xs = [i * 60 / (len(points) - 1) for i in range(len(points))]
    ys = [20 - (p - lo) / ((hi - lo) or 1) * 16 for p in points]
    d = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(zip(xs, ys)))
    return f'<svg class="{cls}" viewBox="-2 0 64 24" aria-hidden="true"><path d="{d}"/><circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.4"/></svg>'


def mock_foundation() -> str:
    chips = "".join(f'<span class="chip sm">{icon(i)}{l}</span>' for i, l in SOURCES[:4])
    return _window("Your data hub", f"""<div class="found">
  <div class="found-chips">{chips}</div>
  <div class="found-flow" aria-hidden="true"><i></i><i></i><i></i></div>
  <div class="found-db">{icon("db")}<div><strong>All your data</strong><span class="live">Updated 6 min ago</span></div></div>
  <div class="def"><b>Revenue</b> = invoices issued in the period, by issue date. <em>Defined once, used everywhere.</em></div>
</div>""")


def mock_scorecard() -> str:
    rows = [("Deals", [31, 31, 26, 30], 25, "{}"), ("Booked", [761, 561, 668, 664], 500, "${}K"),
            ("Billed", [2.3, 2.5, 2.4, 2.3], 1.9, "${}M"), ("Cash", [417, 494, 306, 532], 450, "${}K")]
    head = "".join(f"<th>{w}</th>" for w in ["Sep 14", "Sep 21", "Sep 28", "Oct 5"])
    body = ""
    for name, vals, goal, fmt in rows:
        cells = "".join(f'<td class="{"hit" if v >= goal else "miss"}">{fmt.format(v)}</td>' for v in vals)
        body += f"<tr><th>{name}</th>{cells}</tr>"
    return _window("Weekly scorecard", f'<table class="mini-score"><thead><tr><th></th>{head}</tr></thead><tbody>{body}</tbody></table>'
                   '<p class="mock-foot">Green: goal hit. Fills itself in every hour.</p>')


def mock_dashboard() -> str:
    this = [0.9, 1.7, 1.6, 1.9, 2.7, 2.1, 1.5, 3.0, 3.3, 1.3]
    last = [1.9, 0.8, 2.0, 1.0, 1.8, 2.3, 4.0, 1.6, 2.2, 1.8]
    bars = []
    for i, (a, b) in enumerate(zip(this, last)):
        x = 8 + i * 26
        bars.append(f'<rect class="bar-b" x="{x + 10}" y="{100 - b * 22:.1f}" width="9" height="{b * 22:.1f}" rx="2"/>'
                    f'<rect class="bar-a{" hl" if i == 8 else ""}" x="{x}" y="{100 - a * 22:.1f}" width="9" height="{a * 22:.1f}" rx="2"/>')
    months = "".join(f'<text x="{12 + i * 26}" y="114" text-anchor="middle">{m}</text>' for i, m in enumerate("JFMAMJJASO"))
    svg = (f'<svg class="mini-chart" viewBox="0 0 270 118" aria-hidden="true"><path class="grid-l" d="M0 34H270M0 67H270M0 100H270"/>'
           f'{"".join(bars)}<g class="axis">{months}</g></svg>')
    return _window("Bookings by month", f"""<div class="dash">
  <div class="legend"><span class="la">This year</span><span class="lb">Last year</span></div>
  {svg}
  <div class="tip">{icon("cursor")}<div><strong>September: $3.3M</strong><span>41 deals · click to see them</span></div></div>
</div>""")


def mock_tool() -> str:
    rows = [("Prairie Surgical", "Proposal", "$85K"), ("Permian Logistics", "Negotiation", "$67K"),
            ("Lone Star Packaging", "Verbal yes", "$61K"), ("Hill Country Clinics", "Proposal", "$44K")]
    body = "".join(f'<tr><td>{a}</td><td><span class="sel">{b}</span></td><td class="num">{c}</td></tr>' for a, b, c in rows)
    return _window("Q4 forecast", f"""<div class="old-file">{icon("sheet")}<s>forecast_v12_final.xlsx</s></div>
<table class="mini-tool"><tbody>{body}</tbody></table>
<div class="tool-foot"><span>{icon("check")}Saved · everyone sees the same numbers</span><strong>$1.84M</strong></div>""")


def mock_alerts() -> str:
    items = [("bell", "Deal slipped a quarter", "Prairie Surgical, $85K, moved to Q1", "now"),
             ("dollar", "Invoice 90 days late", "Permian Logistics, $41K", "9:12"),
             ("chart", "Billing behind pace", "Austin is at 71% of this month's goal", "Mon")]
    cards = "".join(f'<div class="push p{i}">{icon(ic)}<div><strong>{t}</strong><span>{s}</span></div><time>{w}</time></div>'
                    for i, (ic, t, s, w) in enumerate(items))
    return f'<div class="mock phone-mock"><div class="phone-notch"></div><div class="push-stack">{cards}</div></div>'


def mock_ask() -> str:
    return _window("Ask AI", f"""<div class="chat">
  <div class="bubble me">Which branch is furthest behind on billing this month?</div>
  <div class="bubble ai">{icon("spark")}<div><p><b>Austin</b>, at 71% of its monthly goal ($212K of $300K). Two large jobs are finished but not invoiced yet.</p>
  <div class="cite">{icon("doc")}From 1,284 invoices · How this is counted</div></div></div>
</div>""")


def mock_brief() -> str:
    return _window("Daily brief · 6:30 AM", f"""<div class="brief">
  <p class="brief-hi">Good morning. Three things today:</p>
  <ol><li><b>2 deals</b> need a follow-up today (Prairie Surgical, Hill Country Clinics).</li>
  <li>Cash collected is <b>8% behind pace</b> this month; Permian Logistics is the biggest gap.</li>
  <li>Board meeting Thursday: <b>prep pack drafted</b> and waiting for your review.</li></ol>
</div>""")


def agent_day() -> str:
    steps = [("6:30 AM", "agent", "Daily brief", "What changed overnight and what needs attention today, for each leader.", ""),
             ("7:15 AM", "calendar", "Meeting prep", "Before the 10:00 customer call: history, open quotes and recent emails on one page.", ""),
             ("11:02 AM", "bell", "Follow-up watch", "An invoice just passed 60 days. A friendly reminder is drafted for the account owner.", "approve"),
             ("Fri 3:00 PM", "doc", "Weekly update", "This week's report written from the numbers, ready to check and send.", "approve")]
    out = []
    for t, ic, title, text, flag in steps:
        btns = ('<div class="agent-btns"><span class="b-ok">Approve</span><span class="b-edit">Edit</span></div>'
                if flag else '<div class="agent-btns"><span class="b-done">Ready</span></div>')
        out.append(f'<li><time>{t}</time><div class="agent-card"><div class="agent-ico">{icon(ic)}</div>'
                   f'<h3>{title}</h3><p>{text}</p>{btns}</div></li>')
    return f'<ol class="agent-day">{"".join(out)}</ol>'


def demo_shot(name: str, alt: str, cls: str = "") -> str:
    return (f'<figure class="shot {cls}"><div class="shot-bar"><i></i><i></i><i></i><span>demo hub</span></div>'
            f'<picture><source srcset="/static/img/demo-{name}-dark.webp" media="(prefers-color-scheme: dark)">'
            f'<img src="/static/img/demo-{name}-light.webp" alt="{alt}" width="1600" height="1000" loading="lazy" decoding="async"></picture></figure>')


ALL_SYSTEMS = [("people", "CRM"), ("dollar", "Accounting"), ("factory", "ERP"), ("clipboard", "Project management"),
               ("truck", "Field service"), ("id", "HR & payroll"), ("box", "Inventory"), ("cart", "E-commerce"),
               ("megaphone", "Marketing"), ("headset", "Support desk"), ("sheet", "Spreadsheets"), ("db", "Databases")]


def systems_grid() -> str:
    return '<div class="sys-grid">' + "".join(f'<div class="sys">{icon(i)}<span>{l}</span></div>' for i, l in ALL_SYSTEMS) + "</div>"
