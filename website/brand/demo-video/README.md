# Demo walkthrough video

`sanford-demo-walkthrough.mp4`: 60 seconds, 1920 × 1080, silent. Where it goes (website, LinkedIn, sales calls) is still to be decided.

1. **The story (0–15 s).** Title card. Seven systems scattered, then pulled into the data hub. A browser window grows out of the hub.
2. **The demo (15–54 s).** A cursor walks through redrawn pages of the Bluestem demo hub, each building itself:
   - Home: the year-to-date tiles count up, bookings by month grows, the last 7 days slide in.
   - Scorecard: eight weeks fill in, green for goal hit, red for missed.
   - Ask AI: "Which branch is behind on billing?" types out and the answer writes itself.
   - Alerts: this week's alerts slide in; the slipped Westlake deal lands on a phone.
   - AI agents: the morning brief writes itself, a payment reminder drafts, and a person clicks Approve.
3. **End card (55–60 s).**

The figures come from the fictional Bluestem demo data (as on the demo pages on Oct 18, 2026). The screens are simplified redraws, not screenshots, and say so on screen.

Rebuild after a change (needs Playwright, Chromium and ffmpeg):

```bash
cd website/brand/demo-video
python build.py                                  # writes capture.html and index.html (viewer page)
mkdir -p frames && node frames.js "$PWD/capture.html" "$PWD/frames" fps 30 60
ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sanford-demo-walkthrough.mp4
```

Everything on screen is a function of time (`renderAt(t)` in `scene.html`); captions and timings are in `CAPS` and the times in `renderAt`.

## The tour and the overview

`combined.py` makes two videos from this walkthrough's demo part (the alerts screen left out, the demo at 1.25×), each
closing on the explainer's end card:
- **The tour** (about 30 s): its own title card, "A tour of the hub", then straight into the demo. It plays on the What
  we build page (`website/static/video/tour-{wide,tall}.mp4`). It deliberately opens differently from the home page
  explainer, so visitors don't take it for the same video.
- **The overview** (about 52 s): the explainer's story first, then the demo. `sanford-overview.mp4` here, full quality,
  for LinkedIn and follow-up emails. Rebuilt only with `--overview`.

The tall cuts film the same scene with a camera that follows the action (`CAM`), with the captions above it in bigger
type, so the screens stay readable on a phone.

```bash
python build.py                                                # capture.html
# explainer frames at 30 fps in FRAMES/wide and FRAMES/tall (see ../animation/README.md)
python combined.py FRAMES /tmp/video-work [path to ffmpeg] [--overview]
```
