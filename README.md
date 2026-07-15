# FamilySim + DemandMind

Synthetic household simulation workspace for Tbilisi retail demand modeling.

## What Is Active

- `Dashboard/demandmind/`
  Active retail demand dashboard in plain HTML/CSS/JS.
- `simulation_core/`, `agents/`, `economy_engine/`, `llm_brain/`
  Headless family simulation and LLM-assisted reasoning stack.
- `georgia-retail-intelligence/retail_data.db`
  Active local retail price database, now rebuilt from `gamige.com` grocery data.

## Current Retail Source Of Truth

The main retail dataset is:

- `georgia-retail-intelligence/retail_data.db`

Current snapshot:

- `22,263` product-store rows
- `22,263` price rows
- `24` distinct stores
- `26` categories
- `21,492` products with image URLs

This SQLite database is the primary local source used by:

- `store_engine.py`
- `data_pipeline/retail_connector.py`
- `economy_engine/market.py`
- `scripts/integrate_retail_data.py`

## Repo Layout

```text
Dashboard/demandmind/         Active demand-forecasting UI
agents/                       Household agent logic
simulation_core/              Simulation loop and population modeling
economy_engine/               Market and pricing logic
llm_brain/                    LLM interfaces and cognition helpers
data/                         Static and raw data inputs
data_pipeline/                Retail ingestion connectors
docs/                         Guides, roadmaps, prompts, reference notes
scripts/                      Setup, launch, integration, maintenance utilities
georgia-retail-intelligence/  Retail collection + migration workspace
```

## Quick Start

Run the active DemandMind UI:

```bash
cd Dashboard/demandmind
python3 serve.py 8600
```

Then open `http://127.0.0.1:8600`.

Run the core simulation:

```bash
python3 simulation_run.py
```

Check retail integration:

```bash
python3 scripts/integrate_retail_data.py --test --sim
```

Run the Taalas/LLM setup helper:

```bash
python3 scripts/setup_taalas.py
```

## Refresh Grocery Data

To rebuild the local retail database from fresh GAMIGE grocery data:

```bash
cd georgia-retail-intelligence
python collector/gamige_grocery_scraper.py
python collector/migrate_gamige_to_retail.py
```

## Notes

- `DemandMind` is the only dashboard surface; legacy map-first views were removed.
- Retail docs live under `docs/reference/database_guide.md`.
- The old `data/raw/georgian_market.csv` path is now only a legacy fallback, not the main retail source.
