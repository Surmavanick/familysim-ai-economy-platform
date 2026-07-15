"""
Migrate gamige_grocery.db into the standard retail_data.db schema.

Each gamige product-store price becomes one product row in the old schema,
so existing consumers (store_engine, economy_engine, retail_connector) keep working.

Usage:
    python collector/migrate_gamige_to_retail.py
"""

import re
import sqlite3
from pathlib import Path

GAMIGE_DB = Path(__file__).resolve().parents[1] / "gamige_grocery.db"
RETAIL_DB = Path(__file__).resolve().parents[1] / "retail_data.db"

# Map gamige store display names -> project store slugs
STORE_SLUG_MAP = {
    "Agrohub": "agrohub",
    "Goodwill": "goodwill",
    "Carrefour": "carrefour",
    "Europroduct": "europroduct",
    "2 Nabiji": "2nabiji",
    "Nikora": "nikora",
    "Magniti": "magniti",
    "Zgapari": "zgapari",
    "Shefisu": "shefisu",
    "Aversi": "aversi",
    "SPAR": "spar",
    "PharmaDepot": "pharmadepot",
    "Alcorium": "alcorium",
    "Kontakt": "kontakt",
    "PSP": "psp",
    "Megatechnica": "megatechnica",
    "Alta": "alta",
    "Alneo": "alneo",
    "Domino": "domino",
    "rezto-Kojori": "resto_kojori",
    "ფასანაური დოლიძე": "fasa_nauri_dolidze",
    "ზოდიაქო": "zodiako",
    "წისქვილი (ლუდის მ.)": "tsiskvili",
    "სახაჭაპურე №1": "sakhachapure_n1",
}

# Fallback rank per store (lower = larger chain)
CHAIN_RANK = {
    "carrefour": 1,
    "goodwill": 2,
    "spar": 3,
    "agrohub": 4,
    "europroduct": 5,
    "nikora": 6,
    "magniti": 7,
    "2nabiji": 8,
    "zgapari": 9,
    "ioli": 10,
    "libre": 11,
    "aversi": 12,
    "psp": 13,
    "gpc": 14,
    "pharmadepot": 15,
    "alcorium": 16,
    "shefisu": 17,
    "kontakt": 18,
    "alta": 19,
    "alneo": 20,
    "megatechnica": 21,
    "domino": 22,
}


def store_to_slug(name: str) -> str:
    if name in STORE_SLUG_MAP:
        return STORE_SLUG_MAP[name]
    # Generate a safe slug
    slug = re.sub(r"[^a-z0-9_-]", "", name.lower().replace(" ", "_").replace(".", ""))[:40]
    return slug or "unknown"


