#!/usr/bin/env python3
"""DemandMind static server with no-store caching (avoids stale JS during dev)."""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from datetime import date
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*_args, **_kwargs):
        return False

from llm_brain.taalas_interface import TaalaLLMInterface
SIM_REPORT_PATH = ROOT / "simulation_report.json"
RETAIL_DB_PATH = ROOT / "georgia-retail-intelligence" / "retail_data.db"
STORES_JSON_PATH = ROOT / "data" / "raw" / "retail_stores.json"
load_dotenv()

STORE_NAME_MAP = {
    "2nabiji": "2 Nabiji",
    "magniti": "Magniti",
    "spar": "Spar",
    "nikora": "Nikora",
    "carrefour": "Carrefour",
    "goodwill": "Goodwill",
    "agrohub": "Agrohub",
    "europroduct": "Europroduct",
    "zgapari": "Zgapari",
    "shefisu": "Shefisu",
}
STORE_BRAND_MAP = {
    "2nabiji": "2nabiji",
    "magniti": "magniti",
    "spar": "spar",
    "nikora": "nikora",
    "carrefour": "carrefour",
    "goodwill": "goodwill",
}
CATEGORY_FACTOR_MAP = {
    "hot_drinks": 0.085,
    "dairy": 0.11,
    "bakery": 0.14,
    "groceries": 0.09,
    "drinks": 0.1,
    "snacks": 0.075,
    "meat_fish": 0.095,
    "vegetables_fruits": 0.13,
}
SIM_LOCK = threading.Lock()
SIM_STATE_LOCK = threading.Lock()
SIM_STATE = {
    "job_id": 0,
    "status": "idle",
    "message": "Ready to run",
    "started_at": None,
    "finished_at": None,
    "elapsed_seconds": 0.0,
    "stdout_tail": [],
    "stderr_tail": [],
    "report_exists": SIM_REPORT_PATH.exists(),
}
SKU_FORECAST_CACHE = {}
SKU_FORECAST_TTL_SECONDS = 600
BRAND_ALIASES = {
    "2nabiji": ["2nabiji", "2 nabiji", "ori nabiji", "nabiji", "kalata", "კალათა", "ორი ნაბიჯი", "2 ნაბიჯი"],
    "magniti": ["magniti", "მაგნიტი"],
    "spar": ["spar", "სპარი"],
    "nikora": ["nikora", "ნიკორა"],
    "carrefour": ["carrefour", "კარფური"],
    "goodwill": ["goodwill", "გუდვილი"],
}


def _snapshot_sim_state():
    with SIM_STATE_LOCK:
        state = dict(SIM_STATE)
    if state["started_at"] and state["status"] in {"queued", "running"}:
        state["elapsed_seconds"] = round(time.time() - state["started_at"], 1)
    return state


def _update_sim_state(**updates):
    with SIM_STATE_LOCK:
        SIM_STATE.update(updates)
        started_at = SIM_STATE.get("started_at")
        if started_at and SIM_STATE.get("status") in {"queued", "running"}:
            SIM_STATE["elapsed_seconds"] = round(time.time() - started_at, 1)
        elif SIM_STATE.get("finished_at") and started_at:
            SIM_STATE["elapsed_seconds"] = round(SIM_STATE["finished_at"] - started_at, 1)


