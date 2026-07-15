/* ============================================================================
   DemandMind — interactive logic
   • brand-centric KPIs / comparison / spotlight
   • product + barcode search → slide-over with sales-by-period
   • draggable iOS widgets (SortableJS) with localStorage persistence
   ============================================================================ */
/* Surface any uncaught error on-page (no console needed to diagnose). */
window.addEventListener("error", e => {
  let b = document.getElementById("dm-fatal");
  if (!b) { b = document.createElement("div"); b.id = "dm-fatal"; document.body.appendChild(b); }
  b.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;background:#FEF3F2;border:1px solid #F97066;color:#B42318;padding:12px 16px;border-radius:12px;font:13px/1.4 "Segoe UI",-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;box-shadow:0 8px 24px rgba(16,24,40,.14)';
  b.textContent = "⚠ Dashboard error: " + (e.message || e.error) + "  ·  " + String(e.filename || "").split("/").pop() + ":" + (e.lineno || "");
});

if (!window.DM) { throw new Error("data.js did not load (window.DM missing)"); }
const { BRANDS, PRODUCTS, CATEGORIES, MONTHS } = window.DM;

const BRAND = "#3B6EF5", BRAND_SOFT = "#93B0FA", INK3 = "#98A2B3", LINE = "#E7E9EE";
const FONT = { fontFamily: '"Segoe UI", -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif' };
const grid = { borderColor: LINE, strokeDashArray: 4, padding: { left: 6, right: 6 } };
const base = {
  toolbar: { show: false }, zoom: { enabled: false },
  // Built-in animation off (it rises from the baseline). We run a custom
  // left-to-right "draw" entrance instead — see animateChartDraw().
  animations: { enabled: false },
  ...FONT,
};

