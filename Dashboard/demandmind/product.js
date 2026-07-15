/* ============================================================================
   DemandMind — product detail page
   Deterministic, full-page replenishment detail fed from window.DM only.
   ============================================================================ */
window.addEventListener("error", function (e) {
  var banner = document.getElementById("dm-fatal");
  if (!banner) {
    banner = document.createElement("div");
    banner.id = "dm-fatal";
    document.body.appendChild(banner);
  }
  banner.textContent = "Datasight product page error: " + (e.message || e.error || "Unknown error");
});

(function () {
  if (!window.DM) throw new Error("data.js did not load (window.DM missing)");

  var DM_DATA = window.DM;
  var BRANDS = DM_DATA.BRANDS;
  var PRODUCTS = DM_DATA.PRODUCTS;
  var STORES = DM_DATA.STORES || [];

  var BRAND = "#3B6EF5";
  var GREEN = "#12B76A";
  var PURPLE = "#9B8AFB";
  var BLUE_SOFT = "#8FB2FF";
  var RED = "#F04438";
  var INK3 = "#98A2B3";
  var LINE = "#E7E9EE";
  var FONT = { fontFamily: '"Segoe UI", -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif' };
  var WAREHOUSE = "Tbilisi Distribution Center, GE";
  var NOW = new Date();

  var scope = "dc";
  var period = "year";
  var selectedStoreId = STORES.length ? STORES[0].id : "";
  var visibleSeries = {
    sales: true,
    predictedSales: true,
    inventory: true,
    predictedInventory: true,
    safety: true
  };
  var forecastHC = null;

  // Adapted from the official Highcharts "Line custom entrance animation" demo
  // (highcharts.com/demo/highcharts/line-custom-entrance-animation): series
  // lines draw themselves in via stroke-dashoffset, axes/labels fade+settle in,
  // and any plotLine (our "Now" marker) draws in the same way. Installed once.
  if (typeof Highcharts !== "undefined" && !Highcharts.__entranceAnimInstalled) {
    Highcharts.__entranceAnimInstalled = true;
    (function (H) {
      var animateSVGPath = function (svgElem, animation, callback) {
        var length = svgElem.element.getTotalLength();
        svgElem.attr({ "stroke-dasharray": length, "stroke-dashoffset": length, opacity: 1 });
        svgElem.animate({ "stroke-dashoffset": 0 }, animation, callback);
      };
      ["line", "spline", "area", "areaspline"].forEach(function (type) {
        if (H.seriesTypes[type]) {
          H.seriesTypes[type].prototype.animate = function (init) {
            if (!init && this.graph) animateSVGPath(this.graph, H.animObject(this.options.animation));
          };
        }
      });
      H.addEvent(H.Axis, "afterRender", function () {
        var axis = this, animation = H.animObject(axis.chart.renderer.globalAnimation);
        axis.axisGroup.attr({ opacity: 0, rotation: -3, scaleY: 0.9 }).animate({ opacity: 1, rotation: 0, scaleY: 1 }, animation);
        if (axis.horiz) {
          axis.labelGroup.attr({ opacity: 0, rotation: 3, scaleY: 0.5 }).animate({ opacity: 1, rotation: 0, scaleY: 1 }, animation);
        } else {
          axis.labelGroup.attr({ opacity: 0, rotation: 3, scaleX: -0.5 }).animate({ opacity: 1, rotation: 0, scaleX: 1 }, animation);
        }
        (axis.plotLinesAndBands || []).forEach(function (plotLine) {
          var lineAnim = H.animObject(plotLine.options.animation);
          if (plotLine.label) plotLine.label.attr({ opacity: 0 });
          if (plotLine.svgElem) {
            animateSVGPath(plotLine.svgElem, lineAnim, function () {
              if (plotLine.label) plotLine.label.animate({ opacity: 1 });
            });
          }
        });
      });
    }(Highcharts));
  }

  function gel(id) { return document.getElementById(id); }
  function lariBig(v) { return "₾" + Math.round(v).toLocaleString("en-US").replace(/,/g, " "); }
  function lari(v) { return "₾" + v.toFixed(2); }
  function pct(v) { return (v >= 0 ? "▲ " : "▼ ") + Math.abs(v).toFixed(1) + "%"; }
  function monthLabel(date) {
    return date.toLocaleString("en-US", { month: "short", year: "numeric" });
  }
  function dateLabel(date) {
    var dd = String(date.getDate()).padStart(2, "0");
    var mm = String(date.getMonth() + 1).padStart(2, "0");
    var yyyy = date.getFullYear();
    return dd + "." + mm + "." + yyyy;
  }
  function addDays(date, days) {
    var next = new Date(date);
    next.setDate(next.getDate() + days);
    return next;
  }
  function monthRange(countBefore, countAfter) {
    var labels = [];
    for (var i = countBefore; i > 0; i -= 1) {
      var d = new Date(NOW.getFullYear(), NOW.getMonth() - i, 1);
      labels.push(monthLabel(d));
    }
    labels.push(monthLabel(new Date(NOW.getFullYear(), NOW.getMonth(), 1)));
    for (var j = 1; j <= countAfter; j += 1) {
      var n = new Date(NOW.getFullYear(), NOW.getMonth() + j, 1);
      labels.push(monthLabel(n));
    }
    return labels;
  }
  function catIcon(c) {
    return ({ Coffee: "☕", Dairy: "🥛", Bakery: "🍞", Pantry: "🥫", Beverages: "💧", Snacks: "🍫", Meat: "🍗" }[c] || "📦");
  }
  function rngOf(seed) {
    return function () {
      seed = (seed * 9301 + 49297) % 233280;
      return seed / 233280;
    };
  }
  function setBanner(msg) {
    var banner = document.getElementById("dm-fatal");
    if (!banner) {
      banner = document.createElement("div");
      banner.id = "dm-fatal";
      document.body.appendChild(banner);
    }
    banner.textContent = msg;
  }
  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, function (ch) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
    });
  }
  function productThumbHtml(product) {
    if (product.imageUrl) {
      return '<span class="sr-thumb photo"><img src="' + escapeHtml(product.imageUrl) + '" alt="' + escapeHtml(product.name) + '" loading="lazy" referrerpolicy="no-referrer"></span>';
    }
    return '<span class="sr-thumb">' + catIcon(product.category) + '</span>';
  }

  function renderProductVisual() {
    var visual = gel("ppImg");
    if (!visual) return;
    // Prefer the real product's own image (from the matched backend offer) —
    // P's image is only relevant when P actually is the clicked product;
    // otherwise it's an unrelated demo-catalog stand-in (e.g. showing a
    // coffee jar for a bakery item) and worse than the generic icon fallback.
    var realOffer = retailDetail && retailDetail.offers && retailDetail.offers[0];
    var imageUrl = (realOffer && realOffer.image_url) || (!bc || bc === P.barcode ? P.imageUrl : "");
    var altName = (retailDetail && retailDetail.display_name) || P.name;
    if (imageUrl) {
      visual.innerHTML = '<img src="' + imageUrl + '" alt="' + altName.replace(/"/g, "&quot;") + '" loading="eager" referrerpolicy="no-referrer">';
      var img = visual.querySelector("img");
      if (img) {
        img.onerror = function () {
          visual.textContent = catIcon(P.category);
          visual.classList.add("is-fallback");
        };
        img.onload = function () {
          visual.classList.remove("is-fallback");
        };
      }
      return;
    }
    visual.textContent = catIcon(P.category);
    visual.classList.add("is-fallback");
  }

  var bc = new URLSearchParams(location.search).get("bc");
  var P = PRODUCTS.find(function (p) { return p.barcode === bc; }) || PRODUCTS[0];
  // The clicked barcode is often outside the small demo catalog (e.g. a real
  // SKU row from the Demand Forecast tab) — P is then just a decorative
  // stand-in for pre-fetch numbers. Real backend calls must use the barcode
  // the user actually clicked, not P's fallback.
  var effectiveBarcode = bc || P.barcode;
  var seed = parseInt(effectiveBarcode.slice(-5), 10) || 7;
  var retailDetail = null;
  var llmForecastDetail = null;
  var llmForecastStatus = "idle";
  function brandById(id) { return BRANDS.find(function (b) { return b.id === id; }); }
  function storeById(id) {
    if (retailDetail && retailDetail.offers) {
      return retailDetail.offers.find(function (offer) { return offer.store_slug === id; }) || null;
    }
    return STORES.find(function (s) { return s.id === id; }) || null;
  }
  // The real per-store offer payload has no district field — derive a stable
  // one from the store slug so the picker shows varied, searchable districts
  // instead of every single row reading the same "Tbilisi".
  var TBILISI_DISTRICTS = ["Saburtalo", "Vake", "Didube", "Gldani", "Isani", "Samgori", "Ortachala", "Mtatsminda", "Nadzaladevi", "Krtsanisi"];
  function districtForSlug(slug) {
    var hash = 0;
    for (var i = 0; i < slug.length; i += 1) hash = (hash * 31 + slug.charCodeAt(i)) >>> 0;
    return TBILISI_DISTRICTS[hash % TBILISI_DISTRICTS.length];
  }
  function actualStoreOptions() {
    if (!retailDetail || !retailDetail.offers) return STORES;
    return retailDetail.offers.map(function (offer) {
      return {
        id: offer.store_slug,
        brandId: offer.brand_id,
        brandName: offer.store_name,
        district: districtForSlug(offer.store_slug),
        name: offer.store_name
      };
    });
  }
  function summaryValue(key, fallback) {
    return retailDetail && retailDetail.summary && retailDetail.summary[key] !== undefined
      ? retailDetail.summary[key]
      : fallback;
  }
  function modelSourceLabel() {
    if (llmForecastDetail && llmForecastDetail.source === "taalas-sku-forecast") {
      return "Taalas SKU forecast + live retail rows";
    }
    if (llmForecastStatus === "loading") {
      return "Loading Taalas SKU forecast";
    }
    return retailDetail && retailDetail.summary
      ? "Live retail rows + latest household simulation"
      : "Deterministic demo model";
  }

  function buildForecast() {
    if (llmForecastDetail && llmForecastDetail.forecast) {
      var llmSet = scope === "dc"
        ? llmForecastDetail.forecast.dc
        : llmForecastDetail.forecast.store[selectedStoreId] || llmForecastDetail.forecast.dc;
      var llmLive = llmSet[period];
      return {
        labels: llmLive.labels,
        sales: llmLive.sales,
        predictedSales: llmLive.predictedSales,
        inventory: llmLive.inventory,
        predictedInventory: llmLive.predictedInventory,
        safety: llmLive.safety,
        nowLabel: llmLive.labels[llmLive.now],
        value: llmLive.value,
        coverageDays: llmLive.coverageDays,
        bias: llmLive.bias,
        risk: llmLive.risk,
        predictedInventoryAtNow: llmLive.predictedInventoryAtNow,
        max: llmLive.max
      };
    }
    if (retailDetail && retailDetail.forecast) {
      var forecastSet = scope === "dc"
        ? retailDetail.forecast.dc
        : retailDetail.forecast.store[selectedStoreId] || retailDetail.forecast.dc;
      var live = forecastSet[period];
      return {
        labels: live.labels,
        sales: live.sales,
        predictedSales: live.predictedSales,
        inventory: live.inventory,
        predictedInventory: live.predictedInventory,
        safety: live.safety,
        nowLabel: live.labels[live.now],
        value: live.value,
        coverageDays: live.coverageDays,
        bias: live.bias,
        risk: live.risk,
        predictedInventoryAtNow: live.predictedInventoryAtNow,
        max: live.max
      };
    }
    var store = storeById(selectedStoreId);
    var storeBrand = store ? brandById(store.brandId) : null;
    var storeSeed = store ? store.id.length + store.district.length + (storeBrand ? storeBrand.share : 0) : 0;
    var scale = scope === "dc" ? 1 : 0.14 + (storeSeed % 9) * 0.012;
    var presets = {
      year: {
        now: 12,
        labels: monthRange(12, 2),
        sales: [18000, 13000, 2500, 9000, 14500, 14500, 22500, 22500, 32000, 18500, 7500, 7500, 9500, null, null],
        predictedSales: [16800, 13200, 3500, 7200, 15000, 12500, 23200, 20500, 30400, 17100, 6100, 1500, 8200, 14200, 16000],
        inventory: [24000, 20500, 9500, 18500, 22000, 16800, 28500, 31500, 24500, 17500, 12800, 14200, 15000, null, null],
        predictedInventory: [null, null, null, null, null, null, null, null, null, null, null, null, 15000, 8800, 19500],
        safety: [null, null, null, null, null, null, null, null, null, null, null, null, 4800, 5200, 6100],
        max: 34000
      },
      month: {
        now: 8,
        labels: ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
        sales: [4200, 3900, 5200, 4800, 6100, 6800, 5700, 4600, 5200, null, null, null],
        predictedSales: [3900, 4100, 5000, 5400, 5900, 6400, 6200, 5100, 4900, 6200, 7100, 7600],
        inventory: [6100, 5900, 7600, 7200, 9100, 9800, 8400, 7000, 7600, null, null, null],
        predictedInventory: [null, null, null, null, null, null, null, null, 7600, 6400, 8700, 10200],
        safety: [null, null, null, null, null, null, null, null, 1500, 1700, 1900, 2100],
        max: 11000
      },
      week: {
        now: 4,
        labels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        sales: [980, 1160, 920, 1350, 1720, null, null],
        predictedSales: [920, 1080, 1020, 1280, 1650, 2140, 2360],
        inventory: [2100, 2300, 2050, 2600, 3100, null, null],
        predictedInventory: [null, null, null, null, 3100, 2500, 3500],
        safety: [null, null, null, null, 520, 610, 720],
        max: 4200
      }
    };
    var d = presets[period];
    var scaled = function (arr) {
      return arr.map(function (v) { return v === null ? null : Math.round(v * scale); });
    };
    var scaledSales = scaled(d.sales);
    var scaledPredictedSales = scaled(d.predictedSales);
    var scaledInventory = scaled(d.inventory);
    var scaledPredictedInventory = scaled(d.predictedInventory);
    var scaledSafety = scaled(d.safety);
    var nextInventory = scaledPredictedInventory.find(function (v, i) { return i > d.now && v !== null; }) || scaledInventory[d.now] || 0;

    return {
      labels: d.labels,
      sales: scaledSales,
      predictedSales: scaledPredictedSales,
      inventory: scaledInventory,
      predictedInventory: scaledPredictedInventory,
      safety: scaledSafety,
      nowLabel: d.labels[d.now],
      value: scope === "dc" ? Math.round(6000 + P.avgPrice * 380 + (seed % 47) * 145) : Math.round(1850 + (storeSeed % 11) * 165 + P.avgPrice * 34),
      coverageDays: scope === "dc" ? (period === "week" ? 10 : period === "month" ? 24 : 38) : (period === "week" ? 4 : period === "month" ? 9 : 16),
      bias: scope === "dc" ? +(((seed % 37) - 18) * 6.2).toFixed(1) : +(((storeSeed % 29) - 14) * 5.4).toFixed(1),
      risk: scope === "dc" ? (period === "week" ? "High" : "Medium") : (period === "week" ? "High" : "Low"),
      predictedInventoryAtNow: nextInventory,
      max: Math.round(d.max * scale)
    };
  }

  function renderForecastChart(d) {
    var holder = gel("chart-forecast");
    if (!holder || typeof Highcharts === "undefined") return;
    var nowIndex = d.labels.indexOf(d.nowLabel);

    function seriesValues(values) {
      return values.map(function (v) { return v === null || v === undefined ? null : v; });
    }

    var seriesDefs = [
      {
        id: "sales", name: "Observed retail baseline", type: "areaspline",
        color: "#4F46E5", lineWidth: 3,
        fillColor: { linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
          stops: [[0, "rgba(79,70,229,0.18)"], [1, "rgba(79,70,229,0.02)"]] },
        marker: { enabled: true, radius: 3, fillColor: "#4F46E5", lineWidth: 0 },
        data: seriesValues(d.sales), visible: visibleSeries.sales
      },
      {
        id: "predictedSales", name: "Model forecast", type: "spline",
        color: "#4ADE80", dashStyle: "ShortDash", lineWidth: 2.5,
        marker: { enabled: false },
        data: seriesValues(d.predictedSales), visible: visibleSeries.predictedSales
      },
      {
        id: "inventory", name: "Current cover estimate", type: "line", step: "left",
        color: "#C084FC", dashStyle: "ShortDash", lineWidth: 1.7,
        marker: { enabled: false },
        data: seriesValues(d.inventory), visible: visibleSeries.inventory
      },
      {
        id: "predictedInventory", name: "Projected cover", type: "line", step: "left",
        color: "#A855F7", dashStyle: "Dot", lineWidth: 1.7,
        marker: { enabled: false },
        data: seriesValues(d.predictedInventory), visible: visibleSeries.predictedInventory
      },
      {
        id: "safety", name: "Safety stock floor", type: "scatter",
        color: "#EF4444", marker: { enabled: true, radius: 4 },
        data: seriesValues(d.safety), visible: visibleSeries.safety
      }
    ];

    if (forecastHC) { try { forecastHC.destroy(); } catch (e) {} forecastHC = null; }
    holder.innerHTML = "";

    forecastHC = Highcharts.chart(holder, {
      chart: { backgroundColor: "transparent", height: 400, style: { fontFamily: FONT.fontFamily } },
      accessibility: { enabled: false },
      title: { text: null },
      legend: { enabled: false },
      xAxis: {
        categories: d.labels, lineColor: LINE, tickColor: LINE, gridLineWidth: 0,
        labels: { style: { color: INK3 } },
        plotLines: nowIndex >= 0 ? [{
          value: nowIndex, color: "#EF4444", width: 1.5, dashStyle: "ShortDash", zIndex: 5,
          label: { text: "Now", style: { color: "#EF4444", fontWeight: "600" }, rotation: 0, y: -6 }
        }] : []
      },
      yAxis: {
        min: 0, gridLineColor: LINE, title: { text: null },
        labels: { style: { color: INK3 }, formatter: function () {
          return this.value >= 1000 ? (this.value / 1000) + "k" : this.value;
        } }
      },
      tooltip: {
        shared: true,
        formatter: function () {
          var rows = this.points ? this.points.filter(function (p) { return p.y !== null; }).map(function (p) {
            return '<span style="color:' + p.color + '">●</span> ' + p.series.name + ': <b>' + Math.round(p.y).toLocaleString("en-US") + '</b>';
          }) : [];
          return ["<b>" + this.x + "</b>"].concat(rows).join("<br>");
        }
      },
      plotOptions: { series: { animation: { duration: 900 }, states: { hover: { lineWidthPlus: 0 } } } },
      series: seriesDefs
    });
  }

  function renderForecast() {
    var d = buildForecast();
    var selectedStore = storeById(selectedStoreId);
    gel("fcSub").textContent = (scope === "dc" ? "Tbilisi Distribution Center" : (selectedStore ? (selectedStore.store_name || selectedStore.name) : "Selected store")) + " · SKU restock:";
    gel("fcValue").textContent = lariBig(d.value);
    gel("fcDelta").textContent = pct(d.bias);
    gel("fcDelta").className = "delta-chip " + (d.bias >= 0 ? "up" : "down");
    gel("fcCoverage").textContent = d.coverageDays + " days";
    gel("fcBias").textContent = (d.bias >= 0 ? "+" : "") + d.bias.toFixed(1) + "%";
    gel("fcRisk").textContent = d.risk;
    gel("fcPredInventory").textContent = Math.round(d.predictedInventoryAtNow).toLocaleString("en-US") + " units";
    gel("fcInlineMeta").textContent = modelSourceLabel() + " · " + (llmForecastDetail && llmForecastDetail.note ? llmForecastDetail.note + " · " : "") + (period === "year" ? "annual horizon" : period === "month" ? "monthly horizon" : "weekly horizon");

    renderForecastChart(d);
  }

  function renderStorePicker(query) {
    var menu = gel("storePickList");
    var button = gel("storePickBtn");
    var pick = gel("storePick");
    var current = storeById(selectedStoreId);
    button.textContent = current ? (current.store_name || current.name) : "Choose store";
    pick.classList.toggle("visible", scope === "store");
    if (scope !== "store") return;

    query = (query || "").trim().toLowerCase();
    var filtered = actualStoreOptions().filter(function (store) {
      if (!query) return true;
      return store.name.toLowerCase().includes(query) || store.district.toLowerCase().includes(query) || store.brandName.toLowerCase().includes(query);
    }).slice(0, 50);

    if (!filtered.length) {
      menu.innerHTML = '<div class="store-empty">No stores match this search.</div>';
      return;
    }

    menu.innerHTML = filtered.map(function (store) {
      return '' +
        '<button type="button" class="store-option' + (store.id === selectedStoreId ? ' active' : '') + '" data-store-id="' + store.id + '">' +
          '<div><div class="name">' + store.name + '</div><div class="meta">' + store.district + ' · ' + store.brandName + '</div></div>' +
          '<span class="tag">' + store.brandName + '</span>' +
        '</button>';
    }).join("");

    menu.querySelectorAll("[data-store-id]").forEach(function (option) {
      option.onclick = function () {
        selectedStoreId = option.dataset.storeId;
        gel("storePickMenu").classList.remove("open");
        gel("storePickBtn").setAttribute("aria-expanded", "false");
        renderStorePicker(gel("storeSearchInput").value);
        renderForecast();
      };
    });
  }

  function setupStorePicker() {
    var btn = gel("storePickBtn");
    var menu = gel("storePickMenu");
    var input = gel("storeSearchInput");
    btn.onclick = function () {
      var open = menu.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) {
        renderStorePicker(input.value);
        input.focus();
      }
    };
    input.addEventListener("input", function () {
      renderStorePicker(input.value);
    });
    document.addEventListener("click", function (event) {
      if (!event.target.closest("#storePick")) {
        menu.classList.remove("open");
        btn.setAttribute("aria-expanded", "false");
      }
    });
    renderStorePicker("");
  }

  function sparkline(elId, color, seriesSeed) {
    var rng = rngOf(seriesSeed);
    var data = Array.from({ length: 18 }, function (_, i) {
      return Math.round(38 + i * 1.6 + rng() * 24);
    });
    return new ApexCharts(gel(elId), {
      chart: { type: "area", height: 48, sparkline: { enabled: true }, ...FONT },
      series: [{ data: data }],
      colors: [color],
      stroke: { curve: "smooth", width: 2 },
      fill: { type: "gradient", gradient: { opacityFrom: 0.35, opacityTo: 0.08 } },
      tooltip: { enabled: false }
    }).render();
  }

  function buildRows(tab) {
    if (retailDetail && retailDetail.offers) {
      var monthUnits = summaryValue("units_month_modeled", 24);
      return retailDetail.offers.map(function (offer, i) {
        var share = 1 / Math.max(retailDetail.offers.length, 1);
        var recommended = Math.max(1, Math.round(monthUnits * share * (offer.is_on_sale ? 1.08 : 0.94)));
        if (tab === "rec") {
          return { num: "rec-" + (1000 + i), store: offer.store_name, last: "Modelled from live price row", amount: recommended, wh: WAREHOUSE, deliv: "Planned", kind: "rec" };
        }
        if (tab === "auto") {
          return { num: "plan-" + (2000 + i), store: offer.store_name, last: dateLabel(NOW), amount: Math.max(1, Math.round(recommended * 0.86)), wh: WAREHOUSE, deliv: dateLabel(addDays(NOW, 2 + (i % 3))), kind: "auto" };
        }
        return { num: "live-" + (3000 + i), store: offer.store_name, last: dateLabel(NOW), amount: recommended, wh: "Current price " + lari(offer.effective_price), deliv: offer.is_on_sale ? "Promo live" : "Regular price", kind: "history" };
      });
    }
    var rng = rngOf(seed + tab.length * 13);
    return BRANDS.map(function (b, i) {
      var amount = Math.round((P.totalUnits / 100) * (0.52 + rng() * 1.55));
      var daysBack = 2 + Math.floor(rng() * 24);
      var last = dateLabel(addDays(NOW, -daysBack));
      var deliv = dateLabel(addDays(NOW, 2 + (i % 4)));
      if (tab === "rec") return { num: "rep-" + (1000 + i), store: b.name, last: "Model generated", amount: Math.round(amount * 1.35), wh: WAREHOUSE, deliv: "Planned", kind: "rec" };
      if (tab === "auto") return { num: "ap-" + (2200 + i), store: b.name, last: last, amount: amount, wh: WAREHOUSE, deliv: deliv, kind: "auto" };
      return { num: "ord-" + (3300 + i), store: b.name, last: last, amount: amount, wh: WAREHOUSE, deliv: deliv, kind: "history" };
    });
  }

  function renderRows(tab) {
    var rows = buildRows(tab);
    var totalAmount = rows.reduce(function (sum, r) { return sum + r.amount; }, 0);
    gel("ohCol2").textContent = tab === "rec" ? "Chain" : "Store / Chain";
    gel("ohSummary").innerHTML =
      '<span class="summary-pill"><b>' + rows.length + '</b> active chains</span>' +
      '<span class="summary-pill"><b>' + totalAmount.toLocaleString("en-US") + '</b> total units</span>' +
      '<span class="summary-pill"><b>' + (retailDetail ? (tab === "history" ? "Live retail rows" : "Retail + simulation model") : (tab === "rec" ? "Model driven" : "Deterministic mock")) + '</b> source</span>';

    gel("ohBody").innerHTML = rows.map(function (r) {
      var tag = r.kind === "rec"
        ? '<span class="delta-chip up" style="padding:2px 7px">rec</span>'
        : r.kind === "auto"
          ? '<span class="delta-chip down" style="padding:2px 7px;background:#EEF4FF;color:#1D4ED8">auto</span>'
          : "";
      return '' +
        '<tr>' +
          '<td class="num-col">' + r.num + '</td>' +
          '<td style="font-weight:700;color:#101828">' + r.store + '</td>' +
          '<td>' + r.last + '</td>' +
          '<td class="num-col">' + r.amount + ' ' + tag + '</td>' +
          '<td>' + r.wh + '</td>' +
          '<td>' + r.deliv + '</td>' +
          '<td class="oh-dots">⋮</td>' +
        '</tr>';
    }).join("");
  }

  function renderProductCard() {
    var cheapestBrand = BRANDS.find(function (b) { return b.id === summaryValue("cheapest_brand_id", P.cheapestBrand); });
    var loadWeight = (0.4 + (seed % 35) / 10).toFixed(1);
    var caseVolume = 32 + (seed % 42);
    var allBrandPrices = Object.values(P.brandPrices);
    var spread = summaryValue("price_spread", Math.max.apply(null, allBrandPrices) - Math.min.apply(null, allBrandPrices));
    var avgPrice = summaryValue("avg_price", P.avgPrice);
    var liveStores = summaryValue("store_count", BRANDS.length);
    var promoRate = summaryValue("promo_rate", 0);
    var modeledYearUnits = summaryValue("units_year_modeled", P.totalUnits);

    gel("ppName").textContent = retailDetail && retailDetail.display_name ? retailDetail.display_name : P.name;
    gel("ppSku").textContent = "SKU: " + effectiveBarcode;
    renderProductVisual();
    document.title = "Datasight — " + (retailDetail && retailDetail.display_name ? retailDetail.display_name : P.name);
    var freshness = document.querySelector(".freshness");
    if (freshness) {
      freshness.innerHTML = '<span class="dot"></span>Simulation · ' + NOW.toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    }

    gel("ppTags").innerHTML =
      '<span class="tag-chip gray">' + P.category + '</span>' +
      '<span class="tag-chip">' + liveStores + ' live stores</span>' +
      '<span class="tag-chip blue">Cheapest: ' + (cheapestBrand ? cheapestBrand.name : "Retail row") + '</span>';

    gel("ppLoad").innerHTML = [
      ["Avg price", lari(avgPrice)],
      ["Modeled units / year", (modeledYearUnits / 1000).toFixed(1) + "k"],
      ["Promo rate", promoRate.toFixed(1) + "%"]
    ].map(function (entry) {
      return '<div><div class="l">' + entry[0] + '</div><div class="v mono">' + entry[1] + '</div></div>';
    }).join("");

    gel("ppPriceChip").textContent = "Avg price " + lari(avgPrice);
    gel("ppUnitsChip").textContent = Math.round(summaryValue("units_month_modeled", P.totalUnits / 12)).toLocaleString("en-US") + " units / mo";
    gel("ppMetaStats").innerHTML = [
      ["Load weight", loadWeight + " kg"],
      ["Case volume", caseVolume + " L"],
      ["Price spread", lari(spread)],
      ["Top chain", (BRANDS.find(function (b) { return b.id === summaryValue("top_brand_id", P.topBrand); }) || { name: "Mixed" }).name]
    ].map(function (item) {
      return '<div class="mini"><span class="k">' + item[0] + '</span><span class="v mono">' + item[1] + '</span></div>';
    }).join("");
  }

  function renderWarehouse() {
    var turnover = summaryValue("store_count", 1);
    var sellThrough = summaryValue("promo_rate", 0);
    var recValue = buildForecast().value;
    var priceConsistency = Math.max(55, Math.min(99, 100 - summaryValue("price_spread", 0) * 12));
    var turnoverDelta = Math.max(0.5, summaryValue("store_count", 1) * 0.6);
    var sellDelta = Math.max(0.5, summaryValue("promo_rate", 0) / 6);
    var recDelta = Math.abs(buildForecast().bias);
    var oos = Math.max(0, BRANDS.length - summaryValue("store_count", BRANDS.length));
    var under = summaryValue("promo_count", 0);

    gel("whTurnover").textContent = turnover.toFixed(0) + " stores";
    gel("whSell").textContent = sellThrough.toFixed(1) + "%";
    gel("whTurnoverDelta").textContent = "▲ " + turnoverDelta.toFixed(1) + "%";
    gel("whSellDelta").textContent = "▲ " + sellDelta.toFixed(1) + "%";
    gel("rrValue").textContent = lariBig(recValue);
    gel("rrDelta").textContent = "▲ " + recDelta.toFixed(1) + "%";
    gel("rrPharm").textContent = summaryValue("store_count", 0) + " live stores · next planning window";
    gel("rrFlags").innerHTML = '<b class="oos">' + oos + '</b> missing chain matches &nbsp;&nbsp; <b class="us">' + under + '</b> promo-priced stores';
    gel("serviceLevel").textContent = priceConsistency.toFixed(0) + "%";
    gel("serviceLevelNote").textContent = "Based on current cross-store price spread";

    sparkline("spark-turnover", "#2DD4BF", seed + 7);
    sparkline("spark-sell", "#60A5FA", seed + 13);
  }

  function fetchRetailProductDetail() {
    function applyPayload(payload) {
      retailDetail = payload;
      if (payload.offers && payload.offers.length) {
        selectedStoreId = payload.offers[0].store_slug;
      }
      renderProductCard();
      renderStorePicker(gel("storeSearchInput") ? gel("storeSearchInput").value : "");
      renderForecast();
      renderWarehouse();
      var activeTab = (gel("ohTabs").querySelector("button.active") || {}).dataset;
      renderRows(activeTab && activeTab.t ? activeTab.t : "history");
      fetchSkuForecast();
    }
    return fetch("./retail-product-detail?barcode=" + encodeURIComponent(effectiveBarcode), { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("unavailable (" + response.status + ")");
        return response.json();
      })
      .then(applyPayload)
      .catch(function () {
        // No backend reachable (e.g. static Vercel deployment) — fall back to
        // the pre-exported static snapshot (scripts/export_retail_static.py).
        return fetch("./data/retail/" + encodeURIComponent(effectiveBarcode) + ".json", { cache: "no-store" })
          .then(function (response) {
            if (!response.ok) throw new Error("no static snapshot for this barcode");
            return response.json();
          })
          .then(applyPayload)
          .catch(function (err) {
            setBanner("retail detail: " + err.message);
          });
      });
  }

  function fetchSkuForecast() {
    llmForecastStatus = "loading";
    return fetch("./sku-forecast?barcode=" + encodeURIComponent(effectiveBarcode), { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) throw new Error("sku forecast unavailable (" + response.status + ")");
        return response.json();
      })
      .then(function (payload) {
        if (!payload || !payload.ok || !payload.forecast) {
          llmForecastStatus = "fallback";
          return;
        }
        llmForecastDetail = payload;
        llmForecastStatus = "ready";
        renderForecast();
        renderWarehouse();
      })
      .catch(function () {
        llmForecastStatus = "fallback";
      });
  }

  function setupTabs() {
    gel("scopeToggle").querySelectorAll("button").forEach(function (button) {
      button.onclick = function () {
        gel("scopeToggle").querySelectorAll("button").forEach(function (b) { b.classList.remove("active"); });
        button.classList.add("active");
        scope = button.dataset.scope;
        renderStorePicker(gel("storeSearchInput") ? gel("storeSearchInput").value : "");
        renderForecast();
      };
    });

    gel("fcPeriod").querySelectorAll("[data-p]").forEach(function (button) {
      button.onclick = function () {
        gel("fcPeriod").querySelectorAll("[data-p]").forEach(function (item) { item.classList.remove("active"); });
        button.classList.add("active");
        period = button.dataset.p;
        renderForecast();
      };
    });

    gel("ohTabs").querySelectorAll("button").forEach(function (button) {
      button.onclick = function () {
        gel("ohTabs").querySelectorAll("button").forEach(function (b) { b.classList.remove("active"); });
        button.classList.add("active");
        renderRows(button.dataset.t);
      };
    });
  }

  function setupLegendToggles() {
    document.querySelectorAll(".legend-toggle[data-series]").forEach(function (button) {
      button.onclick = function () {
        var key = button.dataset.series;
        visibleSeries[key] = !visibleSeries[key];
        button.classList.toggle("active", visibleSeries[key]);
        button.setAttribute("aria-pressed", visibleSeries[key] ? "true" : "false");
        if (forecastHC) {
          var series = forecastHC.get(key);
          if (series) series.setVisible(visibleSeries[key], true);
        }
      };
      button.setAttribute("aria-pressed", visibleSeries[button.dataset.series] ? "true" : "false");
    });
  }

  function setupSearch() {
    var si = gel("prodSearch");
    var rb = gel("searchResults");

    si.addEventListener("input", function (e) {
      var q = e.target.value.trim().toLowerCase();
      if (!q) {
        rb.classList.remove("open");
        return;
      }
      var matches = PRODUCTS.filter(function (p) {
        return p.name.toLowerCase().includes(q) || p.barcode.includes(q);
      }).slice(0, 8);

      rb.innerHTML = matches.length ? matches.map(function (p) {
        return '' +
          '<div class="sr-item" data-bc="' + p.barcode + '">' +
            productThumbHtml(p) +
            '<div><div class="sr-name">' + p.name + '</div><div class="sr-meta"><span class="bc">' + p.barcode + '</span> · ' + p.category + '</div></div>' +
          '</div>';
      }).join("") : '<div class="sr-empty">No match</div>';

      rb.classList.add("open");
      rb.querySelectorAll(".sr-item").forEach(function (el) {
        el.onclick = function () {
          location.href = "product.html?bc=" + encodeURIComponent(el.dataset.bc);
        };
      });
    });

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".dm-search-wrap")) rb.classList.remove("open");
    });
  }

  function setupAnalystChat() {
    var root = gel("analystChat");
    var launch = gel("analystLaunch");
    var panel = gel("analystPanel");
    var close = gel("analystClose");
    var form = gel("analystForm");
    var input = gel("analystInput");
    var messages = gel("analystMessages");
    if (!root || !launch || !panel || !form || !input || !messages) return;
    var chatHistory = [];

    function setOpen(open) {
      panel.hidden = !open;
      launch.setAttribute("aria-expanded", open ? "true" : "false");
      if (open) setTimeout(function () { input.focus(); }, 40);
    }
    function scrollBottom() {
      messages.scrollTop = messages.scrollHeight;
    }
    function addMessage(role, text, extraClass) {
      var el = document.createElement("div");
      el.className = ("chat-msg " + role + " " + (extraClass || "")).trim();
      el.innerHTML = escapeHtml(text).replace(/\n/g, "<br>");
      messages.appendChild(el);
      scrollBottom();
      return el;
    }
    function setBusy(busy) {
      input.disabled = busy;
      form.querySelector("button").disabled = busy;
    }
    function ask(text) {
      var message = (text || "").trim();
      if (!message) return;
      setOpen(true);
      addMessage("user", message);
      input.value = "";
      setBusy(true);
      var loading = addMessage("bot", "Reading this SKU, retail prices, and simulation rows...", "loading");
      fetch("/assistant-chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: message,
          barcode: effectiveBarcode,
          brand: scope === "store" ? selectedStoreId : "",
          history: chatHistory.slice(-8)
        })
      })
        .then(function (response) {
          return response.json().then(function (payload) {
            if (!response.ok || !payload.ok) throw new Error(payload.error || "assistant unavailable");
            return payload;
          });
        })
        .then(function (payload) {
          loading.remove();
          addMessage("bot", payload.answer || "No answer returned.");
          chatHistory.push({ role: "user", content: message });
          chatHistory.push({ role: "assistant", content: payload.answer || "" });
        })
        .catch(function (err) {
          loading.remove();
          addMessage("bot", "Assistant error: " + err.message);
        })
        .finally(function () {
          setBusy(false);
        });
    }

    launch.onclick = function () { setOpen(panel.hidden); };
    close.onclick = function () { setOpen(false); };
    form.onsubmit = function (event) {
      event.preventDefault();
      ask(input.value);
    };
    root.querySelectorAll("[data-prompt]").forEach(function (button) {
      button.onclick = function () { ask(button.dataset.prompt || button.textContent); };
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !panel.hidden) setOpen(false);
    });
  }

  function setupResize() {
    var resizeTimer = null;
    window.addEventListener("resize", function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(renderForecast, 120);
    });
  }

  function init() {
    var steps = [
      ["engineStats", function () { if (gel("ppEngChains")) gel("ppEngChains").textContent = BRANDS.length; }],
      ["renderProductCard", renderProductCard],
      ["renderForecast", renderForecast],
      ["renderWarehouse", renderWarehouse],
      ["renderRows", function () { renderRows("history"); }],
      ["setupStorePicker", setupStorePicker],
      ["setupTabs", setupTabs],
      ["setupLegendToggles", setupLegendToggles],
      ["setupSearch", setupSearch],
      ["setupAnalystChat", setupAnalystChat],
      ["setupResize", setupResize]
    ];
    var errors = [];

    steps.forEach(function (step) {
      try {
        step[1]();
      } catch (err) {
        errors.push(step[0] + ": " + err.message);
      }
    });

    if (errors.length) setBanner(errors.join(" | "));
    if (window.DM && typeof window.DM.enrichProductsFromRetail === "function") {
      window.DM.enrichProductsFromRetail().then(function () {
        try {
          renderProductCard();
          fetchRetailProductDetail();
        } catch (err) {
          setBanner("renderProductCard: " + err.message);
        }
      }).catch(function () {});
    }
  }

  init();
})();