def map_category(gamige_cat: str, name: str = "") -> tuple[str, str]:
    """Return (category_slug, parent_category_slug) for a gamige category + product name."""
    cat = (gamige_cat or "").lower().strip()
    text = cat + " " + (name or "").lower()

    # Dairy (use Georgian word stems to catch case endings)
    # Use product name for finer dairy classification when category is broad
    if "ყველ" in text or "კრემყველი" in text or "ყველის ფესტივალი" in text or "მდნარი ყველი" in text:
        return "cheese", "dairy"
    if any(k in text for k in ["იოგურტ", "პუდინგ"]) or "დესერტ" in text:
        return "yogurt", "dairy"
    if any(k in text for k in ["ხაჭო", "მაწონი", "არაჟანი"]):
        return "dairy", "dairy"
    if "კვერცხ" in text:
        return "eggs", "dairy"
    if any(k in text for k in ["რძ", "კეფირი", "აირანი", "ნაღები", "ყავის კრემი"]):
        return "milk_kefir", "dairy"

    # Bakery
    if any(k in text for k in ["პურ", "ბისკვიტ", "ვაფლ", "კრუასან", "ფუნთუშ", "ხრაშუნა პური", "თეთრი პური", "რუხი პური", "ჭვავის", "პურის საცხობი", "გემოვანი პური", "ფქვილი/პური", "დიეტური, დიაბეტური პური"]):
        return "bakery", "bakery"

    # Meat / fish (check before produce so olive-oil meats don't become vegetables)
    if any(k in text for k in ["ძეხვ", "სოსის", "სარდელ", "შაშხ", "პაშტეტ", "დელიკატეს", "მორტადელ", "კოლბას", "ვეტჩინ"]):
        return "sausages", "meat_fish"
    if any(k in text for k in ["ხორც", "ქათამ", "კურდლის", "მწვადი", "ფრეშ ხორცი", "ძროხის", "ღორის", "ნედლი ქათამი", "გაყინული ხორცი", "ფარში", "ტოლმა"]):
        return "meat_fish", "meat_fish"
    if any(k in text for k in ["თევზ", "ზღვის პროდუქტ", "შებოლილი", "დამარილებული თევზი", "ხმელი თევზი", "თევზის კონსერვი", "ანჩოუს"]):
        return "meat_fish", "meat_fish"

    # Produce
    if any(k in text for k in ["ხილი", "ბოსტანი", "მწვანილი", "მიკრო მწვანილი", "ბანანი", "ვაშლი", "მზესუმზირა", "კიტრი", "ტომატ", "კარტოფილი"]):
        return "vegetables_fruits", "vegetables_fruits"

    # Frozen / ready meals
    if any(k in text for k in ["გაყინულ", "ნახევარფაბრიკატ", "ხინკალ", "სუპ", "ცხელი კერძი", "ცივი კერძი", "ხაჭაპურ", "საოჯახო ნაყინი", "ნაყინი საოჯახო"]):
        return "frozen", "frozen"

    # Sweets
    if any(k in text for k in ["ტკბილეულ", "კანფეტ", "შოკოლად", "ბომბონერ", "ჰალვა", "გოზინაყ", "ჟელიბონ", "საღეჭ", "ტკბილეულის შეკვრა", "საბავშვო ტკბილეული"]):
        return "candy", "sweets"
    if "ნაყინ" in text:
        return "ice_cream", "sweets"

    # Snacks
    if any(k in text for k in ["სნექ", "ჩიფს", "სუხარიკ", "კრეკერ", "მარილიანი და ტკბილი სნექი", "ჩირი და თხილი"]):
        return "snacks", "snacks"
    if any(k in text for k in ["თხილ", "ნუშ", "მიწისთხილ"]):
        return "nuts_dried", "snacks"

    # Coffee / tea / cereals
    if any(k in text for k in ["ყავ", "ხსნადი ყავა", "ერთჯერადი ყავა", "დაფქული ყავა"]):
        return "cereals", "hot_drinks"
    if any(k in text for k in ["ჩაი", "მცენარეული", "შავი ჩაი", "მწვანე ჩაი", "ცივი ჩაი", "ცივი ყავა"]):
        return "cereals", "hot_drinks"
    if any(k in text for k in ["მარცვლეულ", "ბურღულ", "ბრინჯ", "ატრია", "ლაფშა", "მაკარონ", "სპაგეტ", "ვერმიშელ", "პასტა", "ბურღულეული"]):
        return "cereals", "groceries"

    # Drinks
    if any(k in text for k in ["სასმელ", "წყალ", "წვენ", "კომპოტ", "სიროფ", "ლიმონათ", "გაზიან", "უალკოჰოლო", "მინერალური", "ულაქტოზო სასმელი", "მატონიზირებელი წყალი"]):
        return "juice_nectar", "drinks"
    if any(k in text for k in ["ლუდ", "ღვინ", "არაყ", "ლიქიორ", "ვერმუტ", "სპირტიან", "ალკოჰოლურ", "ჭაჭა", "ქართული ღვინო", "უცხოური ღვინო", "ცქრიალა ღვინო"]):
        return "alcohol", "drinks"
    if "ენერგეტიკულ" in text:
        return "energy_drinks", "drinks"

    # Oils / sauces / condiments
    if any(k in text for k in ["ზეთ", "ძმარ", "სოუს", "საწებელ", "მაიონეზ", "ტყემალ"]):
        return "sauces", "groceries"

    # Canned / staples
    if any(k in text for k in ["კონსერვ", "ბაკალეა", "მშრალი ბაკალეა"]):
        return "canned_goods", "groceries"
    if any(k in text for k in ["შაქარ", "მარილ", "ფქვილ", "საცხობ"]):
        return "flour_sugar_salt", "groceries"
    if any(k in text for k in ["თაფლ", "მურაბა", "ჯემ"]):
        return "jams_honey", "groceries"

    # Special diets
    if any(k in text for k in ["bio", "უგლუტენო", "ულაქტოზო", "დიეტურ", "დიაბეტურ"]):
        return "special_diet", "groceries"

    # Spar / Goodwill private labels
    if any(k in text for k in ["სპარის წარმოება", "გუდვილის ექსკლუზიური ბრენდები"]):
        return "private_label", "groceries"

    # Generic food
    if "სურსათ" in text:
        return "groceries", "groceries"

    # Default
    return "other", "other"


