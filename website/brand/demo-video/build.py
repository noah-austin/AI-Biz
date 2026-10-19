"""Builds the demo walkthrough video page: capture.html (local fonts, for rendering frames) and index.html (the viewer page)."""
import base64
from pathlib import Path

HERE = Path(__file__).parent
REPO = Path(__file__).resolve().parents[3]
b64 = lambda p: base64.b64encode((REPO / p).read_bytes()).decode()
SEAL_OX = "data:image/svg+xml;base64," + b64("website/static/brand/seal.svg")
SEAL_REV = "data:image/svg+xml;base64," + b64("website/static/brand/seal-reversed.svg")

FILM_CSS = """
.film { position:relative; width:1920px; height:1080px; overflow:hidden; background:#f5efe4; color:#2a2622;
  font-family:'Inter', system-ui, Arial, sans-serif; transform-origin:0 0; text-align:left; line-height:normal }
.film * { box-sizing:border-box }
#stage { position:absolute; inset:0 }
#stage > * { position:absolute }
.cap { left:140px; top:58px; width:1640px; visibility:hidden }
.cap1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:54px; line-height:1.1 }
.cap2 { font-size:26px; color:#4f4842; margin-top:10px }

/* act 1 */
.sys { z-index:1; width:340px; padding:20px 26px; background:#fbf8f2; border:1.5px solid #d9cdb9; border-radius:14px; box-shadow:0 10px 28px rgba(42,38,34,.10); visibility:hidden }
.sname { font-weight:600; font-size:30px } .sdet { font-size:21px; color:#4f4842; margin-top:4px }
.hub { z-index:3; left:960px; top:600px; display:flex; flex-direction:column; align-items:center; visibility:hidden }
.hubdisc { width:290px; height:290px; border-radius:50%; background:#6b1f2a; display:flex; align-items:center; justify-content:center;
  box-shadow:0 0 0 10px rgba(107,31,42,.12), 0 24px 60px rgba(107,31,42,.30) }
.hubt1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:42px; margin-top:26px }
.hubt2 { font-size:22px; color:#4f4842; margin-top:4px; letter-spacing:.02em }
.hubring { left:960px; top:600px; margin-top:-53px; width:300px; height:300px; border-radius:50%; border:3px solid #8f6f3e; visibility:hidden }

/* the browser window */
.win { left:140px; top:196px; width:1640px; height:850px; background:#f4f3f0; border-radius:16px; overflow:hidden; border:1px solid #cfc6b6;
  box-shadow:0 30px 80px rgba(42,38,34,.25); font-family:'Inter', system-ui, Arial, sans-serif; color:#1d1d1f; visibility:hidden }
.win * { position:relative }
.chrome { height:44px; background:#e9e6e0; display:flex; align-items:center; padding-left:18px; gap:9px; border-bottom:1px solid #d8d3ca }
.chrome i { width:13px; height:13px; border-radius:50%; background:#cfc8bc }
.url { margin-left:24px; width:520px; height:28px; border-radius:8px; background:#f7f5f1; font-size:15px; color:#6b665f; display:flex; align-items:center; padding-left:14px }
.nav { height:72px; background:#fbfaf8; border-bottom:1px solid #e3dfd8; display:flex; align-items:center; padding:0 48px }
.logo { font-weight:700; font-size:22px; display:flex; align-items:center; gap:10px; margin-right:34px }
.logo b { width:24px; height:24px; border-radius:6px; background:linear-gradient(135deg,#17a2a2,#2463d6) } .logo span { color:#7a7670; font-weight:600 }
.tabs { display:flex; gap:6px; font-size:19px; color:#4c4944 } .tabs span { padding:9px 14px; border-radius:9px }
.tabs span.on { background:#ebe8e2; color:#1d1d1f; font-weight:600 }
.ask { margin-left:auto; padding:9px 18px; border-radius:22px; border:1px solid #d8d3ca; background:#f1efeb; font-weight:600; font-size:18px }
.ask.on { background:#2463d6; color:#fff; border-color:#2463d6 }
.body { height:734px }
.note { position:absolute; left:48px; bottom:16px; font-size:15px; color:#8a857d; visibility:hidden }
.page { position:absolute; inset:0; padding:36px 48px; visibility:hidden }
.ptitle { font-weight:700; font-size:38px } .psub { font-size:20px; color:#6b665f; margin-top:6px; margin-bottom:26px }
.card { background:#fff; border:1px solid #e4e0d9; border-radius:14px }
.muted { color:#7a7670 } .sm { font-size:15px }
.tiles { display:flex; gap:16px } .tile { flex:1; padding:18px 20px; height:150px; visibility:hidden }
.tl { font-size:17px; color:#55524c } .tv { font-weight:700; font-size:40px; margin-top:8px; font-variant-numeric:tabular-nums } .td { font-size:16px; color:#6b665f; margin-top:6px }
.td.up { color:#137a4f } .td.down { color:#b8322a }
.grid2 { display:flex; gap:18px; margin-top:18px } .chart { flex:1.75; height:370px; padding:20px 24px; visibility:hidden } .last7 { flex:1; height:370px; padding:20px 24px; visibility:hidden }
.ch { display:flex; justify-content:space-between; align-items:baseline; font-size:20px; margin-bottom:12px } .ch .muted { font-size:16px }
.lg { font-size:15px; color:#55524c; display:flex; align-items:center; gap:6px } .lg i { width:12px; height:12px; border-radius:3px; display:inline-block; margin-left:10px }
.b26 { background:#2463d6 } .b25 { background:#c9c7bb }
.bars { display:flex; height:262px; align-items:flex-end; gap:12px; border-bottom:1px solid #ddd8cf; padding:0 6px }
.bg { flex:1; height:100%; display:flex; flex-direction:column; justify-content:flex-end } .pair { display:flex; align-items:flex-end; gap:4px; height:100% }
.bar { flex:1; border-radius:4px 4px 0 0; height:0 } .bar.none { visibility:hidden }
.mo { position:absolute; bottom:-26px; width:100%; text-align:center; font-size:14px; color:#8a857d }
.l7 { display:flex; justify-content:space-between; gap:16px; padding:8px 0; border-top:1px solid #efebe5; font-size:17px; visibility:hidden }
.l7.head { font-weight:600; border-top:none; font-size:18px; padding-top:12px } .lnk { color:#2463d6 } .amt { font-weight:600; white-space:nowrap }

.sc { padding:10px 22px } .scrow { display:flex; align-items:center; border-top:1px solid #efebe5; height:64px } .schead { border-top:none; height:44px; font-size:16px; color:#6b665f; font-weight:600 }
.scm { width:300px; font-size:18px; font-weight:600 } .scm .sm { font-weight:400 } .scc { flex:1; text-align:center; font-size:17px } .scg { width:110px; text-align:right; font-size:16px; color:#55524c; visibility:hidden }
.pillc { display:inline-block; padding:6px 10px; border-radius:8px; font-variant-numeric:tabular-nums; visibility:hidden } .pillc.ok { background:#dff1e7; color:#0f6a43 } .pillc.no { background:#f8e1de; color:#a32a22 }

.dim { position:absolute; inset:0; background:#1d1d1f; visibility:hidden }
.panel { position:absolute; right:0; top:116px; width:660px; height:734px; background:#fff; border-left:1px solid #e0dcd5; box-shadow:-20px 0 50px rgba(0,0,0,.12); padding:28px 32px; visibility:hidden }
.ph { display:flex; justify-content:space-between; align-items:baseline; font-size:24px } .ph .muted { font-size:16px }
.qbox { margin-top:22px; height:58px; border:1.5px solid #cfd9ee; border-radius:12px; padding:0 18px; display:flex; align-items:center; font-size:20px; width:480px }
.caret { width:2px; height:26px; background:#2463d6; margin-left:2px }
.send { position:absolute; right:32px; top:96px; height:58px; width:100px; border-radius:12px; background:#2463d6; color:#fff; font-weight:600; font-size:19px; display:flex; align-items:center; justify-content:center }
.you { margin:28px 0 0 auto; width:fit-content; max-width:460px; background:#eef3fc; border-radius:14px 14px 4px 14px; padding:12px 18px; font-size:19px; visibility:hidden }
.think { margin-top:18px; display:flex; gap:7px; visibility:hidden } .think i { width:10px; height:10px; border-radius:50%; background:#8a857d }
.ans { margin-top:18px; font-size:22px; line-height:1.5; min-height:100px; visibility:hidden }
.cmp { margin-top:20px; display:flex; flex-direction:column; gap:12px; visibility:hidden } .cr { display:flex; align-items:center; gap:14px; font-size:16px; color:#55524c }
.cr span { width:170px } .cr b { color:#1d1d1f; font-size:17px } .cb { height:22px; border-radius:5px; max-width:300px; flex:none } .cb.now { background:#b8322a } .cb.then { background:#c9c7bb }
.cr .cb { width:0 } .cmp .cr { width:100% } .cr .cb { flex-basis:auto }
.src { margin-top:22px; display:inline-block; font-size:15px; color:#55524c; background:#f3f1ec; border-radius:8px; padding:7px 12px; visibility:hidden }

.alist { padding:6px 26px; width:1170px } .arow { display:flex; align-items:center; gap:18px; padding:16px 0; border-top:1px solid #efebe5; font-size:18px; visibility:hidden }
.arow:first-child { border-top:none } .arow.hl { background:#fff7e6; margin:0 -26px; padding-left:26px; padding-right:26px }
.bang { width:34px; height:34px; border-radius:50%; background:#f8e1de; color:#a32a22; font-weight:700; display:flex; align-items:center; justify-content:center; flex:none }
.ak { flex:1 } .akind { font-weight:600; font-size:16px; color:#a32a22; margin-bottom:2px } .adt { width:80px; text-align:right; font-size:15px }
.phone { left:1470px; top:470px; width:330px; height:640px; border-radius:46px; background:linear-gradient(160deg,#2b3a4a,#18202b); border:10px solid #111; box-shadow:0 30px 70px rgba(0,0,0,.35); padding:22px; color:#fff; visibility:hidden }
.notch { position:absolute; left:50%; top:10px; width:110px; height:26px; margin-left:-55px; background:#111; border-radius:14px }
.ptime { position:relative; text-align:center; font-size:64px; font-weight:300; margin-top:50px } .pdate { position:relative; text-align:center; font-size:16px; opacity:.85 }
.notif { position:relative; margin-top:34px; background:rgba(255,255,255,.88); color:#1d1d1f; border-radius:18px; padding:14px 16px; visibility:hidden }
.nh { font-size:12px; color:#6b665f; display:flex; align-items:center; gap:7px; letter-spacing:.04em } .nh span { margin-left:auto } .nlogo { width:16px; height:16px; border-radius:4px; background:linear-gradient(135deg,#17a2a2,#2463d6) }
.nt { font-weight:600; font-size:16px; margin-top:6px } .nb { font-size:15px; margin-top:2px; line-height:1.35 }

.ag .brief { flex:1.25; height:560px; padding:22px 26px; visibility:hidden } .ag .appr { flex:1; height:560px; padding:22px 26px; visibility:hidden }
.bl { padding:16px 0; border-top:1px solid #efebe5; font-size:20px; line-height:1.45; visibility:hidden } .bl:nth-child(2) { border-top:none }
.mail { margin-top:6px; background:#f6f4f0; border-radius:12px; padding:18px 20px; height:458px } .mail.ok { background:#eaf5ee }
.mh { font-weight:600; font-size:19px } .mbody { white-space:pre-line; font-size:17px; line-height:1.42; margin-top:10px; height:268px }
.btns { display:flex; gap:10px; margin-top:6px; visibility:hidden } .btns span { padding:11px 18px; border-radius:10px; font-weight:600; font-size:17px }
.approve { background:#2463d6; color:#fff } .approve.press { background:#1a4fb0 } .copy { border:1px solid #d8d3ca; background:#fff }
.done { position:absolute; left:20px; bottom:22px; font-weight:600; color:#0f6a43; font-size:19px; visibility:hidden }

.cursor { left:0; top:0; z-index:20; visibility:hidden } .click { width:46px; height:46px; border-radius:50%; border:3px solid #2463d6; z-index:19; visibility:hidden }
.veil { inset:0; background:#f5efe4; visibility:hidden; z-index:30 }
.card-end { inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; z-index:31; visibility:hidden }
.title { background:#f5efe4; gap:22px; z-index:32 }
.card-end img { margin-bottom:40px }
.e1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:76px; line-height:1.12; text-align:center }
.e2 { font-size:34px; font-weight:600; color:#6b1f2a; margin-top:40px; letter-spacing:.02em }
.t0 { font-size:26px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:#8f6f3e }
.t1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:92px }
"""

