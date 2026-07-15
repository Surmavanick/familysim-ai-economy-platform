"""
Simulation report generator.

Aggregates final model state into a structured report dict, persists it to
``simulation_report.json`` and renders a human-readable summary to the terminal.

Schema is kept compatible with the dashboard / QUICK_START tooling that reads
``simulation_report.json``.
"""
import json
import sqlite3
from datetime import datetime, timedelta, date
from pathlib import Path

REPORT_PATH = "simulation_report.json"

# Simulation always starts at this wall-clock (see FamilySimulation.__init__)
_SIM_START = datetime(2024, 1, 1, 8, 0)

# Per-SKU weekly detail is emitted only for the top-N SKUs by units; the long
# tail carries lightweight {units, spend, visits}. Zero-demand SKUs are omitted.
_SKU_TOP_N = 50

# Statistical extrapolation (Path B): the simulation only ever models a sample
# of households (100-1000), not a real city. District/income sampling in
# world/tbilisi_geography.py already draws that sample proportionally to real
# Tbilisi demographics, so scaling the sample's aggregate counts (units,
# spend, visits, headcounts) up to a target population is a standard
# market-sizing extrapolation — the same technique real retail analytics uses
# for census-weighted estimates. Only COUNT/SUM fields are scaled; averages,
# ratios and prices (avg_ticket, share_of_spend, avg_stress, final_avg_budget)
# are population-size-invariant and must NOT be multiplied.
_TARGET_POPULATION = 300_000

# Retail catalog DB (the SKU universe) — read once per report for coverage context.
_RETAIL_DB = Path(__file__).resolve().parent.parent / "georgia-retail-intelligence" / "retail_data.db"


def _safe_avg(values):
    values = list(values)
    return (sum(values) / len(values)) if values else 0.0


def generate_simulation_report(model, save_path=REPORT_PATH):
    """Build the report dict from final model state and persist it to JSON."""
    agents = list(model.schedule.agents)
    households = list(model.households.values())

    budgets = [h.budget for h in households]
    total_wealth = sum(budgets)
    avg_budget = _safe_avg(budgets)

    # ── Wellbeing aggregates ─────────────────────────────────────────────
    avg_stress = _safe_avg(a.stress for a in agents)
    avg_health = _safe_avg(a.health for a in agents)
    avg_hunger = _safe_avg(a.hunger for a in agents)
    avg_fun = _safe_avg(a.fun for a in agents)
    high_stress_count = sum(1 for a in agents if a.stress > 75)
    critical_hunger_count = sum(1 for a in agents if a.hunger > 80)
    agents_with_reasoning = sum(
        1 for a in agents if getattr(a, "last_reasoning", None) is not None
    )

    # ── Household financial tiers ────────────────────────────────────────
    in_crisis = sum(1 for b in budgets if b < 500)
    comfortable = sum(1 for b in budgets if b >= 2000)
    stable = len(households) - in_crisis - comfortable

    # ── Duration / real-calendar anchor ──────────────────────────────────
    # The simulation runs on an internal 2024 clock. Anchor its window to the
    # real calendar so the dashboard's observed series and the forecast share a
    # single timeline: the observed window is the `duration_days` ending today.
    duration_days = max(0, (model.current_time - _SIM_START).days)
    sim_end_date = date.today()
    sim_start_date = sim_end_date - timedelta(days=duration_days)

    # ── Events ───────────────────────────────────────────────────────────
    events_summary = model.events_engine.get_event_summary()

    llm_active = hasattr(model.llm, "api_key")

    # ── Market-size extrapolation (Path B) ────────────────────────────────
    sample_population = len(agents)
    scaling_factor = (_TARGET_POPULATION / sample_population) if sample_population else 1.0

    def scale_count(value):
        """Scale a headcount/unit/spend SUM. Never apply to averages or ratios."""
        return round(value * scaling_factor, 2)

    report = {
        "simulation_metadata": {
            "name": "FAMILYSIM - Tbilisi Family Economy Simulation",
            "duration": f"{sim_end_date} ({duration_days} days)",
            "start_date": sim_start_date.isoformat(),
            "end_date": sim_end_date.isoformat(),
            # Real, actually-simulated sample size — kept honest/unscaled so the
            # Simulation panel never overstates what was literally modeled.
            "total_households": len(households),
            "total_population": len(agents),
            "sample_population": sample_population,
            "sample_households": len(households),
            "target_population": _TARGET_POPULATION,
            "scaling_factor": round(scaling_factor, 3),
            "simulation_date": str(datetime.now()),
        },
        "geographic_distribution": {
            "districts": dict(model.district_distribution),
            "description": (
                "Agents distributed across Tbilisi districts with realistic "
                "income/employment variations"
            ),
        },
        "llm_system": {
            "status": "✓ Active",
            "type": (
                "Taalas Cloud API" if llm_active
                else "Heuristic Reasoning Fallback"
            ),
            "agents_with_reasoning": agents_with_reasoning,
        },
        "economic_summary": {
            # Per-household values/averages — population-size-invariant, not scaled.
            "final_avg_budget": round(avg_budget, 2),
            "richest_household": max(budgets) if budgets else 0,
            "poorest_household": min(budgets) if budgets else 0,
            # A SUM across households — scales with population.
            "total_population_wealth": scale_count(total_wealth),
        },
        "agent_wellbeing": {
            # Averages — not scaled.
            "avg_stress": round(avg_stress, 1),
            "avg_health": round(avg_health, 1),
            "avg_hunger": round(avg_hunger, 1),
            "avg_fun": round(avg_fun, 1),
            # Headcounts — scale with population.
            "high_stress_count": round(high_stress_count * scaling_factor),
            "critical_hunger_count": round(critical_hunger_count * scaling_factor),
        },
        "events_occurred": {
            "total_events": events_summary.get("total_events", 0),
            "by_type": events_summary.get("by_type", {}),
            "unique_events": events_summary.get("unique_events", []),
        },
        "social_dynamics": {
            "households_in_crisis": round(in_crisis * scaling_factor),
            "households_stable": round(stable * scaling_factor),
            "households_comfortable": round(comfortable * scaling_factor),
        },
        "retail_breakdown": _build_retail_breakdown(model, sim_start_date, scaling_factor),
        "insights": _build_insights(model, avg_budget, avg_stress, llm_active),
    }

    if save_path:
        try:
            with open(save_path, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, ensure_ascii=False)
        except OSError as exc:
            print(f"[REPORT] Warning: could not write {save_path}: {exc}")

    return report


