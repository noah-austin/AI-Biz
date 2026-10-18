"""Builds the Sanford Operations explainer animation.

stage(): the 1920x1080 animated stage (HTML + CSS keyframes on one 24 s timeline).
Writes index.html (the artifact page) and capture.html (for rendering frames to video, local fonts).
"""
import base64
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parents[3]
T = 24.0  # seconds per loop

OX, PA, INK, INK2, BRASS, SOFT, CARD, LINE = "#6b1f2a", "#f5efe4", "#2a2622", "#4f4842", "#8f6f3e", "#e9dcc9", "#fbf8f2", "#d9cdb9"
BAD, GOOD = "#b8322a", "#137a4f"

css, html = [], []
_n = [0]


def anim(points, ease="cubic-bezier(.45,0,.25,1)"):
    """points: [(seconds, 'css declarations')]. Returns a class name with that keyframe animation."""
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


# ------------------------------------------------------------------ captions (top left)
CAPS = [
    (0.8, 4.8, "Your data lives in ten places,", "and the numbers don’t match."),
    (5.3, 8.9, "We bring it into one place.", "Read-only. Nothing gets replaced."),
    (9.3, 12.8, "Every number is defined once.", "So everyone works from the same one."),
    (13.2, 19.0, "Then we put it to work.", "Reports, tools, AI and AI agents."),
]
for i, (a, b, l1, l2) in enumerate(CAPS):
    c = show(a, b, 0.5, "transform:translateY(0)", "transform:translateY(14px)")
    el(f"cap {c}", "", f'<div class="cap1">{l1}</div><div class="cap2">{l2}</div>')

# ------------------------------------------------------------------ systems (left)
SYSTEMS = [
    # name, detail (before), detail (after), scattered dx, dy, rot, conflict
    ("CRM", "Bookings $4.2M", "Bookings $4.2M", 60, 50, -4, True),
    ("Accounting", "Revenue $4.0M", "Bookings $4.2M", 740, -50, 3, True),
    ("ERP", "Jobs and costs", "Jobs and costs", 1340, -200, 2, False),
    ("Project tool", "Hours and tasks", "Hours and tasks", 400, 210, -3, False),
    ("HR & payroll", "Headcount 212", "Headcount 212", 880, -170, 4, False),
    ("Spreadsheets", "Bookings $3.9M", "Bookings $4.2M", 1260, -40, -2, True),
]
COL_X, COL_Y0, CW, CH, GAP = 120, 250, 360, 96, 24
for i, (name, d1, d2, dx, dy, rot, conflict) in enumerate(SYSTEMS):
    y = COL_Y0 + i * (CH + GAP)
    # drift while scattered, then glide into the column at 5.4-6.6 s
    drift = [(0, f"transform:translate({dx}px,{dy}px) rotate({rot}deg)"),
             (1.7, f"transform:translate({dx + 10}px,{dy - 12}px) rotate({rot + 1}deg)"),
             (3.4, f"transform:translate({dx - 8}px,{dy + 8}px) rotate({rot - 1}deg)"),
             (5.2 + i * 0.06, f"transform:translate({dx}px,{dy}px) rotate({rot}deg)"),
             (6.6 + i * 0.06, "transform:translate(0,0) rotate(0deg)")]
    mv = anim(drift)
    fade = show(0.6 + i * 0.12, 19.6, 0.6)
    inner = f'<div class="sname">{name}</div>'
    if d1 != d2:
        a = show(0.1, 10.2, 0.4)
        b = show(10.4, 19.6, 0.4)
        inner += f'<div class="sdet {a}">{d1}</div><div class="sdet {b}">{d2}</div>'
    else:
        inner += f'<div class="sdet">{d1}</div>'
    if conflict:
        bad = show(1.8 + i * 0.25, 10.0, 0.35)
        good = show(10.6, 19.6, 0.35)
        inner += f'<div class="pill bad {bad}">Doesn’t match</div><div class="pill good {good}">Matches</div>'
    html.append(f'<div class="{fade}" style="position:absolute;left:{COL_X}px;top:{y}px"><div class="card sys {mv}">{inner}</div></div>')

