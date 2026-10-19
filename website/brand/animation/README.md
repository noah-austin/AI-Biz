# Explainer animation

Two cuts of the same 26.5-second story (a 2.5-second title card, then 24 seconds), silent, looping:

- `website/static/video/explainer-wide.mp4`: drawn at 1920 × 1080, saved at 1280 × 720 for the site. For LinkedIn, render a full-size copy (CRF 18, no scaling).
- `website/static/video/explainer-tall.mp4`: 720 × 1080, for phones: stacked layout, bigger text.

The home page plays the tall cut on screens up to 640px wide and the wide cut elsewhere, and shows a still of the end card
to visitors who ask for reduced motion. `poster.png` is the end card for social posts.

Rebuild after a change (the beats and timings are in `build.py`: `CAPS`, `SYSTEMS`, `TOOLS`; the numbers on screen are illustrative):

```bash
cd website/brand/animation
python build.py                                   # writes capture-wide.html and capture-tall.html (open them to preview)
for c in wide tall; do
  python frames.py capture-$c.html /tmp/frames-$c fps 30          # needs Playwright
  w=$([ $c = wide ] && echo 1280 || echo 720)   # the site plays these small; both together are about 1.2 MB
  ffmpeg -y -framerate 30 -i /tmp/frames-$c/f%04d.png -vf scale=$w:-2:flags=lanczos -c:v libx264 -preset veryslow -tune animation -crf 28 -pix_fmt yuv420p -movflags +faststart ../../static/video/explainer-$c.mp4
  ffmpeg -y -i /tmp/frames-$c/f0010.png -q:v 4 ../../static/video/explainer-$c.jpg        # poster: the title card
  ffmpeg -y -i /tmp/frames-$c/f0735.png -q:v 4 ../../static/video/explainer-$c-end.jpg    # reduced-motion still: the end card
done
```
