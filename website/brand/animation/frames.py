"""Renders a capture page to PNG frames: python frames.py capture-wide.html OUTDIR fps 30 [scale]
or stills at given seconds: python frames.py capture-tall.html OUTDIR at 3 8 12 17 22."""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

page_file, out, mode, *rest = sys.argv[1:]
size = {"wide": (1920, 1080, 1), "tall": (720, 1080, 1.5)}["tall" if "tall" in page_file else "wide"]
if mode == "fps":
    fps = float(rest[0])
    times = [i * 1000 / fps for i in range(round(26.5 * fps))]
else:
    times = [float(t) * 1000 for t in rest]
Path(out).mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": size[0], "height": size[1]}, device_scale_factor=size[2])
    pg.goto(Path(page_file).resolve().as_uri())
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(300)
    pg.evaluate("document.getAnimations().forEach(a => a.pause())")
    for i, t in enumerate(times):
        pg.evaluate("ms => document.getAnimations().forEach(a => { a.currentTime = ms; })", t)
        pg.screenshot(path=f"{out}/f{i:04d}.png")
    b.close()
print("frames", len(times))