# ------------------------------------------------------------------ connectors and the hub
HX, HY, HR = 960, 560, 150
OUT_X = 1430
paths_in = [f"M{COL_X + CW} {COL_Y0 + i * (CH + GAP) + CH / 2} C {COL_X + CW + 180} {COL_Y0 + i * (CH + GAP) + CH / 2}, {HX - HR - 160} {HY}, {HX - HR} {HY}" for i in range(6)]
paths_out = [f"M{HX + HR} {HY} C {HX + HR + 160} {HY}, {OUT_X - 180} {COL_Y0 + i * (CH + GAP) + CH / 2}, {OUT_X} {COL_Y0 + i * (CH + GAP) + CH / 2}" for i in range(5)]
svg = [f'<svg class="wires" width="1920" height="1080" viewBox="0 0 1920 1080">']
for i, d in enumerate(paths_in):
    k = anim([(6.9 + i * 0.12, "stroke-dashoffset:700;opacity:1"), (8.1 + i * 0.12, "stroke-dashoffset:0;opacity:1"),
              (19.2, "stroke-dashoffset:0;opacity:1"), (19.7, "stroke-dashoffset:0;opacity:0")])
    svg.append(f'<path class="{k}" d="{d}" pathLength="700" fill="none" stroke="{BRASS}" stroke-width="2.5" stroke-dasharray="700"/>')
for i, d in enumerate(paths_out):
    k = anim([(13.3 + i * 0.5, "stroke-dashoffset:700;opacity:1"), (14.1 + i * 0.5, "stroke-dashoffset:0;opacity:1"),
              (19.2, "stroke-dashoffset:0;opacity:1"), (19.7, "stroke-dashoffset:0;opacity:0")])
    svg.append(f'<path class="{k}" d="{d}" pathLength="700" fill="none" stroke="{OX}" stroke-width="2.5" stroke-dasharray="700"/>')
svg.append("</svg>")
html.append("".join(svg))

# data dots flowing into the hub, then out to the tools
for i, d in enumerate(paths_in):
    for j in range(2):
        start = 8.3 + i * 0.13 + j * 0.7
        pts = [(0, "offset-distance:0%;opacity:0")]
        t = start
        while t + 1.2 < 19.0:
            pts += [(t, "offset-distance:0%;opacity:0"), (t + 0.15, "offset-distance:10%;opacity:1"),
                    (t + 1.05, "offset-distance:92%;opacity:1"), (t + 1.2, "offset-distance:100%;opacity:0")]
            t += 1.4
        k = anim(pts, "linear")
        el(f"dot {k}", f"offset-path:path('{d}');background:{BRASS}")
for i, d in enumerate(paths_out):
    start = 14.3 + i * 0.5
    pts = [(0, "offset-distance:0%;opacity:0")]
    t = start
    while t + 1.2 < 19.0:
        pts += [(t, "offset-distance:0%;opacity:0"), (t + 0.15, "offset-distance:10%;opacity:1"),
                (t + 1.05, "offset-distance:92%;opacity:1"), (t + 1.2, "offset-distance:100%;opacity:0")]
        t += 1.5
    k = anim(pts, "linear")
    el(f"dot {k}", f"offset-path:path('{d}');background:{OX}")

hub = anim([(6.4, "transform:scale(0);opacity:0"), (7.1, "transform:scale(1.06);opacity:1"), (7.5, "transform:scale(1);opacity:1"),
            (9.4, "transform:scale(1);opacity:1"), (9.8, "transform:scale(1.04);opacity:1"), (10.2, "transform:scale(1);opacity:1"),
            (19.2, "transform:scale(1);opacity:1"), (19.7, "transform:scale(.9);opacity:0")])
