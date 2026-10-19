// node frames3d.js <capture.html> <outdir> fps <fps> <duration>  |  node frames3d.js <file> <outdir> <t1> <t2> ...
const { chromium } = require('playwright');
(async () => {
  const [file, out, mode, ...rest] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto('file://' + file); await p.waitForFunction(() => window.sceneReady === true, null, { timeout: 60000 });
  let times = mode === 'fps' ? Array.from({ length: Math.round(+rest[1] * +rest[0]) }, (_, i) => i / +rest[0]) : [mode, ...rest].map(Number);
  let i = 0;
  if (mode === 'fps' && rest[2] !== undefined) { i = +rest[2]; times = times.slice(+rest[2], +rest[3]); } const t0 = Date.now();
  for (const t of times) { await p.evaluate(t => window.renderAt(t), t); await p.screenshot({ path: `${out}/f${String(i++).padStart(4, '0')}.png` }); }
  console.log('frames', i, 'ms/frame', Math.round((Date.now() - t0) / i), errs.slice(0, 3));
  await b.close();
})();
