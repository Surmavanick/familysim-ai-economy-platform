"""
Store selection + basket building engine for FamilySim.
Uses curated retail store geography plus retail_data.db pricing snapshots.
"""
import json
import math
import os
import random
import sqlite3

_DIR = os.path.dirname(os.path.abspath(__file__))
_STORES_PATH = os.path.join(_DIR, "data", "raw", "retail_stores.json")
_DB_PATH = os.path.join(_DIR, "georgia-retail-intelligence", "retail_data.db")

# ── Price tier: income thresholds for store preference ────────────────────────
_TIER_CHAINS = {
    "budget":  ["Magniti", "Kalata", "Daily", "Nikora", "2 Nabiji", "Zgapari", "Ioli"],
    "medium":  ["Spar", "Ioli", "Nikora", "2 Nabiji", "Libre", "Goodwill", "Europroduct", "Georgita", "Zgapari"],
    "premium": ["Carrefour", "Goodwill", "Spar", "Libre", "Agrohub"],
}
# ── Pharmacy chains (triggered by health events, not regular shopping) ────────
PHARMACY_CHAINS = {"Aversi", "PSP", "GPC", "Pharmadepot"}
_PHARMACY_TIER = {
    "budget":  ["Pharmadepot", "Aversi"],
    "medium":  ["Aversi", "PSP", "GPC"],
    "premium": ["PSP", "GPC", "Aversi"],
}
_INCOME_TIER = [
    (0,    500,  "budget"),
    (500,  1500, "medium"),
    (1500, 9e9,  "premium"),
]

# ── Basket categories per role (ordered by priority) ─────────────────────────
_BASKET_CATS = {
    "father":      ["bakery", "milk_kefir", "sausages", "vegetables_fruits", "dairy"],
    "mother":      ["bakery", "vegetables_fruits", "dairy", "milk_kefir", "yogurt"],
    "grandparent": ["bakery", "dairy", "milk_kefir", "vegetables_fruits"],
    "child":       ["bakery", "milk_kefir", "dairy"],
}
_CAT_LABEL = {
    "bakery":            "Bread",
    "milk_kefir":        "Milk",
    "dairy":             "Dairy",
    "vegetables_fruits": "Produce",
    "sausages":          "Sausages",
    "meat_fish":         "Meat",
    "yogurt":            "Yogurt",
    "cheese":            "Cheese",
    "frozen":            "Frozen",
    "snacks":            "Snacks",
}

# ── SKU loyalty: probability a returning household re-buys its preferred barcode ─
_LOYALTY_PROB = 0.7

# ── Module-level cache ─────────────────────────────────────────────────────────
_stores: list | None = None
_price_cache: dict = {}   # (store_slug, category_slug) -> [{product_id, barcode, name, image_url, store_slug, category_slug, parent_category_slug, price}, ...]


def _haversine(lat1, lng1, lat2, lng2) -> float:
    """Returns distance in metres between two WGS-84 points."""
    R = 6_371_000
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_stores() -> list:
    global _stores
    if _stores is None:
        with open(_STORES_PATH, encoding="utf-8") as f:
            _stores = json.load(f)
    return _stores


def _db_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _load_price_rows(store_slug: str, category_slug: str) -> list:
    key = (store_slug, category_slug)
    if key not in _price_cache:
        try:
            conn = _db_conn()
            c = conn.cursor()
            c.execute("""
                SELECT p.id AS product_id,
                       p.barcode,
                       p.name,
                       p.image_url,
                       p.store_slug,
                       p.category_slug,
                       p.parent_category_slug,
                       COALESCE(pr.sale_price, pr.original_price) AS price
                FROM products p
                JOIN prices pr ON p.id = pr.product_id
                WHERE p.store_slug = ? AND p.category_slug = ?
                  AND pr.original_price > 0 AND pr.original_price < 30
                ORDER BY pr.original_price
                LIMIT 60
            """, (store_slug, category_slug))
            rows = [{
                "product_id":           r["product_id"],
                "barcode":              r["barcode"],
                "name":                 r["name"],
                "image_url":            r["image_url"],
                "store_slug":           r["store_slug"],
                "category_slug":        r["category_slug"],
                "parent_category_slug": r["parent_category_slug"],
                "price":                float(r["price"]),
            } for r in c.fetchall()]
            conn.close()
        except Exception:
            rows = []
        _price_cache[key] = rows
    return _price_cache[key]


