// node frames.js <capture.html> <outdir> <fps|times...>
const { chromium } = require('playwright');
(async () => {
  const [file, out, mode, ...rest] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  await p.goto('file://' + file); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(300);
  await p.evaluate(() => document.getAnimations().forEach(a => a.pause()));
  const times = mode === 'fps' ? Array.from({ length: Math.round(24 * +rest[0]) }, (_, i) => i * 1000 / +rest[0]) : [mode, ...rest].map(t => +t * 1000);
  let i = 0;
  for (const t of times) {
    await p.evaluate(ms => document.getAnimations().forEach(a => { a.currentTime = ms; }), t);
    await p.screenshot({ path: `${out}/f${String(i++).padStart(4, '0')}.png` });
  }
  await b.close(); console.log('frames', i);
})();
