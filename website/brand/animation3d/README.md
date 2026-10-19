# 3D explainer: "The foundation"

`sanford-explainer-3d.mp4`: 29 seconds, 1920 × 1080, silent. A small 3D world (Three.js, real lighting and shadows):

1. **Islands.** Seven systems (CRM, accounting, inventory, ERP, field service, HR & payroll, spreadsheets), each its own building on its own island, each with its own data circling it.
2. **Bring it together.** Brass channels reach from every island to the centre, and a foundation stamped with the seal rises out of the water. The data flows in.
3. **Build on it.** A tower goes up on the foundation, floor by floor, each floor signed with its name: reports, tools, alerts, Ask AI, AI agents. A dome caps it.
4. **Put to work.** AI agents fly from the top of the tower out to every island and back, and each trip leaves a small finished job ("Reminder drafted", "Reorder flagged"...). The light warms towards evening so the lit tower glows.

Rebuild after a change (needs Playwright, Chromium and ffmpeg):

```bash
cd website/brand/animation3d
npm pack three@0.160.0 && tar xzf three-0.160.0.tgz      # local copy of three.js for rendering
python build.py                                          # writes capture.html and index.html (viewer page)
mkdir -p frames && node frames3d.js "$PWD/capture.html" "$PWD/frames" fps 30 29
ffmpeg -framerate 30 -i frames/f%04d.png -c:v libx264 -crf 18 -pix_fmt yuv420p -movflags +faststart sanford-explainer-3d.mp4
```

To render faster, split the frames across processes: `... fps 30 29 <first> <last>` renders frames first to last-1.

Everything on screen is a function of time (`renderAt(t)` in `scene.html`), so every render is the same.