# Universal fallback categories (widely stocked across all chains)
_FALLBACK_CATS = ["snacks", "chips", "wafers_biscuits", "candy", "nuts_dried",
                   "sauces", "canned_goods", "juice_nectar", "chocolate", "cereals"]


def _income_tier(budget: float) -> str:
    for lo, hi, tier in _INCOME_TIER:
        if lo <= budget < hi:
            return tier
    return "medium"


# ── Public API ─────────────────────────────────────────────────────────────────

def find_nearby_stores(lat: float, lng: float, max_dist_m: float = 1500) -> list:
    """Return stores within max_dist_m, each augmented with a 'dist_m' key."""
    stores = _load_stores()
    result = []
    for s in stores:
        d = _haversine(lat, lng, s["lat"], s["lng"])
        if d <= max_dist_m:
            result.append({**s, "dist_m": round(d)})
    result.sort(key=lambda s: s["dist_m"])
    return result


def select_store(lat: float, lng: float, budget: float,
                 max_dist_m: float = 1500, rng: random.Random | None = None,
                 pharmacy: bool = False) -> dict | None:
    """
    Pick the store an agent will shop at.
    Scoring: distance score (0-1) × 0.45  +  tier match (0/0.5/1) × 0.55
    Falls back to wider radius if nothing nearby.
    """
    if rng is None:
        rng = random
    tier = _income_tier(budget)
    preferred = _PHARMACY_TIER[tier] if pharmacy else _TIER_CHAINS[tier]
    candidates = find_nearby_stores(lat, lng, max_dist_m)
    if not candidates:
        candidates = find_nearby_stores(lat, lng, max_dist_m * 2)
    if not candidates:
        return None

    # Filter to correct store type
    if pharmacy:
        candidates = [s for s in candidates if s["chain"] in PHARMACY_CHAINS] or candidates
    else:
        candidates = [s for s in candidates if s["chain"] not in PHARMACY_CHAINS] or candidates

    max_d = max(s["dist_m"] for s in candidates) or 1
    scored = []
    for s in candidates:
        dist_score = 1.0 - s["dist_m"] / max_d
        tier_score = 1.0 if s["chain"] in preferred else (0.4 if s["price_level"] == tier else 0.1)
        scored.append((dist_score * 0.45 + tier_score * 0.55, s))

    scored.sort(key=lambda x: x[0], reverse=True)
    # Weighted random sample from top-5 to avoid always picking same store
    top = scored[:5]
    weights = [x[0] for x in top]
    total_w = sum(weights)
    r = rng.random() * total_w
    acc = 0
    for w, store in top:
        acc += w
        if r <= acc:
            return store
    return top[0][1]


