# 3D explainer

`sanford-explainer-3d.mp4`: 26.5 seconds, 1920 × 1080, silent. Same story as `../animation/`, in 3D (Three.js): many systems, brought together into the data hub (a seal coin), working as one, then built on.

Rebuild after a change (needs Playwright, Chromium and ffmpeg):

```bash
cd website/brand/animation3d
npm pack three@0.160.0 && tar xzf three-0.160.0.tgz      # local copy of three.js for rendering
python build.py                                          # writes capture.html and index.html (viewer page)
mkdir -p frames && node frames3d.js "$PWD/capture.html" "$PWD/frames" fps 30 26.5
ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sanford-explainer-3d.mp4
```

Everything on screen is a function of time (`renderAt(t)` in `scene.html`), so every render is the same. The numbers shown are illustrative.