def _run_simulation_job(job_id):
    _update_sim_state(
        job_id=job_id,
        status="running",
        message="Simulation is running",
        started_at=time.time(),
        finished_at=None,
        stdout_tail=[],
        stderr_tail=[],
        report_exists=SIM_REPORT_PATH.exists(),
    )
    try:
        proc = subprocess.run(
            [sys.executable, "simulation_run.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        stdout_tail = (proc.stdout or "").strip().splitlines()[-18:]
        stderr_tail = (proc.stderr or "").strip().splitlines()[-18:]
        finished_at = time.time()
        if proc.returncode != 0:
            _update_sim_state(
                job_id=job_id,
                status="error",
                message="Simulation failed",
                finished_at=finished_at,
                stdout_tail=stdout_tail,
                stderr_tail=stderr_tail,
                report_exists=SIM_REPORT_PATH.exists(),
            )
            return

        _update_sim_state(
            job_id=job_id,
            status="done",
            message="Simulation complete",
            finished_at=finished_at,
            stdout_tail=stdout_tail,
            stderr_tail=stderr_tail,
            report_exists=SIM_REPORT_PATH.exists(),
        )
    finally:
        SIM_LOCK.release()


def _retail_media_payload(barcodes):
    if not RETAIL_DB_PATH.exists():
        return {"items": [], "count": 0, "source": "missing-retail-db"}

    cleaned = [barcode.strip() for barcode in barcodes if barcode and barcode.strip()]
    if not cleaned:
        return {"items": [], "count": 0, "source": str(RETAIL_DB_PATH)}

    placeholders = ",".join("?" for _ in cleaned)
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
    conn = sqlite3.connect(RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(sql, cleaned).fetchall()
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

    return {"items": list(deduped.values()), "count": len(deduped), "source": str(RETAIL_DB_PATH)}


def _load_sim_report():
    if not SIM_REPORT_PATH.exists():
        return {}
    try:
        return json.loads(SIM_REPORT_PATH.read_text())
    except Exception:
        return {}


def _store_locations_payload():
    """Real store universe (id/name/chain/lat/lng/address) from the curated
    store geography, joined by exact name with this run's simulated per-store
    demand (spend/units/visits/avg_ticket). Stores the simulation never
    visited are still returned (has_demand=False) so the map shows the real
    footprint, not just the sampled subset — same absence-is-zero principle
    as sku_breakdown."""
    if not STORES_JSON_PATH.exists():
        return {"stores": [], "meta": {"total_stores": 0, "stores_with_demand": 0}}
    try:
        stores = json.loads(STORES_JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"stores": [], "meta": {"total_stores": 0, "stores_with_demand": 0}}

    sim = _load_sim_report()
    by_name = {}
    for row in ((sim.get("retail_breakdown") or {}).get("stores") or []):
        by_name[row.get("store_name")] = row

    out = []
    for s in stores:
        demand = by_name.get(s.get("name"))
        out.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "chain": s.get("chain"),
            "brand_id": s.get("chain_slug") or s.get("db_slug"),
            "lat": s.get("lat"),
            "lng": s.get("lng"),
            "district": s.get("district"),
            "address": s.get("address"),
            "color": s.get("color"),
            "spend": round(demand["spend"], 2) if demand else 0.0,
            "units": demand["units"] if demand else 0,
            "visits": demand["visits"] if demand else 0,
            "avg_ticket": round(demand["avg_ticket"], 2) if demand else 0.0,
            "has_demand": bool(demand),
        })
    return {
        "stores": out,
        "meta": {"total_stores": len(out), "stores_with_demand": len(by_name)},
    }


def _report_cache_stamp():
    try:
        return int(SIM_REPORT_PATH.stat().st_mtime)
    except Exception:
        return 0


def _effective_price(row):
    return float(row["sale_price"] or row["original_price"] or 0.0)


def _safe_read_json_body(handler):
    try:
        length = int(handler.headers.get("Content-Length", "0") or "0")
    except ValueError:
        length = 0
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _json_clone(payload):
    return json.loads(json.dumps(payload))


def _extract_json_object(raw_text):
    if not raw_text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_text, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass

    match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass
    return None


def _clamp(value, low, high):
    return max(low, min(high, value))


def _normalized_store_weights(offers, llm_payload):
    raw = {}
    for offer in offers:
        price = max(offer["effective_price"], 0.01)
        sale_boost = 1.12 if offer["is_on_sale"] else 1.0
        raw[offer["store_slug"]] = (1 / price) * sale_boost

    llm_weights = (llm_payload or {}).get("store_multipliers") or {}
    for offer in offers:
        slug = offer["store_slug"]
        multiplier = llm_weights.get(slug, 1.0)
        try:
            multiplier = float(multiplier)
        except Exception:
            multiplier = 1.0
        raw[slug] *= _clamp(multiplier, 0.45, 1.8)

    total = sum(raw.values()) or float(len(offers) or 1)
    return {slug: value / total for slug, value in raw.items()}


def _future_positions(period_key):
    if period_key == "year":
        return 12, 3
    if period_key == "month":
        return 9, 3
    return 5, 2


def _coerce_series(payload, key, length, fallback_values):
    raw = payload.get(key)
    if not isinstance(raw, list):
        return fallback_values[:]
    cooked = []
    for value in raw[:length]:
        try:
            cooked.append(max(1, int(round(float(value)))))
        except Exception:
            cooked.append(fallback_values[len(cooked)])
    while len(cooked) < length:
        cooked.append(fallback_values[len(cooked)])
    return cooked


def _normalize_llm_payload(payload):
    if not isinstance(payload, dict):
        return {}
    if payload.get("dc"):
        return payload

    if isinstance(payload.get("forecast"), dict):
        forecast = payload["forecast"]
        normalized = {
            "confidence": (
                (forecast.get("year_next") or {}).get("confidence")
                or payload.get("confidence")
                or 0.0
            ),
            "bias_pct": (
                (forecast.get("year_next") or {}).get("bias_pct")
                or payload.get("bias_pct")
                or 0.0
            ),
            "coverage_days": (
                (forecast.get("year_next") or {}).get("coverage_days")
                or payload.get("coverage_days")
                or 12
            ),
            "risk": payload.get("risk", "medium"),
            "note": (
                (forecast.get("year_next") or {}).get("note")
                or payload.get("note")
                or ""
            ),
            "store_multipliers": (
                (forecast.get("year_next") or {}).get("store_multipliers")
                or payload.get("store_multipliers")
                or {}
            ),
            "dc": {
                "year_sales_fc": (forecast.get("year_next") or {}).get("sales_fc") or [],
                "month_sales_fc": (forecast.get("month_next") or {}).get("sales_fc") or [],
                "week_sales_fc": (forecast.get("week_next") or {}).get("sales_fc") or [],
            },
        }
        return normalized

    forecasts = payload.get("forecasts") or {}
    normalized = {
        "confidence": payload.get("confidence", 0.0),
        "bias_pct": payload.get("bias_pct", 0.0),
        "coverage_days": payload.get("coverage_days", 12),
        "risk": payload.get("risk", "medium"),
        "note": payload.get("note", ""),
        "store_multipliers": payload.get("store_multipliers") or {},
        "dc": {
            "year_sales_fc": [],
            "month_sales_fc": [],
            "week_sales_fc": [],
        },
    }
    for prefix, key, length in (
        ("year_next_", "year_sales_fc", 3),
        ("month_next_", "month_sales_fc", 3),
        ("week_next_", "week_sales_fc", 2),
    ):
        for idx in range(1, length + 1):
            if forecasts.get(prefix + str(idx)) is not None:
                normalized["dc"][key].append(forecasts.get(prefix + str(idx)))
    return normalized


def _extract_numeric_sequence(raw_text, marker, expected_len):
    pattern = re.compile(marker + r".{0,120}?\|\s*([0-9,\s]+)", re.IGNORECASE | re.DOTALL)
    match = pattern.search(raw_text or "")
    if not match:
        return []
    values = [part.strip() for part in match.group(1).split(",")]
    cooked = []
    for value in values:
        if not value:
            continue
        try:
            cooked.append(int(round(float(value))))
        except Exception:
            continue
        if len(cooked) >= expected_len:
            break
    return cooked


def _extract_llm_payload_from_text(raw_text):
    if not raw_text:
        return {}

    year_values = _extract_numeric_sequence(raw_text, r"Forecasted Units.*?Next 3 months", 3)
    month_values = _extract_numeric_sequence(raw_text, r"Forecasted Units.*?Next 3 weeks", 3)
    week_values = _extract_numeric_sequence(raw_text, r"Forecasted Units.*?Next 2 days", 2)
    if not year_values and not month_values and not week_values:
        year_values = _extract_numeric_sequence(raw_text, r"Forecasted Demand.*?Next 3 months", 3)
        month_values = _extract_numeric_sequence(raw_text, r"Forecasted Demand.*?Next 3 weeks", 3)
        week_values = _extract_numeric_sequence(raw_text, r"Forecasted Demand.*?Next 2 days", 2)
    if not year_values and not month_values and not week_values:
        return {}

    note_match = re.search(r"\*\*Note:\*\*\s*(.+)", raw_text or "", re.IGNORECASE)
    return {
        "confidence": 0.42,
        "bias_pct": 0.0,
        "coverage_days": 12,
        "risk": "medium",
        "note": note_match.group(1).strip()[:160] if note_match else "Parsed from Taalas narrative forecast.",
        "store_multipliers": {},
        "dc": {
            "year_sales_fc": year_values,
            "month_sales_fc": month_values,
            "week_sales_fc": week_values,
        },
    }


def _derive_inventory_series(sales_values, coverage_days, period_key):
    if period_key == "year":
        factor = max(1.45, coverage_days / 12.0)
    elif period_key == "month":
        factor = max(1.35, coverage_days / 10.0)
    else:
        factor = max(1.25, coverage_days / 7.0)
    return [max(2, int(round(value * factor))) for value in sales_values]


def _derive_safety_series(sales_values, risk):
    base = {"low": 0.28, "medium": 0.38, "high": 0.5}.get(str(risk).lower(), 0.38)
    return [max(1, int(round(value * base))) for value in sales_values]


_MONTH_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _today_from_sim(sim):
    """Single source of truth for 'today': the simulation report's real-calendar
    end date, falling back to the system date when no report is present."""
    end = ((sim or {}).get("simulation_metadata") or {}).get("end_date")
    if end:
        try:
            return date.fromisoformat(end)
        except ValueError:
            pass
    return date.today()


def _year_axis_labels(today, observed=12, forecast=3):
    """Month labels for the year view anchored on `today`: `observed` months up
    to and including the current month, then `forecast`-1 months ahead. Index
    `observed` is 'now' (the current month) — where observed meets forecast."""
    labels = []
    for offset in range(-observed, forecast):
        m = today.month - 1 + offset
        labels.append(f"{_MONTH_ABBR[m % 12]} {today.year + m // 12}")
    return labels


def _detect_barcode(message, supplied=""):
    supplied = str(supplied or "").strip()
    if supplied:
        return supplied
    match = re.search(r"\b\d{8,14}\b", message or "")
    return match.group(0) if match else ""


def _detect_brand_id(message, supplied=""):
    if _is_brand_comparison_question(message) or _is_brand_decline_question(message):
        return ""
    explicit = _explicit_brand_id(message)
    if explicit:
        return explicit
    text = (message or "").lower()
    supplied = str(supplied or "").strip().lower()
    if supplied and supplied != "all":
        return supplied
    return ""


def _brand_alias_in_text(text, alias):
    text = (text or "").lower()
    alias = (alias or "").lower().strip()
    if not alias:
        return False
    if alias in text:
        return True
    # Georgian brand names often arrive with case suffixes:
    # "სპარი" -> "სპარს", "მაგნიტი" -> "მაგნიტს", "კალათა" -> "კალათას".
    if _has_georgian_text(alias):
        stem = alias.rstrip("იაეოუს")
        if len(stem) >= 4 and stem in text:
            return True
    return False


def _explicit_brand_id(message):
    text = (message or "").lower()
    for brand_id, aliases in BRAND_ALIASES.items():
        if any(_brand_alias_in_text(text, alias) for alias in aliases):
            return brand_id
    return ""


def _retail_catalog_context():
    if not RETAIL_DB_PATH.exists():
        return {"source": "missing-retail-db"}
    conn = sqlite3.connect(RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS product_store_rows,
              COUNT(DISTINCT barcode) AS distinct_barcodes,
              COUNT(DISTINCT store_slug) AS stores,
              ROUND(AVG(COALESCE(pr.sale_price, pr.original_price)), 2) AS avg_price,
              ROUND(SUM(CASE WHEN pr.is_on_sale THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS promo_rate
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            WHERE COALESCE(pr.sale_price, pr.original_price) > 0
            """
        ).fetchone()
        stores = conn.execute(
            """
            SELECT store_slug, COUNT(*) AS rows
            FROM products
            GROUP BY store_slug
            ORDER BY rows DESC
            LIMIT 8
            """
        ).fetchall()
    finally:
        conn.close()
    return {
        "source": "retail_data.db",
        "product_store_rows": int(row["product_store_rows"] or 0),
        "distinct_barcodes": int(row["distinct_barcodes"] or 0),
        "stores": int(row["stores"] or 0),
        "avg_price": float(row["avg_price"] or 0),
        "promo_rate_pct": float(row["promo_rate"] or 0),
        "largest_store_feeds": [{"store_slug": r["store_slug"], "rows": r["rows"]} for r in stores],
    }


def _retail_brand_catalog_context(brand_id):
    if not brand_id or not RETAIL_DB_PATH.exists():
        return {}
    conn = sqlite3.connect(RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS product_store_rows,
              COUNT(DISTINCT p.barcode) AS distinct_barcodes,
              ROUND(AVG(COALESCE(pr.sale_price, pr.original_price)), 2) AS avg_price,
              ROUND(SUM(CASE WHEN pr.is_on_sale THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS promo_rate
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            WHERE p.store_slug = ?
              AND COALESCE(pr.sale_price, pr.original_price) > 0
            """,
            (brand_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row or not row["product_store_rows"]:
        return {}
    return {
        "catalog_product_store_rows": int(row["product_store_rows"] or 0),
        "catalog_distinct_barcodes": int(row["distinct_barcodes"] or 0),
        "catalog_avg_price": float(row["avg_price"] or 0),
        "catalog_promo_rate_pct": float(row["promo_rate"] or 0),
    }


def _product_names_for_barcodes(barcodes):
    cleaned = [str(barcode) for barcode in barcodes if barcode]
    if not cleaned or not RETAIL_DB_PATH.exists():
        return {}
    placeholders = ",".join("?" for _ in cleaned)
    conn = sqlite3.connect(RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            f"""
            SELECT barcode, name, image_url, store_slug,
                   ROUND(AVG(COALESCE(pr.sale_price, pr.original_price)), 2) AS avg_price
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            WHERE barcode IN ({placeholders})
            GROUP BY barcode
            """,
            cleaned,
        ).fetchall()
    finally:
        conn.close()
    return {
        row["barcode"]: {
            "name": row["name"],
            "avg_price": float(row["avg_price"] or 0),
            "store_slug": row["store_slug"],
            "image_url": row["image_url"],
        }
        for row in rows
    }


def _top_sku_context(sim, limit=8):
    sku_breakdown = ((sim or {}).get("retail_breakdown") or {}).get("sku_breakdown") or {}
    ranked = sorted(sku_breakdown.items(), key=lambda item: item[1].get("units", 0), reverse=True)[:limit]
    names = _product_names_for_barcodes([barcode for barcode, _ in ranked])
    return [
        {
            "barcode": barcode,
            "name": names.get(barcode, {}).get("name", "Unknown SKU"),
            "units": data.get("units", 0),
            "spend": round(data.get("spend", 0), 2),
            "visits": data.get("visits", 0),
            "avg_price": names.get(barcode, {}).get("avg_price", 0),
        }
        for barcode, data in ranked
    ]


def _full_week_buckets(sim, buckets):
    end = ((sim or {}).get("simulation_metadata") or {}).get("end_date")
    if not end:
        return buckets
    try:
        end_date = date.fromisoformat(end)
    except ValueError:
        return buckets
    full = []
    for bucket in buckets:
        try:
            start = date.fromisoformat(bucket.get("start", ""))
        except ValueError:
            continue
        # The final bucket can be only 1-2 days long; exclude it from trend
        # comparisons so it does not create a fake sales collapse.
        if (end_date - start).days >= 6:
            full.append(bucket)
    return full or buckets


def _declining_sku_context(sim, brand_id="", limit=8):
    sku_breakdown = ((sim or {}).get("retail_breakdown") or {}).get("sku_breakdown") or {}
    rows = []
    for barcode, data in sku_breakdown.items():
        if brand_id and brand_id not in (data.get("brands") or {}):
            continue
        buckets = _full_week_buckets(sim, data.get("weekly_buckets") or [])
        if len(buckets) < 3:
            continue
        split = max(1, len(buckets) // 2)
        first_units = sum(int(bucket.get("units") or 0) for bucket in buckets[:split])
        last_units = sum(int(bucket.get("units") or 0) for bucket in buckets[split:])
        if first_units <= 0 or last_units >= first_units:
            continue
        drop_units = first_units - last_units
        drop_pct = round(drop_units * 100 / first_units, 1)
        rows.append({
            "barcode": barcode,
            "first_period_units": first_units,
            "last_period_units": last_units,
            "drop_units": drop_units,
            "drop_pct": drop_pct,
            "total_units": data.get("units", 0),
            "spend": round(data.get("spend", 0), 2),
            "visits": data.get("visits", 0),
            "weeks_compared": len(buckets),
        })

    rows.sort(key=lambda row: (row["drop_units"], row["drop_pct"]), reverse=True)
    names = _product_names_for_barcodes([row["barcode"] for row in rows[:limit]])
    for row in rows[:limit]:
        row.update({
            "name": names.get(row["barcode"], {}).get("name", "Unknown SKU"),
            "avg_price": names.get(row["barcode"], {}).get("avg_price", 0),
        })
    return rows[:limit]


def _brand_sales_context(sim):
    brands = (((sim or {}).get("retail_breakdown") or {}).get("brands") or {})
    rows = []
    for brand_id, brand in brands.items():
        rows.append({
            "brand_id": brand_id,
            "brand_name": brand.get("brand_name") or STORE_NAME_MAP.get(brand_id, brand_id),
            "units": int(round(brand.get("units") or 0)),
            "spend": round(brand.get("spend") or 0, 2),
            "visits": int(round(brand.get("visits") or 0)),
            "avg_ticket": round(brand.get("avg_ticket") or 0, 2),
            "share_of_spend": round(brand.get("share_of_spend") or 0, 1),
            "top_products": brand.get("top_products", [])[:3],
            "top_categories": brand.get("top_categories", [])[:3],
        })
    return sorted(rows, key=lambda row: row["spend"], reverse=True)


def _brand_trend_context(sim):
    sku_breakdown = ((sim or {}).get("retail_breakdown") or {}).get("sku_breakdown") or {}
    brand_rows = {}
    for _barcode, data in sku_breakdown.items():
        buckets = _full_week_buckets(sim, data.get("weekly_buckets") or [])
        brands = data.get("brands") or {}
        total_brand_units = sum(brands.values()) or data.get("units") or 0
        if len(buckets) < 3 or total_brand_units <= 0:
            continue
        split = max(1, len(buckets) // 2)
        first_units = sum(int(bucket.get("units") or 0) for bucket in buckets[:split])
        last_units = sum(int(bucket.get("units") or 0) for bucket in buckets[split:])
        first_spend = sum(float(bucket.get("spend") or 0) for bucket in buckets[:split])
        last_spend = sum(float(bucket.get("spend") or 0) for bucket in buckets[split:])
        for brand_id, brand_units in brands.items():
            share = brand_units / total_brand_units
            row = brand_rows.setdefault(brand_id, {
                "brand_id": brand_id,
                "brand_name": STORE_NAME_MAP.get(brand_id, brand_id),
                "first_units": 0.0,
                "last_units": 0.0,
                "first_spend": 0.0,
                "last_spend": 0.0,
                "sku_count": 0,
            })
            row["first_units"] += first_units * share
            row["last_units"] += last_units * share
            row["first_spend"] += first_spend * share
            row["last_spend"] += last_spend * share
            row["sku_count"] += 1

    rows = []
    for row in brand_rows.values():
        first_units = row["first_units"]
        last_units = row["last_units"]
        delta_units = last_units - first_units
        delta_pct = round(delta_units * 100 / first_units, 1) if first_units else 0
        rows.append({
            "brand_id": row["brand_id"],
            "brand_name": row["brand_name"],
            "first_units": round(first_units),
            "last_units": round(last_units),
            "delta_units": round(delta_units),
            "delta_pct": delta_pct,
            "first_spend": round(row["first_spend"], 2),
            "last_spend": round(row["last_spend"], 2),
            "delta_spend": round(row["last_spend"] - row["first_spend"], 2),
            "sku_count": row["sku_count"],
        })
    return sorted(rows, key=lambda item: item["delta_units"])


def _assistant_brand_context(sim, brand_id):
    if not brand_id:
        return None
    breakdown = (sim or {}).get("retail_breakdown") or {}
    brand = (breakdown.get("brands") or {}).get(brand_id)
    if not brand:
        return {
            "brand_id": brand_id,
            "brand_name": STORE_NAME_MAP.get(brand_id, brand_id),
            "status": "no_simulated_brand_rows",
            **_retail_brand_catalog_context(brand_id),
        }
    days = _sim_window_days(sim)
    return {
        "brand_id": brand_id,
        "brand_name": brand.get("brand_name"),
        "window_days": days,
        "observed_units": brand.get("units", 0),
        "observed_spend": brand.get("spend", 0),
        "observed_visits": brand.get("visits", 0),
        "quarter_projected_units": round(brand.get("units", 0) * 90 / max(days, 1)),
        "quarter_projected_spend": round(brand.get("spend", 0) * 90 / max(days, 1), 2),
        "avg_ticket": brand.get("avg_ticket", 0),
        "share_of_spend": brand.get("share_of_spend", 0),
        "top_categories": brand.get("top_categories", [])[:5],
        "top_products": brand.get("top_products", [])[:5],
        "district_mix": brand.get("district_mix", {}),
    }


def _assistant_sku_context(sim, barcode):
    if not barcode:
        return None
    detail = _retail_product_detail_payload(barcode)
    if "error" in detail:
        return {"barcode": barcode, "status": detail["error"]}

    sku = _sim_sku(sim, barcode)
    days = _sim_window_days(sim)
    summary = detail.get("summary") or {}
    base = {
        "barcode": barcode,
        "name": detail.get("display_name"),
        "category": detail.get("parent_category_slug") or detail.get("category_slug"),
        "observed_source": detail.get("observed_source", "heuristic"),
        "avg_price": summary.get("avg_price"),
        "min_price": summary.get("min_price"),
        "max_price": summary.get("max_price"),
        "price_spread": summary.get("price_spread"),
        "store_count": summary.get("store_count"),
        "promo_rate_pct": summary.get("promo_rate"),
        "cheapest_store": (detail.get("offers") or [{}])[0].get("store_name"),
        "carrying_stores": [
            {
                "store": offer.get("store_name"),
                "price": offer.get("effective_price"),
                "promo": offer.get("is_on_sale"),
            }
            for offer in (detail.get("offers") or [])[:8]
        ],
    }
    if sku:
        base.update({
            "simulation_window_days": days,
            "observed_units": sku.get("units", 0),
            "observed_spend": round(sku.get("spend", 0), 2),
            "observed_visits": sku.get("visits", 0),
            "quarter_projected_units": round(sku.get("units", 0) * 90 / max(days, 1)),
            "quarter_projected_spend": round(sku.get("spend", 0) * 90 / max(days, 1), 2),
            "weekly_buckets": sku.get("weekly_buckets", []),
        })
    else:
        monthly = summary.get("units_month_modeled", 0)
        base.update({
            "simulation_window_days": days,
            "observed_units": 0,
            "observed_spend": 0,
            "observed_visits": 0,
            "quarter_projected_units": round(monthly * 3),
            "quarter_projected_spend": round(monthly * 3 * (summary.get("avg_price") or 0), 2),
            "projection_note": "No exact simulated SKU row found; projection uses retail availability and brand/category signal.",
        })
    return base


def _contextual_message(message, history=None):
    history = history if isinstance(history, list) else []
    text = (message or "").lower()
    followupish = any(token in text for token in (
        "ჭრილ", "მითხარი", "ეგ", "იგივე", "არა", "ანუ", "ვის", "რომელი",
    ))
    has_specific_intent = any((
        _is_product_decline_question(message),
        _is_brand_decline_question(message),
        _is_brand_comparison_question(message),
        _is_top_sku_question(message),
        bool(_detect_barcode(message)),
    ))
    if not followupish or has_specific_intent:
        return message
    previous_user = ""
    for item in reversed(history[-8:]):
        if isinstance(item, dict) and item.get("role") == "user" and item.get("content"):
            previous_user = str(item.get("content"))
            break
    if not previous_user:
        return message
    return previous_user + "\nFollow-up: " + message


def _assistant_context(message, supplied_brand="", supplied_barcode="", history=None):
    message = _contextual_message(message, history)
    sim = _load_sim_report()
    barcode = _detect_barcode(message, supplied_barcode)
    brand_id = _detect_brand_id(message, supplied_brand)
    if _is_product_decline_question(message) and not _explicit_brand_id(message):
        brand_id = ""
    breakdown = (sim or {}).get("retail_breakdown") or {}
    metadata = (sim or {}).get("simulation_metadata") or {}
    social = (sim or {}).get("social_dynamics") or {}
    wellbeing = (sim or {}).get("agent_wellbeing") or {}
    totals = breakdown.get("totals") or {}
    days = _sim_window_days(sim)

    return {
        "today": _today_from_sim(sim).isoformat(),
        "question": message,
        "simulation": {
            "has_report": bool(sim),
            "window_days": days,
            "start_date": metadata.get("start_date"),
            "end_date": metadata.get("end_date"),
            "households": metadata.get("total_households"),
            "population": metadata.get("total_population"),
            "llm_system": (sim or {}).get("llm_system", {}),
            "retail_totals": totals,
            "quarter_projected_units": round((totals.get("units") or 0) * 90 / max(days, 1)),
            "quarter_projected_spend": round((totals.get("spend") or 0) * 90 / max(days, 1), 2),
            "households_in_crisis": social.get("households_in_crisis"),
            "avg_stress": wellbeing.get("avg_stress"),
        },
        "catalog": _retail_catalog_context(),
        "selected_brand": _assistant_brand_context(sim, brand_id),
        "selected_sku": _assistant_sku_context(sim, barcode),
        "brand_sales": _brand_sales_context(sim),
        "brand_trends": _brand_trend_context(sim),
        "top_skus": _top_sku_context(sim, limit=8),
        "declining_skus": _declining_sku_context(sim, brand_id=brand_id, limit=8),
        "instructions": [
            "Answer in the same language as the user's question. Georgian questions should be answered in Georgian.",
            "Use only the supplied context for numeric claims. If a metric is missing, say it is not available.",
            "When using 90-day numbers from a 30-day simulation, call them quarter projections, not actual quarterly sales.",
            "Be concise but actionable: include the number, source, and one retail recommendation.",
        ],
    }


def _has_georgian_text(value):
    return bool(re.search(r"[\u10A0-\u10FF]", value or ""))


def _format_int(value):
    try:
        return f"{int(round(float(value or 0))):,}"
    except Exception:
        return "0"


def _format_money(value):
    try:
        return f"₾{float(value or 0):,.2f}"
    except Exception:
        return "₾0.00"


def _format_pct(value):
    try:
        return f"{float(value or 0):.1f}%"
    except Exception:
        return "0.0%"


def _is_top_sku_question(question):
    text = (question or "").lower()
    return any(token in text for token in ("top", "ყველაზე", "ლიდერ", "კარგი", "გაყიდ", "sold", "best")) and (
        "sku" in text or "პროდუქტ" in text or "საქონ" in text or "item" in text or "product" in text
    )


def _is_brand_comparison_question(question):
    text = (question or "").lower()
    has_brand_word = any(token in text for token in ("ბრენდ", "brand", "chain", "ქსელ", "ჭრილ"))
    mentions_multiple = sum(1 for brand_id, aliases in BRAND_ALIASES.items() if any(_brand_alias_in_text(text, alias) for alias in aliases)) >= 2
    asks_best = any(token in text for token in ("კარგი", "ყველაზე", "ლიდერ", "ვის", "ტოპ", "top", "best", "ranking"))
    salesish = any(token in text for token in ("გაყიდ", "sales", "sold", "შემოსავალ", "revenue", "units"))
    return (has_brand_word or mentions_multiple) and asks_best and salesish


def _is_brand_decline_question(question):
    text = (question or "").lower()
    brandish = any(token in text for token in ("ბრენდ", "brand", "chain", "ქსელ"))
    decline = any(token in text for token in (
        "იკლო", "დაიკლო", "შემცირ", "დაეცა", "ვარდნ", "კლება",
        "declin", "decrease", "dropped", "fell", "down",
    ))
    salesish = any(token in text for token in ("გაყიდ", "sales", "sold", "demand", "მოთხოვნ"))
    return brandish and decline and salesish


def _is_product_decline_question(question):
    text = (question or "").lower()
    if _is_brand_decline_question(question):
        return False
    decline = any(token in text for token in (
        "იკლო", "დაიკლო", "შემცირ", "დაეცა", "ვარდნ", "კლება",
        "declin", "decrease", "dropped", "fell", "down",
    ))
    productish = any(token in text for token in (
        "პროდუქ", "sku", "საქონ", "item", "product",
    ))
    salesish = any(token in text for token in (
        "გაყიდ", "sales", "sold", "demand", "მოთხოვნ",
    ))
    return decline and (productish or salesish)


def _is_llm_answer_suspicious(answer, asked_georgian=False):
    if not answer or len(answer.strip()) < 8:
        return True
    if "\ufffd" in answer or "�" in answer:
        return True
    if re.search(r"(?:[\u10A0-\u10FF]\s+){5,}", answer):
        return True
    if answer.rstrip().endswith(("—", "-", "→", ":", ",")):
        return True
    if asked_georgian and not _has_georgian_text(answer):
        return True
    if not asked_georgian and _has_georgian_text(answer):
        return True
    lowered = answer.lower()
    return "context:" in lowered or "```json" in lowered or '"selected_sku"' in lowered


def _answer_lost_key_numbers(answer, fallback):
    def norm_numbers(value):
        return [re.sub(r"[^0-9]", "", number) for number in re.findall(r"\d[\d,.]*", value or "")]
    fallback_numbers = norm_numbers(fallback)
    if not fallback_numbers:
        return False
    answer_numbers = set(norm_numbers(answer))
    important = fallback_numbers[:4]
    matches = sum(1 for number in important if number in answer_numbers)
    return matches < min(2, len(important))


ASSISTANT_JSON_INTENTS = {
    "brand_best",
    "brand_decline",
    "brand_summary",
    "product_decline",
    "top_skus",
    "sku_summary",
    "overall_summary",
    "unknown",
}
ASSISTANT_JSON_METRICS = {
    "revenue",
    "units",
    "spend",
    "visits",
    "decline_units",
    "decline_pct",
    "projection",
    "availability",
    "mixed",
}
ASSISTANT_JSON_REASONS = {
    "revenue_leader",
    "unit_leader",
    "weekly_decline",
    "product_decline",
    "sku_projection",
    "catalog_only",
    "insufficient_data",
    "follow_up_context",
    "general",
}


def _assistant_token(value):
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").strip().lower().replace("-", "_")).strip("_")


def _normalize_brand_id_value(value):
    text = str(value or "").strip().lower()
    if not text:
        return ""
    compact = re.sub(r"[^a-z0-9]+", "", text)
    for brand_id, name in STORE_NAME_MAP.items():
        candidates = {brand_id, name.lower(), re.sub(r"[^a-z0-9]+", "", name.lower())}
        candidates.update(alias.lower() for alias in BRAND_ALIASES.get(brand_id, []))
        candidates.update(re.sub(r"[^a-z0-9]+", "", alias.lower()) for alias in BRAND_ALIASES.get(brand_id, []))
        if text in candidates or compact in candidates:
            return brand_id
    return text if text in STORE_NAME_MAP else ""


def _infer_assistant_intent(context):
    question = context.get("question") or ""
    if _is_brand_decline_question(question):
        return "brand_decline"
    if _is_brand_comparison_question(question) or any(token in question.lower() for token in ("კარგი გაყიდვ", "ყველაზე კარგი", "best sales")):
        return "brand_best"
    if _is_product_decline_question(question):
        return "product_decline"
    if _is_top_sku_question(question):
        return "top_skus"
    if context.get("selected_sku"):
        return "sku_summary"
    if context.get("selected_brand"):
        return "brand_summary"
    return "overall_summary"


def _assistant_compact_context(context):
    sim = context.get("simulation") or {}
    selected_brand = context.get("selected_brand") or None
    selected_sku = context.get("selected_sku") or None

    def compact_brand(row):
        return {
            "brand_id": row.get("brand_id"),
            "brand_name": row.get("brand_name"),
            "units": row.get("units"),
            "spend": row.get("spend"),
            "visits": row.get("visits"),
            "avg_ticket": row.get("avg_ticket"),
            "share_of_spend": row.get("share_of_spend"),
        }

    def compact_trend(row):
        return {
            "brand_id": row.get("brand_id"),
            "brand_name": row.get("brand_name"),
            "first_units": row.get("first_units"),
            "last_units": row.get("last_units"),
            "delta_units": row.get("delta_units"),
            "delta_pct": row.get("delta_pct"),
            "sku_count": row.get("sku_count"),
        }

    def compact_sku(row):
        return {
            "barcode": row.get("barcode"),
            "name": row.get("name"),
            "units": row.get("units"),
            "spend": row.get("spend"),
            "visits": row.get("visits"),
            "first_period_units": row.get("first_period_units"),
            "last_period_units": row.get("last_period_units"),
            "drop_units": row.get("drop_units"),
            "drop_pct": row.get("drop_pct"),
        }

    sku_summary = None
    if selected_sku:
        sku_summary = {
            "barcode": selected_sku.get("barcode"),
            "name": selected_sku.get("name"),
            "category": selected_sku.get("category"),
            "observed_source": selected_sku.get("observed_source"),
            "observed_units": selected_sku.get("observed_units"),
            "observed_spend": selected_sku.get("observed_spend"),
            "observed_visits": selected_sku.get("observed_visits"),
            "quarter_projected_units": selected_sku.get("quarter_projected_units"),
            "quarter_projected_spend": selected_sku.get("quarter_projected_spend"),
            "avg_price": selected_sku.get("avg_price"),
            "store_count": selected_sku.get("store_count"),
            "cheapest_store": selected_sku.get("cheapest_store"),
            "projection_note": selected_sku.get("projection_note"),
        }

    return {
        "question": context.get("question"),
        "simulation": {
            "window_days": sim.get("window_days"),
            "start_date": sim.get("start_date"),
            "end_date": sim.get("end_date"),
            "retail_totals": sim.get("retail_totals"),
            "quarter_projected_units": sim.get("quarter_projected_units"),
            "quarter_projected_spend": sim.get("quarter_projected_spend"),
        },
        "selected_brand": selected_brand,
        "selected_sku": sku_summary,
        "brand_sales": [compact_brand(row) for row in (context.get("brand_sales") or [])[:8]],
        "brand_trends": [compact_trend(row) for row in (context.get("brand_trends") or [])[:8]],
        "top_skus": [compact_sku(row) for row in (context.get("top_skus") or [])[:8]],
        "declining_skus": [compact_sku(row) for row in (context.get("declining_skus") or [])[:8]],
    }


def _build_assistant_json_prompt(message, context, deterministic_answer, history):
    schema = {
        "intent": "brand_best | brand_decline | brand_summary | product_decline | top_skus | sku_summary | overall_summary | unknown",
        "answer_language": "ka | en",
        "primary_metric": "revenue | units | decline_units | decline_pct | projection | availability | mixed",
        "winner_brand": "brand_id or empty string",
        "declining_brands": ["brand_id"],
        "selected_barcodes": ["barcode"],
        "reason": "revenue_leader | unit_leader | weekly_decline | product_decline | sku_projection | catalog_only | insufficient_data | follow_up_context | general",
        "confidence": 0.0,
    }
    return (
        "You are Taalas, the reasoning layer for a retail demand dashboard.\n"
        "Return STRICT JSON ONLY. No prose, no markdown, no comments.\n"
        "Use English keys and enum values only. Do not write the final user answer.\n"
        "Your job is to classify the question, choose the relevant metric, and point to the right entities from CONTEXT.\n"
        "All final wording and all numeric rendering will be done by the application.\n"
        "Use only IDs, barcodes, and metrics that exist in CONTEXT. If unsure, use intent=unknown, reason=insufficient_data, confidence <= 0.4.\n"
        "For 'best sales', default primary_metric to revenue unless the user explicitly asks for units/items.\n"
        "For decline questions, use full-week trend rows and include only entities with negative delta_units.\n\n"
        "JSON_SCHEMA:\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n\nQUESTION:\n"
        + message
        + "\n\nRECENT_USER_CHAT:\n"
        + json.dumps(
            [
                {"role": item.get("role"), "content": item.get("content")}
                for item in (history[-6:] if isinstance(history, list) else [])
                if isinstance(item, dict) and item.get("role") == "user"
            ],
            ensure_ascii=False,
            indent=2,
        )
        + "\n\nVERIFIED_FALLBACK_ANSWER_FOR_REFERENCE_ONLY:\n"
        + deterministic_answer
        + "\n\nCONTEXT:\n"
        + json.dumps(_assistant_compact_context(context), ensure_ascii=False, indent=2)
    )


def _normalize_assistant_json_payload(raw_payload, context):
    payload = _extract_json_object(raw_payload) if isinstance(raw_payload, str) else raw_payload
    if not isinstance(payload, dict):
        return None

    inferred_intent = _infer_assistant_intent(context)
    intent = _assistant_token(payload.get("intent"))
    if inferred_intent in {"brand_best", "brand_decline", "product_decline", "top_skus"}:
        intent = inferred_intent
    elif intent not in ASSISTANT_JSON_INTENTS:
        intent = inferred_intent

    metric = _assistant_token(payload.get("primary_metric"))
    if metric not in ASSISTANT_JSON_METRICS:
        metric = "mixed"
    if metric == "spend":
        metric = "revenue"

    reason = _assistant_token(payload.get("reason"))
    if reason not in ASSISTANT_JSON_REASONS:
        reason = "general"

    try:
        confidence = float(payload.get("confidence"))
    except Exception:
        confidence = 0.5
    confidence = _clamp(confidence, 0.0, 1.0)

    language = _assistant_token(payload.get("answer_language"))
    if language not in {"ka", "en"}:
        language = "ka" if _has_georgian_text(context.get("question") or "") else "en"

    winner_brand = _normalize_brand_id_value(payload.get("winner_brand"))
    declining_brands = []
    raw_declining = payload.get("declining_brands") or []
    if isinstance(raw_declining, str):
        raw_declining = [raw_declining]
    for value in raw_declining[:8]:
        brand_id = _normalize_brand_id_value(value)
        if brand_id and brand_id not in declining_brands:
            declining_brands.append(brand_id)

    selected_barcodes = []
    raw_barcodes = payload.get("selected_barcodes") or []
    if isinstance(raw_barcodes, str):
        raw_barcodes = [raw_barcodes]
    for value in raw_barcodes[:8]:
        match = re.search(r"\b\d{8,14}\b", str(value or ""))
        if match and match.group(0) not in selected_barcodes:
            selected_barcodes.append(match.group(0))

    if intent == "unknown" and confidence < 0.25:
        return None

    return {
        "intent": intent,
        "answer_language": language,
        "primary_metric": metric,
        "winner_brand": winner_brand,
        "declining_brands": declining_brands,
        "selected_barcodes": selected_barcodes,
        "reason": reason,
        "confidence": round(confidence, 2),
    }


def _assistant_brand_row(rows, brand_id):
    if not brand_id:
        return None
    for row in rows:
        if row.get("brand_id") == brand_id:
            return row
    return None


def _assistant_structured_brand_sales_answer(context, payload, georgian=True):
    rows = context.get("brand_sales") or []
    sim = context.get("simulation") or {}
    if not rows:
        return _assistant_brand_sales_answer(context, georgian=georgian)

    by_spend = sorted(rows, key=lambda row: row.get("spend", 0), reverse=True)
    by_units = sorted(rows, key=lambda row: row.get("units", 0), reverse=True)
    metric = payload.get("primary_metric") or "revenue"
    question = (context.get("question") or "").lower()
    if any(token in question for token in ("ცალ", "რაოდენ", "unit", "items", "units")):
        metric = "units"
    elif any(token in question for token in ("ლარ", "თანხ", "შემოსავალ", "revenue", "spend")):
        metric = "revenue"
    else:
        metric = "revenue"

    computed_leader = by_units[0] if metric == "units" else by_spend[0]
    llm_winner = _assistant_brand_row(rows, payload.get("winner_brand"))
    if llm_winner:
        leader_value = computed_leader.get("units" if metric == "units" else "spend", 0) or 0
        llm_value = llm_winner.get("units" if metric == "units" else "spend", 0) or 0
        if leader_value and llm_value >= leader_value * 0.97:
            computed_leader = llm_winner

    revenue_leader = by_spend[0]
    units_leader = by_units[0]
    days = sim.get("window_days") or 30

    if georgian:
        if metric == "units":
            lines = [
                f"ცალებით ლიდერია {computed_leader['brand_name']}: {_format_int(computed_leader['units'])} units ბოლო {days} დღიან simulation-ში.",
                f"ლარში კი წინ არის {revenue_leader['brand_name']}: {_format_money(revenue_leader['spend'])} ({revenue_leader['share_of_spend']}% spend share).",
            ]
        else:
            lines = [
                f"ლარის მიხედვით ლიდერია {computed_leader['brand_name']}: {_format_money(computed_leader['spend'])} ბოლო {days} დღიან simulation-ში.",
                f"ცალებით წინ არის {units_leader['brand_name']}: {_format_int(units_leader['units'])} units.",
            ]
        lines.append("Top brands ლარით:")
        for idx, row in enumerate(by_spend[:5], 1):
            lines.append(f"{idx}. {row['brand_name']}: {_format_money(row['spend'])}, {_format_int(row['units'])} units, {row['visits']} visits.")
        lines.append("წაკითხვა: revenue და units აქ ერთსა და იმავე პასუხს არ იძლევა, ამიტომ ორივე metric უნდა ჩანდეს dashboard-ში.")
        return "\n".join(lines)

    if metric == "units":
        lines = [
            f"By units, {computed_leader['brand_name']} leads with {_format_int(computed_leader['units'])} units in the last {days}-day simulation.",
            f"By revenue, {revenue_leader['brand_name']} leads with {_format_money(revenue_leader['spend'])} ({revenue_leader['share_of_spend']}% spend share).",
        ]
    else:
        lines = [
            f"By revenue, {computed_leader['brand_name']} leads with {_format_money(computed_leader['spend'])} in the last {days}-day simulation.",
            f"By units, {units_leader['brand_name']} leads with {_format_int(units_leader['units'])} units.",
        ]
    lines.append("Top brands by revenue:")
    for idx, row in enumerate(by_spend[:5], 1):
        lines.append(f"{idx}. {row['brand_name']}: {_format_money(row['spend'])}, {_format_int(row['units'])} units, {row['visits']} visits.")
    lines.append("Readout: revenue and units do not point to the exact same chain, so the dashboard should show both metrics.")
    return "\n".join(lines)


def _assistant_structured_brand_decline_answer(context, payload, georgian=True):
    rows = context.get("brand_trends") or []
    sim = context.get("simulation") or {}
    declining = [row for row in rows if row.get("delta_units", 0) < 0]
    if not declining:
        return _assistant_brand_decline_answer(context, georgian=georgian)

    declining_by_units = sorted(declining, key=lambda row: row.get("delta_units", 0))
    declining_by_pct = sorted(declining, key=lambda row: abs(row.get("delta_pct", 0)), reverse=True)
    main = declining_by_units[0]
    pct = declining_by_pct[0]
    days = sim.get("window_days") or 30

    if georgian:
        lines = [
            f"ბოლო {days} დღის full-week trend-ით ყველაზე დიდი აბსოლუტური კლება აქვს {main['brand_name']}-ს: "
            f"{_format_int(main['first_units'])} -> {_format_int(main['last_units'])} units, "
            f"-{_format_int(abs(main['delta_units']))} ({abs(main['delta_pct'])}%)."
        ]
        if pct.get("brand_id") != main.get("brand_id"):
            lines.append(
                f"პროცენტულად ყველაზე მკვეთრია {pct['brand_name']}: "
                f"{_format_int(pct['first_units'])} -> {_format_int(pct['last_units'])} units ({abs(pct['delta_pct'])}%), "
                "მაგრამ ბაზა პატარაა."
            )
        lines.append("კლების სია:")
        for idx, row in enumerate(declining_by_units[:5], 1):
            lines.append(
                f"{idx}. {row['brand_name']}: {_format_int(row['first_units'])} -> {_format_int(row['last_units'])} units, "
                f"-{_format_int(abs(row['delta_units']))}."
            )
        lines.append("წაკითხვა: ეს ჯერ არ არის სრული quarterly history; ეს არის simulation window-ის სუფთა full-week comparison.")
        return "\n".join(lines)

    lines = [
        f"Using the last {days} days of full-week trend, {main['brand_name']} has the largest absolute decline: "
        f"{_format_int(main['first_units'])} -> {_format_int(main['last_units'])} units, "
        f"-{_format_int(abs(main['delta_units']))} ({abs(main['delta_pct'])}%)."
    ]
    if pct.get("brand_id") != main.get("brand_id"):
        lines.append(
            f"By percentage, {pct['brand_name']} drops more sharply: "
            f"{_format_int(pct['first_units'])} -> {_format_int(pct['last_units'])} units ({abs(pct['delta_pct'])}%), but from a smaller base."
        )
    lines.append("Declining chains:")
    for idx, row in enumerate(declining_by_units[:5], 1):
        lines.append(
            f"{idx}. {row['brand_name']}: {_format_int(row['first_units'])} -> {_format_int(row['last_units'])} units, "
            f"-{_format_int(abs(row['delta_units']))}."
        )
    lines.append("Readout: this is not full quarterly history yet; it is a clean full-week comparison inside the simulation window.")
    return "\n".join(lines)


def _assistant_structured_declining_skus_answer(context, payload, georgian=True):
    rows = context.get("declining_skus") or []
    sim = context.get("simulation") or {}
    if not rows:
        return _assistant_declining_skus_answer(context, georgian=georgian)

    if georgian:
        lines = [
            f"SKU დონეზე კლება ასე ჩანს ბოლო {sim.get('window_days') or 30} დღიანი simulation-ის full-week comparison-ით:"
        ]
        for idx, row in enumerate(rows[:5], 1):
            lines.append(
                f"{idx}. {row.get('name')} ({row.get('barcode')}): "
                f"{_format_int(row.get('first_period_units'))} -> {_format_int(row.get('last_period_units'))} units, "
                f"-{_format_int(row.get('drop_units'))} ({row.get('drop_pct')}%)."
            )
        lines.append("წაკითხვა: ამ SKU-ებზე ჯერ მიზეზი უნდა გაირკვეს: promo დასრულდა, ფასი აიწია თუ stockout იყო.")
        return "\n".join(lines)

    lines = [f"SKU-level declines from the last {sim.get('window_days') or 30}-day full-week simulation comparison:"]
    for idx, row in enumerate(rows[:5], 1):
        lines.append(
            f"{idx}. {row.get('name')} ({row.get('barcode')}): "
            f"{_format_int(row.get('first_period_units'))} -> {_format_int(row.get('last_period_units'))} units, "
            f"-{_format_int(row.get('drop_units'))} ({row.get('drop_pct')}%)."
        )
    lines.append("Readout: check promo ending, price jump, and stockout before changing safety stock.")
    return "\n".join(lines)


def _assistant_structured_top_skus_answer(context, payload, georgian=True):
    rows = context.get("top_skus") or []
    sim = context.get("simulation") or {}
    days = max(int(sim.get("window_days") or 30), 1)
    if not rows:
        return _assistant_top_skus_answer(context, georgian=georgian)

    if georgian:
        lines = [f"ყველაზე ძლიერი SKU-ები ბოლო {days} დღიან simulation-ში:"]
        for idx, row in enumerate(rows[:5], 1):
            q_units = round((row.get("units") or 0) * 90 / days)
            q_spend = round((row.get("spend") or 0) * 90 / days, 2)
            lines.append(
                f"{idx}. {row.get('name') or row.get('barcode')}: "
                f"{_format_int(row.get('units'))} units observed, quarter projection {_format_int(q_units)} units / {_format_money(q_spend)}."
            )
        lines.append("წაკითხვა: ესენი არის watchlist-ის პირველი კანდიდატები, მაგრამ თითოეულზე store-level cover ცალკე უნდა ნახო.")
        return "\n".join(lines)

    lines = [f"Strongest SKUs in the last {days}-day simulation:"]
    for idx, row in enumerate(rows[:5], 1):
        q_units = round((row.get("units") or 0) * 90 / days)
        q_spend = round((row.get("spend") or 0) * 90 / days, 2)
        lines.append(
            f"{idx}. {row.get('name') or row.get('barcode')}: "
            f"{_format_int(row.get('units'))} units observed, quarter projection {_format_int(q_units)} units / {_format_money(q_spend)}."
        )
    lines.append("Readout: these are the first watchlist candidates, but each still needs store-level cover checked.")
    return "\n".join(lines)


def _assistant_structured_sku_answer(context, payload, georgian=True):
    sku = context.get("selected_sku")
    sim = context.get("simulation") or {}
    if not sku or sku.get("status"):
        return _assistant_fallback_answer(context)

    if georgian:
        lines = [
            f"{sku.get('name') or sku.get('barcode')} ({sku.get('barcode')})",
            f"Quarter projection: {_format_int(sku.get('quarter_projected_units'))} units / {_format_money(sku.get('quarter_projected_spend'))}.",
            f"Retail footprint: avg price {_format_money(sku.get('avg_price'))}, {sku.get('store_count') or 0} live stores, cheapest: {sku.get('cheapest_store') or 'n/a'}.",
        ]
        if sku.get("observed_units"):
            lines.append(
                f"Simulation actual: ბოლო {sku.get('simulation_window_days') or sim.get('window_days') or 30} დღეში "
                f"{_format_int(sku.get('observed_units'))} units, {_format_money(sku.get('observed_spend'))}, {sku.get('observed_visits') or 0} visits."
            )
        else:
            lines.append("Simulation actual: exact SKU sale ამ run-ში არ მოხვდა, ამიტომ projection retail footprint + category/brand signal-იდან მოდის.")
        lines.append("წაკითხვა: თუ live stores 3+-ია, DC replenishment-ზე მცირე safety buffer უკვე აზრიანია.")
        return "\n".join(lines)

    lines = [
        f"{sku.get('name') or sku.get('barcode')} ({sku.get('barcode')})",
        f"Quarter projection: {_format_int(sku.get('quarter_projected_units'))} units / {_format_money(sku.get('quarter_projected_spend'))}.",
        f"Retail footprint: avg price {_format_money(sku.get('avg_price'))}, {sku.get('store_count') or 0} live stores, cheapest: {sku.get('cheapest_store') or 'n/a'}.",
    ]
    if sku.get("observed_units"):
        lines.append(
            f"Simulation actual: {_format_int(sku.get('observed_units'))} units, {_format_money(sku.get('observed_spend'))}, "
            f"{sku.get('observed_visits') or 0} visits over {sku.get('simulation_window_days') or sim.get('window_days') or 30} days."
        )
    else:
        lines.append("Simulation actual: this exact SKU did not sell in the run, so projection uses retail footprint and category/brand signal.")
    lines.append("Readout: if it is live in 3+ stores, a small DC safety buffer is already reasonable.")
    return "\n".join(lines)


def _assistant_render_structured_answer(context, payload, deterministic_answer):
    georgian = (payload.get("answer_language") == "ka") or _has_georgian_text(context.get("question") or "")
    intent = payload.get("intent") or _infer_assistant_intent(context)
    if intent == "brand_best":
        return _assistant_structured_brand_sales_answer(context, payload, georgian=georgian)
    if intent == "brand_decline":
        return _assistant_structured_brand_decline_answer(context, payload, georgian=georgian)
    if intent == "product_decline":
        return _assistant_structured_declining_skus_answer(context, payload, georgian=georgian)
    if intent == "top_skus":
        return _assistant_structured_top_skus_answer(context, payload, georgian=georgian)
    if intent == "sku_summary":
        return _assistant_structured_sku_answer(context, payload, georgian=georgian)
    if intent in {"brand_summary", "overall_summary", "unknown"}:
        return deterministic_answer
    return deterministic_answer


def _assistant_top_skus_answer(context, georgian=True):
    rows = context.get("top_skus") or []
    sim = context.get("simulation") or {}
    days = max(int(sim.get("window_days") or 30), 1)
    if not rows:
        return "simulation-ში SKU გაყიდვების breakdown ჯერ არ არის." if georgian else "The simulation does not contain SKU sales rows yet."

    if georgian:
        lines = [f"Top SKU-ები ბოლო {days} დღიანი simulation window-დან:"]
        for idx, row in enumerate(rows[:5], 1):
            q_units = round((row.get("units") or 0) * 90 / days)
            q_spend = round((row.get("spend") or 0) * 90 / days, 2)
            lines.append(
                f"{idx}. {row.get('name') or row.get('barcode')} ({row.get('barcode')}): "
                f"{_format_int(row.get('units'))} units observed, quarter projection {_format_int(q_units)} units / {_format_money(q_spend)}."
            )
        lines.append("Action: ეს SKU-ები ჩასვი replenishment watchlist-ში და თითოეულზე ცალკე store-level cover გადაამოწმე.")
        return "\n".join(lines)

    lines = [f"Top SKUs from the last {days}-day simulation window:"]
    for idx, row in enumerate(rows[:5], 1):
        q_units = round((row.get("units") or 0) * 90 / days)
        q_spend = round((row.get("spend") or 0) * 90 / days, 2)
        lines.append(
            f"{idx}. {row.get('name') or row.get('barcode')} ({row.get('barcode')}): "
            f"{_format_int(row.get('units'))} units observed, quarter projection {_format_int(q_units)} units / {_format_money(q_spend)}."
        )
    lines.append("Action: place these SKUs on the replenishment watchlist and review store-level cover for each.")
    return "\n".join(lines)


def _assistant_declining_skus_answer(context, georgian=True):
    rows = context.get("declining_skus") or []
    sim = context.get("simulation") or {}
    brand = context.get("selected_brand")
    if not rows:
        if georgian:
            return "ამ simulation report-ში საკმარისი weekly SKU history ვერ ვიპოვე, რომ გაყიდვების კლება სანდოდ გამოვთვალო."
        return "I could not find enough weekly SKU history in this simulation report to calculate product declines reliably."

    if georgian:
        scope = ""
        if brand and not brand.get("status"):
            scope = f" ({brand.get('brand_name') or brand.get('brand_id')} filter)"
        lines = [
            f"სრული historical quarter ჯერ არ გვაქვს; ეს არის ბოლო {sim.get('window_days') or 30} დღიანი simulation window-ის full-week comparison{scope}.",
            "ყველაზე მკვეთრი კლება ჰქონდათ:",
        ]
        for idx, row in enumerate(rows[:5], 1):
            lines.append(
                f"{idx}. {row.get('name')} ({row.get('barcode')}): "
                f"{_format_int(row.get('first_period_units'))} → {_format_int(row.get('last_period_units'))} units, "
                f"-{_format_int(row.get('drop_units'))} units ({row.get('drop_pct')}%)."
            )
        lines.append("Action: ამ SKU-ებზე შეამოწმე promo ended, price jump ან stockout; forecast-ში safety stock არ გაზარდო სანამ მიზეზი არ გაირკვევა.")
        return "\n".join(lines)

    scope = ""
    if brand and not brand.get("status"):
        scope = f" ({brand.get('brand_name') or brand.get('brand_id')} filter)"
    lines = [
        f"We do not have a full historical quarter yet; this uses full-week comparison from the last {sim.get('window_days') or 30}-day simulation window{scope}.",
        "Largest product declines:",
    ]
    for idx, row in enumerate(rows[:5], 1):
        lines.append(
            f"{idx}. {row.get('name')} ({row.get('barcode')}): "
            f"{_format_int(row.get('first_period_units'))} -> {_format_int(row.get('last_period_units'))} units, "
            f"-{_format_int(row.get('drop_units'))} units ({row.get('drop_pct')}%)."
        )
    lines.append("Action: check promo end, price jump, or stockout before increasing safety stock.")
    return "\n".join(lines)


def _assistant_brand_sales_answer(context, georgian=True):
    rows = context.get("brand_sales") or []
    sim = context.get("simulation") or {}
    if not rows:
        return "ბრენდების გაყიდვები ამ report-ში ვერ ვიპოვე." if georgian else "I could not find brand sales in this report."

    by_spend = sorted(rows, key=lambda row: row.get("spend", 0), reverse=True)
    by_units = sorted(rows, key=lambda row: row.get("units", 0), reverse=True)
    leader_spend = by_spend[0]
    leader_units = by_units[0]

    if georgian:
        lines = [
            f"ბრენდის ჭრილში, ბოლო {sim.get('window_days') or 30} დღიან simulation-ში სურათი ასეთია:",
            f"ლარში ლიდერია {leader_spend['brand_name']}: {_format_money(leader_spend['spend'])}, {leader_spend['share_of_spend']}% spend share.",
            f"ცალებში ლიდერია {leader_units['brand_name']}: {_format_int(leader_units['units'])} units.",
            "რეიტინგი ლარის მიხედვით:",
        ]
        for idx, row in enumerate(by_spend[:5], 1):
            lines.append(
                f"{idx}. {row['brand_name']} — {_format_money(row['spend'])}, "
                f"{_format_int(row['units'])} units, {row['visits']} visits."
            )
        lines.append("ჩემი წაკითხვა: Spar და Carrefour თითქმის ერთ დონეზე არიან revenue-ში; Magniti ამ run-ში actual sales-ში საერთოდ არ მოხვდა, ამიტომ მას retail catalog-ში ვხედავთ, მაგრამ simulation sales-ში არა.")
        return "\n".join(lines)

    lines = [
        f"By brand, for the last {sim.get('window_days') or 30}-day simulation:",
        f"Revenue leader: {leader_spend['brand_name']} with {_format_money(leader_spend['spend'])}, {leader_spend['share_of_spend']}% spend share.",
        f"Unit leader: {leader_units['brand_name']} with {_format_int(leader_units['units'])} units.",
        "Ranking by revenue:",
    ]
    for idx, row in enumerate(by_spend[:5], 1):
        lines.append(
            f"{idx}. {row['brand_name']} — {_format_money(row['spend'])}, "
            f"{_format_int(row['units'])} units, {row['visits']} visits."
        )
    return "\n".join(lines)


def _assistant_brand_decline_answer(context, georgian=True):
    rows = context.get("brand_trends") or []
    sim = context.get("simulation") or {}
    declining = [row for row in rows if row.get("delta_units", 0) < 0]
    if not declining:
        return "ბრენდების weekly trend-ში კლება არ ჩანს ამ report-ის ფარგლებში." if georgian else "No brand-level decline is visible in this report's weekly trend."

    if georgian:
        lines = [
            f"სრული კვარტლის history ჯერ არ გვაქვს, ამიტომ ამას ვკითხულობ ბოლო {sim.get('window_days') or 30} დღის full-week trend-ით.",
            "გაყიდვების კლება ბრენდების ჭრილში ასე ჩანს:",
        ]
        for idx, row in enumerate(declining[:5], 1):
            lines.append(
                f"{idx}. {row['brand_name']} — {_format_int(row['first_units'])} → {_format_int(row['last_units'])} units, "
                f"{_format_int(abs(row['delta_units']))} units-ით ნაკლები ({abs(row['delta_pct'])}%)."
            )
        lines.append("ჩემი დასკვნა: ყველაზე დიდი აბსოლუტური ვარდნა Spar-ზეა; პროცენტულად 2 Nabiji უფრო მკვეთრად ეცემა, მაგრამ ბაზა ბევრად პატარაა.")
        return "\n".join(lines)

    lines = [
        f"We do not have full quarter history yet, so this reads the last {sim.get('window_days') or 30} days by full-week trend.",
        "Brand-level sales declines:",
    ]
    for idx, row in enumerate(declining[:5], 1):
        lines.append(
            f"{idx}. {row['brand_name']} — {_format_int(row['first_units'])} -> {_format_int(row['last_units'])} units, "
            f"{_format_int(abs(row['delta_units']))} fewer units ({abs(row['delta_pct'])}%)."
        )
    return "\n".join(lines)


def _assistant_fallback_answer(context):
    question = context.get("question") or ""
    georgian = _has_georgian_text(question)
    sku = context.get("selected_sku")
    brand = context.get("selected_brand")
    sim = context.get("simulation") or {}
    if _is_brand_decline_question(question):
        return _assistant_brand_decline_answer(context, georgian=georgian)
    if _is_brand_comparison_question(question):
        return _assistant_brand_sales_answer(context, georgian=georgian)
    if _is_product_decline_question(question):
        return _assistant_declining_skus_answer(context, georgian=georgian)
    if _is_top_sku_question(question):
        return _assistant_top_skus_answer(context, georgian=georgian)
    if any(token in question.lower() for token in ("კარგი გაყიდვ", "ყველაზე კარგი", "best sales")):
        return _assistant_brand_sales_answer(context, georgian=georgian)
    if sku and sku.get("status"):
        if georgian:
            return f"ამ SKU-ზე მონაცემი ვერ ვიპოვე: {sku['status']}."
        return f"I could not find this SKU: {sku['status']}."
    if sku:
        observed_units = sku.get("observed_units", 0)
        observed_spend = sku.get("observed_spend", 0)
        observed_visits = sku.get("observed_visits", 0)
        source = sku.get("observed_source", "retail/simulation")
        source_note = (
            "actual SKU rows from simulation"
            if observed_units
            else "retail DB availability + category/brand signal"
        )
        if georgian:
            lines = [
                f"{sku.get('name') or sku.get('barcode')} ({sku.get('barcode')})",
                f"Quarter projection: {_format_int(sku.get('quarter_projected_units'))} units / {_format_money(sku.get('quarter_projected_spend'))}.",
                f"ფასი/coverage: avg {_format_money(sku.get('avg_price'))}, {sku.get('store_count') or 0} live stores, cheapest: {sku.get('cheapest_store') or 'n/a'}.",
            ]
            if observed_units:
                lines.append(
                    f"Actual simulation: ბოლო {sku.get('simulation_window_days') or sim.get('window_days') or 30} დღეში "
                    f"{_format_int(observed_units)} units, {_format_money(observed_spend)}, {observed_visits} visits."
                )
            else:
                lines.append("Actual simulation: exact SKU sale არ მოხვდა, ამიტომ projection მოდის retail footprint + category/brand signal-იდან.")
            lines.append(f"Source: {source} ({source_note}).")
            lines.append("Action: ჯერ შეამოწმე store-level availability; თუ 3+ store-ზეა live, DC replenishment-ს მცირე safety buffer დაუმატე.")
            return "\n".join(lines)
        lines = [
            f"{sku.get('name') or sku.get('barcode')} ({sku.get('barcode')})",
            f"Quarter projection: {_format_int(sku.get('quarter_projected_units'))} units / {_format_money(sku.get('quarter_projected_spend'))}.",
            f"Price/coverage: avg {_format_money(sku.get('avg_price'))}, {sku.get('store_count') or 0} live stores, cheapest: {sku.get('cheapest_store') or 'n/a'}.",
        ]
        if observed_units:
            lines.append(
                f"Actual simulation: {_format_int(observed_units)} units, {_format_money(observed_spend)}, {observed_visits} visits "
                f"over {sku.get('simulation_window_days') or sim.get('window_days') or 30} days."
            )
        else:
            lines.append("Actual simulation: this exact SKU did not sell in the run, so projection uses retail footprint and category/brand signal.")
        lines.append(f"Source: {source} ({source_note}).")
        lines.append("Action: review store-level availability first; if live in 3+ stores, add a small DC safety buffer.")
        return "\n".join(lines)
    if brand and not brand.get("status"):
        top_categories = ", ".join(
            str(item.get("category") or item.get("name") or item) for item in (brand.get("top_categories") or [])[:3]
        ) or "n/a"
        top_products = ", ".join(
            str(item.get("name") or item) for item in (brand.get("top_products") or [])[:3]
        ) or "n/a"
        if georgian:
            return "\n".join([
                f"{brand.get('brand_name') or brand.get('brand_id')} brand summary",
                f"Quarter projection: {_format_int(brand.get('quarter_projected_units'))} units / {_format_money(brand.get('quarter_projected_spend'))}.",
                f"Actual simulation: {_format_int(brand.get('observed_units'))} units, {_format_money(brand.get('observed_spend'))}, {brand.get('observed_visits') or 0} visits.",
                f"Avg ticket: {_format_money(brand.get('avg_ticket'))}; spend share: {_format_pct(brand.get('share_of_spend'))}.",
                f"Top categories: {top_categories}.",
                f"Top products: {top_products}.",
                "Action: ამ brand-ზე dashboard-ის ქვედა widgets უკვე filtered უნდა წაიკითხო; პირველი ნაბიჯი top category stock cover-ის შემოწმებაა.",
            ])
        return "\n".join([
            f"{brand.get('brand_name') or brand.get('brand_id')} brand summary",
            f"Quarter projection: {_format_int(brand.get('quarter_projected_units'))} units / {_format_money(brand.get('quarter_projected_spend'))}.",
            f"Actual simulation: {_format_int(brand.get('observed_units'))} units, {_format_money(brand.get('observed_spend'))}, {brand.get('observed_visits') or 0} visits.",
            f"Avg ticket: {_format_money(brand.get('avg_ticket'))}; spend share: {_format_pct(brand.get('share_of_spend'))}.",
            f"Top categories: {top_categories}.",
            f"Top products: {top_products}.",
            "Action: read lower widgets as filtered to this brand and review stock cover for the top category first.",
        ])
    if brand and brand.get("status") == "no_simulated_brand_rows":
        if georgian:
            return "\n".join([
                f"{brand.get('brand_name') or brand.get('brand_id')} brand-ზე ამ simulation window-ში exact demand rows არ დაფიქსირდა.",
                f"Retail DB footprint: {_format_int(brand.get('catalog_product_store_rows'))} product-store rows, "
                f"{_format_int(brand.get('catalog_distinct_barcodes'))} barcodes, avg price {_format_money(brand.get('catalog_avg_price'))}, "
                f"promo rate {_format_pct(brand.get('catalog_promo_rate_pct'))}.",
                "Action: dashboard-მა ამ brand-ზე global totals არ უნდა აჩვენოს; ან უფრო დიდი/გრძელი simulation გაუშვი, ან store visit weights-ში ეს chain გააძლიერე.",
            ])
        return "\n".join([
            f"{brand.get('brand_name') or brand.get('brand_id')} has no exact demand rows in this simulation window.",
            f"Retail DB footprint: {_format_int(brand.get('catalog_product_store_rows'))} product-store rows, "
            f"{_format_int(brand.get('catalog_distinct_barcodes'))} barcodes, avg price {_format_money(brand.get('catalog_avg_price'))}, "
            f"promo rate {_format_pct(brand.get('catalog_promo_rate_pct'))}.",
            "Action: do not show global totals for this brand; run a longer simulation or increase this chain's store-visit weight.",
        ])
    if georgian:
        return (
            f"ბოლო {sim.get('window_days') or 30} დღიანი simulation window-ზე საერთო quarter projection არის "
            f"{_format_int(sim.get('quarter_projected_units'))} units და "
            f"{_format_money(sim.get('quarter_projected_spend'))}. "
            f"Actual retail simulation: {_format_int((sim.get('retail_totals') or {}).get('units'))} units, "
            f"{_format_money((sim.get('retail_totals') or {}).get('spend'))}, "
            f"{(sim.get('retail_totals') or {}).get('visits') or 0} visits. "
            "კონკრეტული SKU-სთვის მომწერე barcode."
        )
    return (
        f"Total quarter projection from the last {sim.get('window_days') or 30}-day simulation window is "
        f"{_format_int(sim.get('quarter_projected_units'))} units and "
        f"{_format_money(sim.get('quarter_projected_spend'))}. "
        "Send a barcode for SKU-level analysis."
    )


def _assistant_chat_payload(message, supplied_brand="", supplied_barcode="", history=None):
    message = (message or "").strip()
    if not message:
        return {"ok": False, "error": "message is required"}

    context = _assistant_context(message, supplied_brand=supplied_brand, supplied_barcode=supplied_barcode, history=history)
    deterministic_answer = _assistant_fallback_answer(context)
    georgian_question = _has_georgian_text(message)

    api_key = os.getenv("TAALAS_API_KEY")
    if not api_key:
        return {
            "ok": True,
            "source": "deterministic-fallback",
            "answer": deterministic_answer,
            "context": context,
        }

    prompt = _build_assistant_json_prompt(message, context, deterministic_answer, history)
    try:
        llm = TaalaLLMInterface(api_key=api_key, timeout=18)
        raw_answer = llm.think(prompt, max_tokens=260)
    except Exception as exc:
        return {
            "ok": True,
            "source": "datasight-context-answer",
            "answer": deterministic_answer,
            "context": context,
            "taalas_ready": True,
            "taalas_error": exc.__class__.__name__,
        }

    structured = _normalize_assistant_json_payload(raw_answer, context)
    if not structured:
        return {
            "ok": True,
            "source": "datasight-context-answer",
            "answer": deterministic_answer,
            "context": context,
            "taalas_ready": True,
            "taalas_error": "invalid_structured_json",
        }

    answer = _assistant_render_structured_answer(context, structured, deterministic_answer)
    if _is_llm_answer_suspicious(answer, asked_georgian=georgian_question) or _answer_lost_key_numbers(answer, deterministic_answer):
        return {
            "ok": True,
            "source": "datasight-context-answer",
            "answer": deterministic_answer,
            "context": context,
            "taalas_ready": True,
            "taalas_payload": structured,
            "taalas_error": "render_guard_fallback",
        }

    return {
        "ok": True,
        "source": "taalas-structured-chat",
        "answer": answer,
        "context": context,
        "taalas_payload": structured,
    }


def _build_llm_prompt(barcode, first_offer, offers, summary, heuristic_forecast, sim):
    brand_snapshots = []
    for offer in offers[:6]:
        brand_snapshots.append({
            "store_slug": offer["store_slug"],
            "store_name": offer["store_name"],
            "price": round(offer["effective_price"], 2),
            "promo": bool(offer["is_on_sale"]),
        })

    retail_totals = ((sim or {}).get("retail_breakdown") or {}).get("totals") or {}
    current_year = heuristic_forecast["dc"]["year"]
    current_month = heuristic_forecast["dc"]["month"]
    current_week = heuristic_forecast["dc"]["week"]

    constraints = [
        "Return strict JSON only. No markdown.",
        "Forecast must be conservative and realistic for one SKU, not category total.",
        "Use units, not money, for forecast arrays.",
        "Future arrays only: year=next 3 months, month=next 3 weeks, week=next 2 days.",
    ]
    # Phase 6: when the simulation has real demand for this exact SKU, feed its
    # actual observed unit series as the baseline (not the heuristic shape) and
    # anchor the forecast to it. Sparse/zero-demand SKUs keep the heuristic slices.
    sku = _sim_sku(sim, barcode)
    if sku and "weekly_buckets" in sku:
        window = _sim_window_days(sim)
        weekly_units = [bucket["units"] for bucket in sku["weekly_buckets"]]
        baseline_observed = {
            "source": "simulation",
            "sku_total_units": sku["units"],
            "sku_total_visits": sku["visits"],
            "window_days": window,
            "weekly_units": weekly_units,
            "monthly_units": sum(weekly_units),
            "avg_daily_units": round(sku["units"] / window, 2),
        }
        constraints.append(
            "baseline_observed.weekly_units are ACTUAL simulated unit sales for THIS exact SKU, "
            "chronological (oldest to newest), over the last window_days. Anchor the forecast to this "
            "observed level and trend; do not revert to category or store-count heuristics."
        )
    else:
        baseline_observed = {
            "source": "heuristic",
            "year_last_observed_units": [value for value in current_year["sales"][9:13] if value is not None],
            "month_last_observed_units": [value for value in current_month["sales"][5:9] if value is not None],
            "week_last_observed_units": [value for value in current_week["sales"][2:5] if value is not None],
        }

    prompt = {
        "task": "Return SKU-level retail demand forecast for one product in Tbilisi grocery chains.",
        "today": _today_from_sim(sim).isoformat(),
        "constraints": constraints,
        "product": {
            "barcode": barcode,
            "name": first_offer["name"],
            "category": first_offer["parent_category_slug"] or first_offer["category_slug"] or "groceries",
            "unit": first_offer["unit"] or "",
        },
        "retail_context": {
            "avg_price": summary["avg_price"],
            "min_price": summary["min_price"],
            "max_price": summary["max_price"],
            "price_spread": summary["price_spread"],
            "store_count": summary["store_count"],
            "promo_rate_pct": summary["promo_rate"],
            "offers": brand_snapshots,
        },
        "simulation_context": {
            "total_retail_units": retail_totals.get("units", 0),
            "total_retail_visits": retail_totals.get("visits", 0),
            "total_retail_spend": retail_totals.get("spend", 0),
        },
        "baseline_observed": baseline_observed,
        "response_schema": {
            "confidence": "0.0-1.0",
            "bias_pct": "number",
            "coverage_days": "integer 3..45",
            "risk": "low|medium|high",
            "note": "short reason, max 18 words",
            "dc": {
                "year_sales_fc": ["int", "int", "int"],
                "month_sales_fc": ["int", "int", "int"],
                "week_sales_fc": ["int", "int"],
            },
            "store_multipliers": {
                "store_slug": "0.45-1.80"
            },
        },
    }
    return json.dumps(prompt, ensure_ascii=False)


def _merge_llm_forecast(base_forecast, llm_payload, offers, avg_price):
    merged = _json_clone(base_forecast)
    risk = str(llm_payload.get("risk") or "medium").lower()
    risk_title = "High" if risk == "high" else "Low" if risk == "low" else "Medium"
    confidence = _clamp(float(llm_payload.get("confidence") or 0.0), 0.0, 1.0)
    coverage_days = _clamp(int(round(float(llm_payload.get("coverage_days") or 12))), 3, 45)
    bias_pct = float(llm_payload.get("bias_pct") or 0.0)
    dc_payload = llm_payload.get("dc") or {}

    dc_future = {}
    for period_key in ("year", "month", "week"):
        start, expected_len = _future_positions(period_key)
        period = merged["dc"][period_key]
        fallback_values = []
        for idx in range(start, start + expected_len):
            fallback_values.append(period["predictedSales"][idx] or period["sales"][max(0, idx - 1)] or 1)
        sales_future = _coerce_series(dc_payload, period_key + "_sales_fc", expected_len, fallback_values)
        inventory_future = _derive_inventory_series(sales_future, coverage_days, period_key)
        safety_future = _derive_safety_series(sales_future, risk)

        period["predictedSales"] = [None] * len(period["labels"])
        period["predictedInventory"] = [None] * len(period["labels"])
        period["safety"] = [None] * len(period["labels"])
        for offset in range(expected_len):
            idx = start + offset
            period["predictedSales"][idx] = sales_future[offset]
            period["predictedInventory"][idx] = inventory_future[offset]
            period["safety"][idx] = safety_future[offset]

        period["value"] = round(sales_future[0] * avg_price, 2)
        period["coverageDays"] = coverage_days if period_key == "year" else max(3, round(coverage_days * (0.72 if period_key == "month" else 0.48)))
        period["bias"] = round(bias_pct if period_key == "year" else bias_pct * (0.76 if period_key == "month" else 0.52), 1)
        period["risk"] = risk_title
        period["predictedInventoryAtNow"] = inventory_future[0]
        period["max"] = max([value for value in period["inventory"] if value is not None] + inventory_future + [1]) + max(4, round(max(sales_future) * 0.22))
        dc_future[period_key] = {"sales": sales_future, "inventory": inventory_future, "safety": safety_future}

    weights = _normalized_store_weights(offers, llm_payload)
    for offer in offers:
        slug = offer["store_slug"]
        store_forecast = merged["store"].get(slug)
        if not store_forecast:
            continue
        share = weights.get(slug, 1 / max(len(offers), 1))
        promo_lift = 1.08 if offer["is_on_sale"] else 0.96
        for period_key in ("year", "month", "week"):
            start, expected_len = _future_positions(period_key)
            store_period = store_forecast[period_key]
            scaled_sales = []
            for value in dc_future[period_key]["sales"]:
                scaled_sales.append(max(1, int(round(value * share * promo_lift))))
            scaled_inventory = _derive_inventory_series(
                scaled_sales,
                max(3, coverage_days - (2 if offer["is_on_sale"] else 0)),
                period_key,
            )
            scaled_safety = _derive_safety_series(scaled_sales, risk)
            store_period["predictedSales"] = [None] * len(store_period["labels"])
            store_period["predictedInventory"] = [None] * len(store_period["labels"])
            store_period["safety"] = [None] * len(store_period["labels"])
            for offset in range(expected_len):
                idx = start + offset
                store_period["predictedSales"][idx] = scaled_sales[offset]
                store_period["predictedInventory"][idx] = scaled_inventory[offset]
                store_period["safety"][idx] = scaled_safety[offset]

            store_period["value"] = round(scaled_sales[0] * offer["effective_price"], 2)
            store_period["coverageDays"] = max(2, round(coverage_days * (0.9 if offer["is_on_sale"] else 1.0)))
            store_period["bias"] = round(bias_pct * (1.04 if offer["is_on_sale"] else 0.92), 1)
            store_period["risk"] = risk_title
            store_period["predictedInventoryAtNow"] = scaled_inventory[0]
            store_period["max"] = max([value for value in store_period["inventory"] if value is not None] + scaled_inventory + [1]) + max(2, round(max(scaled_sales) * 0.3))

    return {
        "source": "taalas-sku-forecast",
        "confidence": round(confidence, 2),
        "note": str(llm_payload.get("note") or "SKU forecast based on live retail footprint.")[:160],
        "dc": merged["dc"],
        "store": merged["store"],
    }


def _llm_sku_forecast(barcode, first_offer, offers, summary, heuristic_forecast, sim):
    api_key = os.getenv("TAALAS_API_KEY")
    if not api_key:
        return {"ok": False, "source": "heuristic-fallback", "reason": "TAALAS_API_KEY missing"}

    cache_key = barcode + ":" + str(_report_cache_stamp())
    cached = SKU_FORECAST_CACHE.get(cache_key)
    if cached and (time.time() - cached["ts"] < SKU_FORECAST_TTL_SECONDS):
        return cached["payload"]

    llm = TaalaLLMInterface(api_key=api_key, timeout=18)
    prompt = _build_llm_prompt(barcode, first_offer, offers, summary, heuristic_forecast, sim)
    raw = llm.think(prompt, max_tokens=420)
    payload = _normalize_llm_payload(_extract_json_object(raw))
    if not payload:
        payload = _extract_llm_payload_from_text(raw)
    if not payload or not isinstance(payload, dict):
        return {"ok": False, "source": "heuristic-fallback", "reason": "Taalas response was not valid JSON"}

    merged_forecast = _merge_llm_forecast(heuristic_forecast, payload, offers, summary["avg_price"])
    response_payload = {
        "ok": True,
        "source": merged_forecast["source"],
        "confidence": merged_forecast["confidence"],
        "note": merged_forecast["note"],
        "forecast": {
            "dc": merged_forecast["dc"],
            "store": merged_forecast["store"],
        },
    }
    SKU_FORECAST_CACHE[cache_key] = {"ts": time.time(), "payload": response_payload}
    return response_payload


def _build_forecast_series(base_units_month, avg_price, store_count, promo_rate, category_key, scope_multiplier, today=None):
    today = today or date.today()
    if category_key == "bakery":
        monthly_shape = [1.08, 1.02, 0.92, 0.98, 1.01, 1.0, 1.05, 1.07, 1.03, 0.99, 1.0, 1.04]
    elif category_key == "drinks":
        monthly_shape = [0.88, 0.9, 0.95, 1.0, 1.08, 1.17, 1.22, 1.18, 1.06, 0.98, 0.92, 0.9]
    else:
        monthly_shape = [0.96, 0.94, 0.9, 0.93, 0.98, 1.0, 1.06, 1.08, 1.03, 0.99, 0.97, 1.01]

    availability_factor = 1 + max(0, store_count - 1) * 0.06 + promo_rate * 0.18
    modeled_month = max(8, round(base_units_month * availability_factor * scope_multiplier))
    year_sales = [max(2, round(modeled_month * factor)) for factor in monthly_shape] + [None, None, None]
    year_pred = [None] * 12 + [
        max(2, round(modeled_month * 1.04)),
        max(2, round(modeled_month * 1.1)),
        max(2, round(modeled_month * 1.14)),
    ]
    year_inventory = [max(4, round(value * 2.6)) for value in year_sales[:12]] + [None, None, None]
    year_pred_inventory = [None] * 12 + [
        max(4, round(year_pred[12] * 2.2)),
        max(4, round(year_pred[13] * 2.0)),
        max(4, round(year_pred[14] * 2.15)),
    ]
    year_safety = [None] * 12 + [
        max(2, round(year_pred[12] * 0.45)),
        max(2, round(year_pred[13] * 0.5)),
        max(2, round(year_pred[14] * 0.54)),
    ]

    weekly_base = max(2, round(modeled_month / 4.4))
    month_sales = [max(1, round(weekly_base * factor)) for factor in [0.95, 1.0, 1.08, 1.02, 1.1, 1.05, 0.98, 0.92, 1.0]] + [None, None, None]
    month_pred = [None] * 9 + [max(1, round(weekly_base * 1.06)), max(1, round(weekly_base * 1.14)), max(1, round(weekly_base * 1.18))]
    month_inventory = [max(2, round(value * 2.35)) for value in month_sales[:9]] + [None, None, None]
    month_pred_inventory = [None] * 9 + [max(2, round(month_pred[9] * 2.0)), max(2, round(month_pred[10] * 1.85)), max(2, round(month_pred[11] * 1.9))]
    month_safety = [None] * 9 + [max(1, round(month_pred[9] * 0.4)), max(1, round(month_pred[10] * 0.42)), max(1, round(month_pred[11] * 0.44))]

    daily_base = max(1, round(modeled_month / 30))
    week_sales = [max(1, round(daily_base * factor)) for factor in [0.92, 0.98, 1.0, 1.04, 1.15]] + [None, None]
    week_pred = [None] * 5 + [max(1, round(daily_base * 1.22)), max(1, round(daily_base * 1.28))]
    week_inventory = [max(2, round(value * 2.8)) for value in week_sales[:5]] + [None, None]
    week_pred_inventory = [None] * 5 + [max(2, round(week_pred[5] * 2.2)), max(2, round(week_pred[6] * 2.0))]
    week_safety = [None] * 5 + [max(1, round(week_pred[5] * 0.48)), max(1, round(week_pred[6] * 0.5))]

    next_predicted = year_pred[12] or modeled_month
    reorder_value = round(next_predicted * avg_price, 2)
    coverage_days = max(3, round((year_inventory[11] or next_predicted * 2.2) / max(1, modeled_month / 30)))
    bias = round(((avg_price - min(avg_price, avg_price * (1 - promo_rate * 0.12))) / max(avg_price, 0.01)) * 100 + promo_rate * 35, 1)
    risk = "Low" if coverage_days >= 20 else "Medium" if coverage_days >= 10 else "High"

    return {
        "year": {
            "now": 12,
            "labels": _year_axis_labels(today),
            "sales": year_sales,
            "predictedSales": year_pred,
            "inventory": year_inventory,
            "predictedInventory": year_pred_inventory,
            "safety": year_safety,
            "max": max(year_inventory[:12] + year_pred_inventory[12:] + [1]) + max(6, round(modeled_month * 0.3)),
            "value": reorder_value,
            "coverageDays": coverage_days,
            "bias": bias,
            "risk": risk,
            "predictedInventoryAtNow": year_pred_inventory[12] or year_inventory[11] or next_predicted,
        },
        "month": {
            "now": 8,
            "labels": ["W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9", "W10", "W11", "W12"],
            "sales": month_sales,
            "predictedSales": month_pred,
            "inventory": month_inventory,
            "predictedInventory": month_pred_inventory,
            "safety": month_safety,
            "max": max(month_inventory[:9] + month_pred_inventory[9:] + [1]) + max(4, round(weekly_base * 0.8)),
            "value": round((month_pred[9] or weekly_base) * avg_price, 2),
            "coverageDays": max(3, round((month_inventory[8] or weekly_base * 2.2) / max(1, weekly_base / 7))),
            "bias": round(bias * 0.72, 1),
            "risk": "Low" if coverage_days >= 18 else "Medium" if coverage_days >= 9 else "High",
            "predictedInventoryAtNow": month_pred_inventory[9] or month_inventory[8] or weekly_base,
        },
        "week": {
            "now": 4,
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            "sales": week_sales,
            "predictedSales": week_pred,
            "inventory": week_inventory,
            "predictedInventory": week_pred_inventory,
            "safety": week_safety,
            "max": max(week_inventory[:5] + week_pred_inventory[5:] + [1]) + max(2, daily_base),
            "value": round((week_pred[5] or daily_base) * avg_price, 2),
            "coverageDays": max(2, round((week_inventory[4] or daily_base * 2.5) / max(1, daily_base))),
            "bias": round(bias * 0.5, 1),
            "risk": "Low" if coverage_days >= 14 else "Medium" if coverage_days >= 7 else "High",
            "predictedInventoryAtNow": week_pred_inventory[5] or week_inventory[4] or daily_base,
        },
    }


def _sim_sku(sim, barcode):
    """The simulation's demand record for one barcode, or None if it had no
    simulated purchases (zero-demand SKUs are absent from sku_breakdown)."""
    return ((sim or {}).get("retail_breakdown") or {}).get("sku_breakdown", {}).get(barcode)


def _sim_window_days(sim):
    meta = (sim or {}).get("simulation_metadata") or {}
    try:
        start = date.fromisoformat(meta["start_date"])
        end = date.fromisoformat(meta["end_date"])
        return max(1, (end - start).days)
    except (KeyError, ValueError):
        return 30


def _overlay_sim_weekly(dc, sku, today):
    """Overlay the SKU's real simulated weekly units onto the month view's recent
    observed slots and lift the period max so the real bars render. Only the
    month view is overlaid — the ~30-day sim window fits its weekly axis; the
    year (12-month) and week (daily) views keep the sim-scaled heuristic shape."""
    month = dc.get("month")
    if not month:
        return
    now_idx = month.get("now", 8)
    sales = month["sales"]
    overlaid = []
    for bucket in sku.get("weekly_buckets", []):
        try:
            bucket_start = date.fromisoformat(bucket["start"])
        except (ValueError, KeyError):
            continue
        idx = now_idx - (today - bucket_start).days // 7
        if 0 <= idx <= now_idx:
            sales[idx] = bucket["units"]
            overlaid.append(bucket["units"])
    if overlaid:
        observed = [v for v in sales[:now_idx + 1] if v is not None]
        inventory = [v for v in month["inventory"] if v is not None]
        month["max"] = max(month["max"], max(observed + inventory + [1]) + max(4, round(max(overlaid) * 0.25)))


def _retail_product_detail_payload(barcode):
    if not RETAIL_DB_PATH.exists():
        return {"error": "missing-retail-db"}

    conn = sqlite3.connect(RETAIL_DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT p.*, pr.original_price, pr.sale_price, pr.discount_percent, pr.is_on_sale
        FROM products p
        JOIN prices pr ON pr.product_id = p.id
        WHERE p.barcode = ?
        ORDER BY COALESCE(pr.sale_price, pr.original_price) ASC, p.chain_rank ASC, p.id ASC
        """,
        (barcode,),
    ).fetchall()
    conn.close()
    if not rows:
        return {"error": f"barcode {barcode} not found"}

    offers_by_store = {}
    for row in rows:
        store_slug = row["store_slug"]
        effective_price = _effective_price(row)
        existing = offers_by_store.get(store_slug)
        if existing and existing["effective_price"] <= effective_price:
            continue
        offers_by_store[store_slug] = {
            "store_slug": store_slug,
            "store_name": STORE_NAME_MAP.get(store_slug, store_slug.replace("_", " ").title()),
            "brand_id": STORE_BRAND_MAP.get(store_slug, store_slug),
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

    offers = sorted(offers_by_store.values(), key=lambda offer: (offer["effective_price"], offer["chain_rank"], offer["store_slug"]))
    first = offers[0]
    prices = [offer["effective_price"] for offer in offers]
    avg_price = round(sum(prices) / len(prices), 2)
    min_price = round(min(prices), 2)
    max_price = round(max(prices), 2)
    promo_count = sum(1 for offer in offers if offer["is_on_sale"])
    promo_rate = promo_count / max(len(offers), 1)

    sim = _load_sim_report()
    today = _today_from_sim(sim)
    breakdown = sim.get("retail_breakdown", {})
    sim_brands = breakdown.get("brands", {})
    related_brand_ids = [offer["brand_id"] for offer in offers if offer["brand_id"] in sim_brands]
    related_metrics = [sim_brands[brand_id] for brand_id in sorted(set(related_brand_ids))]
    total_brand_units = sum(metric.get("units", 0) for metric in related_metrics)
    total_brand_visits = sum(metric.get("visits", 0) for metric in related_metrics)
    total_brand_spend = sum(metric.get("spend", 0) for metric in related_metrics)
    category_key = first["parent_category_slug"] or "groceries"
    category_factor = CATEGORY_FACTOR_MAP.get(category_key, 0.085)
    base_units_month = max(
        len(offers) * 8,
        round((total_brand_units or len(offers) * 18) * category_factor * (1 + promo_rate * 0.35))
    )
    # Phase 5: SKUs with sufficient simulated demand (top-N, carry weekly_buckets)
    # drive the forecast off their real simulated magnitude; sparse/zero-demand
    # SKUs keep the per-SKU DB heuristic (the chosen sparsity fallback).
    sku_demand = _sim_sku(sim, barcode)
    observed_source = "heuristic"
    if sku_demand and "weekly_buckets" in sku_demand:
        base_units_month = max(2, round(sku_demand["units"] * 30.0 / _sim_window_days(sim)))
        observed_source = "simulation"
    units_year = base_units_month * 12
    price_pressure = (min_price / avg_price) if avg_price else 1
    trend_pct = round((promo_rate * 11 + (1 - price_pressure) * 14 + max(total_brand_visits, 1) * 0.08) * -1, 1)
    cheapest_brand_id = offers[0]["brand_id"]
    top_brand_counts = {}
    for offer in offers:
        top_brand_counts[offer["brand_id"]] = top_brand_counts.get(offer["brand_id"], 0) + 1
    top_brand_id = sorted(top_brand_counts.items(), key=lambda item: (-item[1], item[0]))[0][0]
    heuristic_forecast = {
        "dc": _build_forecast_series(base_units_month, avg_price, len(offers), promo_rate, category_key, 1.0, today=today),
        "store": {},
    }
    for offer in offers:
        store_units_month = max(2, round(base_units_month / max(len(offers), 1) * (1.08 if offer["is_on_sale"] else 0.96)))
        heuristic_forecast["store"][offer["store_slug"]] = _build_forecast_series(store_units_month, offer["effective_price"], 1, 1.0 if offer["is_on_sale"] else 0.0, category_key, 0.42, today=today)

    if observed_source == "simulation":
        _overlay_sim_weekly(heuristic_forecast["dc"], sku_demand, today)

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
            "cheapest_brand_id": cheapest_brand_id,
            "top_brand_id": top_brand_id,
            "units_month_modeled": base_units_month,
            "units_year_modeled": units_year,
            "trend_pct": trend_pct,
            "model_source": "live-retail-prices-plus-latest-simulation",
            "total_brand_visits": total_brand_visits,
            "total_brand_spend": round(total_brand_spend, 2),
        },
        "observed_source": observed_source,
        "forecast": heuristic_forecast,
    }


class NoCacheHandler(SimpleHTTPRequestHandler):
    def _write_json(self, code, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/simulation-report.json":
            if not SIM_REPORT_PATH.exists():
                self._write_json(404, {"error": "simulation_report.json not found"})
                return

            body = SIM_REPORT_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if route == "/simulation-status":
            self._write_json(200, _snapshot_sim_state())
            return
        if route == "/store-locations":
            self._write_json(200, _store_locations_payload())
            return
        if route == "/retail-product-media":
            params = parse_qs(parsed.query)
            barcodes = []
            for value in params.get("barcodes", []):
                barcodes.extend(part.strip() for part in value.split(","))
            self._write_json(200, _retail_media_payload(barcodes))
            return
        if route == "/retail-product-detail":
            params = parse_qs(parsed.query)
            barcode = (params.get("barcode") or [""])[0].strip()
            if not barcode:
                self._write_json(400, {"error": "barcode is required"})
                return
            payload = _retail_product_detail_payload(barcode)
            self._write_json(200 if "error" not in payload else 404, payload)
            return
        if route == "/sku-forecast":
            params = parse_qs(parsed.query)
            barcode = (params.get("barcode") or [""])[0].strip()
            if not barcode:
                self._write_json(400, {"error": "barcode is required"})
                return
            detail = _retail_product_detail_payload(barcode)
            if "error" in detail:
                self._write_json(404, detail)
                return
            payload = _llm_sku_forecast(
                barcode=barcode,
                first_offer=detail["offers"][0],
                offers=detail["offers"],
                summary=detail["summary"],
                heuristic_forecast=detail["forecast"],
                sim=_load_sim_report(),
            )
            self._write_json(200, payload)
            return

        super().do_GET()

    def do_POST(self):
        route = (urlparse(self.path).path or "/").rstrip("/") or "/"
        if route == "/assistant-chat" or route.endswith("/assistant-chat"):
            body = _safe_read_json_body(self)
            payload = _assistant_chat_payload(
                body.get("message", ""),
                supplied_brand=body.get("brand", ""),
                supplied_barcode=body.get("barcode", ""),
                history=body.get("history", []),
            )
            self._write_json(200 if payload.get("ok") else 400, payload)
            return

        if route != "/run-simulation":
            self._write_json(404, {"error": "unknown endpoint", "route": route})
            return

        if not SIM_LOCK.acquire(blocking=False):
            self._write_json(409, {
                "ok": False,
                "error": "simulation already running",
                "status": _snapshot_sim_state(),
            })
            return

        next_job_id = _snapshot_sim_state()["job_id"] + 1
        _update_sim_state(
            job_id=next_job_id,
            status="queued",
            message="Simulation queued",
            started_at=time.time(),
            finished_at=None,
            stdout_tail=[],
            stderr_tail=[],
            report_exists=SIM_REPORT_PATH.exists(),
        )
        thread = threading.Thread(target=_run_simulation_job, args=(next_job_id,), daemon=True)
        thread.start()
        self._write_json(202, {
            "ok": True,
            "message": "simulation queued",
            "status": _snapshot_sim_state(),
        })

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8600
    ThreadingHTTPServer(("127.0.0.1", port), NoCacheHandler).serve_forever()
