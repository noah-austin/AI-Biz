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

## The overview video (explainer + demo)

`combined.py` joins the explainer's story (`../animation`, to "Then we build on it.") with this walkthrough's demo part,
leaving out the alerts screen and playing the demo at 1.25×, then closes on the explainer's end card: about 52 seconds.
It writes `website/static/video/overview-wide.mp4` and `overview-tall.mp4` (played on the What we build page) and
`sanford-overview.mp4` here (full quality, for LinkedIn and follow-up emails).

The tall cut films the same scene with a camera that follows the action (`CAM` in `combined.py`), with the captions above
it in bigger type, so the screens stay readable on a phone.

```bash
python build.py                                              # capture.html
# explainer frames at 30 fps in FRAMES/wide and FRAMES/tall (see ../animation/README.md)
python combined.py FRAMES /tmp/overview-work [path to ffmpeg]
```
