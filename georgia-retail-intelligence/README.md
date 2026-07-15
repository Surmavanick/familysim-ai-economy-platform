# Georgia Retail Intelligence

Retail collection workspace for the FamilySim + DemandMind project.

## What Is Current

The active local retail database is:

- `retail_data.db`

It is currently rebuilt from **GAMIGE grocery data** and used directly by the main project.

Current snapshot:

- `22,263` product-store rows
- `22,263` price rows
- `24` distinct stores
- `26` categories
- `19,908` rows with preserved barcodes
- `21,492` products with image URLs

Top store slugs in the current snapshot include:

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

## Project Structure

```text
collector/
  gamige_grocery_scraper.py     Scrape current GAMIGE grocery catalog
  migrate_gamige_to_retail.py   Rebuild retail_data.db in the shared schema
sql/schema.sql                  Shared retail schema
gamige_grocery.db               Raw GAMIGE scrape output
retail_data.db                  Active local retail database
```

## Recommended Refresh Flow

When you want fresh grocery data:

```bash
cd georgia-retail-intelligence
python collector/gamige_grocery_scraper.py
python collector/migrate_gamige_to_retail.py
```

That flow:

1. Scrapes GAMIGE grocery listings into `gamige_grocery.db`
2. Rebuilds `retail_data.db` using the existing shared schema, preserving `barcode` and `image_url`
3. Keeps `store_engine.py` and the rest of the app working without code changes

## How The Main Project Uses This

The parent project reads `retail_data.db` through:

- `store_engine.py`
- `data_pipeline/retail_connector.py`
- `economy_engine/market.py`
- `scripts/integrate_retail_data.py`

So once `retail_data.db` is updated here, the simulation and dashboard automatically pick up the new prices.

## Historical Components

The old tarifebi-first collector path has been removed from this workspace.
The active grocery ingestion path is now GAMIGE-only.
