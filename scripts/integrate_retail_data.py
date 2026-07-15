"""
Georgia Retail Intelligence — Integration Script

Run this to test the current retail data connection and verify that
the simulation can read from the shared retail database.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from data_pipeline.retail_connector import RetailConnector
from economy_engine.market import Market


def test_connection():
    print("=" * 60)
    print("GEORGIA RETAIL INTELLIGENCE — CONNECTION TEST")
    print("=" * 60)

    # Use local SQLite by default unless Supabase is explicitly configured and works
    connector = RetailConnector(db_url="sqlite")

    # 1. Fetch some products
    print("\n📦 Fetching sample products...")
    df = connector.fetch_products(limit=10)
    if df.empty:
        print("❌ No products found. Make sure the collector has run at least once.")
        return False

    print(f"✅ Found {len(df)} sample products")
    print(df[["name", "store_slug", "original_price", "sale_price"]].head().to_string(index=False))

    # 2. Find cheapest milk
    print("\n🔍 Finding cheapest 'milk'...")
    cheapest = connector.get_cheapest("milk")
    if cheapest:
        print(f"✅ Cheapest: {cheapest['name']} @ {cheapest['store_slug']} — ₾{cheapest.get('sale_price') or cheapest.get('original_price')}")
    else:
        print("⚠️ No milk found in database.")

    # 3. Inflation snapshot
    print("\n📊 Inflation snapshot (all categories)...")
    snap = connector.get_inflation_snapshot()
    print(f"   Products tracked: {snap.get('product_count', 0)}")
    print(f"   Avg original price: ₾{snap.get('avg_original', 0):.2f}")
    print(f"   Avg sale price: ₾{snap.get('avg_sale', 0):.2f}")
    print(f"   Avg discount: {snap.get('avg_discount', 0):.1f}%")
    print(f"   Sale ratio: {snap.get('sale_ratio', 0):.1%}")

    return True


def test_simulation_integration():
    print("\n" + "=" * 60)
    print("SIMULATION INTEGRATION TEST")
    print("=" * 60)

    market = Market(use_live_data=True, city_slug="tbilisi")
    print(f"\n🏪 Stores loaded: {[s.name for s in market.stores]}")
    print(f"📈 Inflation index: {market.inflation_index:.4f}")

    if market.stores:
        store = market.stores[0]
        sample = store.products.head(3)
        print(f"\n🛒 Sample products from {store.name}:")
        for _, row in sample.iterrows():
            print(f"   • {row['name']} — ₾{row['price']:.2f}")


def run_collector():
    """Run the collector manually (requires georgia-retail-intelligence submodule)."""
    import subprocess
    collector_path = PROJECT_ROOT / "georgia-retail-intelligence" / "collector" / "main.py"
    if not collector_path.exists():
        print(f"❌ Collector not found at {collector_path}")
        return

    print("\n🚀 Running collector...")
    subprocess.run([sys.executable, str(collector_path)], cwd=PROJECT_ROOT / "georgia-retail-intelligence")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Georgia Retail Intelligence Integration")
    parser.add_argument("--test", action="store_true", help="Test retail connector against the active database")
    parser.add_argument("--sim", action="store_true", help="Test simulation integration")
    parser.add_argument("--collect", action="store_true", help="Run the legacy collector manually")
    args = parser.parse_args()

    if not any([args.test, args.sim, args.collect]):
        # Run all by default
        args.test = True
        args.sim = True

    if args.test:
        test_connection()
    if args.sim:
        test_simulation_integration()
    if args.collect:
        run_collector()