ring = anim([(7.4, "transform:scale(1);opacity:0"), (7.8, "transform:scale(1);opacity:.5"), (9.0, "transform:scale(1.5);opacity:0"),
             (12.6, "transform:scale(1);opacity:0"), (13.0, "transform:scale(1);opacity:.5"), (14.4, "transform:scale(1.5);opacity:0")])
el(f"ring {ring}", f"left:{HX - HR}px;top:{HY - HR}px")
el(f"hub {hub}", f"left:{HX - HR}px;top:{HY - HR}px",
   '<div class="hub1">Your data hub</div><div class="hub2">Every system,<br>one set of numbers</div>')

# rulebook card under the hub
rb = show(9.6, 19.4, 0.5, "transform:translateY(0)", "transform:translateY(16px)")
el(f"card rule {rb}", f"left:{HX - 230}px;top:{HY - HR - 186}px;width:490px",
   '<div class="rlabel">The rulebook</div><div class="rline"><b>Bookings</b> = signed deals, counted on their close date</div>'
   '<div class="rnum">$4.2M <span>· one number, everyone agrees</span></div>')

# ------------------------------------------------------------------ tools (right)
TOOLS = [
    ("Weekly scorecard", "fills itself in every Monday"),
    ("Forecast", "commit $4.2M · best case $6.8M"),
    ("Alert", "Westlake deal slipped to December"),
    ("Ask AI", "“Which branch is behind on billing?”"),
    ("AI agents", "Daily brief ready at 6:30 AM"),
]
for i, (name, det) in enumerate(TOOLS):
    y = COL_Y0 + i * (CH + GAP)
    t0 = 13.9 + i * 0.5
    pop = anim([(t0, "opacity:0;transform:translateX(30px) scale(.96)"), (t0 + 0.45, "opacity:1;transform:translateX(0) scale(1)"),
                (19.3, "opacity:1;transform:translateX(0) scale(1)"), (19.8, "opacity:0;transform:translateX(0) scale(.97)")])
    inner = f'<div class="tname">{name}</div><div class="tdet">{det}</div>'
    if name == "Weekly scorecard":
        sq = ""
        for j in range(7):
            k = anim([(t0 + 0.6 + j * 0.18, f"background:#4a4440"), (t0 + 0.8 + j * 0.18, f"background:{'#c9a46a' if j == 4 else '#3f9d6e'}")])
            sq += f'<i class="{k}"></i>'
        inner = f'<div class="tname">{name}</div><div class="sq">{sq}</div>'
    if name == "Alert":
        k = anim([(t0 + 0.5, "transform:scale(1);opacity:1"), (t0 + 0.8, "transform:scale(1.5);opacity:.4"), (t0 + 1.1, "transform:scale(1);opacity:1"),
                  (t0 + 1.4, "transform:scale(1.5);opacity:.4"), (t0 + 1.7, "transform:scale(1);opacity:1")])
        inner = f'<span class="bell {k}"></span>' + inner
    if name == "Ask AI":
        q = show(t0 + 0.2, t0 + 1.9, 0.3)
        a = show(t0 + 2.1, None, 0.3)
        inner = f'<div class="tname">{name}</div><div class="tdet {q}">{det}</div><div class="tdet ans {a}">Fort Worth, at 81% of last year</div>'
    html.append(f'<div class="card tool {pop}" style="left:{OUT_X}px;top:{y}px">{inner}</div>')

# ------------------------------------------------------------------ end card
seal = base64.b64encode((REPO / "website/static/brand/seal.svg").read_bytes()).decode()
veil = anim([(0, "opacity:1"), (0.6, "opacity:0"), (19.3, "opacity:0"), (19.9, "opacity:1")])
el(f"veil {veil}", "")
endc = anim([(19.8, "opacity:0;transform:translateY(18px)"), (20.6, "opacity:1;transform:translateY(0)"),
             (23.2, "opacity:1;transform:translateY(0)"), (23.8, "opacity:0;transform:translateY(0)")])
