// Renders the brand SVGs to PNG. Usage: node website/brand/render_png.js  (needs Playwright + Chromium)
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const dir = path.join(__dirname, '..', 'static', 'brand');
const jobs = [["seal.svg", 1024, "seal-1024.png"], ["seal-solid.svg", 800, "profile-800.png"],
  ["mark.svg", 180, "apple-touch-icon.png"], ["mark.svg", 512, "mark-512.png"], ["lockup.svg", 600, "email-signature.png"]];
(async () => {
  const b = await chromium.launch();
  for (const [src, w, out] of jobs) {
    const p = await b.newPage({ viewport: { width: w, height: w }, deviceScaleFactor: 1 });
    await p.setContent(`<html><body style="margin:0;background:transparent"><img id="i" src="data:image/svg+xml;base64,${fs.readFileSync(path.join(dir, src)).toString('base64')}" style="width:${w}px;display:block"></body></html>`);
    await p.waitForTimeout(150);
    await (await p.$('#i')).screenshot({ path: path.join(dir, out), omitBackground: true });
    console.log('wrote', out); await p.close();
  }
  await b.close();
})();
