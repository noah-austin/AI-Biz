// Renders the LinkedIn images. Usage: node website/brand/linkedin/render.js  (needs Playwright + Chromium)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const R = path.join(__dirname, '..', '..', '..'), OUT = path.join(R, 'website/brand/linkedin');
const b64 = f => fs.readFileSync(path.join(R, f)).toString('base64');
const fonts = `@font-face{font-family:PF;src:url(data:font/woff2;base64,${b64('website/static/fonts/playfair-700.woff2')});font-weight:700}
@font-face{font-family:PFI;src:url(data:font/woff2;base64,${b64('website/brand/fonts/playfair-display-latin-400-italic.woff2')})}
@font-face{font-family:IN;src:url(data:font/woff2;base64,${b64('website/static/fonts/inter-latin-var.woff2')});font-weight:100 900}`;
const svg = f => `data:image/svg+xml;base64,${b64('website/static/brand/' + f)}`;
const OX = '#6b1f2a', PA = '#f5efe4', INK = '#2a2622', BR = '#8f6f3e', LBR = '#c9a46a', SOFT = '#e9dcc9';
const base = `*{box-sizing:border-box;margin:0}body{overflow:hidden;position:relative;font-family:IN,sans-serif}
.pf{font-family:PF,serif;font-weight:700}.it{font-family:PFI,serif}.eb{font-family:IN;font-weight:600;letter-spacing:.18em;text-transform:uppercase}`;
const jobs = {
  // Personal banner 1584x396. Profile photo covers the lower left, so content sits right.
  'profile-banner.png': [1584, 396, `<body style="background:${PA};position:relative">
    <img src="${svg('seal.svg')}" style="position:absolute;right:-70px;top:-60px;width:520px;opacity:.07">
    <div style="position:absolute;left:600px;right:90px;top:72px;display:flex;flex-direction:column;gap:18px">
      <div class="eb" style="font-size:17px;color:${BR}">Sanford Operations</div>
      <div class="pf" style="font-size:50px;line-height:1.08;color:${INK}">All your data in one place,<br>and everything it unlocks.</div>
      <div style="font-size:21px;color:#4f4842">Reports that build themselves · Tools · AI and AI agents</div>
      <div style="font-size:21px;font-weight:600;color:${OX}">sanfordoperations.com</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:10px;background:${OX}"></div></body>`],
  // Company page cover, ~6:1 (fits 1512x256, 1128x191 and 4200x700). Logo covers the lower left.
  'company-cover.png': [1512, 256, `<body style="background:${OX};position:relative">
    <img src="${svg('seal-reversed.svg')}" style="position:absolute;right:-40px;top:-90px;width:430px;opacity:.10">
    <div style="position:absolute;left:400px;right:120px;top:0;bottom:0;display:flex;flex-direction:column;justify-content:center;gap:12px">
      <div class="pf" style="font-size:42px;line-height:1.1;color:${PA}">All your data in one place,<br>and everything it unlocks.</div>
      <div style="font-size:19px;color:${SOFT}">Reports, tools, AI and AI agents for small and mid-size companies · sanfordoperations.com</div>
    </div>
    <div style="position:absolute;left:0;right:0;bottom:0;height:6px;background:${LBR}"></div></body>`],
  // Company logo, square. LinkedIn rounds the corners.
  'company-logo.png': [400, 400, `<body style="background:${OX};display:flex;align-items:center;justify-content:center">
    <img src="${svg('seal-reversed.svg')}" style="width:330px"></body>`],
  // Post images, 1200x627
  'post-launch.png': [1200, 627, `<body style="background:${OX};display:flex;align-items:center;gap:70px;padding:0 90px">
    <img src="${svg('seal-reversed.svg')}" style="width:330px;flex:none">
    <div style="display:flex;flex-direction:column;gap:22px">
      <div class="eb" style="font-size:18px;color:${SOFT}">Now open</div>
      <div class="pf" style="font-size:54px;line-height:1.08;color:${PA}">All your data in one place, and everything it unlocks.</div>
      <div style="font-size:24px;color:${SOFT}">sanfordoperations.com</div>
    </div></body>`],
  'post-crm-ai.png': [1200, 627, `<body style="background:${PA};padding:0 90px;display:flex;flex-direction:column;justify-content:center;gap:40px">
    <div class="pf" style="font-size:52px;line-height:1.1;color:${INK}">Your CRM’s AI only sees<br>your CRM.</div>
    <div style="display:flex;gap:22px">
      ${[['CRM', true], ['Accounting', false], ['Projects', false], ['Spreadsheets', false]].map(([t, on]) => `<div style="flex:1;height:150px;border-radius:16px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:10px;${on ? `background:${OX};color:${PA}` : `background:#ece3d3;color:#8a7f74;border:2px dashed #cdbfa8`}">
        <div style="font-size:26px;font-weight:600">${t}</div><div style="font-size:18px">${on ? 'AI can see this' : 'AI can’t see this'}</div></div>`).join('')}
    </div>
    <div style="font-size:24px;color:#4f4842">Real questions cross systems. Put the data in one place first.</div></body>`],
  'post-win-rate.png': [1200, 627, `<body style="background:${PA};padding:0 90px;display:flex;flex-direction:column;justify-content:center;gap:34px">
    <div class="pf" style="font-size:48px;line-height:1.1;color:${INK}">You can win most deals<br>and still lose most of the money.</div>
    <div style="display:flex;gap:28px">
      <div style="flex:1;background:#fbf8f2;border:1px solid #e4dccf;border-radius:16px;padding:28px 32px"><div class="eb" style="font-size:16px;color:${BR}">By count</div><div class="pf" style="font-size:72px;color:${INK}">70%</div><div style="font-size:22px;color:#4f4842">7 of 10 deals won</div></div>
      <div style="flex:1;background:${OX};border-radius:16px;padding:28px 32px"><div class="eb" style="font-size:16px;color:${SOFT}">By dollars</div><div class="pf" style="font-size:72px;color:${PA}">30%</div><div style="font-size:22px;color:${SOFT}">$300K of $1M won</div></div>
    </div>
    <div style="font-size:19px;color:#6e655e">Illustration with made-up numbers · Sanford Operations</div></body>`],
  'post-monday.png': [1200, 627, `<body style="background:${INK};padding:0 110px;display:flex;flex-direction:column;justify-content:center;gap:30px">
    <div class="pf" style="font-size:96px;line-height:.6;color:${LBR}">“</div>
    <div class="pf" style="font-size:50px;line-height:1.15;color:${PA}">If half the Monday meeting is arguing about whose number is right, the problem isn’t the people.</div>
    <div style="display:flex;align-items:center;gap:16px"><img src="${svg('seal-reversed.svg')}" style="width:54px"><div style="font-size:22px;color:${SOFT}">Sanford Operations</div></div></body>`],
};
(async () => {
  const b = await chromium.launch();
  for (const [name, [w, h, body]] of Object.entries(jobs)) {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: name === 'company-logo.png' ? 2 : 2 });
    await p.setContent(`<html><head><style>${fonts}${base}body{width:${w}px;height:${h}px}</style></head>${body}</html>`);
    await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(200);
    await p.screenshot({ path: path.join(OUT, name) }); await p.close(); console.log('wrote', name);
  }
  await b.close();
})();
