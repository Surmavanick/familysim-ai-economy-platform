/* ============================================================================
   DemandMind — mock retail dataset (brand-centric).
   Deterministic generation so numbers are stable across reloads.
   Replace with live retail/simulation endpoints if this file is retired later.
   ============================================================================ */
/* Wrapped in an IIFE: classic scripts share one global lexical scope, so any
   top-level `const BRANDS` here would collide with app.js's destructure of the
   same name ("Identifier already declared"). Only window.DM escapes. */
(function () {
function mulberry32(seed) {
  return function () {
    seed |= 0; seed = seed + 0x6D2B79F5 | 0;
    let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}

/* ── Retail brands / chains (colors from the simulation store metadata) ───── */
const BRANDS = [
  { id: "2nabiji",  name: "Kalata",    short: "K",  color: "#E8521E", share: 26, priceIdx: 0.90, promos: 7 },
  { id: "magniti",  name: "Magniti",   short: "M",  color: "#E30613", share: 28, priceIdx: 0.94, promos: 8 },
  { id: "spar",     name: "Spar",      short: "S",  color: "#00703C", share: 24, priceIdx: 1.12, promos: 4 },
  { id: "daily",    name: "Daily",     short: "D",  color: "#0EA5E9", share: 22, priceIdx: 1.02, promos: 5 },
];
// Baseline snapshot for the "project forward" feature (regenerateForDate) —
// each horizon drifts price/share from this fixed anchor, never from the
// already-drifted state, so repeated picks of the same date stay reproducible.
const BASE_BRANDS = BRANDS.map(b => ({ priceIdx: b.priceIdx, share: b.share }));

/* ── Product catalogue (barcode-searchable) ───────────────────────────────── */
const PRODUCT_DEFS = [
  { name: "JACOBS Espresso Classic 52g",         barcode: "8711000371176", category: "Coffee",    base: 12.80, season: "payday" },
  { name: "MacCoffee Classic 50g",               barcode: "8887290101325", category: "Coffee",    base: 17.40, season: "payday" },
  { name: "Sante Milk 1L",                       barcode: "4860051001304", category: "Dairy",     base: 4.50,  season: "steady" },
  { name: "Sulguni Cheese 900g",                 barcode: "4860450207970", category: "Dairy",     base: 9.20,  season: "weekend" },
  { name: "Lavashi Bread 360g",                  barcode: "4860105010108", category: "Bakery",    base: 1.20,  season: "steady" },
  { name: "Barilla Fusilli 450g",                barcode: "8076809576000", category: "Pantry",    base: 3.80,  season: "steady" },
  { name: "Makfa Flour 1kg",                     barcode: "4601780002572", category: "Pantry",    base: 1.80,  season: "steady" },
  { name: "Calve Tomato Ketchup 350g",           barcode: "4640174750026", category: "Pantry",    base: 3.20,  season: "weekend" },
  { name: "Oleina Sunflower Oil 1L",             barcode: "4607083550482", category: "Pantry",    base: 5.60,  season: "steady" },
  { name: "Our Table Sugar 800g",                barcode: "4860100261710", category: "Pantry",    base: 2.90,  season: "steady" },
  { name: "Eggs Kumisi 10pk",                    barcode: "4860009260302", category: "Dairy",     base: 5.40,  season: "weekend" },
  { name: "Borjomi Mineral Water 0.5L",          barcode: "4860019001353", category: "Beverages", base: 1.90,  season: "summer" },
  { name: "Barambo Export Chocolate 125g",       barcode: "4860009788745", category: "Snacks",    base: 3.50,  season: "payday" },
  { name: "B.YOND Rice Cakes 100g",              barcode: "3800233091182", category: "Pantry",    base: 3.30,  season: "steady" },
  { name: "Grako Chicken Fillet 500g",           barcode: "4860106260021", category: "Meat",      base: 13.50, season: "weekend" },
];

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DISTRICTS = ["Saburtalo", "Vake", "Didube", "Gldani", "Isani", "Samgori", "Ortachala", "Mtatsminda", "Nadzaladevi", "Krtsanisi"];

function seasonalCurve(season, rng) {
  // 12 monthly multipliers
  return MONTHS.map((_, i) => {
    let base = 1;
    if (season === "summer")  base = i >= 5 && i <= 8 ? 1.5 : 0.85;
    if (season === "weekend") base = 1 + (i % 3 === 0 ? 0.15 : 0);
    if (season === "payday")  base = 1.1 - (i % 2) * 0.1;
    return base * (0.9 + rng() * 0.25);
  });
}

function buildProduct(p, idx, seedOffset) {
  const rng = mulberry32(1000 + idx + seedOffset);
  // Prices per brand
  const brandPrices = {};
  BRANDS.forEach(b => { brandPrices[b.id] = +(p.base * b.priceIdx * (0.97 + rng() * 0.07)).toFixed(2); });
  const cheapest = Object.entries(brandPrices).sort((a, b) => a[1] - b[1])[0][0];

  // Sales series
  const monthlyMult = seasonalCurve(p.season, rng);
  const baseVol = Math.round(400 + rng() * 2600);
  const monthly = monthlyMult.map(m => Math.round(baseVol * m));
  const weekly  = Array.from({ length: 12 }, (_, i) => Math.round(baseVol / 4 * (0.85 + rng() * 0.4)));
  const daily   = Array.from({ length: 30 }, (_, i) => {
    const dow = i % 7;
    const weekendBoost = (dow === 5 || dow === 6) ? 1.35 : 1;
    const payday = (i === 0 || i === 14) ? 1.4 : 1;
    return Math.round(baseVol / 30 * weekendBoost * payday * (0.7 + rng() * 0.6));
  });

  const total = monthly.reduce((s, v) => s + v, 0);
  const trend = +(((monthly[11] - monthly[8]) / monthly[8]) * 100).toFixed(1);

  return {
    ...p,
    imageUrl: "",
    brandPrices,
    cheapestBrand: cheapest,
    avgPrice: +(Object.values(brandPrices).reduce((s, v) => s + v, 0) / BRANDS.length).toFixed(2),
    sales: { daily, weekly, monthly },
    totalUnits: total,
    trend,
    topBrand: BRANDS[Math.floor(rng() * 3)].id, // best-selling brand for this product
  };
}

function buildCategories() {
  const map = {};
  PRODUCTS.forEach(p => { map[p.category] = (map[p.category] || 0) + p.totalUnits; });
  return Object.entries(map).map(([name, units]) => ({ name, units })).sort((a, b) => b.units - a.units);
}

const PRODUCTS = PRODUCT_DEFS.map((p, idx) => buildProduct(p, idx, 0));

/* Category aggregates */
const CATEGORIES = buildCategories();

/* ── "Project demand forward" — deterministic re-roll of brand price/share
   drift plus a fresh product/category generation, seeded by the chosen
   horizon so the same date always reproduces the same projection. ────────── */
function regenerateForDate(daysAhead) {
  const horizon = Math.min(1, Math.max(0.15, daysAhead / 45));
  const rng = mulberry32(9000 + Math.round(daysAhead));
  BRANDS.forEach((b, i) => {
    const base = BASE_BRANDS[i];
    const inflation = 1 + horizon * (0.03 + rng() * 0.07);
    const shareJitter = 1 + (rng() - 0.5) * 0.5 * horizon;
    b.priceIdx = +(base.priceIdx * inflation).toFixed(3);
    b.share = Math.max(3, base.share * shareJitter);
  });
  const shareTotal = BRANDS.reduce((s, b) => s + b.share, 0) || 1;
  BRANDS.forEach(b => { b.share = +(b.share / shareTotal * 100).toFixed(1); });

  const seedOffset = Math.round(daysAhead) * 37;
  PRODUCT_DEFS.forEach((p, idx) => Object.assign(PRODUCTS[idx], buildProduct(p, idx, seedOffset)));

  const freshCategories = buildCategories();
  CATEGORIES.length = 0;
  freshCategories.forEach(c => CATEGORIES.push(c));

  return { daysAhead, horizon };
}

const STORES = (() => {
  const stores = [];
  BRANDS.forEach((brand, brandIndex) => {
    const count = brandIndex < 4 ? 30 : 20;
    for (let i = 0; i < count; i += 1) {
      const district = DISTRICTS[(brandIndex * 3 + i) % DISTRICTS.length];
      stores.push({
        id: `${brand.id}-store-${i + 1}`,
        brandId: brand.id,
        brandName: brand.name,
        district,
        name: `${brand.name} ${district} #${String(i + 1).padStart(2, "0")}`,
      });
    }
  });
  return stores;
})();

let retailMediaPromise = null;

function enrichProductsFromRetail() {
  if (retailMediaPromise) return retailMediaPromise;
  const barcodes = PRODUCTS.map(product => product.barcode).filter(Boolean);
  retailMediaPromise = fetch("./retail-product-media?barcodes=" + encodeURIComponent(barcodes.join(",")), { cache: "no-store" })
    .then(response => {
      if (!response.ok) throw new Error("retail media unavailable (" + response.status + ")");
      return response.json();
    })
    .then(payload => {
      const byBarcode = {};
      (payload.items || []).forEach(item => { byBarcode[item.barcode] = item; });
      PRODUCTS.forEach(product => {
        const match = byBarcode[product.barcode];
        if (!match) return;
        product.imageUrl = match.image_url || product.imageUrl || "";
        product.retailName = match.name || product.name;
        product.retailStoreSlug = match.store_slug || "";
      });
      return payload;
    })
    .catch(error => {
      retailMediaPromise = Promise.resolve({ items: [], error: error.message });
      return retailMediaPromise;
    });
  return retailMediaPromise;
}

window.DM = { BRANDS, PRODUCTS, CATEGORIES, MONTHS, STORES, enrichProductsFromRetail, regenerateForDate };
})();