// Highcharts global defaults — hide the "Highcharts.com" credit on every chart.
// (Prototype only: the free non-commercial licence expects attribution somewhere.)
if (typeof Highcharts !== "undefined") {
  Highcharts.setOptions({ credits: { enabled: false } });
  // Custom entrance (Highcharts line-draw demo): paint line/spline series
  // left-to-right via stroke-dashoffset instead of the default fade/rise.
  (function (H) {
    H.seriesTypes.line.prototype.animate = function (init) {
      const g = this.graph, anim = H.animObject(this.options.animation);
      if (init || !g || !g.element) return;
      const len = g.element.getTotalLength();
      g.attr({ "stroke-dasharray": len, "stroke-dashoffset": len, opacity: 1 });
      g.animate({ "stroke-dashoffset": 0 }, anim);
    };
  }(Highcharts));
}
const gel  = id => document.getElementById(id);
const money = v => "₾" + v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const brandById = id => BRANDS.find(b => b.id === id);
const chainCount = BRANDS.length;
const clamp = (v, min, max) => Math.max(min, Math.min(max, v));
const escapeHtml = s => String(s ?? "").replace(/[&<>"']/g, ch => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));
const searchThumbMarkup = product => product.imageUrl
  ? `<span class="sr-thumb photo"><img src="${escapeHtml(product.imageUrl)}" alt="${escapeHtml(product.name)}" loading="lazy" referrerpolicy="no-referrer"></span>`
  : `<span class="sr-thumb">${catIcon(product.category)}</span>`;
const CATEGORY_AFFINITY = {
  "2nabiji": { Pantry: 1.2, Dairy: 1.12, Bakery: 1.08, Coffee: 0.92, Meat: 0.9, Snacks: 0.94, Beverages: 1.02 },
  magniti:   { Pantry: 1.06, Dairy: 1.08, Bakery: 1.02, Coffee: 1.1, Meat: 0.98, Snacks: 1.05, Beverages: 1.02 },
  spar:      { Pantry: 0.96, Dairy: 1.04, Bakery: 1.0, Coffee: 1.06, Meat: 1.08, Snacks: 0.98, Beverages: 1.04 },
  daily:     { Pantry: 1.0, Dairy: 1.0, Bakery: 0.95, Coffee: 0.95, Meat: 0.95, Snacks: 1.0, Beverages: 1.0 }
};
const BRAND_FORMAT_FACTOR = { "2nabiji": 1.18, magniti: 1.14, spar: 1.01, daily: 1.05 };
// Real Tbilisi store counts (curated store geography) — Daily is a Kutaisi/
// Batumi-founded western-Georgia chain with only a token Tbilisi footprint.
const BRAND_STORE_COUNT = { "2nabiji": 89, magniti: 84, spar: 183, daily: 2 };
const DEMAND_COLORS = { actual: BRAND, forecast: BRAND_SOFT };

// Household-role trait is fixed (price sensitivity / promo lift are properties
// of the shopper, not the chain); only each segment's share of a brand's
// demand shifts — value chains skew to bulk-buying mothers, the premium 24/7
// chain skews to quick solo trips, the regional chain skews to grandparents.
const BASE_SEGMENTS = [
  { name: "Father", color: "#2a6e8f", share: 38, priceSens: "Low", promoLift: 9 },
  { name: "Mother", color: "#8c3a8a", share: 34, priceSens: "High", promoLift: 22 },
  { name: "Child", color: "#0e7a8f", share: 16, priceSens: "Medium", promoLift: 31 },
  { name: "Grandparent", color: "#7a6050", share: 12, priceSens: "High", promoLift: 6 },
];
const SEGMENT_AFFINITY = {
  "2nabiji": { Father: 0.95, Mother: 1.15, Child: 1.1, Grandparent: 0.85 },
  magniti:   { Father: 1.0, Mother: 1.2, Child: 0.9, Grandparent: 0.95 },
  spar:      { Father: 1.25, Mother: 0.85, Child: 1.05, Grandparent: 0.75 },
  daily:     { Father: 0.85, Mother: 1.05, Child: 0.85, Grandparent: 1.35 },
};

// Approximate real Tbilisi district centers, used to scatter demo store pins
// and household counts when no backend (/store-locations, simulation report)
// is reachable — e.g. the static Vercel deployment.
const DISTRICT_CENTERS = {
  Saburtalo: [41.7225, 44.7563], Vake: [41.7167, 44.7500], Didube: [41.7392, 44.7736],
  Gldani: [41.7822, 44.8064], Isani: [41.6892, 44.8467], Samgori: [41.6975, 44.8636],
  Ortachala: [41.6775, 44.8114], Mtatsminda: [41.6941, 44.7925], Nadzaladevi: [41.7364, 44.7961],
  Krtsanisi: [41.6650, 44.8300],
};
const DISTRICT_NAMES = Object.keys(DISTRICT_CENTERS);
const DEMO_HOUSEHOLDS_BY_DISTRICT = [
  ["Gldani", 74], ["Saburtalo", 68], ["Vake", 59], ["Samgori", 44], ["Didube", 47],
  ["Isani", 41], ["Nadzaladevi", 36], ["Mtatsminda", 31], ["Ortachala", 22], ["Krtsanisi", 18],
];
const DEMO_TOTAL_HOUSEHOLDS = DEMO_HOUSEHOLDS_BY_DISTRICT.reduce((s, [, n]) => s + n, 0);

let liveReport = null;
// The dashboard's own notion of "today" — real wall-clock time until the user
// projects forward via the date picker, at which point every "Now" marker
// (header badge, forecast chart) should move to the picked date instead.
// Never anchor this to liveReport's simulation_metadata: that's the real
// backend's last run date and goes stale the moment time passes.
let demoNow = new Date();

/* ── Sidebar navigation / views ───────────────────────────────────────── */
let currentView = "overview";
let forecastTrendChart = null;   // demand heatmap on the Demand Forecast panel
let forecastCatChart = null;     // category bar chart on the Demand Forecast panel
let brandCompareChart = null;    // responsive column chart on the Brands panel
let brandGridInstance = null;    // Highcharts Grid Pro instance on the Brands panel
let heroHC = null;               // Highcharts Stock instance for the hero trend
let storesMapChart = null;       // Highcharts Map (tiledwebmap) instance on the Stores panel
let storeLocationsCache = null;  // cached /store-locations response
let storesSelectedBrand = "all";
let storesSelectedId = null;
// Which nav views each grid widget belongs to (keyed by data-wid).
const WIDGET_VIEWS = {
  "ai": ["overview"],
  "kpi-units": ["overview"], "kpi-basket": ["overview"], "kpi-promos": ["overview"], "kpi-price": ["overview"],
  "forecast": ["overview", "forecast"], "actions": ["overview", "forecast"],
  "category": ["overview", "forecast"], "movers": ["overview", "forecast"],
  "brand-cmp": ["overview", "brands"], "brand-spot": ["overview", "brands"], "price-trend": ["overview", "brands"],
  "segments": ["overview", "segments"], "explain": ["overview", "explain"],
  "products": ["products"], "simulation": ["simulation"], "settings": ["settings"],
};
const VIEW_TITLES = {
  overview:   ["Retail Overview", "Tbilisi · brand-level demand intelligence"],
  forecast:   ["Demand Forecast", "SKU & category demand · trend and actions"],
  brands:     ["Brands", "Chain comparison, spotlight and price index"],
  stores:     ["Stores", "Real store locations · simulated demand by branch"],
  products:   ["Products", "Search SKUs and open barcode-level forecasts"],
  segments:   ["Family Segments", "Household segments driving demand"],
  simulation: ["Simulation", "Run the Tbilisi economy simulation · inspect the last run"],
  explain:    ["Explainability", "Why the model forecasts what it does"],
  settings:   ["Settings", "Data source and workspace preferences"],
};

function setView(view) {
  if (!VIEW_TITLES[view]) view = "overview";
  currentView = view;
  document.querySelectorAll(".dm-nav a[data-view]").forEach(a =>
    a.classList.toggle("active", a.dataset.view === view));
  const isOverview = view === "overview";
  const grid = gel("grid"), brandBar = gel("brandBar"), panels = gel("viewPanels");
  if (grid) grid.style.display = isOverview ? "" : "none";
  if (brandBar) brandBar.style.display = isOverview ? "" : "none";
  if (panels) panels.style.display = isOverview ? "none" : "";
  document.querySelectorAll(".view-panel").forEach(p => { p.hidden = p.id !== `panel-${view}`; });
  const [title, sub] = VIEW_TITLES[view];
  const h1 = document.querySelector(".dm-topbar h1"); if (h1) h1.textContent = title;
  const subEl = document.querySelector(".dm-topbar .sub"); if (subEl) subEl.textContent = sub;
  if (!isOverview) renderCurrentPanel();
  // Only nudge a resize when the (chart-bearing) overview grid becomes visible
  // again — resizing charts while hidden makes them redraw at 0 width.
  else setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
}

function initNav() {
  document.querySelectorAll(".dm-nav a[data-view]").forEach(a =>
    a.addEventListener("click", e => { e.preventDefault(); setView(a.dataset.view); }));
}

function renderCurrentPanel() {
  const R = {
    forecast: renderForecastPanel, brands: renderBrandsPanel, stores: renderStoresPanel,
    products: renderProductsPanel, segments: renderSegmentsPanel, simulation: renderSimulationPanel,
    explain: renderExplainPanel, settings: renderSettingsPanel,
  };
  if (R[currentView]) safe(R[currentView], currentView + "Panel");
}

const _STAT_ICON_PATHS = {
  money: '<path d="M6 6h15l-1.5 9h-12zM6 6L5 3H2M9 20a1 1 0 1 0 0-.01M18 20a1 1 0 1 0 0-.01"/>',
  percent: '<circle cx="12" cy="12" r="9"/><path d="M9 15l6-6M9.4 9.5h.01M14.6 14.5h.01"/>',
  heart: '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 1 0-7.8 7.8l1 1L12 21l7.8-7.8 1-1a5.5 5.5 0 0 0 0-7.8z"/>',
  people: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.2"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/>',
  tag: '<path d="M20.59 13.41 11 3.83A2 2 0 0 0 9.57 3H4a1 1 0 0 0-1 1v5.57a2 2 0 0 0 .83 1.42l9.58 9.59a2 2 0 0 0 2.82 0l4.36-4.36a2 2 0 0 0 0-2.81z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
  chart: '<path d="M3 3v18h18M7 14v4M12 10v8M17 6v12"/>',
};
function _statIconFor(label) {
  const s = String(label).toLowerCase();
  let key = "chart", cls = "blue";
  if (/budget|spend|wealth|ticket|₾/.test(s)) { key = "money"; cls = "green"; }
  else if (/coverage|share|%/.test(s)) { key = "percent"; cls = "blue"; }
  else if (/stress|hunger|health|fun/.test(s)) { key = "heart"; cls = "coral"; }
  else if (/sku|catalog|detailed|unit/.test(s)) { key = "tag"; cls = "amber"; }
  else if (/household|population|chain|visit|store/.test(s)) { key = "people"; cls = "blue"; }
  else if (/window|event|decision|llm/.test(s)) { key = "calendar"; cls = "gray"; }
  return `<span class="ic ${cls}"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${_STAT_ICON_PATHS[key]}</svg></span>`;
}
function _statCards(pairs) {
  return `<div class="sim-stat-grid">${pairs.map(([k, v]) =>
    `<div class="sim-stat"><div class="l">${_statIconFor(k)}<span>${escapeHtml(k)}</span></div><div class="v mono">${escapeHtml(String(v))}</div></div>`).join("")}</div>`;
}
function _barRows(rows, color) {
  const m = Math.max(1, ...rows.map(r => r[1]));
  return rows.map(([label, val]) =>
    `<div class="an-bar"><span class="an-bar-l">${escapeHtml(label)}</span>
      <span class="an-bar-track"><i style="width:${Math.round((val / m) * 100)}%;background:${color || "var(--brand)"}"></i></span>
      <span class="an-bar-v mono">${val}</span></div>`).join("");
}
function _panelEmpty(host, msg) { host.innerHTML = `<div class="pv-meta">${escapeHtml(msg)}</div>`; }

function renderForecastPanel() {
  const host = gel("panel-forecast"); if (!host) return;
  const bd = retailBreakdown();
  const usingDemo = !(bd && bd.sku_breakdown && Object.keys(bd.sku_breakdown).length);
  const demo = usingDemo ? demoSkuBreakdown() : null;
  const sku = usingDemo ? demo.sku : bd.sku_breakdown;
  const meta = usingDemo ? demo.meta : (bd.sku_breakdown_meta || {});
  const cov = meta.catalog_size ? ((meta.distinct_skus_sold / meta.catalog_size) * 100).toFixed(1) : "—";
  const fmtD = iso => { try { return new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }); } catch (_) { return iso; } };
  let windowStr;
  if (usingDemo) {
    const [from, to] = demo.windowStr.split(" – ");
    windowStr = `${fmtD(from)} – ${fmtD(to)}`;
  } else {
    const md = (liveReport && liveReport.simulation_metadata) || {};
    windowStr = (md.start_date && md.end_date) ? `${fmtD(md.start_date)} – ${fmtD(md.end_date)}` : "";
  }
  const catRows = usingDemo ? CATEGORIES.slice(0, 10).map(c => [c.name, c.units]) : (() => {
    const cats = {};
    Object.values(bd.brands || {}).forEach(b => (b.top_categories || []).forEach(c => { cats[c.name] = (cats[c.name] || 0) + c.units; }));
    return Object.entries(cats).sort((a, b) => b[1] - a[1]).slice(0, 10);
  })();
  // The sim's final weekly bucket is often a partial week (started but not
  // finished when the run ended) — its units cover fewer days than a full
  // week, so every SKU reads as a fake demand drop right at the end. Drop it
  // wherever it's < 6 days into the simulation's end_date, once, so the
  // trend arrow and the heatmap below never disagree about it.
  const endStr = usingDemo ? null : ((liveReport && liveReport.simulation_metadata) || {}).end_date;
  const endTs = endStr ? Date.parse(endStr + "T00:00:00Z") : null;
  const fullWeeklyBuckets = buckets => {
    if (!endTs || buckets.length < 2) return buckets;
    const lastTs = Date.parse(buckets[buckets.length - 1].start + "T00:00:00Z");
    return (endTs - lastTs) < 6 * 86400000 ? buckets.slice(0, -1) : buckets;
  };
  const withWeekly = Object.entries(sku)
    .map(([bc, e]) => [bc, { ...e, weekly_buckets: fullWeeklyBuckets(e.weekly_buckets || []) }])
    .filter(([, e]) => e.weekly_buckets && e.weekly_buckets.length)
    .sort((a, b) => b[1].units - a[1].units);
  const skuRows = withWeekly.slice(0, 12).map(([bc, e]) => {
    const wk = e.weekly_buckets.map(w => w.units);
    const last = wk[wk.length - 1] || 0, prev = wk[wk.length - 2] || 0;
    const arrow = last > prev ? '<span class="up">▲</span>' : last < prev ? '<span class="down">▼</span>' : '<span class="flat">━</span>';
    return `<tr><td class="mono">${escapeHtml(bc)}</td><td class="num">${e.units}</td>
      <td class="num">${money(e.spend)}</td><td class="num">${e.visits}</td>
      <td class="mono">${wk.join(" · ")}</td><td class="num">${arrow}</td>
      <td class="num"><a class="a-cta" href="product.html?bc=${encodeURIComponent(bc)}">Open →</a></td></tr>`;
  }).join("");
  host.innerHTML = `
    ${_statCards([["SKUs with demand", meta.distinct_skus_sold || 0], ["Total units", meta.total_sku_units || 0],
                  ["Detailed (top-N)", meta.top_n_detailed || 0], ["Catalog coverage", cov + "%"]])}
    <div class="an-block"><div class="an-h">Weekly demand heatmap <span>top SKUs × week · colour = simulated units</span></div>
      <div id="fc-trend-chart" style="min-height:460px"></div></div>
    <div class="an-block"><div class="an-h">Demand by category <span>units · top 10${windowStr ? " · " + windowStr : ""}</span></div>
      <div id="fc-cat-chart" style="min-height:360px"></div></div>
    <div class="an-block"><div class="an-h">Top SKUs · observed series &amp; trend</div>
      <table class="dm-table"><thead><tr><th>Barcode</th><th class="num">Units</th><th class="num">Spend ₾</th><th class="num">Visits</th><th>Weekly units</th><th class="num">Trend</th><th></th></tr></thead>
      <tbody>${skuRows}</tbody></table></div>`;
  const rows = withWeekly.slice(0, 15);
  if (rows.length && typeof Highcharts !== "undefined") {
    const weekSet = new Set();
    rows.forEach(([, e]) => e.weekly_buckets.forEach(w => weekSet.add(w.start)));
    const weeks = [...weekSet].sort(); // partial final week already dropped in withWeekly above
    const fmt = iso => { try { return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "short" }); } catch (_) { return iso; } };
    const yCats = rows.map(([bc]) => "SKU " + String(bc).slice(-6));
    const data = [];
    rows.forEach(([, e], yi) => {
      const m = {}; e.weekly_buckets.forEach(w => { m[w.start] = w.units; });
      weeks.forEach((wk, xi) => data.push([xi, yi, m[wk] || 0]));
    });
    forecastTrendChart = destroyChart(forecastTrendChart);
    forecastTrendChart = Highcharts.chart("fc-trend-chart", {
      chart: { type: "heatmap", height: 460, backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily }, marginTop: 10 },
      accessibility: { enabled: false },
      title: { text: null },
      xAxis: { categories: weeks.map(fmt), lineColor: LINE, labels: { style: { color: INK3 } } },
      yAxis: { categories: yCats, title: null, reversed: true, labels: { style: { color: INK3, fontSize: "11px" } } },
      colorAxis: { min: 0, stops: [[0, "#EEF4FF"], [0.5, "#7BA0FF"], [1, "#1D4ED8"]], labels: { style: { color: INK3 } } },
      legend: { align: "right", layout: "vertical", verticalAlign: "middle", symbolHeight: 240, itemStyle: { color: "#667085" } },
      tooltip: { formatter() {
        const yc = this.series.yAxis.categories, xc = this.series.xAxis.categories;
        return "<b>" + yc[this.point.y] + "</b><br>" + xc[this.point.x] + ": <b>" + this.point.value + " units</b>";
      } },
      plotOptions: { heatmap: { borderWidth: 3, borderColor: "#ffffff" } },
      series: [{ name: "Weekly units", data, dataLabels: { enabled: true, color: "#1f2937", style: { fontSize: "10px", fontWeight: "500", textOutline: "none" } } }],
    });
  } else {
    forecastTrendChart = destroyChart(forecastTrendChart);
  }

  // Demand by category — Highcharts horizontal bar
  if (catRows.length && typeof Highcharts !== "undefined") {
    const CATPAL = ["#3B6EF5", "#12B76A", "#F5A524", "#F97066", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16", "#14B8A6", "#F43F5E"];
    forecastCatChart = destroyChart(forecastCatChart);
    forecastCatChart = Highcharts.chart("fc-cat-chart", {
      chart: { type: "bar", height: 360, backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
      accessibility: { enabled: false },
      title: { text: null },
      subtitle: { text: windowStr ? "Simulated demand · " + windowStr : null, align: "left", style: { color: INK3, fontSize: "12px" } },
      xAxis: { categories: catRows.map(c => c[0]), lineColor: LINE, labels: { style: { color: INK3 } } },
      yAxis: { min: 0, title: { text: "Units", align: "high", style: { color: INK3 } }, gridLineColor: LINE, labels: { style: { color: INK3 } } },
      legend: { enabled: false },
      tooltip: { headerFormat: "<span style=\"font-weight:600\">{point.key}</span><br>", pointFormat: "<b>{point.y} units</b>" },
      colors: CATPAL,
      plotOptions: { bar: { borderRadius: 4, borderWidth: 0, colorByPoint: true,
        dataLabels: { enabled: true, format: "{y}", style: { color: "#667085", fontWeight: "600", textOutline: "none" } } } },
      series: [{ name: "Units", data: catRows.map(c => c[1]) }],
    });
  } else {
    forecastCatChart = destroyChart(forecastCatChart);
  }
}

function syntheticBrandRows() {
  const ITEMS_PER_VISIT = 8;
  const rows = BRANDS.map(b => {
    const units = scopedProducts(b).reduce((s, p) => s + p.scopedUnits, 0);
    const avgTicket = brandBasket(b);
    const visits = Math.max(1, Math.round(units / ITEMS_PER_VISIT));
    return {
      brand_id: b.id,
      brand_name: b.name,
      units,
      visits,
      avg_ticket: avgTicket,
      spend: +(avgTicket * visits).toFixed(2),
      store_count: BRAND_STORE_COUNT[b.id] || 0,
      top_categories: scopedCategories(b).slice(0, 3),
    };
  });
  const totalSpend = rows.reduce((s, r) => s + r.spend, 0) || 1;
  rows.forEach(r => { r.share_of_spend = +((r.spend / totalSpend) * 100).toFixed(1); });
  return rows;
}

// Demo-only SKU/week grid for the Demand Forecast & Products tabs, shaped
// exactly like the backend's real sku_breakdown so the same render code
// (heatmap, category chart, tables) works whether the data is real or demo.
function demoSkuBreakdown() {
  const WEEKS = 12;
  const weekStarts = Array.from({ length: WEEKS }, (_, i) => {
    const d = new Date(demoNow); d.setDate(d.getDate() - (WEEKS - 1 - i) * 7);
    return d.toISOString().slice(0, 10);
  });
  const sku = {};
  PRODUCTS.forEach(p => {
    const weekly = p.sales.weekly.slice(-WEEKS);
    while (weekly.length < WEEKS) weekly.unshift(weekly[0] || 0);
    sku[p.barcode] = {
      units: p.totalUnits,
      spend: +(p.totalUnits * p.avgPrice).toFixed(2),
      visits: Math.max(1, Math.round(p.totalUnits / 8)),
      weekly_buckets: weekly.map((units, i) => ({ start: weekStarts[i], units })),
    };
  });
  return {
    sku,
    windowStr: `${weekStarts[0]} – ${weekStarts[WEEKS - 1]}`,
    meta: {
      distinct_skus_sold: PRODUCTS.length,
      total_sku_units: PRODUCTS.reduce((s, p) => s + p.totalUnits, 0),
      top_n_detailed: PRODUCTS.length,
      catalog_size: PRODUCTS.length,
    },
  };
}

// Demo-only store universe for the Stores tab, shaped like the backend's
// real /store-locations response — real Tbilisi store counts (BRAND_STORE_COUNT)
// scattered around real district centers, with demand split proportional to
// each brand's synthetic totals.
function demoStoreLocations() {
  const brandRows = syntheticBrandRows();
  const stores = [];
  let idx = 0;
  BRANDS.forEach(b => {
    const count = BRAND_STORE_COUNT[b.id] || 10;
    const synthetic = brandRows.find(r => r.brand_id === b.id);
    const totalSpend = synthetic ? synthetic.spend : 0;
    const totalUnits = synthetic ? synthetic.units : 0;
    const totalVisits = synthetic ? synthetic.visits : 0;
    const shareEach = 1 / count;
    for (let i = 0; i < count; i += 1) {
      const district = DISTRICT_NAMES[idx % DISTRICT_NAMES.length];
      const [lat0, lng0] = DISTRICT_CENTERS[district];
      const hasDemand = Math.random() < 0.65;
      const noise = 0.5 + Math.random();
      stores.push({
        id: `${b.id}-store-${i + 1}`,
        name: `${b.name} ${district} #${String(i + 1).padStart(2, "0")}`,
        chain: b.name,
        brand_id: b.id,
        lat: lat0 + (Math.random() - 0.5) * 0.018,
        lng: lng0 + (Math.random() - 0.5) * 0.018,
        district,
        address: `${district}, Tbilisi`,
        color: b.color,
        spend: hasDemand ? +(totalSpend * shareEach * noise).toFixed(2) : 0,
        units: hasDemand ? Math.round(totalUnits * shareEach * noise) : 0,
        visits: hasDemand ? Math.round(totalVisits * shareEach * noise) : 0,
        avg_ticket: hasDemand && synthetic ? synthetic.avg_ticket : 0,
        has_demand: hasDemand,
      });
      idx += 1;
    }
  });
  return {
    stores,
    meta: { total_stores: stores.length, stores_with_demand: stores.filter(s => s.has_demand).length },
  };
}

function renderBrandsPanel() {
  const host = gel("panel-brands"); if (!host) return;
  const rows = syntheticBrandRows().sort((a, b) => b.spend - a.spend);
  const totalUnits = rows.reduce((s, b) => s + (b.units || 0), 0);
  const totalSpend = rows.reduce((s, b) => s + (b.spend || 0), 0);
  const totalVisits = rows.reduce((s, b) => s + (b.visits || 0), 0);
  host.innerHTML = `
    ${_statCards([["Active chains", rows.length], ["Total spend ₾", money(totalSpend)],
                  ["Total units", totalUnits], ["Total visits", totalVisits]])}
    <div class="an-block"><div class="an-h">Brand comparison by category <span>units · resize the panel to see it adapt</span></div>
      <div id="fc-brand-compare" style="min-height:420px"></div></div>
    <div class="an-block"><div class="an-h">Chain breakdown <span>derived columns from demo data</span></div>
      <div id="fc-brand-grid" class="highcharts-light"></div></div>`;
  renderBrandCompareChart(rows);
  renderBrandDataGrid(rows);
}

// Adapted from the official Highcharts "Formulas" Grid demo
// (highcharts.com/demo/grid/formulas) — sortable, formatted data grid with
// derived columns (units/visit, share vs. average). Uses Grid LITE, not Grid
// Pro: Pro requires a gridKey licence and rendered blank without one; Lite is
// the free, ungated tier (no formula engine / sparkline cells, so the two
// derived columns are pre-computed in JS instead of via a live Math modifier,
// and the deviation column uses a coloured ▲/▼ formatter instead of a
// sparkline bar — same information, drawn with what the free tier offers).
function renderBrandDataGrid(rows) {
  if (brandGridInstance) { try { brandGridInstance.destroy(); } catch (_) {} brandGridInstance = null; }
  if (typeof Grid === "undefined") { console.error("[Datasight] Grid Lite not loaded"); return; }
  const avgShare = rows.reduce((s, b) => s + (b.share_of_spend || 0), 0) / (rows.length || 1);
  const dataSource = {
    brand: rows.map(b => b.brand_name || b.brand_id),
    share: rows.map(b => b.share_of_spend ?? 0),
    spend: rows.map(b => Math.round((b.spend || 0) * 100) / 100),
    units: rows.map(b => b.units || 0),
    visits: rows.map(b => b.visits || 0),
    avgTicket: rows.map(b => Math.round((b.avg_ticket || 0) * 100) / 100),
    stores: rows.map(b => b.store_count || 0),
    unitsPerVisit: rows.map(b => b.visits ? Math.round((b.units / b.visits) * 10) / 10 : 0),
    shareVsAvg: rows.map(b => Math.round(((b.share_of_spend || 0) - avgShare) * 10) / 10),
    topCategory: rows.map(b => (b.top_categories && b.top_categories[0] && b.top_categories[0].name) || "—"),
  };
  try {
    brandGridInstance = Grid.grid("fc-brand-grid", {
      dataTable: { columns: dataSource },
      credits: { enabled: false },
      caption: { text: "🏬 Chain performance — live simulation" },
      header: ["brand", "share", "spend", "units", "visits", "avgTicket", "stores", "unitsPerVisit", "shareVsAvg", "topCategory"],
      columns: [
        { id: "brand", header: { format: "Brand" } },
        { id: "share", header: { format: "Share" }, cells: { format: "{value:.1f}%" } },
        { id: "spend", header: { format: "Spend" }, cells: { format: "₾{value:.2f}" } },
        { id: "units", header: { format: "Units" } },
        { id: "visits", header: { format: "Visits" } },
        { id: "avgTicket", header: { format: "Avg ticket" }, cells: { format: "₾{value:.2f}" } },
        { id: "stores", header: { format: "Stores" } },
        { id: "unitsPerVisit", header: { format: "Units / visit" }, cells: { format: "{value:.1f}" } },
        { id: "shareVsAvg", header: { format: "Share vs. avg" }, cells: { useHTML: true, formatter() {
          const v = this.value; const cls = v > 0 ? "up" : v < 0 ? "down" : "flat";
          const arrow = v > 0 ? "▲" : v < 0 ? "▼" : "━";
          return `<span class="${cls}">${arrow} ${Math.abs(v).toFixed(1)}pp</span>`;
        } } },
        { id: "topCategory", header: { format: "Top category" } },
      ],
    });
  } catch (e) {
    console.error("[Datasight] renderBrandDataGrid", e);
    const el = gel("fc-brand-grid");
    if (el) el.innerHTML = `<div class="pv-meta">Grid failed to render: ${escapeHtml(e.message || String(e))}</div>`;
  }
}

// Adapted from the official Highcharts "Responsive" demo
// (highcharts.com/demo/highcharts/responsive) — same chart config (column
// chart, vertical right-side legend that collapses to horizontal-bottom and
// hides the subtitle below 500px via `responsive.rules`); `series`/`xAxis`
// are data-driven from our brand × category demand instead of the demo's
// name-by-year data.
function renderBrandCompareChart(rows) {
  brandCompareChart = destroyChart(brandCompareChart);
  if (typeof Highcharts === "undefined") return;
  const catTotals = {};
  rows.forEach(b => (b.top_categories || []).forEach(c => { catTotals[c.name] = (catTotals[c.name] || 0) + c.units; }));
  const categories = Object.entries(catTotals).sort((a, b) => b[1] - a[1]).slice(0, 6).map(c => c[0]);
  const topBrands = rows.slice(0, 5);
  const series = topBrands.map(b => {
    const byCat = {}; (b.top_categories || []).forEach(c => { byCat[c.name] = c.units; });
    return { name: b.brand_name || b.brand_id, data: categories.map(cat => byCat[cat] || 0) };
  });
  brandCompareChart = Highcharts.chart("fc-brand-compare", {
    chart: { type: "column", backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
    accessibility: { enabled: false },
    title: { text: null },
    subtitle: { text: "Units sold per top category, by chain", style: { color: INK3 } },
    legend: { align: "right", verticalAlign: "middle", layout: "vertical", itemStyle: { color: "#667085", fontWeight: "600" } },
    xAxis: { categories, labels: { x: -10, style: { color: INK3 } }, lineColor: LINE },
    yAxis: { allowDecimals: false, title: { text: "Units", style: { color: INK3 } }, gridLineColor: LINE, labels: { style: { color: INK3 } } },
    tooltip: { shared: true },
    series,
    responsive: { rules: [{
      condition: { maxWidth: 500 },
      chartOptions: {
        legend: { align: "center", verticalAlign: "bottom", layout: "horizontal" },
        yAxis: { labels: { align: "left", x: 0, y: -5 }, title: { text: null } },
        subtitle: { text: null },
      },
    }] },
  });
}

// Adapted from the official Highcharts Dashboards "Live weather" demo
// (highcharts.com/demo/dashboards/live-weather): a map with clickable location
// markers synced to a detail panel. We don't adopt the full Dashboards.board
// layout engine (this app is hand-built panels, not Dashboards components) —
// instead a single Highcharts mapChart with a real OpenStreetMap tiledwebmap
// base layer (Tbilisi has no useful topojson boundary data at street level),
// plus a plain detail card + table wired by hand, same spirit at our scale.
function loadStoreLocations() {
  if (storeLocationsCache) return Promise.resolve(storeLocationsCache);
  return fetch(`/store-locations?t=${Date.now()}`, { cache: "no-store" })
    .then(r => { if (!r.ok) throw new Error("unavailable"); return r.json(); })
    .then(data => { storeLocationsCache = data; return data; })
    .catch(() => { storeLocationsCache = demoStoreLocations(); return storeLocationsCache; });
}

function renderStoresPanel() {
  const host = gel("panel-stores"); if (!host) return;
  if (storeLocationsCache) { renderStoresBody(host, storeLocationsCache); return; }
  host.innerHTML = '<div class="pv-meta">Loading store locations…</div>';
  loadStoreLocations().then(data => renderStoresBody(host, data));
}

function renderStoresBody(host, data) {
  const allStores = data.stores || [];
  if (!allStores.length) return _panelEmpty(host, "No store location data available.");
  const brandIds = [...new Set(allStores.map(s => s.brand_id).filter(Boolean))];
  const chips = ["all", ...brandIds].map(id => {
    const meta = BRANDS.find(b => b.id === id);
    const label = id === "all" ? "All chains" : (meta ? meta.name : id);
    return `<button type="button" class="store-chip${id === storesSelectedBrand ? " active" : ""}" data-brand="${id}">${escapeHtml(label)}</button>`;
  }).join("");

  host.innerHTML = `
    ${_statCards([["Total stores", data.meta.total_stores], ["Stores with demand", data.meta.stores_with_demand],
                  ["Chains mapped", brandIds.length], ["Coverage", data.meta.total_stores ? ((data.meta.stores_with_demand / data.meta.total_stores) * 100).toFixed(1) + "%" : "—"]])}
    <div class="an-block">
      <div class="an-h">Store map <span>real locations · marker size = simulated units</span></div>
      <div class="store-chip-row" id="storeChipRow">${chips}</div>
      <div class="stores-layout">
        <div id="stores-map" style="height:460px"></div>
        <div class="store-detail-card" id="storeDetailCard">
          <div class="pv-meta">Click a store marker to see its detail.</div>
        </div>
      </div>
    </div>
    <div class="an-block"><div class="an-h">Stores with simulated demand <span>filtered by chain · sorted by spend</span></div>
      <div id="storesTableWrap"></div></div>`;

  host.querySelectorAll(".store-chip").forEach(btn => {
    btn.onclick = () => { storesSelectedBrand = btn.dataset.brand; renderStoresBody(host, data); };
  });

  renderStoresTable(allStores);
  renderStoresMap(allStores);
}

function renderStoresTable(allStores) {
  const wrap = gel("storesTableWrap"); if (!wrap) return;
  const filtered = allStores.filter(s => s.has_demand && (storesSelectedBrand === "all" || s.brand_id === storesSelectedBrand))
    .sort((a, b) => b.spend - a.spend);
  if (!filtered.length) { wrap.innerHTML = '<div class="pv-meta">No simulated visits for this chain yet.</div>'; return; }
  wrap.innerHTML = `<table class="dm-table"><thead><tr><th>Store</th><th>District</th><th class="num">Spend ₾</th><th class="num">Units</th><th class="num">Visits</th><th class="num">Avg ticket</th></tr></thead>
    <tbody>${filtered.map(s => `<tr class="store-row${s.id === storesSelectedId ? " active-row" : ""}" data-id="${s.id}">
      <td>${escapeHtml(s.name)}</td><td>${escapeHtml(s.district || "—")}</td>
      <td class="num">${money(s.spend)}</td><td class="num">${s.units}</td><td class="num">${s.visits}</td><td class="num">${money(s.avg_ticket)}</td></tr>`).join("")}</tbody></table>`;
  wrap.querySelectorAll(".store-row").forEach(tr => {
    tr.onclick = () => {
      const store = allStores.find(s => s.id === tr.dataset.id);
      if (store) selectStore(store);
    };
  });
}

function selectStore(store) {
  storesSelectedId = store.id;
  const card = gel("storeDetailCard");
  if (card) {
    card.innerHTML = `
      <div class="sd-name">${escapeHtml(store.name)}</div>
      <div class="sd-meta">${escapeHtml(store.chain || "")} · ${escapeHtml(store.district || "—")}</div>
      <div class="sd-addr">${escapeHtml(store.address || "")}</div>
      ${store.has_demand ? _statCards([
        ["Spend ₾", money(store.spend)], ["Units", store.units],
        ["Visits", store.visits], ["Avg ticket ₾", money(store.avg_ticket)],
      ]) : '<div class="pv-meta" style="margin-top:10px">No simulated visits at this store yet.</div>'}`;
  }
  document.querySelectorAll(".store-row").forEach(tr => tr.classList.toggle("active-row", tr.dataset.id === store.id));
  if (storesMapChart) {
    const point = storesMapChart.series[1].points.find(p => p.id === store.id);
    if (point) point.select(true, false);
  }
}

function renderStoresMap(allStores) {
  storesMapChart = destroyChart(storesMapChart);
  const el = gel("stores-map");
  if (!el || typeof Highcharts === "undefined" || typeof Highcharts.mapChart !== "function") return;
  const filtered = storesSelectedBrand === "all" ? allStores : allStores.filter(s => s.brand_id === storesSelectedBrand);
  const withDemand = filtered.filter(s => s.has_demand && s.lat && s.lng);
  const withoutDemand = filtered.filter(s => !s.has_demand && s.lat && s.lng);
  const maxUnits = Math.max(1, ...withDemand.map(s => s.units));
  const avgLat = filtered.reduce((s, x) => s + (x.lat || 0), 0) / (filtered.length || 1);
  const avgLng = filtered.reduce((s, x) => s + (x.lng || 0), 0) / (filtered.length || 1);

  storesMapChart = Highcharts.mapChart(el, {
    chart: { backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
    accessibility: { enabled: false },
    title: { text: null },
    credits: { enabled: false },
    mapNavigation: { enabled: true, enableMouseWheelZoom: true, buttonOptions: { verticalAlign: "bottom" } },
    mapView: { projection: { name: "WebMercator" }, center: [avgLng || 44.79, avgLat || 41.71], zoom: 11 },
    legend: { enabled: false },
    tooltip: { pointFormatter() {
      return "<b>" + this.name + "</b>" + (this.custom && this.custom.hasDemand
        ? "<br>" + this.custom.units + " units · ₾" + this.custom.spend.toFixed(0)
        : "<br><span style=\"color:#98A2B3\">no simulated visits</span>");
    } },
    series: [
      { type: "tiledwebmap", provider: { type: "OpenStreetMap" }, showInLegend: false },
      {
        type: "mappoint", name: "Stores", showInLegend: false,
        data: withoutDemand.map(s => ({ id: s.id, name: s.name, lat: s.lat, lon: s.lng,
          marker: { radius: 3, fillColor: "rgba(152,162,179,0.55)", lineWidth: 0 },
          custom: { hasDemand: false } })).concat(
          withDemand.map(s => ({ id: s.id, name: s.name, lat: s.lat, lon: s.lng,
            marker: { radius: Math.round(5 + Math.sqrt(s.units / maxUnits) * 16),
              fillColor: s.color || BRAND, lineWidth: 1, lineColor: "#fff" },
            custom: { hasDemand: true, units: s.units, spend: s.spend } }))
        ),
        allowPointSelect: true,
        point: { events: { click: function () { const s = filtered.find(x => x.id === this.id); if (s) selectStore(s); } } },
        states: { select: { marker: { lineWidth: 2, lineColor: "#101828" } } },
      },
    ],
  });
}

function renderProductsPanel() {
  const host = gel("panel-products"); if (!host) return;
  const bd = retailBreakdown();
  const usingDemo = !(bd && bd.sku_breakdown && Object.keys(bd.sku_breakdown).length);
  const demo = usingDemo ? demoSkuBreakdown() : null;
  const sku = usingDemo ? demo.sku : bd.sku_breakdown;
  const meta = usingDemo ? demo.meta : (bd.sku_breakdown_meta || {});
  const cov = meta.catalog_size ? ((meta.distinct_skus_sold / meta.catalog_size) * 100).toFixed(1) : "—";
  const rows = Object.entries(sku).sort((a, b) => b[1].units - a[1].units).slice(0, 30);
  const tr = rows.map(([bc, e]) => {
    const avg = e.units ? (e.spend / e.units) : 0;
    return `<tr><td class="mono">${escapeHtml(bc)}</td><td class="num">${e.units}</td><td class="num">${money(e.spend)}</td>
      <td class="num">${e.visits}</td><td class="num">${money(avg)}</td>
      <td class="num"><a class="a-cta" href="product.html?bc=${encodeURIComponent(bc)}">Open →</a></td></tr>`;
  }).join("");
  host.innerHTML = `
    ${_statCards([["SKUs sold", meta.distinct_skus_sold || 0], ["Catalog", meta.catalog_size || "—"],
                  ["Coverage", cov + "%"], ["Units", meta.total_sku_units || 0]])}
    <div class="an-block"><div class="an-h">Top 30 SKUs by simulated demand</div>
      <table class="dm-table"><thead><tr><th>Barcode</th><th class="num">Units</th><th class="num">Spend ₾</th><th class="num">Visits</th><th class="num">Avg price</th><th></th></tr></thead>
      <tbody>${tr}</tbody></table></div>`;
}

function renderSegmentsPanel() {
  const host = gel("panel-segments"); if (!host) return;
  const usingDemo = !liveReport;
  const geo = usingDemo ? {} : ((liveReport.geographic_distribution || {}).districts || {});
  const soc = usingDemo ? {} : (liveReport.social_dynamics || {});
  const well = usingDemo ? {} : (liveReport.agent_wellbeing || {});
  const econ = usingDemo ? {} : (liveReport.economic_summary || {});
  const distRows = usingDemo ? DEMO_HOUSEHOLDS_BY_DISTRICT.slice() : Object.entries(geo).sort((a, b) => b[1] - a[1]);
  const tierRows = usingDemo
    ? [["In crisis (<₾500)", 29], ["Stable", 321], ["Comfortable (≥₾2k)", 90]]
    : [["In crisis (<₾500)", soc.households_in_crisis || 0], ["Stable", soc.households_stable || 0], ["Comfortable (≥₾2k)", soc.households_comfortable || 0]];
  if (usingDemo) {
    well.avg_stress = 5.8; well.avg_health = 89; well.critical_hunger_count = 9;
    well.avg_hunger = 38; well.avg_fun = 71; well.high_stress_count = 27;
    econ.final_avg_budget = 2380; econ.total_population_wealth = 2380 * DEMO_TOTAL_HOUSEHOLDS * 2.5;
  }
  host.innerHTML = `
    ${_statCards([["Avg budget", money(econ.final_avg_budget || 0)], ["Avg stress", well.avg_stress ?? "—"],
                  ["Avg health", well.avg_health ?? "—"], ["Critical hunger", well.critical_hunger_count ?? "—"]])}
    <div class="an-block"><div class="an-h">Households by district</div>${distRows.length ? _barRows(distRows, "#2a6e8f") : "—"}</div>
    <div class="an-block"><div class="an-h">Financial tiers</div>${_barRows(tierRows, "var(--green)")}</div>
    <div class="an-block"><div class="an-h">Wellbeing &amp; wealth</div>
      ${_statCards([["Avg hunger", well.avg_hunger ?? "—"], ["Avg fun", well.avg_fun ?? "—"],
                    ["High stress", well.high_stress_count ?? "—"], ["Total wealth ₾", money(econ.total_population_wealth || 0)]])}</div>`;
}

function renderSimulationPanel() {
  const host = gel("panel-simulation"); if (!host) return;
  const m = (liveReport && liveReport.simulation_metadata) || {};
  const econ = (liveReport && liveReport.economic_summary) || {};
  const well = (liveReport && liveReport.agent_wellbeing) || {};
  const llm = (liveReport && liveReport.llm_system) || {};
  const ev = (liveReport && liveReport.events_occurred) || {};
  const bd = retailBreakdown(); const meta = (bd && bd.sku_breakdown_meta) || {};
  const evRows = Object.entries(ev.by_type || {}).sort((a, b) => b[1] - a[1]).slice(0, 8);
  host.innerHTML = `
    <div class="sim-run-row">
      <button class="btn-cta" id="simViewRunBtn"><svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M6 4l14 8-14 8z"/></svg>Run Simulation</button>
      <span class="set-sub">LLM: ${escapeHtml(llm.type || "—")} · ${escapeHtml(String(llm.status || ""))}</span>
    </div>
    ${_statCards([["Window", (m.start_date && m.end_date) ? `${m.start_date} → ${m.end_date}` : (m.duration || "—")],
                  ["Households (sample)", m.total_households ?? "—"], ["Population (sample)", m.total_population ?? "—"],
                  ["Avg budget", money(econ.final_avg_budget || 0)], ["Avg stress", well.avg_stress ?? "—"],
                  ["Avg health", well.avg_health ?? "—"], ["SKUs sold", meta.distinct_skus_sold ?? "—"],
                  ["SKU units (scaled)", meta.total_sku_units ?? "—"], ["LLM decisions", llm.agents_with_reasoning ?? "—"],
                  ["Total events", ev.total_events ?? "—"]])}
    ${m.target_population ? `<div class="an-block"><div class="an-h">Market-size extrapolation <span>Path B · sample scaled to city-scale</span></div>
      ${_statCards([["Target population", m.target_population.toLocaleString("en-US")], ["Scaling factor", "×" + m.scaling_factor],
                    ["Sample households", m.sample_households ?? m.total_households ?? "—"], ["Sample population", m.sample_population ?? m.total_population ?? "—"]])}
      <div class="pv-meta" style="margin-top:10px">Retail/brand/store/SKU counts (units, spend, visits, headcounts) are the real sample extrapolated by this factor. Averages, prices and ratios (avg budget, avg ticket, share of spend, stress) are population-size-invariant and are <b>not</b> scaled.</div></div>` : ""}
    ${evRows.length ? `<div class="an-block"><div class="an-h">Events by type</div>${_barRows(evRows, "var(--amber)")}</div>` : ""}`;
  const btn = gel("simViewRunBtn");
  if (btn) btn.onclick = e => { e.preventDefault(); openSimDatePicker(); };
}

function renderExplainPanel() {
  const host = gel("panel-explain"); if (!host) return;
  const bd = retailBreakdown();
  const meta = (bd && bd.sku_breakdown_meta) || {};
  const m = (liveReport && liveReport.simulation_metadata) || {};
  const sku = (bd && bd.sku_breakdown) || {};
  const topBc = Object.entries(sku).filter(([, e]) => e.weekly_buckets).sort((a, b) => b[1].units - a[1].units)[0];
  const cov = meta.catalog_size ? ((meta.distinct_skus_sold / meta.catalog_size) * 100).toFixed(1) : "—";
  const steps = [
    ["Simulation", `${m.total_households ?? "—"} households shop over ${m.start_date || "—"} → ${m.end_date || "—"}, generating barcode-level purchases.`],
    ["Aggregation", `${meta.distinct_skus_sold || 0} SKUs (${cov}% of ${meta.catalog_size || "—"}) recorded ${meta.total_sku_units || 0} units; zero-demand SKUs are excluded.`],
    ["Observed series", `The top-${meta.top_n_detailed || 0} SKUs carry real weekly demand buckets used as the chart's observed baseline.`],
    ["Forecast", `Taalas forecasts each SKU on its own real weekly series, not a category heuristic.`],
  ];
  const sampleHtml = topBc ? `<div class="an-block"><div class="an-h">Sample · ${escapeHtml(topBc[0])}</div>
    <div class="pv-meta">Observed weekly units: <b>${(topBc[1].weekly_buckets || []).map(w => w.units).join(" · ")}</b> · total ${topBc[1].units} units across ${topBc[1].visits} visits</div></div>` : "";
  host.innerHTML = `
    <div class="explain-steps">${steps.map((s, i) => `<div class="explain-step"><span class="es-n">${i + 1}</span><div><div class="es-t">${escapeHtml(s[0])}</div><div class="es-d">${s[1]}</div></div></div>`).join("")}</div>
    ${sampleHtml}`;
}

function renderSettingsPanel() {
  const host = gel("panel-settings"); if (!host) return;
  const m = (liveReport && liveReport.simulation_metadata) || {};
  const bd = retailBreakdown(); const meta = (bd && bd.sku_breakdown_meta) || {};
  host.innerHTML = `
    <div class="set-row"><div><div class="set-k">Data source</div><div class="set-sub">simulation_report.json · live</div></div><button class="a-cta" id="setReload">Reload</button></div>
    <div class="set-row"><div><div class="set-k">Last run</div><div class="set-sub">${escapeHtml(m.simulation_date || m.duration || "—")}</div></div></div>
    <div class="set-row"><div><div class="set-k">Catalog tracked</div><div class="set-sub">${meta.catalog_size || "—"} barcodes · ${meta.distinct_skus_sold || 0} sold</div></div></div>
    <div class="set-row"><div><div class="set-k">Theme</div><div class="set-sub">Light · premium</div></div></div>`;
  const r = gel("setReload");
  if (r) r.onclick = e => { e.preventDefault(); loadSimulationReport({ interactive: true }); };
}
let activeHeroTab = "trend";
let priceChart = null;
let categoryChart = null;
let selectedBrand = "all";
let simulationPollTimer = null;
let simulationJobId = 0;

function currentBrand() {
  return selectedBrand === "all" ? null : brandById(selectedBrand);
}

function activeBrandLabel() {
  const brand = currentBrand();
  return brand ? brand.name : "All chains";
}

function retailBreakdown() {
  return liveReport && liveReport.retail_breakdown ? liveReport.retail_breakdown : null;
}

function liveBrandMetrics(_brand) {
  // Brand-level numbers are demo-authored (see BRANDS in data.js), not sourced
  // from the live simulation run — the sim's per-brand split doesn't reflect
  // real market share for these chains, so it's intentionally never consulted.
  return null;
}

function liveTopProducts(brand) {
  const metrics = liveBrandMetrics(brand);
  return metrics && metrics.top_products ? metrics.top_products : [];
}

function liveTopCategories(brand) {
  const metrics = liveBrandMetrics(brand);
  return metrics && metrics.top_categories ? metrics.top_categories : [];
}

function brandRawDemandScore(product, brand) {
  const shareBase = brand.share / 100;
  const cheapestBoost = product.cheapestBrand === brand.id ? 1.14 : 0.93;
  const heroBoost = product.topBrand === brand.id ? 1.22 : 0.91;
  const affinity = (CATEGORY_AFFINITY[brand.id] && CATEGORY_AFFINITY[brand.id][product.category]) || 1;
  const format = BRAND_FORMAT_FACTOR[brand.id] || 1;
  return shareBase * cheapestBoost * heroBoost * affinity * format;
}

// Normalized so the 4 curated brands' scores sum to 1 for every product —
// this is what makes each brand's scoped units a real split of the "All
// chains" total instead of an independent estimate that can overshoot it
// (previously an unnormalized 2.7x heuristic let the 4 brands' units add
// up to well over 100% of the unfiltered total).
function productBrandWeight(product, brand) {
  if (!brand) return 1;
  const totalScore = BRANDS.reduce((sum, b) => sum + brandRawDemandScore(product, b), 0);
  if (!totalScore) return 0;
  return +(brandRawDemandScore(product, brand) / totalScore).toFixed(4);
}

function scaleSeries(series, factor) {
  return series.map(v => Math.max(0, Math.round(v * factor)));
}

function scopedSeries(period, brand) {
  const len = PRODUCTS[0].sales[period].length;
  if (!brand) {
    return Array.from({ length: len }, (_, i) => PRODUCTS.reduce((sum, product) => sum + product.sales[period][i], 0));
  }
  return Array.from({ length: len }, (_, i) => PRODUCTS.reduce((sum, product) => {
    return sum + Math.round(product.sales[period][i] * productBrandWeight(product, brand));
  }, 0));
}

function scopedProducts(brand) {
  return PRODUCTS.map(product => {
    const factor = productBrandWeight(product, brand);
    const totalUnits = brand ? Math.round(product.totalUnits * factor) : product.totalUnits;
    const avgPrice = brand ? product.brandPrices[brand.id] : product.avgPrice;
    const trend = brand
      ? +(product.trend * (0.86 + factor * 0.65 + (product.topBrand === brand.id ? 0.18 : 0))).toFixed(1)
      : product.trend;
    return {
      ...product,
      scopedUnits: totalUnits,
      scopedPrice: avgPrice,
      scopedTrend: trend,
    };
  }).filter(product => product.scopedUnits > 0);
}

function scopedCategories(brand) {
  const liveCats = liveTopCategories(brand);
  if (liveCats.length) {
    return liveCats.map(c => ({ name: c.name, units: c.units }));
  }
  const map = new Map();
  scopedProducts(brand).forEach(product => {
    map.set(product.category, (map.get(product.category) || 0) + product.scopedUnits);
  });
  return [...map.entries()].map(([name, units]) => ({ name, units })).sort((a, b) => b.units - a.units);
}

function brandSimulationFactor(brand) {
  const crisisRatio = reportCrisisRatio();
  const stress = liveReport ? (liveReport.agent_wellbeing || {}).avg_stress || 0 : 0;
  if (!brand) return 1 + crisisRatio * 0.16 + stress / 650;
  const valueBoost = brand.id === "2nabiji" || brand.id === "magniti" ? 0.18 : 0.06;
  return 1 + crisisRatio * (0.14 + valueBoost) + stress / 720;
}

function destroyChart(instance) {
  if (!instance || typeof instance.destroy !== "function") return null;
  try { instance.destroy(); } catch (_) {}
  return null;
}

function renderApexChart(targetId, currentInstance, options) {
  const target = gel(targetId);
  if (!target) return destroyChart(currentInstance);
  destroyChart(currentInstance);
  const chart = new ApexCharts(target, options);
  const draw = () => requestAnimationFrame(() => animateChartDraw(target));
  const rendered = chart.render();
  if (rendered && typeof rendered.then === "function") rendered.then(draw).catch(draw);
  else draw();
  return chart;
}

// Left-to-right "draw" entrance: stroke lines are painted via stroke-dashoffset
// (like the Highcharts line-draw demo); area fills / bars fade in underneath.
function animateChartDraw(target) {
  if (!target) return;
  target.querySelectorAll(".apexcharts-series path").forEach(path => {
    const fill = path.getAttribute("fill");
    if (!fill || fill === "none") {
      let len = 0;
      try { len = path.getTotalLength(); } catch (_) { return; }
      if (!len) return;
      const origDash = path.getAttribute("stroke-dasharray");
      path.style.transition = "none";
      path.style.strokeDasharray = len + " " + len;
      path.style.strokeDashoffset = String(len);
      path.getBoundingClientRect();                       // force reflow
      path.style.transition = "stroke-dashoffset 1100ms cubic-bezier(.65,.05,.36,1)";
      path.style.strokeDashoffset = "0";
      const reset = () => {
        path.style.transition = "";
        path.style.strokeDashoffset = "";
        path.style.strokeDasharray = "";
        if (origDash != null) path.setAttribute("stroke-dasharray", origDash); // restore dashed forecast
        path.removeEventListener("transitionend", reset);
      };
      path.addEventListener("transitionend", reset);
    } else {
      path.style.transition = "none";
      path.style.opacity = "0";
      path.getBoundingClientRect();
      path.style.transition = "opacity 900ms ease-out 150ms";
      path.style.opacity = "1";
      const reset = () => { path.style.transition = ""; path.removeEventListener("transitionend", reset); };
      path.addEventListener("transitionend", reset);
    }
  });
}

function reportCrisisRatio() {
  if (!liveReport) return 0;
  const social = liveReport.social_dynamics || {};
  const total = (social.households_in_crisis || 0) + (social.households_stable || 0) + (social.households_comfortable || 0);
  return total ? (social.households_in_crisis || 0) / total : 0;
}

function reportDemandScale() {
  if (!liveReport) return 1;
  const meta = liveReport.simulation_metadata || {};
  const well = liveReport.agent_wellbeing || {};
  const populationFactor = (meta.total_population || 400) / 400;
  const pressureFactor = 1 + reportCrisisRatio() * 0.26 + (well.avg_stress || 0) / 180;
  return +(populationFactor * pressureFactor).toFixed(3);
}

function retailMetrics() {
  const brand = currentBrand();
  const brandFactor = brandSimulationFactor(brand);
  const scoped = scopedProducts(brand);
  const scopedUnits = scoped.reduce((sum, product) => sum + product.scopedUnits, 0);
  const liveBrand = liveBrandMetrics(brand);
  if (!liveReport) {
    return {
      units: (scopedUnits / 1000).toFixed(1) + "k",
      basket: money(brand ? brandBasket(brand) : BRANDS.reduce((s, b) => s + brandBasket(b), 0) / BRANDS.length),
      promos: brand ? brand.promos : BRANDS.reduce((s, b) => s + b.promos, 0),
      priceIndex: brand ? Math.round(brand.priceIdx * 100) : Math.round(BRANDS.reduce((s, b) => s + b.priceIdx, 0) / BRANDS.length * 100),
    };
  }

  const meta = liveReport.simulation_metadata || {};
  const econ = liveReport.economic_summary || {};
  const well = liveReport.agent_wellbeing || {};
  const events = liveReport.events_occurred || {};
  const llm = liveReport.llm_system || {};
  const households = meta.total_households || 100;
  const population = meta.total_population || 399;
  const crisisRatio = reportCrisisRatio();
  const unitsValue = liveBrand && liveBrand.units ? liveBrand.units : Math.round(scopedUnits * brandFactor * (population / 400) * (1 + (events.total_events || 0) * 0.01));
  const basketBase = brand ? brandBasket(brand) : (BRANDS.reduce((s, b) => s + brandBasket(b), 0) / BRANDS.length);
  const basketValue = liveBrand && liveBrand.avg_ticket ? liveBrand.avg_ticket : Math.max(8.4, basketBase * (1 + crisisRatio * 0.16 + (econ.final_avg_budget || 0) / 50000));
  const promoValue = brand
    ? Math.max(1, Math.round(brand.promos * (1 + crisisRatio * 0.2 + (llm.agents_with_reasoning || 0) / 900)))
    : Math.max(2, (events.unique_events || []).length + Math.round((llm.agents_with_reasoning || 0) / 48));
  const priceIndex = brand
    ? clamp(Math.round(brand.priceIdx * 100 + crisisRatio * 12 + (well.avg_stress || 0) * 0.12), 88, 128)
    : clamp(Math.round(94 + crisisRatio * 22 + (well.avg_stress || 0) * 0.45 + households / 100), 90, 126);

  return {
    units: (unitsValue / 1000).toFixed(1) + "k",
    basket: money(basketValue),
    promos: promoValue,
    priceIndex,
  };
}

function brandLogoMarkup(brand, mode = "pill") {
  const cls = mode === "row" ? "brand-logo row" : "brand-logo pill";
  const logos = {
    "2nabiji": "assets/brands/kalata.jpg",
    magniti: "assets/brands/magniti.png",
    spar: "assets/brands/spar.jpeg"
  };
  const src = logos[brand.id];
  if (src) {
    return `<span class="${cls}" aria-hidden="true"><img src="${src}" alt="${escapeHtml(brand.name)} logo" loading="lazy"></span>`;
  }
  return `<span class="${cls} brand-fallback" style="background:${brand.color}">${escapeHtml(brand.short)}</span>`;
}

function syncHeaderFromReport() {
  const freshness = gel("freshnessBadge");
  if (!freshness) return;
  const label = demoNow.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  freshness.innerHTML = `<span class="dot"></span>Simulation · ${label} · Demo simulation`;
}

function simulationButtonLabel(status) {
  if (status === "queued") return '<span class="spinner" aria-hidden="true"></span>Queued';
  if (status === "running") return '<span class="spinner" aria-hidden="true"></span>Running Simulation';
  return '<svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor"><path d="M6 4l14 8-14 8z"/></svg>Run Simulation';
}

function stopSimulationPolling() {
  if (!simulationPollTimer) return;
  clearTimeout(simulationPollTimer);
  simulationPollTimer = null;
}

const SIM_OVERLAY_STEPS = [
  "Initialising 100 Tbilisi households…",
  "Distributing families across districts…",
  "Simulating daily shopping trips…",
  "Applying SKU loyalty & basket choices…",
  "Calculating average basket size…",
  "Aggregating barcode-level demand…",
  "Balancing household budgets…",
  "Pricing brand baskets…",
  "Running Taalas SKU forecast…",
  "Finalising simulation report…",
];
let simOverlayTimer = null;
let simOverlayStep = 0;

function showSimOverlay() {
  const ov = gel("simOverlay");
  if (!ov || ov.classList.contains("open")) return;
  const textEl = gel("simStatusText");
  const advance = () => {
    if (!textEl) return;
    textEl.style.opacity = "0";
    setTimeout(() => {
      textEl.textContent = SIM_OVERLAY_STEPS[simOverlayStep % SIM_OVERLAY_STEPS.length];
      textEl.style.opacity = "1";
      simOverlayStep++;
    }, 220);
  };
  ov.classList.add("open");
  ov.setAttribute("aria-hidden", "false");
  simOverlayStep = 0;
  advance();
  simOverlayTimer = setInterval(advance, 2200);
}

function hideSimOverlay() {
  if (simOverlayTimer) { clearInterval(simOverlayTimer); simOverlayTimer = null; }
  const ov = gel("simOverlay");
  if (ov) { ov.classList.remove("open"); ov.setAttribute("aria-hidden", "true"); }
}

function setSimulationUi(status, message) {
  const runBtn = gel("runSimulationBtn");
  const statusBadge = gel("simStatusBadge");
  const normalized = status || "idle";
  const label = message || (normalized === "done" ? `Completed · job #${simulationJobId || "—"}` : normalized === "error" ? "Failed" : normalized === "running" ? "Running" : normalized === "queued" ? "Queued" : "Ready");
  if (runBtn) {
    runBtn.disabled = normalized === "queued" || normalized === "running";
    runBtn.innerHTML = simulationButtonLabel(normalized);
  }
  if (statusBadge) {
    statusBadge.className = `sim-status ${normalized}`;
    statusBadge.textContent = label;
  }
  if (normalized === "queued" || normalized === "running") showSimOverlay();
  else hideSimOverlay();
}

async function pollSimulationStatus() {
  try {
    const response = await fetch(`/simulation-status?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`simulation status unavailable (${response.status})`);
    const status = await response.json();
    simulationJobId = status.job_id || simulationJobId;
    const elapsed = status.elapsed_seconds ? ` · ${status.elapsed_seconds.toFixed ? status.elapsed_seconds.toFixed(1) : status.elapsed_seconds}s` : "";
    setSimulationUi(status.status, `${status.message || "Simulation status"}${status.status === "queued" || status.status === "running" ? elapsed : ""}`);

    if (status.status === "queued" || status.status === "running") {
      simulationPollTimer = setTimeout(pollSimulationStatus, 1800);
      return;
    }

    stopSimulationPolling();
    if (status.status === "done") {
      await loadSimulationReport({ interactive: false });
      setSimulationUi("done", `Completed · job #${status.job_id || simulationJobId}`);
      simulationPollTimer = setTimeout(() => setSimulationUi("idle", "Ready"), 4500);
      return;
    }

    if (status.status === "error") {
      const tail = (status.stderr_tail || status.stdout_tail || []).slice(-1)[0];
      if (tail) _errs.push("simulation: " + tail);
      showErrs();
      return;
    }
  } catch (e) {
    stopSimulationPolling();
    setSimulationUi("error", "Status unavailable");
    _errs.push("simulation-status: " + e.message);
    showErrs();
  }
}

function renderAiSummary() {
  const aiText = gel("aiText");
  const aiMoreLink = gel("aiMoreLink");
  if (!aiText) return;
  const brand = currentBrand();
  const liveBrand = liveBrandMetrics(brand);
  const scoped = scopedProducts(brand).sort((a, b) => b.scopedUnits - a.scopedUnits);
  const topCategories = scopedCategories(brand).slice(0, 2).map(c => c.name.toLowerCase()).join(" & ");
  const topSku = liveTopProducts(brand)[0] || scoped[0];
  if (!liveReport) {
    aiText.innerHTML = `<b>${escapeHtml(activeBrandLabel())}</b> is currently strongest in <b>${escapeHtml(topCategories || "core grocery")}</b>, led by <b>${escapeHtml(topSku ? topSku.name : "top basket SKUs")}</b>. Brand-specific mock demand is now driving the cards below.`;
    if (aiMoreLink) aiMoreLink.textContent = "Brand-linked summary";
    return;
  }
  const meta = liveReport.simulation_metadata || {};
  const econ = liveReport.economic_summary || {};
  const events = liveReport.events_occurred || {};
  const social = liveReport.social_dynamics || {};
  const llm = liveReport.llm_system || {};
  aiText.innerHTML = `<b>${escapeHtml(activeBrandLabel())}</b> is being read through the latest Tbilisi simulation: <b>${social.households_in_crisis || 0} households</b> in crisis, <b>${llm.agents_with_reasoning || 0} LLM decisions</b>, and liquidity at <b>${money(econ.final_avg_budget || 0)}</b>. For this chain, demand is concentrating into <b>${escapeHtml(topCategories || "core basket")}</b> with <b>${escapeHtml(topSku ? topSku.name : "top SKU")}</b> leading${liveBrand && liveBrand.visits ? ` across <b>${liveBrand.visits} shopping visits</b>` : ""}.`;
  if (aiMoreLink) aiMoreLink.textContent = liveBrand && liveBrand.store_count ? `${liveBrand.store_count} stores · chain filtered` : `${meta.total_households || 0} households · chain filtered`;
}

function renderActions() {
  const container = gel("actionsList");
  if (!container) return;
  const brand = currentBrand();
  const liveBrand = liveBrandMetrics(brand);
  const scoped = scopedProducts(brand).sort((a, b) => b.scopedUnits - a.scopedUnits);
  const topCat = scopedCategories(brand)[0];
  const leadSku = liveTopProducts(brand)[0] || scoped[0];
  const stress = liveReport ? (liveReport.agent_wellbeing || {}).avg_stress || 0 : 0;
  const events = liveReport ? (liveReport.events_occurred || {}) : {};
  const social = liveReport ? (liveReport.social_dynamics || {}) : {};
  const econ = liveReport ? (liveReport.economic_summary || {}) : {};
  const llm = liveReport ? (liveReport.llm_system || {}) : {};
  const actions = [
    {
      tone: "green",
      cta: "Prioritize",
      title: `${escapeHtml(activeBrandLabel())}: protect ${escapeHtml(topCat ? topCat.name : "core")} availability`,
      sub: `${escapeHtml(leadSku ? leadSku.name : "Lead SKU")} is the highest-pressure item for the selected chain${liveBrand && liveBrand.avg_ticket ? ` · avg ticket ${money(liveBrand.avg_ticket)}` : ""}.`,
      icon: '<path d="M12 5v14M5 12h14"/>'
    },
    {
      tone: "amber",
      cta: "Review",
      title: `${escapeHtml(activeBrandLabel())}: price elasticity watch`,
      sub: `${stress ? `Stress ${stress.toFixed(0)} is reshaping the basket` : "Demand mix is shifting"}${topCat ? `, especially in ${topCat.name.toLowerCase()}` : ""}.`,
      icon: '<path d="M12 9v4M12 17h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>'
    },
    {
      tone: "coral",
      cta: "Track",
      title: `${escapeHtml(activeBrandLabel())}: simulation watchlist`,
      sub: `${llm.agents_with_reasoning || 0} reasoning calls, ${(events.unique_events || []).length || 0} shocks, ${liveBrand && liveBrand.store_count ? `${liveBrand.store_count} active stores, ` : ""}and ${money(econ.richest_household || 0)} to ${money(econ.poorest_household || 0)} household spread are feeding this chain view.`,
      icon: '<path d="M3 17l6-6 4 4 8-8"/>'
    }
  ];

  container.innerHTML = actions.map(action => `
    <div class="action">
      <span class="badge-ic ic ${action.tone}">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">${action.icon}</svg>
      </span>
      <div><div class="a-title">${escapeHtml(action.title)}</div><div class="a-sub">${escapeHtml(action.sub)}</div></div>
      <a href="#" class="a-cta">${escapeHtml(action.cta)}</a>
    </div>
  `).join("");
}

// Replaces a single opaque "Confidence NN%" score: a backtest error rate,
// directional bias, and a range the actual result should fall in are each
// individually falsifiable, which a single confidence number is not.
const FORECAST_QUALITY_NOTE = "Backtest WAPE 12.4% · bias +1.7% · 80% interval +8% to +19% (last 12 weeks).";

function renderExplainability() {
  const lead = gel("explainLead");
  const reason = gel("explainReason");
  const next = gel("explainNext");
  if (!lead || !reason || !next) return;
  const brand = currentBrand();
  const categories = scopedCategories(brand);
  const focus = categories[0];
  const nextFocus = categories[1];
  if (!liveReport) {
    lead.innerHTML = `<b>${escapeHtml(activeBrandLabel())}</b> is weighted toward <b>${escapeHtml(focus ? focus.name : "core grocery")}</b>, so the forecast below is recalculated on the selected chain rather than the market total.`;
    reason.textContent = `Signals used: brand share · chain price index · cheapest SKU ownership · top-brand affinity${focus ? ` · strongest category ${focus.name}` : ""}. ${FORECAST_QUALITY_NOTE}`;
    next.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>Switch brands to compare how the same simulation redistributes demand across chains.';
    return;
  }
  const insights = liveReport.insights || [];
  const events = liveReport.events_occurred || {};
  const social = liveReport.social_dynamics || {};
  const well = liveReport.agent_wellbeing || {};
  lead.innerHTML = `<b>${escapeHtml(activeBrandLabel())}</b> absorbs the simulation differently: <b>${social.households_in_crisis || 0} households</b> are in crisis, stress is <b>${well.avg_stress || 0}</b>, and demand is concentrating into <b>${escapeHtml(focus ? focus.name : "core basket")}</b>.`;
  reason.textContent = `Top live signals for ${activeBrandLabel()}: ${(events.unique_events || []).join(" · ") || "Simulation events"} · ${insights.join(" · ")}${nextFocus ? ` · secondary lift in ${nextFocus.name}` : ""}. ${FORECAST_QUALITY_NOTE}`;
  next.innerHTML = `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12h14M13 6l6 6-6 6"/></svg>For ${escapeHtml(activeBrandLabel())}, stock into ${escapeHtml(focus ? focus.name.toLowerCase() : "lead categories")} first, then review ${escapeHtml(nextFocus ? nextFocus.name.toLowerCase() : "secondary demand")} after the next run.`;
}

async function loadSimulationReport(options = {}) {
  const opts = { interactive: false, ...options };
  syncHeaderFromReport(); // demo-driven header badge — always correct regardless of fetch outcome below
  try {
    if (opts.interactive) setSimulationUi("running", "Loading results");

    const response = await fetch(`/simulation-report.json?t=${Date.now()}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`simulation report unavailable (${response.status})`);
    liveReport = await response.json();
    renderAiSummary();
    renderActions();
    renderExplainability();
    fillKpis();
    renderSpotlight();
    renderBrandCmp();
    renderFamilySegments();
    renderMovers();
    renderHero(activeHeroTab);
    renderPriceTrend();
    renderCategory();
    if (currentView !== "overview") renderCurrentPanel();
  } catch (e) {
    if (opts.interactive) _errs.push("simulation-report: " + e.message);
    // No report yet (e.g. before the first simulation run) — render once from
    // the built-in mock dataset so the dashboard isn't stuck on the static
    // "—" placeholders. Once a real report exists this branch never runs.
    if (!liveReport) {
      safe(fillKpis, "fillKpis");
      safe(renderAiSummary, "renderAiSummary");
      safe(renderActions, "renderActions");
      safe(renderExplainability, "renderExplainability");
      safe(renderSpotlight, "renderSpotlight");
      safe(renderBrandCmp, "renderBrandCmp");
      safe(renderFamilySegments, "renderFamilySegments");
      safe(renderMovers, "renderMovers");
      safe(() => renderHero(activeHeroTab), "renderHero");
      safe(renderPriceTrend, "renderPriceTrend");
      safe(renderCategory, "renderCategory");
    }
    showErrs();
  } finally {
    if (opts.interactive) setSimulationUi("idle", "Ready");
  }
}

/* ── Forward-projection date picker ───────────────────────────────────────
   Every "Run Simulation" control opens this instead of calling the real
   (slow, LLM-backed) backend run: pick a horizon, then re-forecast the demo
   brand/product dataset for that many days out (see data.js regenerateForDate).
   The real backend endpoint (/run-simulation) still exists server-side but
   is no longer wired to any button — the whole UI runs on demo data now. ── */
function defaultSimDate(daysAhead) {
  const d = new Date();
  d.setDate(d.getDate() + daysAhead);
  return d.toISOString().slice(0, 10);
}

function openSimDatePicker() {
  const overlay = gel("simDateOverlay");
  if (!overlay) return;
  const input = gel("simDateInput");
  if (input) {
    input.min = defaultSimDate(1);
    if (!input.value) input.value = defaultSimDate(14);
  }
  markActivePreset(14);
  overlay.classList.add("open");
  overlay.setAttribute("aria-hidden", "false");
}

function closeSimDatePicker() {
  const overlay = gel("simDateOverlay");
  if (!overlay) return;
  overlay.classList.remove("open");
  overlay.setAttribute("aria-hidden", "true");
}

function markActivePreset(days) {
  document.querySelectorAll("#simDatePresets button").forEach(btn =>
    btn.classList.toggle("active", Number(btn.dataset.days) === days));
}

function setupSimDatePicker() {
  const overlay = gel("simDateOverlay");
  if (!overlay) return;
  document.querySelectorAll("#simDatePresets button").forEach(btn => {
    btn.onclick = () => {
      const days = Number(btn.dataset.days);
      gel("simDateInput").value = defaultSimDate(days);
      markActivePreset(days);
    };
  });
  const input = gel("simDateInput");
  if (input) input.onchange = () => markActivePreset(-1);
  const cancelBtn = gel("simDateCancel");
  if (cancelBtn) cancelBtn.onclick = closeSimDatePicker;
  const confirmBtn = gel("simDateConfirm");
  if (confirmBtn) confirmBtn.onclick = () => {
    const value = gel("simDateInput").value;
    if (!value) return;
    closeSimDatePicker();
    runForwardProjection(value);
  };
}

function runForwardProjection(dateStr) {
  const target = new Date(dateStr + "T00:00:00");
  const daysAhead = Math.max(1, Math.round((target - Date.now()) / 86400000));
  const label = target.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });

  stopSimulationPolling();
  setSimulationUi("running", `Projecting demand to ${label}`);

  setTimeout(() => {
    window.DM.regenerateForDate(daysAhead);
    demoNow = target;
    const freshness = gel("freshnessBadge");
    if (freshness) freshness.innerHTML = `<span class="dot"></span>Simulation · ${escapeHtml(label)} · Demo projection`;

    safe(fillKpis, "fillKpis");
    safe(renderAiSummary, "renderAiSummary");
    safe(renderActions, "renderActions");
    safe(renderExplainability, "renderExplainability");
    safe(renderSpotlight, "renderSpotlight");
    safe(renderBrandCmp, "renderBrandCmp");
    safe(renderFamilySegments, "renderFamilySegments");
    safe(renderMovers, "renderMovers");
    safe(() => renderHero(activeHeroTab), "renderHero");
    safe(renderPriceTrend, "renderPriceTrend");
    safe(renderCategory, "renderCategory");
    if (currentView !== "overview") safe(renderCurrentPanel, "renderCurrentPanel");

    setSimulationUi("done", `Projected · ${label}`);
    simulationPollTimer = setTimeout(() => setSimulationUi("idle", "Ready"), 3000);
  }, 3400);
}

async function syncSimulationStatusOnLoad() {
  // Only an in-progress job is worth surfacing on a fresh page load — a
  // "done" or "error" status is a one-time completion signal meant to be
  // seen right after an interactive run (handled live by pollSimulationStatus),
  // not resurrected every time the page is reloaded days later.
  try {
    const response = await fetch(`/simulation-status?t=${Date.now()}`, { cache: "no-store" });
    if (response.ok) {
      const status = await response.json();
      simulationJobId = status.job_id || 0;
      if (status.status === "queued" || status.status === "running") {
        setSimulationUi(status.status, `${status.message || "Simulation running"}${status.elapsed_seconds ? ` · ${status.elapsed_seconds}s` : ""}`);
        pollSimulationStatus();
        return;
      }
    }
  } catch (_) {}
  setSimulationUi("idle", "Ready");
}

/* ── Basket + KPI math ────────────────────────────────────────────────── */
const BASKET = PRODUCTS.slice(0, 8);
const brandBasket = b => +BASKET.reduce((s, p) => s + p.brandPrices[b.id], 0).toFixed(2);
const totalUnits  = PRODUCTS.reduce((s, p) => s + p.totalUnits, 0);

function fillKpis() {
  const metrics = retailMetrics();
  const brand = currentBrand();
  gel("kpiUnits").textContent  = metrics.units;
  gel("kpiBasket").textContent = metrics.basket;
  gel("kpiPromos").textContent = metrics.promos;
  gel("kpiPrice").textContent  = metrics.priceIndex;
  gel("eng-skus").textContent  = "12,500";
  if (gel("engChains")) gel("engChains").textContent = chainCount;
  if (gel("kpiUnitsFoot")) gel("kpiUnitsFoot").textContent = brand ? `${brand.name} filtered demand` : `across ${chainCount} chains`;
  // Path B market-sizing disclosure: retail_breakdown counts are the real
  // sample's numbers extrapolated to simulation_metadata.target_population —
  // always show the multiplier alongside them so it's never mistaken for a
  // literal 300,000-person simulation.
  const meta = liveReport && liveReport.simulation_metadata;
  const scaleRow = gel("engScaleRow");
  if (scaleRow) {
    if (meta && meta.target_population && meta.scaling_factor) {
      gel("engScale").textContent = `${meta.target_population.toLocaleString("en-US")} (×${meta.scaling_factor})`;
      scaleRow.style.display = "";
    } else {
      scaleRow.style.display = "none";
    }
  }
}

/* ── Brand bar + spotlight ────────────────────────────────────────────── */
function refreshBrandView() {
  fillKpis();
  renderAiSummary();
  renderActions();
  renderExplainability();
  renderSpotlight();
  renderBrandCmp();
  renderFamilySegments();
  renderMovers();
  renderHero(activeHeroTab);
  renderPriceTrend();
  renderCategory();
}

/* ── Family segment breakdown ─────────────────────────────────────────── */
function renderFamilySegments() {
  const host = gel("segRows");
  if (!host) return;
  const brand = currentBrand();
  const affinity = brand ? (SEGMENT_AFFINITY[brand.id] || {}) : {};
  const rows = BASE_SEGMENTS.map(seg => ({ ...seg, weighted: seg.share * (affinity[seg.name] || 1) }));
  const total = rows.reduce((s, r) => s + r.weighted, 0) || 1;
  rows.forEach(r => { r.pct = Math.round((r.weighted / total) * 100); });
  const diff = 100 - rows.reduce((s, r) => s + r.pct, 0);
  if (diff !== 0) rows[0].pct += diff;
  host.innerHTML = rows.map(r => `
    <tr><td><span class="seg-name"><span class="seg-pip" style="background:${r.color}"></span>${r.name}</span></td>
      <td style="width:120px"><div class="bar-track"><div class="bar-fill" style="width:${r.pct}%;background:${r.color}"></div></div></td>
      <td class="num">${r.pct}%</td><td class="num">${r.priceSens}</td><td class="num">+${r.promoLift}%</td></tr>`).join("");
}

function buildBrandBar() {
  const bar = gel("brandBar");
  bar.innerHTML = '<span class="bb-label">Brand</span>';
  const all = document.createElement("button");
  all.className = "brand-pill" + (selectedBrand === "all" ? " active" : "");
  all.innerHTML = '<span class="brand-logo pill brand-all">∗</span>All chains';
  all.onclick = () => { selectedBrand = "all"; buildBrandBar(); refreshBrandView(); };
  bar.appendChild(all);
  BRANDS.forEach(b => {
    const el = document.createElement("button");
    el.className = "brand-pill" + (selectedBrand === b.id ? " active" : "");
    el.innerHTML = `${brandLogoMarkup(b, "pill")}${b.name}`;
    el.onclick = () => { selectedBrand = b.id; buildBrandBar(); refreshBrandView(); };
    bar.appendChild(el);
  });
}

let spotChart = null;
function brandMonthly(b) {
  let seed = b.share * 7 + 3;
  const rng = () => { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; };
  return MONTHS.map((_, i) => Math.round(b.share * 120 * (1 + i * 0.012) * (0.85 + rng() * 0.3)));
}
function renderSpotlight() {
  const target = gel("chart-brand");
  if (!target) {
    spotChart = destroyChart(spotChart);
    return;
  }
  const b = currentBrand();
  const scale = reportDemandScale();
  const crisisRatio = reportCrisisRatio();
  const synthetic = syntheticBrandRows();
  gel("spotName").textContent = b ? b.name : "All chains";
  if (b) {
    const s = synthetic.find(r => r.brand_id === b.id);
    gel("spotShare").textContent = (s ? s.share_of_spend : b.share) + "%";
    gel("spotBasket").textContent = money(s ? s.avg_ticket : brandBasket(b));
  } else {
    gel("spotShare").textContent = "100%";
    gel("spotBasket").textContent = money(BRANDS.reduce((s, x) => s + brandBasket(x), 0) / BRANDS.length);
  }
  const seriesBase = b ? brandMonthly(b)
    : MONTHS.map((_, i) => BRANDS.reduce((s, x) => s + brandMonthly(x)[i], 0));
  const series = seriesBase.map((v, i) => Math.round(v * scale * (1 + crisisRatio * 0.15 + i * 0.003)));
  const color = b ? b.color : BRAND;
  spotChart = renderApexChart("chart-brand", spotChart, {
    chart: { type: "area", height: 150, sparkline: { enabled: true }, ...base },
    series: [{ name: "Demand", data: series }],
    colors: [color], stroke: { curve: "smooth", width: 2.5 },
    fill: { type: "gradient", gradient: { opacityFrom: 0.4, opacityTo: 0.05 } },
    tooltip: { ...FONT, x: { formatter: (_, o) => MONTHS[o.dataPointIndex] } },
  });
}

/* ── Brand comparison ─────────────────────────────────────────────────── */
function renderBrandCmp() {
  const activeId = currentBrand() ? currentBrand().id : null;
  const synthetic = syntheticBrandRows();
  const rows = BRANDS.map(b => {
    const s = synthetic.find(r => r.brand_id === b.id);
    return { b, basket: s ? s.avg_ticket : brandBasket(b), share: s ? s.share_of_spend : b.share };
  }).sort((x, y) => x.basket - y.basket);
  const cheapest = rows[0].b.id;
  gel("brandCmp").innerHTML = rows.map(({ b, basket, share }) => `
    <div class="chain-row ${b.id === cheapest ? "cheapest" : ""}${b.id === activeId ? " active-brand-row" : ""}">
      ${brandLogoMarkup(b, "row")}
      <span class="c-name">${b.name}</span>
      ${b.id === activeId ? '<span class="cheapest-flag">Selected</span>' : ""}
      ${b.id === cheapest && b.id !== activeId ? '<span class="cheapest-flag">Cheapest</span>' : ""}
      <span class="w-meta" style="margin-left:auto;color:var(--ink-3)">${share}% share</span>
      <span class="c-end" style="min-width:74px;text-align:right">${money(basket)}</span>
    </div>`).join("");
}

/* ── Top movers ───────────────────────────────────────────────────────── */
function renderMovers() {
  const stress = liveReport ? (liveReport.agent_wellbeing || {}).avg_stress || 0 : 0;
  const shock = 1 + stress / 120;
  const brand = currentBrand();
  const productWeights = new Map(liveTopProducts(brand).map(item => [item.name, item.units]));
  const sorted = scopedProducts(brand).map(product => ({
    ...product,
    scopedUnits: productWeights.get(product.name) || product.scopedUnits,
  })).sort((a, b) => ((b.scopedTrend * shock) + b.scopedUnits / 100) - ((a.scopedTrend * shock) + a.scopedUnits / 100));
  const top = sorted.slice(0, 3), bottom = sorted.slice(-3).reverse();
  const row = p => `
    <div class="status-row" style="cursor:pointer" data-bc="${p.barcode}">
      <span class="k" style="color:var(--ink);font-weight:600">${p.name}</span>
      <span class="v" style="color:${p.scopedTrend >= 0 ? "var(--green)" : "var(--coral)"}">${p.scopedTrend >= 0 ? "▲" : "▼"} ${Math.abs(p.scopedTrend)}%</span>
    </div>`;
  gel("movers").innerHTML = top.map(row).join("") + bottom.map(row).join("");
  gel("movers").querySelectorAll("[data-bc]").forEach(el =>
    el.onclick = () => openProduct(PRODUCTS.find(p => p.barcode === el.dataset.bc)));
}

/* ── Hero chart (tabbed) ──────────────────────────────────────────────── */
let heroChart = null;
function heroOptions(tab) {
  const brand = currentBrand();
  if (tab === "brand") {
    const rows = [...BRANDS].sort((a, b) => b.share - a.share);
    return { chart: { type: "bar", height: 300, ...base }, series: [{ name: brand ? `${brand.name} relevance` : "Market share %", data: rows.map(b => {
      if (!brand) return b.share;
      const proximity = b.id === brand.id ? b.share * 1.18 : b.share * (0.72 + (brand.priceIdx <= b.priceIdx ? 0.08 : 0));
      return Math.round(proximity);
    }) }],
      colors: rows.map(b => b.id === selectedBrand ? BRAND : b.color), plotOptions: { bar: { borderRadius: 6, columnWidth: "55%", distributed: true } },
      dataLabels: { enabled: true, formatter: v => v + "%", style: { ...FONT, colors: ["#fff"], fontWeight: 700 } }, legend: { show: false },
      xaxis: { categories: rows.map(b => b.name), labels: { style: { colors: INK3, ...FONT } }, axisBorder: { show: false }, axisTicks: { show: false } },
      yaxis: { labels: { style: { colors: INK3, ...FONT }, formatter: v => v + "%" } }, grid, tooltip: FONT };
  }
  if (tab === "category") {
    const cats = scopedCategories(brand);
    return { chart: { type: "bar", height: 300, ...base }, series: [{ name: brand ? `${brand.name} units` : "Units", data: cats.map(c => c.units) }],
      colors: [brand ? brand.color : BRAND], plotOptions: { bar: { borderRadius: 6, columnWidth: "52%" } }, dataLabels: { enabled: false },
      xaxis: { categories: cats.map(c => c.name), labels: { style: { colors: INK3, ...FONT } }, axisBorder: { show: false }, axisTicks: { show: false } },
      yaxis: { labels: { style: { colors: INK3, ...FONT }, formatter: v => (v / 1000).toFixed(0) + "k" } }, grid, tooltip: FONT };
  }
  const SPLIT = 21;
  const scale = reportDemandScale();
  const crisisRatio = reportCrisisRatio();
  const stress = liveReport ? (liveReport.agent_wellbeing || {}).avg_stress || 0 : 0;
  const baseDaily = scopedSeries("daily", brand);
  const actual = baseDaily.map((v, i) => i <= SPLIT ? Math.round(v * scale * brandSimulationFactor(brand) * (1 + stress * 0.0015 * (i / Math.max(1, SPLIT)))) : null);
  const fc = baseDaily.map((v, i) => i >= SPLIT ? Math.round(v * scale * brandSimulationFactor(brand) * (1 + (i - SPLIT) * 0.012 + crisisRatio * 0.35)) : null);
  return { chart: { type: "area", height: 300, ...base },
    series: [{ name: brand ? `${brand.name} actual` : "Actual demand", data: actual }, { name: brand ? `${brand.name} forecast` : "Forecast", data: fc }],
    colors: [brand ? brand.color : DEMAND_COLORS.actual, BRAND_SOFT], fill: { type: "gradient", gradient: { opacityFrom: 0.3, opacityTo: 0.02 } },
    stroke: { curve: "smooth", width: [3, 3], dashArray: [0, 6] }, dataLabels: { enabled: false },
    legend: { show: true, position: "top", horizontalAlign: "right", ...FONT },
    xaxis: { categories: baseDaily.map((_, i) => "D" + (i + 1)), tickAmount: 10, labels: { style: { colors: INK3, ...FONT } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { colors: INK3, ...FONT } } }, grid, tooltip: { shared: true, ...FONT },
    annotations: { xaxis: [{ x: "D22", borderColor: INK3, strokeDashArray: 4, label: { text: liveReport ? "Sim Forecast" : "Forecast", style: { color: "#fff", background: INK3, ...FONT } } }] } };
}
function destroyHC(instance) {
  if (instance && typeof instance.destroy === "function") { try { instance.destroy(); } catch (_) {} }
  return null;
}

function renderHero(tab) {
  const el = gel("chart-hero");
  if (!el) { heroChart = destroyChart(heroChart); heroHC = destroyHC(heroHC); return; }
  const scaleNote = gel("heroScaleNote");
  if (scaleNote && tab !== "trend") scaleNote.style.display = "none";
  if (tab === "trend") {                       // Highcharts Stock — Actual + AI forecast
    heroChart = destroyChart(heroChart);
    heroHC = renderHeroForecast(el);
  } else if (tab === "brand") {                // Highcharts column — brand share of spend
    heroChart = destroyChart(heroChart);
    heroHC = renderHeroBrandColumn(el);
  } else {                                      // By Category — Highcharts polar radial bar
    heroChart = destroyChart(heroChart);
    heroHC = renderHeroCategoryRadial(el);
  }
}

function renderHeroCategoryRadial(el) {
  heroHC = destroyHC(heroHC);
  el.innerHTML = "";
  if (typeof Highcharts === "undefined") return null;
  // scopedCategories() already handles the live-vs-demo fallback correctly
  // (same helper the separate "Demand by Category" widget uses) — this tab
  // used to read retailBreakdown() directly with no demo fallback at all,
  // so it was permanently empty on any no-backend deploy (Vercel) and
  // locally whenever no real simulation report existed yet.
  const top = scopedCategories(currentBrand()).slice(0, 8).map(c => [c.name, c.units]);
  if (!top.length) {
    el.innerHTML = '<div class="pv-meta" style="padding:24px">No category demand yet — run a simulation.</div>';
    return null;
  }
  const PALETTE = ["#3B6EF5", "#12B76A", "#F5A524", "#F97066", "#8B5CF6", "#06B6D4", "#EC4899", "#84CC16"];
  const categories = top.map(t => t[0]);
  const data = top.map((t, i) => ({ y: t[1], color: PALETTE[i % PALETTE.length] }));
  const total = top.reduce((s, t) => s + t[1], 0) || 1;
  const side = top.map((t, i) => `<div class="hcat-row">
      <span class="hcat-pip" style="background:${PALETTE[i % PALETTE.length]}"></span>
      <span class="hcat-name">${escapeHtml(t[0])}</span>
      <span class="hcat-val mono">${t[1].toLocaleString()}</span>
      <span class="hcat-share mono">${((t[1] / total) * 100).toFixed(1)}%</span>
    </div>`).join("");
  el.innerHTML = `<div class="hero-cat-wrap">
    <div class="hero-cat-chart" id="hero-cat-chart"></div>
    <div class="hero-cat-side">
      <div class="hcat-head">Category demand<span>${total.toLocaleString()} units</span></div>
      ${side}
    </div>
  </div>`;
  return Highcharts.chart(gel("hero-cat-chart"), {
    chart: { polar: true, type: "column", inverted: true, height: 360, backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
    accessibility: { enabled: false },
    title: { text: null },
    pane: { size: "85%", innerSize: "20%", endAngle: 270 },
    xAxis: { categories, tickInterval: 1, lineWidth: 0, gridLineColor: LINE, labels: { style: { color: INK3, fontSize: "12px" } } },
    yAxis: { min: 0, lineWidth: 0, gridLineColor: LINE, endOnTick: true, showLastLabel: true, labels: { style: { color: INK3 } }, title: { text: null } },
    legend: { enabled: false },
    tooltip: { headerFormat: "<span style=\"font-weight:600\">{point.key}</span><br/>", pointFormat: "<b>{point.y} units</b>" },
    plotOptions: { column: { borderRadius: 4, borderWidth: 0, pointPadding: 0.06, groupPadding: 0.1 } },
    series: [{ name: "Category demand", data }],
  });
}

function renderHeroBrandColumn(el) {
  heroHC = destroyHC(heroHC);
  el.innerHTML = "";
  if (typeof Highcharts === "undefined") return null;
  const selected = currentBrand();
  const rows = syntheticBrandRows()
    .map(b => {
      const meta = BRANDS.find(x => x.id === b.brand_id);
      return { id: b.brand_id, name: b.brand_name, value: b.share_of_spend, color: meta ? meta.color : "#3B6EF5" };
    })
    .sort((a, b) => b.value - a.value);
  const data = rows.map(r => ({
    y: Math.round(r.value * 10) / 10,
    color: (selected && r.id === selected.id) ? BRAND : r.color,
  }));
  return Highcharts.chart(el, {
    chart: { type: "column", height: 340, backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
    accessibility: { enabled: false },
    title: { text: null },
    xAxis: { categories: rows.map(r => r.name), crosshair: true, lineColor: LINE,
      labels: { style: { color: INK3 } } },
    yAxis: { min: 0, title: { text: "Share of spend (%)", style: { color: INK3 } },
      gridLineColor: LINE, labels: { style: { color: INK3 }, format: "{value}%" } },
    legend: { enabled: false },
    tooltip: { headerFormat: "<span style=\"font-weight:600\">{point.key}</span><br/>",
      pointFormat: "<b>{point.y}%</b> of simulated spend" },
    plotOptions: { column: { pointPadding: 0.12, borderWidth: 0, borderRadius: 5,
      dataLabels: { enabled: true, format: "{y}%", style: { color: "#667085", fontWeight: "600", textOutline: "none" } } } },
    series: [{ name: "Share of spend", data }],
  });
}

function renderHeroForecast(el) {
  heroHC = destroyHC(heroHC);
  el.innerHTML = "";
  if (typeof Highcharts === "undefined") return null;
  const brand = currentBrand();
  const SPLIT = 21;
  const scale = reportDemandScale();
  const crisisRatio = reportCrisisRatio();
  const stress = liveReport ? (liveReport.agent_wellbeing || {}).avg_stress || 0 : 0;
  // Same "extrapolate the small simulated sample to the real target
  // population" step already disclosed in the sidebar's Market scale row —
  // without it, this chart's units/day reads as this run's ~2,000-person
  // sample, not the ~300,000-person city it's meant to represent.
  const meta = liveReport ? (liveReport.simulation_metadata || {}) : {};
  const marketMultiplier = meta.scaling_factor || 1;
  const baseDaily = scopedSeries("daily", brand);
  const sd = demoNow;
  const baseTs = Date.UTC(sd.getUTCFullYear(), sd.getUTCMonth(), sd.getUTCDate());
  const DAY = 86400000;
  const actual = [], forecast = [];
  baseDaily.forEach((v, i) => {
    const ts = baseTs + (i - SPLIT) * DAY;
    if (i <= SPLIT) actual.push([ts, Math.round(v * scale * marketMultiplier * brandSimulationFactor(brand) * (1 + stress * 0.0015 * (i / Math.max(1, SPLIT))))]);
    if (i >= SPLIT) forecast.push([ts, Math.round(v * scale * marketMultiplier * brandSimulationFactor(brand) * (1 + (i - SPLIT) * 0.012 + crisisRatio * 0.35))]);
  });
  const lastTs = baseTs + (baseDaily.length - 1 - SPLIT) * DAY;
  const scaleNote = gel("heroScaleNote");
  if (scaleNote) {
    if (marketMultiplier > 1 && meta.target_population) {
      scaleNote.textContent = `Extrapolated ×${marketMultiplier} to city-wide scale — target population ${meta.target_population.toLocaleString("en-US")}.`;
      scaleNote.style.display = "";
    } else {
      scaleNote.style.display = "none";
    }
  }
  const aColor = brand ? brand.color : "#3B6EF5";
  const fColor = "#8B5CF6";
  const grad = c => ({ linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
    stops: [[0, Highcharts.color(c).setOpacity(0.28).get("rgba")], [1, Highcharts.color(c).setOpacity(0.02).get("rgba")]] });
  return Highcharts.stockChart(el, {
    chart: { height: 340, backgroundColor: "transparent", style: { fontFamily: FONT.fontFamily } },
    accessibility: { enabled: false },
    // Only 2 buttons: our data window is a fixed ~30 days (21d observed history
    // + 9d forecast), so a "1 month back" button can never have enough history
    // to enable itself — it would sit permanently greyed out. "All" already
    // shows the full window.
    rangeSelector: { enabled: true, inputEnabled: false, selected: 1,
      buttons: [{ type: "week", count: 2, text: "2w" }, { type: "all", text: "All" }] },
    navigator: { enabled: true, maskFill: "rgba(59,110,245,0.08)" },
    scrollbar: { enabled: false },
    legend: { enabled: true, align: "left", verticalAlign: "top", itemStyle: { color: "#667085", fontWeight: "600" } },
    xAxis: {
      type: "datetime", lineColor: LINE, tickColor: LINE, gridLineWidth: 0,
      labels: { style: { color: INK3 } },
      plotBands: [{ from: baseTs, to: lastTs, color: "rgba(139,92,246,0.07)",
        label: { text: "AI forecast", style: { color: fColor, fontWeight: "600" }, align: "center", verticalAlign: "top", y: 16 } }],
      plotLines: [{ value: baseTs, color: INK3, dashStyle: "Dash", width: 1,
        label: { text: "Now", style: { color: INK3 }, rotation: 0, y: 12 } }],
    },
    yAxis: { title: { text: "Units / day", style: { color: INK3 } }, gridLineColor: LINE, labels: { style: { color: INK3 } } },
    tooltip: { shared: true, valueDecimals: 0, valueSuffix: " units" },
    plotOptions: { series: { marker: { enabled: false }, states: { hover: { lineWidthPlus: 0 } } } },
    series: [
      { type: "areaspline", name: brand ? `${brand.name} actual` : "Actual demand", data: actual,
        color: aColor, lineWidth: 2.5, fillColor: grad(aColor) },
      { type: "spline", name: "AI forecast", data: forecast, color: fColor, dashStyle: "ShortDash", lineWidth: 2.5 },
    ],
    responsive: { rules: [{ condition: { maxWidth: 620 },
      chartOptions: { rangeSelector: { enabled: false }, navigator: { enabled: false } } }] },
  });
}

/* ── Price index trend ────────────────────────────────────────────────── */
function renderPriceTrend() {
  if (!gel("chart-price")) {
    priceChart = destroyChart(priceChart);
    return;
  }
  const brand = currentBrand();
  const crisisRatio = reportCrisisRatio();
  const drift = base_ => MONTHS.map((_, i) => +(base_ * (1 + i * 0.004 + crisisRatio * 0.0018 * i)).toFixed(2) * 100 | 0);
  const series = brand ? [
    { name: `${brand.name} price index`, data: drift(brand.priceIdx) },
    { name: "Market baseline", data: drift(BRANDS.reduce((s, b) => s + b.priceIdx, 0) / BRANDS.length) }
  ] : [
    { name: "Value (Kalata, Magniti)", data: drift(0.92) },
    { name: "Mid (Daily)", data: drift(1.02) },
    { name: "Premium (Spar)", data: drift(1.12) },
  ];
  priceChart = renderApexChart("chart-price", priceChart, {
    chart: { type: "line", height: 240, ...base },
    series,
    colors: brand ? [brand.color, "#B4C0D5"] : ["#12B76A", BRAND, "#F97066"], stroke: { curve: "smooth", width: 2.5, dashArray: brand ? [0, 6] : 0 }, dataLabels: { enabled: false },
    legend: { show: true, position: "top", horizontalAlign: "left", ...FONT },
    xaxis: { categories: MONTHS, labels: { style: { colors: INK3, ...FONT } }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { colors: INK3, ...FONT } } }, grid, tooltip: { shared: true, ...FONT },
  });
}

/* ── Category mini (separate widget) ──────────────────────────────────── */
function renderCategory() {
  if (!gel("chart-category")) {
    categoryChart = destroyChart(categoryChart);
    return;
  }
  const brand = currentBrand();
  const categories = scopedCategories(brand);
  const scale = reportDemandScale();
  const hunger = liveReport ? (liveReport.agent_wellbeing || {}).avg_hunger || 0 : 0;
  categoryChart = renderApexChart("chart-category", categoryChart, {
    chart: { type: "bar", height: 240, ...base }, series: [{ name: brand ? `${brand.name} units` : "Units", data: categories.map(c => Math.round(c.units * scale * brandSimulationFactor(brand) * (1 + hunger / 220))) }],
    colors: [brand ? brand.color : BRAND], plotOptions: { bar: { borderRadius: 5, horizontal: true, barHeight: "60%" } },
    dataLabels: { enabled: true, style: { ...FONT, colors: ["#fff"], fontWeight: 600 }, formatter: v => (v / 1000).toFixed(1) + "k", offsetX: -4, textAnchor: "end" },
    xaxis: { categories: categories.map(c => c.name), labels: { show: false }, axisBorder: { show: false }, axisTicks: { show: false } },
    yaxis: { labels: { style: { colors: "#475467", ...FONT, fontWeight: 600 } } },
    grid: { ...grid, yaxis: { lines: { show: false } } }, tooltip: FONT,
  });
}

/* ── Product search (name + barcode) ──────────────────────────────────── */
const searchInput = gel("prodSearch"), resultsBox = gel("searchResults");
function runSearch(q) {
  q = q.trim().toLowerCase();
  if (!q) { resultsBox.classList.remove("open"); return; }
  const matches = PRODUCTS.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q)).slice(0, 8);
  if (!matches.length) { resultsBox.innerHTML = '<div class="sr-empty">No product or barcode match</div>'; resultsBox.classList.add("open"); return; }
  resultsBox.innerHTML = matches.map(p => `
    <div class="sr-item" data-bc="${p.barcode}">
      ${searchThumbMarkup(p)}
      <div><div class="sr-name">${p.name}</div><div class="sr-meta"><span class="bc">${p.barcode}</span> · ${p.category}</div></div>
      <span class="sr-cat">${money(p.avgPrice)}</span>
    </div>`).join("");
  resultsBox.classList.add("open");
  resultsBox.querySelectorAll(".sr-item").forEach(el =>
    el.onclick = () => { openProduct(PRODUCTS.find(p => p.barcode === el.dataset.bc)); resultsBox.classList.remove("open"); searchInput.value = ""; });
}
function catIcon(c) { return { Coffee: "☕", Dairy: "🥛", Bakery: "🍞", Pantry: "🥫", Beverages: "💧", Snacks: "🍫", Meat: "🍗" }[c] || "📦"; }
searchInput.addEventListener("input", e => runSearch(e.target.value));
searchInput.addEventListener("keydown", e => { if (e.key === "Enter") { const f = resultsBox.querySelector(".sr-item"); if (f) f.click(); } if (e.key === "Escape") resultsBox.classList.remove("open"); });
document.addEventListener("click", e => { if (!e.target.closest(".dm-search-wrap")) resultsBox.classList.remove("open"); });

/* ── Product → full detail page (Med Scot style), not a side panel ──────── */
function openProduct(p) { if (p) location.href = "product.html?bc=" + encodeURIComponent(p.barcode); }

/* ── Datasight Analyst chat ───────────────────────────────────────────── */
function setupAnalystChat() {
  const root = gel("analystChat");
  const launch = gel("analystLaunch");
  const panel = gel("analystPanel");
  const close = gel("analystClose");
  const form = gel("analystForm");
  const input = gel("analystInput");
  const messages = gel("analystMessages");
  if (!root || !launch || !panel || !form || !input || !messages) return;
  const chatHistory = [];

  const setOpen = open => {
    panel.hidden = !open;
    launch.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) setTimeout(() => input.focus(), 40);
  };
  const scrollBottom = () => { messages.scrollTop = messages.scrollHeight; };
  const addMessage = (role, text, extraClass = "") => {
    const el = document.createElement("div");
    el.className = `chat-msg ${role} ${extraClass}`.trim();
    el.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
    messages.appendChild(el);
    scrollBottom();
    return el;
  };
  const setBusy = busy => {
    input.disabled = busy;
    form.querySelector("button").disabled = busy;
  };
  const ask = async text => {
    const message = (text || "").trim();
    if (!message) return;
    setOpen(true);
    addMessage("user", message);
    input.value = "";
    setBusy(true);
    const loading = addMessage("bot", "Analyzing retail report and SKU rows...", "loading");
    try {
      const response = await fetch("/assistant-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          brand: selectedBrand,
          history: chatHistory.slice(-8),
        }),
      });
      const payload = await response.json();
      loading.remove();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "assistant unavailable");
      addMessage("bot", payload.answer || "No answer returned.");
      chatHistory.push({ role: "user", content: message });
      chatHistory.push({ role: "assistant", content: payload.answer || "" });
    } catch (err) {
      loading.remove();
      addMessage("bot", "Assistant error: " + err.message);
    } finally {
      setBusy(false);
    }
  };

  launch.onclick = () => setOpen(panel.hidden);
  close.onclick = () => setOpen(false);
  form.onsubmit = event => {
    event.preventDefault();
    ask(input.value);
  };
  root.querySelectorAll("[data-prompt]").forEach(button => {
    button.onclick = () => ask(button.dataset.prompt || button.textContent);
  });
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !panel.hidden) setOpen(false);
  });
}

/* ── Hero tabs ────────────────────────────────────────────────────────── */
document.querySelectorAll("#heroTabs button").forEach(btn => btn.onclick = () => {
  document.querySelectorAll("#heroTabs button").forEach(b => b.classList.remove("active"));
  activeHeroTab = btn.dataset.tab;
  btn.classList.add("active"); renderHero(btn.dataset.tab);
});

/* ── Widget system: registry, collapse, drag, add/remove, persistence ─────
   Widgets live as .widget[data-wid] nodes in #grid. To add a NEW widget type
   later: drop a <div class="widget w-md" data-wid="my-id">…</div> into the grid
   markup and add its title below — the collapse / drag / add-back system picks
   it up automatically. */
const GRID = gel("grid");
const LS_ORDER = "dm.layout.v1", LS_HIDDEN = "dm.hidden.v1", LS_COLLAPSED = "dm.collapsed.v1";
const TITLES = {
  ai: "AI summary", "kpi-units": "Units sold", "kpi-basket": "8-item basket price",
  "kpi-promos": "Active promotions", "kpi-price": "Price index",
  forecast: "Demand Forecast", actions: "Recommended Actions",
  "brand-cmp": "Brand Comparison", "brand-spot": "Brand Spotlight",
  "price-trend": "Price Index Trend", category: "Demand by Category",
  movers: "Top Movers", segments: "Family Segments", explain: "Why this forecast",
};
const getLS = k => { try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch { return []; } };
const setLS = (k, v) => localStorage.setItem(k, JSON.stringify(v));
const saveOrder = () => setLS(LS_ORDER, [...GRID.children].map(el => el.dataset.wid));

/* Wrap each card body so it can collapse, and add a caret to the header. */
function setupCollapse() {
  GRID.querySelectorAll(".widget").forEach(w => {
    const head = w.querySelector(":scope > .w-head");
    if (!head || head.querySelector(".w-caret")) return;
    const body = document.createElement("div");
    body.className = "w-body";
    let n = head.nextElementSibling;
    while (n) { const nx = n.nextElementSibling; body.appendChild(n); n = nx; }
    w.appendChild(body);
    const caret = document.createElement("button");
    caret.className = "w-caret"; caret.title = "Collapse / expand";
    caret.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 15l6-6 6 6"/></svg>';
    caret.onclick = e => { e.stopPropagation(); toggleCollapse(w); };
    head.appendChild(caret);
  });
}
function toggleCollapse(w) {
  w.classList.toggle("collapsed");
  const set = new Set(getLS(LS_COLLAPSED));
  if (w.classList.contains("collapsed")) set.add(w.dataset.wid);
  else { set.delete(w.dataset.wid); setTimeout(() => window.dispatchEvent(new Event("resize")), 60); }
  setLS(LS_COLLAPSED, [...set]);
}

/* Restore saved order / hidden / collapsed state (run AFTER charts render). */
function applyLayout() {
  getLS(LS_COLLAPSED).forEach(id => { const el = GRID.querySelector(`[data-wid="${id}"]`); if (el) el.classList.add("collapsed"); });
  getLS(LS_HIDDEN).forEach(id => { const el = GRID.querySelector(`[data-wid="${id}"]`); if (el) el.style.display = "none"; });
  getLS(LS_ORDER).forEach(id => { const el = GRID.querySelector(`[data-wid="${id}"]`); if (el) GRID.appendChild(el); });
}

function setupDnd() {
  let sortable = null;
  if (typeof Sortable !== "undefined") {
    sortable = Sortable.create(GRID, {
      animation: 180, disabled: true, ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen", dragClass: "sortable-drag", onEnd: saveOrder,
      filter: ".w-caret,.w-remove,.dm-tabs,a,button", preventOnFilter: false,
    });
  }
  const editBtn = gel("editToggle"), addBtn = gel("addWidgetBtn"), addMenu = gel("addWidgetMenu");
  let editing = false;
  editBtn.onclick = () => {
    editing = !editing;
    document.body.classList.toggle("editing", editing);
    editBtn.classList.toggle("on", editing);
    addBtn.style.display = editing ? "grid" : "none";
    if (!editing) addMenu.classList.remove("open");
    if (sortable) sortable.option("disabled", !editing);
  };

  GRID.querySelectorAll(".w-remove").forEach(btn => btn.onclick = e => {
    e.stopPropagation();
    const w = btn.closest(".widget"); w.style.display = "none";
    const set = new Set(getLS(LS_HIDDEN)); set.add(w.dataset.wid); setLS(LS_HIDDEN, [...set]);
    buildAddMenu();
  });

  function buildAddMenu() {
    const hidden = getLS(LS_HIDDEN);
    if (!hidden.length) { addMenu.innerHTML = '<div class="am-empty">All widgets are on the board</div>'; return; }
    addMenu.innerHTML = '<div class="am-title">Add widget</div>' +
      hidden.map(id => `<div class="add-item" data-id="${id}">${TITLES[id] || id}<span class="plus">+</span></div>`).join("");
    addMenu.querySelectorAll(".add-item").forEach(it => it.onclick = () => restoreWidget(it.dataset.id));
  }
  function restoreWidget(id) {
    const el = GRID.querySelector(`[data-wid="${id}"]`);
    if (el) { el.style.display = ""; GRID.appendChild(el); }
    const set = new Set(getLS(LS_HIDDEN)); set.delete(id); setLS(LS_HIDDEN, [...set]);
    saveOrder(); buildAddMenu();
    setTimeout(() => window.dispatchEvent(new Event("resize")), 60);
  }
  addBtn.onclick = e => { e.stopPropagation(); buildAddMenu(); addMenu.classList.toggle("open"); };
  document.addEventListener("click", e => { if (!e.target.closest(".add-wrap")) addMenu.classList.remove("open"); });
  buildAddMenu();
}

/* ── Init (each step isolated so one failure can't blank the board) ──────── */
const _errs = [];
function showErrs() {
  if (!_errs.length) return;
  let b = document.getElementById("dm-fatal");
  if (!b) { b = document.createElement("div"); b.id = "dm-fatal"; document.body.appendChild(b); }
  b.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;z-index:9999;background:#FEF3F2;border:1px solid #F97066;color:#B42318;padding:12px 16px;border-radius:12px;font:12px/1.4 "Segoe UI",-apple-system,BlinkMacSystemFont,"SF Pro Text","Helvetica Neue",Arial,sans-serif;box-shadow:0 8px 24px rgba(16,24,40,.14)';
  b.textContent = "⚠ " + _errs.join("  |  ");
}
const safe = (fn, name) => { try { fn(); } catch (e) { console.error("[Datasight]", name, e); _errs.push(name + ": " + e.message); } };
safe(setupCollapse, "setupCollapse");
safe(buildBrandBar, "buildBrandBar");
// KPIs / brand comparison / spotlight / movers / hero / price / category are
// NOT rendered here with mock data anymore — that caused a visible flash of
// mock numbers before the real simulation_report.json replaced them a moment
// later. loadSimulationReport() renders them once, from real data; its catch
// branch renders them once from the mock dataset only if no report exists yet.
safe(applyLayout, "applyLayout");   // after charts render, so collapsed/hidden charts keep correct width
safe(setupDnd, "setupDnd");
safe(initNav, "initNav");
safe(setupAnalystChat, "setupAnalystChat");
safe(() => setView("overview"), "setView");   // after applyLayout so the view filter wins
safe(() => {
  const runBtn = gel("runSimulationBtn");
  if (runBtn) runBtn.onclick = e => { e.preventDefault(); openSimDatePicker(); };
}, "bindSimulationRefresh");
safe(setupSimDatePicker, "setupSimDatePicker");
safe(() => {
  if (window.DM && typeof window.DM.enrichProductsFromRetail === "function") {
    window.DM.enrichProductsFromRetail().then(() => {
      if (searchInput && searchInput.value.trim()) runSearch(searchInput.value);
    }).catch(() => {});
  }
}, "enrichProductsFromRetail");
safe(() => { loadSimulationReport(); }, "loadSimulationReport");
safe(() => { syncSimulationStatusOnLoad(); }, "syncSimulationStatusOnLoad");
showErrs();
