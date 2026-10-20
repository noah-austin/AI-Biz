"""Two videos from the demo walkthrough, each in a wide and a tall (phone) cut.

- The tour (What we build page): its own title card, then straight into the demo hub. About 30 seconds. It opens
  differently from the home page explainer on purpose, so visitors don't take it for the same video.
- The overview (LinkedIn, follow-up emails): the explainer's story, then the same demo. About 52 seconds.

    python build.py                     # writes capture.html (the demo scene)
    python combined.py EXPLAINER_FRAMES_DIR WORK_DIR [ffmpeg]

EXPLAINER_FRAMES_DIR holds the explainer's frames from ../animation (frames.py at 30 fps) in wide/ and tall/.
Writes ../../static/video/tour-{wide,tall}.mp4 (+ posters) and sanford-overview.mp4 here (full quality).

The tall cut films the same scene with a "camera" that follows the action, so the text stays readable on a phone,
and puts the captions above it in bigger type. The edit is the same in both cuts (EDIT below).
"""
import json
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
STATIC = HERE.parents[1] / "static" / "video"
FPS = 30
EXPLAINER_END = 20.9          # the explainer plays to "Then we build on it." (then fades)
END_CARD = (22.4, 26.0)       # the explainer's end card closes both cuts
# the overview (LinkedIn): scene time ranges of the demo, at the given speed; it leaves out the alerts screen (38-44.7 s)
EDIT = [(12.5, 38.0, 1.25), (44.75, 54.6, 1.25)]
# the tour: the walkthrough's own opening (systems -> hub -> browser), then the demo; ranges that meet play on unbroken
TOUR = [(3.3, 15.0, 1.15), (15.0, 54.6, 1.25)]
# the tour's opening captions, as three steps (replacing scene.html's first three captions in this cut only)
TOUR_STEPS = [["1. We connect your systems.", "CRM, accounting, ERP, field service, payroll, spreadsheets. Read-only."],
              ["2. Everything lands in one place.", "Your data hub: one database you own, updated every hour."],
              ["3. Then we build the tools.", "Here’s what that looks like for a demo company."]]
TITLE_SECONDS = 2.8

# the demo scene's captions (same text and times as scene.html), shown above the camera in the tall cut
CAPS = [[3.4, 7.2, *TOUR_STEPS[0]], [7.6, 11.2, *TOUR_STEPS[1]], [11.6, 15.0, *TOUR_STEPS[2]],
        [15.4, 22.6, "One home page for the whole business.", "The numbers that matter, updated every hour."],
        [23.0, 30.2, "The weekly scorecard fills itself in.", "Green means the goal was hit. Nobody types it up."],
        [30.6, 38.2, "Ask questions in plain English.", "Answers come straight from your own data."],
        [38.6, 44.6, "Alerts reach the right person.", "When something needs attention, the right leader hears about it."],
        [45.0, 53.6, "AI agents do the daily legwork.", "They prepare the work. A person approves anything that goes out."]]
# camera: [scene time, centre x, centre y, zoom] in film pixels (the film is 1920 x 1080; the camera is 1008 x 1284)
CAM = [[3.3, 960, 600, 0.75], [11.4, 960, 600, 0.75], [13.2, 960, 621, 0.593], [14.4, 960, 621, 0.593],   # opening: systems fly into the hub
       [15.6, 545, 640, 1.5], [18.6, 545, 640, 1.5], [19.8, 1330, 640, 1.5], [21.6, 1330, 640, 1.5],      # home: tiles, chart, last 7 days
       [22.6, 700, 600, 1.3],                                                                             # click Scorecard
       [23.6, 520, 640, 1.5], [24.6, 520, 640, 1.5], [26.2, 1010, 640, 1.5], [28.8, 1010, 640, 1.5],     # weeks fill in
       [30.6, 1480, 620, 1.5], [38.0, 1480, 620, 1.5],                                                    # Ask AI panel
       [38.9, 585, 640, 1.25], [41.1, 585, 640, 1.25], [41.9, 1600, 700, 1.4], [44.0, 1600, 700, 1.4],    # alerts, then the phone
       [44.75, 592, 640, 1.3], [48.4, 592, 640, 1.3], [49.4, 1390, 640, 1.3], [54.6, 1390, 640, 1.3]]    # brief, then approval