def extract_unit(name: str, size: str) -> str | None:
    text = f"{name or ''} {size or ''}"
    patterns = [
        r"\d+(?:[.,]\d+)?\s*(?:კგ|kg)",
        r"\d+(?:[.,]\d+)?\s*(?:გ|gr|გრ|g)\b",
        r"\d+(?:[.,]\d+)?\s*(?:ლ|l|ლიტრი)\b",
        r"\d+(?:[.,]\d+)?\s*(?:მლ|ml)\b",
        r"\d+(?:[.,]\d+)?\s*(?:ც|ცალი|pcs|pc)",
        r"\d+(?:[.,]\d+)?\s*(?:კგ|kg|kilo)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return size if size else None


def init_retail_db() -> None:
    conn = sqlite3.connect(RETAIL_DB)
    conn.executescript(
        """
        DROP TABLE IF EXISTS prices;
        DROP TABLE IF EXISTS products;
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT,
            barcode TEXT,
            image_url TEXT,
            unit TEXT,
            store_slug TEXT,
            category_slug TEXT,
            parent_category_slug TEXT,
            city_slug TEXT,
            chain_rank INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            original_price REAL,
            sale_price REAL,
            discount_percent REAL,
            is_on_sale INTEGER,
            recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX idx_prices_product_id ON prices(product_id);
        CREATE INDEX idx_prices_recorded_at ON prices(recorded_at);
        CREATE INDEX idx_products_store ON products(store_slug);
        CREATE INDEX idx_products_category ON products(category_slug);
        CREATE INDEX idx_products_parent_category ON products(parent_category_slug);
        CREATE INDEX idx_products_city ON products(city_slug);
        CREATE INDEX idx_products_barcode ON products(barcode);
        """
    )
    conn.commit()
    conn.close()


def migrate() -> dict:
    if not GAMIGE_DB.exists():
        raise FileNotFoundError(f"gamige_grocery.db not found at {GAMIGE_DB}")

    init_retail_db()

    src = sqlite3.connect(GAMIGE_DB)
    src.row_factory = sqlite3.Row
    dst = sqlite3.connect(RETAIL_DB)
    dst.row_factory = sqlite3.Row

    cur_src = src.cursor()
    cur_dst = dst.cursor()

    # Load all products
    cur_src.execute("SELECT id, name, size, category, image_url, barcode FROM products")
    products = {str(row["id"]): dict(row) for row in cur_src.fetchall()}

    # Load all prices
    cur_src.execute("SELECT product_id, store, price, old_price, in_stock, product_url FROM prices")
    prices = cur_src.fetchall()

    inserted_products = 0
    inserted_prices = 0
    skipped_no_store = 0
    skipped_no_price = 0
    unknown_stores = set()
    next_id = 1

    for pr in prices:
        pid = str(pr["product_id"])
        product = products.get(pid)
        if not product:
            continue

        store_name = pr["store"]
        if not store_name:
            skipped_no_store += 1
            continue

        price = pr["price"]
        if price is None:
            skipped_no_price += 1
            continue

        store_slug = store_to_slug(store_name)
        if store_name not in STORE_SLUG_MAP:
            unknown_stores.add(store_name)

        category_slug, parent_slug = map_category(product["category"], product["name"])
        unit = extract_unit(product["name"], product["size"])

        old_price = pr["old_price"]
        original_price = float(old_price) if old_price is not None else float(price)
        sale_price = float(price)
        is_on_sale = 0
        discount_percent = 0
        if old_price is not None and old_price > price:
            is_on_sale = 1
            discount_percent = round((old_price - price) / old_price * 100, 2)

        # Generate a unique product ID for this product-store combination
        unique_id = next_id
        next_id += 1

        cur_dst.execute(
            """
            INSERT INTO products (id, name, barcode, image_url, unit, store_slug, category_slug,
                                  parent_category_slug, city_slug, chain_rank)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                unique_id,
                product["name"],
                product["barcode"],
                product["image_url"],
                unit,
                store_slug,
                category_slug,
                parent_slug,
                "tbilisi",
                CHAIN_RANK.get(store_slug, 99),
            ),
        )

        cur_dst.execute(
            """
            INSERT INTO prices (product_id, original_price, sale_price, discount_percent, is_on_sale)
            VALUES (?, ?, ?, ?, ?)
            """,
            (unique_id, original_price, sale_price, discount_percent, is_on_sale),
        )

        inserted_products += 1
        inserted_prices += 1

    dst.commit()
    dst.close()
    src.close()

    return {
        "products": inserted_products,
        "prices": inserted_prices,
        "skipped_no_store": skipped_no_store,
        "skipped_no_price": skipped_no_price,
        "unknown_stores": sorted(unknown_stores),
    }


def main():
    print("Migrating gamige_grocery.db -> retail_data.db")
    stats = migrate()

    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print(f"  product-store rows inserted: {stats['products']}")
    print(f"  price rows inserted: {stats['prices']}")
    print(f"  skipped (no store): {stats['skipped_no_store']}")
    print(f"  skipped (no price): {stats['skipped_no_price']}")
    if stats["unknown_stores"]:
        print(f"  unknown stores mapped to slugs: {', '.join(stats['unknown_stores'])}")


if __name__ == "__main__":
    main()
