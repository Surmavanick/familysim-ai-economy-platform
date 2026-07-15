"""
Georgia Retail Intelligence — Live Data Connector

Connects the simulation and dashboard code to the shared retail database.
Supports:
- Supabase / PostgreSQL when `SUPABASE_DB` is configured
- Local SQLite `retail_data.db` as the normal fallback path

Usage:
    from data_pipeline.retail_connector import RetailConnector
    connector = RetailConnector()
    products = connector.fetch_products(store_slug="spar")
    cheapest = connector.get_cheapest("milk")
"""

import os
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB")
DEFAULT_LOCAL_DB = Path(__file__).resolve().parents[1] / "georgia-retail-intelligence" / "retail_data.db"


class RetailConnector:
    """Async + sync bridge to the retail database."""

    def __init__(self, db_url: str = None):
        self.db_url = db_url or DB_URL
        self.is_postgres = bool(self.db_url) and self.db_url.startswith("postgresql")
        if self.is_postgres:
            self.local_db_path = DEFAULT_LOCAL_DB
        elif self.db_url and self.db_url not in ("sqlite", "local"):
            self.local_db_path = Path(self.db_url)
        else:
            self.local_db_path = DEFAULT_LOCAL_DB

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    async def get_conn(self):
        if self.is_postgres:
            import asyncpg
            return await asyncpg.connect(self.db_url)
        raise RuntimeError("Async interface requires PostgreSQL. Use sync methods for SQLite.")

    def _sqlite_conn(self):
        conn = sqlite3.connect(str(self.local_db_path))
        conn.row_factory = sqlite3.Row
        return conn

    # ------------------------------------------------------------------
    # Sync SQLite interface (used by simulation when running locally)
    # ------------------------------------------------------------------

    def _fetch_products_sqlite(self, store_slug=None, category_slug=None, city_slug=None, limit=1000) -> List[Dict]:
        conn = self._sqlite_conn()
        conditions = []
        params = []

        if store_slug:
            conditions.append("p.store_slug = ?")
            params.append(store_slug)
        if category_slug:
            conditions.append("p.category_slug = ?")
            params.append(category_slug)
        if city_slug:
            conditions.append("p.city_slug = ?")
            params.append(city_slug)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT p.*, pr.original_price, pr.sale_price, pr.discount_percent, pr.is_on_sale
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            {where}
            ORDER BY p.name
            LIMIT ?
        """
        params.append(limit)

        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    def _get_cheapest_sqlite(self, product_name_substring: str, city_slug=None) -> Optional[Dict]:
        conn = self._sqlite_conn()
        params = [f"%{product_name_substring}%"]
        city_filter = "AND p.city_slug = ?" if city_slug else ""
        if city_slug:
            params.append(city_slug)

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT p.id, p.name, p.store_slug, p.city_slug,
                   pr.original_price, pr.sale_price, pr.is_on_sale
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            WHERE p.name LIKE ? {city_filter}
            ORDER BY COALESCE(pr.sale_price, pr.original_price) ASC
            LIMIT 1
        """, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def _get_inflation_snapshot_sqlite(self, category_slug=None, city_slug=None) -> Dict:
        conn = self._sqlite_conn()
        conditions = []
        params = []

        if category_slug:
            conditions.append("p.category_slug = ?")
            params.append(category_slug)
        if city_slug:
            conditions.append("p.city_slug = ?")
            params.append(city_slug)

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT
                COUNT(DISTINCT p.id) AS product_count,
                AVG(pr.original_price) AS avg_original,
                AVG(pr.sale_price) AS avg_sale,
                AVG(pr.discount_percent) AS avg_discount,
                SUM(CASE WHEN pr.is_on_sale THEN 1 ELSE 0 END) * 1.0 / NULLIF(COUNT(*), 0) AS sale_ratio
            FROM products p
            JOIN prices pr ON pr.product_id = p.id
            {where}
        """, params)
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Async PostgreSQL interface
    # ------------------------------------------------------------------

    async def fetch_products_async(self, store_slug=None, category_slug=None, city_slug=None, limit=1000):
        """Fetch live products from Supabase."""
        conn = await self.get_conn()
        conditions = []
        params = []
        idx = 1

        if store_slug:
            conditions.append(f"store_slug = ${idx}")
            params.append(store_slug)
            idx += 1
        if category_slug:
            conditions.append(f"category_slug = ${idx}")
            params.append(category_slug)
            idx += 1
        if city_slug:
            conditions.append(f"city_slug = ${idx}")
            params.append(city_slug)
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        sql = f"""
            SELECT p.*, lp.original_price, lp.sale_price, lp.discount_percent, lp.is_on_sale
            FROM products p
            LEFT JOIN latest_prices lp ON lp.product_id = p.id
            {where}
            ORDER BY p.name
            LIMIT ${idx}
        """
        params.append(limit)

        rows = await conn.fetch(sql, *params)
        await conn.close()
        return [dict(r) for r in rows]

    async def get_cheapest_async(self, product_name_substring: str, city_slug=None):
        """Find the cheapest store for a given product name."""
        conn = await self.get_conn()
        city_filter = "AND p.city_slug = $2" if city_slug else ""
        params = [f"%{product_name_substring}%"]
        if city_slug:
            params.append(city_slug)

        row = await conn.fetchrow(f"""
            SELECT p.id, p.name, p.store_slug, p.city_slug,
                   lp.original_price, lp.sale_price, lp.is_on_sale
            FROM products p
            LEFT JOIN latest_prices lp ON lp.product_id = p.id
            WHERE p.name ILIKE $1 {city_filter}
            ORDER BY COALESCE(lp.sale_price, lp.original_price) ASC NULLS LAST
            LIMIT 1
        """, *params)
        await conn.close()
        return dict(row) if row else None

    async def get_price_history_async(self, product_id: int, days: int = 30):
        """Get price history for a product."""
        conn = await self.get_conn()
        rows = await conn.fetch("""
            SELECT original_price, sale_price, discount_percent, is_on_sale, recorded_at
            FROM prices
            WHERE product_id = $1
              AND recorded_at > NOW() - INTERVAL '$2 days'
            ORDER BY recorded_at DESC
        """, product_id, days)
        await conn.close()
        return [dict(r) for r in rows]

    async def get_inflation_snapshot_async(self, category_slug=None, city_slug=None):
        """Compute average price changes for inflation tracking."""
        conn = await self.get_conn()
        conditions = []
        params = []
        idx = 1

        if category_slug:
            conditions.append(f"p.category_slug = ${idx}")
            params.append(category_slug)
            idx += 1
        if city_slug:
            conditions.append(f"p.city_slug = ${idx}")
            params.append(city_slug)
            idx += 1

        where = "WHERE " + " AND ".join(conditions) if conditions else ""

        row = await conn.fetchrow(f"""
            SELECT
                COUNT(DISTINCT p.id) AS product_count,
                AVG(lp.original_price) AS avg_original,
                AVG(lp.sale_price) AS avg_sale,
                AVG(lp.discount_percent) AS avg_discount,
                SUM(CASE WHEN lp.is_on_sale THEN 1 ELSE 0 END)::FLOAT / NULLIF(COUNT(*), 0) AS sale_ratio
            FROM products p
            LEFT JOIN latest_prices lp ON lp.product_id = p.id
            {where}
        """, *params)
        await conn.close()
        return dict(row) if row else {}

    # ------------------------------------------------------------------
    # Sync interface (convenience for simulation loops / pandas)
    # ------------------------------------------------------------------

    def fetch_products(self, store_slug=None, category_slug=None, city_slug=None, limit=1000):
        """Synchronous wrapper — returns pandas DataFrame."""
        if self.is_postgres:
            import asyncio
            rows = asyncio.run(self.fetch_products_async(store_slug, category_slug, city_slug, limit))
        else:
            rows = self._fetch_products_sqlite(store_slug, category_slug, city_slug, limit)
        return pd.DataFrame(rows)

    def get_cheapest(self, product_name_substring: str, city_slug=None):
        """Synchronous wrapper."""
        if self.is_postgres:
            import asyncio
            return asyncio.run(self.get_cheapest_async(product_name_substring, city_slug))
        return self._get_cheapest_sqlite(product_name_substring, city_slug)

    def get_price_history(self, product_id: int, days: int = 30):
        """Synchronous wrapper."""
        if self.is_postgres:
            import asyncio
            return asyncio.run(self.get_price_history_async(product_id, days))
        raise NotImplementedError("Price history sync not implemented for SQLite.")

    def get_inflation_snapshot(self, category_slug=None, city_slug=None):
        """Synchronous wrapper."""
        if self.is_postgres:
            import asyncio
            return asyncio.run(self.get_inflation_snapshot_async(category_slug, city_slug))
        return self._get_inflation_snapshot_sqlite(category_slug, city_slug)

    # ------------------------------------------------------------------
    # Simulation bridge helpers
    # ------------------------------------------------------------------

    def to_market_dataframe(self, city_slug="tbilisi") -> pd.DataFrame:
        """
        Returns a DataFrame in the exact format expected by
        economy_engine.market.Market.initialize_stores_from_data()

        Columns: id, name, price, category, store
        """
        df = self.fetch_products(city_slug=city_slug, limit=50000)
        if df.empty:
            return df

        df = df.rename(columns={
            "store_slug": "store",
            "category_slug": "category",
        })

        df["price"] = df.apply(
            lambda r: r["sale_price"] if pd.notna(r.get("sale_price")) and r.get("is_on_sale")
            else r.get("original_price", 0),
            axis=1
        )

        for col in ["id", "name", "price", "category", "store"]:
            if col not in df.columns:
                df[col] = None

        return df[["id", "name", "price", "category", "store"]].dropna(subset=["price"])

    def get_store_names(self, city_slug="tbilisi") -> list:
        """Return list of unique store slugs."""
        if self.is_postgres:
            import asyncio
            conn = asyncio.run(self.get_conn())
            rows = asyncio.run(conn.fetch(
                "SELECT DISTINCT store_slug FROM products WHERE city_slug = $1 ORDER BY store_slug",
                city_slug
            ))
            asyncio.run(conn.close())
            return [r["store_slug"] for r in rows]

        conn = self._sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT store_slug FROM products WHERE city_slug = ? ORDER BY store_slug", (city_slug,))
        rows = [r["store_slug"] for r in cursor.fetchall()]
        conn.close()
        return rows