TALL = """<style>
body { width:1080px; height:1620px; overflow:hidden; background:#f3eee2 }
#tcap { position:absolute; left:60px; top:66px; width:960px }
#tcap .c1 { font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:68px; line-height:1.1; color:#2a2622 }
#tcap .c2 { font-family:'Inter', system-ui, Arial, sans-serif; font-size:35px; line-height:1.3; color:#4f4842; margin-top:12px }
#cam { position:absolute; left:36px; top:310px; width:1008px; height:1284px; overflow:hidden; border-radius:28px; background:#f3eee2 }
#film { position:absolute; left:0; top:0; transform-origin:0 0 }
#film .cap { display:none !important }
</style>"""
TALL_JS = """<script>
(() => {
const CAPS = %s, CAM = %s;
const cl = x => Math.min(1, Math.max(0, x)), sm = x => { x = cl(x); return x * x * (3 - 2 * x); };
const ease = x => { x = cl(x); return x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const box = document.getElementById('tcap'), film = document.getElementById('film');
window.renderTall = t => {
  renderAt(t);
  let c = null, o = 0;
  for (const [a, b, l1, l2] of CAPS) { const k = Math.min(sm((t - a + 0.5) / 0.5), 1 - sm((t - b + 0.5) / 0.5)); if (k > o) { o = k; c = [l1, l2]; } }
  box.innerHTML = c ? `<div class="c1">${c[0]}</div><div class="c2">${c[1]}</div>` : '';
  box.style.opacity = o; box.style.transform = `translateY(${(1 - o) * 14}px)`;
  let k = CAM.length - 1; for (let i = 0; i < CAM.length - 1; i++) if (t < CAM[i + 1][0]) { k = i; break; }
  const A = CAM[k], B = CAM[Math.min(k + 1, CAM.length - 1)], e = B[0] > A[0] ? ease((t - A[0]) / (B[0] - A[0])) : 0;
  const [x, y, z] = [1, 2, 3].map(j => A[j] + (B[j] - A[j]) * e);
  film.style.transform = `translate(${504 - x * z}px, ${642 - y * z}px) scale(${z})`;
};
})();
</script>"""


def tall_page() -> Path:
    src = (HERE / "capture.html").read_text()
    film = '<div id="film" class="film">\n  <div id="stage"></div>\n</div>'
    assert film in src, "capture.html changed shape; run build.py"
    out = src.replace("</head>", TALL + "</head>").replace(film, f'<div id="tcap"></div><div id="cam">{film}</div>')
    out = out.replace("</body>", TALL_JS % (json.dumps(CAPS), json.dumps(CAM)) + "</body>")
    path = HERE / "capture-tall.html"
    path.write_text(out)
    return path


def render_title(cut: str, work: Path) -> Path:
    """The tour's opening card, as one still in the brand's style (the end card is the explainer's)."""
    w, h = {"wide": (1920, 1080), "tall": (1080, 1620)}[cut]
    big = {"wide": 96, "tall": 84}[cut]
    seal = (HERE.parents[1] / "static" / "brand" / "seal.svg").as_uri()
    fonts = (HERE / "capture.html").read_text().split("<style>", 1)[1].split("body{", 1)[0]   # the embedded @font-faces
    page = f"""<!doctype html><html><head><meta charset="utf-8"><style>{fonts}
body {{ margin:0; width:{w}px; height:{h}px; background:#f4efe3; display:flex; flex-direction:column; align-items:center;
  justify-content:center; gap:26px; text-align:center; font-family:'Inter', Arial, sans-serif; color:#2a2622 }}
.e {{ font-size:{big * 0.3:.0f}px; font-weight:600; letter-spacing:.2em; text-transform:uppercase; color:#8f6f3e }}
.t {{ font-family:'Playfair Display', Playfair, Georgia, serif; font-weight:700; font-size:{big}px; line-height:1.1; padding:0 60px }}
.s {{ font-size:{big * 0.36:.0f}px; color:#4f4842; max-width:{w - 160}px; line-height:1.4; text-wrap:balance }}
</style></head><body><img src="{seal}" width="{big * 1.6:.0f}" height="{big * 1.6:.0f}" alt="">
<div class="e">Sanford Operations</div><div class="t">From scattered data to working tools</div>
<div class="s">Bluestem Facility Services, a fictional company with made-up data.</div></body></html>"""
    src = work / f"title-{cut}.html"
    src.write_text(page)
    out = work / f"title-{cut}.png"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": w, "height": h})
        pg.goto(src.resolve().as_uri())
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(out))
        b.close()
    return out


def render_demo(cut: str, work: Path, edit=EDIT, name="demo") -> list[Path]:
    page = HERE / "capture.html" if cut == "wide" else tall_page()
    size = {"wide": (1920, 1080), "tall": (1080, 1620)}[cut]
    call = "renderAt" if cut == "wide" else "renderTall"
    dirs = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": size[0], "height": size[1]})
        pg.add_init_script("window.CAPTURE = true")
        pg.goto(page.resolve().as_uri())
        pg.wait_for_function("window.sceneReady === true")
        if name == "tour":   # the opening captions read as three steps in this cut
            pg.evaluate("""steps => [...document.querySelectorAll('#stage .cap')].slice(0, 3).forEach((c, i) => {
                c.querySelector('.cap1').textContent = steps[i][0]; c.querySelector('.cap2').textContent = steps[i][1]; })""", TOUR_STEPS)
        n, last_end, i0 = -1, None, 0
        for a, z, speed in edit:
            if a != last_end:   # a new piece of the edit (otherwise carry straight on in the same folder)
                n, i0 = n + 1, 0
                d = work / f"{name}-{cut}-{n}"
                d.mkdir(parents=True, exist_ok=True)
                dirs.append(d)
            for i in range(round((z - a) / speed * FPS)):
                pg.evaluate(f"{call}({a + i * speed / FPS})")
                pg.screenshot(path=str(d / f"f{i0 + i:04d}.png"))
            i0 += round((z - a) / speed * FPS)
            last_end = z
        b.close()
    return dirs


