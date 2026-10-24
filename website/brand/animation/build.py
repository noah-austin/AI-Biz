"""Builds the Sanford Operations explainer animation, in two cuts of the same story.

wide: 1920 x 1080, for desktop, LinkedIn and calls.  tall: 720 x 1080, for phones (bigger text, stacked layout).
Each cut is HTML + CSS keyframes on one 26.5 s timeline, written to capture-<cut>.html (local fonts; open it in a
browser to preview, or render it to video). The website plays the MP4s rendered from these; see README.md.
"""
import base64
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parents[3]
OFF = 2.5  # title card at the start
T = 24.0 + OFF  # seconds per loop

OX, PA, INK, INK2, BRASS, SOFT, CARD, LINE = "#6b1f2a", "#f5efe4", "#2a2622", "#4f4842", "#8f6f3e", "#e9dcc9", "#fbf8f2", "#d9cdb9"
BAD, GOOD = "#b8322a", "#137a4f"

css, html = [], []
_n = [0]


def anim(points, ease="cubic-bezier(.45,0,.25,1)", shift=True):
    """points: [(seconds, 'css declarations')], timed from the end of the title card unless shift=False.
    Returns a class name with that keyframe animation."""
    if shift:
        points = [(t + OFF, d) for t, d in points]
    _n[0] += 1
    name = f"k{_n[0]}"
    pts = sorted(points)
    frames = []
    if pts[0][0] > 0:
        frames.append(f"0%{{{pts[0][1]}}}")
    for t, decl in pts:
        frames.append(f"{t / T * 100:.3f}%{{{decl};animation-timing-function:{ease}}}")
    if pts[-1][0] < T:
        frames.append(f"100%{{{pts[-1][1]}}}")
    css.append(f"@keyframes {name}{{{''.join(frames)}}}")
    css.append(f".{name}{{animation:{name} {T}s linear infinite}}")
    return name


def show(t_in, t_out=None, dur=0.5, extra_in="", extra_out=""):
    """Fade in at t_in (and out at t_out)."""
    pts = [(max(t_in - dur, 0), f"opacity:0;{extra_out}"), (t_in, f"opacity:1;{extra_in}")]
    if t_out is not None:
        pts += [(t_out - dur, f"opacity:1;{extra_in}"), (t_out, f"opacity:0;{extra_out}")]
    return anim(pts)


def el(cls, style, inner="", tag="div"):
    html.append(f'<{tag} class="{cls}" style="{style}">{inner}</{tag}>')


CAPS = [
    (0.8, 4.8, "Your data lives in many systems.", "Each one only sees its own piece."),
    (5.3, 8.9, "We bring it all together.", "Every system, copied into one place you own."),
    (9.3, 12.8, "Now it works as one.", "See across every system at once."),
    (13.2, 19.0, "Then we build on it.", "Reports, custom software, AI and AI agents."),
]
# name, detail, scattered rotation
SYSTEMS = [("CRM", "Deals and customers", -4), ("Accounting", "Invoices and payments", 3), ("ERP", "Jobs and costs", 2),
           ("Project tool", "Hours and tasks", -3), ("HR & payroll", "People and payroll", 4),
           ("Spreadsheets", "Forecasts and trackers", -2)]
EXTRAS = [("Email and files", "Contracts and attachments", 3), ("Inventory", "Stock and orders", -3),
          ("Support desk", "Tickets and requests", 2), ("Marketing", "Leads and campaigns", -2),
          ("Field service", "Visits and work orders", 4)]
# name, detail (wide), detail (tall, where it needs to be shorter)
TOOLS = [
    ("Weekly scorecard", "fills itself in every Monday", ""),
    ("Custom software", "commissions · warehouse · scheduling", "commissions · warehouse"),
    ("Alert", "Westlake deal slipped to December", "Westlake deal slipped"),
    ("Ask AI", "“Which branch is behind on billing?”", "“Who's behind on billing?”"),
    ("AI agents", "Daily brief ready at 6:30 AM", "Daily brief ready, 6:30 AM"),
]