el(f"endcard {endc}", "",
   f'<img src="data:image/svg+xml;base64,{seal}" alt="Sanford Operations seal" width="230" height="230">'
   '<div class="end1">Your data in one place.</div><div class="end1">Numbers everyone trusts, put to work.</div>'
   '<div class="end2">sanfordoperations.com</div>')

STAGE_CSS = f"""
.stage {{ position:relative; width:1920px; height:1080px; overflow:hidden; background:{PA}; color:{INK};
  font-family:'Inter', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif; transform-origin:0 0 }}
.stage > * {{ position:absolute }}
.cap {{ left:120px; top:72px; width:1300px }}
.cap1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; font-size:66px; line-height:1.1; color:{INK} }}
.cap2 {{ font-size:30px; color:{INK2}; margin-top:12px }}
.card {{ border-radius:16px; box-sizing:border-box }}
.sys {{ position:relative; width:{CW}px; height:{CH}px; background:{CARD}; border:1.5px solid {LINE}; padding:18px 24px;
  box-shadow:0 10px 30px rgba(42,38,34,.08) }}
.sname {{ font-weight:600; font-size:27px }}
.sdet {{ position:absolute; left:24px; top:54px; font-size:21px; color:{INK2}; font-variant-numeric:tabular-nums }}
.pill {{ position:absolute; right:14px; bottom:14px; font-size:16px; font-weight:600; padding:5px 11px; border-radius:999px }}
.pill.bad {{ background:#f6dedb; color:{BAD} }}
.pill.good {{ background:#dcefe4; color:{GOOD} }}
.wires {{ left:0; top:0 }}
.dot {{ left:0; top:0; width:12px; height:12px; border-radius:50%; offset-rotate:0deg; opacity:0 }}
.hub, .ring {{ width:{2 * HR}px; height:{2 * HR}px; border-radius:50% }}
.hub {{ background:{OX}; color:{PA}; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;
  box-shadow:0 20px 50px rgba(107,31,42,.30); opacity:0 }}
.ring {{ border:3px solid {OX}; opacity:0 }}
.hub1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; font-size:38px; text-align:center }}
.hub2 {{ font-size:21px; color:{SOFT}; text-align:center; line-height:1.3 }}
.rule {{ background:{CARD}; border:1.5px solid {LINE}; padding:16px 22px; box-shadow:0 10px 30px rgba(42,38,34,.08); opacity:0 }}
.rlabel {{ font-size:16px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:{BRASS} }}
.rline {{ font-size:20px; line-height:1.35; margin-top:8px; color:{INK} }}
.rnum {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; font-size:34px; color:{OX}; margin-top:6px }}
.rnum span {{ font-family:'Inter', system-ui, Arial, sans-serif; font-weight:500; font-size:19px; color:{GOOD} }}
.tool {{ width:400px; height:{CH}px; background:{INK}; color:{PA}; padding:18px 24px; opacity:0; box-shadow:0 12px 30px rgba(42,38,34,.18) }}
.tname {{ font-weight:600; font-size:26px }}
.tdet {{ position:absolute; left:24px; top:56px; font-size:18px; color:#d8cdbf; white-space:nowrap }}
.tdet.ans {{ color:#f0d9a8; font-weight:600 }}
.sq {{ position:absolute; left:24px; top:58px; display:flex; gap:8px }}
.sq i {{ display:block; width:32px; height:20px; border-radius:4px; background:#4a4440 }}
.bell {{ position:absolute; right:22px; top:22px; width:14px; height:14px; border-radius:50%; background:#f0a35e }}
.veil {{ left:0; top:0; width:1920px; height:1080px; background:{PA} }}
.endcard {{ left:0; top:0; width:1920px; height:1080px; display:flex; flex-direction:column; align-items:center; justify-content:center; opacity:0 }}
.endcard img {{ margin-bottom:44px }}
.end1 {{ font-family:'Playfair Display', 'Playfair', Georgia, serif; font-weight:700; font-size:76px; line-height:1.12; color:{INK}; text-align:center }}
.end2 {{ font-size:34px; font-weight:600; color:{OX}; margin-top:40px; letter-spacing:.02em }}
"""


