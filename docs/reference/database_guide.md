# Georgia Retail Intelligence — Current Database Guide

## Overview

The project no longer treats the old tarifebi snapshot as the primary retail source.

The current local source of truth is:

- `georgia-retail-intelligence/retail_data.db`

That database is now rebuilt from **GAMIGE grocery data** while preserving the same `products` / `prices` schema that the simulation already expects.

Current snapshot:

- `22,263` product-store rows
- `22,263` price rows
- `24` stores
- `26` categories
- `21,492` products with image URLs

## What Uses This Database

These modules now rely on the shared SQLite retail DB:

- `store_engine.py`
- `data_pipeline/retail_connector.py`
- `economy_engine/market.py`
- `scripts/integrate_retail_data.py`

This means the dashboard, shopping logic, and simulation all read from the same retail source.

## Refresh Flow

Use this flow whenever you want new grocery data:

```bash
cd georgia-retail-intelligence
python collector/gamige_grocery_scraper.py
python collector/migrate_gamige_to_retail.py
```

What happens:

1. `gamige_grocery_scraper.py` collects fresh grocery rows into `gamige_grocery.db`
2. `migrate_gamige_to_retail.py` rewrites `retail_data.db`
3. The rest of the main repo keeps working because the schema stays compatible

## Database Files

- `georgia-retail-intelligence/retail_data.db`
  Active local retail database used by the app
- `georgia-retail-intelligence/gamige_grocery.db`
  Raw GAMIGE scrape snapshot
- `data/raw/retail_stores.json`
  Store metadata, chain names, geography, and slugs

## Schema Notes

The important shared tables are still:

### `products`

- one row per product-store listing
- includes:
  - `id`
  - `name`
  - `image_url`
  - `store_slug`
  - `category_slug`
  - `city_slug`

### `prices`

- one row per captured price
- includes:
  - `product_id`
  - `original_price`
  - `sale_price`
  - `discount_percent`
  - `is_on_sale`
  - `recorded_at`

`store_engine.py` reads prices using:

- `COALESCE(pr.sale_price, pr.original_price)`

So discount price is used when present, otherwise regular price.

## Connector Behavior

`data_pipeline/retail_connector.py` works like this:

1. if `SUPABASE_DB` is configured and reachable, it can use PostgreSQL
2. if not, it falls back to local SQLite automatically
3. if you explicitly pass `db_url="sqlite"`, it uses the local database directly

For the current project setup, the local SQLite path is the normal working mode.

## Market Behavior

`economy_engine/market.py` now:

1. tries Supabase if configured
2. falls back to local SQLite retail data
3. falls back to tiny mock data only if both fail

So `Market(use_live_data=True)` is now effectively “use the shared retail DB first”.

## Quick Checks

Test the connector + market integration:

```bash
python scripts/integrate_retail_data.py --test --sim
```

Quick SQLite query:

```python
import sqlite3

conn = sqlite3.connect("georgia-retail-intelligence/retail_data.db")
cur = conn.cursor()

for row in cur.execute("""
    SELECT store_slug, COUNT(*)
    FROM products
    GROUP BY store_slug
    ORDER BY COUNT(*) DESC
    LIMIT 10
"""):
    print(row)
```

## Current Coverage Notes

The current snapshot includes grocery and adjacent store coverage such as:

- `agrohub`
- `goodwill`
- `carrefour`
- `europroduct`
- `2nabiji`
- `nikora`
- `magniti`
- `zgapari`
- `spar`
- `aversi`
- `psp`
- `pharmadepot`
- `shefisu`
- `alcorium`

This is enough for the current DemandMind workflow, but store coverage is not uniform across chains, so chain-level comparisons should still be read as directional unless the DB is refreshed regularly.

## Historical Components

The old tarifebi-first collector path has been removed from the active workspace.
The current grocery ingestion path is GAMIGE-only.

## Practical Rule

If retail prices look stale, do this first:

```bash
cd georgia-retail-intelligence
python collector/gamige_grocery_scraper.py
python collector/migrate_gamige_to_retail.py
python ../scripts/integrate_retail_data.py --test --sim
```
