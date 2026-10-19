"""'See how it works': pick an industry, watch its systems flow into one hub, open what the hub caught this week.

Pure HTML and CSS (the site runs no scripts): the industry tabs are radio buttons, the cards are <details>, and the
animations restart each time a panel is shown. Every example comes from one of our fictional demo companies.
"""
from html import escape as esc

from .visuals import icon

# Each industry: its systems, and three things the hub caught. A preview is ("bars", title, [(label, value, highlight)],
# unit, goal or None) or ("line", title, [values], [first label, last label], unit) or ("brief", title, [lines]).
INDUSTRIES = [
    {"key": "facility", "tab": "Facility services", "company": "Bluestem Facility Services",
     "about": "a fictional HVAC and building-services company with six branches",
     "systems": [("people", "CRM"), ("dollar", "Accounting"), ("truck", "Field service app"), ("box", "Inventory"),
                 ("id", "HR & payroll")],
     "catches": [
         ("bell", "Alert", "Houston reaches only 74% of emergency calls within 4 hours",
          "Two technicians short since late summer, so overtime is at 19% and calls wait.",
          ("bars", "Emergency calls on time, last 30 days", [("Austin", 92, False), ("Dallas", 90, False), ("Fort Worth", 88, False),
                                                             ("Houston", 74, True), ("Houston South", 85, False), ("San Antonio", 95, False)], "%", 90)),
         ("scorecard", "Scorecard", "Fort Worth needs a return visit on 1 repair in 4",
          "First-time fix is 73% there, against about 87% at every other branch.",
          ("bars", "First-time fix, last 90 days", [("Austin", 89, False), ("Dallas", 87, False), ("Fort Worth", 73, True),
                                                    ("Houston", 85, False), ("Houston South", 85, False), ("San Antonio", 87, False)], "%", 85)),
         ("agent", "AI brief", "This morning's brief, written before anyone got in",
          "The AI agent reads every system overnight and leaves a short list for the COO.",
          ("brief", "Daily brief, 6:30 AM", ["Two critical parts are out of stock in Houston: run capacitors and fan motors.",
                                             "77 completed jobs still aren't invoiced after 14 days ($101K).",
                                             "Two technicians are working on an expired state license.",
                                             "15 open deals were pushed to a later month this week ($2.0M)."])),
     ]},
    {"key": "distribution", "tab": "Distribution", "company": "Bramblewood Industrial Supply",
     "about": "a fictional industrial-supply distributor with six branches",
     "systems": [("people", "CRM"), ("cart", "ERP: orders"), ("dollar", "Accounting"), ("box", "Inventory"), ("truck", "Purchasing"),
                 ("id", "HR & payroll")],
     "catches": [
         ("bell", "Alert", "Corpus Christi ships only 79% of order lines complete",
          "It's two warehouse staff short and two fast movers are out of stock, so customers wait on backorders.",
          ("bars", "Fill rate by branch, last 30 days", [("Houston", 92, False), ("Dallas", 93, False), ("San Antonio", 94, False),
                                                         ("Austin", 96, False), ("Beaumont", 94, False), ("Corpus Christi", 79, True)], "%", 95)),
         ("chart", "Dashboard", "Safety & PPE margin slid from 23% to 17% in a year",
          "The vendor raised costs about 10%; nobody passed it on to customers.",
          ("line", "Gross margin, Safety & PPE", [22.9, 22.6, 22.2, 21.8, 21.4, 20.9, 20.3, 19.8, 19.1, 18.5, 17.8, 17.0], ["Oct", "Sep"], "%")),
         ("agent", "AI brief", "One rep is giving away 9 points of margin",
          "Everyone else sells at about 25%. The brief names the rep and the customers.",
          ("bars", "Gross margin by rep, last 30 days", [("Rep A", 25, False), ("Rep B", 25, False), ("Rep C", 25, False),
                                                         ("Rep D", 24, False), ("Rep E", 16, True)], "%", None)),
     ]},
    {"key": "services", "tab": "Professional services", "company": "Kestrel Ridge Engineering",
     "about": "a fictional engineering firm with four offices",
     "systems": [("people", "CRM"), ("clock", "Projects & time"), ("dollar", "Accounting"), ("id", "HR & payroll")],
     "catches": [
         ("scorecard", "Scorecard", "Austin billed 58% of its hours, down from 74%",
          "It lost its biggest client in February and kept the same people: room for a fifth more work.",
          ("line", "Billable utilization, Austin", [74, 75, 73, 74, 61, 59, 58, 59, 57, 58, 59, 58], ["Nov", "Oct"], "%")),
         ("chart", "Dashboard", "One project manager's fixed fees run a third over budget",
          "The firm bills 95% of the hours it spends; this one PM's projects bill 72%.",
          ("bars", "Realization by project manager", [("PM A", 72, True), ("PM B", 81, False), ("PM C", 87, False),
                                                      ("PM D", 93, False), ("Firm average", 95, False)], "%", None)),
         ("agent", "AI brief", "$41K of hourly work hasn't been billed since July",
          "Work done is cash lent to the client until it's invoiced.",
          ("brief", "Daily brief, 6:30 AM", ["A traffic study in Houston has $41K of time not billed since July 10.",
                                             "9 fixed-fee projects are burning budget faster than they progress.",
                                             "State agencies are paying 87% of standard rates: worth raising at renewal.",
                                             "Two engineers are working on an expired PE license."])),
     ]},
    {"key": "construction", "tab": "Construction", "company": "Mesquite Ridge Constructors",
     "about": "a fictional commercial general contractor with three offices",
     "systems": [("people", "CRM"), ("blocks", "Job cost"), ("dollar", "Accounting"), ("truck", "Purchasing"), ("id", "HR & payroll")],
     "catches": [
         ("chart", "Dashboard", "Active jobs are earning 10.1% margin, bid at 12.1%",
          "Most of the fade is on one project manager's jobs: about $940K of gross profit.",
          ("bars", "Projected margin on active jobs", [("Bid", 12.1, False), ("Projected today", 10.1, True)], "%", None)),
         ("bell", "Alert", "A warehouse job is 78% done but only 53% billed",
          "It's under-billed by $316K: the company is financing the owner's job.",
          ("bars", "Warehouse shell, as of last month-end", [("Work complete", 78, False), ("Contract billed", 53, True)], "%", None)),
         ("agent", "AI brief", "$345K of change orders are waiting on owners' signatures",
          "Some have waited since May. The work is done; the money isn't agreed.",
          ("brief", "Daily brief, 6:30 AM", ["Six change orders worth $345K are waiting on owners; the oldest is from May 20.",
                                             "A distribution-center job is now projected to lose money (-0.4%).",
                                             "San Antonio field crews are at 15% overtime: two positions open.",
                                             "Two crane operators' certifications have lapsed."])),
     ]},
    {"key": "manufacturing", "tab": "Manufacturing", "company": "Cottonwood Precision Manufacturing",
     "about": "a fictional contract manufacturer with two plants",
     "systems": [("people", "CRM"), ("cart", "ERP: orders"), ("factory", "Shop floor"), ("box", "Inventory"), ("truck", "Purchasing"),
                 ("id", "HR & payroll")],
     "catches": [
         ("bell", "Alert", "The Waco press brake is 45% effective: 49 hours down this month",
          "Breakdown after breakdown, so its production orders run late and Waco customers wait.",
          ("bars", "Effectiveness by work center, last 30 days", [("Waco press brake", 45, True), ("CNC machining", 74, False),
                                                                  ("Fort Worth press brake", 76, False), ("Powder coat line", 79, False),
                                                                  ("Laser cutting", 85, False), ("Welding cells", 91, False)], "%", None)),
         ("chart", "Dashboard", "CNC scrap jumped from 2% to 7% in July",
          "Two experienced machinists left; the scrap shows up weeks before anyone would notice.",
          ("line", "Scrap rate, CNC machining", [2.1, 1.8, 2.3, 2.0, 2.2, 1.9, 6.8, 6.1, 7.4, 6.9, 7.8, 7.3], ["May", "Oct"], "%")),
         ("agent", "AI brief", "Steel is up 12% and January's prices haven't moved",
          "Margin on steel-heavy trailer parts is the thinnest in the shop.",
          ("brief", "Daily brief, 6:30 AM", ["Trailer components are at 22% margin, against 30% on machined parts.",
                                             "The steel service center delivered late on 3 of the last 10 orders.",
                                             "Waco shipped 79% of order lines complete in the last 30 days.",
                                             "Two welders' certifications have lapsed."])),
     ]},
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
    radios, tabs, panels = [], [], []
    for i, ind in enumerate(INDUSTRIES):
        radios.append(f'<input class="how-radio" type="radio" name="how-industry" id="how-{ind["key"]}"{" checked" if i == 0 else ""}>')
        tabs.append(f'<label for="how-{ind["key"]}">{esc(ind["tab"])}</label>')
        systems = "".join(f'<li class="s{k}">{icon(ic)}<span>{esc(name)}</span></li>' for k, (ic, name) in enumerate(ind["systems"]))
        cards = "".join(
            f'<details class="catch c{k}"><summary><span class="catch-kind">{icon(ic)}{esc(kind)}</span>'
            f'<strong>{esc(head)}</strong><span class="catch-why">{esc(why)}</span>'
            f'<span class="catch-open">See the screen</span></summary>{_preview(pv)}</details>'
            for k, (ic, kind, head, why, pv) in enumerate(ind["catches"]))
        panels.append(f"""<div class="how-panel" id="panel-{ind["key"]}">
  <div class="how-step how-systems"><p class="how-label">1 · Your systems</p><ul>{systems}</ul></div>
  <div class="how-pipe" aria-hidden="true"><i></i></div>
  <div class="how-step how-core"><p class="how-label">2 · One hub</p>
    <div class="how-hub">{icon("db")}<strong>Your data hub</strong><span>connected, cleaned, one set of numbers</span></div>
    <p class="how-outs">Scorecard · Dashboards · Alerts · AI agents</p></div>
  <div class="how-pipe" aria-hidden="true"><i></i></div>
  <div class="how-step how-catches"><p class="how-label">3 · What it caught this week</p>{cards}</div>
  <p class="how-foot">Examples from {esc(ind["company"])}, {esc(ind["about"])} in our demos. Open a card to see the screen.</p>
</div>""")
    return f"""<section class="how-section" id="how-it-works"><div class="wrap">
  <header class="sec-head center"><p class="eyebrow">See how it works</p><h2>Pick a company like yours</h2>
  <p class="lead">Your systems flow into one hub. Then it starts telling you things, every morning, before anyone asks.</p></header>
  <div class="how">{"".join(radios)}<div class="how-tabs" role="group" aria-label="Industry">{"".join(tabs)}</div>
  <div class="how-panels">{"".join(panels)}</div></div>
  <div class="cta-row center"><a class="btn" href="/contact?interest=call">Book a call</a>
    <a class="btn ghost" href="/contact?interest=demo">Request a live demo →</a></div>
</div></section>"""