def assemble(cut: str, explainer: Path, demo: list[Path], out: Path, crf: int, width: int | None):
    """explainer story -> fade -> demo part 1 -> crossfade -> demo part 2 -> crossfade -> end card."""
    ff = sys.argv[3] if len(sys.argv) > 3 else "ffmpeg"
    bg = "0xF4EFE3"
    d1 = len(list(demo[0].glob("*.png"))) / FPS
    d2 = len(list(demo[1].glob("*.png"))) / FPS
    end_start, end_len = END_CARD[0], END_CARD[1] - END_CARD[0]
    scale = f",scale={width}:-2:flags=lanczos" if width else ""
    norm = f"fps={FPS},format=yuv420p,settb=AVTB"
    graph = (f"[0:v]trim=end={EXPLAINER_END},setpts=PTS-STARTPTS,{norm},fade=t=out:st={EXPLAINER_END - 0.6}:d=0.6:color={bg}[x];"
             f"[1:v]setpts=PTS-STARTPTS,{norm},fade=t=in:st=0:d=0.5:color={bg}[a];"
             f"[2:v]setpts=PTS-STARTPTS,{norm}[b];"
             f"[3:v]trim=start={end_start}:end={END_CARD[1]},setpts=PTS-STARTPTS,{norm}[e];"
             f"[a][b]xfade=transition=fade:duration=0.3:offset={d1 - 0.3:.3f}[ab];"
             f"[ab][e]xfade=transition=fade:duration=0.5:offset={d1 + d2 - 0.3 - 0.5:.3f}[abe];"
             f"[x][abe]concat=n=2:v=1{scale}[v]")
    seq = lambda d: ["-framerate", str(FPS), "-i", str(d / "f%04d.png")]
    cmd = [ff, "-loglevel", "error", "-y", *seq(explainer), *seq(demo[0]), *seq(demo[1]), *seq(explainer),
           "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264", "-preset", "veryslow", "-tune", "animation",
           "-crf", str(crf), "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


def assemble_tour(cut: str, title: Path, demo: list[Path], explainer: Path, out: Path, crf: int, width: int | None):
    """title card -> crossfade -> the demo piece(s), crossfaded where the edit cuts -> crossfade -> end card."""
    ff = sys.argv[3] if len(sys.argv) > 3 else "ffmpeg"
    lengths = [len(list(d.glob("*.png"))) / FPS for d in demo]
    scale = f",scale={width}:-2:flags=lanczos" if width else ""
    norm = f"fps={FPS},format=yuv420p,settb=AVTB"
    n = len(demo)
    graph = [f"[{i}:v]setpts=PTS-STARTPTS,{norm}[s{i}]" for i in range(n + 1)]
    graph.append(f"[{n + 1}:v]trim=start={END_CARD[0]}:end={END_CARD[1]},setpts=PTS-STARTPTS,{norm}[s{n + 1}]")
    t, prev = TITLE_SECONDS, "s0"
    for i in range(1, n + 2):   # each join: 0.5 s into and out of the cards, 0.3 s between demo pieces
        d = 0.5 if i in (1, n + 1) else 0.3
        graph.append(f"[{prev}][s{i}]xfade=transition=fade:duration={d}:offset={t - d:.3f}[j{i}]")
        t, prev = t - d + (lengths[i - 1] if i <= n else 0), f"j{i}"
    graph[-1] = graph[-1].replace(f"[j{n + 1}]", f"{scale}[v]")
    seq = lambda d: ["-framerate", str(FPS), "-i", str(d / "f%04d.png")]
    cmd = [ff, "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", str(TITLE_SECONDS), "-i", str(title),
           *[x for d in demo for x in seq(d)], *seq(explainer), "-filter_complex", ";".join(graph), "-map", "[v]",
           "-c:v", "libx264", "-preset", "veryslow", "-tune", "animation", "-crf", str(crf), "-pix_fmt", "yuv420p",
           "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    frames, work = Path(sys.argv[1]), Path(sys.argv[2])
    work.mkdir(parents=True, exist_ok=True)
    for cut, width in (("wide", 1280), ("tall", 720)):
        tour = render_demo(cut, work, TOUR, "tour")
        assemble_tour(cut, render_title(cut, work), tour, frames / cut, STATIC / f"tour-{cut}.mp4", 28, width)
        if cut == "wide" and "--overview" in sys.argv:   # the longer LinkedIn cut; only when asked
            assemble(cut, frames / cut, render_demo(cut, work), HERE / "sanford-overview.mp4", 20, None)
        print(cut, "done")
