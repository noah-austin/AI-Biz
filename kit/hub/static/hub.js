// Hub helpers: theme-aware Chart.js defaults, and rendering of queued charts.
(function () {
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function compactMoney(v) {
    const a = Math.abs(v), s = v < 0 ? "-" : "";
    if (a >= 1e6) return s + "$" + (a / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
    if (a >= 1e4) return s + "$" + Math.round(a / 1e3) + "K";
    if (a >= 1e3) return s + "$" + (a / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
    return s + "$" + Math.round(a);
  }
  function fullMoney(v) { return (v < 0 ? "-$" : "$") + Math.abs(Math.round(v)).toLocaleString("en-US"); }
  const fmt = {
    money: { tick: compactMoney, tip: fullMoney },
    pct: { tick: v => Math.round(v) + "%", tip: v => v == null ? "—" : v.toFixed(1) + "%" },
    count: { tick: v => Math.round(v).toLocaleString("en-US"), tip: v => Math.round(v).toLocaleString("en-US") },
  };
  function resolveColor(c) { return typeof c === "string" && c.startsWith("--") ? token(c) : c; }

  function build(item) {
    const el = document.getElementById(item.id);
    if (!el || !window.Chart) return;
    const cfg = item.config, f = fmt[cfg.format || "money"];
    const grid = token("--grid"), ink2 = token("--ink-2"), card = token("--card");
    const datasets = cfg.datasets.map(d => {
      const color = resolveColor(d.color);
      const base = { label: d.label, data: d.data, borderColor: color, backgroundColor: color };
      if ((d.type || cfg.type) === "line") {
        return Object.assign(base, { type: "line", borderWidth: 2, pointRadius: d.points === false ? 0 : 4,
          pointHoverRadius: 6, pointBorderColor: card, pointBorderWidth: 2, tension: 0, spanGaps: true,
          borderDash: d.dash ? [6, 4] : [], fill: false });
      }
      return Object.assign(base, { type: "bar", maxBarThickness: 24, borderRadius: { topLeft: 4, topRight: 4 },
        borderSkipped: "start", borderWidth: 0, stack: cfg.stacked ? "s" : undefined });
    });
    new Chart(el, {
      data: { labels: cfg.labels, datasets },
      options: {
        maintainAspectRatio: false, responsive: true, animation: false,
        interaction: { mode: "index", intersect: false },
        layout: { padding: { top: 6 } },
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => " " + ctx.dataset.label + ": " + f.tip(ctx.parsed.y) } },
        },
        scales: {
          x: { stacked: !!cfg.stacked, grid: { display: false }, border: { color: token("--axis") }, ticks: { color: ink2 } },
          y: { stacked: !!cfg.stacked, beginAtZero: true, suggestedMax: cfg.suggestedMax, grid: { color: grid },
               border: { display: false }, ticks: { color: ink2, callback: f.tick, maxTicksLimit: 6 } },
        },
        onClick: cfg.links ? (evt, els) => { if (els.length && cfg.links[els[0].index]) location.href = cfg.links[els[0].index]; } : undefined,
      },
    });
  }
  function start() {
    if (!window.Chart) return setTimeout(start, 50);
    Chart.defaults.font.family = getComputedStyle(document.body).fontFamily;
    (window.hubCharts || []).forEach(build);
  }
  // "Copy" buttons next to drafted messages and posts.
  document.addEventListener("click", async e => {
    const b = e.target.closest("[data-copy-btn]");
    if (!b) return;
    const box = b.closest("article, section").querySelector("[data-copy]");
    if (!box) return;
    const label = b.dataset.label || (b.dataset.label = b.textContent);
    try { await navigator.clipboard.writeText(box.innerText); b.textContent = "Copied"; }
    catch (err) { const r = document.createRange(); r.selectNodeContents(box); const s = getSelection(); s.removeAllRanges(); s.addRange(r); b.textContent = "Selected: copy it"; }
    setTimeout(() => { b.textContent = label; }, 2500);
  });
  document.addEventListener("DOMContentLoaded", () => {
    const tour = document.querySelector("[data-tour]");
    if (tour) {
      try { if (localStorage.getItem("hub-tour-hidden") === "1") tour.hidden = true; } catch (e) {}
      const hide = tour.querySelector("[data-tour-hide]");
      if (hide) hide.addEventListener("click", () => { tour.hidden = true; try { localStorage.setItem("hub-tour-hidden", "1"); } catch (e) {} });
    }
    // Forecast: totals follow the calls as they change.
    const fc = document.querySelector("[data-forecast]");
    if (fc) {
      const fmt = v => v >= 1e6 ? "$" + (v / 1e6).toFixed(1) + "M" : v >= 1e3 ? "$" + Math.round(v / 1e3) + "K" : "$" + Math.round(v);
      const commitEl = document.querySelector('[data-total="commit"]'), bestEl = document.querySelector('[data-total="best"]');
      const booked = parseFloat(commitEl.dataset.booked) || 0;
      const sum = () => {
        let c = 0, b = 0;
        fc.querySelectorAll("tr[data-amount]").forEach(tr => {
          const v = tr.querySelector("[data-call]").value, a = parseFloat(tr.dataset.amount) || 0;
          if (v === "commit") c += a; else if (v === "best") b += a;
          tr.classList.toggle("omitted", v === "omit");
        });
        commitEl.textContent = fmt(booked + c); bestEl.textContent = fmt(booked + c + b);
        const bar = document.querySelector("[data-fbar]"), total = bar ? parseFloat(bar.dataset.total) || 0 : 0;
        if (bar && total) {
          bar.querySelector('[data-seg="commit"]').style.width = (100 * c / total) + "%";
          bar.querySelector('[data-seg="best"]').style.width = (100 * b / total) + "%";
          document.querySelector('[data-leg="commit"]').textContent = fmt(c);
          document.querySelector('[data-leg="best"]').textContent = fmt(b);
        }
      };
      fc.addEventListener("change", e => { if (e.target.matches("[data-call]")) sum(); });
      sum();
    }
    // Wide time tables open on the latest weeks.
    document.querySelectorAll("[data-scroll-end]").forEach(el => { el.scrollLeft = el.scrollWidth; });
    start();
  });
})();
