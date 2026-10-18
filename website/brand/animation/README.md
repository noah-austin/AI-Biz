# Explainer animation

`sanford-explainer.mp4`: 26.5 seconds (a 2.5-second title card, then 24 seconds), 1920 × 1080, silent, loops. For LinkedIn, the website and calls. `poster.png` is the end card; the first frame is the title card.

Rebuild after a change:

```bash
python website/brand/animation/build.py          # writes index.html (viewer page) and capture.html here
node website/brand/animation/frames.js "$PWD/website/brand/animation/capture.html" /tmp/frames fps 30   # needs Playwright
ffmpeg -framerate 30 -i /tmp/frames/f%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart website/brand/animation/sanford-explainer.mp4
```

The beats and their timings are in `build.py` (`CAPS`, `SYSTEMS`, `TOOLS`). The numbers on screen are illustrative.