def stage():
    return f'<div class="stage" id="stage" role="img" aria-label="Animation: a company’s scattered systems are brought into one place, every number is defined once, and the data is put to work in reports, tools, AI and AI agents.">{"".join(html)}</div>'


PAGE = """<title>Sanford Explainer</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap">
<style>
/* One look by choice: the brand's parchment world. The stage is a 1920x1080 film frame scaled to the column. */
:root { --bg: #efe7d9; --ink: #2a2622; --ink-2: #4f4842; --accent: #6b1f2a; --accent-ink: #f5efe4; --line: #d9cdb9; color-scheme: light }
body { background: var(--bg); color: var(--ink); font: 16px/1.5 'Inter', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif }
.wrap { max-width: 1200px; margin: 0 auto; padding-block: 32px 56px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: flex; flex-direction: column; gap: 18px }
.eyebrow { margin: 0; font-size: 12.5px; font-weight: 600; letter-spacing: .16em; text-transform: uppercase; color: #7a5c30 }
h1 { margin: 0; font: 700 clamp(26px, 4.5vw, 38px)/1.15 'Playfair Display', 'Playfair', Georgia, serif; text-wrap: balance }
.lead { margin: 0; color: var(--ink-2); max-width: 64ch }
.frame { position: relative; width: 100%; aspect-ratio: 16 / 9; max-width: 100%; overflow: hidden; border-radius: 14px;
  border: 1px solid var(--line); box-shadow: 0 18px 48px rgba(42,38,34,.14); background: #f5efe4 }
.frame .stage { position: absolute; left: 0; top: 0 }
.controls { display: flex; gap: 10px; flex-wrap: wrap; align-items: center }
button { font: 600 14px 'Inter', system-ui, Arial, sans-serif; border-radius: 8px; padding: 9px 16px; cursor: pointer; min-height: 38px;
  border: 1px solid var(--line); background: #fbf8f2; color: var(--ink) }
button.primary { background: var(--accent); color: var(--accent-ink); border-color: var(--accent) }
button:focus-visible { outline: 3px solid #8f6f3e; outline-offset: 2px }
.note { margin: 0; font-size: 13.5px; color: var(--ink-2) }
.beats { margin: 0; padding-left: 20px; color: var(--ink-2); display: flex; flex-direction: column; gap: 4px }
@media (prefers-reduced-motion: reduce) { .stage *, .stage { animation-play-state: paused !important } }
STAGE_CSS
</style>
<div class="wrap">
  <p class="eyebrow">Sanford Operations</p>
  <h1>What we do, in 24 seconds</h1>
  <p class="lead">Scattered systems come together in one place, every number is defined once, and the data is put to work. It loops; the video file for LinkedIn and the website is made from this same animation.</p>
  <div class="frame" id="frame">STAGE</div>
  <div class="controls">
    <button type="button" class="primary" id="toggle">Pause</button>
    <button type="button" id="replay">Play from the start</button>
  </div>
  <ol class="beats">
    <li>0–5 s · Your data lives in ten places, and the numbers don’t match.</li>
    <li>5–9 s · We bring it into one place.</li>
    <li>9–13 s · Every number is defined once.</li>
    <li>13–19 s · Then we put it to work: scorecard, forecast, alerts, Ask AI, AI agents.</li>
    <li>19–24 s · Your data in one place. Numbers everyone trusts, put to work.</li>
  </ol>
</div>
<script>
(() => {
  const frame = document.getElementById('frame'), stage = document.getElementById('stage');
  const fit = () => { stage.style.transform = 'scale(' + (frame.clientWidth / 1920) + ')'; };
  fit(); new ResizeObserver(fit).observe(frame);
  const anims = () => stage.getAnimations({ subtree: true });
  const btn = document.getElementById('toggle');
  let paused = false;
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const setAll = ms => anims().forEach(a => { a.currentTime = ms; });
  if (reduce) { setAll(21000); anims().forEach(a => a.pause()); paused = true; btn.textContent = 'Play'; }
  btn.addEventListener('click', () => {
    paused = !paused;
    anims().forEach(a => paused ? a.pause() : a.play());
    btn.textContent = paused ? 'Play' : 'Pause';
  });
  document.getElementById('replay').addEventListener('click', () => {
    setAll(0); anims().forEach(a => a.play()); paused = false; btn.textContent = 'Pause';
  });
})();
</script>
"""