def _brand_id_for_chain(chain_name):
    chain = (chain_name or "").strip().lower()
    mapping = {
        "2 nabiji": "2nabiji",
        "magniti": "magniti",
        "spar": "spar",
        "nikora": "nikora",
        "carrefour": "carrefour",
        "goodwill": "goodwill",
    }
    return mapping.get(chain)


def _catalog_size():
    """Distinct barcodes in the retail catalog (the SKU universe). Coverage
    context only; returns None if the DB is unavailable."""
    try:
        conn = sqlite3.connect(str(_RETAIL_DB))
        row = conn.execute(
            "SELECT COUNT(DISTINCT barcode) FROM products "
            "WHERE barcode IS NOT NULL AND barcode != ''"
        ).fetchone()
        conn.close()
        return int(row[0]) if row else None
    except Exception:
        return None


def _build_sku_breakdown(transactions, sim_start_date, scaling_factor=1.0, top_n=_SKU_TOP_N):
    """Aggregate simulated purchases into a barcode-keyed demand signal.

    Zero-demand SKUs are omitted entirely (absence == zero). Every purchased SKU
    carries lightweight {units, spend, visits}; the top-N by units additionally
    carry {stores, brands, weekly_buckets}. Lines without a barcode cannot be
    keyed to a SKU and are tallied under meta.units_without_barcode. Unlike the
    brand-gated totals above, this counts every chain so no SKU signal is lost.

    `scaling_factor` extrapolates the sample's real per-SKU counts to
    _TARGET_POPULATION (Path B market-sizing) — applied to units/spend/visits
    only. Ranking into the top-N happens on raw (pre-scale) units, but since
    scaling is a uniform positive multiplier the relative order is identical
    either way.
    """
    sku = {}
    units_without_barcode = 0
    total_sku_units = 0
    sim_start_internal = _SIM_START.date()

    for tx in transactions:
        chain = tx.get("chain_name")
        brand_id = _brand_id_for_chain(chain) or (chain or "unknown")
        try:
            tx_date = datetime.fromisoformat(tx["timestamp"]).date()
            week_idx = max(0, (tx_date - sim_start_internal).days // 7)
        except Exception:
            week_idx = 0
        counted_visit = set()
        for item in tx.get("items", []):
            qty = item.get("quantity", 1)
            total_sku_units += qty
            barcode = item.get("barcode")
            if not barcode:
                units_without_barcode += qty
                continue
            entry = sku.get(barcode)
            if entry is None:
                entry = sku[barcode] = {
                    "units": 0, "spend": 0.0, "visits": 0,
                    "_stores": {}, "_brands": {}, "_weeks": {},
                }
            spend = item.get("price", 0.0) * qty
            entry["units"] += qty
            entry["spend"] += spend
            if barcode not in counted_visit:
                entry["visits"] += 1
                counted_visit.add(barcode)
            store_slug = item.get("store_slug")
            if store_slug:
                entry["_stores"][store_slug] = entry["_stores"].get(store_slug, 0) + qty
            entry["_brands"][brand_id] = entry["_brands"].get(brand_id, 0) + qty
            week = entry["_weeks"].setdefault(week_idx, {"units": 0, "spend": 0.0})
            week["units"] += qty
            week["spend"] += spend

    ranked = sorted(sku.items(), key=lambda kv: kv[1]["units"], reverse=True)
    detailed = {barcode for barcode, _ in ranked[:top_n]}

    breakdown = {}
    for barcode, entry in sku.items():
        record = {
            "units": round(entry["units"] * scaling_factor),
            "spend": round(entry["spend"] * scaling_factor, 2),
            "visits": round(entry["visits"] * scaling_factor),
        }
        if barcode in detailed:
            record["stores"] = {k: round(v * scaling_factor) for k, v in entry["_stores"].items()}
            record["brands"] = {k: round(v * scaling_factor) for k, v in entry["_brands"].items()}
            record["weekly_buckets"] = [
                {
                    "start": (sim_start_date + timedelta(days=week * 7)).isoformat(),
                    "units": round(data["units"] * scaling_factor),
                    "spend": round(data["spend"] * scaling_factor, 2),
                }
                for week, data in sorted(entry["_weeks"].items())
            ]
        breakdown[barcode] = record

    meta = {
        # Structural/catalog counts — not population-dependent, never scaled.
        "distinct_skus_sold": len(sku),
        "catalog_size": _catalog_size(),
        "top_n_detailed": min(top_n, len(sku)),
        # Real per-SKU volume, scaled to the target population.
        "units_without_barcode": round(units_without_barcode * scaling_factor),
        "total_sku_units": round(total_sku_units * scaling_factor),
    }
    return breakdown, meta


def _build_retail_breakdown(model, sim_start_date, scaling_factor=1.0):
    transactions = list(getattr(model, "retail_transactions", []) or [])
    brand_stats = {}
    store_stats = {}
    totals = {"spend": 0.0, "units": 0, "visits": 0}

    for tx in transactions:
        brand_id = _brand_id_for_chain(tx.get("chain_name"))
        if not brand_id:
            continue
        totals["spend"] += tx.get("total_cost", 0.0)
        totals["units"] += tx.get("units", 0)
        totals["visits"] += 1

        b = brand_stats.setdefault(brand_id, {
            "brand_id": brand_id,
            "brand_name": tx.get("chain_name"),
            "spend": 0.0,
            "units": 0,
            "visits": 0,
            "stores": set(),
            "districts": {},
            "categories": {},
            "products": {},
        })
        b["spend"] += tx.get("total_cost", 0.0)
        b["units"] += tx.get("units", 0)
        b["visits"] += 1
        b["stores"].add(tx.get("store_name"))
        district = tx.get("district") or "Unknown"
        b["districts"][district] = b["districts"].get(district, 0) + 1
        for category, count in (tx.get("categories") or {}).items():
            b["categories"][category] = b["categories"].get(category, 0) + count
        for item in tx.get("items", []):
            name = item.get("name") or item.get("label") or "Unknown"
            b["products"][name] = b["products"].get(name, 0) + 1

        store_key = tx.get("store_name") or f"{brand_id}-store"
        s = store_stats.setdefault(store_key, {
            "store_name": tx.get("store_name"),
            "chain_name": tx.get("chain_name"),
            "brand_id": brand_id,
            "district": district,
            "spend": 0.0,
            "units": 0,
            "visits": 0,
        })
        s["spend"] += tx.get("total_cost", 0.0)
        s["units"] += tx.get("units", 0)
        s["visits"] += 1

    # Ratios (avg_ticket, share_of_spend) are computed from the RAW per-brand
    # sums below — scale-invariant (numerator and denominator scale by the same
    # factor), so this is identical to computing them from scaled sums. Only
    # the display counts (spend/units/visits and their breakdowns) are scaled.
    brands = {}
    for brand_id, stat in brand_stats.items():
        top_categories = sorted(stat["categories"].items(), key=lambda kv: kv[1], reverse=True)[:5]
        top_products = sorted(stat["products"].items(), key=lambda kv: kv[1], reverse=True)[:8]
        brands[brand_id] = {
            "brand_id": brand_id,
            "brand_name": stat["brand_name"],
            "spend": round(stat["spend"] * scaling_factor, 2),
            "units": round(stat["units"] * scaling_factor),
            "visits": round(stat["visits"] * scaling_factor),
            "avg_ticket": round(stat["spend"] / stat["visits"], 2) if stat["visits"] else 0.0,
            "store_count": len(stat["stores"]),
            "share_of_spend": round((stat["spend"] / totals["spend"]) * 100, 1) if totals["spend"] else 0.0,
            "top_categories": [{"name": name, "units": round(units * scaling_factor)} for name, units in top_categories],
            "top_products": [{"name": name, "units": round(units * scaling_factor)} for name, units in top_products],
            "district_mix": {d: round(c * scaling_factor) for d, c in stat["districts"].items()},
        }

    stores = sorted([
        {
            "store_name": stat["store_name"],
            "chain_name": stat["chain_name"],
            "brand_id": stat["brand_id"],
            "district": stat["district"],
            "spend": round(stat["spend"] * scaling_factor, 2),
            "units": round(stat["units"] * scaling_factor),
            "visits": round(stat["visits"] * scaling_factor),
            "avg_ticket": round(stat["spend"] / stat["visits"], 2) if stat["visits"] else 0.0,
        }
        for stat in store_stats.values()
    ], key=lambda row: row["spend"], reverse=True)[:50]

    sku_breakdown, sku_breakdown_meta = _build_sku_breakdown(transactions, sim_start_date, scaling_factor)

    return {
        "totals": {
            "spend": round(totals["spend"] * scaling_factor, 2),
            "units": round(totals["units"] * scaling_factor),
            "visits": round(totals["visits"] * scaling_factor),
        },
        "brands": brands,
        "stores": stores,
        "sku_breakdown": sku_breakdown,
        "sku_breakdown_meta": sku_breakdown_meta,
    }


def _build_insights(model, avg_budget, avg_stress, llm_active):
    insights = [
        "✓ Agents distributed realistically across Tbilisi districts",
        "✓ Real Georgian economic events integrated (child benefits, pensions, utilities)",
    ]
    if avg_stress > 50:
        insights.append("⚠ High average stress — households under economic pressure")
    else:
        insights.append("✓ Stress levels manageable across the population")
    insights.append(
        "✓ LLM reasoning active (Taalas Cloud)" if llm_active
        else "✓ LLM reasoning ready (using heuristic fallback)"
    )
    insights.append(f"✓ Final average household budget: ₾{avg_budget:,.0f}")
    return insights


def print_report(report):
    """Render the report dict to the terminal."""
    meta = report["simulation_metadata"]
    econ = report["economic_summary"]
    well = report["agent_wellbeing"]
    events = report["events_occurred"]
    social = report["social_dynamics"]

    print("\n" + "=" * 60)
    print(f"  {meta['name']}")
    print("=" * 60)
    print(f"  Duration        : {meta['duration']}")
    print(f"  Households       : {meta['total_households']} (sample)")
    print(f"  Population       : {meta['total_population']} (sample)")
    print(f"  Market estimate  : {meta.get('target_population', meta['total_population']):,} "
          f"(x{meta.get('scaling_factor', 1)} extrapolation)")
    print(f"  LLM System       : {report['llm_system']['type']} "
          f"({report['llm_system']['agents_with_reasoning']} agents reasoned)")

    print("\n  -- Economy --")
    print(f"  Avg Budget       : ₾{econ['final_avg_budget']:,.2f}")
    print(f"  Richest / Poorest: ₾{econ['richest_household']:,.2f} / "
          f"₾{econ['poorest_household']:,.2f}")
    print(f"  Total Wealth     : ₾{econ['total_population_wealth']:,.2f}")

    print("\n  -- Wellbeing --")
    print(f"  Avg Stress       : {well['avg_stress']}")
    print(f"  Avg Health       : {well['avg_health']}")
    print(f"  Avg Hunger       : {well['avg_hunger']}")
    print(f"  High Stress      : {well['high_stress_count']} agents")
    print(f"  Critical Hunger  : {well['critical_hunger_count']} agents")

    print("\n  -- Households --")
    print(f"  In Crisis        : {social['households_in_crisis']}")
    print(f"  Stable           : {social['households_stable']}")
    print(f"  Comfortable      : {social['households_comfortable']}")

    print("\n  -- Events --")
    print(f"  Total Events     : {events['total_events']}")
    for etype, count in events["by_type"].items():
        print(f"    - {etype:<12}: {count}")

    print("\n  -- Insights --")
    for line in report["insights"]:
        print(f"  {line}")

    print("\n" + "=" * 60)
    print(f"  Report saved to: {REPORT_PATH}")
    print("=" * 60 + "\n")
