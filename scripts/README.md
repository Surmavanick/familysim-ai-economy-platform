# Scripts Index

## Main Utilities

- `setup_taalas.py` — verify and prepare Taalas-based LLM usage
- `quick_start.py` — compact CLI helper for common Taalas + simulation tasks
- `integrate_retail_data.py` — verify RetailConnector, local SQLite retail DB, and `Market(use_live_data=True)`
- `patch_coordinates.py` — one-off geography data patch helper

## Retail Refresh

Retail refresh scripts now live inside `georgia-retail-intelligence/collector/`:

- `gamige_grocery_scraper.py` — scrape fresh grocery data from GAMIGE
- `migrate_gamige_to_retail.py` — rebuild `retail_data.db` from GAMIGE output
