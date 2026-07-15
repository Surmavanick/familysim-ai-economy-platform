#!/usr/bin/env python3
"""Export product image/name lookups for the 15 demo-catalog barcodes
(Dashboard/demandmind/data.js) into a static JSON the no-backend (Vercel)
dashboard can fetch as a fallback for /retail-product-media, which only
exists on the local Python server.

Mirrors serve.py's _retail_media_payload() exactly (same query, same
dedup/ordering, not filtered to the 4 curated brands) so the static
fallback matches what the live endpoint already returns locally.
Re-run this whenever data.js's demo PRODUCT_DEFS barcodes change.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "Dashboard" / "demandmind"))

import serve  # reuse RETAIL_DB_PATH

DATA_JS_PATH = ROOT / "Dashboard" / "demandmind" / "data.js"
OUT_PATH = ROOT / "Dashboard" / "demandmind" / "data" / "product-media.json"


def demo_barcodes():
    text = DATA_JS_PATH.read_text()
    return re.findall(r'barcode:\s*"(\d+)"', text)


def main():
    barcodes = demo_barcodes()
    if not barcodes:
        print("No demo barcodes found in data.js")
        return
    if not serve.RETAIL_DB_PATH.exists():
        print(f"No retail DB at {serve.RETAIL_DB_PATH}")
        return

    placeholders = ",".join("?" for _ in barcodes)
    sql = f"""
        SELECT barcode, name, image_url, store_slug, chain_rank
        FROM products
        WHERE barcode IN ({placeholders})
          AND barcode IS NOT NULL
          AND TRIM(barcode) <> ''
          AND image_url IS NOT NULL
          AND TRIM(image_url) <> ''
        ORDER BY CASE WHEN image_url LIKE 'http%' THEN 0 ELSE 1 END, chain_rank ASC, id ASC
    """
    conn = sqlite3.connect(serve.RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, barcodes).fetchall()
    conn.close()

    deduped = {}
    for row in rows:
        if row["barcode"] in deduped:
            continue
        deduped[row["barcode"]] = {
            "barcode": row["barcode"],
            "name": row["name"],
            "image_url": row["image_url"],
            "store_slug": row["store_slug"],
        }

    OUT_PATH.write_text(json.dumps({"items": list(deduped.values())}, ensure_ascii=False, separators=(",", ":")))
    print(f"Wrote {len(deduped)} of {len(barcodes)} demo product images to {OUT_PATH}")


if __name__ == "__main__":
    main()
