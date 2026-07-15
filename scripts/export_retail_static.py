#!/usr/bin/env python3
"""Export retail_data.db into static per-barcode JSON files for the static
(Vercel) deployment of the demandmind dashboard, which has no backend server
to answer /retail-product-detail. Re-run this whenever retail_data.db changes.

Forecast data is intentionally NOT baked in here — it depends on the live
simulation report and would go stale. product.js already has a client-side
heuristic forecast fallback for when retailDetail.forecast is absent.
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Dashboard" / "demandmind"))

import serve  # reuse STORE_NAME_MAP / STORE_BRAND_MAP / _effective_price / RETAIL_DB_PATH

OUT_DIR = ROOT / "Dashboard" / "demandmind" / "data" / "retail"


def build_payload(barcode, rows):
    offers_by_store = {}
    for row in rows:
        store_slug = row["store_slug"]
        effective_price = serve._effective_price(row)
        existing = offers_by_store.get(store_slug)
        if existing and existing["effective_price"] <= effective_price:
            continue
        offers_by_store[store_slug] = {
            "store_slug": store_slug,
            "store_name": serve.STORE_NAME_MAP.get(store_slug, store_slug.replace("_", " ").title()),
            "brand_id": serve.STORE_BRAND_MAP.get(store_slug, store_slug),
            "name": row["name"],
            "barcode": row["barcode"],
            "image_url": row["image_url"],
            "unit": row["unit"],
            "category_slug": row["category_slug"],
            "parent_category_slug": row["parent_category_slug"],
            "original_price": float(row["original_price"] or 0),
            "sale_price": float(row["sale_price"] or 0),
            "discount_percent": float(row["discount_percent"] or 0),
            "is_on_sale": bool(row["is_on_sale"]),
            "effective_price": effective_price,
            "chain_rank": int(row["chain_rank"] or 99),
        }
    offers = sorted(offers_by_store.values(), key=lambda o: (o["effective_price"], o["chain_rank"], o["store_slug"]))
    if not offers:
        return None
    first = offers[0]
    prices = [o["effective_price"] for o in offers]
    avg_price = round(sum(prices) / len(prices), 2)
    min_price = round(min(prices), 2)
    max_price = round(max(prices), 2)
    promo_count = sum(1 for o in offers if o["is_on_sale"])
    promo_rate = promo_count / max(len(offers), 1)
    top_brand_counts = {}
    for o in offers:
        top_brand_counts[o["brand_id"]] = top_brand_counts.get(o["brand_id"], 0) + 1
    top_brand_id = sorted(top_brand_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return {
        "barcode": barcode,
        "display_name": first["name"],
        "unit": first["unit"],
        "image_url": first["image_url"],
        "category_slug": first["category_slug"],
        "parent_category_slug": first["parent_category_slug"],
        "offers": offers,
        "summary": {
            "avg_price": avg_price,
            "min_price": min_price,
            "max_price": max_price,
            "price_spread": round(max_price - min_price, 2),
            "store_count": len(offers),
            "promo_count": promo_count,
            "promo_rate": round(promo_rate * 100, 1),
            "cheapest_brand_id": offers[0]["brand_id"],
            "top_brand_id": top_brand_id,
            "model_source": "static-export-live-retail-prices",
        },
        "observed_source": "heuristic",
    }


def main():
    if not serve.RETAIL_DB_PATH.exists():
        print(f"No retail DB at {serve.RETAIL_DB_PATH}")
        return
    conn = sqlite3.connect(serve.RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    barcodes = [r[0] for r in conn.execute(
        "SELECT DISTINCT barcode FROM products WHERE barcode IS NOT NULL"
    ).fetchall()]
    # Clear stale files first — a barcode that had curated-brand offers in a
    # previous export but doesn't anymore (e.g. after tightening the brand
    # filter) must not leave its old JSON snapshot sitting around unchanged.
    if OUT_DIR.exists():
        for existing in OUT_DIR.glob("*.json"):
            existing.unlink()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for barcode in barcodes:
        rows = conn.execute(
            """
            SELECT p.*, pr.original_price, pr.sale_price, pr.discount_percent, pr.is_on_sale
            FROM products p JOIN prices pr ON pr.product_id = p.id
            WHERE p.barcode = ?
            ORDER BY COALESCE(pr.sale_price, pr.original_price) ASC, p.chain_rank ASC, p.id ASC
            """,
            (barcode,),
        ).fetchall()
        rows = [r for r in rows if serve.STORE_BRAND_MAP.get(r["store_slug"], r["store_slug"]) in serve.CURATED_BRAND_IDS]
        payload = build_payload(barcode, rows)
        if payload is None:
            continue
        (OUT_DIR / f"{barcode}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        )
        written += 1
    conn.close()
    print(f"Wrote {written} product JSON files to {OUT_DIR}")


if __name__ == "__main__":
    main()