if __name__ == "__main__":
    st = stage()
    allcss = STAGE_CSS + "\n".join(css)
    (HERE / "index.html").write_text(PAGE.replace("STAGE_CSS", allcss).replace("STAGE", st))
    f = lambda p: base64.b64encode((REPO / p).read_bytes()).decode()
    fonts = (f"@font-face{{font-family:'Playfair Display';font-weight:700;src:url(data:font/woff2;base64,{f('website/static/fonts/playfair-700.woff2')})}}"
             f"@font-face{{font-family:'Inter';font-weight:100 900;src:url(data:font/woff2;base64,{f('website/static/fonts/inter-latin-var.woff2')})}}")
    (HERE / "capture.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}body{{margin:0}}{allcss}</style></head><body>{st}</body></html>")
    print("keyframes:", _n[0], "html bytes:", len(st))


# ------------------------------------------------------------------ website version
# The site allows no inline styles or scripts (CSP), so every style attribute becomes a class in
# website/static/explainer.css, and the stage scales to its box with CSS alone.
def site():
    import re
    st = stage().replace(f"data:image/svg+xml;base64,{seal}", "/static/brand/seal.svg")
    rules = []

    def cls_style(m):
        n = len(rules)
        rules.append(m.group(3))
        return f'{m.group(1)}{m.group(2)} s{n}"'
    st = re.sub(r'(<\w+ class=")([^"]*)" style="([^"]*)"', cls_style, st)
    st = re.sub(r'class="([^"]*)"', lambda m: 'class="' + re.sub(r"\bk(\d+)\b", r"exk\1", m.group(1)) + '"', st)
    assert "style=" not in st, "inline style left"

    def prefix(block):
        return re.sub(r"(^|\})\s*([^{}@][^{}]*)\{",
                      lambda m: m.group(1) + ",".join(".explainer " + s.strip() for s in m.group(2).split(",")) + "{", block)
    kf = "\n".join(css)
    kf = re.sub(r"@keyframes k(\d+)", r"@keyframes exk\1", kf)
    kf = re.sub(r"\.k(\d+)\{animation:k(\d+) ", r".explainer .exk\1{animation:exk\2 ", kf)
    out = ["/* Generated by website/brand/animation/build.py. Do not edit by hand. */",
           ".explainer{position:relative;width:100%;aspect-ratio:16/9;container-type:inline-size;overflow:hidden;"
           "border-radius:14px;border:1px solid var(--line);background:#f5efe4;text-align:left;line-height:normal}",
           prefix(STAGE_CSS.strip()),
           ".explainer .stage{position:absolute;left:0;top:0;transform-origin:0 0;transform:scale(tan(atan2(100cqw,1920px)))}",
           kf,
           "".join(f".explainer .s{i}{{{r}}}" for i, r in enumerate(rules) if r),
           "@media (prefers-reduced-motion: reduce){.explainer *{animation-delay:-21s!important;animation-play-state:paused!important}}"]
    (REPO / "website/static/explainer.css").write_text("\n".join(out) + "\n")
    (REPO / "website/explainer.html").write_text(f'<div class="explainer">{st}</div>\n')
    print("site: wrote website/static/explainer.css and website/explainer.html")


site()