def wide():
    CW, CH, X0, Y0, GAP = 360, 96, 120, 250, 24
    cards = [(X0, Y0 + i * (CH + GAP)) for i in range(6)]
    HX, HY, HR, OUT_X = 960, 560, 150, 1430
    tools = [(OUT_X, Y0 + i * (CH + GAP)) for i in range(5)]
    return SimpleNamespace(
        name="wide", W=1920, H=1080, CW=CW, CH=CH, TW=400, HX=HX, HY=HY, HR=HR, cards=cards, tools=tools,
        scatter=[(20, 30), (480, -120), (940, -200), (1340, -340), (220, -190), (700, -290)],  # offsets from the column
        extras=[(1280, 570), (130, 810), (640, 830), (1160, 820), (1500, 760)],
        paths_in=[f"M{x + CW} {y + CH / 2} C {x + CW + 180} {y + CH / 2}, {HX - HR - 160} {HY}, {HX - HR} {HY}" for x, y in cards],
        paths_out=[f"M{HX + HR} {HY} C {HX + HR + 160} {HY}, {x - 180} {y + CH / 2}, {x} {y + CH / 2}" for x, y in tools],
        wires_behind=False,
        customer=(HX - 245, HY - HR - 214, 490, 19.4),
        css="""
.cap { left:120px; top:72px; width:1300px } .cap1 { font-size:66px } .cap2 { font-size:30px }
.sys { padding:18px 24px } .sname { font-size:27px } .sdet { left:24px; top:54px; font-size:21px }
.hub1 { font-size:38px } .hub2 { font-size:21px }
.rlabel { font-size:16px } .vname { font-size:30px } .vrow { font-size:19px }
.tool { padding:18px 24px } .tname { font-size:26px } .tdet { left:24px; top:56px; font-size:18px }
.sq { left:24px; top:58px } .sq i { width:32px; height:20px }
.titlecard img { width:170px; height:170px } .t-eyebrow { font-size:26px } .t-title { font-size:92px }
.endcard img { width:230px; height:230px } .end1 { font-size:76px } .end2 { font-size:34px; margin-top:40px }
""")