def build_basket(store_slug: str, role: str, budget: float,
                 rng: random.Random | None = None,
                 preferred_skus: dict | None = None) -> dict:
    """
    Build a realistic grocery basket from DB products at this store.
    Returns:
      {
        "items":  [{"label": "Bread", "name": "...", "price": 2.65,
                    "barcode": "...", "product_id": 123, "store_slug": "...",
                    "category_slug": "bakery"}, ...],
        "total":  12.40,
        "event_label": "Bread ₾2.65, Milk ₾3.20 — Total ₾12.40"
      }
    """
    if rng is None:
        rng = random
    cats = _BASKET_CATS.get(role, _BASKET_CATS["mother"])
    # cap basket at 40% of budget (minimum ₾5 floor so even broke agents eat)
    spend_limit = max(5.0, min(budget * 0.40, 80.0))

    items = []
    spent = 0.0
    # Try preferred categories, then universal fallbacks if basket is still empty
    all_cats = list(cats) + [c for c in _FALLBACK_CATS if c not in cats]
    for cat in all_cats:
        if spent >= spend_limit:
            break
        rows = _load_price_rows(store_slug, cat)
        if not rows:
            continue
        # SKU loyalty: a returning household re-buys its preferred barcode for this
        # category (cross-store). Otherwise pick from the cheapest half and, on the
        # first purchase in this category, establish loyalty.
        pool = rows[:max(1, len(rows)//2)]
        pref_bc = preferred_skus.get(cat) if preferred_skus is not None else None
        row = None
        if pref_bc and rng.random() < _LOYALTY_PROB:
            row = next((r for r in rows if r["barcode"] == pref_bc), None)
        if row is None:
            row = rng.choice(pool)
            if preferred_skus is not None and not pref_bc and row.get("barcode"):
                preferred_skus[cat] = row["barcode"]
        price = row["price"]
        if spent + price > spend_limit:
            continue
        label = _CAT_LABEL.get(cat, cat.replace("_", " ").title())
        items.append({
            "label":         label,
            "name":          row["name"],
            "price":         round(price, 2),
            "barcode":       row["barcode"],
            "product_id":    row["product_id"],
            "store_slug":    row["store_slug"],
            "category_slug": row["category_slug"],
        })
        spent += price
        if len(items) >= len(cats):  # don't add more than preferred list length
            break

    total = round(sum(i["price"] for i in items), 2)
    if items:
        parts = [f"{i['label']} ₾{i['price']:.2f}" for i in items[:3]]
        suffix = f" +{len(items)-3} more" if len(items) > 3 else ""
        event_label = ", ".join(parts) + suffix + f" — Total ₾{total:.2f}"
    else:
        event_label = f"Groceries — Total ₾{total:.2f}"

    return {"items": items, "total": total, "event_label": event_label}


def shopping_trip(lat: float, lng: float, budget: float, role: str,
                  rng: random.Random | None = None,
                  preferred_skus: dict | None = None) -> dict | None:
    """
    Full shopping trip: select store + build basket.
    Returns None if no store found or basket total is 0.
    """
    store = select_store(lat, lng, budget, rng=rng, pharmacy=False)
    if not store:
        return None
    basket = build_basket(store["db_slug"], role, budget, rng=rng, preferred_skus=preferred_skus)
    if basket["total"] <= 0:
        return None
    return {
        "store":         store,
        "basket":        basket,
        "cost":          basket["total"],
        "event_label":   f"{store['name']}: {basket['event_label']}",
    }


_PHARMACY_BASKET_CATS = ["medications", "vitamins", "oral_care_pharm", "hygiene_products"]
_PHARMA_CAT_LABEL = {
    "medications": "Medicine", "vitamins": "Vitamins",
    "oral_care_pharm": "Oral care", "hygiene_products": "Hygiene",
    "special_care": "Treatment", "baby_care": "Baby care",
}

def pharmacy_trip(lat: float, lng: float, budget: float, role: str,
                  rng: random.Random | None = None) -> dict | None:
    """
    Healthcare visit: select nearest pharmacy + build medication basket.
    Triggered when agent health < 60.
    """
    if rng is None:
        rng = random
    store = select_store(lat, lng, budget, max_dist_m=2000, rng=rng, pharmacy=True)
    if not store:
        return None
    spend_limit = max(8.0, min(budget * 0.20, 60.0))
    items = []
    spent = 0.0
    for cat in _PHARMACY_BASKET_CATS:
        rows = _load_price_rows(store["db_slug"], cat)
        if not rows:
            continue
        pool = rows[:max(1, len(rows)//2)]
        row = rng.choice(pool)
        price = row["price"]
        if spent + price > spend_limit:
            continue
        label = _PHARMA_CAT_LABEL.get(cat, cat.replace("_", " ").title())
        items.append({"label": label, "name": row["name"], "price": round(price, 2)})
        spent += price
        if len(items) >= 2:
            break
    if not items:
        return None
    total = round(sum(i["price"] for i in items), 2)
    parts = [f"{i['label']} ₾{i['price']:.2f}" for i in items]
    return {
        "store":       store,
        "cost":        total,
        "event_label": f"{store['name']}: {', '.join(parts)} — Total ₾{total:.2f}",
    }