scene = (HERE / "scene.html").read_text().replace("SEAL_OX", SEAL_OX).replace("SEAL_REV", SEAL_REV)
fonts = (f"@font-face{{font-family:'Playfair Display';font-weight:700;src:url(data:font/woff2;base64,{b64('website/static/fonts/playfair-700.woff2')})}}"
         f"@font-face{{font-family:'Inter';font-weight:100 900;src:url(data:font/woff2;base64,{b64('website/static/fonts/inter-latin-var.woff2')})}}")
(HERE / "capture.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><style>{fonts}body{{margin:0}}{FILM_CSS}</style>"
                                   f"<script>window.CAPTURE=true</script></head><body>{scene}</body></html>")

PAGE = """<title>Sanford Demo Walkthrough</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@300;400;600;700&display=swap">
<style>
/* One look by choice: the brand's parchment world. A 1920x1080 film frame scaled to the column. */
:root { --bg:#efe7d9; --ink:#2a2622; --ink-2:#4f4842; --accent:#6b1f2a; --accent-ink:#f5efe4; --line:#d9cdb9; color-scheme:light }
body { background:var(--bg); color:var(--ink); font:16px/1.5 'Inter', system-ui, -apple-system, 'Segoe UI', Arial, sans-serif; margin:0 }
.wrap { max-width:1200px; margin:0 auto; padding-block:32px 56px; padding-left:max(16px, env(safe-area-inset-left, 0px));
  padding-right:max(16px, env(safe-area-inset-right, 0px)); display:flex; flex-direction:column; gap:18px }
.eyebrow { margin:0; font-size:12.5px; font-weight:600; letter-spacing:.16em; text-transform:uppercase; color:#7a5c30 }
h1 { margin:0; font:700 clamp(26px, 4.5vw, 38px)/1.15 'Playfair Display', Georgia, serif; text-wrap:balance }
.lead { margin:0; color:var(--ink-2); max-width:64ch }
.frame { position:relative; width:100%; aspect-ratio:16 / 9; overflow:hidden; border-radius:14px; border:1px solid var(--line);
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
  <h1>See it at work</h1>
  <p class="lead">One minute: your systems come together in your data hub, then a walk through what we build on it, using the Bluestem demo company. The video file is made from this same animation.</p>
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
(HERE / "index.html").write_text(PAGE.replace("FILM_CSS", FILM_CSS).replace("SCENE", scene))
print("built")
