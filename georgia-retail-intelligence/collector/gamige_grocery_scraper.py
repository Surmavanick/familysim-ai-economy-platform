"""
GAMIGE.com grocery-only collector.

Scrapes only food/grocery categories from https://gamige.com and stores them
in gamige_grocery.db with per-store prices and image URLs.

Usage:
    python collector/gamige_grocery_scraper.py
"""

import argparse
import asyncio
import json
import sqlite3
import time
import urllib.parse
from pathlib import Path
from typing import Dict, List, Optional, Set

import httpx

DB_PATH = Path(__file__).resolve().parents[1] / "gamige_grocery.db"
PROGRESS_FILE = Path(__file__).resolve().parents[1] / "gamige_grocery_progress.json"
BASE_URL = "https://gamige.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json",
}
DEFAULT_LIMIT = 200
DEFAULT_CONCURRENCY = 5

# Grocery / food-related category names discovered on gamige.com
GROCERY_CATEGORIES = [
    # Dairy & eggs
    "რძის პროდუქტი",
    "რძის პროდუქტები, კვერცხი",
    "რძის ნაწარმი და კვერცხი",
    "რძე, ნაღები",
    "რძე, რძის შემცვლელი",
    "ნაღები, ყავის კრემი",
    "კარაქი & სპრედი",
    "კარაქი, მარგარინი, სპრედი",
    "კეფირი, აირანი",
    "მაწონი",
    "ხაჭო & ხაჭოს დესერტი",
    "ხაჭო, მაწონი, არაჟანი",
    "კვერცხი და რძის ნაწარმი",
    "ყველი",
    "ქართული ყველი",
    "დესერტი",
    "რძის შემცველი დესერტი",
    "იოგურტი & პუდინგი",

    # Meat & fish
    "ხორცი",
    "ხორცი და თევზი",
    "ხორცი და ნახევარფაბრიკატები",
    "ხორცის და თევზის პროდუქტები",
    "ახალი ხორცი და ხორცპროდუქტები",
    "მწვადი/ხორცი",
    "ქათამი",
    "სოსისი & სარდელი",
    "სოსისი და ძეხვეული",
    "ძეხვეული",
    "თევზი და ზღვის პროდუქტები",
    "ზღვის პროდუქტები",
    "გაყინული თევზი, ზღვის პროდუქტები",
    "შებოლილი, დამარილებული თევზი",

    # Bread & bakery
    "პური",
    "პურ-ფუნთუშეული",
    "ტოსტის, ბურგერის პური",
    "ფუნთუშეული",
    "ბისკვიტები, ორცხობილა",
    "ორცხობილა, ბისკვიტი & ვაფლი",
    "კრუასანი & ზეფირი",

    # Fruits & vegetables
    "ხილი/ბოსტანი",
    "ხილ-ბოსტანი",
    "ხილ-ბოსტნეული",
    "ბოსტნეული",
    "მწვანილი",

    # Drinks
    "სასმელები",
    "სასმელი",
    "წყალი",
    "წვენი & კომპოტი",
    "წვენი, კომპოტი, სიროფი",
    "უალკოჰოლო სასმელები",
    "უალკოჰოლო სასმელი",
    "ცივი ჩაი, ცივი ყავა",
    "ენერგეტიკული სასმელები",
    "ენერგეტიკული სასმელი",
    "ლუდი",
    "ალკოჰოლური სასმელები",
    "ალკოჰოლური სასმელი",
    "არაყი, ჭაჭა",
    "ლიქიორი & ვერმუტი",
    "ღვინო",
    "სპირტიანი",

    # Sweets & snacks
    "ტკბილეული",
    "ტკბილეული და ნაყინი",
    "საბავშვო ტკბილეული",
    "კანფეტი",
    "კანფეტი, ჟელიბონი",
    "ბომბონერი",
    "შოკოლადის ფილა",
    "ჰალვა, გოზინაყი",
    "სნექი",
    "სნექები",
    "სნექი, ჩირი და თხილი",
    "მარილიანი და ტკბილი სნექი",
    "ჩიფსი",
    "ჩიფსი, სუხარიკი",
    "კრეკერი და სხვა",
    "ნაყინი",
    "ნაყინი ",

    # Coffee & tea
    "ყავა",
    "ყავა და ჩაი",
    "ყავა, ჩაი და კაკაო",
    "ხსნადი ყავა",
    "ჩაი",
    "შავი ჩაი",
    "ჩაი, ყავა და კაკაო",

    # Pasta, rice, grains
    "მაკარონი",
    "პასტა, მაკარონი",
    "ბრინჯი, ატრია",
    "ატრია, ლაფშა",
    "მარცვლეული",
    "მარცვლეული & ბურღული",
    "მარცვლეული, ბურღული",

    # Oils, sauces, condiments
    "ზეთი ",
    "ზეთი",
    "კონსერვები",
    "კონსერვი",
    "სოუსები, საწებელი",
    "სოუსი, საწებელი, ტყემალი",
    "მაიონეზი & სოუსები",

    # Baking & staples
    "შაქარი, მარილი",
    "ფქვილი, ცხობა",
    "თაფლი, მურაბა & ჯემი",

    # Nuts & dried fruit
    "თხილეული, ნუში",
    "მიწისთხილი, თხილი",

    # Frozen & ready meals
    "გაყინული პროდუქტები",
    "გაყინული პროდუქცია",
    "ნახევარფაბრიკატები",
    "ნახევარფაბრიკატი",
    "სხვა გაყინული ნახევარფაბრიკატები",
    "ცხელი კერძი",
    "ცივი კერძი",
    "ხინკალი",
    "სუპი",

    # Other food
    "სურსათი",
    "BIO პროდუქტები",
    "უგლუტენო",
    "ულაქტოზო",
    "დიეტური და დიაბეტური",
    "უგლუტენო, ულაქტოზო, დიაბეტური",
    "სპარის წარმოება",
    "გუდვილის ექსკლუზიური ბრენდები",
    "საბავშვო",
    "ბაკალეა",
    "მშრალი ბაკალეა ",
]


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT,
            size TEXT,
            category TEXT,
            image_url TEXT,
            barcode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            store TEXT,
            price REAL,
            old_price REAL,
            in_stock INTEGER,
            product_url TEXT,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
        CREATE INDEX IF NOT EXISTS idx_prices_product_id ON prices(product_id);
        CREATE INDEX IF NOT EXISTS idx_prices_store ON prices(store);
        CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
        """
    )
    conn.commit()
    conn.close()


def load_progress() -> Dict:
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_progress(progress: Dict) -> None:
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


async def fetch_category_page(
    client: httpx.AsyncClient,
    category: str,
    page: int,
    limit: int,
    retries: int = 3,
) -> Dict:
    for attempt in range(retries):
        try:
            response = await client.get(
                f"{BASE_URL}/api/search",
                params={"category": category, "page": page, "limit": limit},
                headers=HEADERS,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            status = getattr(e, "response", None) and getattr(e.response, "status_code", None)
            if status == 429:
                wait = 2 ** attempt + 1
                print(f"    429 on '{category}' page {page}, waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(1)
    return {}


def save_products_batch(conn: sqlite3.Connection, products: List[Dict]) -> int:
    cursor = conn.cursor()
    saved = 0
    for p in products:
        pid = str(p.get("id", ""))
        if not pid:
            continue
        cursor.execute(
            """
            INSERT INTO products (id, name, size, category, image_url, barcode)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                size = excluded.size,
                category = excluded.category,
                image_url = excluded.image_url,
                barcode = excluded.barcode,
                updated_at = CURRENT_TIMESTAMP
            """,
            (pid, p.get("name"), p.get("size"), p.get("category"), p.get("image"), p.get("barcode")),
        )
        saved += 1

        stores = p.get("stores") or []
        prices_map = p.get("prices") or {}
        old_prices_map = p.get("oldPrices") or {}

        if stores:
            for s in stores:
                store_name = s.get("store")
                price = s.get("price")
                old_price = s.get("old_price") or old_prices_map.get(store_name)
                in_stock = 1 if s.get("inStock") else 0
                product_url = s.get("url")
                if store_name is None or price is None:
                    continue
                cursor.execute(
                    """
                    INSERT INTO prices (product_id, store, price, old_price, in_stock, product_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (pid, store_name, float(price), float(old_price) if old_price is not None else None, in_stock, product_url),
                )
        elif prices_map:
            for store_name, price in prices_map.items():
                old_price = old_prices_map.get(store_name)
                cursor.execute(
                    """
                    INSERT INTO prices (product_id, store, price, old_price, in_stock, product_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (pid, store_name, float(price), float(old_price) if old_price is not None else None, 1, None),
                )
    conn.commit()
    return saved


def get_stats(conn: sqlite3.Connection) -> Dict:
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    product_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM prices")
    price_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(DISTINCT store) FROM prices")
    store_count = cursor.fetchone()[0]
    return {"products": product_count, "prices": price_count, "stores": store_count}


async def scrape_grocery(limit: int, concurrency: int) -> Dict:
    import math

    init_db()
    conn = sqlite3.connect(DB_PATH)
    progress = load_progress()
    completed_categories = set(progress.get("completed_categories", []))

    async with httpx.AsyncClient(headers=HEADERS, timeout=30.0) as client:
        sem = asyncio.Semaphore(concurrency)

        async def fetch_and_save(category: str, page: int) -> int:
            async with sem:
                data = await fetch_category_page(client, category, page, limit)
                products = data.get("results", [])
                if products:
                    return save_products_batch(conn, products)
                return 0

        total_products = 0
        category_stats = {}

        for category in GROCERY_CATEGORIES:
            if category in completed_categories:
                print(f"Skipping completed category: {category}")
                continue

            try:
                first = await fetch_category_page(client, category, 1, limit)
            except Exception as e:
                print(f"ERROR fetching category '{category}': {e}")
                continue

            total = first.get("total", 0)
            if not total:
                print(f"No products for category: {category}")
                progress.setdefault("completed_categories", []).append(category)
                save_progress(progress)
                continue

            pages = math.ceil(total / limit)
            print(f"Category '{category}': {total} products, {pages} pages")

            # Save first page
            saved = save_products_batch(conn, first.get("results", []))
            total_products += saved

            # Fetch remaining pages in batches
            batch_size = concurrency * 3
            for start in range(2, pages + 1, batch_size):
                end = min(start + batch_size, pages + 1)
                tasks = [fetch_and_save(category, page) for page in range(start, end)]
                results = await asyncio.gather(*tasks, return_exceptions=True)

                batch_saved = 0
                for res in results:
                    if isinstance(res, Exception):
                        print(f"  ERROR: {res}")
                    else:
                        batch_saved += res
                total_products += batch_saved

                print(
                    f"  {category} pages {start}-{min(end - 1, pages)}/{pages}: +{batch_saved} | "
                    f"total DB: {get_stats(conn)['products']}"
                )
                await asyncio.sleep(0.3)

            category_stats[category] = total
            progress.setdefault("completed_categories", []).append(category)
            save_progress(progress)

    stats = get_stats(conn)
    conn.close()
    stats["category_stats"] = category_stats
    return stats


async def main_async():
    parser = argparse.ArgumentParser(description="Scrape grocery products from GAMIGE.com")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help="Products per page (max 200)")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Concurrent page fetches")
    args = parser.parse_args()

    t0 = time.time()
    print("Starting GAMIGE.com grocery scrape...")
    stats = await scrape_grocery(limit=args.limit, concurrency=args.concurrency)
    elapsed = time.time() - t0

    print("\n" + "=" * 60)
    print("FINAL STATS")
    print("=" * 60)
    print(f"  products: {stats['products']}")
    print(f"  prices: {stats['prices']}")
    print(f"  stores: {stats['stores']}")
    print(f"  elapsed_seconds: {elapsed:.1f}")


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
