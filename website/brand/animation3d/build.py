"""Builds the 3D explainer: capture.html (local three.js + fonts, for rendering frames) and index.html (the viewer page)."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parents[3]
b64 = lambda p: base64.b64encode((REPO / p).read_bytes()).decode()
SEAL_OX = "data:image/svg+xml;base64," + b64("website/static/brand/seal.svg")
SEAL_REV = "data:image/svg+xml;base64," + b64("website/static/brand/seal-reversed.svg")

FILM_CSS = """
.film { position:relative; width:1920px; height:1080px; overflow:hidden; background:#f5efe4; color:#2a2622;
  font-family:'Inter', system-ui, Arial, sans-serif; transform-origin:0 0 }
.film canvas { position:absolute; left:0; top:0; width:1920px; height:1080px }
.lt { position:absolute; left:96px; bottom:84px; max-width:1200px; padding:26px 34px 28px 40px; opacity:0;
  background:rgba(245,239,228,.9); border-radius:6px; box-shadow:0 12px 40px rgba(42,38,34,.18) }
.lt i { position:absolute; left:0; top:0; bottom:0; width:8px; background:#8f6f3e; border-radius:6px 0 0 6px }
.c1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:56px; line-height:1.1 }
.c2 { font-size:28px; color:#4f4842; margin-top:12px }
.veil { position:absolute; inset:0; background:#f5efe4 }
.card-end { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; opacity:0; background:transparent }
#title { background:#f5efe4; gap:22px }
.card-end img { margin-bottom:40px }
#title img { margin-bottom:0 }
.e1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:76px; line-height:1.12; text-align:center }
.e2 { font-size:34px; font-weight:600; color:#6b1f2a; margin-top:40px; letter-spacing:.02em }
.t0 { font-size:26px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:#8f6f3e; margin-top:14px }
.t1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:92px }
"""

scene = (HERE / "scene.html").read_text().replace("SEAL_OX", SEAL_OX).replace("SEAL_REV", SEAL_REV)

fonts = (f"@font-face{{font-family:'Playfair Display';font-weight:700;src:url(data:font/woff2;base64,{b64('website/static/fonts/playfair-700.woff2')})}}"
         f"@font-face{{font-family:'Inter';font-weight:100 900;src:url(data:font/woff2;base64,{b64('website/static/fonts/inter-latin-var.woff2')})}}")
capture = (f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}body{{margin:0}}{FILM_CSS}</style>"
           f"<script>window.CAPTURE=true</script></head><body>{scene.replace('THREE_SRC', 'package/build/three.min.js')}</body></html>")
(HERE / "capture.html").write_text(capture)

PAGE = """<title>Sanford Explainer 3D</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;500;600&display=swap">
<style>
/* One look by choice: the brand's parchment world. A 1920x1080 film frame scaled to the column. */
:root { --bg:#efe7d9; --ink:#2a2622; --ink-2:#4f4842; --accent:#6b1f2a; --accent-ink:#f5efe4; --line:#d9cdb9; color-scheme:light }
body { background:var(--bg); color:var(--ink); font:16px/1.5 'Inter', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif }
.wrap { max-width:1200px; margin:0 auto; padding-block:32px 56px; padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px)); display:flex; flex-direction:column; gap:18px }
.eyebrow { margin:0; font-size:12.5px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:#7a5c30 }
h1 { margin:0; font:700 clamp(26px, 4.5vw, 38px)/1.15 'Playfair Display', Georgia, serif; text-wrap:balance }
.lead { margin:0; color:var(--ink-2); max-width:64ch }
.frame { position:relative; width:100%; aspect-ratio:16 / 9; max-width:100%; overflow:hidden; border-radius:14px; border:1px solid var(--line);
  box-shadow:0 18px 48px rgba(42,38,34,.14); background:#f5efe4 }
.frame .film { position:absolute; left:0; top:0 }
.controls { display:flex; gap:10px; flex-wrap:wrap }
button { font:600 14px 'Inter', system-ui, Arial, sans-serif; border-radius:8px; padding:9px 16px; cursor:pointer; min-height:38px;
  border:1px solid var(--line); background:#fbf8f2; color:var(--ink) }
button.primary { background:var(--accent); color:var(--accent-ink); border-color:var(--accent) }
button:focus-visible { outline:3px solid #8f6f3e; outline-offset:2px }
FILM_CSS
</style>
<div class="wrap">
  <p class="eyebrow">Sanford Operations</p>
  <h1>The foundation</h1>
  <p class="lead">A small world of separate systems, joined to one foundation, with tools, AI and AI agents built on top. The video file is made from this same scene.</p>
  <div class="frame" id="frame">SCENE</div>
  <div class="controls"><button type="button" class="primary" id="toggle">Pause</button><button type="button" id="replay">Play from the start</button></div>
</div>
<script>
(() => {
  const frame = document.getElementById('frame'), film = document.getElementById('film');
  const fit = () => { film.style.transform = 'scale(' + (frame.clientWidth / 1920) + ')'; };
  fit(); new ResizeObserver(fit).observe(frame);
  const btn = document.getElementById('toggle');
  btn.addEventListener('click', () => { if (window.film) btn.textContent = window.film.toggle() ? 'Play' : 'Pause'; });
  document.getElementById('replay').addEventListener('click', () => { if (window.film) { window.film.replay(); btn.textContent = 'Pause'; } });
})();
</script>
"""
(HERE / "index.html").write_text(PAGE.replace("FILM_CSS", FILM_CSS).replace(
    "SCENE", scene.replace("THREE_SRC", "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js")))
print("built")