def tall():
    W, CW, CH = 720, 310, 84
    cards = [(40 + (i % 2) * 330, 210 + (i // 2) * 92) for i in range(6)]
    HX, HY, HR = 360, 625, 105
    tools = [(40 + (i % 2) * 330, 800 + (i // 2) * 92) for i in range(4)] + [(205, 984)]
    # scattered at the start: a loose 6 x 2 grid, systems and extras mixed
    slots = [(25 + (k % 2) * 360 + (k * 37 % 30) - 15, 225 + (k // 2) * 138) for k in range(12)]
    sys_slots, extra_slots = [0, 3, 4, 7, 8, 11], [1, 2, 5, 6, 9]
    return SimpleNamespace(
        name="tall", W=W, H=1080, CW=CW, CH=CH, TW=CW, HX=HX, HY=HY, HR=HR, cards=cards, tools=tools,
        scatter=[(slots[s][0] - x, slots[s][1] - y) for s, (x, y) in zip(sys_slots, cards)],
        extras=[slots[s] for s in extra_slots],
        # wires run behind the cards: from each card's bottom edge to the top of the hub, then on to the tools
        paths_in=[f"M{x + CW / 2} {y + CH} C {x + CW / 2} {y + CH + 110}, {HX} {HY - HR - 110}, {HX} {HY - HR}" for x, y in cards],
        paths_out=[f"M{HX} {HY + HR} C {HX} {HY + HR + 70}, {x + CW / 2} {y - 70}, {x + CW / 2} {y}" for x, y in tools],
        wires_behind=True,
        customer=(80, HY + HR + 30, 560, 13.5),  # below the hub, gone before the tools arrive
        css="""
.cap { left:40px; top:44px; width:640px } .cap1 { font-size:46px } .cap2 { font-size:24px; margin-top:10px }
.sys { padding:12px 18px } .sname { font-size:24px } .sdet { left:18px; top:46px; font-size:18px }
.hub1 { font-size:25px } .hub2 { font-size:16px }
.rlabel { font-size:14px } .vname { font-size:26px } .vrow { font-size:18px }
.tool { padding:12px 18px } .tname { font-size:23px } .tdet { left:18px; top:46px; font-size:17px }
.bell { right:16px; top:16px }
.sq { left:18px; top:48px; gap:7px } .sq i { width:28px; height:18px }
.titlecard { padding:0 50px; box-sizing:border-box; text-align:center }
.titlecard img { width:130px; height:130px } .t-eyebrow { font-size:20px } .t-title { font-size:56px; line-height:1.12 }
.endcard { padding:0 40px; box-sizing:border-box }
.endcard img { width:170px; height:170px; margin-bottom:34px } .end1 { font-size:44px } .end2 { font-size:24px; margin-top:30px }
""")


def scene(L):
    """Builds one cut's stage. Returns the stage HTML; its keyframes are in css."""
    html.clear()
    tallcut = L.name == "tall"

    # captions (top left)
    for a, b, l1, l2 in CAPS:
        c = show(a, b, 0.5, "transform:translateY(0)", "transform:translateY(14px)")
        el(f"cap {c}", "", f'<div class="cap1">{l1}</div><div class="cap2">{l2}</div>')
    wire_at = len(html)

    # systems: scattered, then glide into place at 5.4-6.6 s
    for i, ((name, det, rot), (x, y), (dx, dy)) in enumerate(zip(SYSTEMS, L.cards, L.scatter)):
        mv = anim([(0, f"transform:translate({dx}px,{dy}px) rotate({rot}deg)"),
                   (1.7, f"transform:translate({dx + 10}px,{dy - 12}px) rotate({rot + 1}deg)"),
                   (3.4, f"transform:translate({dx - 8}px,{dy + 8}px) rotate({rot - 1}deg)"),
                   (5.2 + i * 0.06, f"transform:translate({dx}px,{dy}px) rotate({rot}deg)"),
                   (6.6 + i * 0.06, "transform:translate(0,0) rotate(0deg)")])
        fade = show(0.6 + i * 0.12, 19.6, 0.6)
        html.append(f'<div class="{fade}" style="position:absolute;left:{x}px;top:{y}px"><div class="card sys {mv}">'
                    f'<div class="sname">{name}</div><div class="sdet">{det}</div></div></div>')

    # more systems: scattered at the start, then pulled into the hub as it appears
    for i, ((name, det, rot), (x, y)) in enumerate(zip(EXTRAS, L.extras)):
        tx, ty = L.HX - (x + L.CW / 2), L.HY - (y + L.CH / 2)
        t1 = 5.5 + i * 0.12
        mv = anim([(0, f"transform:translate(0,0) rotate({rot}deg) scale(1);opacity:1"),
                   (1.8, f"transform:translate(-9px,10px) rotate({rot - 1}deg) scale(1);opacity:1"),
                   (3.5, f"transform:translate(8px,-8px) rotate({rot + 1}deg) scale(1);opacity:1"),
                   (t1, f"transform:translate(0,0) rotate({rot}deg) scale(1);opacity:1"),
                   (t1 + 1.1, f"transform:translate({tx:.0f}px,{ty:.0f}px) rotate(0deg) scale(.25);opacity:0")])
        fade = show(0.7 + (i + 6) * 0.1, None, 0.6)
        html.append(f'<div class="{fade}" style="position:absolute;left:{x}px;top:{y}px"><div class="card sys {mv}">'
                    f'<div class="sname">{name}</div><div class="sdet">{det}</div></div></div>')

    # connectors and the data dots flowing along them
    mark = len(html)
    svg = [f'<svg class="wires" width="{L.W}" height="{L.H}" viewBox="0 0 {L.W} {L.H}">']
    for i, d in enumerate(L.paths_in):
        k = anim([(6.9 + i * 0.12, "stroke-dashoffset:700;opacity:1"), (8.1 + i * 0.12, "stroke-dashoffset:0;opacity:1"),
                  (19.2, "stroke-dashoffset:0;opacity:1"), (19.7, "stroke-dashoffset:0;opacity:0")])
        svg.append(f'<path class="{k}" d="{d}" pathLength="700" fill="none" stroke="{BRASS}" stroke-width="2.5" stroke-dasharray="700"/>')
    for i, d in enumerate(L.paths_out):
        k = anim([(13.3 + i * 0.5, "stroke-dashoffset:700;opacity:1"), (14.1 + i * 0.5, "stroke-dashoffset:0;opacity:1"),
                  (19.2, "stroke-dashoffset:0;opacity:1"), (19.7, "stroke-dashoffset:0;opacity:0")])
        svg.append(f'<path class="{k}" d="{d}" pathLength="700" fill="none" stroke="{OX}" stroke-width="2.5" stroke-dasharray="700"/>')
    svg.append("</svg>")
    html.append("".join(svg))
    for i, d in enumerate(L.paths_in):
        for j in range(2):
            pts, t = [(0, "offset-distance:0%;opacity:0")], 8.3 + i * 0.13 + j * 0.7
            while t + 1.2 < 19.0:
                pts += [(t, "offset-distance:0%;opacity:0"), (t + 0.15, "offset-distance:10%;opacity:1"),
                        (t + 1.05, "offset-distance:92%;opacity:1"), (t + 1.2, "offset-distance:100%;opacity:0")]
                t += 1.4
            el(f"dot {anim(pts, 'linear')}", f"offset-path:path('{d}');background:{BRASS}")
    for i, d in enumerate(L.paths_out):
        pts, t = [(0, "offset-distance:0%;opacity:0")], 14.3 + i * 0.5
        while t + 1.2 < 19.0:
            pts += [(t, "offset-distance:0%;opacity:0"), (t + 0.15, "offset-distance:10%;opacity:1"),
                    (t + 1.05, "offset-distance:92%;opacity:1"), (t + 1.2, "offset-distance:100%;opacity:0")]
            t += 1.5
        el(f"dot {anim(pts, 'linear')}", f"offset-path:path('{d}');background:{OX}")
    if L.wires_behind:  # stacked layout: the wires pass behind the cards
        wires = html[mark:]
        del html[mark:]
        html[wire_at:wire_at] = wires

    # the hub
    HX, HY, HR = L.HX, L.HY, L.HR
    hub = anim([(6.4, "transform:scale(0);opacity:0"), (7.1, "transform:scale(1.06);opacity:1"), (7.5, "transform:scale(1);opacity:1"),
                (9.4, "transform:scale(1);opacity:1"), (9.8, "transform:scale(1.04);opacity:1"), (10.2, "transform:scale(1);opacity:1"),
                (19.2, "transform:scale(1);opacity:1"), (19.7, "transform:scale(.9);opacity:0")])
    ring = anim([(7.4, "transform:scale(1);opacity:0"), (7.8, "transform:scale(1);opacity:.5"), (9.0, "transform:scale(1.5);opacity:0"),
                 (12.6, "transform:scale(1);opacity:0"), (13.0, "transform:scale(1);opacity:.5"), (14.4, "transform:scale(1.5);opacity:0")])
    box = f"left:{HX - HR}px;top:{HY - HR}px;width:{2 * HR}px;height:{2 * HR}px"
    el(f"ring {ring}", box)
    el(f"hub {hub}", box, '<div class="hub1">Your data hub</div><div class="hub2">Every system,<br>together</div>')

    # one customer, seen across systems at once (the payoff of having it together)
    cx, cy, cw, c_out = L.customer
    rb = show(9.6, c_out, 0.5, "transform:translateY(0)", "transform:translateY(16px)")
    rows = [("3 open deals · $412K", "CRM"), ("$31K unpaid, 62 days", "Accounting"), ("2 jobs in progress", "ERP")]
    rows_html = "".join(f'<div class="vrow"><span>{t}</span><em>{src}</em></div>' for t, src in rows)
    el(f"card rule {rb}", f"left:{cx}px;top:{cy}px;width:{cw}px",
       '<div class="rlabel">One customer, every system</div><div class="vname">Prairie Surgical Hospital</div>' + rows_html)

    # tools
    for i, ((name, det, det_tall), (x, y)) in enumerate(zip(TOOLS, L.tools)):
        det = det_tall if tallcut and det_tall else det
        t0 = 13.9 + i * 0.5
        pop = anim([(t0, "opacity:0;transform:translateX(30px) scale(.96)"), (t0 + 0.45, "opacity:1;transform:translateX(0) scale(1)"),
                    (19.3, "opacity:1;transform:translateX(0) scale(1)"), (19.8, "opacity:0;transform:translateX(0) scale(.97)")])
        inner = f'<div class="tname">{name}</div><div class="tdet">{det}</div>'
        if name == "Weekly scorecard":
            sq = ""
            for j in range(7):
                k = anim([(t0 + 0.6 + j * 0.18, "background:#4a4440"), (t0 + 0.8 + j * 0.18, f"background:{'#c9a46a' if j == 4 else '#3f9d6e'}")])
                sq += f'<i class="{k}"></i>'
            inner = f'<div class="tname">{name}</div><div class="sq">{sq}</div>'
        if name == "Alert":
            k = anim([(t0 + 0.5, "transform:scale(1);opacity:1"), (t0 + 0.8, "transform:scale(1.5);opacity:.4"), (t0 + 1.1, "transform:scale(1);opacity:1"),
                      (t0 + 1.4, "transform:scale(1.5);opacity:.4"), (t0 + 1.7, "transform:scale(1);opacity:1")])
            inner = f'<span class="bell {k}"></span>' + inner
        if name == "Ask AI":
            q = show(t0 + 0.2, t0 + 1.9, 0.3)
            a = show(t0 + 2.1, None, 0.3)
            ans = "Fort Worth, at 81%" if tallcut else "Fort Worth, at 81% of last year"
            inner = f'<div class="tname">{name}</div><div class="tdet {q}">{det}</div><div class="tdet ans {a}">{ans}</div>'
        html.append(f'<div class="card tool {pop}" style="left:{x}px;top:{y}px;width:{L.TW}px">{inner}</div>')

    # title card and end card
    seal = "data:image/svg+xml;base64," + base64.b64encode((REPO / "website/static/brand/seal.svg").read_bytes()).decode()
    veil = anim([(0, "opacity:1"), (OFF - 0.5, "opacity:1"), (OFF + 0.1, "opacity:0"), (19.3 + OFF, "opacity:0"), (19.9 + OFF, "opacity:1")], shift=False)
    el(f"veil {veil}", "")
    intro = anim([(0, "opacity:1;transform:translateY(0)"), (OFF - 0.55, "opacity:1;transform:translateY(0)"), (OFF - 0.05, "opacity:0;transform:translateY(-12px)"),
                  (T - 0.6, "opacity:0;transform:translateY(10px)"), (T, "opacity:1;transform:translateY(0)")], shift=False)
    endc = anim([(19.8, "opacity:0;transform:translateY(18px)"), (20.6, "opacity:1;transform:translateY(0)"),
                 (23.2, "opacity:1;transform:translateY(0)"), (23.8, "opacity:0;transform:translateY(0)")])
    el(f"endcard {endc}", "",
       f'<img src="{seal}" alt="Sanford Operations seal">'
       '<div class="end1">Your data in one place.</div><div class="end1">Numbers everyone trusts, put to work.</div>'
       '<div class="end2">sanfordoperations.com</div>')
    el(f"titlecard {intro}", "", f'<img src="{seal}" alt="">'
       '<div class="t-eyebrow">Sanford Operations</div><div class="t-title">How we put your data to work</div>')
    return f'<div class="stage">{"".join(html)}</div>'


def stage_css(L):
    return f"""
.stage {{ position:relative; width:{L.W}px; height:{L.H}px; overflow:hidden; background:{PA}; color:{INK};
  font-family:'Inter', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif }}
.stage > * {{ position:absolute }}
.cap1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; line-height:1.1; color:{INK} }}
.cap2 {{ color:{INK2}; margin-top:12px }}
.card {{ border-radius:16px; box-sizing:border-box }}
.sys {{ position:relative; width:{L.CW}px; height:{L.CH}px; background:{CARD}; border:1.5px solid {LINE};
  box-shadow:0 10px 30px rgba(42,38,34,.08) }}
.sname {{ font-weight:600 }}
.sdet {{ position:absolute; color:{INK2}; font-variant-numeric:tabular-nums; white-space:nowrap }}
.wires {{ left:0; top:0 }}
.dot {{ left:0; top:0; width:12px; height:12px; border-radius:50%; offset-rotate:0deg; opacity:0 }}
.hub, .ring {{ border-radius:50%; box-sizing:border-box }}
.hub {{ background:{OX}; color:{PA}; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;
  box-shadow:0 20px 50px rgba(107,31,42,.30); opacity:0 }}
.ring {{ border:3px solid {OX}; opacity:0 }}
.hub1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; text-align:center }}
.hub2 {{ color:{SOFT}; text-align:center; line-height:1.3 }}
.rule {{ background:{CARD}; border:1.5px solid {LINE}; padding:16px 22px; box-shadow:0 10px 30px rgba(42,38,34,.08); opacity:0 }}
.rlabel {{ font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:{BRASS} }}
.vname {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; color:{INK}; margin:4px 0 6px }}
.vrow {{ display:flex; justify-content:space-between; align-items:center; color:{INK}; padding:5px 0; border-top:1px solid {LINE} }}
.vrow em {{ font-style:normal; font-size:15px; font-weight:600; color:{BRASS}; background:#f1e7d6; padding:2px 9px; border-radius:999px }}
.tool {{ height:{L.CH}px; background:{INK}; color:{PA}; opacity:0; box-shadow:0 12px 30px rgba(42,38,34,.18) }}
.tname {{ font-weight:600 }}
.tdet {{ position:absolute; color:#d8cdbf; white-space:nowrap }}
.tdet.ans {{ color:#f0d9a8; font-weight:600 }}
.sq {{ position:absolute; display:flex; gap:8px }}
.sq i {{ display:block; border-radius:4px; background:#4a4440 }}
.bell {{ position:absolute; right:22px; top:22px; width:14px; height:14px; border-radius:50%; background:#f0a35e }}
.veil {{ left:0; top:0; width:{L.W}px; height:{L.H}px; background:{PA} }}
.endcard {{ left:0; top:0; width:{L.W}px; height:{L.H}px; display:flex; flex-direction:column; align-items:center; justify-content:center; opacity:0 }}
.endcard img {{ margin-bottom:44px }}
.titlecard {{ left:0; top:0; width:{L.W}px; height:{L.H}px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:22px }}
.t-eyebrow {{ font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:{BRASS}; margin-top:14px }}
.t-title {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; color:{INK}; text-wrap:balance }}
.end1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; line-height:1.12; color:{INK}; text-align:center }}
.end2 {{ font-weight:600; color:{OX}; letter-spacing:.02em }}
""" + L.css


if __name__ == "__main__":
    f = lambda p: base64.b64encode((REPO / p).read_bytes()).decode()
    fonts = (f"@font-face{{font-family:'Playfair Display';font-weight:700;src:url(data:font/woff2;base64,{f('website/static/fonts/playfair-700.woff2')})}}"
             f"@font-face{{font-family:'Inter';font-weight:100 900;src:url(data:font/woff2;base64,{f('website/static/fonts/inter-latin-var.woff2')})}}")
    for L in (wide(), tall()):
        css.clear()
        st = scene(L)
        (HERE / f"capture-{L.name}.html").write_text(
            f"<!doctype html><html><head><meta charset='utf-8'><title>Explainer ({L.name})</title>"
            f"<style>{fonts}body{{margin:0}}{stage_css(L)}{''.join(css)}</style></head><body>{st}</body></html>")
        print(f"{L.name}: {L.W}x{L.H}, {len(css) // 2} keyframes")
