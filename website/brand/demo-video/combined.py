"""The overview video: the explainer's story, then a click-through of the demo hub, in a wide and a tall (phone) cut.

    python build.py                     # writes capture.html (the demo scene)
    python combined.py EXPLAINER_FRAMES_DIR WORK_DIR

EXPLAINER_FRAMES_DIR holds the explainer's frames from ../animation (frames.py at 30 fps) in wide/ and tall/.
Writes ../../static/video/overview-{wide,tall}.mp4 (+ posters) and sanford-overview.mp4 (full quality, for LinkedIn).

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
# scene time ranges of the demo, played at the given speed; the alerts screen (38-44.7 s) is left out
EDIT = [(12.5, 38.0, 1.25), (44.75, 54.6, 1.25)]

# the demo scene's captions (same text and times as scene.html), shown above the camera in the tall cut
CAPS = [[11.6, 15.0, "Then we build on it.", "Here’s what that looks like, for a demo company."],
        [15.4, 22.6, "One home page for the whole business.", "The numbers that matter, updated every hour."],
        [23.0, 30.2, "The weekly scorecard fills itself in.", "Green means the goal was hit. Nobody types it up."],
        [30.6, 38.2, "Ask questions in plain English.", "Answers come straight from your own data."],
        [45.0, 53.6, "AI agents do the daily legwork.", "They prepare the work. A person approves anything that goes out."]]
# camera: [scene time, centre x, centre y, zoom] in film pixels (the film is 1920 x 1080; the camera is 1008 x 1284)
CAM = [[12.5, 960, 621, 0.593], [14.4, 960, 621, 0.593],
       [15.6, 545, 640, 1.5], [18.6, 545, 640, 1.5], [19.8, 1330, 640, 1.5], [21.6, 1330, 640, 1.5],      # home: tiles, chart, last 7 days
       [22.6, 700, 600, 1.3],                                                                             # click Scorecard
       [23.6, 520, 640, 1.5], [24.6, 520, 640, 1.5], [26.2, 1010, 640, 1.5], [28.8, 1010, 640, 1.5],     # weeks fill in
       [30.6, 1480, 620, 1.5], [38.0, 1480, 620, 1.5],                                                    # Ask AI panel
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


def render_demo(cut: str, work: Path) -> list[Path]:
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
        for n, (a, z, speed) in enumerate(EDIT):
            d = work / f"demo-{cut}-{n}"
            d.mkdir(parents=True, exist_ok=True)
            frames = round((z - a) / speed * FPS)
            for i in range(frames):
                pg.evaluate(f"{call}({a + i * speed / FPS})")
                pg.screenshot(path=str(d / f"f{i:04d}.png"))
            dirs.append(d)
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


if __name__ == "__main__":
    frames, work = Path(sys.argv[1]), Path(sys.argv[2])
    for cut, width in (("wide", 1280), ("tall", 720)):
        demo = render_demo(cut, work)
        assemble(cut, frames / cut, demo, STATIC / f"overview-{cut}.mp4", 28, width)
        if cut == "wide":
            assemble(cut, frames / cut, demo, HERE / "sanford-overview.mp4", 20, None)
        print(cut, "done")
