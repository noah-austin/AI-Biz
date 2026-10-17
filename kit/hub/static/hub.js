// Hub helpers: theme-aware Chart.js defaults, and rendering of queued charts.
(function () {
  function token(name) { return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }
  function compactMoney(v) {
    const a = Math.abs(v), s = v < 0 ? "-" : "";
    if (a >= 1e6) return s + "$" + (a / 1e6).toFixed(a >= 1e7 ? 0 : 1) + "M";
    if (a >= 1e3) return s + "$" + Math.round(a / 1e3) + "K";
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
  document.addEventListener("DOMContentLoaded", () => {
    // Wide time tables open on the latest weeks.
    document.querySelectorAll("[data-scroll-end]").forEach(el => { el.scrollLeft = el.scrollWidth; });
    start();
  });
})();
